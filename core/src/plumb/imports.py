"""Read import statements with tree-sitter and resolve them to files in the repo.

Only imports that point at the repo's own code become edges. Standard
library and third-party imports are dropped, since they say nothing about
how the repo itself is put together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path, PurePosixPath

import tree_sitter_java
import tree_sitter_python
from tree_sitter import Language, Node, Parser

from plumb.inventory import Category, FileInfo


@dataclass(frozen=True)
class Import:
    """One import statement, as written."""

    module: str  # dotted name; for relative imports, without the leading dots
    names: tuple[str, ...]  # names after "from x import", empty for "import x"
    level: int  # number of leading dots in a relative import
    line: int  # 1-based
    # The local name each of `names` is bound to ("x as y" binds y).
    local_names: tuple[str, ...] = field(default=(), compare=False)


@dataclass(frozen=True)
class Edge:
    """A resolved import: `source` file uses `target` file."""

    source: str
    target: str
    line: int


@cache
def _python_parser() -> Parser:
    return Parser(Language(tree_sitter_python.language()))


@cache
def _java_parser() -> Parser:
    return Parser(Language(tree_sitter_java.language()))


def _text(node: Node | None) -> str:
    return node.text.decode("utf-8", "replace") if node is not None and node.text else ""


def _unalias(node: Node) -> Node | None:
    """The real name in "x as y", or the node itself when there is no alias."""
    return node.child_by_field_name("name") if node.type == "aliased_import" else node


def python_imports(source: bytes) -> list[Import]:
    """All import statements in a Python file, including ones inside functions."""
    tree = _python_parser().parse(source)
    found: list[Import] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "import_statement":
            for child in node.named_children:
                target = (
                    child.child_by_field_name("name") if child.type == "aliased_import" else child
                )
                if target is not None and target.type == "dotted_name":
                    found.append(Import(_text(target), (), 0, node.start_point.row + 1))
        elif node.type == "import_from_statement":
            found.append(_from_import(node))
        else:
            stack.extend(reversed(node.children))
    return sorted(found, key=lambda i: i.line)


def _from_import(node: Node) -> Import:
    module_node = node.child_by_field_name("module_name")
    level = 0
    module = ""
    if module_node is not None and module_node.type == "relative_import":
        for child in module_node.children:
            if child.type == "import_prefix":
                level = len(_text(child))
            elif child.type == "dotted_name":
                module = _text(child)
    else:
        module = _text(module_node)
    names: list[str] = []
    local: list[str] = []
    for child in node.children_by_field_name("name"):
        names.append(_text(_unalias(child)))
        alias = child.child_by_field_name("alias") if child.type == "aliased_import" else None
        local.append(_text(alias) if alias is not None else names[-1])
    return Import(module, tuple(names), level, node.start_point.row + 1, tuple(local))


class PythonIndex:
    """Maps dotted module names to the repo's Python files."""

    def __init__(self, paths: list[str]) -> None:
        all_paths = set(paths)
        self.module_of: dict[str, str] = {}
        self.file_of: dict[str, str] = {}
        for path in paths:
            name = _module_name(path, all_paths)
            self.module_of[path] = name
            # The first file found wins if two roots give the same name.
            self.file_of.setdefault(name, path)

    def absolute(self, importer: str, item: Import) -> str | None:
        """The dotted module an import names, with relative imports made absolute."""
        if not item.level:
            return item.module
        package = self.module_of[importer].split(".")
        if not importer.endswith("__init__.py"):
            package = package[:-1]
        if item.level - 1 > len(package):
            return None
        base = package[: len(package) - (item.level - 1)]
        return ".".join([*base, *([item.module] if item.module else [])])

    def resolve(self, importer: str, item: Import) -> list[str]:
        """Repo files that one import statement refers to."""
        module = self.absolute(importer, item)
        if module is None:
            return []

        targets: list[str] = []
        if item.names:
            for name in item.names:
                hit = self.file_of.get(f"{module}.{name}" if module else name)
                if hit:
                    targets.append(hit)
        if not targets:
            hit = self._longest_prefix(module)
            if hit:
                targets.append(hit)
        return [t for t in dict.fromkeys(targets) if t != importer]

    def _longest_prefix(self, module: str) -> str | None:
        parts = module.split(".")
        for end in range(len(parts), 0, -1):
            hit = self.file_of.get(".".join(parts[:end]))
            if hit:
                return hit
        return None


