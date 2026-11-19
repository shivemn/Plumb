"""Follow a request from its route handler through the repo's own code.

Starting at the function a route runs, calls are followed into other repo
files when the name called was imported from one: `crud.create_user(...)`,
`UserService(db).get(...)`, `get_user(...)`. Calls into the database or out
to other services are recorded as what the request touches. The trace stops
at a few levels deep and never guesses: a call whose target cannot be found
from the imports is not followed.

The result reads like "GET /users/{id}: routes/users.py get_user, then
services/users.py UserService.get, then repositories/users.py
UserRepo.by_id, which queries the database".
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

from tree_sitter import Node

from plumb.entrypoints import EntryKind, EntryPoint, py_text, py_tree, walk
from plumb.graph import component_of
from plumb.imports import PythonIndex, python_imports
from plumb.inventory import Category, FileInfo

MAX_DEPTH = 4
MAX_STEPS = 10

_DATABASE_CALL = re.compile(
    r"\b(db|session|conn|connection|cursor|database|engine|tx)\."
    r"(execute|query|commit|add|add_all|delete|merge|scalars?|get|fetch\w*|refresh|exec|flush)$"
)
_OUTSIDE = {
    "requests": "an outside HTTP service",
    "httpx": "an outside HTTP service",
    "aiohttp": "an outside HTTP service",
    "urllib3": "an outside HTTP service",
    "redis": "Redis",
    "boto3": "AWS",
    "smtplib": "an email server",
    "pika": "RabbitMQ",
    "kafka": "Kafka",
    "confluent_kafka": "Kafka",
    "pymongo": "MongoDB",
    "motor": "MongoDB",
    "openai": "the OpenAI API",
    "anthropic": "the Anthropic API",
    "stripe": "Stripe",
}


@dataclass(frozen=True)
class Step:
    path: str
    line: int
    name: str  # "get_user", "UserService.get"
    caller: int | None = None  # index of the step that calls this one; None for the handler
    before: bool = False  # run by the framework before the handler, such as @ModelAttribute


@dataclass(frozen=True)
class Touch:
    what: str  # "the database", "Redis", "an outside HTTP service"
    call: str  # the call that does it, as written
    path: str
    line: int
    by: int = 0  # index of the step that makes the call


@dataclass(frozen=True)
class Flow:
    route: EntryPoint
    steps: tuple[Step, ...]
    touches: tuple[Touch, ...]


@dataclass(frozen=True)
class _Binding:
    path: str
    name: str | None  # None when the local name is a whole module


class _PythonFiles:
    def __init__(self, repo: Path, paths: list[str]) -> None:
        self.repo = repo
        self.index = PythonIndex(paths)
        self.paths = set(paths)

    @cache  # noqa: B019 - one instance per trace, dropped with it
    def tree(self, path: str) -> Node:
        return py_tree((self.repo / path).read_bytes()).root_node

    @cache  # noqa: B019
    def bindings(self, path: str) -> dict[str, _Binding]:
        """Local names in a file that point at other repo files, and outside modules."""
        found: dict[str, _Binding] = {}
        for item in python_imports((self.repo / path).read_bytes()):
            module = self.index.absolute(path, item)
            if module is None:
                continue
            if not item.names:  # import a.b.c
                hit = self.index.file_of.get(module)
                top = module.split(".")[0]
                found[top] = _Binding(hit or f"outside:{top}", None)
                continue
            for name, local in zip(item.names, item.local_names or item.names, strict=False):
                submodule = self.index.file_of.get(f"{module}.{name}" if module else name)
                if submodule:
                    found[local] = _Binding(submodule, None)
                elif module in self.index.file_of:
                    found[local] = _Binding(self.index.file_of[module], name)
                elif not item.level:
                    found[local] = _Binding(f"outside:{module.split('.')[0]}", name)
        return found

    def function(self, path: str, name: str) -> Node | None:
        """A top-level function, or a method written as Class.method."""
        owner, _, method = name.rpartition(".")
        for node in self.tree(path).named_children:
            definition = _definition(node)
            if definition is None:
                continue
            found = py_text(definition.child_by_field_name("name"))
            if not owner and definition.type == "function_definition" and found == name:
                return definition
            if owner and definition.type == "class_definition" and found == owner:
                body = definition.child_by_field_name("body")
                for member in body.named_children if body else []:
                    inner = _definition(member)
                    if (
                        inner is not None
                        and inner.type == "function_definition"
                        and py_text(inner.child_by_field_name("name")) == method
                    ):
                        return inner
        return None

    def is_class(self, path: str, name: str) -> bool:
        for node in self.tree(path).named_children:
            definition = _definition(node)
            if (
                definition is not None
                and definition.type == "class_definition"
                and py_text(definition.child_by_field_name("name")) == name
            ):
                return True
        return False


def _definition(node: Node) -> Node | None:
    if node.type == "decorated_definition":
        return node.child_by_field_name("definition")
    if node.type in ("function_definition", "class_definition"):
        return node
    return None


def _handler_at(root: Node, line: int) -> Node | None:
    """The function a route decorator on `line` (or a def on `line`) belongs to."""
    for node in walk(root):
        if node.type == "decorated_definition" and node.start_point.row + 1 <= line:
            definition = node.child_by_field_name("definition")
            if definition is not None and definition.start_point.row + 1 >= line:
                return definition if definition.type == "function_definition" else None
        if node.type == "function_definition" and node.start_point.row + 1 == line:
            return node
    return None


def _calls(function: Node) -> Iterator[Node]:
    body = function.child_by_field_name("body")
    if body is None:
        return
    for node in walk(body):
        if node.type == "call":
            yield node


def _class_of(path: str, function: Node) -> str | None:
    parent = function.parent
    while parent is not None:
        if parent.type == "class_definition":
            return py_text(parent.child_by_field_name("name"))
        parent = parent.parent
    return None


def _local_types(function: Node) -> dict[str, str]:
    """Variables whose class is known: typed parameters and `x = Class(...)`."""
    found: dict[str, str] = {}
    parameters = function.child_by_field_name("parameters")
    for param in parameters.named_children if parameters else []:
        if param.type not in ("typed_parameter", "typed_default_parameter"):
            continue
        name = param.child_by_field_name("name") or next(
            (c for c in param.named_children if c.type == "identifier"), None
        )
        annotation = py_text(param.child_by_field_name("type"))
        if name is not None and re.fullmatch(r"[A-Za-z_]\w*", annotation):
            found[py_text(name)] = annotation
    body = function.child_by_field_name("body")
    nodes: Iterator[Node] = walk(body) if body is not None else iter(())
    for node in nodes:
        if node.type != "assignment":
            continue
        left, right = node.child_by_field_name("left"), node.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier":
            continue
        if right.type == "await":
            right = right.named_children[0] if right.named_children else right
        if right.type == "call":
            callee = py_text(right.child_by_field_name("function"))
            if re.fullmatch(r"[A-Z]\w*", callee):
                found[py_text(left)] = callee
    return found


def _target(files: _PythonFiles, path: str, function: Node, call: Node) -> tuple[str, str] | None:
    """The repo file and function a call runs, if the imports say so."""
    callee = call.child_by_field_name("function")
    if callee is None:
        return None
    bindings = files.bindings(path)
    if callee.type == "identifier":
        name = py_text(callee)
        binding = bindings.get(name)
        if binding and binding.name and not binding.path.startswith("outside:"):
            if files.is_class(binding.path, binding.name):
                return binding.path, f"{binding.name}.__init__"
            return binding.path, binding.name
        if files.function(path, name) is not None:
            return path, name
        return None
    if callee.type != "attribute":
        return None
    method = py_text(callee.child_by_field_name("attribute"))
    obj = callee.child_by_field_name("object")
    if obj is None:
        return None
    if obj.type == "call":  # Service(db).method()
        obj = obj.child_by_field_name("function") or obj
    root = py_text(obj)
    typed = _local_types(function).get(root)
    if typed is not None:
        root = typed
    if root == "self":
        owner = _class_of(path, function)
        return (path, f"{owner}.{method}") if owner else None
    binding = bindings.get(root)
    if binding is None or binding.path.startswith("outside:"):
        return None
    if binding.name is None:  # module.function()
        return binding.path, method
    if files.is_class(binding.path, binding.name):  # Class.method() or Class(...).method()
        return binding.path, f"{binding.name}.{method}"
    return None


def _touch(files: _PythonFiles, path: str, call: Node) -> Touch | None:
    callee = py_text(call.child_by_field_name("function"))
    line = call.start_point.row + 1
    if _DATABASE_CALL.search(callee):
        return Touch("the database", callee, path, line)
    root = callee.split(".")[0].split("(")[0]
    binding = files.bindings(path).get(root)
    if binding is not None and binding.path.startswith("outside:"):
        what = _OUTSIDE.get(binding.path.removeprefix("outside:"))
        if what:
            return Touch(what, callee, path, line)
    return None


def trace_python(files: _PythonFiles, route: EntryPoint) -> Flow | None:
    handler = _handler_at(files.tree(route.path), route.line)
    if handler is None:
        return None
    name = py_text(handler.child_by_field_name("name"))
    steps: list[Step] = [Step(route.path, handler.start_point.row + 1, name)]
    touches: list[Touch] = []
    seen = {(route.path, name)}
    queue: list[tuple[str, Node, int, int]] = [(route.path, handler, 0, 0)]
    while queue and len(steps) < MAX_STEPS:
        path, function, depth, index = queue.pop(0)
        for call in _calls(function):
            touch = _touch(files, path, call)
            if touch is not None and touch.what not in {t.what for t in touches}:
                touches.append(replace(touch, by=index))
            target = _target(files, path, function, call)
            if target is None or target in seen or depth + 1 >= MAX_DEPTH:
                continue
            if target[1].endswith(".__init__"):  # building an object is not a step
                continue
            seen.add(target)
            definition = files.function(*target)
            if definition is None:
                continue
            steps.append(Step(target[0], definition.start_point.row + 1, target[1], index))
            queue.append((target[0], definition, depth + 1, len(steps) - 1))
            if len(steps) >= MAX_STEPS:
                break
    return Flow(route, tuple(steps), tuple(touches))


def trace_flows(repo: Path, files: list[FileInfo], entry_points: list[EntryPoint]) -> list[Flow]:
    """Traces for HTTP routes whose handler could be found, in Python or Java."""
    from plumb.javaflow import JavaFiles, trace_java  # imports this module's types

    def source(language: str, suffix: str) -> list[str]:
        return [
            f.path
            for f in files
            if f.category is Category.SOURCE and f.language == language and f.path.endswith(suffix)
        ]

    routes = [e for e in entry_points if e.kind is EntryKind.HTTP]
    python = _PythonFiles(repo, source("python", ".py"))
    java_paths = source("java", ".java")
    java = JavaFiles(repo, java_paths) if any(r.path.endswith(".java") for r in routes) else None
    flows: list[Flow] = []
    for route in routes:
        flow = None
        if route.path in python.paths:
            flow = trace_python(python, route)
        elif java is not None and route.path in java.paths:
            flow = trace_java(java, route)
        if flow is not None:
            flows.append(flow)
    return flows


def layers(flow: Flow) -> tuple[str, ...]:
    """The folders a request passes through, in order, each once."""
    found: list[str] = []
    for step in flow.steps:
        folder = component_of(step.path)
        if folder not in found:
            found.append(folder)
    return tuple(found)
