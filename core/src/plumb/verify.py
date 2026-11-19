"""Check every claim the model wrote against the facts it cites, and drop the ones that fail.

A claim is kept only if all of these hold:

- it cites at least one fact, and every cited fact exists and was given
  to the model for this section;
- every file path, route and `code name` it mentions appears in a cited fact;
- every number it states appears in a cited fact;
- every well-known technology it names (PostgreSQL, Kafka, React...)
  appears in a cited fact.

These checks catch invented files, routes and figures, the commonest ways
a generated explanation goes wrong. They cannot catch a wrong reading of
a fact that uses only the fact's own words; the evaluation's answer keys
are there for that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from plumb.model import Claim, Fact, FactSet, FileEvidence, RemovedClaim, Report, Section
from plumb.system import DEPENDENCIES, IMAGES
from plumb.writer.write import Draft, DraftClaim

_PATH = re.compile(
    r"(?<![\w/])(?:[\w.-]+/)+[\w.{}:\[\]*-]+|\b[\w-]+\.(?:py|java|kt|ts|tsx|js|jsx|"
    r"astro|vue|svelte|ya?ml|toml|json|xml|md|sql|properties|gradle|prisma|cfg|ini)\b"
)
# Slashed words that are not paths: CI/CD, I/O, TCP/IP, and/or.
_NOT_A_PATH = re.compile(r"[A-Z]+(?:/[A-Z]+)+|and/or|either/or|read/write|input/output")
_ROUTE = re.compile(r"(?<![\w/.])/[\w{}:.\[\]-]+(?:/[\w{}:.\[\]-]*)*")
_CODE = re.compile(r"`([^`]+)`")
_NUMBER = re.compile(r"(?<![\w./-])\d[\d,]*(?:\.\d+)?(?![\w/])")


_FRAMEWORKS = (
    "FastAPI", "Flask", "Django", "Spring", "Spring Boot", "Express", "Next.js", "React", "Vue",
    "Svelte", "Astro", "Angular", "Celery", "Typer", "Click", "argparse", "Docker", "Compose",
    "Kubernetes", "Helm", "Terraform", "GraphQL", "gRPC", "Prisma", "SQLAlchemy", "Hibernate",
    "Alembic", "Flyway", "Liquibase", "Render", "Heroku", "Vercel", "Netlify", "Nginx",
    "Kafka", "Redis", "PostgreSQL", "Postgres", "MySQL", "MongoDB", "SQLite", "RabbitMQ",
)  # fmt: skip
_TECH_NAMES = sorted(
    {name for _, name in IMAGES.values()}
    | {name for _, name in DEPENDENCIES.values()}
    | set(_FRAMEWORKS),
    key=len,
    reverse=True,
)
# Case-sensitive on purpose: "Express" and "Render" are products, "express" and
# "render" are ordinary words.
_TECH = re.compile(r"(?<![\w.-])(" + "|".join(re.escape(n) for n in _TECH_NAMES) + r")(?![\w-])")


@dataclass(frozen=True)
class Check:
    ok: bool
    reason: str = ""


def check_claim(claim: DraftClaim, given: dict[str, Fact], all_ids: set[str]) -> Check:
    text = claim.text.strip()
    if not text:
        return Check(False, "empty sentence")
    if not claim.fact_ids:
        return Check(False, "cites no fact")
    unknown = [i for i in claim.fact_ids if i not in all_ids]
    if unknown:
        return Check(False, f"cites facts that do not exist: {', '.join(unknown)}")
    outside = [i for i in claim.fact_ids if i not in given]
    if outside:
        return Check(False, f"cites facts not given for this section: {', '.join(outside)}")

    cited = [given[i] for i in claim.fact_ids]
    source = " ".join(
        [f.statement for f in cited]
        + [e.path for f in cited for e in f.evidence if isinstance(e, FileEvidence)]
    )
    named = {
        m.group(0).rstrip(".,;:")
        for m in _PATH.finditer(text)
        if not _NOT_A_PATH.fullmatch(m.group(0).rstrip(".,;:"))
    }
    named |= {m.group(0).rstrip(".,;:") for m in _ROUTE.finditer(text)}
    named |= {m.group(1) for m in _CODE.finditer(text)}
    missing = sorted(n for n in named if n and n not in source)
    if missing:
        return Check(False, f"names something its facts do not: {', '.join(missing)}")

    lowered = source.lower()
    unbacked = sorted(
        {m.group(1) for m in _TECH.finditer(text) if not _mentions(lowered, m.group(1))}
    )
    if unbacked:
        return Check(False, f"names technology its facts do not: {', '.join(unbacked)}")

    # Numbers inside names already checked above are not counted twice.
    bare = text
    for name in named:
        bare = bare.replace(name, " ")
    source_numbers = {_normalise(m.group(0)) for m in _NUMBER.finditer(source)}
    wrong = [
        m.group(0) for m in _NUMBER.finditer(bare) if _normalise(m.group(0)) not in source_numbers
    ]
    if wrong:
        return Check(False, f"states numbers its facts do not: {', '.join(wrong)}")
    return Check(True)


# Other ways the facts can name a technology: a short name, or a tool that only
# exists for it (kubectl runs against Kubernetes).
_SAME_TECH: dict[str, tuple[str, ...]] = {
    "postgres": ("postgresql",),
    "postgresql": ("postgres",),
    "kafka": ("apache kafka",),
    "ignite": ("apache ignite",),
    "kubernetes": ("kubectl", "k8s/", "helm"),
}


def _mentions(source: str, name: str) -> bool:
    lowered = name.lower()
    return lowered in source or any(other in source for other in _SAME_TECH.get(lowered, ()))


def _normalise(number: str) -> str:
    return number.replace(",", "").rstrip(".")


def verify(drafts: list[Draft], facts: FactSet, model: str) -> Report:
    all_ids = {f.id for f in facts.facts}
    by_id = {f.id: f for f in facts.facts}
    sections: list[Section] = []
    removed: list[RemovedClaim] = []
    cited: set[str] = set()
    for draft in drafts:
        spec = draft.task.section
        if draft.problem:
            removed.append(RemovedClaim(section=spec.id, text="", reason=draft.problem))
        given = {f.id: f for f in draft.task.facts}
        kept: list[Claim] = []
        for claim in draft.claims:
            result = check_claim(claim, given, all_ids)
            if result.ok:
                kept.append(Claim(text=claim.text.strip(), fact_ids=claim.fact_ids))
                cited.update(claim.fact_ids)
            else:
                removed.append(RemovedClaim(section=spec.id, text=claim.text, reason=result.reason))
        sections.append(Section(id=spec.id, title=spec.title, claims=kept))
    return Report(
        repo=facts.repo,
        kind=facts.kind,
        model=model,
        sections=sections,
        removed=removed,
        facts=[by_id[i] for i in sorted(cited, key=lambda i: int(i[1:]))],
    )
