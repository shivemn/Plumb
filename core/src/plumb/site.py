"""Build the reports the static site shows.

The site lists the repos in web/repos.toml. Each is analysed, a model writes
its report, and the result goes to web/reports/<owner>__<name>.json, with a
Markdown copy beside it. A repo that already has a report is skipped, so a
build that stops at a free model's daily limit carries on the next day where
it left off. web/reports/index.json lists what is there, for the gallery.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from plumb.markdown import render_markdown
from plumb.model import Report
from plumb.pipeline import Analysis
from plumb.verify import verify
from plumb.views import build_views, today
from plumb.writer.models import ModelClient, ResponseCache
from plumb.writer.plan import plan_report
from plumb.writer.write import write_report


@dataclass(frozen=True)
class SiteRepo:
    ref: str  # owner/name
    commit: str | None = None

    @property
    def slug(self) -> str:
        return self.ref.replace("/", "__")


def write_full_report(analysis: Analysis, client: ModelClient, answers: ResponseCache) -> Report:
    """Analysis in, verified report with its views out. Raises ModelError."""
    drafts = write_report(plan_report(analysis.facts), client, answers)
    verified = verify(drafts, analysis.facts, client.name)
    return verified.model_copy(update={"views": build_views(analysis), "written_at": today()})


def save_report(report: Report, json_path: Path) -> Path:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(report.model_dump_json(indent=1) + "\n", encoding="utf-8")
    md_path = json_path.with_suffix(".md")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return md_path


def load_repos(path: Path) -> list[SiteRepo]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [SiteRepo(r["ref"], r.get("commit")) for r in data.get("repo", [])]


def summary_of(report: Report) -> str:
    """One line for the gallery: the report's first overview claim."""
    for section in report.sections:
        if section.id == "overview" and section.claims:
            return section.claims[0].text
    return ""


def write_index(reports_dir: Path, order: list[SiteRepo]) -> Path:
    """index.json: one entry per report, in the order of repos.toml."""
    entries: list[dict[str, object]] = []
    for repo in order:
        path = reports_dir / f"{repo.slug}.json"
        if not path.exists():
            continue
        report = Report.model_validate_json(path.read_text(encoding="utf-8"))
        kept = sum(len(s.claims) for s in report.sections)
        removed = sum(1 for r in report.removed if r.text)
        entries.append(
            {
                "slug": repo.slug,
                "repo": f"{report.repo.owner}/{report.repo.name}",
                "commit": report.repo.commit,
                "kind": report.kind.value,
                "summary": summary_of(report),
                "kept": kept,
                "removed": removed,
                "model": report.model,
                "written_at": report.written_at,
            }
        )
    reports_dir.mkdir(parents=True, exist_ok=True)
    index = reports_dir / "index.json"
    index.write_text(json.dumps({"reports": entries}, indent=1) + "\n", encoding="utf-8")
    return index
