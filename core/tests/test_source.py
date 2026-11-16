from collections.abc import Callable
from pathlib import Path

import pytest

from plumb.source import Limits, SourceError, fetch, parse_github
from tests.conftest import RepoBuilder


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("https://github.com/shivemn/Plumb", ("shivemn", "Plumb")),
        ("https://github.com/shivemn/Plumb.git", ("shivemn", "Plumb")),
        ("https://github.com/psf/requests/", ("psf", "requests")),
        ("git@github.com:pallets/click.git", ("pallets", "click")),
        ("jhy/jsoup", ("jhy", "jsoup")),
        ("https://gitlab.com/a/b", None),
        ("https://github.com/a/b/tree/main", None),
        ("not a repo", None),
    ],
)
def test_parse_github(ref: str, expected: tuple[str, str] | None) -> None:
    assert parse_github(ref) == expected


def test_fetch_local_repo(make_repo: Callable[[str], RepoBuilder], tmp_path: Path) -> None:
    repo = make_repo("demo")
    head = repo.commit({"a.py": "x = 1\n"})
    checkout = fetch(str(repo.path), workdir=tmp_path / "work")
    assert checkout.commit == head
    assert checkout.owner == "local"
    assert checkout.name == "demo"


def test_fetch_reads_github_remote(make_repo: Callable[[str], RepoBuilder], tmp_path: Path) -> None:
    repo = make_repo("demo")
    repo.commit({"a.py": "x = 1\n"})
    repo.run("remote", "add", "origin", "https://github.com/sample-org/demo.git")
    checkout = fetch(str(repo.path), workdir=tmp_path / "work")
    assert (checkout.owner, checkout.name) == ("sample-org", "demo")


def test_fetch_rejects_too_many_files(
    make_repo: Callable[[str], RepoBuilder], tmp_path: Path
) -> None:
    repo = make_repo("big")
    repo.commit({f"f{i}.txt": "x" for i in range(5)})
    with pytest.raises(SourceError, match="more than 3 tracked files"):
        fetch(str(repo.path), workdir=tmp_path / "work", limits=Limits(max_files=3))


def test_fetch_rejects_too_many_bytes(
    make_repo: Callable[[str], RepoBuilder], tmp_path: Path
) -> None:
    repo = make_repo("heavy")
    repo.commit({"blob.txt": "x" * 4096})
    with pytest.raises(SourceError, match="add up to more than"):
        fetch(str(repo.path), workdir=tmp_path / "work", limits=Limits(max_bytes=1024))


def test_fetch_rejects_folder_without_git(tmp_path: Path) -> None:
    folder = tmp_path / "plain"
    folder.mkdir()
    with pytest.raises(SourceError, match="not a git repository"):
        fetch(str(folder), workdir=tmp_path / "work")


def test_fetch_rejects_other_hosts(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="not a local folder or a GitHub repo"):
        fetch("https://gitlab.com/a/b", workdir=tmp_path / "work")
