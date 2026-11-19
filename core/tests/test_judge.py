from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

from plumb.model import (
    Claim,
    Fact,
    FileEvidence,
    RemovedClaim,
    RepoKind,
    RepoRef,
    Report,
    Section,
)

JUDGE_PATH = Path(__file__).resolve().parents[2] / "eval" / "judge.py"


def load_judge() -> ModuleType:
    spec = importlib.util.spec_from_file_location("judge", JUDGE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["judge"] = module  # dataclasses look their module up while being made
    spec.loader.exec_module(module)
    return module


judge = load_judge()


def report() -> Report:
    fact = Fact(
        id="f1",
        statement="HTTP route GET /items in app/main.py",
        evidence=[FileEvidence(path="app/main.py", start_line=2, end_line=2)],
    )
    claims = [
        Claim(text="It serves GET /items.", fact_ids=["f1"]),
        Claim(text="Routes live in app/main.py.", fact_ids=["f1"]),
        Claim(text="It has one route.", fact_ids=["f1"]),
    ]
    return Report(
        repo=RepoRef(owner="o", name="shop", commit="abcdef1"),
        kind=RepoKind.SERVICE,
        model="anthropic:claude-opus-5-5",
        sections=[Section(id="entry_points", title="Ways in", claims=claims)],
        removed=[RemovedClaim(section="entry_points", text="Uses Redis.", reason="no fact")],
        facts=[fact],
    )


def answers(*values: str) -> Callable[[str], str]:
    replies: Iterator[str] = iter(values)

    def ask(prompt: str) -> str:
        return next(replies)

    return ask


def ignore(text: str) -> None:
    pass


def test_judging_saves_as_it_goes_and_resumes(tmp_path: Path) -> None:
    clones = tmp_path / "clones"
    (clones / "o__shop" / "app").mkdir(parents=True)
    (clones / "o__shop" / "app" / "main.py").write_text("app = App()\n@app.get('/items')\n")
    shown: list[str] = []
    count = judge.judge(report(), answers("x", "c", "q"), shown.append, tmp_path, clones)
    assert count == 1
    assert "Please answer c, w, u, s or q." in shown
    assert any("    2 | @app.get('/items')" in s for s in shown)

    assert judge.judge(report(), answers("w", "u"), shown.append, tmp_path, clones) == 2
    saved = judge.load_judgments(judge.judgment_file(report(), tmp_path))
    assert sorted(saved.values()) == ["correct", "unsure", "wrong"]


def test_summary(tmp_path: Path) -> None:
    judge.judge(report(), answers("c", "w", "s"), ignore, tmp_path, tmp_path)
    text = judge.summarise([report()], tmp_path)
    assert "All reports: 1 of 2 correct (50%)." in text
    row = "| shop | anthropic:claude-opus-5-5 | 1 of 2 correct (50%) | 0 | 1 | 1 of 4 (25%) |"
    assert row in text


def test_claim_key_ignores_spacing() -> None:
    assert judge.claim_key("It  serves\nGET /items.") == judge.claim_key("It serves GET /items.")
