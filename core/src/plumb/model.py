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
    WEBSITE = "website"
    DOCS = "docs"
    SMALL = "small"
    UNKNOWN = "unknown"


class Topic(StrEnum):
    """What a fact is about. The prompt planner picks facts for each section by topic."""

    KIND = "kind"
    LANGUAGES = "languages"
    SKIPPED = "skipped"
    BUILD = "build"
    SYSTEM = "system"
    SETTINGS = "settings"
    MIGRATIONS = "migrations"
    ENTRY_POINTS = "entry_points"
    PUBLIC_API = "public_api"
    FLOW = "flow"
    STRUCTURE = "structure"
    HISTORY = "history"
    CONTRIBUTE = "contribute"
    ACTIVITY = "activity"
    GENERAL = "general"


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
    topic: Topic = Topic.GENERAL
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


class Section(Strict):
    """One part of a report, such as the system design or how to contribute."""

    id: str = Field(pattern=r"^[a-z_]+$")
    title: str = Field(min_length=1)
    claims: list[Claim]


class RemovedClaim(Strict):
    """A sentence the verifier dropped, and why. Shown so readers can check the checker."""

    section: str
    text: str
    reason: str


# Views: what the page draws beside the claims. They come straight from the
# analysis, not from a model, so a section can show its diagram or table even
# when every claim in it was removed. Each item names the file it came from.


class Place(Strict):
    path: str
    line: int | None = None


class Stat(Strict):
    label: str
    value: str


class SystemPart(Strict):
    name: str
    role: Literal["service", "store", "monitoring", "outside", "container"]
    detail: str
    places: list[Place]


class SystemLink(Strict):
    source: str  # a part name, or "Clients" for whatever calls the routes
    target: str
    label: str
    place: Place | None = None


class SystemView(Strict):
    parts: list[SystemPart]
    links: list[SystemLink]
    links_known: bool = Field(description="False when parts exist but who uses what is unknown.")


class FileBlock(Strict):
    path: str
    lines: int
    commits: int


class Folder(Strict):
    path: str
    files: int
    lines: int
    blocks: list[FileBlock]
    uses: list[str]


class CodeMap(Strict):
    rows: list[list[Folder]] = Field(description="Folders higher up use folders lower down.")
    shown_files: int
    left_out: str
    warm: int = Field(description="Commits from which a file counts as often changed.")
    hot: int


class HotSpot(Strict):
    path: str
    commits: int
    authors: int
    changes_with: list[str]


class ApiName(Strict):
    name: str
    kind: str
    signature: str = ""
    summary: str = ""
    place: Place


class FlowStep(Strict):
    name: str
    place: Place
    caller: int | None = None
    before: bool = False


class FlowReach(Strict):
    what: str
    call: str
    place: Place
    by: int


class FlowView(Strict):
    route: str
    place: Place
    steps: list[FlowStep]
    reaches: list[FlowReach]


class RouteRow(Strict):
    kind: str  # "HTTP route", "Command", ...
    name: str
    framework: str = ""
    place: Place


class Gap(Strict):
    title: str
    detail: str


class Views(Strict):
    stats: list[Stat]
    system: SystemView | None = None
    code_map: CodeMap | None = None
    hot_spots: list[HotSpot] = Field(default_factory=list[HotSpot])
    window: str = ""
    api: list[ApiName] = Field(default_factory=list[ApiName])
    api_root: str = ""
    flows: list[FlowView] = Field(default_factory=list[FlowView])
    flows_traced: int = 0
    routes: list[RouteRow] = Field(default_factory=list[RouteRow])
    gaps: list[Gap] = Field(default_factory=list[Gap])


class Report(Strict):
    """What the web app renders: verified claims, grouped into sections."""

    schema_version: Literal[1] = 1
    repo: RepoRef
    kind: RepoKind
    model: str = Field(description="The model that wrote the claims, as provider:model.")
    sections: list[Section]
    removed: list[RemovedClaim]
    facts: list[Fact] = Field(
        description="Every fact a kept claim cites, so the report stands alone."
    )
    views: Views | None = None
    written_at: str | None = Field(
        default=None, description="When the report was written, ISO date."
    )
