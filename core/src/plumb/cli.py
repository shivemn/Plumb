"""Command-line entry point."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import typer

from plumb import __version__
from plumb.github import GitHubClient
from plumb.markdown import render_markdown
from plumb.model import FactSet, Report
from plumb.pipeline import Analysis, analyse_repo
from plumb.source import Limits, SourceError
from plumb.verify import verify
from plumb.writer.models import ModelError, ResponseCache, make_client
from plumb.writer.plan import SYSTEM_PROMPT, plan_report
from plumb.writer.write import write_report

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
GITHUB_CACHE = Path.home() / ".plumb" / "github"


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
    github: Annotated[
        bool,
        typer.Option(
            help="Read starter issues and review speed from GitHub. Set GITHUB_TOKEN "
            "for more than 60 requests an hour."
        ),
    ] = True,
) -> None:
    """Analyse a repo without AI and write its facts as JSON."""
    analysis = _analyse_or_exit(repo, workdir, commit, window_days, max_files, github)
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
    repo: str,
    workdir: Path,
    commit: str | None,
    window_days: int,
    max_files: int,
    github: bool = True,
) -> Analysis:
    client = (
        GitHubClient(token=os.environ.get("GITHUB_TOKEN"), cache_dir=GITHUB_CACHE)
        if github
        else None
    )
    try:
        analysis = analyse_repo(
            repo,
            workdir,
            commit=commit,
            window_days=window_days,
            limits=Limits(max_files=max_files),
            github=client,
        )
    except SourceError as error:
        typer.echo(f"Could not analyse {repo}: {error}", err=True)
        raise typer.Exit(1) from error
    finally:
        if client is not None:
            client.close()
    if analysis.activity is not None and analysis.activity.error:
        typer.echo(f"Issues and pull requests were left out: {analysis.activity.error}", err=True)
    if analysis.history is None:
        typer.echo(
            "This clone has only part of its history, so hot spots and files that change "
            "together are left out. Use a full clone or pass a GitHub URL instead.",
            err=True,
        )
    return analysis


DEFAULT_CACHE = Path.home() / ".plumb" / "answers.sqlite"


@app.command()
def report(
    repo: Annotated[str, typer.Argument(help="A GitHub URL, owner/name, or a local folder.")],
    model: Annotated[
        str,
        typer.Option(
            help="provider:model, such as anthropic:claude-opus-5-5 or "
            "openrouter:openai/gpt-oss-120b:free. Also groq:, gemini:, openai: and "
            "ollama:<model>. The key comes from <PROVIDER>_API_KEY, such as OPENROUTER_API_KEY."
        ),
    ] = "anthropic:claude-opus-5-5",
    out: Annotated[
        Path | None, typer.Option(help="Report JSON. Defaults to <name>.report.json.")
    ] = None,
    markdown: Annotated[
        Path | None, typer.Option(help="Also write Markdown here. Defaults to <name>.report.md.")
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(help="Write the prompts and show their size, without calling a model."),
    ] = False,
    window_days: Annotated[int, typer.Option(help="Days of history to mine.")] = 90,
    workdir: Annotated[Path, typer.Option(help="Where cloned repos are kept.")] = DEFAULT_WORKDIR,
    max_files: Annotated[int, typer.Option(help="Refuse repos with more tracked files.")] = 20_000,
    commit: Annotated[
        str | None, typer.Option(help="Analyse this commit instead of the newest.")
    ] = None,
    github: Annotated[
        bool,
        typer.Option(
            help="Read starter issues and review speed from GitHub. Set GITHUB_TOKEN "
            "for more than 60 requests an hour."
        ),
    ] = True,
    cache: Annotated[Path, typer.Option(help="Where model answers are cached.")] = DEFAULT_CACHE,
) -> None:
    """Analyse a repo, have a model write the report, and keep only claims that check out."""
    analysis = _analyse_or_exit(repo, workdir, commit, window_days, max_files, github)
    name = analysis.checkout.name
    tasks = plan_report(analysis.facts)

    if dry_run:
        folder = Path(f"{name}.prompts")
        folder.mkdir(exist_ok=True)
        for number, task in enumerate(tasks, start=1):
            target = folder / f"{number:02d}-{task.section.id}.txt"
            target.write_text(f"{SYSTEM_PROMPT}\n---\n{task.prompt}", encoding="utf-8")
            typer.echo(
                f"{task.section.title}: {len(task.facts)} facts, "
                f"about {task.estimated_tokens:,} input tokens"
            )
        total = sum(t.estimated_tokens for t in tasks)
        typer.echo(f"{len(tasks)} prompts written to {folder}, about {total:,} input tokens in all")
        return

    try:
        client = make_client(model)
    except ModelError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    answers = ResponseCache(cache)
    try:
        drafts = write_report(tasks, client, answers)
    except ModelError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    finally:
        answers.close()
    verified = verify(drafts, analysis.facts, client.name)

    json_path = out or Path(f"{name}.report.json")
    md_path = markdown or Path(f"{name}.report.md")
    json_path.write_text(verified.model_dump_json(indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(verified), encoding="utf-8")
    kept = sum(len(s.claims) for s in verified.sections)
    dropped = sum(1 for r in verified.removed if r.text)
    typer.echo(
        f"{kept} of {kept + dropped} claims kept, {dropped} removed. "
        f"Wrote {json_path} and {md_path}"
    )


DEFAULT_DATABASE = Path.home() / ".plumb" / "jobs.sqlite"


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Address to listen on.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to listen on.")] = 8000,
    database: Annotated[Path, typer.Option(help="The job table.")] = DEFAULT_DATABASE,
) -> None:
    """Run the web API that queues repos and serves their facts. Needs plumb[server]."""
    try:
        import uvicorn

        from plumb.server.app import default_app
    except ImportError as error:
        typer.echo("The server needs extra packages: uv sync --extra server", err=True)
        raise typer.Exit(1) from error
    uvicorn.run(default_app(database), host=host, port=port)


@app.command()
def worker(
    database: Annotated[Path, typer.Option(help="The job table.")] = DEFAULT_DATABASE,
    workdir: Annotated[Path, typer.Option(help="Where cloned repos are kept.")] = DEFAULT_WORKDIR,
    max_files: Annotated[int, typer.Option(help="Refuse repos with more tracked files.")] = 20_000,
    once: Annotated[bool, typer.Option(help="Run one queued job and stop.")] = False,
    github: Annotated[
        bool, typer.Option(help="Read starter issues and review speed from GitHub.")
    ] = True,
) -> None:
    """Run queued analysis jobs."""
    import logging

    from plumb.server.jobs import JobStore
    from plumb.server.worker import make_analyser, run_forever, run_once

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    store = JobStore(database)
    client = (
        GitHubClient(token=os.environ.get("GITHUB_TOKEN"), cache_dir=GITHUB_CACHE)
        if github
        else None
    )
    analyse = make_analyser(workdir, Limits(max_files=max_files), client)
    if once:
        job = run_once(store, analyse)
        typer.echo(f"{job.repo}: {job.status.value}" if job else "No jobs queued.")
        return
    run_forever(store, analyse)
