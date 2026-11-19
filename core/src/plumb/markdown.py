"""Render a verified report as Markdown, with every claim linked to its sources."""

from __future__ import annotations

from plumb.model import CommitEvidence, FileEvidence, IssueEvidence, Report


def _evidence(item: FileEvidence | CommitEvidence | IssueEvidence) -> str:
    if isinstance(item, FileEvidence):
        if item.start_line is None:
            return f"`{item.path}`"
        if item.start_line == item.end_line:
            return f"`{item.path}` line {item.start_line}"
        return f"`{item.path}` lines {item.start_line} to {item.end_line}"
    if isinstance(item, CommitEvidence):
        return f"commit {item.sha[:7]}"
    return f"issue {item.number}"


def render_markdown(report: Report) -> str:
    repo = report.repo
    kept = sum(len(s.claims) for s in report.sections)
    dropped = sum(1 for r in report.removed if r.text)
    lines = [
        f"# {repo.owner}/{repo.name}",
        "",
        f"Commit {repo.commit[:7]}. Kind: {report.kind.value}. Written by {report.model}.",
        f"{kept} of {kept + dropped} claims kept after checking them against the code.",
        "",
    ]
    for section in report.sections:
        lines += [f"## {section.title}", ""]
        if not section.claims:
            lines += ["Nothing in this section could be supported by what was found.", ""]
            continue
        for claim in section.claims:
            refs = ", ".join(f"[{i}](#{i})" for i in claim.fact_ids)
            lines.append(f"- {claim.text} ({refs})")
        lines.append("")

    if report.facts:
        lines += ["## Sources", ""]
        for fact in report.facts:
            where = "; ".join(_evidence(e) for e in fact.evidence)
            end = "" if fact.statement.endswith((".", "!", "?")) else "."
            lines.append(f'- <a id="{fact.id}"></a>**{fact.id}**: {fact.statement}{end} {where}')
        lines.append("")

    if report.removed:
        lines += ["## Removed", "", "These were written by the model and failed a check.", ""]
        for item in report.removed:
            text = f'"{item.text}"' if item.text else "Whole section"
            lines.append(f"- {text} ({item.section}): {item.reason}")
        lines.append("")
    return "\n".join(lines)
