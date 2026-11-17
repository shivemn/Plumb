"""Ask the model for each section's claims and read its answers.

The answers are not trusted here: this step only checks that each answer
is JSON of the right shape. Whether the claims are true is the verifier's
job (plumb.verify).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from plumb.writer.models import ModelClient, ResponseCache
from plumb.writer.plan import SYSTEM_PROMPT, SectionTask


class DraftClaim(BaseModel):
    text: str
    fact_ids: list[str] = []


class DraftSection(BaseModel):
    claims: list[DraftClaim]


@dataclass
class Draft:
    task: SectionTask
    claims: list[DraftClaim] = field(default_factory=list[DraftClaim])
    problem: str | None = None  # set when the model's answer could not be read


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


def parse_answer(text: str) -> DraftSection:
    """Read a model answer, tolerating a code fence or words around the JSON."""
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end < start:
        raise ValueError("no JSON object in the answer")
    try:
        return DraftSection.model_validate(json.loads(cleaned[start : end + 1]))
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(str(error).splitlines()[0]) from error


def write_section(
    task: SectionTask, client: ModelClient, cache: ResponseCache | None = None
) -> Draft:
    prompt = task.prompt
    for attempt in range(2):
        text = _ask(client, prompt, cache)
        try:
            return Draft(task, parse_answer(text).claims)
        except ValueError as error:
            if attempt == 1:
                return Draft(task, problem=f"the model's answer could not be read: {error}")
            prompt = (
                f"{task.prompt}\nYour last answer could not be read ({error}). "
                "Answer again with the JSON object only."
            )
    raise AssertionError("not reached")


def _ask(client: ModelClient, prompt: str, cache: ResponseCache | None) -> str:
    if cache is None:
        return client.complete(SYSTEM_PROMPT, prompt)
    key = ResponseCache.key(client.name, SYSTEM_PROMPT, prompt)
    hit = cache.get(key)
    if hit is not None:
        return hit
    text = client.complete(SYSTEM_PROMPT, prompt)
    cache.put(key, client.name, text)
    return text


def write_report(
    tasks: list[SectionTask], client: ModelClient, cache: ResponseCache | None = None
) -> list[Draft]:
    return [write_section(task, client, cache) for task in tasks]
