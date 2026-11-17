"""Turn what the analysis found into facts, each with its evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import PurePosixPath

from plumb.entrypoints import EntryKind, EntryPoint
from plumb.graph import component_edges, most_used, mutual_components
from plumb.history import History
from plumb.imports import Edge
from plumb.inventory import Category, FileInfo
from plumb.model import (
    CommitEvidence,
    Evidence,
    Fact,
    FactSet,
    FileEvidence,
    RepoKind,
    RepoRef,
)
from plumb.source import Checkout
from plumb.system import Clue, Role, System

# Files that say how a repo is built, run or deployed. Later stages read
# these to find services, databases and entry points.
_BUILD_FILES = (
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
    "pyproject.toml", "setup.py", "requirements.txt", "package.json", "pom.xml",
    "build.gradle", "build.gradle.kts", "go.mod", "Cargo.toml", "Makefile", "Procfile",
    "render.yaml", "fly.toml", "vercel.json", "netlify.toml",
)  # fmt: skip


class FactBuilder:
    def __init__(self) -> None:
        self.facts: list[Fact] = []

    def add(self, statement: str, evidence: Sequence[Evidence]) -> str:
        fact_id = f"f{len(self.facts) + 1}"
        self.facts.append(Fact(id=fact_id, statement=statement, evidence=list(evidence)))
        return fact_id


def build_facts(
    checkout: Checkout,
    files: list[FileInfo],
    history: History | None,
    edges: list[Edge] | None = None,
    entry_points: list[EntryPoint] | None = None,
    system: System | None = None,
    settings: dict[str, list[Clue]] | None = None,
    kind: RepoKind = RepoKind.UNKNOWN,
) -> FactSet:
    builder = FactBuilder()
    add_language_facts(builder, files)
    add_skipped_facts(builder, files)
    add_build_file_facts(builder, files)
    if system is not None:
        add_system_facts(builder, system)
    if settings:
        add_setting_facts(builder, settings)
    if entry_points:
        add_entry_point_facts(builder, entry_points)
    if edges:
        add_graph_facts(builder, edges)
    if history is not None:
        add_history_facts(builder, history)
    return FactSet(
        repo=RepoRef(owner=checkout.owner, name=checkout.name, commit=checkout.commit),
        kind=kind,
        facts=builder.facts,
    )


def add_language_facts(builder: FactBuilder, files: list[FileInfo]) -> None:
    by_language: defaultdict[str, list[FileInfo]] = defaultdict(list)
    for info in files:
        if info.language and info.category is Category.SOURCE:
            by_language[info.language].append(info)
    ranked = sorted(by_language.items(), key=lambda item: -sum(f.lines for f in item[1]))
    for language, infos in ranked:
        lines = sum(f.lines for f in infos)
        largest = sorted(infos, key=lambda f: (-f.lines, f.path))[:3]
        builder.add(
            f"{_plural(len(infos), 'source file')} in {language}, {lines:,} lines in all",
            [FileEvidence(path=f.path) for f in largest],
        )


def add_skipped_facts(builder: FactBuilder, files: list[FileInfo]) -> None:
    for category in (Category.VENDORED, Category.GENERATED, Category.EXAMPLE):
        skipped = [f for f in files if f.category is category]
        if not skipped:
            continue
        folders = Counter(_top_folder(f.path) for f in skipped)
        examples = [
            next(f for f in skipped if _top_folder(f.path) == top)
            for top, _ in folders.most_common(3)
        ]
        builder.add(
            f"{_plural(len(skipped), f'{category.value} file')} left out of the analysis",
            [FileEvidence(path=f.path) for f in examples],
        )


def add_build_file_facts(builder: FactBuilder, files: list[FileInfo]) -> None:
    for info in files:
        if info.category in (Category.VENDORED, Category.GENERATED):
            continue
        pure = PurePosixPath(info.path)
        if pure.name in _BUILD_FILES:
            builder.add(f"Build or deploy file {info.path}", [FileEvidence(path=info.path)])
        elif pure.parts[:2] == (".github", "workflows") and pure.suffix in (".yml", ".yaml"):
            builder.add(f"GitHub Actions workflow {info.path}", [FileEvidence(path=info.path)])


_ROLE_LABELS = {
    Role.SERVICE: "Service run from this repo",
    Role.STORE: "Database, cache or queue",
    Role.MONITORING: "Monitoring",
    Role.OUTSIDE: "Outside service",
    Role.CONTAINER: "Other container",
}


def add_system_facts(builder: FactBuilder, system: System) -> None:
    for role, label in _ROLE_LABELS.items():
        for part in system.of(role):
            details = "; ".join(dict.fromkeys(c.detail for c in part.clues))
            builder.add(
                f"{label}: {part.name} ({details})",
                [
                    FileEvidence(path=c.path, start_line=c.line, end_line=c.line)
                    for c in part.clues[:5]
                ],
            )


def add_setting_facts(
    builder: FactBuilder, settings: dict[str, list[Clue]], limit: int = 30
) -> None:
    for name, clues in list(settings.items())[:limit]:
        places = ", ".join(c.path for c in clues)
        builder.add(
            f"Setting {name} is read from the environment in {places}",
            [FileEvidence(path=c.path, start_line=c.line, end_line=c.line) for c in clues],
        )


_ENTRY_LABELS = {
    EntryKind.HTTP: "HTTP route",
    EntryKind.COMMAND: "Command",
    EntryKind.CONSUMER: "Queue consumer",
    EntryKind.SCHEDULED: "Scheduled job",
    EntryKind.TASK: "Background task",
    EntryKind.MAIN: "Program entry",
    EntryKind.SCRIPT: "Package script",
}


def add_entry_point_facts(builder: FactBuilder, entry_points: list[EntryPoint]) -> None:
    """One fact per kind with a count, then one per entry point, up to a limit per kind."""
    for kind, label in _ENTRY_LABELS.items():
        found = [e for e in entry_points if e.kind is kind]
        if not found:
            continue
        builder.add(
            f"{_plural(len(found), label.lower())} found",
            [FileEvidence(path=e.path, start_line=e.line, end_line=e.line) for e in found[:3]],
        )
        for entry in found[:40]:
            via = f" ({entry.framework})" if entry.framework else ""
            builder.add(
                f"{label} {entry.name}{via} in {entry.path}",
                [FileEvidence(path=entry.path, start_line=entry.line, end_line=entry.line)],
            )


def add_graph_facts(builder: FactBuilder, edges: list[Edge], limit: int = 15) -> None:
    components = component_edges(edges)
    for item in components[:limit]:
        builder.add(
            f"Code in {item.source} uses code in {item.target} "
            f"({_plural(item.count, 'reference')})",
            [_line(e) for e in item.examples],
        )
    for forward, back in mutual_components(components):
        builder.add(
            f"{forward.source} and {forward.target} each use the other",
            [_line(forward.examples[0]), _line(back.examples[0])],
        )
    for target, users in most_used(edges):
        sources = len({e.source for e in users})
        if sources < 3:
            break
        builder.add(
            f"{target} is used by {_plural(sources, 'other file')}",
            [FileEvidence(path=target), *(_line(e) for e in users[:2])],
        )


def _line(edge: Edge) -> FileEvidence:
    return FileEvidence(path=edge.source, start_line=edge.line, end_line=edge.line)


# A file has to change at least this often to count as a hot spot.
MIN_HOT_COMMITS = 3


def add_history_facts(builder: FactBuilder, history: History, limit: int = 10) -> None:
    window = f"between {history.since:%d %b %Y} and {history.until:%d %b %Y}"
    if history.commits:
        builder.add(
            f"{_plural(len(history.commits), 'commit')} {window}",
            [CommitEvidence(sha=c.sha) for c in history.commits[:3]],
        )
    for item in history.hot_files(limit):
        if item.commits < MIN_HOT_COMMITS:
            break
        builder.add(
            f"{item.path} changed in {_plural(item.commits, 'commit')} "
            f"by {_plural(item.authors, 'author')} {window}",
            [FileEvidence(path=item.path), *(CommitEvidence(sha=s) for s in item.recent_shas[:3])],
        )
    for coupling in history.couplings[:limit]:
        builder.add(
            f"{coupling.a} and {coupling.b} changed in the same commit "
            f"{_plural(coupling.together, 'time')} {window}",
            [FileEvidence(path=coupling.a), FileEvidence(path=coupling.b)],
        )


def _top_folder(path: str) -> str:
    parts = PurePosixPath(path).parts
    for i, part in enumerate(parts):
        if part in ("node_modules", "vendor", "dist", "build", "target", "third_party"):
            return "/".join(parts[: i + 1])
    return parts[0] if len(parts) > 1 else "."


def _plural(count: int, noun: str) -> str:
    return f"{count:,} {noun}" + ("" if count == 1 else "s")
