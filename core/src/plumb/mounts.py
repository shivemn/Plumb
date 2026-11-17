"""Join route prefixes that are added where a router is mounted, often in another file.

FastAPI routers are mounted with `parent.include_router(child, prefix=...)`
and Flask blueprints with `app.register_blueprint(bp, url_prefix=...)`.
A route's full path is every prefix on the way from the app down to it.
A prefix taken from settings (`settings.API_V1_STR`) is looked up as a
class attribute with a plain string default; if it cannot be found it is
kept as written in braces.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

from tree_sitter import Node

from plumb.entrypoints import EntryKind, EntryPoint, py_call_args, py_string, py_text, py_tree, walk
from plumb.imports import Import, PythonIndex, python_imports
from plumb.inventory import Category, FileInfo

RouterKey = tuple[str, str]  # (file, variable name)

_MOUNT_CALLS = {"include_router": "prefix", "register_blueprint": "url_prefix"}
_SETTING_DEFAULT = re.compile(
    rb"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=\n]+)?=\s*[\"']([^\"'\n]*)[\"']", re.M
)


@dataclass(frozen=True)
class Mount:
    parent: RouterKey
    child: RouterKey
    prefix: str


def _local_names(path: str, source: bytes, index: PythonIndex) -> dict[str, RouterKey | str]:
    """What each imported name means: a module file, or a (file, name) pair."""
    names: dict[str, RouterKey | str] = {}
    for item in python_imports(source):
        if not item.names:
            continue
        base = index.resolve(path, Import(item.module, (), item.level, item.line))
        local_names = item.local_names or item.names
        for name, local in zip(item.names, local_names, strict=False):
            as_module = index.resolve(path, Import(item.module, (name,), item.level, item.line))
            # "from app.api.routes import items" names a module file; "from
            # app.api.main import api_router" names something inside one.
            if as_module and (not base or as_module[0] != base[0]):
                names[local] = as_module[0]
            elif base:
                names[local] = (base[0], name)
    return names


def _key(expression: Node, path: str, names: dict[str, RouterKey | str]) -> RouterKey | None:
    text = py_text(expression)
    if expression.type == "identifier":
        meaning = names.get(text)
        return meaning if isinstance(meaning, tuple) else (path, text)
    if expression.type == "attribute":
        obj, _, attribute = text.rpartition(".")
        meaning = names.get(obj)
        if isinstance(meaning, str):
            return (meaning, attribute)
    return None


def find_mounts(repo: Path, files: list[FileInfo]) -> tuple[list[Mount], dict[str, str]]:
    paths = [
        f.path
        for f in files
        if f.language == "python" and f.path.endswith(".py") and f.category is Category.SOURCE
    ]
    index = PythonIndex(paths)
    settings: dict[str, set[str]] = defaultdict(set)
    mounts: list[Mount] = []
    for path in paths:
        source = (repo / path).read_bytes()
        for match in _SETTING_DEFAULT.finditer(source):
            settings[match.group(1).decode()].add(match.group(2).decode())
        if b"include_router" not in source and b"register_blueprint" not in source:
            continue
        names = _local_names(path, source, index)
        for node in walk(py_tree(source).root_node):
            if node.type != "call":
                continue
            function = node.child_by_field_name("function")
            if function is None or function.type != "attribute":
                continue
            method = py_text(function.child_by_field_name("attribute"))
            keyword = _MOUNT_CALLS.get(method)
            parent_node = function.child_by_field_name("object")
            if keyword is None or parent_node is None or parent_node.type != "identifier":
                continue
            positional, keywords = py_call_args(node)
            child = _key(positional[0], path, names) if positional else None
            if child is None:
                continue
            prefix_node = keywords.get(keyword)
            prefix = ""
            if prefix_node is not None:
                literal = py_string(prefix_node)
                prefix = literal if literal is not None else f"{{{py_text(prefix_node)}}}"
            mounts.append(Mount((path, py_text(parent_node)), child, prefix))
    unique = {name: next(iter(values)) for name, values in settings.items() if len(values) == 1}
    return mounts, unique


def _resolve_setting(prefix: str, settings: dict[str, str]) -> str:
    match = re.fullmatch(r"\{\w+\.([A-Za-z_][A-Za-z0-9_]*)\}", prefix)
    if match and match.group(1) in settings:
        return settings[match.group(1)]
    return prefix


def full_prefixes(
    key: RouterKey, parents: dict[RouterKey, list[Mount]], settings: dict[str, str]
) -> list[str]:
    """Every prefix chain from the top of the app down to `key`."""
    results: list[str] = []

    def climb(current: RouterKey, suffix: str, seen: frozenset[RouterKey]) -> None:
        mounts = parents.get(current, [])
        if not mounts or current in seen:
            results.append(suffix)
            return
        for mount in mounts:
            prefix = _resolve_setting(mount.prefix, settings)
            climb(mount.parent, prefix.rstrip("/") + suffix, seen | {current})

    climb(key, "", frozenset())
    return list(dict.fromkeys(results))[:4]


def join_mounts(repo: Path, files: list[FileInfo], found: list[EntryPoint]) -> list[EntryPoint]:
    mounts, settings = find_mounts(repo, files)
    if not mounts:
        return found
    parents: dict[RouterKey, list[Mount]] = defaultdict(list)
    for mount in mounts:
        parents[mount.child].append(mount)
    result: list[EntryPoint] = []
    for entry in found:
        if entry.kind is not EntryKind.HTTP or entry.router is None:
            result.append(entry)
            continue
        verb, _, route = entry.name.partition(" ")
        for prefix in full_prefixes((entry.path, entry.router), parents, settings):
            result.append(replace(entry, name=f"{verb} {prefix}{route}"))
    return result
