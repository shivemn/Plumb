from collections.abc import Callable

from plumb.contrib import find_steps, guide_steps, makefile_steps, workflow_steps
from plumb.facts import FactBuilder, add_step_facts
from plumb.inventory import build_inventory
from tests.conftest import RepoBuilder

MAKEFILE = """\
.PHONY: test
init:
\tpython -m pip install -r requirements-dev.txt
test:
\t@python -m pytest tests
VAR := 1
publish:
\ttwine upload dist/*
"""

WORKFLOW = """\
name: CI
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install
        run: pip install -e .[dev]
      - name: Test
        run: |
          echo starting
          pytest -q
"""


def test_makefile_steps() -> None:
    found = [(s.name, s.command, s.line) for s in makefile_steps("Makefile", MAKEFILE)]
    assert found == [
        ("init", "python -m pip install -r requirements-dev.txt", 2),
        ("test", "python -m pytest tests", 4),
    ]


def test_workflow_steps() -> None:
    found = [(s.name, s.command, s.line) for s in workflow_steps("ci.yml", WORKFLOW)]
    assert found == [("Install", "pip install -e .[dev]", 9), ("Test", "pytest -q", 13)]


def test_guide_steps() -> None:
    text = "# Contributing\n\n## Setup\nx\n## Running tests\n"
    assert [(s.name, s.line) for s in guide_steps("CONTRIBUTING.md", text)] == [
        ("Setup", 3),
        ("Running tests", 5),
    ]


def test_find_steps(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("shop")
    repo.commit(
        {
            "Makefile": MAKEFILE,
            ".github/workflows/ci.yml": WORKFLOW,
            "CONTRIBUTING.md": "## Setup\n",
            "examples/Makefile": "test:\n\tnope\n",
        }
    )
    kinds = sorted({s.kind for s in find_steps(repo.path, build_inventory(repo.path))})
    assert kinds == ["ci", "guide", "make"]
    assert all(
        not s.path.startswith("examples") for s in find_steps(repo.path, build_inventory(repo.path))
    )


DOWNSTREAM = """
jobs:
  race-tests:
    name: ${{ matrix.config.name }}
    steps:
      - uses: actions/checkout@v4
      - run: tox run
  flask-tests:
    name: Flask
    steps:
      - uses: actions/checkout@v4
        with:
          repository: pallets/flask
      - run: pytest
"""


def test_workflow_steps_know_their_job_and_other_repositories() -> None:
    own, flask = workflow_steps("nightly.yaml", DOWNSTREAM)
    assert (own.job, own.other_repo) == ("race-tests", "")  # a templated name falls back to the key
    assert (flask.job, flask.other_repo) == ("Flask", "pallets/flask")
    builder = FactBuilder()
    add_step_facts(builder, [flask, own])
    statements = [f.statement for f in builder.facts]
    assert statements[0] == "A CI step in job race-tests of nightly.yaml runs: tox run"
    assert statements[1].startswith("A CI step in job Flask of nightly.yaml runs: pytest (this job")
    assert "checks out pallets/flask" in statements[1]
