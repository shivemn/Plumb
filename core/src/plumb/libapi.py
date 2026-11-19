"""Public APIs of Java and JavaScript/TypeScript libraries, and the choice of finder.

Java: public top-level types outside packages named internal, impl or
examples, shallowest package first, then the ones the rest of the code uses
most. The public static methods of the types in the root package are listed
too, since that is where libraries put their front door (`Jsoup.parse`).

JavaScript and TypeScript: the exports of the file package.json points at
(`exports`, `types`, `module` or `main`), mapped back from a build folder to
its source, with `export ... from` and `export *` followed into other files.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import replace
from functools import cache
from pathlib import Path, PurePosixPath
from typing import cast

import tree_sitter_java
from tree_sitter import Language, Node, Parser

from plumb.entrypoints import py_text as text_of
from plumb.imports import Edge
from plumb.inventory import Category, FileInfo
from plumb.jsimports import js_parser_for
from plumb.publicapi import (
    NameKind,
    PublicApi,
    PublicName,
    find_python_api,
    summary_line,
)

_HIDDEN_PACKAGES = {"internal", "impl", "examples", "example", "test", "tests"}
_JAVA_TYPES = {
    "class_declaration": NameKind.CLASS,
    "record_declaration": NameKind.CLASS,
    "enum_declaration": NameKind.CLASS,
    "interface_declaration": NameKind.INTERFACE,
    "annotation_type_declaration": NameKind.INTERFACE,
}
_JS_SUFFIXES = (".ts", ".tsx", ".mts", ".js", ".mjs", ".cjs", ".jsx")


@cache
def _java_parser() -> Parser:
    return Parser(Language(tree_sitter_java.language()))


def _doc_before(node: Node) -> str:
    previous = node.prev_named_sibling
    if previous is not None and previous.type in ("block_comment", "comment"):
        comment = text_of(previous)
        if comment.startswith("/**"):
            return summary_line(comment.removeprefix("/**").removesuffix("*/"))
    return ""


def _modifiers(node: Node) -> str:
    found = next((c for c in node.named_children if c.type == "modifiers"), None)
    return text_of(found)


def _java_params(method: Node) -> str:
    params = method.child_by_field_name("parameters")
    names = [
        text_of(p.child_by_field_name("name"))
        for p in (params.named_children if params else [])
        if p.type in ("formal_parameter", "spread_parameter")
    ]
    return ", ".join(n for n in names if n)


def _java_types(path: str, source: bytes, with_methods: bool) -> list[PublicName]:
    root = _java_parser().parse(source).root_node
    found: list[PublicName] = []
    for node in root.named_children:
        kind = _JAVA_TYPES.get(node.type)
        if kind is None or not re.search(r"\bpublic\b", _modifiers(node)):
            continue
        name = text_of(node.child_by_field_name("name"))
        superclass = text_of(node.child_by_field_name("superclass"))
        if re.search(r"(Exception|Error)\b", f"{name} {superclass}"):
            kind = NameKind.EXCEPTION
        line = node.start_point.row + 1
        found.append(PublicName(name, kind, path, line, summary=_doc_before(node)))
        body = node.child_by_field_name("body")
        if not with_methods or body is None or kind is NameKind.EXCEPTION:
            continue
        for member in body.named_children:
            modifiers = _modifiers(member)
            if member.type != "method_declaration" or not re.search(r"\bpublic\b", modifiers):
                continue
            if "static" not in modifiers.split():
                continue
            method = f"{name}.{text_of(member.child_by_field_name('name'))}"
            earlier = next((i for i, n in enumerate(found) if n.name == method), None)
            if earlier is not None:  # an overload: count it on the first form
                found[earlier] = replace(found[earlier], forms=found[earlier].forms + 1)
                continue
            found.append(
                PublicName(
                    method,
                    NameKind.FUNCTION,
                    path,
                    member.start_point.row + 1,
                    _java_params(member),
                    _doc_before(member),
                )
            )
    return found


def _java_package(path: str) -> tuple[str, ...]:
    parts = PurePosixPath(path).parts
    if "java" in parts:
        parts = parts[parts.index("java") + 1 :]
    return tuple(parts[:-1])


def java_api(repo: Path, files: list[FileInfo], edges: list[Edge]) -> PublicApi | None:
    java = [
        f.path
        for f in files
        if f.category is Category.SOURCE
        and f.language == "java"
        and not f.path.endswith(("package-info.java", "module-info.java"))
        and not _HIDDEN_PACKAGES & set(_java_package(f.path))
    ]
    if not java:
        return None
    packages = {_java_package(p) for p in java}
    root_package = min(packages, key=len)
    used = Counter(e.target for e in edges)
    ranked = sorted(java, key=lambda p: (len(_java_package(p)), -used[p], p))
    names: list[PublicName] = []
    for path in ranked:
        in_root = _java_package(path) == root_package
        names += _java_types(path, (repo / path).read_bytes(), with_methods=in_root)
    build = next(
        (f.path for f in files if f.path in ("pom.xml", "build.gradle", "build.gradle.kts")),
        ranked[0],
    )
    return PublicApi(".".join(root_package), build, names)


# JavaScript and TypeScript


def _package_entry(manifest: dict[str, object]) -> list[str]:
    """Files package.json points at, most specific first."""
    found: list[str] = []
    exports = manifest.get("exports")
    if isinstance(exports, dict):
        table = cast("dict[str, object]", exports)
        exports = table.get(".", table)
    if isinstance(exports, str):
        found.append(exports)
    elif isinstance(exports, dict):
        for key in ("types", "import", "require", "default"):
            value = cast("dict[str, object]", exports).get(key)
            if isinstance(value, str):
                found.append(value)
    for key in ("types", "typings", "module", "main", "source"):
        value = manifest.get(key)
        if isinstance(value, str):
            found.append(value)
    return found


def _source_for(entry: str, paths: set[str]) -> str | None:
    """Map a built file such as dist/index.js back to src/index.ts, if it exists."""
    entry = entry.removeprefix("./")
    stem = re.sub(r"(\.d)?\.(m|c)?[jt]sx?$", "", entry)
    stems = [stem]
    first, _, rest = stem.partition("/")
    if first in ("dist", "lib", "build", "out", "esm", "cjs") and rest:
        stems += [f"src/{rest}", rest]
    for candidate_stem in stems:
        for suffix in _JS_SUFFIXES:
            if f"{candidate_stem}{suffix}" in paths:
                return f"{candidate_stem}{suffix}"
            if f"{candidate_stem}/index{suffix}" in paths:
                return f"{candidate_stem}/index{suffix}"
    return None


def _resolve_js(importer: str, spec: str, paths: set[str]) -> str | None:
    if not spec.startswith("."):
        return None
    base = PurePosixPath(importer).parent
    joined = str(PurePosixPath(base, spec))
    parts: list[str] = []
    for part in joined.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return _source_for("/".join(parts), paths)


def _js_string(node: Node | None) -> str:
    return text_of(node).strip("'\"`") if node is not None else ""


def _declared_name(declaration: Node) -> tuple[str, NameKind, str]:
    """Name, kind and parameter names of an exported declaration."""
    kind_of = {
        "function_declaration": NameKind.FUNCTION,
        "generator_function_declaration": NameKind.FUNCTION,
        "class_declaration": NameKind.CLASS,
        "abstract_class_declaration": NameKind.CLASS,
        "interface_declaration": NameKind.INTERFACE,
        "type_alias_declaration": NameKind.INTERFACE,
        "enum_declaration": NameKind.CLASS,
    }
    if declaration.type in kind_of:
        name = text_of(declaration.child_by_field_name("name"))
        params = _js_params(declaration.child_by_field_name("parameters"))
        kind = kind_of[declaration.type]
        if kind is NameKind.CLASS and re.search(r"(Error|Exception)$", name):
            kind = NameKind.EXCEPTION
        return name, kind, params
    if declaration.type in ("lexical_declaration", "variable_declaration"):
        declarator = next(
            (c for c in declaration.named_children if c.type == "variable_declarator"), None
        )
        if declarator is not None:
            value = declarator.child_by_field_name("value")
            if value is not None and value.type in ("arrow_function", "function_expression"):
                params = _js_params(value.child_by_field_name("parameters"))
                return text_of(declarator.child_by_field_name("name")), NameKind.FUNCTION, params
            return text_of(declarator.child_by_field_name("name")), NameKind.VALUE, ""
    return "", NameKind.VALUE, ""


def _js_params(node: Node | None) -> str:
    names: list[str] = []
    for child in node.named_children if node is not None else []:
        pattern = child.child_by_field_name("pattern") or child
        text = text_of(pattern).split(":")[0].split("=")[0].strip().rstrip("?")
        if text and not text.startswith(("{", "[")):
            names.append(text)
        elif text:
            names.append("options")
    return ", ".join(names)


def js_exports(
    repo: Path, path: str, paths: set[str], depth: int = 3, seen: frozenset[str] = frozenset()
) -> list[PublicName]:
    if path in seen or depth == 0:
        return []
    source = (repo / path).read_bytes()
    root = js_parser_for(path).parse(source).root_node
    local: dict[str, tuple[NameKind, int, str, str]] = {}
    for node in root.named_children:
        target = (
            node.child_by_field_name("declaration") if node.type == "export_statement" else node
        )
        if target is None:
            continue
        name, kind, params = _declared_name(target)
        if name:
            local[name] = (kind, node.start_point.row + 1, params, _doc_before(node))
    found: list[PublicName] = []
    for node in root.named_children:
        if node.type != "export_statement":
            continue
        line = node.start_point.row + 1
        spec = _js_string(node.child_by_field_name("source"))
        declaration = node.child_by_field_name("declaration")
        clause = next((c for c in node.named_children if c.type == "export_clause"), None)
        if declaration is not None:
            name, kind, params = _declared_name(declaration)
            if name:
                found.append(PublicName(name, kind, path, line, params, _doc_before(node)))
        elif spec and clause is None:  # export * from "./x"
            target = _resolve_js(path, spec, paths)
            if target:
                found += js_exports(repo, target, paths, depth - 1, seen | {path})
        elif clause is not None:
            target = _resolve_js(path, spec, paths) if spec else None
            followed = js_exports(repo, target, paths, depth - 1, seen | {path}) if target else []
            inner = {n.name: n for n in followed}
            for item in clause.named_children:
                original = text_of(item.child_by_field_name("name"))
                public = text_of(item.child_by_field_name("alias")) or original
                if target and original in inner:
                    hit = inner[original]
                    found.append(
                        PublicName(
                            public, hit.kind, hit.path, hit.line, hit.signature, hit.summary, path
                        )
                    )
                elif original in local:
                    kind, at, params, doc = local[original]
                    found.append(PublicName(public, kind, path, at, params, doc))
                else:
                    found.append(PublicName(public, NameKind.VALUE, path, line))
        elif any(c.type == "default" for c in node.children):
            found.append(PublicName("default", NameKind.VALUE, path, line))
    return list({n.name: n for n in found}.values())


def js_api(repo: Path, files: list[FileInfo]) -> PublicApi | None:
    manifest_path = repo / "package.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = cast("dict[str, object]", json.loads(manifest_path.read_text("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    paths = {f.path for f in files if f.category is Category.SOURCE}
    entries = _package_entry(manifest) + ["src/index", "index"]
    entry = next((s for e in entries if (s := _source_for(e, paths))), None)
    if entry is None:
        return None
    name = str(manifest.get("name") or PurePosixPath(entry).parent.name or repo.name)
    return PublicApi(name, entry, js_exports(repo, entry, paths))


def find_public_api(
    repo: Path, files: list[FileInfo], edges: list[Edge], project: str | None = None
) -> PublicApi | None:
    """The public API in the repo's main language, or None if none is found."""
    lines: Counter[str] = Counter()
    for info in files:
        if info.category is Category.SOURCE and info.language:
            language = "javascript" if info.language == "typescript" else info.language
            lines[language] += info.lines
    finders = {
        "python": lambda: find_python_api(repo, files, project),
        "java": lambda: java_api(repo, files, edges),
        "javascript": lambda: js_api(repo, files),
    }
    for language, _ in lines.most_common():
        finder = finders.get(language)
        if finder is not None:
            api = finder()
            if api is not None and api.names:
                return api
    return None
