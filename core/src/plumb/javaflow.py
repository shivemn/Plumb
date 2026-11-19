"""Follow a Spring request from its controller method through the repo's own classes.

A call such as `this.owners.findById(id)` is followed by the type of
`owners`: a field, a constructor or method parameter, or a local variable.
An interface with one implementation in the repo is followed into that
class. A repository interface (one extending a Spring Data repository, or
named ...Repository or ...Dao with no single implementation) is where the
request reaches the database. Templates for JDBC, REST, Kafka and RabbitMQ
are recorded as what the request touches.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import tree_sitter_java
from tree_sitter import Language, Node, Parser

from plumb.entrypoints import EntryPoint, py_text, walk
from plumb.flow import MAX_DEPTH, MAX_STEPS, Flow, Step, Touch

_SPRING_DATA = re.compile(r"\b(Jpa|Crud|PagingAndSorting|ListCrud|Mongo|Reactive\w*|)Repository\b")
_REPOSITORY_NAME = re.compile(r"(Repository|Dao|DAO|Repo)$")
_TEMPLATES = {
    "JdbcTemplate": "the database",
    "NamedParameterJdbcTemplate": "the database",
    "EntityManager": "the database",
    "JdbcClient": "the database",
    "MongoTemplate": "MongoDB",
    "RedisTemplate": "Redis",
    "StringRedisTemplate": "Redis",
    "RestTemplate": "an outside HTTP service",
    "RestClient": "an outside HTTP service",
    "WebClient": "an outside HTTP service",
    "KafkaTemplate": "Kafka",
    "RabbitTemplate": "RabbitMQ",
    "JmsTemplate": "a JMS queue",
}


@cache
def _java_parser() -> Parser:
    return Parser(Language(tree_sitter_java.language()))


@dataclass(frozen=True)
class _Type:
    name: str
    path: str
    node: Node  # class or interface declaration
    interface: bool
    supertypes: tuple[str, ...]


def _simple(type_text: str) -> str:
    """`List<Owner>` -> List, `org.x.Owner` -> Owner."""
    return type_text.split("<")[0].split(".")[-1].strip().rstrip("[]")


def _supertypes(node: Node) -> tuple[str, ...]:
    names: list[str] = []
    for field_name in ("superclass", "interfaces"):
        part = node.child_by_field_name(field_name)
        if part is not None:
            names += [_simple(t) for t in re.findall(r"[\w.]+(?:<[^>]*>)?", py_text(part))]
    for child in node.named_children:
        if child.type == "extends_interfaces":
            names += [_simple(t) for t in re.findall(r"[\w.]+(?:<[^>]*>)?", py_text(child))]
    return tuple(n for n in names if n not in ("extends", "implements"))


class JavaFiles:
    def __init__(self, repo: Path, paths: list[str]) -> None:
        self.repo = repo
        self.paths = set(paths)
        self.types: dict[str, _Type] = {}
        self.implementations: defaultdict[str, list[str]] = defaultdict(list)
        for path in paths:
            for node in walk(self.tree(path)):
                if node.type not in ("class_declaration", "interface_declaration"):
                    continue
                name = py_text(node.child_by_field_name("name"))
                supertypes = _supertypes(node)
                interface = node.type == "interface_declaration"
                self.types.setdefault(name, _Type(name, path, node, interface, supertypes))
                if not interface:
                    for parent in supertypes:
                        self.implementations[parent].append(name)

    @cache  # noqa: B019 - one instance per trace
    def tree(self, path: str) -> Node:
        return _java_parser().parse((self.repo / path).read_bytes()).root_node

    def method(self, type_name: str, method: str) -> tuple[str, Node] | None:
        found = self.types.get(type_name)
        if found is None:
            return None
        body = found.node.child_by_field_name("body")
        for member in body.named_children if body else []:
            if member.type == "method_declaration" and (
                py_text(member.child_by_field_name("name")) == method
            ):
                return found.path, member
        for parent in found.supertypes:  # inherited from a class in the repo
            if parent in self.types and parent != type_name:
                hit = self.method(parent, method)
                if hit is not None:
                    return hit
        return None

    def is_repository(self, type_name: str) -> bool:
        found = self.types.get(type_name)
        if found is None:
            return bool(_REPOSITORY_NAME.search(type_name))
        if any(_SPRING_DATA.fullmatch(s) for s in found.supertypes):
            return True
        return (
            found.interface
            and bool(_REPOSITORY_NAME.search(type_name))
            and (len(self.implementations[type_name]) != 1)
        )

    def concrete(self, type_name: str) -> str | None:
        """The class a call on this type runs: itself, or an interface's one implementation."""
        found = self.types.get(type_name)
        if found is None:
            return None
        if not found.interface:
            return type_name
        impls = self.implementations[type_name]
        return impls[0] if len(impls) == 1 else None


