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
from plumb.site import load_repos, save_report, write_full_report, write_index
from plumb.source import Limits, SourceError
from plumb.writer.models import ModelError, ResponseCache, make_client
from plumb.writer.plan import plan_report

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


# Plumb's own files: clones, caches and the job table. PLUMB_HOME moves them,
# for a container with its data on a volume.
PLUMB_HOME = Path(os.environ.get("PLUMB_HOME") or Path.home() / ".plumb")
DEFAULT_WORKDIR = PLUMB_HOME / "repos"
GITHUB_CACHE = PLUMB_HOME / "github"


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


DEFAULT_CACHE = PLUMB_HOME / "answers.sqlite"


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
            target.write_text(f"{task.system}\n---\n{task.prompt}", encoding="utf-8")
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
        verified = write_full_report(analysis, client, answers)
    except ModelError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    finally:
        answers.close()

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


DEFAULT_DATABASE = PLUMB_HOME / "jobs.sqlite"


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Address to listen on.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(envvar="PORT", help="Port to listen on.")] = 8000,
    database: Annotated[
        Path, typer.Option(envvar="PLUMB_DATABASE", help="The job table.")
    ] = DEFAULT_DATABASE,
    workdir: Annotated[
        Path, typer.Option(envvar="PLUMB_WORKDIR", help="Where repos are cloned.")
    ] = DEFAULT_WORKDIR,
    with_worker: Annotated[
        bool, typer.Option(help="Also run a worker, in its own process.")
    ] = True,
) -> None:
    """Run the web API, and a worker beside it. Needs plumb[server].

    Settings come from the environment, so a host can set them without a
    command line: PLUMB_MODEL (the server's own model, such as
    openrouter:nvidia/nemotron-3-ultra-550b-a55b:free, with its key in
    OPENROUTER_API_KEY), PLUMB_DAILY_REPORTS, PLUMB_ALLOWED_ORIGINS
    (comma-separated), PLUMB_JOBS_PER_HOUR, PLUMB_MAX_WAITING, PLUMB_JOB_SECONDS,
    PLUMB_MAX_FILES, and behind a proxy PLUMB_CLIENT_IP_HEADER (a header the
    proxy sets to the visitor's address) or PLUMB_TRUST_PROXY=1.
    """
    try:
        import uvicorn

        from plumb.server.app import create_app
        from plumb.server.jobs import JobStore
    except ImportError as error:
        typer.echo("The server needs extra packages: uv sync --extra server", err=True)
        raise typer.Exit(1) from error
    import multiprocessing

    from plumb.server.config import server_settings
    from plumb.server.keeper import WorkerKeeper

    settings = server_settings(os.environ)
    # Set up the job table before the worker opens it, so the two processes
    # never race to create it.
    store = JobStore(database)
    keeper = None
    if with_worker:
        keeper = WorkerKeeper(
            lambda: multiprocessing.Process(
                target=_worker_process, args=(database, workdir), daemon=True, name="plumb-worker"
            )
        )
        keeper.start()
    try:
        app_ = create_app(store, settings, keeper.alive if keeper else None)
        uvicorn.run(app_, host=host, port=port)
    finally:
        if keeper is not None:
            keeper.stop()


def _worker_process(database: Path, workdir: Path) -> None:
    worker(database=database, workdir=workdir)


