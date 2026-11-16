"""Run git safely on repositories Plumb does not trust."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Settings applied to every git call. Repos are untrusted: no prompts, no
# hooks from the repo, no fetching submodules over local file paths, and no
# credential helpers that could leak the user's own credentials.
_SAFE_CONFIG = (
    "-c", "core.hooksPath=/dev/null",
    "-c", "protocol.file.allow=never",
    "-c", "core.symlinks=false",
    "-c", "credential.helper=",
    "-c", "core.quotePath=false",
)  # fmt: skip


class GitError(RuntimeError):
    """A git command failed or ran out of time."""


def git(
    *args: str,
    cwd: Path | None = None,
    timeout: float = 120,
) -> str:
    """Run a git command and return its standard output as text."""
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    try:
        result = subprocess.run(
            ["git", *_SAFE_CONFIG, *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise GitError(f"git {args[0]} took longer than {timeout:.0f} seconds") from error
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise GitError(f"git {args[0]} failed: {message}")
    return result.stdout.decode("utf-8", "replace")
