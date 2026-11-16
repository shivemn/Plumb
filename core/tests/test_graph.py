from plumb.graph import component_edges, file_graph, most_used, mutual_components
from plumb.imports import Edge

EDGES = [
    Edge("api/routes.py", "core/routing.py", 3),
    Edge("api/routes.py", "store/db.py", 4),
    Edge("api/deps.py", "store/db.py", 1),
    Edge("core/routing.py", "store/db.py", 2),
    Edge("core/routing.py", "core/rates.py", 1),  # same component, not counted
    Edge("store/db.py", "core/rates.py", 9),  # store uses core, and core uses store
]


def test_component_edges() -> None:
    summary = {(c.source, c.target): c.count for c in component_edges(EDGES)}
    assert summary == {
        ("api", "store"): 2,
        ("api", "core"): 1,
        ("core", "store"): 1,
        ("store", "core"): 1,
    }


def test_mutual_components() -> None:
    ((forward, back),) = mutual_components(component_edges(EDGES))
    assert (forward.source, forward.target) == ("core", "store")
    assert (back.source, back.target) == ("store", "core")


def test_most_used() -> None:
    target, users = most_used(EDGES, limit=1)[0]
    assert target == "store/db.py"
    assert [e.source for e in users] == ["api/deps.py", "api/routes.py", "core/routing.py"]


def test_file_graph() -> None:
    graph = file_graph(EDGES)
    assert graph.in_degree("store/db.py") == 3
