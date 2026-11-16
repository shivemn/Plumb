import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from typer.testing import CliRunner

from plumb.cli import app
from plumb.facts import build_facts
from plumb.history import mine
from plumb.inventory import build_inventory
from plumb.model import FactSet, FileEvidence
from plumb.source import fetch
from tests.conftest import RepoBuilder


def sample_repo(make_repo: Callable[[str], RepoBuilder]) -> RepoBuilder:
    repo = make_repo("shop")
    repo.commit(
        {
            "Dockerfile": "FROM python:3.12\n",
            ".github/workflows/ci.yml": "on: push\n",
            "shop/api.py": "def get():\n    return 1\n",
            "shop/db.py": "x = 1\n",
            "node_modules/x/index.js": "1\n",
        },
        days_ago=20,
    )
    for i in range(3):
        repo.commit({"shop/api.py": f"# {i}\n", "shop/db.py": f"# {i}\n"}, days_ago=10 - i)
    return repo


def test_facts_cite_real_files(make_repo: Callable[[str], RepoBuilder], tmp_path: Path) -> None:
    repo = sample_repo(make_repo)
    checkout = fetch(str(repo.path), workdir=tmp_path)
    files = build_inventory(repo.path)
    facts = build_facts(checkout, files, mine(repo.path))

    tracked = {f.path for f in files}
    for fact in facts.facts:
        for evidence in fact.evidence:
            if isinstance(evidence, FileEvidence):
                assert evidence.path in tracked, fact.statement

    statements = [f.statement for f in facts.facts]
    assert "2 source files in python, 2 lines in all" in statements
    assert "1 vendored file left out of the analysis" in statements
    assert "Build or deploy file Dockerfile" in statements
    assert "GitHub Actions workflow .github/workflows/ci.yml" in statements
    assert any(s.startswith("shop/api.py changed in 4 commits by 1 author") for s in statements)
    assert any("changed in the same commit 4 times" in s for s in statements)
    assert [f.id for f in facts.facts] == [f"f{i}" for i in range(1, len(facts.facts) + 1)]


def test_analyse_command_writes_valid_json(
    make_repo: Callable[[str], RepoBuilder], tmp_path: Path
) -> None:
    repo = sample_repo(make_repo)
    out = tmp_path / "shop.facts.json"
    result = CliRunner().invoke(
        app, ["analyse", str(repo.path), "--out", str(out), "--workdir", str(tmp_path / "w")]
    )
    assert result.exit_code == 0, result.output
    assert "facts written to" in result.output
    facts = FactSet.model_validate(json.loads(out.read_text()))
    assert facts.repo.name == "shop"


def test_rarely_changed_files_are_not_hot_spots(
    make_repo: Callable[[str], RepoBuilder], tmp_path: Path
) -> None:
    repo = sample_repo(make_repo)
    repo.commit({"shop/once.py": "x = 1\n"})
    facts = build_facts(
        fetch(str(repo.path), tmp_path), build_inventory(repo.path), mine(repo.path)
    )
    assert not any(f.statement.startswith("shop/once.py") for f in facts.facts)


def test_shallow_clone_skips_history(
    make_repo: Callable[[str], RepoBuilder], tmp_path: Path
) -> None:
    repo = sample_repo(make_repo)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo.path}", str(shallow)], check=True
    )
    out = tmp_path / "s.json"
    args = ["analyse", str(shallow), "--out", str(out), "--workdir", str(tmp_path / "w")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "only part of its history" in result.output
    statements = [f["statement"] for f in json.loads(out.read_text())["facts"]]
    assert not any("changed in" in s for s in statements)


def test_analyse_reports_bad_input(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app, ["analyse", "https://gitlab.com/a/b", "--workdir", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "Could not analyse" in result.output
