"""Run queued jobs, one at a time: analyse the repo, then write its report.

The report is written by the server's own model only while it is under its
daily cap. Past the cap, the job finishes with facts alone, and the site
offers to write the report in the visitor's browser with their own key.
Each job has a time limit, and its clone is deleted when it finishes, so
the server's disk does not fill up.
"""

from __future__ import annotations

import logging
import shutil
import signal
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from plumb.github import GitHubClient
from plumb.model import Report
from plumb.pipeline import Analysis, analyse_repo
from plumb.server.jobs import Job, JobStore
from plumb.site import write_full_report
from plumb.source import Limits, SourceError
from plumb.views import build_views
from plumb.writer.models import ModelClient, ModelError, ResponseCache

log = logging.getLogger("plumb.worker")

Analyse = Callable[[Job, Callable[[str], None]], Analysis]


class JobTimeout(Exception):
    pass


@dataclass
class ServerWriter:
    """The server's own model, with a cap on reports per day."""

    client: ModelClient
    cache: ResponseCache | None
    daily_reports: int

    def has_room(self, store: JobStore) -> bool:
        since = datetime.now(UTC) - timedelta(days=1)
        return store.reports_written_since(since) < self.daily_reports

    def write(self, analysis: Analysis) -> Report:
        return write_full_report(analysis, self.client, self.cache)


def make_analyser(
    workdir: Path, limits: Limits | None = None, github: GitHubClient | None = None
) -> Analyse:
    def analyse(job: Job, progress: Callable[[str], None]) -> Analysis:
        # Always a URL: "owner/name" could also name a folder on the server.
        url = f"https://github.com/{job.repo}"
        return analyse_repo(
            url, workdir, commit=job.commit, limits=limits, github=github, progress=progress
        )

    return analyse


class time_limit:  # noqa: N801 - used like a function: `with time_limit(300):`
    """Stop the job after `seconds`. Works on the main thread only; elsewhere, no limit."""

    def __init__(self, seconds: int) -> None:
        self.seconds = seconds
        self.armed = seconds > 0 and threading.current_thread() is threading.main_thread()

    def _stop(self, signum: int, frame: object) -> None:
        raise JobTimeout(f"the analysis took longer than {self.seconds} seconds")

    def __enter__(self) -> None:
        if self.armed:
            self.previous = signal.signal(signal.SIGALRM, self._stop)
            signal.alarm(self.seconds)

    def __exit__(self, *exc: object) -> None:
        if self.armed:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self.previous)


def run_once(
    store: JobStore,
    analyse: Analyse,
    writer: ServerWriter | None = None,
    seconds: int = 0,
    workdir: Path | None = None,
) -> Job | None:
    """Claim and run one job. Returns the job, or None if the queue was empty."""
    job = store.claim()
    if job is None:
        return None
    started = time.monotonic()

    def progress(stage: str) -> None:
        store.set_stage(job.id, stage)

    analysis: Analysis | None = None
    try:
        with time_limit(seconds):
            analysis = analyse(job, progress)
            report = None
            if writer is not None and writer.has_room(store):
                progress("Writing and checking the report")
                try:
                    report = writer.write(analysis)
                except ModelError as error:
                    # The facts still stand; the visitor can write the report themselves.
                    log.warning("job %s: the model failed: %s", job.id, error)
    except SourceError as error:
        store.fail(job.id, str(error))
        log.info("job %s for %s failed: %s", job.id, job.repo, error)
    except JobTimeout as error:
        store.fail(job.id, f"{error}; try a smaller repo")
        log.info("job %s for %s timed out", job.id, job.repo)
    except Exception as error:  # noqa: BLE001 - a broken job must not stop the worker
        store.fail(job.id, "the analysis stopped with an internal error")
        log.exception("job %s for %s crashed: %s", job.id, job.repo, error)
    else:
        assert analysis is not None
        store.finish(
            job.id,
            analysis.checkout.commit,
            analysis.facts.model_dump_json(),
            report.model_dump_json() if report is not None else None,
            build_views(analysis).model_dump_json(),
        )
        log.info("job %s for %s done in %.1f s", job.id, job.repo, time.monotonic() - started)
    finally:
        # The facts and report are kept; the clone is not needed again.
        if workdir is not None:
            shutil.rmtree(workdir / job.repo.replace("/", "__"), ignore_errors=True)
    return store.get(job.id)


def run_forever(
    store: JobStore,
    analyse: Analyse,
    writer: ServerWriter | None = None,
    seconds: int = 0,
    workdir: Path | None = None,
    poll_seconds: float = 1.0,
    stop: threading.Event | None = None,
) -> None:
    while stop is None or not stop.is_set():
        if run_once(store, analyse, writer, seconds, workdir) is None:
            time.sleep(poll_seconds)
