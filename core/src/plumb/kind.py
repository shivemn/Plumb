"""Decide what kind of repo this is, from what the other stages found.

The kind decides which section leads the report: a system design diagram
for a service, the public API for a library, and so on. Every decision
comes with the clues behind it, and a repo that matches nothing is called
unknown rather than forced into a kind.
"""

from __future__ import annotations

from dataclasses import dataclass

from plumb.deps import Dependency
from plumb.entrypoints import EntryKind, EntryPoint
from plumb.inventory import Category, FileInfo
from plumb.model import RepoKind
from plumb.system import Clue, Role, System

SMALL_SOURCE_LINES = 300

_WEBSITE_DEPS = {"astro", "next", "gatsby", "@sveltejs/kit", "nuxt", "@remix-run/react", "vite"}
_MANIFESTS = {"pyproject.toml", "setup.py", "setup.cfg", "pom.xml", "build.gradle", "package.json"}
_RUNNING = {EntryKind.HTTP, EntryKind.CONSUMER, EntryKind.SCHEDULED}


@dataclass(frozen=True)
class KindDecision:
    kind: RepoKind
    reason: str
    clues: tuple[Clue, ...]


def _clue(entry: EntryPoint) -> Clue:
    return Clue(entry.path, entry.line, entry.name)


def decide_kind(
    files: list[FileInfo],
    entry_points: list[EntryPoint],
    system: System,
    deps: list[Dependency],
) -> KindDecision:
    source = [f for f in files if f.category is Category.SOURCE]
    source_lines = sum(f.lines for f in source)
    docs = [f for f in files if f.category is Category.DOCS]

    if not source:
        clues = tuple(Clue(f.path, 1, "documentation") for f in docs[:3])
        if clues:
            return KindDecision(RepoKind.DOCS, "no source code, only documents", clues)
        return KindDecision(RepoKind.UNKNOWN, "no source code or documents", ())

    services = system.of(Role.SERVICE)
    running = [e for e in entry_points if e.kind in _RUNNING]
    if services or running:
        clues = [c for part in services for c in part.clues[:1]]
        clues += [_clue(e) for e in running[: max(0, 3 - len(clues))]]
        what: list[str] = []
        if services:
            what.append(f"{len(services)} deployable service(s)")
        if running:
            what.append(f"{len(running)} route(s), consumer(s) or scheduled job(s)")
        return KindDecision(RepoKind.SERVICE, " and ".join(what), tuple(clues[:3]))

    commands = [e for e in entry_points if e.kind is EntryKind.COMMAND]
    if commands:
        return KindDecision(
            RepoKind.CLI,
            f"{len(commands)} command(s) and no routes or services",
            tuple(_clue(e) for e in commands[:3]),
        )

    notebooks = [f for f in source if f.language == "notebook"]
    if notebooks and sum(f.lines for f in notebooks) * 2 >= source_lines:
        return KindDecision(
            RepoKind.DATA,
            f"{len(notebooks)} notebook(s) make up most of the code",
            tuple(Clue(f.path, 1, "notebook") for f in notebooks[:3]),
        )

    website = [d for d in deps if d.name in _WEBSITE_DEPS]
    if website:
        return KindDecision(
            RepoKind.WEBSITE,
            "a front-end build tool and no back-end service",
            tuple(Clue(d.path, d.line, f"dependency {d.name}") for d in website[:3]),
        )

    if source_lines < SMALL_SOURCE_LINES:
        largest = sorted(source, key=lambda f: -f.lines)[:3]
        return KindDecision(
            RepoKind.SMALL,
            f"{source_lines} lines of source code",
            tuple(Clue(f.path, 1, f"{f.lines} lines") for f in largest),
        )

    manifests = [f for f in files if f.path.rsplit("/", 1)[-1] in _MANIFESTS and "/" not in f.path]
    if manifests:
        return KindDecision(
            RepoKind.LIBRARY,
            "a package definition and no commands, routes or services",
            tuple(Clue(f.path, 1, "package definition") for f in manifests[:3]),
        )
    return KindDecision(RepoKind.UNKNOWN, "no package definition, commands or services", ())
