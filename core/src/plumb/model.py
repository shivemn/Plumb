"""The shared data contract.

Every part of Plumb (the Python core, the Go miner and the web app) reads
and writes these shapes. The JSON Schema in /schema is generated from this
file with `plumb schema`, so edit here, never there.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RepoKind(StrEnum):
    """What kind of repo this is. Decides which section leads the report."""

    SERVICE = "service"
    LIBRARY = "library"
    CLI = "cli"
    DATA = "data"
    DOCS = "docs"
    SMALL = "small"
    UNKNOWN = "unknown"


class FileEvidence(Strict):
    kind: Literal["file"] = "file"
    path: str = Field(min_length=1, description="Path from the repo root, with forward slashes.")
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _lines_in_order(self) -> FileEvidence:
        if (self.start_line is None) != (self.end_line is None):
            raise ValueError("give both start_line and end_line, or neither")
        if (
            self.start_line is not None
            and self.end_line is not None
            and self.end_line < self.start_line
        ):
            raise ValueError("end_line comes before start_line")
        return self


class CommitEvidence(Strict):
    kind: Literal["commit"] = "commit"
    sha: str = Field(pattern=r"^[0-9a-f]{7,40}$")


class IssueEvidence(Strict):
    kind: Literal["issue"] = "issue"
    number: int = Field(ge=1)


Evidence = Annotated[
    FileEvidence | CommitEvidence | IssueEvidence,
    Field(discriminator="kind"),
]


class Fact(Strict):
    """Something Plumb found without AI, with the evidence for it."""

    id: str = Field(pattern=r"^f[0-9]+$")
    statement: str = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)


class Claim(Strict):
    """A sentence the model wrote. It must cite at least one fact."""

    text: str = Field(min_length=1)
    fact_ids: list[str] = Field(min_length=1)


class RepoRef(Strict):
    owner: str = Field(min_length=1)
    name: str = Field(min_length=1)
    commit: str = Field(pattern=r"^[0-9a-f]{7,40}$")


class FactSet(Strict):
    """Everything the analysis stage hands to the writing stage."""

    schema_version: Literal[1] = 1
    repo: RepoRef
    kind: RepoKind
    facts: list[Fact]

    @model_validator(mode="after")
    def _ids_unique(self) -> FactSet:
        ids = [fact.id for fact in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("fact ids must be unique")
        return self
