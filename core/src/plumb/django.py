"""Read Django URL patterns and database settings.

Routes come from `urlpatterns` in urls.py files: each `path()`, `re_path()`
or `url()` that points at a view is a route, `include("app.urls")` adds a
prefix to another file's routes, and `router.register()` from Django REST
framework is one route per registration. Regex patterns are shown in a
readable form: `^profiles/(?P<username>\\w+)/?$` becomes `/profiles/{username}`.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from tree_sitter import Node

from plumb.entrypoints import (
    EntryKind,
    EntryPoint,
    py_call_args,
    py_string,
    py_text,
    py_tree,
    walk,
)
from plumb.imports import PythonIndex
from plumb.inventory import Category, FileInfo

_ROUTE_CALLS = {"path", "re_path", "url"}
_ENGINES = {
    "sqlite3": "SQLite",
    "postgresql": "PostgreSQL",
    "postgresql_psycopg2": "PostgreSQL",
    "postgis": "PostgreSQL",
    "mysql": "MySQL",
    "oracle": "Oracle",
}
_ENGINE = re.compile(r"""["']ENGINE["']\s*:\s*["']django\.(?:contrib\.gis\.)?db\.backends\.(\w+)""")


def readable(pattern: str) -> str:
    """Turn a Django route pattern, regex or not, into /a/{b} form."""
    text = pattern.strip()
    text = re.sub(r"\(\?P<(\w+)>[^)]*\)", r"{\1}", text)  # regex groups
    text = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", text)  # path converters
    text = text.lstrip("^").rstrip("$")
    text = re.sub(r"/\?$", "", text).rstrip("?")
    return "/" + text.strip("/") if text.strip("/") else ""


@dataclass(frozen=True)
class UrlFile:
    routes: tuple[tuple[str, int], ...]  # (readable path, line)
    includes: tuple[tuple[str, str], ...]  # (prefix, module name)


def read_urls(source: bytes) -> UrlFile:
    root = py_tree(source).root_node
    routes: list[tuple[str, int]] = []
    includes: list[tuple[str, str]] = []
    registered: list[tuple[str, int]] = []
    router_mounts: list[str] = []
    for node in walk(root):
        if node.type != "call":
            continue
        function = py_text(node.child_by_field_name("function"))
        positional, _ = py_call_args(node)
        if function.endswith(".register") and positional:
            name = py_string(positional[0])
            if name is not None:
                registered.append((readable(name), node.start_point.row + 1))
            continue
        if function not in _ROUTE_CALLS or len(positional) < 2:
            continue
        pattern = py_string(positional[0])
        if pattern is None:
            continue
        prefix = readable(pattern)
        target = positional[1]
        line = node.start_point.row + 1
        included = _included(target)
        if included is None:
            routes.append((prefix or "/", line))
        elif included.endswith(".urls") and "." not in included.removesuffix(".urls"):
            router_mounts.append(prefix)  # include(router.urls)
        elif included.startswith("module:"):
            includes.append((prefix, included.removeprefix("module:")))
        else:
            routes.append((prefix or "/", line))  # admin.site.urls and the like
    for mount in router_mounts or ([""] if registered else []):
        routes.extend((mount + path, line) for path, line in registered)
    return UrlFile(tuple(routes), tuple(includes))


def _included(target: Node) -> str | None:
    """What an include() points at: "module:app.urls", "router.urls", or None for a view."""
    if target.type == "call" and py_text(target.child_by_field_name("function")) == "include":
        positional, _ = py_call_args(target)
        if not positional:
            return None
        literal = py_string(positional[0])
        if literal is not None:
            return f"module:{literal}"
        first = positional[0]
        if first.type == "tuple" and first.named_children:
            inner = py_string(first.named_children[0])
            if inner is not None:
                return f"module:{inner}"
        return py_text(first)
    if target.type == "attribute" and py_text(target).endswith("site.urls"):
        return "admin.site.urls"
    return None


def django_routes(repo: Path, files: list[FileInfo]) -> list[EntryPoint]:
    python = [
        f.path
        for f in files
        if f.category is Category.SOURCE and f.path.endswith(".py") and f.language == "python"
    ]
    url_files = [p for p in python if PurePosixPath(p).name == "urls.py"]
    if not url_files:
        return []
    index = PythonIndex(python)
    parsed = {path: read_urls((repo / path).read_bytes()) for path in url_files}
    parents: dict[str, list[tuple[str, str]]] = defaultdict(list)  # child -> (parent, prefix)
    for path, info in parsed.items():
        for prefix, module in info.includes:
            child = index.file_of.get(module)
            if child in parsed:
                parents[child].append((path, prefix))

    def prefixes(path: str, seen: frozenset[str]) -> list[str]:
        if path in seen or not parents.get(path):
            return [""]
        found: list[str] = []
        for parent, prefix in parents[path]:
            found += [p + prefix for p in prefixes(parent, seen | {path})]
        return list(dict.fromkeys(found))[:4]

    routes: list[EntryPoint] = []
    for path, info in parsed.items():
        for route, line in info.routes:
            for prefix in prefixes(path, frozenset()):
                full = (prefix + route).replace("//", "/") or "/"
                entry = EntryPoint(EntryKind.HTTP, f"ANY {full}", path, line, "django")
                routes.append(entry)
    return sorted(routes, key=lambda e: (e.path, e.line))


def django_databases(text: str) -> list[tuple[str, int]]:
    """Database products named by ENGINE in a settings file, with their lines."""
    found: list[tuple[str, int]] = []
    for match in _ENGINE.finditer(text):
        name = _ENGINES.get(match.group(1))
        if name:
            found.append((name, text.count("\n", 0, match.start()) + 1))
    return found
