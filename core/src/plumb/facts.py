"""Turn what the analysis found into facts, each with its evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import PurePosixPath

from plumb.history import History
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
    kind: RepoKind = RepoKind.UNKNOWN,
) -> FactSet:
    builder = FactBuilder()
    add_language_facts(builder, files)
    add_skipped_facts(builder, files)
    add_build_file_facts(builder, files)
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
    for category in (Category.VENDORED, Category.GENERATED):
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
