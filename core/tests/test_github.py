from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from plumb.github import GitHubClient, GitHubError

ISSUES: list[dict[str, object]] = [
    {
        "number": 12,
        "title": "Typo in README",
        "labels": [{"name": "good first issue"}],
        "created_at": "2026-10-01T10:00:00Z",
        "comments": 2,
        "body": "See docs/setup.md",
    },
    {"number": 13, "title": "A PR", "pull_request": {}, "created_at": "2026-10-02T10:00:00Z"},
]
PULLS: list[dict[str, object]] = [
    {
        "number": 40,
        "title": "Fix",
        "created_at": "2026-10-01T10:00:00Z",
        "merged_at": "2026-10-02T10:00:00Z",
    },
    {"number": 41, "title": "Closed", "created_at": "2026-10-01T10:00:00Z", "merged_at": None},
]


def fake(seen: list[httpx.Request]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/issues"):
            return httpx.Response(200, json=ISSUES)
        if request.url.path.endswith("/pulls"):
            return httpx.Response(200, json=PULLS)
        if request.url.path.endswith("/reviews"):
            review = {"submitted_at": "2026-10-01T12:00:00Z", "user": {"login": "ann"}}
            return httpx.Response(200, json=[review])
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handle)


def test_issues_leave_out_pull_requests() -> None:
    client = GitHubClient(transport=fake([]))
    (issue,) = client.issues("o", "r", labels="good first issue")
    assert issue.number == 12
    assert issue.labels == ("good first issue",)
    assert issue.body == "See docs/setup.md"


def test_pull_requests_and_reviews() -> None:
    client = GitHubClient(transport=fake([]))
    merged, closed = client.pull_requests("o", "r")
    assert merged.merged_at is not None and closed.merged_at is None
    (review,) = client.reviews("o", "r", 40)
    assert review.author == "ann"


def test_token_is_sent_as_a_bearer_header() -> None:
    seen: list[httpx.Request] = []
    GitHubClient(token="secret", transport=fake(seen)).issues("o", "r")
    assert seen[0].headers["Authorization"] == "Bearer secret"
    assert seen[0].url.host == "api.github.com"


def test_answers_are_cached(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    first = GitHubClient(cache_dir=tmp_path, transport=fake(seen))
    first.issues("o", "r")
    second = GitHubClient(cache_dir=tmp_path, transport=fake(seen))
    second.issues("o", "r")
    assert len(seen) == 1 and second.requests == 0
    assert json.loads(next(tmp_path.iterdir()).read_text())[0]["number"] == 12


def test_rate_limit_says_to_set_a_token() -> None:
    def limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, headers={"x-ratelimit-remaining": "0"}, json={})

    client = GitHubClient(transport=httpx.MockTransport(limited))
    with pytest.raises(GitHubError, match="GITHUB_TOKEN"):
        client.issues("o", "r")


def test_missing_repo() -> None:
    with pytest.raises(GitHubError, match="private or renamed"):
        GitHubClient(transport=fake([])).get("/repos/o/gone")
