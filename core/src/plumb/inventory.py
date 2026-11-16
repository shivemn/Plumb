"""List a repo's files and sort them into kinds.

Only files tracked by git are counted. Vendored, generated and binary files
are kept in the inventory but marked, so later stages can skip them and the
report can say they were skipped.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from plumb.gitutil import git


class Category(StrEnum):
    SOURCE = "source"
    TEST = "test"
    CONFIG = "config"
    DOCS = "docs"
    DATA = "data"
    VENDORED = "vendored"
    GENERATED = "generated"
    BINARY = "binary"


@dataclass(frozen=True)
class FileInfo:
    path: str  # from the repo root, forward slashes
    language: str | None
    category: Category
    lines: int
    size: int


LANGUAGES: dict[str, str] = {
    ".py": "python", ".pyi": "python",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".scala": "scala",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php", ".cs": "csharp",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".swift": "swift", ".r": "r", ".jl": "julia", ".lua": "lua", ".dart": "dart",
    ".sh": "shell", ".bash": "shell", ".ps1": "powershell",
    ".sql": "sql", ".html": "html", ".css": "css", ".scss": "css", ".vue": "vue",
    ".svelte": "svelte", ".ipynb": "notebook",
}  # fmt: skip

_VENDORED_DIRS = frozenset({
    "node_modules", "vendor", "third_party", "third-party", "bower_components",
    ".venv", "venv", "site-packages", "Pods",
})  # fmt: skip
_GENERATED_DIRS = frozenset({"dist", "build", "target", "out", ".next", "__pycache__", "coverage"})
_LOCK_FILES = frozenset({
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
    "Pipfile.lock", "Cargo.lock", "go.sum", "composer.lock", "Gemfile.lock",
})  # fmt: skip
_CONFIG_NAMES = frozenset({
    "dockerfile", "makefile", "pom.xml", "build.gradle", "settings.gradle", "pyproject.toml",
    "setup.py", "setup.cfg", "package.json", "tsconfig.json", "go.mod", "cargo.toml",
    "procfile", "render.yaml", "fly.toml", "vercel.json", "netlify.toml", ".gitignore",
    ".gitattributes", ".dockerignore", ".editorconfig", "requirements.txt",
})  # fmt: skip
_CONFIG_SUFFIXES = frozenset({".yml", ".yaml", ".toml", ".ini", ".cfg", ".properties", ".env"})
_DOC_SUFFIXES = frozenset({".md", ".rst", ".txt", ".adoc"})
_BINARY_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".jar",
    ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".mp3", ".class", ".so", ".dll", ".exe",
})  # fmt: skip
_TEST_DIRS = frozenset({"test", "tests", "__tests__", "spec", "specs", "testing"})


def classify(path: str, head: bytes) -> tuple[str | None, Category]:
    """Return (language, category) for a file, from its path and first bytes."""
    pure = PurePosixPath(path)
    parts = pure.parts[:-1]
    name = pure.name
    suffix = pure.suffix.lower()
    language = LANGUAGES.get(suffix)

    if any(part in _VENDORED_DIRS for part in parts):
        return language, Category.VENDORED
    if suffix in _BINARY_SUFFIXES or b"\0" in head:
        return None, Category.BINARY
    if (
        any(part in _GENERATED_DIRS for part in parts)
        or name in _LOCK_FILES
        or name.endswith((".min.js", ".min.css", ".map", "_pb2.py", ".pb.go", ".generated.ts"))
    ):
        return language, Category.GENERATED
    if _is_test(pure):
        return language, Category.TEST
    if name.lower() in _CONFIG_NAMES or name.lower().startswith(("dockerfile", "docker-compose")):
        return language, Category.CONFIG
    if parts[:2] == (".github", "workflows") or suffix in _CONFIG_SUFFIXES:
        return language, Category.CONFIG
    if language is not None:
        return language, Category.SOURCE
    if suffix in _DOC_SUFFIXES or name.upper() in {"LICENSE", "LICENCE", "NOTICE", "AUTHORS"}:
        return None, Category.DOCS
    return None, Category.DATA


def _is_test(pure: PurePosixPath) -> bool:
    if any(part in _TEST_DIRS for part in pure.parts[:-1]):
        return True
    if pure.suffix.lower() not in LANGUAGES:
        return False
    stem = pure.stem
    return stem.startswith("test_") or stem.endswith(
        ("_test", ".test", ".spec", "Test", "Tests", "IT")
    )


def build_inventory(repo: Path) -> list[FileInfo]:
    """Inventory every tracked file in `repo` at its current commit."""
    files: list[FileInfo] = []
    for path in git("ls-files", "-z", cwd=repo).split("\0"):
        if not path:
            continue
        full = repo / path
        if full.is_symlink() or not full.is_file():
            continue
        data = full.read_bytes()
        language, category = classify(path, data[:8192])
        files.append(FileInfo(path, language, category, _count_lines(data, category), len(data)))
    return files


def _count_lines(data: bytes, category: Category) -> int:
    if category is Category.BINARY or not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def language_lines(files: list[FileInfo]) -> Counter[str]:
    """Lines of first-party source and test code per language."""
    totals: Counter[str] = Counter()
    for info in files:
        if info.language and info.category in (Category.SOURCE, Category.TEST):
            totals[info.language] += info.lines
    return totals
