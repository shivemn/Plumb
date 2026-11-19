"""Read issues and pull requests from GitHub's REST API.

Works without a token for public repos, at GitHub's limit of 60 requests an
hour per address; set GITHUB_TOKEN to raise that to 5,000. Answers are kept
on disk for a day, so running Plumb twice on a repo costs no requests the
second time. The token is only ever sent to api.github.com.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

import httpx

API = "https://api.github.com"
CACHE_SECONDS = 24 * 60 * 60


class GitHubError(Exception):
    """GitHub could not be read. The message says why and what to do."""


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    labels: tuple[str, ...]
    created_at: datetime
    comments: int
    body: str


@dataclass(frozen=True)
class PullRequest:
    number: int
    title: str
    created_at: datetime
    merged_at: datetime | None


@dataclass(frozen=True)
class Review:
    submitted_at: datetime
    author: str


def _time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [
        cast("dict[str, object]", v) for v in cast("list[object]", value) if isinstance(v, dict)
    ]


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        cache_dir: Path | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(
            base_url=API, headers=headers, timeout=20, transport=transport, follow_redirects=True
        )
        self._cache = cache_dir
        self.requests = 0  # sent to GitHub, not answered from the cache

    def get(self, path: str, params: dict[str, str | int] | None = None) -> object:
        params = params or {}
        key = hashlib.sha256(json.dumps([path, sorted(params.items())]).encode()).hexdigest()
        cached = self._cache / f"{key}.json" if self._cache else None
        if cached and cached.exists() and time.time() - cached.stat().st_mtime < CACHE_SECONDS:
            return json.loads(cached.read_text(encoding="utf-8"))
        try:
            response = self._http.get(path, params=params)
        except httpx.HTTPError as error:
            raise GitHubError(f"could not reach GitHub: {error}") from error
        self.requests += 1
        if response.status_code == 404:
            raise GitHubError(f"{path} was not found: the repo may be private or renamed")
        if (
            response.status_code in (403, 429)
            and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GitHubError(
                "GitHub's hourly request limit was reached; set GITHUB_TOKEN to raise it"
            )
        if response.status_code >= 400:
            raise GitHubError(f"GitHub answered {response.status_code} for {path}")
        data: object = response.json()
        if cached:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(data), encoding="utf-8")
        return data

    def issues(self, owner: str, name: str, *, labels: str = "", limit: int = 50) -> list[Issue]:
        """Open issues, newest first. Pull requests, which the API mixes in, are left out."""
        params: dict[str, str | int] = {"state": "open", "per_page": min(limit, 100)}
        if labels:
            params["labels"] = labels
        found: list[Issue] = []
        for item in _dicts(self.get(f"/repos/{owner}/{name}/issues", params)):
            created = _time(item.get("created_at"))
            if "pull_request" in item or created is None:
                continue
            found.append(
                Issue(
                    number=int(cast("int", item["number"])),
                    title=str(item.get("title") or ""),
                    labels=tuple(
                        str(label.get("name", "")) for label in _dicts(item.get("labels"))
                    ),
                    created_at=created,
                    comments=int(cast("int", item.get("comments") or 0)),
                    body=str(item.get("body") or ""),
                )
            )
        return found[:limit]

    def pull_requests(self, owner: str, name: str, *, limit: int = 30) -> list[PullRequest]:
        """Closed pull requests, most recently updated first."""
        params: dict[str, str | int] = {
            "state": "closed",
            "sort": "updated",
            "direction": "desc",
            "per_page": min(limit, 100),
        }
        found: list[PullRequest] = []
        for item in _dicts(self.get(f"/repos/{owner}/{name}/pulls", params)):
            created = _time(item.get("created_at"))
            if created is None:
                continue
            found.append(
                PullRequest(
                    number=int(cast("int", item["number"])),
                    title=str(item.get("title") or ""),
                    created_at=created,
                    merged_at=_time(item.get("merged_at")),
                )
            )
        return found[:limit]

    def reviews(self, owner: str, name: str, number: int) -> list[Review]:
        found: list[Review] = []
        for item in _dicts(self.get(f"/repos/{owner}/{name}/pulls/{number}/reviews")):
            submitted = _time(item.get("submitted_at"))
            user = item.get("user")
            author = (
                str(cast("dict[str, object]", user).get("login", ""))
                if isinstance(user, dict)
                else ""
            )
            if submitted is not None:
                found.append(Review(submitted, author))
        return found

    def close(self) -> None:
        self._http.close()
