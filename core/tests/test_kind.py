from plumb.deps import Dependency
from plumb.entrypoints import EntryKind, EntryPoint
from plumb.inventory import Category, FileInfo
from plumb.kind import decide_kind
from plumb.model import RepoKind
from plumb.system import Clue, Role, System


def source(path: str, lines: int = 400, language: str = "python") -> FileInfo:
    return FileInfo(path, language, Category.SOURCE, lines, lines * 30)


def doc(path: str) -> FileInfo:
    return FileInfo(path, None, Category.DOCS, 10, 300)


def config(path: str) -> FileInfo:
    return FileInfo(path, None, Category.CONFIG, 10, 300)


def test_docs_repo() -> None:
    decision = decide_kind([doc("readme.md"), doc("contributing.md")], [], System(), [])
    assert decision.kind is RepoKind.DOCS
    assert decision.clues[0].path == "readme.md"


def test_service_from_routes() -> None:
    route = EntryPoint(EntryKind.HTTP, "GET /health", "app/main.py", 5, "fastapi")
    decision = decide_kind([source("app/main.py")], [route], System(), [])
    assert decision.kind is RepoKind.SERVICE
    assert decision.clues == (Clue("app/main.py", 5, "GET /health"),)


def test_service_from_compose() -> None:
    system = System()
    system.add(Role.SERVICE, "api", Clue("compose.yml", 2, "Compose service built from ."))
    assert decide_kind([source("api.py")], [], system, []).kind is RepoKind.SERVICE


def test_cli() -> None:
    command = EntryPoint(EntryKind.COMMAND, "shop (shop.cli:main)", "pyproject.toml", 9)
    assert decide_kind([source("shop/cli.py")], [command], System(), []).kind is RepoKind.CLI


def test_data_project() -> None:
    files = [source("analysis.ipynb", 900, "notebook"), source("utils.py", 200)]
    assert decide_kind(files, [], System(), []).kind is RepoKind.DATA


def test_website() -> None:
    dep = Dependency("npm", "astro", "package.json", 12)
    files = [source("src/lib/content.ts", 900, "typescript"), config("package.json")]
    decision = decide_kind(files, [], System(), [dep])
    assert decision.kind is RepoKind.WEBSITE


def test_small_and_library() -> None:
    assert decide_kind([source("tool.py", 80)], [], System(), []).kind is RepoKind.SMALL
    library = [source("shop/core.py", 2000), config("pyproject.toml")]
    assert decide_kind(library, [], System(), []).kind is RepoKind.LIBRARY
    assert decide_kind([source("shop/core.py", 2000)], [], System(), []).kind is RepoKind.UNKNOWN
