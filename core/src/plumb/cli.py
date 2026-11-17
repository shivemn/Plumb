"""Command-line entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from plumb import __version__
from plumb.deps import find_dependencies
from plumb.entrypoints import find_entry_points
from plumb.facts import build_facts
from plumb.graph import all_edges
from plumb.history import is_shallow, mine
from plumb.inventory import Category, build_inventory
from plumb.kind import decide_kind
from plumb.model import FactSet
from plumb.source import Limits, SourceError, fetch
from plumb.system import find_settings, find_system

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _show_version(value: bool) -> None:
    if value:
        typer.echo(f"plumb {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_show_version, is_eager=True, help="Show the version."),
    ] = False,
) -> None:
    """Explain a repository, with a source behind every claim."""


@app.command()
def schema(
    out: Annotated[Path, typer.Option(help="Where to write the JSON Schema.")] = Path(
        "../schema/factset.schema.json"
    ),
) -> None:
    """Write the JSON Schema for the shared fact format."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(FactSet.model_json_schema(), indent=2) + "\n", encoding="utf-8")
    typer.echo(f"Wrote {out}")


DEFAULT_WORKDIR = Path.home() / ".plumb" / "repos"


@app.command()
def analyse(
    repo: Annotated[str, typer.Argument(help="A GitHub URL, owner/name, or a local folder.")],
    out: Annotated[
        Path | None, typer.Option(help="Where to write the facts. Defaults to <name>.facts.json.")
    ] = None,
    window_days: Annotated[int, typer.Option(help="Days of history to mine.")] = 90,
    workdir: Annotated[Path, typer.Option(help="Where cloned repos are kept.")] = DEFAULT_WORKDIR,
    max_files: Annotated[int, typer.Option(help="Refuse repos with more tracked files.")] = 20_000,
    commit: Annotated[
        str | None, typer.Option(help="Analyse this commit instead of the newest.")
    ] = None,
) -> None:
    """Analyse a repo without AI and write its facts as JSON."""
    try:
        checkout = fetch(repo, workdir=workdir, limits=Limits(max_files=max_files), commit=commit)
    except SourceError as error:
        typer.echo(f"Could not analyse {repo}: {error}", err=True)
        raise typer.Exit(1) from error

    files = build_inventory(checkout.path)
    first_party = {f.path for f in files if f.category in (Category.SOURCE, Category.TEST)}
    if is_shallow(checkout.path):
        history = None
        typer.echo(
            "This clone has only part of its history, so hot spots and files that change "
            "together are left out. Use a full clone or pass a GitHub URL instead.",
            err=True,
        )
    else:
        history = mine(checkout.path, window_days=window_days, keep=first_party)
    edges = all_edges(checkout.path, files)
    entry_points = find_entry_points(checkout.path, files)
    deps = find_dependencies(checkout.path, files)
    system = find_system(checkout.path, files, checkout.name, deps)
    settings = find_settings(checkout.path, files)
    decision = decide_kind(files, entry_points, system, deps)
    facts = build_facts(checkout, files, history, edges, entry_points, system, settings, decision)

    target = out or Path(f"{checkout.name}.facts.json")
    target.write_text(facts.model_dump_json(indent=2) + "\n", encoding="utf-8")
    typer.echo(
        f"{checkout.owner}/{checkout.name} at {checkout.commit[:7]} ({decision.kind.value}): "
        f"{len(files)} files, {len(first_party)} first-party, {len(edges)} import links, "
        f"{len(entry_points)} entry points, "
        f"{len(history.commits) if history else 'no'} commits read, "
        f"{len(facts.facts)} facts written to {target}"
    )
