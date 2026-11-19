"""The web API: queue a repo for analysis and fetch its facts.

    POST /api/jobs            {"repo": "owner/name" or a GitHub URL, "commit": optional}
    GET  /api/jobs/{id}       status, and the facts link once done
    GET  /api/jobs/{id}/facts the FactSet JSON
    GET  /api/health

The server never sees a model key: it only produces facts. The browser
sends the facts and the user's own key straight to the model provider,
then runs the verifier on the answer.

Only GitHub repos are accepted. A local path in a request is refused, so
the server cannot be pointed at its own files.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

from plumb import __version__
from plumb.server.jobs import Job, JobStore, Status
from plumb.source import parse_github

_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")


class JobRequest(BaseModel):
    repo: str = Field(min_length=3, max_length=200, examples=["encode/httpx"])
    commit: str | None = Field(default=None, examples=["7cff5f79bc78"])


class JobView(BaseModel):
    id: str
    repo: str
    commit: str | None
    status: Status
    created_at: datetime
    finished_at: datetime | None
    error: str | None
    facts_url: str | None
    queue_position: int | None = None


def _view(job: Job, waiting: int | None = None) -> JobView:
    return JobView(
        id=job.id,
        repo=job.repo,
        commit=job.commit,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        error=job.error,
        facts_url=f"/api/jobs/{job.id}/facts" if job.status is Status.DONE else None,
        queue_position=waiting if job.status is Status.QUEUED else None,
    )


def create_app(store: JobStore) -> FastAPI:
    app = FastAPI(title="Plumb", version=__version__, docs_url="/api/docs", redoc_url=None)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"ok": True, "version": __version__, "queued": store.waiting()}

    @app.post("/api/jobs", status_code=status.HTTP_202_ACCEPTED)
    def add_job(request: Annotated[JobRequest, Body()]) -> JobView:
        parsed = parse_github(request.repo.strip())
        if parsed is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "give a public GitHub repo as owner/name or https://github.com/owner/name",
            )
        commit = request.commit.lower() if request.commit else None
        if commit is not None and not _COMMIT.match(commit):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "commit must be a hex SHA")
        owner, name = parsed
        job = store.add(f"{owner}/{name}", commit)
        return _view(job, store.waiting())

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> JobView:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such job")
        return _view(job, store.waiting())

    @app.get("/api/jobs/{job_id}/facts")
    def get_facts(job_id: str) -> Response:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such job")
        if job.status is not Status.DONE or job.facts is None:
            raise HTTPException(status.HTTP_409_CONFLICT, f"job is {job.status.value}")
        return Response(job.facts, media_type="application/json")

    return app


def default_app(database: Path) -> FastAPI:
    return create_app(JobStore(database))
