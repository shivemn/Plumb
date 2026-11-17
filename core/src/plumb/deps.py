"""Read declared dependencies from build files, with the line each is on.

Covers pyproject.toml, requirements files, pom.xml, Gradle build files and
package.json. Only names are read; versions do not matter for working out
what a repo talks to.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

from plumb.inventory import Category, FileInfo


@dataclass(frozen=True)
class Dependency:
    ecosystem: str  # "python", "maven", "npm"
    name: str  # normalised: lower case; Maven as group:artifact
    path: str
    line: int


_PEP508_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_MAVEN_BLOCK = re.compile(r"<dependency>(.*?)</dependency>", re.S)
_MAVEN_GROUP = re.compile(r"<groupId>\s*([^<\s]+)\s*</groupId>")
_MAVEN_ARTIFACT = re.compile(r"<artifactId>\s*([^<\s]+)\s*</artifactId>")
_GRADLE_COORD = re.compile(
    r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation|kapt|annotationProcessor)"""
    r"""\s*\(?\s*["']([\w.-]+):([\w.-]+)(?::[^"']*)?["']"""
)


def _python_name(spec: str) -> str | None:
    match = _PEP508_NAME.match(spec)
    if not match:
        return None
    return re.sub(r"[-_.]+", "-", match.group(1)).lower()


def _line_of(lines: list[str], needle: str, start: int = 0) -> int:
    for index in range(start, len(lines)):
        if needle in lines[index]:
            return index + 1
    return 1


def pyproject_deps(path: str, text: str) -> list[Dependency]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    project = cast("dict[str, object]", data.get("project", {}))
    specs: list[str] = [str(s) for s in cast("list[object]", project.get("dependencies", []))]
    optional = cast("dict[str, list[object]]", project.get("optional-dependencies", {}))
    for group in optional.values():
        specs.extend(str(s) for s in group)
    tool = cast("dict[str, object]", data.get("tool", {}))
    poetry = cast("dict[str, object]", tool.get("poetry", {}))
    specs.extend(cast("dict[str, object]", poetry.get("dependencies", {})).keys())
    lines = text.splitlines()
    found: list[Dependency] = []
    for spec in specs:
        name = _python_name(spec)
        if name and name != "python":
            raw = _PEP508_NAME.match(spec)
            line = _line_of(lines, raw.group(1) if raw else name)
            found.append(Dependency("python", name, path, line))
    return found


def requirements_deps(path: str, text: str) -> list[Dependency]:
    found: list[Dependency] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "git+", "http")):
            continue
        name = _python_name(line)
        if name:
            found.append(Dependency("python", name, path, number))
    return found


def pom_deps(path: str, text: str) -> list[Dependency]:
    found: list[Dependency] = []
    for block in _MAVEN_BLOCK.finditer(text):
        group = _MAVEN_GROUP.search(block.group(1))
        artifact = _MAVEN_ARTIFACT.search(block.group(1))
        if artifact is None:
            continue
        line = text.count("\n", 0, block.start(1) + artifact.start()) + 1
        name = f"{group.group(1) if group else ''}:{artifact.group(1)}".lower()
        found.append(Dependency("maven", name, path, line))
    return found


def gradle_deps(path: str, text: str) -> list[Dependency]:
    found: list[Dependency] = []
    for match in _GRADLE_COORD.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append(Dependency("maven", f"{match.group(1)}:{match.group(2)}".lower(), path, line))
    return found


def package_json_deps(path: str, text: str) -> list[Dependency]:
    try:
        data: object = json.loads(text)
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []
    package = cast("dict[str, object]", data)
    lines = text.splitlines()
    found: list[Dependency] = []
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        block = package.get(section)
        if not isinstance(block, dict):
            continue
        start = _line_of(lines, f'"{section}"') - 1
        for name in cast("dict[str, object]", block):
            found.append(Dependency("npm", name.lower(), path, _line_of(lines, f'"{name}"', start)))
    return found


_READERS = {
    "pyproject.toml": pyproject_deps,
    "pom.xml": pom_deps,
    "build.gradle": gradle_deps,
    "build.gradle.kts": gradle_deps,
    "package.json": package_json_deps,
}


def find_dependencies(repo: Path, files: list[FileInfo]) -> list[Dependency]:
    found: list[Dependency] = []
    for info in files:
        if info.category in (Category.VENDORED, Category.GENERATED, Category.EXAMPLE):
            continue
        name = PurePosixPath(info.path).name
        reader = _READERS.get(name)
        if reader is None and re.fullmatch(r"requirements[\w.-]*\.(txt|in)", name):
            reader = requirements_deps
        if reader is not None:
            text = (repo / info.path).read_text(encoding="utf-8", errors="replace")
            found.extend(reader(info.path, text))
    return found
