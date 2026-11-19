from collections.abc import Callable

from plumb.entrypoints import find_entry_points
from plumb.inventory import build_inventory
from plumb.openapi import openapi_routes
from plumb.system import Role, dependency_part
from tests.conftest import RepoBuilder

SPEC = """\
openapi: 3.0.1
servers:
  - url: http://localhost:9966/petclinic/api
paths:
  /owners:
    get:
      operationId: listOwners
    post:
      operationId: addOwner
  /owners/{ownerId}:
    parameters: []
    get:
      operationId: getOwner
"""


def test_openapi_routes() -> None:
    found = [(e.name, e.line) for e in openapi_routes("src/openapi.yml", SPEC)]
    assert found == [
        ("GET /petclinic/api/owners", 6),
        ("POST /petclinic/api/owners", 8),
        ("GET /petclinic/api/owners/{ownerId}", 12),
    ]


def test_not_a_spec() -> None:
    assert openapi_routes("openapi.yml", "name: something else\npaths: {}\n") == []


def test_spec_routes_join_code_routes_without_doubles(
    make_repo: Callable[[str], RepoBuilder],
) -> None:
    repo = make_repo("api")
    repo.commit(
        {
            "src/main/resources/openapi.yml": SPEC,
            "app/main.py": '@app.get("/petclinic/api/owners")\ndef owners(): ...\n',
        }
    )
    names = sorted(e.name for e in find_entry_points(repo.path, build_inventory(repo.path)))
    assert names == [
        "GET /petclinic/api/owners",
        "GET /petclinic/api/owners/{ownerId}",
        "POST /petclinic/api/owners",
    ]


def test_hsqldb() -> None:
    assert dependency_part("org.hsqldb:hsqldb") == (Role.STORE, "HSQLDB")
