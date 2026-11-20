"""A queue of analysis jobs, kept in a database table.

The web API adds a job; a worker claims the oldest queued one, runs the
analysis and stores the facts. Claiming is one UPDATE, so two workers never
take the same job. A repo already analysed at the same commit is answered
from the table instead of being analysed again.

This uses SQLite, which is enough for one machine. The SQL is kept to what
PostgreSQL also accepts, so moving the table there later is a change of
driver, not of design.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    requested TEXT,
    commit_sha TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error TEXT,
    facts TEXT,
    stage TEXT,
    report TEXT,
    client TEXT,
    views TEXT
);
CREATE INDEX IF NOT EXISTS jobs_queue ON jobs (status, created_at);
CREATE INDEX IF NOT EXISTS jobs_repo ON jobs (repo, commit_sha);
"""
# Columns added after the first version, for tables made before them.
_LATER_COLUMNS = ("stage", "report", "client", "views")

# A running job not finished in this time is taken to be from a worker that died.
STALE_AFTER = timedelta(minutes=15)
# A request without a commit reuses an analysis of the newest commit this recent.
FRESH_FOR = timedelta(hours=1)


class Status(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class Job:
    id: str
    repo: str
    commit: str | None
    status: Status
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    facts: str | None  # FactSet JSON, once done
    stage: str | None = None  # what the worker is doing, for the progress view
    report: str | None = None  # Report JSON, when the server wrote one
    views: str | None = None  # Views JSON: the diagrams and tables, written without a model


def _now() -> datetime:
    return datetime.now(UTC)


def _time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        repo=row["repo"],
        commit=row["commit_sha"],
        status=Status(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        started_at=_time(row["started_at"]),
        finished_at=_time(row["finished_at"]),
        error=row["error"],
        facts=row["facts"],
        stage=row["stage"],
        report=row["report"],
        views=row["views"],
    )


class _Rows:
    """Rows read while holding the lock, so no cursor is shared between threads."""

    def __init__(self, rows: list[sqlite3.Row]) -> None:
        self.rows = rows

    def fetchone(self) -> sqlite3.Row | None:
        return self.rows[0] if self.rows else None


class JobStore:
    def __init__(self, path: Path | str) -> None:
        if isinstance(path, Path):
            path.parent.mkdir(parents=True, exist_ok=True)
        # One connection, shared by the web server's threads and the worker
        # thread; the lock keeps them from using it at the same time.
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)
        have = {row[1] for row in self._db.execute("PRAGMA table_info(jobs)")}
        for column in _LATER_COLUMNS:
            if column not in have:
                self._db.execute(f"ALTER TABLE jobs ADD COLUMN {column} TEXT")

    def _run(self, sql: str, args: tuple[object, ...] = ()) -> _Rows:
        with self._lock:
            return _Rows(self._db.execute(sql, args).fetchall())

    def add(self, repo: str, commit: str | None = None, client: str | None = None) -> Job:
        """Queue a job, or return one that already answers the same request.

        With a commit, any job that ran or will run at that commit answers it.
        Without one, a queued or running job does, or a finished one less
        than FRESH_FOR old, since the newest commit may have moved since.
        """
        failed = Status.FAILED.value
        if commit is not None:
            row = self._run(
                "SELECT * FROM jobs WHERE repo = ? AND status != ? AND "
                "(requested = ? OR commit_sha LIKE ? || '%') ORDER BY created_at DESC LIMIT 1",
                (repo, failed, commit, commit),
            ).fetchone()
            if row is not None:
                return _job(row)
        else:
            row = self._run(
                "SELECT * FROM jobs WHERE repo = ? AND status != ? AND requested IS NULL "
                "ORDER BY created_at DESC LIMIT 1",
                (repo, failed),
            ).fetchone()
            if row is not None:
                job = _job(row)
                finished = job.finished_at
                if finished is None or _now() - finished < FRESH_FOR:
                    return job
        job_id = uuid.uuid4().hex
        self._run(
            "INSERT INTO jobs (id, repo, requested, commit_sha, status, created_at, client) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, repo, commit, commit, Status.QUEUED.value, _now().isoformat(), client),
        )
        job = self.get(job_id)
        assert job is not None
        return job

    def get(self, job_id: str) -> Job | None:
        row = self._run("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _job(row) if row is not None else None

    def claim(self) -> Job | None:
        """Take the oldest queued job, or one whose worker stopped answering."""
        now = _now()
        stale = (now - STALE_AFTER).isoformat()
        row = self._run(
            "UPDATE jobs SET status = ?, started_at = ? WHERE id = ("
            "  SELECT id FROM jobs WHERE status = ? OR (status = ? AND started_at < ?)"
            "  ORDER BY created_at LIMIT 1"
            ") RETURNING *",
            (
                Status.RUNNING.value,
                now.isoformat(),
                Status.QUEUED.value,
                Status.RUNNING.value,
                stale,
            ),
        ).fetchone()
        return _job(row) if row is not None else None

    def finish(
        self,
        job_id: str,
        commit: str,
        facts: str,
        report: str | None = None,
        views: str | None = None,
    ) -> None:
        self._run(
            "UPDATE jobs SET status = ?, finished_at = ?, commit_sha = ?, facts = ?, report = ?, "
            "views = ?, stage = NULL WHERE id = ?",
            (Status.DONE.value, _now().isoformat(), commit, facts, report, views, job_id),
        )

    def set_stage(self, job_id: str, stage: str) -> None:
        self._run("UPDATE jobs SET stage = ? WHERE id = ?", (stage, job_id))

    def reports_written_since(self, since: datetime) -> int:
        """Reports the server's own model wrote, for its daily cap."""
        row = self._run(
            "SELECT COUNT(*) FROM jobs WHERE report IS NOT NULL AND finished_at >= ?",
            (since.isoformat(),),
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def requests_from(self, client: str, since: datetime) -> int:
        row = self._run(
            "SELECT COUNT(*) FROM jobs WHERE client = ? AND created_at >= ?",
            (client, since.isoformat()),
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def latest_report(self, repo: str, commit: str) -> Job | None:
        """A finished job with a written report for this repo at this commit."""
        row = self._run(
            "SELECT * FROM jobs WHERE repo = ? AND commit_sha = ? AND report IS NOT NULL "
            "ORDER BY finished_at DESC LIMIT 1",
            (repo, commit),
        ).fetchone()
        return _job(row) if row is not None else None

    def fail(self, job_id: str, error: str) -> None:
        self._run(
            "UPDATE jobs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
            (Status.FAILED.value, _now().isoformat(), error, job_id),
        )

    def waiting(self) -> int:
        row = self._run(
            "SELECT COUNT(*) FROM jobs WHERE status = ?", (Status.QUEUED.value,)
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def close(self) -> None:
        self._db.close()
