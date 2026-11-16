import pytest
from pydantic import ValidationError

from plumb.model import Claim, Fact, FactSet, FileEvidence, RepoKind, RepoRef

REPO = RepoRef(owner="sample-org", name="parcel-tracker", commit="4f2a91c")


def fact(fact_id: str) -> Fact:
    return Fact(
        id=fact_id,
        statement="Service api starts the FastAPI app on port 8000",
        evidence=[FileEvidence(path="docker-compose.yml", start_line=4, end_line=19)],
    )


def test_factset_round_trips_through_json() -> None:
    facts = FactSet(repo=REPO, kind=RepoKind.SERVICE, facts=[fact("f1")])
    assert FactSet.model_validate_json(facts.model_dump_json()) == facts


def test_fact_needs_evidence() -> None:
    with pytest.raises(ValidationError):
        Fact(id="f1", statement="Unsupported", evidence=[])


def test_claim_needs_a_fact() -> None:
    with pytest.raises(ValidationError):
        Claim(text="Unsupported", fact_ids=[])


def test_line_range_must_be_in_order() -> None:
    with pytest.raises(ValidationError):
        FileEvidence(path="a.py", start_line=20, end_line=4)


def test_line_range_needs_both_ends() -> None:
    with pytest.raises(ValidationError):
        FileEvidence(path="a.py", start_line=4)


def test_fact_ids_must_be_unique() -> None:
    with pytest.raises(ValidationError):
        FactSet(repo=REPO, kind=RepoKind.SERVICE, facts=[fact("f1"), fact("f1")])
