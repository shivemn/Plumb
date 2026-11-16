"""Mine a repo's git history: what changes, who changes it, what changes together.

Only file names are read from each commit, never file contents, so this
works on a blobless clone without downloading old versions of files.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import combinations
from pathlib import Path

from plumb.gitutil import git

_RECORD = "\x1e"
_FIELD = "\x1f"

# A commit that touches more files than this is usually a bulk change
# (formatting, renames, dependency updates). It says little about which
# files belong together, so it is left out of change-coupling.
BULK_COMMIT_FILES = 30


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    when: datetime
    files: tuple[str, ...]


@dataclass(frozen=True)
class FileHistory:
    path: str
    commits: int
    authors: int
    last_changed: datetime
    recent_shas: tuple[str, ...]  # newest first, at most 5


@dataclass(frozen=True)
class Coupling:
    a: str
    b: str
    together: int  # commits that changed both
    confidence: float  # together / commits that changed the less-changed of the two


@dataclass
class History:
    since: datetime
    until: datetime
    commits: list[Commit] = field(default_factory=list[Commit])
    files: dict[str, FileHistory] = field(default_factory=dict[str, FileHistory])
    couplings: list[Coupling] = field(default_factory=list[Coupling])

    def hot_files(self, limit: int = 10) -> list[FileHistory]:
        ranked = sorted(self.files.values(), key=lambda f: (-f.commits, -f.authors, f.path))
        return ranked[:limit]


def read_commits(repo: Path, since: datetime | None = None) -> list[Commit]:
    """Commits reachable from HEAD, newest first, with the files each changed."""
    args = [
        "log",
        "--no-merges",
        "--no-renames",
        "--name-only",
        f"--format={_RECORD}%H{_FIELD}%an{_FIELD}%at",
    ]
    if since is not None:
        args.append(f"--since={int(since.timestamp())}")
    output = git(*args, cwd=repo, timeout=300)
    commits: list[Commit] = []
    for record in output.split(_RECORD):
        if not record.strip():
            continue
        header, _, body = record.partition("\n")
        sha, author, stamp = header.split(_FIELD)
        files = tuple(line for line in body.splitlines() if line.strip())
        when = datetime.fromtimestamp(int(stamp), tz=UTC)
        commits.append(Commit(sha, author, when, files))
    return commits


def mine(
    repo: Path,
    window_days: int = 90,
    keep: set[str] | None = None,
    min_together: int = 3,
) -> History:
    """Summarise the last `window_days` of history, ending at the newest commit.

    The window ends at the newest commit rather than today, so an old or
    quiet repo still gets a useful picture. `keep` limits the files counted,
    usually to first-party source files from the inventory.
    """
    newest = read_commits_head_time(repo)
    since = newest - timedelta(days=window_days)
    commits = read_commits(repo, since=since)
    history = History(since=since, until=newest, commits=commits)

    per_file_commits: Counter[str] = Counter()
    per_file_authors: defaultdict[str, set[str]] = defaultdict(set)
    per_file_last: dict[str, datetime] = {}
    per_file_shas: defaultdict[str, list[str]] = defaultdict(list)
    pair_counts: Counter[tuple[str, str]] = Counter()

    for commit in commits:
        files = sorted({f for f in commit.files if keep is None or f in keep})
        for path in files:
            per_file_commits[path] += 1
            per_file_authors[path].add(commit.author)
            per_file_last.setdefault(path, commit.when)
            if len(per_file_shas[path]) < 5:
                per_file_shas[path].append(commit.sha)
        if 2 <= len(files) <= BULK_COMMIT_FILES:
            for pair in combinations(files, 2):
                pair_counts[pair] += 1

    for path, count in per_file_commits.items():
        history.files[path] = FileHistory(
            path=path,
            commits=count,
            authors=len(per_file_authors[path]),
            last_changed=per_file_last[path],
            recent_shas=tuple(per_file_shas[path]),
        )

    for (a, b), together in pair_counts.items():
        if together < min_together:
            continue
        smaller = min(per_file_commits[a], per_file_commits[b])
        history.couplings.append(Coupling(a, b, together, together / smaller))
    history.couplings.sort(key=lambda c: (-c.together, -c.confidence, c.a, c.b))
    return history


def is_shallow(repo: Path) -> bool:
    """True if the clone has only part of the history, so counts would be wrong."""
    return git("rev-parse", "--is-shallow-repository", cwd=repo).strip() == "true"


def read_commits_head_time(repo: Path) -> datetime:
    stamp = git("log", "-1", "--format=%ct", cwd=repo).strip()
    return datetime.fromtimestamp(int(stamp), tz=UTC)
