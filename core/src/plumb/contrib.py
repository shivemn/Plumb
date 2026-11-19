"""Find how a repo is set up, built and tested: the raw material for "How to contribute".

Read from the Makefile, GitHub Actions workflows and the contribution
guide. A command that CI runs is the strongest evidence of how to test a
repo, because it has to work for the checks to pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from plumb.inventory import Category, FileInfo


@dataclass(frozen=True)
class Step:
    kind: str  # "make", "ci", "guide"
    name: str  # target name, workflow step, or guide heading
    command: str
    path: str
    line: int
    job: str = ""  # the CI job a step belongs to
    other_repo: str = ""  # a repository the job checks out instead of this one


_MAKE_TARGET = re.compile(r"^([A-Za-z][\w.-]*)\s*:(?!=)")
_USEFUL_TARGETS = (
    "install", "init", "setup", "dev", "develop", "build", "run", "start", "serve",
    "test", "tests", "check", "lint", "format", "fmt", "typecheck", "ci", "docs",
)  # fmt: skip
_SKIP_COMMANDS = re.compile(r"^(echo|cd|ls|cat|mkdir|rm|cp|mv|export|set|if|fi|true)\b")


def makefile_steps(path: str, text: str) -> list[Step]:
    lines = text.splitlines()
    found: list[Step] = []
    for index, line in enumerate(lines):
        match = _MAKE_TARGET.match(line)
        if not match or match.group(1) not in _USEFUL_TARGETS:
            continue
        recipe = next(
            (
                lines[i].strip().lstrip("@-")
                for i in range(index + 1, min(index + 8, len(lines)))
                if lines[i].startswith("\t") and lines[i].strip()
            ),
            "",
        )
        if recipe:
            found.append(Step("make", match.group(1), recipe, path, index + 1))
    return found


def workflow_steps(path: str, text: str) -> list[Step]:
    """Each `run:` command in a GitHub Actions workflow, with its step name."""
    try:
        root = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        return []
    found: list[Step] = []
    for job_key, job in _pairs(_get(root, "jobs")):
        steps = _get(job, "steps")
        if not isinstance(steps, SequenceNode):
            continue
        job_name = _get(job, "name")
        job_label = job_key
        if isinstance(job_name, ScalarNode) and "${{" not in str(job_name.value):
            job_label = str(job_name.value)
        other = _other_repository(cast("list[Node]", steps.value))
        for step in cast("list[Node]", steps.value):
            run = _get(step, "run")
            if not isinstance(run, ScalarNode):
                continue
            name = _get(step, "name")
            label = str(name.value) if isinstance(name, ScalarNode) else ""
            for offset, command in enumerate(str(run.value).splitlines()):
                command = command.strip()
                if command and not _SKIP_COMMANDS.match(command) and not command.startswith("#"):
                    line = run.start_mark.line + 1 + (offset if run.style in ("|", ">") else 0)
                    if run.style in ("|", ">"):
                        line += 1
                    found.append(Step("ci", label, command, path, line, job_label, other))
    return found


def _other_repository(steps: list[Node]) -> str:
    """The repository an actions/checkout step fetches, if it is not this one."""
    for step in steps:
        uses = _get(step, "uses")
        if isinstance(uses, ScalarNode) and str(uses.value).startswith("actions/checkout"):
            repository = _get(_get(step, "with"), "repository")
            if isinstance(repository, ScalarNode) and "${{" not in str(repository.value):
                return str(repository.value)
    return ""


def guide_steps(path: str, text: str) -> list[Step]:
    """Section headings of a contribution guide."""
    found: list[Step] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            found.append(Step("guide", line[3:].strip(), "", path, number))
    return found[:8]


def _get(node: Node | None, key: str) -> Node | None:
    if not isinstance(node, MappingNode):
        return None
    for key_node, value in cast("list[tuple[Node, Node]]", node.value):
        if isinstance(key_node, ScalarNode) and key_node.value == key:
            return value
    return None


def _pairs(node: Node | None) -> list[tuple[str, Node]]:
    if not isinstance(node, MappingNode):
        return []
    pairs = cast("list[tuple[Node, Node]]", node.value)
    return [(str(k.value), v) for k, v in pairs if isinstance(k, ScalarNode)]


def find_steps(repo: Path, files: list[FileInfo]) -> list[Step]:
    found: list[Step] = []
    for info in files:
        if info.category in (Category.VENDORED, Category.GENERATED, Category.EXAMPLE):
            continue
        pure = PurePosixPath(info.path)
        name = pure.name
        reader = None
        if name in ("Makefile", "makefile", "GNUmakefile"):
            reader = makefile_steps
        elif pure.parts[:2] == (".github", "workflows") and pure.suffix in (".yml", ".yaml"):
            reader = workflow_steps
        elif name.lower().startswith("contributing") and pure.suffix.lower() in (".md", ".rst"):
            reader = guide_steps
        if reader is not None:
            text = (repo / info.path).read_text(encoding="utf-8", errors="replace")
            found.extend(reader(info.path, text))
    return found
