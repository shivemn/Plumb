"""Command-line entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from plumb import __version__
from plumb.model import FactSet, Report
from plumb.pipeline import Analysis, analyse_repo
from plumb.source import Limits, SourceError

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
    out: Annotated[Path, typer.Option(help="Folder to write the JSON Schemas into.")] = Path(
        "../schema"
    ),
) -> None:
    """Write the JSON Schemas for the fact and report formats."""
    out.mkdir(parents=True, exist_ok=True)
    for name, model in (("factset", FactSet), ("report", Report)):
        target = out / f"{name}.schema.json"
        target.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
        typer.echo(f"Wrote {target}")


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
    analysis = _analyse_or_exit(repo, workdir, commit, window_days, max_files)
    checkout, facts, history = analysis.checkout, analysis.facts, analysis.history

    target = out or Path(f"{checkout.name}.facts.json")
    target.write_text(facts.model_dump_json(indent=2) + "\n", encoding="utf-8")
    typer.echo(
        f"{checkout.owner}/{checkout.name} at {checkout.commit[:7]} "
        f"({analysis.decision.kind.value}): {len(analysis.files)} files, "
        f"{len(analysis.first_party)} first-party, {len(analysis.edges)} import links, "
        f"{len(analysis.entry_points)} entry points, "
        f"{len(history.commits) if history else 'no'} commits read, "
        f"{len(facts.facts)} facts written to {target}"
    )


def _analyse_or_exit(
    repo: str, workdir: Path, commit: str | None, window_days: int, max_files: int
) -> Analysis:
    try:
        analysis = analyse_repo(
            repo,
            workdir,
            commit=commit,
            window_days=window_days,
            limits=Limits(max_files=max_files),
        )
    except SourceError as error:
        typer.echo(f"Could not analyse {repo}: {error}", err=True)
        raise typer.Exit(1) from error
    if analysis.history is None:
        typer.echo(
            "This clone has only part of its history, so hot spots and files that change "
            "together are left out. Use a full clone or pass a GitHub URL instead.",
            err=True,
        )
    return analysis