def _variable_types(owner: Node, method: Node) -> dict[str, str]:
    """Types of fields, parameters and local variables visible in `method`."""
    found: dict[str, str] = {}

    def declare(type_node: Node | None, declarators: Iterator[Node]) -> None:
        for declarator in declarators:
            name = py_text(declarator.child_by_field_name("name"))
            if name and type_node is not None:
                found[name] = _simple(py_text(type_node))

    body = owner.child_by_field_name("body")
    for member in body.named_children if body else []:
        if member.type == "field_declaration":
            declare(member.child_by_field_name("type"), _declarators(member))
        if member.type == "constructor_declaration":
            _parameters(member, found)
    _parameters(method, found)
    for node in walk(method):
        if node.type == "local_variable_declaration":
            declare(node.child_by_field_name("type"), _declarators(node))
    return found


def _declarators(node: Node) -> Iterator[Node]:
    return (c for c in node.named_children if c.type == "variable_declarator")


def _parameters(method: Node, found: dict[str, str]) -> None:
    params = method.child_by_field_name("parameters")
    for param in params.named_children if params else []:
        name = py_text(param.child_by_field_name("name"))
        type_node = param.child_by_field_name("type")
        if name and type_node is not None:
            found[name] = _simple(py_text(type_node))


def _modifiers(node: Node) -> str:
    found = next((c for c in node.named_children if c.type == "modifiers"), None)
    return py_text(found)


def _model_attributes(owner: Node) -> list[Node]:
    body = owner.child_by_field_name("body")
    return [
        member
        for member in (body.named_children if body else [])
        if member.type == "method_declaration" and "@ModelAttribute" in _modifiers(member)
    ]


def _is_accessor(method: Node) -> bool:
    """A getter or setter with a one-statement body: not a step worth showing."""
    name = py_text(method.child_by_field_name("name"))
    body = method.child_by_field_name("body")
    statements = len(body.named_children) if body is not None else 0
    return bool(re.match(r"(get|set|is|has)[A-Z]", name)) and statements <= 1


def _owner(node: Node) -> Node | None:
    parent = node.parent
    while parent is not None and parent.type not in ("class_declaration", "interface_declaration"):
        parent = parent.parent
    return parent


def _handler_at(root: Node, line: int) -> Node | None:
    for node in walk(root):
        if node.type != "method_declaration":
            continue
        name = node.child_by_field_name("name")
        if name is not None and node.start_point.row + 1 <= line <= name.start_point.row + 1:
            return node
    return None


def trace_java(files: JavaFiles, route: EntryPoint) -> Flow | None:
    handler = _handler_at(files.tree(route.path), route.line)
    owner = _owner(handler) if handler is not None else None
    if handler is None or owner is None:
        return None
    owner_name = py_text(owner.child_by_field_name("name"))
    first = f"{owner_name}.{py_text(handler.child_by_field_name('name'))}"
    steps = [Step(route.path, handler.start_point.row + 1, first)]
    touches: list[Touch] = []
    seen = {first}
    queue: list[tuple[str, str, Node, Node, int, int]] = [
        (route.path, owner_name, owner, handler, 0, 0)
    ]
    # Spring runs a controller's @ModelAttribute methods before each of its handlers.
    for member in _model_attributes(owner):
        name = f"{owner_name}.{py_text(member.child_by_field_name('name'))}"
        seen.add(name)
        steps.append(Step(route.path, member.start_point.row + 1, name, 0, before=True))
        queue.append((route.path, owner_name, owner, member, 0, len(steps) - 1))
    while queue and len(steps) < MAX_STEPS:
        path, type_name, type_node, method, depth, index = queue.pop(0)
        variables = _variable_types(type_node, method)
        for call in walk(method):
            if call.type != "method_invocation":
                continue
            name = py_text(call.child_by_field_name("name"))
            obj = call.child_by_field_name("object")
            target_type = type_name
            if obj is not None:
                text = py_text(obj).removeprefix("this.")
                if text == "this":
                    target_type = type_name
                elif text in variables:
                    target_type = variables[text]
                elif text in files.types:  # a static call
                    target_type = text
                else:
                    continue
            line = call.start_point.row + 1
            what = _TEMPLATES.get(target_type)
            if what is None and target_type != type_name and files.is_repository(target_type):
                what = "the database"
            if what is not None:
                if what not in {t.what for t in touches}:
                    # Name the type, not the variable: OwnerRepository.save, not this.owners.save
                    touches.append(Touch(what, f"{target_type}.{name}", path, line, index))
                continue
            concrete = files.concrete(target_type)
            key = f"{concrete}.{name}"
            if concrete is None or key in seen or depth + 1 >= MAX_DEPTH:
                continue
            hit = files.method(concrete, name)
            if hit is None:
                continue
            seen.add(key)
            target_path, target_method = hit
            if _is_accessor(target_method):
                continue
            steps.append(Step(target_path, target_method.start_point.row + 1, key, index))
            target_owner = _owner(target_method)
            if target_owner is not None:
                at = len(steps) - 1
                queue.append((target_path, concrete, target_owner, target_method, depth + 1, at))
            if len(steps) >= MAX_STEPS:
                break
    return Flow(route, tuple(steps), tuple(touches))
