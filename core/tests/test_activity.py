from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from plumb.activity import (
    Activity,
    ReviewSpeed,
    StarterIssue,
    describe_hours,
    files_named,
    is_starter,
    read_activity,
)
from plumb.facts import FactBuilder, add_activity_facts
from plumb.github import GitHubClient, Issue
from plumb.model import IssueEvidence, Topic

START = datetime(2026, 10, 1, tzinfo=UTC)
PATHS = {"src/app/server.py", "docs/setup.md", "src/app/util.py", "tests/util.py"}


def issue(number: int, labels: tuple[str, ...], body: str = "") -> Issue:
    return Issue(number, f"Issue {number}", labels, START, 0, body)


def stamp(hours: float) -> str:
    return (START + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def test_starter_labels_ignore_case() -> None:
    assert is_starter(issue(1, ("Good First Issue",)))
    assert is_starter(issue(2, ("help wanted", "bug")))
    assert not is_starter(issue(3, ("bug",)))


def test_files_named_by_path_or_unique_name() -> None:
    text = "Crash in src/app/server.py, see setup.md. util.py is fine. Version 1.2 too."
    assert files_named(text, PATHS) == ("src/app/server.py", "docs/setup.md")


def test_partial_path_matches_the_end_of_a_repo_path() -> None:
    assert files_named("look at app/util.py", PATHS) == ("src/app/util.py",)


def test_describe_hours() -> None:
    assert describe_hours(0.5) == "under an hour"
    assert describe_hours(5.2) == "5 hours"
    assert describe_hours(24 * 6) == "6 days"


def fake_github() -> httpx.MockTransport:
    issues: list[dict[str, object]] = [
        {
            "number": 7,
            "title": "Fix the error in server.py",
            "labels": [{"name": "good first issue"}],
            "created_at": stamp(0),
            "body": "",
        },
        {"number": 8, "title": "Big redesign", "labels": [], "created_at": stamp(0)},
    ]
    pulls = [
        {
            "number": n,
            "title": "x",
            "created_at": stamp(0),
            "merged_at": stamp(hours),
            "user": {"login": "author"},
        }
        for n, hours in ((20, 10), (21, 30), (22, 50))
    ]

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/issues"):
            return httpx.Response(200, json=issues)
        if path.endswith("/pulls"):
            return httpx.Response(200, json=pulls)
        number = int(path.split("/")[-2])
        reviews = [
            {"submitted_at": stamp(1), "user": {"login": "author"}},  # own comment, ignored
            {"submitted_at": stamp(number - 18), "user": {"login": "maintainer"}},
        ]
        return httpx.Response(200, json=reviews)

    return httpx.MockTransport(handle)


def test_read_activity() -> None:
    activity = read_activity(GitHubClient(transport=fake_github()), "o", "r", PATHS)
    (starter,) = activity.starters
    assert starter.issue.number == 7 and starter.files == ("src/app/server.py",)
    assert activity.open_issues == 2
    assert activity.speed is not None
    assert activity.speed.hours_to_merge == 30
    assert activity.speed.hours_to_review == 3  # 2, 3 and 4 hours


def test_github_failure_is_reported_not_raised() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    activity = read_activity(GitHubClient(transport=transport), "o", "r", PATHS)
    assert activity.starters == [] and activity.error == "GitHub answered 500 for /repos/o/r/issues"


def test_activity_facts_cite_issues_and_files() -> None:
    starter = StarterIssue(issue(7, ("good first issue",)), ("src/app/server.py",))
    speed = ReviewSpeed((20, 21, 22), 30, (20, 21, 22), 3)
    builder = FactBuilder()
    add_activity_facts(builder, Activity([starter], 2, speed))
    statements = [f.statement for f in builder.facts]
    assert statements[1] == (
        'Open issue #7 "Issue 7" is labelled good first issue; it names src/app/server.py'
    )
    assert "a median of 30 hours" in statements[2]
    assert "a median of 3 hours" in statements[3]
    assert all(f.topic is Topic.ACTIVITY for f in builder.facts)
    assert builder.facts[2].evidence[0] == IssueEvidence(number=20)
