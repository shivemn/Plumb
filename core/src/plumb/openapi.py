"""Read routes from OpenAPI (Swagger) files.

Some services define their API in an OpenAPI file and generate the route
code at build time, so the routes are not in the repo's source. The file is
then the only record of them. Routes that the code also defines are not
counted twice.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.parse import urlparse

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from plumb.entrypoints import EntryKind, EntryPoint
from plumb.inventory import Category, FileInfo

_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
_NAMES = ("openapi", "swagger", "api-spec", "api_spec")


def _items(node: Node | None) -> list[tuple[str, Node, int]]:
    if not isinstance(node, MappingNode):
        return []
    pairs = cast("list[tuple[Node, Node]]", node.value)
    return [(str(k.value), v, k.start_mark.line + 1) for k, v in pairs if isinstance(k, ScalarNode)]


def _get(node: Node | None, key: str) -> Node | None:
    return next((v for k, v, _ in _items(node) if k == key), None)


def openapi_routes(path: str, text: str) -> list[EntryPoint]:
    try:
        root = yaml.compose(text, Loader=yaml.SafeLoader)  # JSON is valid YAML
    except yaml.YAMLError:
        return []
    if _get(root, "openapi") is None and _get(root, "swagger") is None:
        return []
    base = ""
    servers = _get(root, "servers")
    if isinstance(servers, SequenceNode) and servers.value:
        url = _get(cast("list[Node]", servers.value)[0], "url")
        if isinstance(url, ScalarNode):
            base = urlparse(str(url.value)).path.rstrip("/")
    base_path = _get(root, "basePath")  # Swagger 2
    if isinstance(base_path, ScalarNode):
        base = str(base_path.value).rstrip("/")
    found: list[EntryPoint] = []
    for route, operations, _ in _items(_get(root, "paths")):
        for method, _, line in _items(operations):
            if method in _METHODS:
                name = f"{method.upper()} {base}{route}"
                found.append(EntryPoint(EntryKind.HTTP, name, path, line, "openapi"))
    return found


def _looks_like_spec(info: FileInfo) -> bool:
    pure = PurePosixPath(info.path)
    if info.category in (Category.VENDORED, Category.GENERATED, Category.EXAMPLE, Category.TEST):
        return False
    return pure.suffix in (".yml", ".yaml", ".json") and pure.stem.lower().startswith(_NAMES)


def find_openapi_routes(
    repo: Path, files: list[FileInfo], known: list[EntryPoint]
) -> list[EntryPoint]:
    """Spec routes that the code does not already define (same method and path)."""
    have: set[tuple[str, str]] = set()
    for entry in known:
        if entry.kind is EntryKind.HTTP:
            verbs, _, route = entry.name.partition(" ")
            for verb in verbs.split(","):
                have.add((verb, route.rstrip("/")))
    found: list[EntryPoint] = []
    for info in files:
        if not _looks_like_spec(info):
            continue
        text = (repo / info.path).read_text(encoding="utf-8", errors="replace")
        if info.path.endswith(".json"):
            try:
                json.loads(text)
            except ValueError:
                continue
        for entry in openapi_routes(info.path, text):
            verb, _, route = entry.name.partition(" ")
            if (verb, route.rstrip("/")) not in have and ("ANY", route.rstrip("/")) not in have:
                found.append(entry)
    return found
