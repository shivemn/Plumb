from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from plumb.facts import FactBuilder, add_api_facts
from plumb.inventory import build_inventory
from plumb.publicapi import NameKind, find_python_api, python_definitions, summary_line
from tests.conftest import RepoBuilder

Make = Callable[[str], RepoBuilder]


def repo_with(make_repo: Make, files: dict[str, str | bytes]) -> Path:
    repo = make_repo("repo")
    repo.run("init", "-q")
    repo.commit(files)
    return repo.path


CLIENT = '''
class Client:
    """An HTTP client.

    More words.
    """


class HTTPError(Exception):
    """Something failed."""


class Timeout(HTTPError):
    pass


def get(url, params=None, *, timeout: float = 5, **kwargs):
    """Send a GET request."""


def _private():
    pass
'''


def test_explicit_imports_without_all(make_repo: Make) -> None:
    tmp_path = repo_with(
        make_repo,
        {
            "pyproject.toml": '[project]\nname = "fetch"\n',
            "src/fetch/__init__.py": (
                "from .client import Client, get\nfrom .client import Timeout as Slow\n"
                "from . import utils\nfrom ._private import hidden\nVERSION = '1'\n"
            ),
            "src/fetch/client.py": CLIENT,
            "src/fetch/utils.py": "def helper():\n    pass\n",
            "src/fetch/_private.py": "hidden = 1\n",
            "tests/__init__.py": "",
        },
    )
    api = find_python_api(tmp_path, build_inventory(tmp_path), "fetch")
    assert api is not None and api.package == "fetch"
    names = {n.name: n for n in api.names}
    assert set(names) == {"Client", "get", "Slow", "utils", "hidden", "VERSION"}
    assert names["Client"].path == "src/fetch/client.py" and names["Client"].line == 2
    assert names["Client"].summary == "An HTTP client."
    assert names["Client"].exported_from == "src/fetch/__init__.py"
    assert names["get"].signature == "url, params, *, timeout, **kwargs"
    assert names["Slow"].kind is NameKind.EXCEPTION  # inherits from HTTPError
    assert names["utils"].kind is NameKind.MODULE and names["utils"].path == "src/fetch/utils.py"


def test_all_and_star_imports_through_a_subpackage(make_repo: Make) -> None:
    tmp_path = repo_with(
        make_repo,
        {
            "lib/__init__.py": (
                "from ._client import *\nfrom ._transports import *\n"
                '__all__ = ["Client", "Transport", "missing"]\n'
            ),
            "lib/_client.py": CLIENT,
            "lib/_transports/__init__.py": "from .base import *\n",
            "lib/_transports/base.py": 'class Transport:\n    """Sends requests."""\n',
        },
    )
    api = find_python_api(tmp_path, build_inventory(tmp_path))
    assert api is not None
    names = {n.name: n for n in api.names}
    assert names["Transport"].path == "lib/_transports/base.py"
    assert names["missing"].kind is NameKind.VALUE and names["missing"].path == "lib/__init__.py"


def test_overloads_give_way_to_the_real_definition() -> None:
    source = b"""
from typing import overload

@overload
def command(name): ...
@overload
def command(name, cls): ...
def command(name=None, cls=None, **attrs):
    '''Creates a new command.'''
"""
    definition = python_definitions(source)["command"]
    assert definition.signature == "name, cls, **attrs"
    assert definition.summary == "Creates a new command."


def test_summary_line() -> None:
    text = "The :class:`Response <Response>` object, which contains a\nserver's response.\n\nMore."
    assert summary_line(text) == "The Response object, which contains a server's response."
    assert summary_line("Add a ``--yes`` option. It asks first.") == "Add a `--yes` option."
    assert summary_line("x " * 100).endswith("...")


def test_api_facts(make_repo: Make) -> None:
    files: dict[str, str | bytes] = {"lib/__init__.py": "from .client import *\n"}
    tmp_path = repo_with(make_repo, {**files, "lib/client.py": CLIENT})
    api = find_python_api(tmp_path, build_inventory(tmp_path))
    assert api is not None
    builder = FactBuilder()
    add_api_facts(builder, api)
    statements = [f.statement for f in builder.facts]
    assert statements == [
        "lib/__init__.py makes 4 names public for code that uses lib: "
        "1 function, 1 class, 2 exceptions",
        "Public function get(url, params, *, timeout, **kwargs) in lib/client.py: "
        "Send a GET request.",
        "Public class Client in lib/client.py: An HTTP client.",
        "Public exceptions: HTTPError, Timeout",
    ]


def test_summary_skips_code_examples() -> None:
    text = 'url = httpx.URL("https://example.org")\nassert url.host == "example.org"\n\nMore.'
    assert summary_line(text) == "More."
    assert summary_line("Builds a URL.\nurl = URL('x')") == "Builds a URL."