@app.command()
def worker(
    database: Annotated[
        Path, typer.Option(envvar="PLUMB_DATABASE", help="The job table.")
    ] = DEFAULT_DATABASE,
    workdir: Annotated[
        Path, typer.Option(envvar="PLUMB_WORKDIR", help="Where repos are cloned.")
    ] = DEFAULT_WORKDIR,
    max_files: Annotated[int, typer.Option(help="Refuse repos with more tracked files.")] = 20_000,
    once: Annotated[bool, typer.Option(help="Run one queued job and stop.")] = False,
    github: Annotated[
        bool, typer.Option(help="Read starter issues and review speed from GitHub.")
    ] = True,
) -> None:
    """Run queued jobs: analyse each repo and, within the daily cap, write its report."""
    import logging

    from plumb.server.config import server_writer, worker_max_files, worker_seconds
    from plumb.server.jobs import JobStore
    from plumb.server.worker import make_analyser, run_forever, run_once

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    store = JobStore(database)
    client = (
        GitHubClient(token=os.environ.get("GITHUB_TOKEN"), cache_dir=GITHUB_CACHE)
        if github
        else None
    )
    limits = Limits(max_files=worker_max_files(os.environ, max_files))
    analyse = make_analyser(workdir, limits, client)
    writer = server_writer(os.environ, DEFAULT_CACHE)
    seconds = worker_seconds(os.environ)
    if writer is None:
        typer.echo("No PLUMB_MODEL set: jobs will produce facts, and no reports.", err=True)
    if once:
        job = run_once(store, analyse, writer, seconds, workdir)
        typer.echo(f"{job.repo}: {job.status.value}" if job else "No jobs queued.")
        return
    run_forever(store, analyse, writer, seconds, workdir)


site_app = typer.Typer(no_args_is_help=True, help="Build the reports for the static site.")
app.add_typer(site_app, name="site")
DEFAULT_WEB = Path(__file__).resolve().parents[3] / "web"


@site_app.command("build")
def site_build(
    model: Annotated[
        str, typer.Option(help="provider:model, as for plumb report.")
    ] = "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free",
    web: Annotated[Path, typer.Option(help="The site folder, with repos.toml.")] = DEFAULT_WEB,
    force: Annotated[bool, typer.Option(help="Write reports that already exist again.")] = False,
    only: Annotated[
        list[str] | None, typer.Option(help="Only this repo (owner/name). Can be repeated.")
    ] = None,
    workdir: Annotated[Path, typer.Option(help="Where cloned repos are kept.")] = DEFAULT_WORKDIR,
    cache: Annotated[Path, typer.Option(help="Where model answers are cached.")] = DEFAULT_CACHE,
    github: Annotated[bool, typer.Option(help="Read issues and pull requests.")] = True,
) -> None:
    """Write a report for each repo in web/repos.toml that does not have one yet.

    Stops at the first model error, such as a free model's daily limit. Run it
    again later: finished reports are kept and answers already paid for are
    cached, so it carries on where it stopped.
    """
    repos = load_repos(web / "repos.toml")
    reports_dir = web / "reports"
    try:
        client = make_client(model)
    except ModelError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    todo = [
        r
        for r in repos
        if (not only or r.ref in only) and (force or not (reports_dir / f"{r.slug}.json").exists())
    ]
    typer.echo(f"{len(repos) - len(todo)} of {len(repos)} reports already written.")
    answers = ResponseCache(cache)
    stopped = False
    try:
        for number, repo in enumerate(todo, start=1):
            typer.echo(f"[{number}/{len(todo)}] {repo.ref}")
            analysis = _analyse_or_exit(
                f"https://github.com/{repo.ref}", workdir, repo.commit, 90, 20_000, github
            )
            try:
                report = write_full_report(analysis, client, answers)
            except ModelError as error:
                typer.echo(f"  stopped: {error}", err=True)
                stopped = True
                break
            md = save_report(report, reports_dir / f"{repo.slug}.json")
            kept = sum(len(s.claims) for s in report.sections)
            typer.echo(f"  {kept} claims kept; wrote {md.with_suffix('.json').name}")
    finally:
        answers.close()
    index = write_index(reports_dir, repos)
    typer.echo(f"Updated {index}")
    if stopped:
        typer.echo("Run the same command again later to finish; finished reports are kept.")
        raise typer.Exit(1)


@site_app.command("index")
def site_index(
    web: Annotated[Path, typer.Option(help="The site folder, with repos.toml.")] = DEFAULT_WEB,
) -> None:
    """Rebuild web/reports/index.json from the reports that exist."""
    typer.echo(f"Wrote {write_index(web / 'reports', load_repos(web / 'repos.toml'))}")
