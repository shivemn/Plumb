from collections.abc import Callable
from pathlib import Path

from plumb.pipeline import analyse_repo
from plumb.views import _grouping, _layers, build_views  # pyright: ignore[reportPrivateUsage]
from tests.conftest import RepoBuilder
from tests.test_facts import sample_repo


def test_views_from_a_sample_repo(make_repo: Callable[[str], RepoBuilder], tmp_path: Path) -> None:
    repo = sample_repo(make_repo)
    views = build_views(analyse_repo(str(repo.path), tmp_path))
    labels = [s.label for s in views.stats]
    assert labels[:2] == ["Commit", "Language"] and "Kind" in labels
    assert views.code_map is not None and views.code_map.shown_files > 0
    folder = views.code_map.rows[0][0]
    assert folder.blocks and folder.blocks[0].lines >= folder.blocks[-1].lines
    assert views.gaps[-1].title.startswith("Expected traffic")


def test_grouping_opens_long_single_paths_and_splits_big_folders() -> None:
    java = [
        f"src/main/java/org/app/{part}/A{n}.java" for part in ("owner", "vet") for n in range(3)
    ]
    group = _grouping(java)
    assert group(java[0]) == "src/main/java/org/app/owner"
    big = [f"web/src/components/C{n}.tsx" for n in range(30)] + ["web/src/main.tsx", "api/app.py"]
    group = _grouping(big)
    assert group("web/src/components/C1.tsx") == "web/src/components"
    assert group("web/src/main.tsx") == "web/src"
    assert group("tests/test_x.py") == ""  # not one of the grouped files


def test_layers_put_used_folders_lower() -> None:
    uses = {"api": {"core"}, "cli": {"core"}, "core": {"store"}}
    assert _layers(["api", "cli", "core", "store"], uses) == [["api", "cli"], ["core"], ["store"]]
    cycle = {"a": {"b"}, "b": {"a"}}
    assert _layers(["a", "b"], cycle) == [["a", "b"]]  # each uses the other: one row
