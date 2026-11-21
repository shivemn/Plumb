from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient

from plumb.model import FactSet, RepoKind, RepoRef, Report
from plumb.pipeline import Analysis, analyse_repo
from plumb.server import worker
from plumb.server.app import Settings, create_app
from plumb.server.config import (
    server_settings,
    server_writer,
    worker_max_files,
    worker_seconds,
)
from plumb.server.jobs import Job, JobStore, Status
from plumb.server.worker import JobTimeout, ServerWriter, run_once, time_limit
from plumb.source import Checkout, SourceError
from plumb.writer.models import ModelError
from tests.conftest import RepoBuilder
from tests.test_facts import sample_repo
from tests.test_report import FakeClient


def api(store: JobStore, settings: Settings | None = None) -> httpx.Client:
    # An httpx client; typed as one for the checker.
    return TestClient(create_app(store, settings))


def api_with_worker(store: JobStore, alive: bool) -> httpx.Client:
    return TestClient(create_app(store, None, lambda: alive))


@pytest.fixture
def store(tmp_path: Path) -> Iterator[JobStore]:
    jobs = JobStore(tmp_path / "jobs.sqlite")
    yield jobs
    jobs.close()


class FakeAnalysis:
    def __init__(self, repo: str) -> None:
        owner, name = repo.split("/")
        self.checkout = Checkout(owner=owner, name=name, commit="abc1234", path=Path("."))
        self.facts = FactSet(
            repo=RepoRef(owner=owner, name=name, commit="abc1234"),
            kind=RepoKind.LIBRARY,
            facts=[],
        )


class _NoViews:
    def model_dump_json(self) -> str:
        return ""  # stored as "no views"


