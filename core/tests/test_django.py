from collections.abc import Callable

import pytest

from plumb.django import django_databases, read_urls, readable
from plumb.entrypoints import find_entry_points
from plumb.inventory import build_inventory
from plumb.system import Role, find_system
from tests.conftest import RepoBuilder


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        (r"^profiles/(?P<username>\w+)/?$", "/profiles/{username}"),
        ("articles/<slug:slug>/", "/articles/{slug}"),
        ("^api/", "/api"),
        ("^$", ""),
        ("", ""),
    ],
)
def test_readable(pattern: str, expected: str) -> None:
    assert readable(pattern) == expected


ROOT = b"""\
from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include('shop.apps.items.urls', namespace='items')),
    path('health/', views.health),
]
"""

ITEMS = b"""\
router = DefaultRouter(trailing_slash=False)
router.register(r'items', ItemViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    re_path(r'^items/(?P<slug>[-\\w]+)/buy/?$', BuyView.as_view()),
]
"""


def test_read_urls() -> None:
    root = read_urls(ROOT)
    assert root.routes == (("/admin", 5), ("/health", 7))
    assert root.includes == (("/api", "shop.apps.items.urls"),)
    items = read_urls(ITEMS)
    assert sorted(items.routes) == [("/items", 2), ("/items/{slug}/buy", 6)]


def test_django_routes_and_database(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("shop")
    repo.commit(
        {
            "shop/__init__.py": "",
            "shop/urls.py": ROOT.decode(),
            "shop/settings.py": (
                "DATABASES = {\n    'default': {\n"
                "        'ENGINE': 'django.db.backends.sqlite3',\n    }\n}\n"
            ),
            "shop/apps/__init__.py": "",
            "shop/apps/items/__init__.py": "",
            "shop/apps/items/urls.py": ITEMS.decode(),
        }
    )
    files = build_inventory(repo.path)
    names = sorted(e.name for e in find_entry_points(repo.path, files))
    assert names == ["ANY /admin", "ANY /api/items", "ANY /api/items/{slug}/buy", "ANY /health"]
    (store,) = find_system(repo.path, files, "shop").of(Role.STORE)
    assert (store.name, store.clues[0].line) == ("SQLite", 3)


def test_django_databases() -> None:
    text = "DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql'}}"
    assert django_databases(text) == [("PostgreSQL", 1)]
