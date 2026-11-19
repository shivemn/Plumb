"""Run queued analysis jobs, one at a time."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

from plumb.github import GitHubClient
from plumb.pipeline import Analysis, analyse_repo
from plumb.server.jobs import Job, JobStore
from plumb.source import Limits, SourceError

log = logging.getLogger("plumb.worker")

Analyse = Callable[[Job], Analysis]


def make_analyser(
    workdir: Path, limits: Limits | None = None, github: GitHubClient | None = None
) -> Analyse:
    def analyse(job: Job) -> Analysis:
        # Always a URL: "owner/name" could also name a folder on the server.
        url = f"https://github.com/{job.repo}"
        return analyse_repo(url, workdir, commit=job.commit, limits=limits, github=github)

    return analyse


def run_once(store: JobStore, analyse: Analyse) -> Job | None:
    """Claim and run one job. Returns the job, or None if the queue was empty."""
    job = store.claim()
    if job is None:
        return None
    started = time.monotonic()
    try:
        analysis = analyse(job)
    except SourceError as error:
        store.fail(job.id, str(error))
        log.info("job %s for %s failed: %s", job.id, job.repo, error)
    except Exception as error:  # noqa: BLE001 - a broken job must not stop the worker
        store.fail(job.id, "the analysis stopped with an internal error")
        log.exception("job %s for %s crashed: %s", job.id, job.repo, error)
    else:
        store.finish(job.id, analysis.checkout.commit, analysis.facts.model_dump_json())
        log.info("job %s for %s done in %.1f s", job.id, job.repo, time.monotonic() - started)
    return store.get(job.id)


def run_forever(store: JobStore, analyse: Analyse, poll_seconds: float = 1.0) -> None:
    while True:
        if run_once(store, analyse) is None:
            time.sleep(poll_seconds)
