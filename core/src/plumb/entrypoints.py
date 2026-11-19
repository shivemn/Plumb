"""Find the ways into a repo's code: routes, commands, consumers, jobs and mains.

Everything here is read from the syntax tree or from build files, never
guessed. Values that are only known at run time (a path held in a
variable, a topic read from settings) are reported as written, so the
report can say where they come from instead of inventing a value.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from enum import StrEnum
from functools import cache
from pathlib import Path, PurePosixPath
from typing import cast

import tree_sitter_java
import tree_sitter_python
from tree_sitter import Language, Node, Parser, Tree

from plumb.inventory import Category, FileInfo
from plumb.jsimports import js_parser_for
from plumb.springconfig import SpringSettings, load_spring_settings


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
    # Where a value in `name` was filled in from, such as a settings file.
    resolved_from: tuple[tuple[str, int], ...] = ()
    # The router or app object a route hangs off, used to join prefixes.
    router: str | None = field(default=None, compare=False)


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
            # "" is a real path in a decorator: the route sits at the router's prefix.
            if first is None or (first and not first.startswith("/")):
                continue
            verb = method.upper() if method in _HTTP_METHODS else _route_methods(keywords)
            full = prefixes.get(owner, "") + first
            entry = EntryPoint(EntryKind.HTTP, f"{verb} {full}", path, line, _web(method))
            found.append(replace(entry, router=owner or None))
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


@cache
def _java_parser() -> Parser:
    return Parser(Language(tree_sitter_java.language()))


_SPRING_MAPPINGS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": "",
}
_JAVA_CONSUMERS = {
    "KafkaListener": ("kafka", ("topics", "topicPattern", "value")),
    "RabbitListener": ("rabbitmq", ("queues", "value")),
    "JmsListener": ("jms", ("destination",)),
    "SqsListener": ("sqs", ("value", "queueNames")),
}


def _java_annotations(node: Node) -> list[Node]:
    modifiers = next((c for c in node.children if c.type == "modifiers"), None)
    if modifiers is None:
        return []
    return [c for c in modifiers.children if c.type in ("annotation", "marker_annotation")]


def _annotation_values(annotation: Node, keys: tuple[str, ...]) -> list[str]:
    """String values given for any of `keys`; a bare argument counts as "value"."""
    arguments = annotation.child_by_field_name("arguments")
    if arguments is None:
        return []
    values: list[str] = []
    for child in arguments.named_children:
        if child.type == "element_value_pair":
            key = _text(child.child_by_field_name("key"))
            if key in keys:
                values.extend(_java_strings(child.child_by_field_name("value")))
        elif "value" in keys:
            values.extend(_java_strings(child))
    return values


def _annotation_raw(annotation: Node, key: str) -> str | None:
    arguments = annotation.child_by_field_name("arguments")
    for child in arguments.named_children if arguments is not None else []:
        if child.type == "element_value_pair" and _text(child.child_by_field_name("key")) == key:
            return _text(child.child_by_field_name("value"))
    return None


def _java_strings(node: Node | None) -> list[str]:
    if node is None:
        return []
    if node.type == "string_literal":
        return ["".join(_text(c) for c in node.named_children if c.type == "string_fragment")]
    if node.type == "element_value_array_initializer":
        return [v for c in node.named_children for v in _java_strings(c)]
    # A constant or expression: keep it as written so the report can name it.
    return [f"{{{_text(node)}}}"]


def java_entry_points(path: str, source: bytes) -> list[EntryPoint]:
    tree = _java_parser().parse(source)
    found: list[EntryPoint] = []
    for node in _walk(tree.root_node):
        if node.type != "class_declaration":
            continue
        class_name = _text(node.child_by_field_name("name"))
        prefixes = [""]
        for annotation in _java_annotations(node):
            if _text(annotation.child_by_field_name("name")) == "RequestMapping":
                prefixes = _annotation_values(annotation, ("value", "path")) or [""]
        body = node.child_by_field_name("body")
        for method in body.named_children if body is not None else []:
            if method.type == "method_declaration":
                found.extend(_java_method(method, path, class_name, prefixes))
    return sorted(found, key=lambda e: e.line)


def _java_method(method: Node, path: str, class_name: str, prefixes: list[str]) -> list[EntryPoint]:
    name = _text(method.child_by_field_name("name"))
    found: list[EntryPoint] = []
    for annotation in _java_annotations(method):
        kind = _text(annotation.child_by_field_name("name")).split(".")[-1]
        line = annotation.start_point.row + 1
        if kind in _SPRING_MAPPINGS:
            verb = _SPRING_MAPPINGS[kind] or _request_method(annotation)
            paths = _annotation_values(annotation, ("value", "path")) or [""]
            for prefix in prefixes:
                for sub in paths:
                    route = (prefix.rstrip("/") + "/" + sub.lstrip("/")).rstrip("/") or "/"
                    found.append(
                        EntryPoint(EntryKind.HTTP, f"{verb} {route}", path, line, "spring")
                    )
        elif kind in _JAVA_CONSUMERS:
            system, keys = _JAVA_CONSUMERS[kind]
            targets = _annotation_values(annotation, keys) or [name]
            group = _annotation_values(annotation, ("groupId", "group"))
            suffix = f", group {group[0]}" if group else ""
            for target in targets:
                label = f"{target}{suffix}"
                found.append(EntryPoint(EntryKind.CONSUMER, label, path, line, system))
        elif kind == "Scheduled":
            found.append(
                EntryPoint(EntryKind.SCHEDULED, _schedule(annotation, name), path, line, "spring")
            )
    if name == "main" and _is_static_main(method):
        line = method.start_point.row + 1
        found.append(EntryPoint(EntryKind.MAIN, class_name, path, line))
    return found


def _request_method(annotation: Node) -> str:
    raw = _annotation_raw(annotation, "method")
    if not raw:
        return "ANY"
    verbs = [part.split(".")[-1] for part in raw.strip("{}").split(",")]
    return ",".join(v.strip() for v in verbs if v.strip())


def _schedule(annotation: Node, method_name: str) -> str:
    for key, label in (("cron", "cron"), ("fixedRate", "every"), ("fixedDelay", "delay")):
        raw = _annotation_raw(annotation, key)
        if raw:
            value = raw.strip('"')
            unit = "" if key == "cron" else " ms"
            return f"{method_name} ({label} {value}{unit})"
    return method_name


def _is_static_main(method: Node) -> bool:
    modifiers = next((c for c in method.children if c.type == "modifiers"), None)
    parameters = _text(method.child_by_field_name("parameters")).replace(" ", "")
    is_static = modifiers is not None and "static" in _text(modifiers).split()
    return is_static and parameters.startswith(("(String[]", "(String..."))


_EXPRESS_OWNERS = {"app", "router", "server", "api", "routes", "fastify"}
_NEXT_ROUTE = re.compile(r"(?:^|/)app/(?P<route>.*?)/?route\.(?:ts|js|tsx|jsx|mjs)$")
_NEXT_API = re.compile(r"(?:^|/)pages/(?P<route>api/.+?)(?:/index)?\.(?:ts|js|tsx|jsx|mjs)$")


def js_entry_points(path: str, source: bytes) -> list[EntryPoint]:
    """Express-style routes (`app.get("/x", ...)`) and Next.js route files."""
    found: list[EntryPoint] = []
    for pattern in (_NEXT_ROUTE, _NEXT_API):
        match = pattern.search(path)
        if match:
            route = "/" + re.sub(r"\(.*?\)/?", "", match["route"]).strip("/")
            found.append(EntryPoint(EntryKind.HTTP, f"ANY {route}", path, 1, "next.js"))
    tree = js_parser_for(path).parse(source)
    for node in _walk(tree.root_node):
        if node.type != "call_expression":
            continue
        function = node.child_by_field_name("function")
        if function is None or function.type != "member_expression":
            continue
        owner = _text(function.child_by_field_name("object"))
        method = _text(function.child_by_field_name("property"))
        if owner not in _EXPRESS_OWNERS or method not in _HTTP_METHODS | {"all", "use"}:
            continue
        arguments = node.child_by_field_name("arguments")
        first = arguments.named_children[0] if arguments and arguments.named_children else None
        route = _js_string(first)
        if route is None or not route.startswith("/") or method == "use":
            continue
        verb = "ANY" if method == "all" else method.upper()
        line = node.start_point.row + 1
        entry = EntryPoint(EntryKind.HTTP, f"{verb} {route}", path, line, "express")
        found.append(replace(entry, router=owner))
    return sorted(found, key=lambda e: e.line)


def _js_string(node: Node | None) -> str | None:
    if node is None or node.type != "string":
        return None
    return "".join(_text(c) for c in node.named_children if c.type == "string_fragment")


_SCRIPT_NAMES = ("start", "dev", "serve", "build", "test", "worker")


def package_json_entry_points(path: str, source: bytes) -> list[EntryPoint]:
    """Installed commands ("bin") and the usual run scripts from package.json."""
    try:
        data: object = json.loads(source.decode("utf-8", "replace"))
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []
    lines = source.decode("utf-8", "replace").splitlines()

    def line_of(key: str, start: int = 0) -> int:
        for index in range(start, len(lines)):
            if f'"{key}"' in lines[index]:
                return index + 1
        return start + 1

    found: list[EntryPoint] = []
    package = cast("dict[str, object]", data)
    bins = package.get("bin")
    bin_line = line_of("bin")
    if isinstance(bins, str):
        name = f"{package.get('name', 'bin')} ({bins})"
        found.append(EntryPoint(EntryKind.COMMAND, name, path, bin_line, "npm"))
    elif isinstance(bins, dict):
        for name, target in cast("dict[str, object]", bins).items():
            line = line_of(name, bin_line - 1)
            found.append(EntryPoint(EntryKind.COMMAND, f"{name} ({target})", path, line, "npm"))
    scripts = package.get("scripts")
    if isinstance(scripts, dict):
        start = line_of("scripts") - 1
        for name, command in cast("dict[str, object]", scripts).items():
            if name in _SCRIPT_NAMES:
                line = line_of(name, start)
                label = f"npm run {name}: {command}"
                found.append(EntryPoint(EntryKind.SCRIPT, label, path, line, "npm"))
    return found


_CONSOLE_SCRIPT = re.compile(r"^\s*([\w.-]+)\s*=\s*([\w.]+:[\w.]+)\s*$")


def setup_scripts(path: str, source: bytes) -> list[EntryPoint]:
    """Commands from console_scripts in setup.cfg or setup.py."""
    text = source.decode("utf-8", "replace")
    found: list[EntryPoint] = []
    lines = text.splitlines()
    if path.endswith("setup.cfg"):
        inside = False
        for number, line in enumerate(lines, start=1):
            if line.strip().startswith("console_scripts"):
                inside = True
                continue
            if inside and (not line.startswith((" ", "\t")) or not line.strip()):
                if line.strip():
                    inside = False
                continue
            match = _CONSOLE_SCRIPT.match(line) if inside else None
            if match:
                name = f"{match.group(1)} ({match.group(2)})"
                found.append(EntryPoint(EntryKind.COMMAND, name, path, number, "package"))
    else:
        for number, line in enumerate(lines, start=1):
            for match in re.finditer(r"[\"']([\w.-]+)\s*=\s*([\w.]+:[\w.]+)[\"']", line):
                if "console_scripts" in text:
                    name = f"{match.group(1)} ({match.group(2)})"
                    found.append(EntryPoint(EntryKind.COMMAND, name, path, number, "package"))
    return found


def find_entry_points(repo: Path, files: list[FileInfo]) -> list[EntryPoint]:
    found: list[EntryPoint] = []
    for info in files:
        name = PurePosixPath(info.path).name
        if info.category is Category.SOURCE and info.language == "python" and name.endswith(".py"):
            found.extend(python_entry_points(info.path, (repo / info.path).read_bytes()))
        elif info.category is Category.SOURCE and info.language == "java":
            found.extend(java_entry_points(info.path, (repo / info.path).read_bytes()))
        elif info.category is Category.SOURCE and info.language in ("javascript", "typescript"):
            found.extend(js_entry_points(info.path, (repo / info.path).read_bytes()))
        elif info.category is Category.CONFIG and name in ("setup.cfg", "setup.py"):
            found.extend(setup_scripts(info.path, (repo / info.path).read_bytes()))
        elif info.category is Category.CONFIG and name == "pyproject.toml":
            found.extend(pyproject_scripts(info.path, (repo / info.path).read_bytes()))
        elif info.category is Category.CONFIG and name == "package.json":
            found.extend(package_json_entry_points(info.path, (repo / info.path).read_bytes()))
    if any("${" in e.name for e in found):
        found = resolve_placeholders(found, load_spring_settings(repo, files))
    # These modules build on this one, so they are imported here.
    from plumb.openapi import find_openapi_routes

    found.extend(find_openapi_routes(repo, files, found))
    if any(PurePosixPath(f.path).name == "urls.py" for f in files):
        from plumb.django import django_routes

        found.extend(django_routes(repo, files))
    if any(e.router and e.framework in ("fastapi", "flask") for e in found):
        from plumb.mounts import join_mounts

        found = join_mounts(repo, files, found)
    if any(e.router and e.framework == "express" for e in found):
        from plumb.expressmounts import join_express_mounts

        found = join_express_mounts(repo, files, found)
    return found


def resolve_placeholders(found: list[EntryPoint], settings: SpringSettings) -> list[EntryPoint]:
    """Fill in ${...} values in Spring entry points from the settings files."""
    result: list[EntryPoint] = []
    for entry in found:
        if "${" not in entry.name or entry.framework in (None, "npm", "package"):
            result.append(entry)
            continue
        name, used = settings.resolve(entry.name)
        sources = tuple(dict.fromkeys((s.path, s.line) for s in used))
        result.append(replace(entry, name=name, resolved_from=sources))
    return result


# Helpers shared with plumb.mounts.
py_text = _text
py_string = _py_string
py_call_args = _call_args
walk = _walk


def py_tree(source: bytes) -> Tree:
    return _python_parser().parse(source)
