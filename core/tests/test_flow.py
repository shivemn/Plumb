from __future__ import annotations

from collections.abc import Callable

from plumb.entrypoints import find_entry_points
from plumb.facts import FactBuilder, add_flow_facts
from plumb.flow import layers, trace_flows
from plumb.inventory import build_inventory
from tests.conftest import RepoBuilder

Make = Callable[[str], RepoBuilder]

ROUTES = """
from fastapi import APIRouter, Depends

from app.services import users as user_service
from app.repositories.users import UserRepo
from app.clients import billing

router = APIRouter()


@router.get("/users/{user_id}")
def read_user(user_id: int, repo: UserRepo = Depends()):
    return repo.by_id(user_id)


@router.post("/users")
def create_user(name: str):
    user = user_service.register(name)
    billing.open_account(user)
    return user


@router.get("/health")
def health():
    return {"ok": True}
"""

SERVICE = """
from app.repositories.users import UserRepo


def register(name):
    repo = UserRepo()
    _check(name)
    return repo.add(name)


def _check(name):
    pass
"""

REPO = """
class UserRepo:
    def __init__(self):
        self.session = None

    def by_id(self, user_id):
        return self.session.get(user_id)

    def add(self, name):
        self.session.add(name)
        self._log(name)

    def _log(self, name):
        pass
"""

CLIENT = """
import httpx


def open_account(user):
    httpx.post("https://billing", json=user)
"""


def build(make_repo: Make) -> RepoBuilder:
    repo = make_repo("repo")
    repo.run("init", "-q")
    repo.commit(
        {
            "app/__init__.py": "",
            "app/routes/__init__.py": "",
            "app/routes/users.py": ROUTES,
            "app/services/__init__.py": "",
            "app/services/users.py": SERVICE,
            "app/repositories/__init__.py": "",
            "app/repositories/users.py": REPO,
            "app/clients/__init__.py": "",
            "app/clients/billing.py": CLIENT,
        }
    )
    return repo


def test_trace_follows_imports_typed_parameters_and_local_objects(make_repo: Make) -> None:
    repo = build(make_repo)
    files = build_inventory(repo.path)
    flows = {
        f.route.name: f for f in trace_flows(repo.path, files, find_entry_points(repo.path, files))
    }
    assert set(flows) == {"GET /users/{user_id}", "POST /users", "GET /health"}

    read = flows["GET /users/{user_id}"]
    assert [s.name for s in read.steps] == ["read_user", "UserRepo.by_id"]
    assert [(t.what, t.call) for t in read.touches] == [("the database", "self.session.get")]

    create = flows["POST /users"]
    assert [s.name for s in create.steps] == [
        "create_user",
        "register",
        "open_account",
        "_check",
        "UserRepo.add",
        "UserRepo._log",
    ]
    assert {t.what for t in create.touches} == {"the database", "an outside HTTP service"}
    assert layers(create) == ("app/routes", "app/services", "app/clients", "app/repositories")

    assert [s.name for s in flows["GET /health"].steps] == ["health"]


def test_flow_facts(make_repo: Make) -> None:
    repo = build(make_repo)
    files = build_inventory(repo.path)
    flows = trace_flows(repo.path, files, find_entry_points(repo.path, files))
    builder = FactBuilder()
    add_flow_facts(builder, flows)
    statements = [f.statement for f in builder.facts]
    assert statements[0] == "2 of 3 traced routes reach the database"  # no path is shared by 2
    create = next(s for s in statements if s.startswith("POST /users"))
    assert create == (
        "POST /users is handled by create_user in app/routes/users.py; "
        "create_user calls register in app/services/users.py and "
        "open_account in app/clients/billing.py; "
        "register calls _check and UserRepo.add in app/repositories/users.py; "
        "UserRepo.add calls UserRepo._log; "
        "open_account reaches an outside HTTP service (httpx.post in app/clients/billing.py); "
        "UserRepo.add reaches the database (self.session.add in app/repositories/users.py)"
    )  # each file is named once
    assert not any(s.startswith("GET /health") for s in statements)  # one step, nothing reached
