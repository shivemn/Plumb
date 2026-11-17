"""Join Express route prefixes added by `.use("/prefix", router)`, across files.

Each `.use(...)` call has an owner: the variable it is called on, or for a
chain such as `const api = Router().use(a).use(b)` the variable the chain
is stored in (`export default Router().use(...)` is owned by the file's
default export). A route's full path is the prefixes of every owner on the
way up, following a file's default export into the files that mount it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from tree_sitter import Node

from plumb.entrypoints import EntryPoint, walk
from plumb.inventory import Category, FileInfo
from plumb.jsimports import JsResolver, js_parser_for, read_aliases

DEFAULT = "<default>"


@dataclass
class FileMounts:
    exported: str | None = None  # owner that is the file's default export
    # local owner -> list of (parent owner, prefix)
    local: dict[str, list[tuple[str, str]]] | None = None
    # imported file -> list of (owner in this file, prefix)
    children: dict[str, list[tuple[str, str]]] | None = None


def _text(node: Node | None) -> str:
    return node.text.decode("utf-8", "replace") if node is not None and node.text else ""


def _string(node: Node | None) -> str | None:
    if node is None or node.type != "string":
        return None
    return "".join(_text(c) for c in node.named_children if c.type == "string_fragment")


def _owner(call: Node) -> str:
    """Who a `.use()` call belongs to."""
    function = call.child_by_field_name("function")
    target = function.child_by_field_name("object") if function is not None else None
    while target is not None and target.type == "call_expression":
        inner = target.child_by_field_name("function")
        if inner is None or inner.type != "member_expression":
            break  # reached Router() or express()
        target = inner.child_by_field_name("object")
    if target is not None and target.type == "identifier":
        return _text(target)
    # A chain started from Router(): owned by whatever it is assigned to.
    parent = call.parent
    while parent is not None:
        if parent.type == "variable_declarator":
            return _text(parent.child_by_field_name("name"))
        if parent.type == "export_statement":
            return DEFAULT
        if parent.type in ("statement_block", "program"):
            break
        parent = parent.parent
    return "<anonymous>"


def _imports(path: str, root: Node, resolver: JsResolver) -> dict[str, str]:
    """Local names bound to another repo file: default imports and require()."""
    names: dict[str, str] = {}
    for node in walk(root):
        if node.type == "import_statement":
            target = resolver.resolve(path, _string(node.child_by_field_name("source")) or "")
            clause = next((c for c in node.named_children if c.type == "import_clause"), None)
            default = (
                next((c for c in clause.named_children if c.type == "identifier"), None)
                if clause is not None
                else None
            )
            if target and default is not None:
                names[_text(default)] = target
        elif node.type == "variable_declarator":
            value = node.child_by_field_name("value")
            if value is not None and value.type == "call_expression":
                function = value.child_by_field_name("function")
                arguments = value.child_by_field_name("arguments")
                if _text(function) == "require" and arguments and arguments.named_children:
                    target = resolver.resolve(path, _string(arguments.named_children[0]) or "")
                    if target:
                        names[_text(node.child_by_field_name("name"))] = target
    return names


def read_file_mounts(path: str, source: bytes, resolver: JsResolver) -> FileMounts:
    root = js_parser_for(path).parse(source).root_node
    names = _imports(path, root, resolver)
    mounts = FileMounts(local=defaultdict(list), children=defaultdict(list))
    assert mounts.local is not None and mounts.children is not None
    for node in walk(root):
        if node.type == "export_statement":
            value = node.child_by_field_name("value") or node.child_by_field_name("declaration")
            if value is not None and value.type == "identifier":
                mounts.exported = _text(value)
            elif value is not None and value.type == "call_expression":
                mounts.exported = DEFAULT
        if node.type != "call_expression":
            continue
        function = node.child_by_field_name("function")
        if function is None or function.type != "member_expression":
            continue
        if _text(function.child_by_field_name("property")) != "use":
            continue
        arguments = node.child_by_field_name("arguments")
        items = list(arguments.named_children) if arguments is not None else []
        prefix = _string(items[0]) if items else None
        if prefix is not None:
            items = items[1:]
        owner = _owner(node)
        for item in items:
            if item.type != "identifier":
                continue
            name = _text(item)
            if name in names:
                mounts.children[names[name]].append((owner, prefix or ""))
            else:
                mounts.local[name].append((owner, prefix or ""))
    return mounts


def join_express_mounts(
    repo: Path, files: list[FileInfo], found: list[EntryPoint]
) -> list[EntryPoint]:
    """Add mount prefixes to Express routes; other entry points pass through."""
    usable = [f for f in files if f.category in (Category.SOURCE, Category.TEST)]
    configs = [
        f.path for f in files if PurePosixPath(f.path).name in ("tsconfig.json", "jsconfig.json")
    ]
    resolver = JsResolver({f.path for f in usable}, read_aliases(repo, configs))
    by_file = {
        f.path: read_file_mounts(f.path, (repo / f.path).read_bytes(), resolver)
        for f in usable
        if f.category is Category.SOURCE and f.language in ("javascript", "typescript")
    }
    # child file -> (parent file, owner in the parent, prefix)
    parents: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for path, mounts in by_file.items():
        for child, places in (mounts.children or {}).items():
            for owner, prefix in places:
                parents[child].append((path, owner, prefix))

    def in_file(path: str, owner: str, seen: frozenset[tuple[str, str]]) -> list[str]:
        if (path, owner) in seen:
            return [""]
        seen = seen | {(path, owner)}
        mounts = by_file.get(path)
        ups = (mounts.local or {}).get(owner, []) if mounts else []
        results: list[str] = []
        for parent, prefix in ups:
            results += [p + prefix.rstrip("/") for p in in_file(path, parent, seen)]
        if not ups:
            if mounts is not None and mounts.exported == owner and parents.get(path):
                for parent_file, parent_owner, prefix in parents[path]:
                    results += [
                        p + prefix.rstrip("/") for p in in_file(parent_file, parent_owner, seen)
                    ]
            else:
                results.append("")
        return list(dict.fromkeys(results))[:4]

    result: list[EntryPoint] = []
    for entry in found:
        if entry.framework != "express" or entry.router is None or entry.path not in by_file:
            result.append(entry)
            continue
        verb, _, route = entry.name.partition(" ")
        for prefix in in_file(entry.path, entry.router, frozenset()):
            result.append(replace(entry, name=f"{verb} {prefix}{route}"))
    return result
