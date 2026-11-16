"""Build small throwaway git repos for tests, with no network."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

BASE_TIME = 1_790_000_000  # a fixed moment in 2026, so tests do not depend on today


class RepoBuilder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._tick = 0
        self.run("init", "-q", "-b", "main")

    def run(self, *args: str, author: str = "Asha", when: int | None = None) -> str:
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": author,
            "GIT_AUTHOR_EMAIL": f"{author.lower()}@example.com",
            "GIT_COMMITTER_NAME": author,
            "GIT_COMMITTER_EMAIL": f"{author.lower()}@example.com",
        }
        if when is not None:
            stamp = f"@{when} +0000"
            env["GIT_AUTHOR_DATE"] = stamp
            env["GIT_COMMITTER_DATE"] = stamp
        result = subprocess.run(
            ["git", *args], cwd=self.path, env=env, capture_output=True, check=True
        )
        return result.stdout.decode()

    def write(self, files: dict[str, str | bytes]) -> None:
        for rel, content in files.items():
            target = self.path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")

    def commit(
        self,
        files: dict[str, str | bytes],
        message: str = "change",
        author: str = "Asha",
        days_ago: float = 0,
    ) -> str:
        self.write(files)
        self.run("add", "-A")
        self._tick += 1
        when = BASE_TIME - int(days_ago * 86_400) + self._tick
        self.run("commit", "-q", "-m", message, author=author, when=when)
        return self.run("rev-parse", "HEAD").strip()


@pytest.fixture
def make_repo(tmp_path: Path) -> Callable[[str], RepoBuilder]:
    def factory(name: str = "repo") -> RepoBuilder:
        path = tmp_path / name
        path.mkdir()
        return RepoBuilder(path)

    return factory
