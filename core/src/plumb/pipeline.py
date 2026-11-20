"""Run every analysis step on a repo, in order, without AI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from plumb.activity import Activity, read_activity
from plumb.contrib import find_steps
from plumb.deps import Dependency, find_dependencies
from plumb.entrypoints import EntryPoint, find_entry_points
from plumb.facts import build_facts
from plumb.flow import Flow, trace_flows
from plumb.github import GitHubClient
from plumb.graph import all_edges
from plumb.history import History, is_shallow, mine
from plumb.imports import Edge
from plumb.inventory import Category, FileInfo, build_inventory
from plumb.kind import KindDecision, decide_kind
from plumb.libapi import find_public_api
from plumb.model import FactSet, RepoKind
from plumb.publicapi import PublicApi
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
    activity: Activity | None = None  # None when GitHub was not asked
    api: PublicApi | None = None  # only looked for in a library
    flows: list[Flow] = field(default_factory=list[Flow])

    @property
    def first_party(self) -> set[str]:
        return {f.path for f in self.files if f.category in (Category.SOURCE, Category.TEST)}


def _quiet(stage: str) -> None:
    pass


def analyse_repo(
    ref: str,
    workdir: Path,
    *,
    commit: str | None = None,
    window_days: int = 90,
    limits: Limits | None = None,
    github: GitHubClient | None = None,
    progress: Callable[[str], None] | None = None,
) -> Analysis:
    """Fetch `ref` and run every analysis step. Raises SourceError if it cannot be fetched.

    With a GitHub client, starter issues and review speed are read too; a
    local folder that is not a GitHub clone has neither.
    """
    say = progress or _quiet
    say("Fetching the repo")
    checkout = fetch(ref, workdir=workdir, limits=limits, commit=commit)
    say("Reading files and history")
    files = build_inventory(checkout.path)
    first_party = {f.path for f in files if f.category in (Category.SOURCE, Category.TEST)}
    history = (
        None
        if is_shallow(checkout.path)
        else mine(checkout.path, window_days=window_days, keep=first_party)
    )
    say("Finding services, routes and imports")
    edges = all_edges(checkout.path, files)
    entry_points = find_entry_points(checkout.path, files)
    deps = find_dependencies(checkout.path, files)
    system = find_system(checkout.path, files, checkout.name, deps)
    settings = find_settings(checkout.path, files)
    decision = decide_kind(files, entry_points, system, deps)
    migrations = find_migrations(files)
    steps = find_steps(checkout.path, files)
    say("Tracing requests through the code")
    flows = trace_flows(checkout.path, files, entry_points)
    api = None
    if decision.kind is RepoKind.LIBRARY:
        api = find_public_api(checkout.path, files, edges, checkout.name)
    activity = None
    if github is not None and checkout.owner != "local":
        say("Reading issues and pull requests")
        paths = {f.path for f in files}
        activity = read_activity(github, checkout.owner, checkout.name, paths)
    facts = build_facts(
        checkout,
        files,
        history,
        edges,
        entry_points,
        system,
        settings,
        decision,
        migrations,
        steps,
        activity,
        api,
        flows,
    )
    return Analysis(
        checkout,
        files,
        history,
        edges,
        entry_points,
        deps,
        system,
        decision,
        migrations,
        facts,
        activity,
        api,
        flows,
    )
