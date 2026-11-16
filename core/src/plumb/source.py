"""Get a repository onto disk, within limits.

A GitHub URL is cloned without file contents for old commits (a blobless
clone), so the full history is available for mining while only the files
at the newest commit are downloaded. A local path that is already a git
repository is used as it is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from plumb.gitutil import GitError, git

_GITHUB_URL = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)"
    r"(?P<owner>[A-Za-z0-9-]{1,39})/(?P<name>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$"
)
_SHORT_NAME = re.compile(r"^(?P<owner>[A-Za-z0-9-]{1,39})/(?P<name>[A-Za-z0-9._-]{1,100})$")


@dataclass(frozen=True)
class Limits:
    """How much of a repo Plumb is willing to take on."""

    clone_timeout_s: float = 300
    max_files: int = 20_000
    max_bytes: int = 500 * 1024 * 1024


@dataclass(frozen=True)
class Checkout:
    owner: str
    name: str
    commit: str
    path: Path


class SourceError(RuntimeError):
    """The repo could not be fetched or is over the limits."""


def parse_github(ref: str) -> tuple[str, str] | None:
    """Return (owner, name) for a GitHub URL or "owner/name", else None."""
    for pattern in (_GITHUB_URL, _SHORT_NAME):
        match = pattern.match(ref.strip())
        if match:
            return match["owner"], match["name"]
    return None


def fetch(ref: str, workdir: Path, limits: Limits | None = None) -> Checkout:
    """Return a checkout of `ref`, which is a local path, a GitHub URL or owner/name."""
    limits = limits or Limits()
    local = Path(ref).expanduser()
    if local.is_dir():
        checkout = _use_local(local.resolve())
    else:
        parsed = parse_github(ref)
        if parsed is None:
            raise SourceError(f"not a local folder or a GitHub repo: {ref}")
        checkout = _clone(*parsed, workdir=workdir, limits=limits)
    _check_size(checkout.path, limits)
    return checkout


def _use_local(path: Path) -> Checkout:
    try:
        top = Path(git("rev-parse", "--show-toplevel", cwd=path).strip())
        commit = git("rev-parse", "HEAD", cwd=top).strip()
    except GitError as error:
        raise SourceError(f"{path} is not a git repository with at least one commit") from error
    owner, name = "local", top.name
    try:
        remote = git("remote", "get-url", "origin", cwd=top).strip()
    except GitError:
        remote = ""
    parsed = parse_github(remote)
    if parsed:
        owner, name = parsed
    return Checkout(owner=owner, name=name, commit=commit, path=top)


def _clone(owner: str, name: str, workdir: Path, limits: Limits) -> Checkout:
    dest = workdir / f"{owner}__{name}"
    if not (dest / ".git").is_dir():
        workdir.mkdir(parents=True, exist_ok=True)
        git(
            "clone",
            "--filter=blob:none",
            "--single-branch",
            "--no-tags",
            f"https://github.com/{owner}/{name}.git",
            str(dest),
            timeout=limits.clone_timeout_s,
        )
    commit = git("rev-parse", "HEAD", cwd=dest).strip()
    return Checkout(owner=owner, name=name, commit=commit, path=dest)


def _check_size(path: Path, limits: Limits) -> None:
    files = 0
    total = 0
    for line in git("ls-files", "-z", "--format=%(objectsize)", cwd=path).split("\0"):
        if not line:
            continue
        files += 1
        total += int(line) if line.isdigit() else 0
        if files > limits.max_files:
            raise SourceError(f"repo has more than {limits.max_files} tracked files")
    if total > limits.max_bytes:
        raise SourceError(f"repo's files add up to more than {limits.max_bytes // 2**20} MB")
