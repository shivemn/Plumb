from collections.abc import Callable

from plumb.imports import Import, PythonIndex, python_edges, python_imports
from plumb.inventory import build_inventory
from tests.conftest import RepoBuilder

SOURCE = b"""\
import os
import shop.db as database, shop.util
from shop import api
from . import models
from ..core.rates import price, fee as charge
from .helpers import *

def late():
    import shop.cache
"""


def test_python_imports() -> None:
    assert python_imports(SOURCE) == [
        Import("os", (), 0, 1),
        Import("shop.db", (), 0, 2),
        Import("shop.util", (), 0, 2),
        Import("shop", ("api",), 0, 3),
        Import("", ("models",), 1, 4),
        Import("core.rates", ("price", "fee"), 2, 5),
        Import("helpers", (), 1, 6),
        Import("shop.cache", (), 0, 9),
    ]


def test_index_names_modules_from_package_roots() -> None:
    index = PythonIndex(
        [
            "src/shop/__init__.py",
            "src/shop/api.py",
            "src/shop/core/__init__.py",
            "src/shop/core/rates.py",
            "scripts/run.py",
        ]
    )
    assert index.module_of["src/shop/core/rates.py"] == "shop.core.rates"
    assert index.module_of["src/shop/__init__.py"] == "shop"
    assert index.module_of["scripts/run.py"] == "run"


def test_resolve() -> None:
    index = PythonIndex(
        [
            "shop/__init__.py",
            "shop/api.py",
            "shop/db.py",
            "shop/core/__init__.py",
            "shop/core/rates.py",
            "shop/web/__init__.py",
            "shop/web/views.py",
        ]
    )
    views = "shop/web/views.py"
    assert index.resolve(views, Import("shop", ("api",), 0, 1)) == ["shop/api.py"]
    assert index.resolve(views, Import("shop.db", (), 0, 1)) == ["shop/db.py"]
    assert index.resolve(views, Import("shop.core.rates", ("price",), 0, 1)) == [
        "shop/core/rates.py"
    ]
    assert index.resolve(views, Import("core.rates", ("price",), 2, 1)) == ["shop/core/rates.py"]
    assert index.resolve(views, Import("os", (), 0, 1)) == []
    assert index.resolve(views, Import("requests", ("get",), 0, 1)) == []
    # Too many dots: goes above the top package, so nothing.
    assert index.resolve(views, Import("x", (), 5, 1)) == []


def test_python_edges(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("shop")
    repo.commit(
        {
            "shop/__init__.py": "",
            "shop/api.py": "from shop.db import save\nimport json\n",
            "shop/db.py": "import sqlite3\n",
            "tests/test_api.py": "from shop import api\n",
        }
    )
    edges = {
        (e.source, e.target, e.line) for e in python_edges(repo.path, build_inventory(repo.path))
    }
    assert edges == {
        ("shop/api.py", "shop/db.py", 1),
        ("tests/test_api.py", "shop/api.py", 1),
    }
