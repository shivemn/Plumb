"""What a newcomer can pick up and how long their pull request will wait.

Two things come from GitHub, not from the code:

- Starter issues: open issues labelled for newcomers ("good first issue",
  "help wanted" and similar), with the repo files each one names, so the
  report can say where to start reading.
- Review speed: the median time from opening a pull request to its first
  review by someone else, and to its merge, over recently closed ones.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath

from plumb.github import GitHubClient, GitHubError, Issue, PullRequest

STARTER_LABELS = {
    "good first issue",
    "good-first-issue",
    "first-timers-only",
    "help wanted",
    "beginner",
    "beginner friendly",
    "easy",
    "starter",
    "e-easy",
    "difficulty: easy",
}
_PATHISH = re.compile(r"[\w./-]*\w\.[A-Za-z]{1,6}\b")


@dataclass(frozen=True)
class StarterIssue:
    issue: Issue
    files: tuple[str, ...]  # repo files the issue names


@dataclass(frozen=True)
class ReviewSpeed:
    merged: tuple[int, ...]  # numbers of the merged pull requests measured
    hours_to_merge: float
    reviewed: tuple[int, ...]
    hours_to_review: float | None


@dataclass(frozen=True)
class Activity:
    starters: list[StarterIssue]
    open_issues: int
    speed: ReviewSpeed | None
    error: str | None = None  # why GitHub could not be read, if it could not


def is_starter(issue: Issue) -> bool:
    return any(label.lower().strip() in STARTER_LABELS for label in issue.labels)


def files_named(text: str, paths: set[str]) -> tuple[str, ...]:
    """Repo files named in `text`, by full path or by a file name only one file has."""
    by_name: dict[str, list[str]] = {}
    for path in paths:
        by_name.setdefault(PurePosixPath(path).name, []).append(path)
    found: list[str] = []
    for token in _PATHISH.findall(text):
        token = token.strip("./")
        if token in paths:
            found.append(token)
        elif "/" in token:
            found += [p for p in paths if p.endswith("/" + token)][:1]
        elif len(by_name.get(token, [])) == 1:
            found.append(by_name[token][0])
    return tuple(dict.fromkeys(found))


def _hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def review_speed(
    client: GitHubClient, owner: str, name: str, pulls: list[PullRequest], reviews: int = 10
) -> ReviewSpeed | None:
    merged = [p for p in pulls if p.merged_at is not None]
    if len(merged) < 3:
        return None
    to_merge = [_hours(p.created_at, p.merged_at) for p in merged if p.merged_at]
    to_review: list[float] = []
    reviewed: list[int] = []
    for pull in merged[:reviews]:
        others = [r for r in client.reviews(owner, name, pull.number) if r.author != pull.author]
        if others:
            first = min(r.submitted_at for r in others)
            to_review.append(_hours(pull.created_at, first))
            reviewed.append(pull.number)
    return ReviewSpeed(
        merged=tuple(p.number for p in merged),
        hours_to_merge=statistics.median(to_merge),
        reviewed=tuple(reviewed),
        hours_to_review=statistics.median(to_review) if len(to_review) >= 3 else None,
    )


def read_activity(client: GitHubClient, owner: str, name: str, paths: set[str]) -> Activity:
    """Read starter issues and review speed. A GitHub failure is reported, not raised."""
    try:
        issues = client.issues(owner, name, limit=100)
        starters = [
            StarterIssue(i, files_named(f"{i.title}\n{i.body}", paths))
            for i in issues
            if is_starter(i)
        ]
        pulls = client.pull_requests(owner, name, limit=30)
        speed = review_speed(client, owner, name, pulls)
    except GitHubError as error:
        return Activity([], 0, None, str(error))
    return Activity(starters, len(issues), speed)


def describe_hours(hours: float) -> str:
    if hours < 1:
        return "under an hour"
    if hours < 48:
        return f"{round(hours)} hours"
    return f"{round(hours / 24)} days"
