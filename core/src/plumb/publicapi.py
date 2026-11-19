"""Find what a library offers to the code that uses it.

For Python, the public names are what the package's `__init__.py` lists in
`__all__`, or, without one, what it imports or defines without a leading
underscore. Each name is followed to the file that defines it, so a report
can say "`Client` in httpx/_client.py" and quote the first line of its
docstring. Re-exported submodules count as names too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from tree_sitter import Node

from plumb.entrypoints import py_string, py_text, py_tree
from plumb.inventory import Category, FileInfo

_SKIP_DIRS = {"tests", "test", "docs", "examples", "example", "benchmarks", "scripts"}


class NameKind(StrEnum):
    CLASS = "class"
    EXCEPTION = "exception"
    FUNCTION = "function"
    MODULE = "module"
    VALUE = "value"
    INTERFACE = "interface"


@dataclass(frozen=True)
class PublicName:
    name: str
    kind: NameKind
    path: str  # where it is defined, or exported if the definition was not found
    line: int
    signature: str = ""  # parameter names for a function, such as "url, params, **kwargs"
    summary: str = ""  # first line of its docstring or doc comment
    exported_from: str = ""  # the file that makes it public, if not the defining file
    forms: int = 1  # overloads of a Java method with this name


@dataclass(frozen=True)
class PublicApi:
    package: str  # "httpx", "org.jsoup", "lodash"
    root: str  # the file that lists the public names
    names: list[PublicName]


@dataclass(frozen=True)
class _Definition:
    kind: NameKind
    line: int
    signature: str
    summary: str


def _docstring(body: Node | None) -> str:
    if body is None or not body.named_children:
        return ""
    first = body.named_children[0]
    if first.type != "expression_statement" or not first.named_children:
        return ""
    node = first.named_children[0]
    if node.type != "string":
        return ""
    text = "".join(py_text(c) for c in node.named_children if c.type == "string_content")
    return summary_line(text)


def summary_line(text: str, limit: int = 120) -> str:
    """The first sentence of a docstring or doc comment, shortened."""
    text = re.sub(r":\w+:`~?([^`<]+?)(?:\s*<[^>]+>)?`", r"\1", text)  # :class:`Request <Request>`
    text = text.replace("``", "`")
    text = re.sub(r"\{@(?:link|linkplain)\s+(?:[\w.]*#)?([^}\s]+)[^}]*\}", r"\1", text)  # Javadoc
    text = re.sub(r"\{@code\s+([^}]+)\}", r"`\1`", text)
    paragraph: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line.strip(" */")).strip()
        if line.startswith(("@", ":", "#", ">>>")):
            break
        if not line:
            if paragraph:
                break
            continue
        paragraph.append(line)
    joined = " ".join(paragraph)
    sentence = re.split(r"(?<=[.!?])\s", joined, maxsplit=1)[0]
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 3].rsplit(" ", 1)[0] + "..."


def _parameters(node: Node | None) -> str:
    names: list[str] = []
    for child in node.named_children if node is not None else []:
        text = py_text(child).split(":")[0].split("=")[0].strip()
        if text:
            names.append(text)
    if names and names[0] in ("self", "cls"):
        names = names[1:]
    return ", ".join(names)


def _bases(node: Node) -> set[str]:
    bases = node.child_by_field_name("superclasses")
    names = [py_text(c).rsplit(".", 1)[-1] for c in bases.named_children] if bases else []
    return set(names)


def _looks_like_exception(name: str) -> bool:
    return bool(re.search(r"(Error|Exception|Warning)$", name))


def python_definitions(source: bytes) -> dict[str, _Definition]:
    """Top-level classes, functions and assignments in a Python file."""
    found: dict[str, _Definition] = {}
    overloads: dict[str, _Definition] = {}
    bases: dict[str, set[str]] = {}
    for node in py_tree(source).root_node.named_children:
        target = node
        if node.type == "decorated_definition":
            target = node.child_by_field_name("definition") or node
        line = node.start_point.row + 1
        name = py_text(target.child_by_field_name("name"))
        if target.type == "class_definition" and name:
            bases[name] = _bases(target)
            body = target.child_by_field_name("body")
            found.setdefault(name, _Definition(NameKind.CLASS, line, "", _docstring(body)))
        elif target.type == "function_definition" and name and _is_overload(node):
            params = _parameters(target.child_by_field_name("parameters"))
            overloads.setdefault(name, _Definition(NameKind.FUNCTION, line, params, ""))
        elif target.type == "function_definition" and name:
            params = _parameters(target.child_by_field_name("parameters"))
            body = target.child_by_field_name("body")
            found.setdefault(name, _Definition(NameKind.FUNCTION, line, params, _docstring(body)))
        elif node.type == "expression_statement" and node.named_children:
            assignment = node.named_children[0]
            if assignment.type == "assignment":
                left = assignment.child_by_field_name("left")
                if left is not None and left.type == "identifier":
                    found.setdefault(py_text(left), _Definition(NameKind.VALUE, line, "", ""))
    for name, definition in overloads.items():
        found.setdefault(name, definition)
    # A class is an exception if a base is, following bases defined in the same file.
    exceptions = {n for n, b in bases.items() if any(_looks_like_exception(x) for x in b)}
    while grown := {n for n, b in bases.items() if b & exceptions} - exceptions:
        exceptions |= grown
    for name in exceptions:
        d = found[name]
        found[name] = _Definition(NameKind.EXCEPTION, d.line, d.signature, d.summary)
    return found


def _is_overload(node: Node) -> bool:
    if node.type != "decorated_definition":
        return False
    decorators = [py_text(c).lstrip("@") for c in node.named_children if c.type == "decorator"]
    return any(d.rsplit(".", 1)[-1] == "overload" for d in decorators)


@dataclass(frozen=True)
class _Export:
    name: str  # the public name
    original: str  # the name in the module it comes from
    module: str  # relative module, such as "._client", or "" for this file
    line: int


def _read_init(source: bytes) -> tuple[list[str] | None, list[_Export], list[tuple[str, int]]]:
    """__all__ (or None), names imported into the file, and star-imported modules."""
    root = py_tree(source).root_node
    listed: list[str] | None = None
    imports: list[_Export] = []
    stars: list[tuple[str, int]] = []
    for node in root.named_children:
        if node.type == "expression_statement" and node.named_children:
            assignment = node.named_children[0]
            left = assignment.child_by_field_name("left")
            right = assignment.child_by_field_name("right")
            if py_text(left) == "__all__" and right is not None:
                listed = [s for c in right.named_children if (s := py_string(c)) is not None]
        elif node.type == "import_from_statement":
            module = py_text(node.child_by_field_name("module_name"))
            line = node.start_point.row + 1
            if any(c.type == "wildcard_import" for c in node.named_children):
                stars.append((module, line))
                continue
            for child in node.children_by_field_name("name"):
                if child.type == "aliased_import":
                    original = py_text(child.child_by_field_name("name"))
                    public = py_text(child.child_by_field_name("alias"))
                else:
                    original = public = py_text(child)
                imports.append(_Export(public, original, module, line))
    return listed, imports, stars


def _module_file(package_dir: str, module: str, paths: set[str]) -> str | None:
    """The file for a relative module like "._client" or ".core" inside a package."""
    if not module.startswith("."):
        return None
    dots = len(module) - len(module.lstrip("."))
    base = PurePosixPath(package_dir)
    for _ in range(dots - 1):
        base = base.parent
    rest = module.lstrip(".").replace(".", "/")
    stem = f"{base}/{rest}" if rest else str(base)
    for candidate in (f"{stem}.py", f"{stem}/__init__.py"):
        if candidate in paths:
            return candidate
    return None


def find_python_packages(files: list[FileInfo], project: str | None = None) -> list[str]:
    """__init__.py files of the repo's top-level packages, the one named like the project first."""
    inits: list[str] = []
    for info in files:
        pure = PurePosixPath(info.path)
        if info.category is not Category.SOURCE or pure.name != "__init__.py":
            continue
        parts = pure.parts[:-1]
        if parts and parts[0] == "src":
            parts = parts[1:]
        if len(parts) == 1 and parts[0] not in _SKIP_DIRS:
            inits.append(info.path)
    wanted = (project or "").lower().replace("-", "_")
    return sorted(inits, key=lambda p: (PurePosixPath(p).parent.name.lower() != wanted, p))


