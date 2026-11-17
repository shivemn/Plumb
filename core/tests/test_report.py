import json
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from plumb import cli
from plumb.markdown import render_markdown
from plumb.model import Report
from tests.conftest import RepoBuilder
from tests.test_facts import sample_repo


class FakeClient:
    """Answers every section with one supported claim and one invented one."""

    name = "fake:test"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        self.calls += 1
        first = next(line.split(":", 1)[0] for line in prompt.splitlines() if line.startswith("f"))
        return json.dumps(
            {
                "claims": [
                    {"text": "This section has facts.", "fact_ids": [first]},
                    {"text": "It also reads app/secret.py.", "fact_ids": [first]},
                ]
            }
        )


@pytest.fixture
def repo(make_repo: Callable[[str], RepoBuilder]) -> RepoBuilder:
    return sample_repo(make_repo)


def test_dry_run_writes_prompts_without_a_key(
    repo: RepoBuilder, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = CliRunner().invoke(
        cli.app, ["report", str(repo.path), "--dry-run", "--workdir", str(tmp_path / "w")]
    )
    assert result.exit_code == 0, result.output
    prompts = sorted((tmp_path / "shop.prompts").iterdir())
    assert prompts and "input tokens in all" in result.output
    assert "<<<facts" in prompts[0].read_text()


def test_report_without_a_key_explains(
    repo: RepoBuilder, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = CliRunner().invoke(cli.app, ["report", str(repo.path), "--workdir", str(tmp_path)])
    assert result.exit_code == 1
    assert "set ANTHROPIC_API_KEY" in result.output


def test_report_keeps_supported_claims_and_writes_markdown(
    repo: RepoBuilder, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeClient()

    def make_client(spec: str) -> FakeClient:
        return fake

    monkeypatch.setattr(cli, "make_client", make_client)
    out, md = tmp_path / "r.json", tmp_path / "r.md"
    args = ["report", str(repo.path), "--out", str(out), "--markdown", str(md)]
    args += ["--workdir", str(tmp_path / "w"), "--cache", str(tmp_path / "c.sqlite")]
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 0, result.output

    report = Report.model_validate_json(out.read_text())
    sections = len(report.sections)
    assert sum(len(s.claims) for s in report.sections) == sections
    assert len(report.removed) == sections
    assert all("app/secret.py" in r.reason for r in report.removed)
    assert f"{sections} of {sections * 2} claims kept" in result.output

    text = md.read_text()
    assert text.startswith("# local/shop")
    assert "## Sources" in text and "## Removed" in text

    # A second run is answered from the cache.
    calls = fake.calls
    CliRunner().invoke(cli.app, args)
    assert fake.calls == calls


def test_markdown_for_an_empty_section() -> None:
    report = Report.model_validate(
        {
            "repo": {"owner": "o", "name": "n", "commit": "abcdef1"},
            "kind": "library",
            "model": "fake:test",
            "sections": [{"id": "overview", "title": "Overview", "claims": []}],
            "removed": [],
            "facts": [],
        }
    )
    assert "could be supported" in render_markdown(report)
