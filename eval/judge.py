"""Judge a report's claims by hand, and score claim precision.

    cd core
    uv run python ../eval/judge.py path/to/repo.report.json   # judge kept claims
    uv run python ../eval/judge.py --summary                   # write results/precision.md

For each claim the verifier kept, the claim is shown with the facts it
cites and the source lines those facts point at (from the clone under
~/.plumb/repos), and you answer:

    c  correct: a reader would be right to believe it
    w  wrong: false, or misleading enough to send a reader the wrong way
    u  unsure: the evidence shown is not enough to tell
    s  skip for now
    q  quit (answers so far are saved)

Answers are saved to judgments/<repo>.<model>.jsonl as you go, keyed by
the claim text, so a second run carries on where the first stopped and a
report written again only asks about claims that changed.

Claim precision is correct / (correct + wrong). Unsure answers are counted
separately rather than guessed. The removal rate is the share of all
claims the model wrote that the verifier dropped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from plumb.model import CommitEvidence, FileEvidence, IssueEvidence, Report

EVAL = Path(__file__).resolve().parent
JUDGMENTS = EVAL / "judgments"
RESULTS = EVAL / "results"
CLONES = Path.home() / ".plumb" / "repos"
VERDICTS = {"c": "correct", "w": "wrong", "u": "unsure"}


@dataclass(frozen=True)
class Item:
    section: str
    text: str
    key: str


def claim_key(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()[:16]


def judgment_file(report: Report, folder: Path = JUDGMENTS) -> Path:
    model = report.model.replace(":", "_").replace("/", "_")
    return folder / f"{report.repo.name}.{model}.jsonl"


def load_judgments(path: Path) -> dict[str, str]:
    """Claim key -> verdict. A later line for the same claim wins."""
    found: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                found[row["key"]] = row["verdict"]
    return found


def items(report: Report) -> list[Item]:
    return [
        Item(section.id, claim.text, claim_key(claim.text))
        for section in report.sections
        for claim in section.claims
    ]


def source_lines(report: Report, evidence: FileEvidence, clones: Path = CLONES) -> list[str]:
    path = clones / f"{report.repo.owner}__{report.repo.name}" / evidence.path
    if evidence.start_line is None or not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(evidence.start_line - 1, 0)
    end = min(evidence.end_line or evidence.start_line, start + 6)
    return [f"      {n + 1:>5} | {lines[n]}" for n in range(start, min(end, len(lines)))]


def describe(report: Report, section: str, text: str, clones: Path = CLONES) -> str:
    """The claim with its facts and their evidence, as shown to the judge."""
    facts = {f.id: f for f in report.facts}
    claim = next(c for s in report.sections if s.id == section for c in s.claims if c.text == text)
    out = [f"[{section}] {text}"]
    for fact_id in claim.fact_ids:
        fact = facts.get(fact_id)
        if fact is None:
            continue
        out.append(f"  {fact.id}: {fact.statement}")
        for evidence in fact.evidence:
            if isinstance(evidence, FileEvidence):
                where = evidence.path + (f":{evidence.start_line}" if evidence.start_line else "")
                out.append(f"    {where}")
                out += source_lines(report, evidence, clones)
            elif isinstance(evidence, CommitEvidence):
                out.append(f"    commit {evidence.sha[:10]}")
            elif isinstance(evidence, IssueEvidence):
                out.append(f"    issue or pull request #{evidence.number}")
    return "\n".join(out)


def judge(
    report: Report,
    ask: Callable[[str], str],
    show: Callable[[str], None],
    folder: Path = JUDGMENTS,
    clones: Path = CLONES,
) -> int:
    """Ask about every claim without a verdict yet. Returns how many were answered."""
    path = judgment_file(report, folder)
    done = load_judgments(path)
    todo = [i for i in items(report) if i.key not in done]
    show(f"{len(todo)} of {len(items(report))} claims to judge in {path.name}")
    answered = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    for number, item in enumerate(todo, 1):
        show(f"\n({number}/{len(todo)}) " + describe(report, item.section, item.text, clones))
        while (answer := ask("[c]orrect [w]rong [u]nsure [s]kip [q]uit: ").strip().lower()) not in (
            *VERDICTS,
            "s",
            "q",
        ):
            show("Please answer c, w, u, s or q.")
        if answer == "q":
            break
        if answer == "s":
            continue
        row = {"key": item.key, "section": item.section, "verdict": VERDICTS[answer]}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({**row, "text": item.text}) + "\n")
        answered += 1
    return answered


def summarise(reports: Iterable[Report], folder: Path = JUDGMENTS) -> str:
    rows: list[str] = []
    totals: Counter[str] = Counter()
    for report in reports:
        verdicts = load_judgments(judgment_file(report, folder))
        counts = Counter(verdicts.get(i.key, "not judged") for i in items(report))
        totals.update(counts)
        kept = sum(len(s.claims) for s in report.sections)
        written = kept + len(report.removed)
        rows.append(
            f"| {report.repo.name} | {report.model} | {_precision(counts)} "
            f"| {counts['unsure']} | {counts['not judged']} "
            f"| {len(report.removed)} of {written} ({_share(len(report.removed), written)}) |"
        )
    return "\n".join(
        [
            "# Claim precision",
            "",
            "Generated by `eval/judge.py --summary` from hand judgments in `eval/judgments/`.",
            "Precision is correct / (correct + wrong); unsure claims are not counted either way.",
            "",
            f"All reports: {_precision(totals)}.",
            "",
            "| Repo | Model | Precision | Unsure | Not judged | Removed by the verifier |",
            "|------|-------|-----------|-------:|-----------:|-------------------------|",
            *rows,
            "",
        ]
    )


def _precision(counts: Counter[str]) -> str:
    judged = counts["correct"] + counts["wrong"]
    if not judged:
        return "no claims judged"
    return f"{counts['correct']} of {judged} correct ({_share(counts['correct'], judged)})"


def _share(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "n/a"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("reports", nargs="*", type=Path, help="report JSON files to judge")
    parser.add_argument("--summary", action="store_true", help="write results/precision.md")
    parser.add_argument(
        "--reports-dir", type=Path, default=RESULTS, help="where --summary finds *.report.json"
    )
    args = parser.parse_args(argv)
    if args.summary:
        paths = args.reports or sorted(args.reports_dir.glob("*.report.json"))
        loaded = [Report.model_validate_json(p.read_text(encoding="utf-8")) for p in paths]
        text = summarise(loaded)
        (RESULTS / "precision.md").write_text(text, encoding="utf-8")
        print(text)
        return 0
    if not args.reports:
        parser.error("give a report to judge, or --summary")
    for path in args.reports:
        report = Report.model_validate_json(path.read_text(encoding="utf-8"))
        judge(report, input, print)
    return 0


if __name__ == "__main__":
    sys.exit(main())
