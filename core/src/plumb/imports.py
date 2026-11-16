"""Read import statements with tree-sitter and resolve them to files in the repo.

Only imports that point at the repo's own code become edges. Standard
library and third-party imports are dropped, since they say nothing about
how the repo itself is put together.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path, PurePosixPath

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


@dataclass(frozen=True)
class Edge:
    """A resolved import: `source` file uses `target` file."""

    source: str
    target: str
    line: int


@cache
def _python_parser() -> Parser:
    return Parser(Language(tree_sitter_python.language()))


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
    for child in node.children_by_field_name("name"):
        names.append(_text(_unalias(child)))
    return Import(module, tuple(names), level, node.start_point.row + 1)


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

    def resolve(self, importer: str, item: Import) -> list[str]:
        """Repo files that one import statement refers to."""
        if item.level:
            package = self.module_of[importer].split(".")
            if not importer.endswith("__init__.py"):
                package = package[:-1]
            if item.level - 1 > len(package):
                return []
            base = package[: len(package) - (item.level - 1)]
            module = ".".join([*base, *([item.module] if item.module else [])])
        else:
            module = item.module

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