def python_api(repo: Path, init: str, paths: set[str]) -> PublicApi:
    package_dir = str(PurePosixPath(init).parent)
    listed, imports, stars = _read_init((repo / init).read_bytes())
    local = python_definitions((repo / init).read_bytes())
    by_name = {e.name: e for e in imports}
    star_files = _star_files(repo, package_dir, stars, paths)
    star_defs = {f: python_definitions((repo / f).read_bytes()) for f in star_files}
    star_line = stars[0][1] if stars else 1

    if listed is not None:
        wanted = listed
    else:
        wanted = [e.name for e in imports if e.module.startswith(".")]
        wanted += list(local)
        # `from .x import *` without __all__ brings in x's public top-level names
        wanted += [name for defs in star_defs.values() for name in defs]
    wanted = [n for n in dict.fromkeys(wanted) if not n.startswith("_")]

    names: list[PublicName] = []
    for name in wanted:
        export = by_name.get(name)
        if export is not None and export.module.startswith("."):
            names.append(_follow(repo, init, package_dir, export, paths))
        elif name in local:
            d = local[name]
            names.append(PublicName(name, d.kind, init, d.line, d.signature, d.summary))
        else:
            hit = next(((f, defs[name]) for f, defs in star_defs.items() if name in defs), None)
            if hit is not None:
                f, d = hit
                names.append(PublicName(name, d.kind, f, d.line, d.signature, d.summary, init))
            else:
                names.append(PublicName(name, NameKind.VALUE, init, star_line))
    return PublicApi(PurePosixPath(package_dir).name, init, names)


