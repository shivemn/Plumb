"""Read JavaScript and TypeScript imports and resolve them to files in the repo.

Covers `import ... from`, `export ... from`, side-effect imports, `require()`
and dynamic `import()`. Relative paths are resolved the way bundlers do
(extensions and index files are tried), and `paths` aliases from the
nearest tsconfig.json or jsconfig.json are followed. Package imports such
as "react" are dropped.
"""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass
from functools import cache
from pathlib import Path, PurePosixPath
from typing import cast

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from plumb.imports import Edge
from plumb.inventory import Category, FileInfo

_JS_LANGUAGES = ("javascript", "typescript")
_TRY_SUFFIXES = (".ts", ".tsx", ".d.ts", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".vue", ".svelte")


@dataclass(frozen=True)
class JsImport:
    specifier: str
    line: int


@cache
def _parser(kind: str) -> Parser:
    if kind == "tsx":
        return Parser(Language(tree_sitter_typescript.language_tsx()))
    if kind == "ts":
        return Parser(Language(tree_sitter_typescript.language_typescript()))
    return Parser(Language(tree_sitter_javascript.language()))


def _parser_for(path: str) -> Parser:
    suffix = PurePosixPath(path).suffix
    if suffix == ".tsx":
        return _parser("tsx")
    if suffix in (".ts", ".mts", ".cts"):
        return _parser("ts")
    # JSX is part of the JavaScript grammar.
    return _parser("js")


def _string_value(node: Node | None) -> str | None:
    if node is None or node.type not in ("string", "template_string"):
        return None
    parts = [c for c in node.named_children if c.type == "string_fragment"]
    if node.type == "template_string" and any(
        c.type == "template_substitution" for c in node.named_children
    ):
        return None  # built at run time, cannot be resolved
    return "".join(p.text.decode("utf-8", "replace") for p in parts if p.text)


def js_imports(path: str, source: bytes) -> list[JsImport]:
    tree = _parser_for(path).parse(source)
    found: list[JsImport] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in ("import_statement", "export_statement"):
            value = _string_value(node.child_by_field_name("source"))
            if value:
                found.append(JsImport(value, node.start_point.row + 1))
        elif node.type == "call_expression":
            function = node.child_by_field_name("function")
            arguments = node.child_by_field_name("arguments")
            is_require = (
                function is not None
                and function.type == "identifier"
                and function.text == b"require"
            )
            is_dynamic = function is not None and function.type == "import"
            if (is_require or is_dynamic) and arguments is not None and arguments.named_children:
                value = _string_value(arguments.named_children[0])
                if value:
                    found.append(JsImport(value, node.start_point.row + 1))
        stack.extend(reversed(node.children))
    return sorted(found, key=lambda i: i.line)


def strip_jsonc(text: str) -> str:
    """Remove comments and trailing commas, which tsconfig files allow."""
    out: list[str] = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
            out.append(ch)
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end == -1 else end
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        else:
            out.append(ch)
        i += 1
    cleaned = "".join(out)
    # Trailing commas before } or ]
    result: list[str] = []
    for index, ch in enumerate(cleaned):
        if ch == ",":
            rest = cleaned[index + 1 :].lstrip()
            if rest[:1] in ("}", "]"):
                continue
        result.append(ch)
    return "".join(result)


@dataclass(frozen=True)
class PathAliases:
    """`compilerOptions.paths` from one tsconfig, made relative to the repo root."""

    folder: str  # where the tsconfig lives
    aliases: tuple[tuple[str, tuple[str, ...]], ...]  # ("@/*", ("src/*",)), longest first


def read_aliases(repo: Path, config_paths: list[str]) -> list[PathAliases]:
    found: list[PathAliases] = []
    for config in config_paths:
        try:
            data: object = json.loads(strip_jsonc((repo / config).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
        options = _as_dict(_as_dict(data).get("compilerOptions"))
        paths = _as_dict(options.get("paths"))
        if not paths:
            continue
        folder = posixpath.dirname(config)
        base = posixpath.normpath(posixpath.join(folder, str(options.get("baseUrl", "."))))
        pairs: list[tuple[str, tuple[str, ...]]] = []
        for pattern, targets in paths.items():
            if isinstance(targets, list):
                items = cast("list[object]", targets)
                resolved = tuple(posixpath.normpath(posixpath.join(base, str(t))) for t in items)
                pairs.append((pattern, resolved))
        pairs.sort(key=lambda p: -len(p[0]))
        found.append(PathAliases(folder, tuple(pairs)))
    # Deepest folder first, so the nearest config wins.
    return sorted(found, key=lambda a: -len(a.folder))


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        typed = cast("dict[object, object]", value)
        return {str(k): v for k, v in typed.items()}
    return {}


class JsResolver:
    def __init__(self, tracked: set[str], aliases: list[PathAliases]) -> None:
        self.tracked = tracked
        self.aliases = aliases

    def resolve(self, importer: str, specifier: str) -> str | None:
        if specifier.startswith((".", "/")):
            base = posixpath.dirname(importer)
            return self._try(posixpath.normpath(posixpath.join(base, specifier)))
        for config in self.aliases:
            if config.folder and not importer.startswith(config.folder + "/"):
                continue
            for pattern, targets in config.aliases:
                for target in targets:
                    candidate = _apply_alias(pattern, target, specifier)
                    if candidate is not None:
                        hit = self._try(candidate)
                        if hit:
                            return hit
        return None

    def _try(self, base: str) -> str | None:
        base = base.removeprefix("./")
        if base in self.tracked and PurePosixPath(base).suffix in _TRY_SUFFIXES:
            return base
        # "./api.js" written for a file that is really api.ts (TypeScript ESM style)
        stem, dot, _ = base.rpartition(".")
        for candidate in (base, stem if dot else base):
            for suffix in _TRY_SUFFIXES:
                if f"{candidate}{suffix}" in self.tracked:
                    return f"{candidate}{suffix}"
        for suffix in _TRY_SUFFIXES:
            if f"{base}/index{suffix}" in self.tracked:
                return f"{base}/index{suffix}"
        return None


def _apply_alias(pattern: str, target: str, specifier: str) -> str | None:
    if "*" not in pattern:
        return target if specifier == pattern else None
    prefix, _, suffix = pattern.partition("*")
    if specifier.startswith(prefix) and specifier.endswith(suffix):
        middle = specifier[len(prefix) : len(specifier) - len(suffix) if suffix else None]
        return target.replace("*", middle, 1)
    return None


def js_edges(repo: Path, files: list[FileInfo]) -> list[Edge]:
    """Import edges between the repo's own JavaScript and TypeScript files."""
    usable = [f for f in files if f.category in (Category.SOURCE, Category.TEST)]
    tracked = {f.path for f in usable}
    configs = [
        f.path
        for f in files
        if PurePosixPath(f.path).name in ("tsconfig.json", "jsconfig.json")
        and f.category not in (Category.VENDORED, Category.GENERATED)
    ]
    resolver = JsResolver(tracked, read_aliases(repo, configs))
    edges: list[Edge] = []
    for info in usable:
        if info.language not in _JS_LANGUAGES:
            continue
        seen: set[str] = set()
        for item in js_imports(info.path, (repo / info.path).read_bytes()):
            target = resolver.resolve(info.path, item.specifier)
            if target and target != info.path and target not in seen:
                seen.add(target)
                edges.append(Edge(info.path, target, item.line))
    return edges
