"""Run every analysis step on a repo, in order, without AI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from plumb.contrib import find_steps
from plumb.deps import Dependency, find_dependencies
from plumb.entrypoints import EntryPoint, find_entry_points
from plumb.facts import build_facts
from plumb.graph import all_edges
from plumb.history import History, is_shallow, mine
from plumb.imports import Edge
from plumb.inventory import Category, FileInfo, build_inventory
from plumb.kind import KindDecision, decide_kind
from plumb.model import FactSet
from plumb.source import Checkout, Limits, fetch
from plumb.system import Migrations, System, find_migrations, find_settings, find_system


@dataclass(frozen=True)
class Analysis:
    checkout: Checkout
    files: list[FileInfo]
    history: History | None  # None for a shallow clone, where counts would be wrong
    edges: list[Edge]
    entry_points: list[EntryPoint]
    deps: list[Dependency]
    system: System
    decision: KindDecision
    migrations: list[Migrations]
    facts: FactSet

    @property
    def first_party(self) -> set[str]:
        return {f.path for f in self.files if f.category in (Category.SOURCE, Category.TEST)}


def analyse_repo(
    ref: str,
    workdir: Path,
    *,
    commit: str | None = None,
    window_days: int = 90,
    limits: Limits | None = None,
) -> Analysis:
    """Fetch `ref` and run every analysis step. Raises SourceError if it cannot be fetched."""
    checkout = fetch(ref, workdir=workdir, limits=limits, commit=commit)
    files = build_inventory(checkout.path)
    first_party = {f.path for f in files if f.category in (Category.SOURCE, Category.TEST)}
    history = (
        None
        if is_shallow(checkout.path)
        else mine(checkout.path, window_days=window_days, keep=first_party)
    )
    edges = all_edges(checkout.path, files)
    entry_points = find_entry_points(checkout.path, files)
    deps = find_dependencies(checkout.path, files)
    system = find_system(checkout.path, files, checkout.name, deps)
    settings = find_settings(checkout.path, files)
    decision = decide_kind(files, entry_points, system, deps)
    migrations = find_migrations(files)
    steps = find_steps(checkout.path, files)
    facts = build_facts(
        checkout, files, history, edges, entry_points, system, settings, decision, migrations, steps
    )
    return Analysis(
        checkout, files, history, edges, entry_points, deps, system, decision, migrations, facts
    )
