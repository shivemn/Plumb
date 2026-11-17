import pytest

from plumb.model import Fact, FactSet, FileEvidence, RepoKind, RepoRef, Topic
from plumb.verify import check_claim, verify
from plumb.writer.plan import plan_report
from plumb.writer.write import Draft, DraftClaim

FACTS = [
    Fact(
        id="f1",
        topic=Topic.SYSTEM,
        statement="Database, cache or queue: PostgreSQL (Compose service db, image postgres:16)",
        evidence=[FileEvidence(path="docker-compose.yml", start_line=5, end_line=5)],
    ),
    Fact(
        id="f2",
        topic=Topic.ENTRY_POINTS,
        statement="HTTP route GET /api/items/{id} (fastapi) in app/api/routes/items.py",
        evidence=[FileEvidence(path="app/api/routes/items.py", start_line=9, end_line=9)],
    ),
    Fact(
        id="f3",
        topic=Topic.ENTRY_POINTS,
        statement="1,204 http routes found",
        evidence=[FileEvidence(path="app/main.py")],
    ),
]
GIVEN = {f.id: f for f in FACTS}
IDS = set(GIVEN)


def claim(text: str, *ids: str) -> DraftClaim:
    return DraftClaim(text=text, fact_ids=list(ids))


@pytest.mark.parametrize(
    ("text", "ids"),
    [
        ("The app stores its data in PostgreSQL.", ("f1",)),
        ("The app stores its data in Postgres.", ("f1",)),
        ("Routes use FastAPI.", ("f2",)),
        ("Callers render items, then express interest through the route.", ("f2",)),
        ("Compose starts PostgreSQL from the image postgres:16.", ("f1",)),
        ("Items are read through GET /api/items/{id} in app/api/routes/items.py.", ("f2",)),
        ("There are 1,204 routes.", ("f3",)),
        ("There are 1204 routes, and `docker-compose.yml` starts the database.", ("f3", "f1")),
    ],
)
def test_supported_claims_are_kept(text: str, ids: tuple[str, ...]) -> None:
    assert check_claim(claim(text, *ids), GIVEN, IDS).ok


@pytest.mark.parametrize(
    ("text", "ids", "reason"),
    [
        ("Uses PostgreSQL.", (), "cites no fact"),
        ("Uses PostgreSQL.", ("f9",), "do not exist: f9"),
        ("Data lives in app/db/models.py.", ("f1",), "names something its facts do not"),
        ("Users sign in at /api/login.", ("f2",), "/api/login"),
        ("The `ItemService` class handles items.", ("f2",), "ItemService"),
        ("Compose starts 3 databases.", ("f1",), "states numbers its facts do not: 3"),
        ("There are 1,205 routes.", ("f3",), "1,205"),
        ("   ", ("f1",), "empty sentence"),
        ("Routes are served by Flask.", ("f2",), "names technology its facts do not: Flask"),
        ("Data goes through Kafka to PostgreSQL.", ("f1",), "Kafka"),
    ],
)
def test_unsupported_claims_are_dropped(text: str, ids: tuple[str, ...], reason: str) -> None:
    result = check_claim(claim(text, *ids), GIVEN, IDS)
    assert not result.ok
    assert reason in result.reason


def test_claim_may_only_cite_facts_given_to_its_section() -> None:
    given = {"f1": GIVEN["f1"]}
    result = check_claim(claim("Has a route.", "f2"), given, IDS)
    assert "not given for this section" in result.reason


def test_verify_builds_a_report() -> None:
    facts = FactSet(
        repo=RepoRef(owner="o", name="shop", commit="4f2a91c"), kind=RepoKind.SERVICE, facts=FACTS
    )
    tasks = {t.section.id: t for t in plan_report(facts)}
    drafts = [
        Draft(
            tasks["system"],
            [claim("PostgreSQL holds the data.", "f1"), claim("Redis caches pages.", "f1")],
        ),
        Draft(tasks["entry_points"], problem="the model's answer could not be read: x"),
    ]
    report = verify(drafts, facts, "fake:test")
    system, entry = report.sections
    assert [c.text for c in system.claims] == ["PostgreSQL holds the data."]
    assert entry.claims == []
    assert [r.reason for r in report.removed] == [
        "names technology its facts do not: Redis",
        "the model's answer could not be read: x",
    ]
    assert [f.id for f in report.facts] == ["f1"]
