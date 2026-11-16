from collections.abc import Callable

import pytest

from plumb.history import BULK_COMMIT_FILES, mine, read_commits
from tests.conftest import RepoBuilder


@pytest.fixture
def busy_repo(make_repo: Callable[[str], RepoBuilder]) -> RepoBuilder:
    repo = make_repo("busy")
    # Old work, outside a 90 day window.
    repo.commit({"old.py": "1\n"}, author="Ravi", days_ago=200)
    # routing.py and rates.py change together four times.
    for i in range(4):
        repo.commit(
            {"core/routing.py": f"{i}\n", "core/rates.py": f"{i}\n"},
            author=["Asha", "Ravi"][i % 2],
            days_ago=40 - i,
        )
    # routing.py also changes alone twice, by a third person.
    repo.commit({"core/routing.py": "a\n"}, author="Meera", days_ago=10)
    repo.commit({"core/routing.py": "b\n"}, author="Meera", days_ago=5)
    repo.commit({"README.md": "docs\n"}, days_ago=1)
    return repo


def test_read_commits_lists_files(busy_repo: RepoBuilder) -> None:
    commits = read_commits(busy_repo.path)
    assert len(commits) == 8
    assert commits[0].files == ("README.md",)  # newest first
    assert set(commits[-1].files) == {"old.py"}


def test_window_ends_at_newest_commit(busy_repo: RepoBuilder) -> None:
    history = mine(busy_repo.path, window_days=90)
    assert "old.py" not in history.files
    assert history.files["core/routing.py"].commits == 6
    assert history.files["core/routing.py"].authors == 3
    assert history.files["core/rates.py"].commits == 4


def test_hot_files_are_ranked(busy_repo: RepoBuilder) -> None:
    hot = [f.path for f in mine(busy_repo.path).hot_files(2)]
    assert hot == ["core/routing.py", "core/rates.py"]


def test_coupling(busy_repo: RepoBuilder) -> None:
    (coupling,) = mine(busy_repo.path).couplings
    assert (coupling.a, coupling.b) == ("core/rates.py", "core/routing.py")
    assert coupling.together == 4
    assert coupling.confidence == 1.0  # every change to rates.py also changed routing.py


def test_keep_limits_files(busy_repo: RepoBuilder) -> None:
    history = mine(busy_repo.path, keep={"core/routing.py"})
    assert set(history.files) == {"core/routing.py"}
    assert history.couplings == []


def test_bulk_commits_are_not_coupled(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("bulk")
    for i in range(3):
        repo.commit({f"f{n}.py": f"{i}\n" for n in range(BULK_COMMIT_FILES + 1)}, days_ago=3 - i)
    history = mine(repo.path)
    assert history.files["f0.py"].commits == 3
    assert history.couplings == []