def _module_name(path: str, all_paths: set[str]) -> str:
    """Dotted name of a file, counted from the first folder that is not a package."""
    pure = PurePosixPath(path)
    parts = [*pure.parent.parts]
    name_parts = [] if pure.name == "__init__.py" else [pure.stem]
    while parts and "/".join([*parts, "__init__.py"]) in all_paths:
        name_parts.insert(0, parts.pop())
    return ".".join(name_parts)


def python_edges(repo: Path, files: list[FileInfo]) -> list[Edge]:
    """Import edges between the repo's own Python files."""
    paths = [
        f.path
        for f in files
        if f.language == "python"
        and f.path.endswith(".py")
        and f.category in (Category.SOURCE, Category.TEST)
    ]
    index = PythonIndex(paths)
    edges: list[Edge] = []
    for path in paths:
        for item in python_imports((repo / path).read_bytes()):
            edges.extend(Edge(path, target, item.line) for target in index.resolve(path, item))
    return edges


_JAVA_NAMES = ("scoped_identifier", "identifier")


@dataclass(frozen=True)
class JavaFile:
    package: str
    imports: tuple[tuple[str, bool, bool, int], ...]  # (name, is_static, is_wildcard, line)
    type_names: dict[str, int]  # simple type names used, with the first line each appears on


def read_java(source: bytes) -> JavaFile:
    """Package, imports and the type names a Java file mentions."""
    tree = _java_parser().parse(source)
    package = ""
    imports: list[tuple[str, bool, bool, int]] = []
    type_names: dict[str, int] = {}
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "package_declaration":
            for child in node.named_children:
                if child.type in _JAVA_NAMES:
                    package = _text(child)
        elif node.type == "import_declaration":
            names = [
                c for c in node.named_children if c.type in ("scoped_identifier", "identifier")
            ]
            is_static = any(c.type == "static" for c in node.children)
            is_wildcard = any(c.type == "asterisk" for c in node.children)
            if names:
                imports.append((_text(names[0]), is_static, is_wildcard, node.start_point.row + 1))
        else:
            if node.type == "type_identifier":
                type_names.setdefault(_text(node), node.start_point.row + 1)
            stack.extend(reversed(node.children))
    return JavaFile(package, tuple(imports), type_names)


def java_edges(repo: Path, files: list[FileInfo]) -> list[Edge]:
    """Edges between the repo's own Java files: imports, plus types used from the same package."""
    paths = [
        f.path
        for f in files
        if f.language == "java" and f.category in (Category.SOURCE, Category.TEST)
    ]
    parsed = {path: read_java((repo / path).read_bytes()) for path in paths}
    by_class: dict[str, str] = {}
    by_package: dict[str, dict[str, str]] = {}
    for path, info in parsed.items():
        simple = PurePosixPath(path).stem
        qualified = f"{info.package}.{simple}" if info.package else simple
        by_class.setdefault(qualified, path)
        by_package.setdefault(info.package, {}).setdefault(simple, path)

    edges: list[Edge] = []
    for path, info in parsed.items():
        targets: dict[str, int] = {}
        for name, is_static, is_wildcard, line in info.imports:
            if is_wildcard and not is_static:
                for simple, target in by_package.get(name, {}).items():
                    if simple in info.type_names:
                        targets.setdefault(target, line)
                continue
            parts = name.split(".")
            for end in range(len(parts), 0, -1):
                hit = by_class.get(".".join(parts[:end]))
                if hit:
                    targets.setdefault(hit, line)
                    break
        for simple, target in by_package.get(info.package, {}).items():
            if simple in info.type_names:
                targets.setdefault(target, info.type_names[simple])
        edges.extend(Edge(path, t, line) for t, line in targets.items() if t != path)
    return edges