@pytest.fixture(autouse=True)
def views_for_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fake analysis has nothing to draw; a real one gets real views."""
    real = worker.build_views

    def views(analysis: Analysis) -> object:
        return _NoViews() if isinstance(analysis, FakeAnalysis) else real(analysis)

    monkeypatch.setattr(worker, "build_views", views)


def fake_analyse(job: Job, progress: Callable[[str], None]) -> Analysis:
    progress("Fetching the repo")
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
    assert done.stage is None and done.report is None  # no writer: facts alone
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


def test_a_crash_does_not_leak_its_message(store: JobStore) -> None:
    def crash(job: Job, progress: Callable[[str], None]) -> Analysis:
        raise RuntimeError("/srv/plumb/secret path")

    store.add("o/a")
    job = run_once(store, crash)
    assert job is not None and job.status is Status.FAILED
    assert job.error == "the analysis stopped with an internal error"


def test_a_stale_running_job_is_claimed_again(store: JobStore) -> None:
    job = store.add("o/a")
    store.claim()
    old = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    store._db.execute("UPDATE jobs SET started_at = ?", (old,))  # pyright: ignore[reportPrivateUsage]
    again = store.claim()
    assert again is not None and again.id == job.id


def test_the_stage_is_shown_while_running(store: JobStore) -> None:
    seen: list[str | None] = []

    def watch(job: Job, progress: Callable[[str], None]) -> Analysis:
        progress("Reading files and history")
        current = store.get(job.id)
        seen.append(current.stage if current else None)
        return cast(Analysis, FakeAnalysis(job.repo))

    store.add("o/a")
    done = run_once(store, watch)
    assert seen == ["Reading files and history"]
    assert done is not None and done.stage is None


def test_the_clone_is_deleted_after_the_job(store: JobStore, tmp_path: Path) -> None:
    workdir = tmp_path / "clones"

    def clone(job: Job, progress: Callable[[str], None]) -> Analysis:
        folder = workdir / "o__a"
        folder.mkdir(parents=True)
        (folder / "big.bin").write_bytes(b"x" * 100)
        if job.commit == "dead123":
            raise SourceError("no such commit")
        return cast(Analysis, FakeAnalysis(job.repo))

    store.add("o/a")
    run_once(store, clone, workdir=workdir)
    assert not (workdir / "o__a").exists()
    store.add("o/a", "dead123")
    failed = run_once(store, clone, workdir=workdir)
    assert failed is not None and failed.status is Status.FAILED
    assert not (workdir / "o__a").exists()  # also after a failure


def test_a_job_past_its_time_limit_fails(store: JobStore) -> None:
    def slow(job: Job, progress: Callable[[str], None]) -> Analysis:
        time.sleep(3)
        return cast(Analysis, FakeAnalysis(job.repo))

    store.add("o/a")
    job = run_once(store, slow, seconds=1)
    assert job is not None and job.status is Status.FAILED
    assert job.error is not None and "longer than 1 seconds" in job.error
    with pytest.raises(JobTimeout), time_limit(1):
        time.sleep(3)
    with time_limit(0):  # no limit
        pass


class StubWriter(ServerWriter):
    def __init__(self, daily_reports: int, fail: bool = False) -> None:
        super().__init__(FakeClient(), None, daily_reports)
        self.fail = fail
        self.written = 0

    def write(self, analysis: Analysis) -> Report:
        if self.fail:
            raise ModelError("rate limited")
        self.written += 1
        facts = analysis.facts
        return Report(
            repo=facts.repo, kind=facts.kind, model="fake:test", sections=[], removed=[], facts=[]
        )


def test_the_server_writes_reports_up_to_its_daily_cap(store: JobStore) -> None:
    writer = StubWriter(daily_reports=2)
    for name in ("a", "b", "c"):
        store.add(f"o/{name}")
    jobs = [run_once(store, fake_analyse, writer) for _ in range(3)]
    assert [j.report is not None for j in jobs if j] == [True, True, False]
    assert writer.written == 2
    assert all(j is not None and j.status is Status.DONE for j in jobs)
    since = datetime.now(UTC) - timedelta(days=1)
    assert store.reports_written_since(since) == 2


def test_a_model_failure_still_leaves_the_facts(store: JobStore) -> None:
    store.add("o/a")
    job = run_once(store, fake_analyse, StubWriter(daily_reports=5, fail=True))
    assert job is not None and job.status is Status.DONE
    assert job.facts is not None and job.report is None
    assert job.note is not None and "rate limited" in job.note
    assert api(store).get(f"/api/jobs/{job.id}").json()["note"] == job.note


def test_api(store: JobStore) -> None:
    client = api(store)
    health = client.get("/api/health").json()
    assert health["ok"] is True and health["server_reports_left_today"] == 0
    assert health["worker_running"] is None
    dead = api_with_worker(store, alive=False)
    assert dead.get("/api/health").json()["worker_running"] is False

    created = client.post("/api/jobs", json={"repo": "https://github.com/Encode/httpx"})
    assert created.status_code == 202
    body = created.json()
    assert body["repo"] == "Encode/httpx" and body["status"] == "queued"
    assert body["queue_position"] == 1 and body["facts_url"] is None
    assert client.get(f"/api/jobs/{body['id']}/facts").status_code == 409

    run_once(store, fake_analyse)
    done = client.get(f"/api/jobs/{body['id']}").json()
    assert done["status"] == "done" and done["facts_url"] == f"/api/jobs/{body['id']}/facts"
    assert done["report_url"] is None and done["tasks_url"] == f"/api/jobs/{body['id']}/tasks"
    facts = client.get(done["facts_url"]).json()
    assert facts["repo"]["name"] == "httpx" and facts["kind"] == "library"
    assert client.get(f"/api/jobs/{body['id']}/report").status_code == 404


def test_api_serves_the_report_the_server_wrote(store: JobStore) -> None:
    client = api(store, Settings(server_model="fake:test", daily_reports=3))
    job = client.post("/api/jobs", json={"repo": "o/a"}).json()
    run_once(store, fake_analyse, StubWriter(daily_reports=3))
    done = client.get(f"/api/jobs/{job['id']}").json()
    assert done["report_url"] == f"/api/jobs/{job['id']}/report" and done["tasks_url"] is None
    assert client.get(done["report_url"]).json()["model"] == "fake:test"
    assert client.get("/api/health").json()["server_reports_left_today"] == 2


def test_api_limits_each_visitor(store: JobStore) -> None:
    client = api(store, Settings(jobs_per_hour=2))
    assert client.post("/api/jobs", json={"repo": "o/a"}).status_code == 202
    assert client.post("/api/jobs", json={"repo": "o/b"}).status_code == 202
    refused = client.post("/api/jobs", json={"repo": "o/c"})
    assert refused.status_code == 429 and "2 repos an hour" in refused.json()["detail"]


def test_api_reads_the_visitor_behind_a_proxy(store: JobStore) -> None:
    client = api(store, Settings(jobs_per_hour=1, trust_proxy=True))
    first = {"x-forwarded-for": "203.0.113.1"}
    second = {"x-forwarded-for": "203.0.113.2, 10.0.0.1"}
    assert client.post("/api/jobs", json={"repo": "o/a"}, headers=first).status_code == 202
    assert client.post("/api/jobs", json={"repo": "o/b"}, headers=first).status_code == 429
    assert client.post("/api/jobs", json={"repo": "o/b"}, headers=second).status_code == 202
    raw = store._run("SELECT client FROM jobs").rows  # pyright: ignore[reportPrivateUsage]
    assert all("203.0.113" not in row[0] for row in raw)  # addresses are not stored


def test_api_prefers_the_header_the_proxy_sets(store: JobStore) -> None:
    settings = Settings(jobs_per_hour=1, trust_proxy=True, client_ip_header="cf-connecting-ip")
    client = api(store, settings)
    one = {"cf-connecting-ip": "203.0.113.1", "x-forwarded-for": "198.51.100.1"}
    forged = {"cf-connecting-ip": "203.0.113.1", "x-forwarded-for": "198.51.100.2"}
    assert client.post("/api/jobs", json={"repo": "o/a"}, headers=one).status_code == 202
    # A new X-Forwarded-For does not make a new visitor.
    assert client.post("/api/jobs", json={"repo": "o/b"}, headers=forged).status_code == 429


def test_api_refuses_when_the_queue_is_full(store: JobStore) -> None:
    client = api(store, Settings(max_waiting=1, jobs_per_hour=10))
    assert client.post("/api/jobs", json={"repo": "o/a"}).status_code == 202
    assert client.post("/api/jobs", json={"repo": "o/b"}).status_code == 503


def test_api_sends_cors_headers_to_the_site_only(store: JobStore) -> None:
    client = api(store)
    site = client.get("/api/health", headers={"origin": "https://shivemn.github.io"})
    assert site.headers["access-control-allow-origin"] == "https://shivemn.github.io"
    other = client.get("/api/health", headers={"origin": "https://example.com"})
    assert "access-control-allow-origin" not in other.headers


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


def test_a_visitor_writes_the_report_with_their_own_model(
    store: JobStore, make_repo: Callable[[str], RepoBuilder], tmp_path: Path
) -> None:
    repo = sample_repo(make_repo)

    def analyse(job: Job, progress: Callable[[str], None]) -> Analysis:
        return analyse_repo(str(repo.path), tmp_path / "w", progress=progress)

    client = api(store)
    job = client.post("/api/jobs", json={"repo": "o/shop"}).json()
    run_once(store, analyse)
    tasks = client.get(f"/api/jobs/{job['id']}/tasks").json()
    assert tasks["tasks"] and all(t["system"] and t["prompt"] for t in tasks["tasks"])

    # What the browser does: ask the model, post back only its answers.
    model = FakeClient()
    answers = [
        {"section": t["section"], "text": model.complete(t["system"], t["prompt"])}
        for t in tasks["tasks"]
    ]
    answers.append({"section": tasks["tasks"][0]["section"] + "_x", "text": "ignored"})
    response = client.post(
        f"/api/jobs/{job['id']}/verify",
        json={"model": "openrouter:some/model:free", "nonce": tasks["nonce"], "answers": answers},
    )
    assert response.status_code == 200, response.text
    report = Report.model_validate_json(response.text)
    kept = [c.text for s in report.sections for c in s.claims]
    assert "This section has facts." in kept
    assert all("secret.py" not in text for text in kept)  # the invented path is dropped
    assert report.model == "openrouter:some/model:free" and report.views is not None
    views = client.get(f"/api/jobs/{job['id']}/views").json()
    assert views == report.views.model_dump(mode="json")
    assert store.get(job["id"]) is not None and store.get(job["id"]).report is None  # pyright: ignore[reportOptionalMemberAccess]


def test_verify_refuses_a_bad_model_name_or_nonce(store: JobStore) -> None:
    client = api(store)
    job = client.post("/api/jobs", json={"repo": "o/a"}).json()
    run_once(store, fake_analyse)
    url = f"/api/jobs/{job['id']}/verify"
    good: dict[str, object] = {"model": "openrouter:x/y", "nonce": "0" * 16, "answers": []}
    assert client.post(url, json=good).status_code == 200
    assert client.post(url, json={**good, "model": "<script>"}).status_code == 422
    assert client.post(url, json={**good, "nonce": "zz"}).status_code == 422
    unreadable = {**good, "answers": [{"section": "overview", "text": "not json"}]}
    body = json.loads(client.post(url, json=unreadable).text)
    assert body["sections"] == [] or all(not s["claims"] for s in body["sections"])


def test_settings_come_from_the_environment(tmp_path: Path) -> None:
    env = {
        "PLUMB_ALLOWED_ORIGINS": "https://a.example, http://localhost:8000,",
        "PLUMB_JOBS_PER_HOUR": "3",
        "PLUMB_MAX_WAITING": "oops",
        "PLUMB_TRUST_PROXY": "1",
        "PLUMB_JOB_SECONDS": "60",
        "PLUMB_CLIENT_IP_HEADER": " CF-Connecting-IP ",
        "PLUMB_MAX_FILES": "4000",
    }
    settings = server_settings(env)
    assert settings.allowed_origins == ("https://a.example", "http://localhost:8000")
    assert settings.jobs_per_hour == 3 and settings.max_waiting == 25 and settings.trust_proxy
    assert settings.server_model is None and worker_seconds(env) == 60
    assert settings.client_ip_header == "cf-connecting-ip"
    assert worker_max_files(env, 20_000) == 4000 and worker_max_files({}, 20_000) == 20_000
    assert server_writer(env, tmp_path / "cache") is None  # no model
    no_key = {"PLUMB_MODEL": "openrouter:x/y:free"}
    assert server_writer(no_key, tmp_path / "cache") is None  # no key
    with_key = {**no_key, "OPENROUTER_API_KEY": "k", "PLUMB_DAILY_REPORTS": "4"}
    writer = server_writer(with_key, tmp_path / "cache")
    assert writer is not None and writer.daily_reports == 4
    assert writer.client.name == "openrouter:x/y:free"


def test_an_old_table_gains_the_new_columns(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "old.sqlite"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE jobs (id TEXT PRIMARY KEY, repo TEXT NOT NULL, requested TEXT, "
        "commit_sha TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT, "
        "finished_at TEXT, error TEXT, facts TEXT)"
    )
    db.commit()
    db.close()
    store = JobStore(path)
    job = store.add("o/a", client="someone")
    store.set_stage(job.id, "Fetching the repo")
    assert store.get(job.id) is not None
    store.close()


def test_two_processes_can_open_the_table_at_once(tmp_path: Path) -> None:
    import multiprocessing

    path = tmp_path / "shared.sqlite"
    context = multiprocessing.get_context("spawn")
    with context.Pool(4) as pool:
        counts = pool.map(_open_and_add, [str(path)] * 8)
    assert counts == [1] * 8
    store = JobStore(path)
    assert store.waiting() == 8
    store.close()


def _open_and_add(path: str) -> int:
    store = JobStore(Path(path))
    job = store.add(f"o/{uuid.uuid4().hex[:8]}")
    store.close()
    return 1 if job.status is Status.QUEUED else 0


def test_opening_waits_out_a_lock_held_by_another_process(tmp_path: Path) -> None:
    import sqlite3
    import threading

    path = tmp_path / "busy.sqlite"
    holder = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    holder.execute("BEGIN EXCLUSIVE")
    release = threading.Timer(1.0, lambda: holder.execute("COMMIT"))
    release.start()
    store = JobStore(path)  # waits, or tries again, until the lock is gone
    assert store.waiting() == 0
    store.close()
    release.join()
    holder.close()
    again = JobStore(path)  # already in WAL: not switched a second time
    assert again._db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"  # pyright: ignore[reportPrivateUsage]
    again.close()
