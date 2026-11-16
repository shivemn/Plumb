"""Build the dependency graph between files and group files into components.

A component is a folder of source files. Edges between components are the
sum of the import edges between their files.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import networkx as nx

from plumb.imports import Edge, java_edges, python_edges
from plumb.inventory import FileInfo


@dataclass(frozen=True)
class ComponentEdge:
    source: str
    target: str
    count: int
    examples: tuple[Edge, ...]  # at most 3, for evidence


def all_edges(repo: Path, files: list[FileInfo]) -> list[Edge]:
    return [*python_edges(repo, files), *java_edges(repo, files)]


def file_graph(edges: list[Edge]) -> nx.DiGraph[str]:
    graph: nx.DiGraph[str] = nx.DiGraph()
    for edge in edges:
        graph.add_edge(edge.source, edge.target)
    return graph


def component_of(path: str) -> str:
    parent = PurePosixPath(path).parent
    return "." if str(parent) == "." else str(parent)


def component_edges(edges: list[Edge]) -> list[ComponentEdge]:
    grouped: defaultdict[tuple[str, str], list[Edge]] = defaultdict(list)
    for edge in edges:
        key = (component_of(edge.source), component_of(edge.target))
        if key[0] != key[1]:
            grouped[key].append(edge)
    result = [
        ComponentEdge(source, target, len(found), tuple(sorted(found, key=_edge_order)[:3]))
        for (source, target), found in grouped.items()
    ]
    return sorted(result, key=lambda c: (-c.count, c.source, c.target))


def mutual_components(component: list[ComponentEdge]) -> list[tuple[ComponentEdge, ComponentEdge]]:
    """Pairs of components that each use the other."""
    by_key = {(c.source, c.target): c for c in component}
    pairs: list[tuple[ComponentEdge, ComponentEdge]] = []
    for (source, target), edge in sorted(by_key.items()):
        back = by_key.get((target, source))
        if back is not None and source < target:
            pairs.append((edge, back))
    return pairs


def most_used(edges: list[Edge], limit: int = 5) -> list[tuple[str, list[Edge]]]:
    """Files used by the most other files, with the edges that use them."""
    users: defaultdict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        users[edge.target].append(edge)
    counts = Counter({target: len({e.source for e in found}) for target, found in users.items()})
    return [
        (target, sorted(users[target], key=_edge_order))
        for target, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _edge_order(edge: Edge) -> tuple[str, int]:
    return (edge.source, edge.line)
