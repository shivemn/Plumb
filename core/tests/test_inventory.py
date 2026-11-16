from collections.abc import Callable

import pytest

from plumb.inventory import Category, build_inventory, classify, language_lines
from tests.conftest import RepoBuilder


@pytest.mark.parametrize(
    ("path", "language", "category"),
    [
        ("src/app/main.py", "python", Category.SOURCE),
        ("src/main/java/com/x/App.java", "java", Category.SOURCE),
        ("tests/test_app.py", "python", Category.TEST),
        ("src/test/java/com/x/AppTest.java", "java", Category.TEST),
        ("web/src/App.test.tsx", "typescript", Category.TEST),
        ("app/conftest_helpers.py", "python", Category.SOURCE),
        ("node_modules/zod/index.js", "javascript", Category.VENDORED),
        ("web/node_modules/a/b.ts", "typescript", Category.VENDORED),
        ("vendor/lib/x.go", "go", Category.VENDORED),
        ("dist/bundle.js", "javascript", Category.GENERATED),
        ("web/package-lock.json", None, Category.GENERATED),
        ("static/app.min.js", "javascript", Category.GENERATED),
        ("proto/user_pb2.py", "python", Category.GENERATED),
        ("docs/logo.png", None, Category.BINARY),
        ("Dockerfile", None, Category.CONFIG),
        ("docker-compose.yml", None, Category.CONFIG),
        ("pom.xml", None, Category.CONFIG),
        (".github/workflows/ci.yml", None, Category.CONFIG),
        ("src/main/resources/application.properties", None, Category.CONFIG),
        ("README.md", None, Category.DOCS),
        ("LICENSE", None, Category.DOCS),
        ("data/loans.csv", None, Category.DATA),
        ("notebooks/explore.ipynb", "notebook", Category.SOURCE),
    ],
)
def test_classify(path: str, language: str | None, category: Category) -> None:
    assert classify(path, b"text") == (language, category)


def test_null_byte_means_binary() -> None:
    assert classify("weird.dat", b"abc\0def")[1] is Category.BINARY


def test_build_inventory(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("demo")
    repo.commit(
        {
            "app/main.py": "import os\n\nprint(os.name)\n",
            "app/util.py": "x = 1",  # no newline at the end
            "tests/test_main.py": "def test():\n    pass\n",
            "node_modules/pkg/index.js": "module.exports = 1\n",
            "logo.png": b"\x89PNG\r\n\x1a\n\0\0",
            "README.md": "# Demo\n",
        }
    )
    files = {info.path: info for info in build_inventory(repo.path)}
    assert files["app/main.py"].lines == 3
    assert files["app/util.py"].lines == 1
    assert files["logo.png"].lines == 0
    assert files["node_modules/pkg/index.js"].category is Category.VENDORED
    assert language_lines(list(files.values())) == {"python": 6}


def test_untracked_files_are_ignored(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("demo")
    repo.commit({"a.py": "x = 1\n"})
    repo.write({"scratch.py": "y = 2\n"})
    assert [info.path for info in build_inventory(repo.path)] == ["a.py"]