def _star_files(
    repo: Path, package_dir: str, stars: list[tuple[str, int]], paths: set[str], depth: int = 3
) -> list[str]:
    """Files star-imported into a package, following `from .x import *` chains."""
    found: list[str] = []
    for module, _ in stars:
        target = _module_file(package_dir, module, paths)
        if target is None or target in found:
            continue
        found.append(target)
        if depth > 1:
            _, _, inner = _read_init((repo / target).read_bytes())
            base = str(PurePosixPath(target).parent)
            if not target.endswith("__init__.py"):
                base = package_dir
            found += [f for f in _star_files(repo, base, inner, paths, depth - 1) if f not in found]
    return found


def _follow(
    repo: Path, init: str, package_dir: str, export: _Export, paths: set[str]
) -> PublicName:
    target = _module_file(package_dir, export.module, paths)
    if target is None:
        return PublicName(export.name, NameKind.VALUE, init, export.line)
    joined = export.module + ("" if export.module.endswith(".") else ".") + export.original
    submodule = _module_file(package_dir, joined, paths)
    if export.module.strip(".") == "" or submodule is not None:
        # from . import utils: the name is a module
        module_path = submodule or target
        return PublicName(export.name, NameKind.MODULE, module_path, 1, exported_from=init)
    definition = python_definitions((repo / target).read_bytes()).get(export.original)
    if definition is None:
        return PublicName(export.name, NameKind.VALUE, init, export.line)
    return PublicName(
        export.name,
        definition.kind,
        target,
        definition.line,
        definition.signature,
        definition.summary,
        init,
    )


def find_python_api(
    repo: Path, files: list[FileInfo], project: str | None = None
) -> PublicApi | None:
    """The public API of the repo's main Python package, or None if there is none."""
    paths = {f.path for f in files}
    packages = find_python_packages(files, project)
    if packages:
        return python_api(repo, packages[0], paths)
    return None
