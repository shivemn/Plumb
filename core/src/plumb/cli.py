"""Command-line entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from plumb import __version__
from plumb.model import FactSet

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
