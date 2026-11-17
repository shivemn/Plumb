"""Find the ways into a repo's code: routes, commands, consumers, jobs and mains.

Everything here is read from the syntax tree or from build files, never
guessed. Values that are only known at run time (a path held in a
variable, a topic read from settings) are reported as written, so the
report can say where they come from instead of inventing a value.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path, PurePosixPath

import tree_sitter_python
from tree_sitter import Language, Node, Parser

from plumb.inventory import Category, FileInfo


class EntryKind(StrEnum):
    HTTP = "http"
    COMMAND = "command"
    CONSUMER = "consumer"
    SCHEDULED = "scheduled"
    TASK = "task"
    MAIN = "main"
    SCRIPT = "script"


@dataclass(frozen=True)
class EntryPoint:
    kind: EntryKind
    name: str  # "GET /items/{id}", "serve", "topic credit-events"
    path: str
    line: int
    framework: str | None = None


_HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "websocket"}


@cache
def _python_parser() -> Parser:
    return Parser(Language(tree_sitter_python.language()))


def _text(node: Node | None) -> str:
    return node.text.decode("utf-8", "replace") if node is not None and node.text else ""


def _py_string(node: Node | None) -> str | None:
    """The value of a plain Python string literal, or None for anything else."""
    if node is None or node.type != "string":
        return None
    if any(c.type == "interpolation" for c in node.named_children):
        return None
    return "".join(_text(c) for c in node.named_children if c.type == "string_content")


def _walk(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _call_args(call: Node) -> tuple[list[Node], dict[str, Node]]:
    arguments = call.child_by_field_name("arguments")
    positional: list[Node] = []
    keywords: dict[str, Node] = {}
    if arguments is None:
        return positional, keywords
    for child in arguments.named_children:
        if child.type == "keyword_argument":
            name = child.child_by_field_name("name")
            value = child.child_by_field_name("value")
            if name is not None and value is not None:
                keywords[_text(name)] = value
        elif child.type != "comment":
            positional.append(child)
    return positional, keywords


def python_entry_points(path: str, source: bytes) -> list[EntryPoint]:
    tree = _python_parser().parse(source)
    framework = _python_cli_framework(source)
    prefixes = _router_prefixes(tree.root_node)
    found: list[EntryPoint] = []
    for node in _walk(tree.root_node):
        if node.type == "decorated_definition":
            found.extend(_from_decorators(node, path, framework, prefixes))
        elif node.type == "call":
            found.extend(_argparse_subcommand(node, path))
        elif node.type == "if_statement" and _is_main_guard(node):
            found.append(
                EntryPoint(EntryKind.MAIN, "run as a script", path, node.start_point.row + 1)
            )
    return sorted(found, key=lambda e: e.line)


def _python_cli_framework(source: bytes) -> str | None:
    if b"import typer" in source or b"from typer" in source:
        return "typer"
    if b"import click" in source or b"from click" in source:
        return "click"
    return None


def _router_prefixes(root: Node) -> dict[str, str]:
    """`router = APIRouter(prefix="/items")` gives {"router": "/items"}."""
    prefixes: dict[str, str] = {}
    for node in _walk(root):
        if node.type != "assignment":
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier" or right.type != "call":
            continue
        function = _text(right.child_by_field_name("function"))
        if function.split(".")[-1] in ("APIRouter", "Blueprint"):
            _, keywords = _call_args(right)
            prefix = _py_string(keywords.get("prefix") or keywords.get("url_prefix"))
            if prefix:
                prefixes[_text(left)] = prefix
    return prefixes


def _from_decorators(
    node: Node, path: str, framework: str | None, prefixes: dict[str, str]
) -> list[EntryPoint]:
    definition = node.child_by_field_name("definition")
    function_name = _text(definition.child_by_field_name("name")) if definition else ""
    found: list[EntryPoint] = []
    for decorator in (c for c in node.children if c.type == "decorator"):
        expression = decorator.named_children[0] if decorator.named_children else None
        if expression is None:
            continue
        call = expression if expression.type == "call" else None
        target = call.child_by_field_name("function") if call is not None else expression
        if target is None:
            continue
        dotted = _text(target)
        owner, _, method = dotted.rpartition(".")
        line = decorator.start_point.row + 1
        positional, keywords = _call_args(call) if call is not None else ([], {})
        first = _py_string(positional[0]) if positional else None

        if call is not None and method in _HTTP_METHODS | {"route", "api_route"}:
            if first is None or not first.startswith("/"):
                continue
            verb = method.upper() if method in _HTTP_METHODS else _route_methods(keywords)
            full = prefixes.get(owner, "") + first
            found.append(EntryPoint(EntryKind.HTTP, f"{verb} {full}", path, line, _web(method)))
        elif method in ("command", "group") or dotted in ("click.command", "click.group"):
            name = first or _py_string(keywords.get("name")) or function_name.replace("_", "-")
            found.append(EntryPoint(EntryKind.COMMAND, name, path, line, framework))
        elif dotted in ("shared_task", "celery.shared_task") or method == "task":
            found.append(EntryPoint(EntryKind.TASK, function_name, path, line, "celery"))
    return found


def _route_methods(keywords: dict[str, Node]) -> str:
    methods = keywords.get("methods")
    if methods is not None and methods.type in ("list", "tuple"):
        values = [_py_string(c) for c in methods.named_children]
        named = [v.upper() for v in values if v]
        if named:
            return ",".join(named)
    return "GET"


def _web(method: str) -> str:
    return "flask" if method == "route" else "fastapi"


def _argparse_subcommand(node: Node, path: str) -> list[EntryPoint]:
    function = node.child_by_field_name("function")
    if function is None or function.type != "attribute":
        return []
    if _text(function.child_by_field_name("attribute")) != "add_parser":
        return []
    positional, _ = _call_args(node)
    name = _py_string(positional[0]) if positional else None
    if not name:
        return []
    return [EntryPoint(EntryKind.COMMAND, name, path, node.start_point.row + 1, "argparse")]


def _is_main_guard(node: Node) -> bool:
    condition = _text(node.child_by_field_name("condition")).replace("'", '"').replace(" ", "")
    return condition in ('__name__=="__main__"', '"__main__"==__name__')


def pyproject_scripts(path: str, source: bytes) -> list[EntryPoint]:
    """Commands a Python package installs, from [project.scripts]."""
    try:
        data = tomllib.loads(source.decode("utf-8", "replace"))
    except tomllib.TOMLDecodeError:
        return []
    scripts = data.get("project", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    lines = source.decode("utf-8", "replace").splitlines()
    found: list[EntryPoint] = []
    for name, target in scripts.items():  # pyright: ignore[reportUnknownVariableType]
        line = next(
            (i + 1 for i, text in enumerate(lines) if text.strip().startswith(f"{name} ")), 1
        )
        found.append(EntryPoint(EntryKind.COMMAND, f"{name} ({target})", path, line, "package"))
    return found


def find_entry_points(repo: Path, files: list[FileInfo]) -> list[EntryPoint]:
    found: list[EntryPoint] = []
    for info in files:
        if (
            info.category is not Category.SOURCE
            and PurePosixPath(info.path).name != "pyproject.toml"
        ):
            continue
        if info.language == "python" and info.path.endswith(".py"):
            found.extend(python_entry_points(info.path, (repo / info.path).read_bytes()))
        elif info.path.endswith("pyproject.toml") and info.category is Category.CONFIG:
            found.extend(pyproject_scripts(info.path, (repo / info.path).read_bytes()))
    return found
