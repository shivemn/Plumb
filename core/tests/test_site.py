import json
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from plumb import cli
from plumb.model import Report
from plumb.pipeline import Analysis, analyse_repo
from plumb.writer.models import ModelError
from tests.conftest import RepoBuilder
from tests.test_facts import sample_repo
from tests.test_report import FakeClient


class LimitedClient(FakeClient):
    """Answers until its daily limit, then refuses, like a free model."""

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = limit

    def complete(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        if self.calls >= self.limit:
            raise ModelError("fake:test: provider answered 429: daily limit")
        return super().complete(system, prompt, max_tokens)


@pytest.fixture
def site(
    make_repo: Callable[[str], RepoBuilder], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    repo = sample_repo(make_repo)
    analysis = analyse_repo(str(repo.path), tmp_path / "w")

    def fake_analyse(*args: object) -> Analysis:
        return analysis

    monkeypatch.setattr(cli, "_analyse_or_exit", fake_analyse)
    web = tmp_path / "web"
    web.mkdir()
    (web / "repos.toml").write_text('[[repo]]\nref = "o/one"\n[[repo]]\nref = "o/two"\n')
    return web


def build(web: Path, client: FakeClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    def make_client(spec: str) -> FakeClient:
        return client

    monkeypatch.setattr(cli, "make_client", make_client)
    args = ["site", "build", "--web", str(web), "--cache", str(tmp_path / "c.sqlite")]
    result = CliRunner().invoke(cli.app, args)
    return result.output


def test_build_stops_at_the_limit_and_carries_on(
    site: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = build(site, LimitedClient(limit=2), tmp_path, monkeypatch)
    assert "stopped: fake:test: provider answered 429" in first
    assert not (site / "reports" / "o__one.json").exists()
    index = json.loads((site / "reports" / "index.json").read_text())
    assert index["reports"] == []

    # The next day: the two answers already given are not paid for again,
    # and the second repo (same facts here) is answered from the cache too.
    client = LimitedClient(limit=100)
    second = build(site, client, tmp_path, monkeypatch)
    assert "0 of 2 reports already written" in second
    report = Report.model_validate_json((site / "reports" / "o__one.json").read_text())
    assert client.calls == len(report.sections) - 2
    assert report.views is not None and report.written_at
    assert (site / "reports" / "o__two.md").exists()
    index = json.loads((site / "reports" / "index.json").read_text())
    assert [r["slug"] for r in index["reports"]] == ["o__one", "o__two"]
    assert index["reports"][0]["summary"] == "This section has facts."

    third = build(site, LimitedClient(limit=0), tmp_path, monkeypatch)
    assert "2 of 2 reports already written" in third
