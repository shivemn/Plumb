"""The web API: queue a repo, follow its progress, and fetch its report.

    POST /api/jobs                {"repo": "owner/name" or a GitHub URL, "commit": optional}
    GET  /api/jobs/{id}           status, the step it is on, and links once done
    GET  /api/jobs/{id}/report    the report, when the server's model wrote one
    GET  /api/jobs/{id}/facts     the facts
    GET  /api/jobs/{id}/views     the diagrams and tables, which need no model
    GET  /api/jobs/{id}/tasks     the prompts, for a visitor writing the report with their own key
    POST /api/jobs/{id}/verify    the visitor's model answers in; the checked report out
    GET  /api/health

A visitor's own key never reaches this server. Their browser fetches the
prompts, sends them straight to the model provider, and posts back only the
model's answers, which are checked here against the facts like any other.

Only GitHub repos are accepted. A local path in a request is refused, so
the server cannot be pointed at its own files. Each visitor may queue a
limited number of jobs an hour, and the queue as a whole has a size limit.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Body, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from plumb import __version__
from plumb.model import FactSet, Views
from plumb.server.jobs import Job, JobStore, Status
from plumb.source import parse_github
from plumb.verify import verify
from plumb.views import today
from plumb.writer.plan import plan_report
from plumb.writer.write import Draft, parse_answer

_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
_MODEL = re.compile(r"^[a-z]+:[\w./:@-]{1,120}$")


@dataclass(frozen=True)
class Settings:
    allowed_origins: tuple[str, ...] = ("https://shivemn.github.io",)
    jobs_per_hour: int = 10  # per visitor
    max_waiting: int = 25  # queued jobs, for everyone
    trust_proxy: bool = False  # read the visitor's address from X-Forwarded-For
    # A header the host's proxy sets to the visitor's address and visitors
    # cannot set themselves, such as cf-connecting-ip behind Cloudflare.
    # X-Forwarded-For can be forged where the proxy only appends to it.
    client_ip_header: str | None = None
    salt: str = field(default_factory=lambda: secrets.token_hex(16))  # visitor addresses are hashed
    server_model: str | None = None  # shown on the health page
    daily_reports: int = 0


class JobRequest(BaseModel):
    repo: str = Field(min_length=3, max_length=200, examples=["encode/httpx"])
    commit: str | None = Field(default=None, examples=["7cff5f79bc78"])


class JobView(BaseModel):
    id: str
    repo: str
    commit: str | None
    status: Status
    stage: str | None
    created_at: datetime
    finished_at: datetime | None
    error: str | None
    facts_url: str | None
    report_url: str | None
    tasks_url: str | None
    note: str | None = None  # why there is no report, when the server's model failed
    queue_position: int | None = None


class Answer(BaseModel):
    section: str = Field(pattern=r"^[a-z_]+$")
    text: str = Field(max_length=20_000)


class VerifyRequest(BaseModel):
    model: str = Field(description="provider:model that wrote the answers")
    nonce: str = Field(pattern=r"^[0-9a-f]{16}$")
    answers: list[Answer] = Field(max_length=12)


def _view(job: Job, waiting: int | None = None) -> JobView:
    done = job.status is Status.DONE
    base = f"/api/jobs/{job.id}"
    return JobView(
        id=job.id,
        repo=job.repo,
        commit=job.commit,
        status=job.status,
        stage=job.stage,
        created_at=job.created_at,
        finished_at=job.finished_at,
        error=job.error,
        facts_url=f"{base}/facts" if done else None,
        report_url=f"{base}/report" if done and job.report else None,
        tasks_url=f"{base}/tasks" if done and not job.report else None,
        queue_position=waiting if job.status is Status.QUEUED else None,
        note=job.note,
    )


def create_app(store: JobStore, settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    app = FastAPI(title="Plumb", version=__version__, docs_url="/api/docs", redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )

    def visitor(request: Request) -> str:
        address = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for")
        set_by_proxy = request.headers.get(config.client_ip_header or "")
        if config.client_ip_header and set_by_proxy:
            address = set_by_proxy.strip()
        elif config.trust_proxy and forwarded:
            address = forwarded.split(",")[0].strip()
        return hashlib.sha256(f"{config.salt}:{address}".encode()).hexdigest()[:24]

    def finished(job_id: str) -> Job:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such job")
        if job.status is not Status.DONE or job.facts is None:
            raise HTTPException(status.HTTP_409_CONFLICT, f"the job is {job.status.value}")
        return job

    @app.get("/api/health")
    def health() -> dict[str, object]:
        since = datetime.now(UTC) - timedelta(days=1)
        left = max(0, config.daily_reports - store.reports_written_since(since))
        return {
            "ok": True,
            "version": __version__,
            "queued": store.waiting(),
            "server_model": config.server_model,
            "server_reports_left_today": left if config.server_model else 0,
        }

    @app.post("/api/jobs", status_code=status.HTTP_202_ACCEPTED)
    def add_job(request: Annotated[JobRequest, Body()], raw: Request) -> JobView:
        parsed = parse_github(request.repo.strip())
        if parsed is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "give a public GitHub repo as owner/name or https://github.com/owner/name",
            )
        commit = request.commit.lower() if request.commit else None
        if commit is not None and not _COMMIT.match(commit):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "commit must be a hex SHA")
        who = visitor(raw)
        hour_ago = datetime.now(UTC) - timedelta(hours=1)
        if store.requests_from(who, hour_ago) >= config.jobs_per_hour:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"at most {config.jobs_per_hour} repos an hour from one address; try again later",
            )
        if store.waiting() >= config.max_waiting:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "the queue is full; try again in a few minutes"
            )
        owner, name = parsed
        job = store.add(f"{owner}/{name}", commit, client=who)
        return _view(job, store.waiting())

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> JobView:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such job")
        return _view(job, store.waiting())

    @app.get("/api/jobs/{job_id}/facts")
    def get_facts(job_id: str) -> Response:
        return Response(finished(job_id).facts, media_type="application/json")

    @app.get("/api/jobs/{job_id}/views")
    def get_views(job_id: str) -> Response:
        job = finished(job_id)
        if not job.views:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no views for this job")
        return Response(job.views, media_type="application/json")

    @app.get("/api/jobs/{job_id}/report")
    def get_report(job_id: str) -> Response:
        job = finished(job_id)
        if job.report is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no report was written for this job")
        return Response(job.report, media_type="application/json")

    @app.get("/api/jobs/{job_id}/tasks")
    def get_tasks(job_id: str) -> dict[str, object]:
        facts = FactSet.model_validate_json(finished(job_id).facts or "{}")
        nonce = secrets.token_hex(8)
        tasks = plan_report(facts, nonce=nonce)
        return {
            "nonce": nonce,
            "tasks": [
                {
                    "section": t.section.id,
                    "title": t.section.title,
                    "system": t.system,
                    "prompt": t.prompt,
                    "estimated_tokens": t.estimated_tokens,
                }
                for t in tasks
            ],
        }

    @app.post("/api/jobs/{job_id}/verify")
    def verify_answers(job_id: str, request: Annotated[VerifyRequest, Body()]) -> Response:
        job = finished(job_id)
        if not _MODEL.match(request.model):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "model must be provider:model"
            )
        facts = FactSet.model_validate_json(job.facts or "{}")
        answers = {a.section: a.text for a in request.answers}
        drafts: list[Draft] = []
        for task in plan_report(facts, nonce=request.nonce):
            text = answers.get(task.section.id)
            if text is None:
                continue
            try:
                drafts.append(Draft(task, parse_answer(text).claims))
            except ValueError as error:
                drafts.append(Draft(task, [], f"the model's answer could not be read: {error}"))
        report = verify(drafts, facts, request.model)
        views = Views.model_validate_json(job.views) if job.views else None
        report = report.model_copy(update={"views": views, "written_at": today()})
        # Not stored: it was written by the visitor's model, so it is theirs alone.
        return Response(report.model_dump_json(), media_type="application/json")

    return app
