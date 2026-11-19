from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient

from plumb.model import FactSet, RepoKind, RepoRef
from plumb.pipeline import Analysis
from plumb.server.app import create_app
from plumb.server.jobs import Job, JobStore, Status
from plumb.server.worker import run_once
from plumb.source import Checkout, SourceError


def api(store: JobStore) -> httpx.Client:
    return TestClient(create_app(store))  # an httpx client; typed as one for the checker


@pytest.fixture
def store(tmp_path: Path) -> JobStore:
    return JobStore(tmp_path / "jobs.sqlite")


class FakeAnalysis:
    def __init__(self, repo: str) -> None:
        owner, name = repo.split("/")
        self.checkout = Checkout(owner=owner, name=name, commit="abc1234", path=Path("."))
        self.facts = FactSet(
            repo=RepoRef(owner=owner, name=name, commit="abc1234"),
            kind=RepoKind.LIBRARY,
            facts=[],
        )


def fake_analyse(job: Job) -> Analysis:
    if job.repo == "o/broken":
        raise SourceError("repository not found")
    return cast(Analysis, FakeAnalysis(job.repo))


def test_queue_claim_and_finish(store: JobStore) -> None:
    first = store.add("o/a")
    second = store.add("o/b")
    assert store.add("o/a").id == first.id  # still queued: the same job
    assert store.waiting() == 2
    claimed = store.claim()
    assert claimed is not None and claimed.id == first.id and claimed.status is Status.RUNNING
    done = run_once(store, fake_analyse)
    assert done is not None and done.id == second.id and done.status is Status.DONE
    assert done.commit == "abc1234" and done.facts is not None
    assert store.claim() is None


def test_a_done_commit_is_not_analysed_again(store: JobStore) -> None:
    job = store.add("o/a", "abc1234")
    run_once(store, fake_analyse)
    assert store.add("o/a", "abc1234").id == job.id
    newest = store.add("o/a")
    assert newest.id != job.id  # asked for the newest commit, which may be another
    run_once(store, fake_analyse)
    assert store.add("o/a").id == newest.id  # finished just now: fresh enough
    short = store.add("o/a", "abc12")  # a short SHA matches either finished job
    assert short.status is Status.DONE and short.commit == "abc1234"
    hour_ago = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    store._db.execute("UPDATE jobs SET finished_at = ?", (hour_ago,))  # pyright: ignore[reportPrivateUsage]
    assert store.add("o/a").id != newest.id


def test_failures_are_recorded(store: JobStore) -> None:
    store.add("o/broken")
    job = run_once(store, fake_analyse)
    assert job is not None and job.status is Status.FAILED
    assert job.error == "repository not found"
    assert store.add("o/broken").id != job.id  # a failed job can be tried again


def test_a_stale_running_job_is_claimed_again(store: JobStore) -> None:
    job = store.add("o/a")
    store.claim()
    old = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    store._db.execute("UPDATE jobs SET started_at = ?", (old,))  # pyright: ignore[reportPrivateUsage]
    again = store.claim()
    assert again is not None and again.id == job.id


def test_api(store: JobStore) -> None:
    client = api(store)
    assert client.get("/api/health").json()["ok"] is True

    created = client.post("/api/jobs", json={"repo": "https://github.com/Encode/httpx"})
    assert created.status_code == 202
    body = created.json()
    assert body["repo"] == "Encode/httpx" and body["status"] == "queued"
    assert body["queue_position"] == 1 and body["facts_url"] is None
    assert client.get(f"/api/jobs/{body['id']}/facts").status_code == 409

    run_once(store, lambda job: cast(Analysis, FakeAnalysis(job.repo)))
    done = client.get(f"/api/jobs/{body['id']}").json()
    assert done["status"] == "done" and done["facts_url"] == f"/api/jobs/{body['id']}/facts"
    facts = client.get(done["facts_url"]).json()
    assert facts["repo"]["name"] == "httpx" and facts["kind"] == "library"


@pytest.mark.parametrize("repo", ["/etc", "../secrets", "C:\\Projects\\Plumb", "not a repo"])
def test_api_refuses_anything_but_a_github_repo(store: JobStore, repo: str) -> None:
    client = api(store)
    assert client.post("/api/jobs", json={"repo": repo}).status_code == 422
    assert store.waiting() == 0


def test_api_checks_the_commit(store: JobStore) -> None:
    client = api(store)
    response = client.post("/api/jobs", json={"repo": "o/r", "commit": "main; rm -rf /"})
    assert response.status_code == 422
    assert client.get("/api/jobs/nope").status_code == 404
