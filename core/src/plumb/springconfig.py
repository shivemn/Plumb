"""Read Spring Boot settings files and resolve ${...} placeholders.

Only the default settings files are read (application.yml, .yaml and
.properties under src/main/resources). Profile files such as
application-prod.yml change values only when that profile is switched on,
so they are not used to fill in placeholders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from plumb.inventory import Category, FileInfo

_DEFAULT_FILES = ("application.yml", "application.yaml", "application.properties")
_PROPERTY = re.compile(r"([^=:\s]+)\s*[=:]\s*(.*)$")
_PLACEHOLDER = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


@dataclass(frozen=True)
class Setting:
    value: str
    path: str
    line: int


class SpringSettings:
    def __init__(self, values: dict[str, Setting]) -> None:
        self.values = values

    def resolve(self, text: str) -> tuple[str, list[Setting]]:
        """Replace each ${key} or ${key:default} in `text`, returning what was used.

        A key that is not in the settings keeps its default if it has one,
        otherwise the placeholder stays as written.
        """
        used: list[Setting] = []

        def replace(match: re.Match[str]) -> str:
            key, default = match.group(1).strip(), match.group(2)
            setting = self.values.get(key) or self.values.get(_relaxed(key))
            if setting is not None:
                used.append(setting)
                if "${" not in setting.value:
                    return setting.value
                # A value can itself hold a placeholder, often an environment
                # variable with a default.
                inner, more = self.resolve(setting.value)
                used.extend(more)
                return inner
            if default is not None:
                return default
            return match.group(0)

        return _PLACEHOLDER.sub(replace, text), used


def _relaxed(key: str) -> str:
    """Spring treats group-id, groupId and group_id as the same key."""
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", key).lower()
    return key.replace("_", "-")


def read_properties(path: str, text: str) -> dict[str, Setting]:
    values: dict[str, Setting] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(("#", "!")):
            continue
        match = _PROPERTY.match(line)
        if match:
            values[_relaxed(match.group(1))] = Setting(match.group(2).strip(), path, number)
    return values


def read_yaml(path: str, text: str) -> dict[str, Setting]:
    values: dict[str, Setting] = {}
    try:
        documents = cast("list[Node | None]", list(yaml.compose_all(text, Loader=yaml.SafeLoader)))
    except yaml.YAMLError:
        return values
    for document in documents:
        if document is not None:
            _flatten(document, "", path, values)
    return values


def _flatten(node: Node, prefix: str, path: str, out: dict[str, Setting]) -> None:
    if isinstance(node, MappingNode):
        for key_node, value in cast("list[tuple[Node, Node]]", node.value):
            if isinstance(key_node, ScalarNode):
                key = f"{prefix}.{key_node.value}" if prefix else str(key_node.value)
                _flatten(value, key, path, out)
    elif isinstance(node, ScalarNode):
        out.setdefault(_relaxed(prefix), Setting(str(node.value), path, node.start_mark.line + 1))
    elif isinstance(node, SequenceNode):
        items = cast("list[Node]", node.value)
        scalars = [str(i.value) for i in items if isinstance(i, ScalarNode)]
        if scalars:
            out.setdefault(
                _relaxed(prefix), Setting(",".join(scalars), path, node.start_mark.line + 1)
            )


def load_spring_settings(repo: Path, files: list[FileInfo]) -> SpringSettings:
    values: dict[str, Setting] = {}
    for info in files:
        pure = PurePosixPath(info.path)
        if info.category is not Category.CONFIG or pure.name not in _DEFAULT_FILES:
            continue
        if "test" in pure.parts:
            continue
        text = (repo / info.path).read_text(encoding="utf-8", errors="replace")
        reader = read_properties if pure.suffix == ".properties" else read_yaml
        for key, setting in reader(info.path, text).items():
            values.setdefault(key, setting)
    return SpringSettings(values)
