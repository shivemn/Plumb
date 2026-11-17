from collections.abc import Callable

from plumb.deps import Dependency
from plumb.inventory import Category, FileInfo, build_inventory
from plumb.system import (
    Clue,
    Role,
    System,
    compose_parts,
    config_parts,
    dependency_part,
    dependency_parts,
    dockerfile_parts,
    find_migrations,
    find_settings,
    find_system,
    image_part,
    procfile_parts,
    render_parts,
)
from tests.conftest import RepoBuilder

COMPOSE = """\
services:
  api:
    build: ./backend
    depends_on: [db]
  db:
    image: postgres:16-alpine
  cache:
    image: docker.io/library/redis:7
  proxy:
    image: traefik:v3
  metrics:
    image: prom/prometheus
"""


def test_image_part() -> None:
    assert image_part("postgres:16") == (Role.STORE, "PostgreSQL")
    assert image_part("docker.io/library/redis:7@sha256:abc") == (Role.STORE, "Redis")
    assert image_part("confluentinc/cp-kafka:7.6.0") == (Role.STORE, "Apache Kafka")
    assert image_part("localhost:5000/postgres") is None
    assert image_part("traefik:v3") is None


def test_compose() -> None:
    system = System()
    compose_parts(system, "docker-compose.yml", COMPOSE)
    summary = {(p.role, p.name, p.clues[0].line, p.clues[0].detail) for p in system.parts.values()}
    assert summary == {
        (Role.SERVICE, "api", 2, "Compose service built from ./backend"),
        (Role.STORE, "PostgreSQL", 5, "Compose service db, image postgres:16-alpine"),
        (Role.STORE, "Redis", 7, "Compose service cache, image docker.io/library/redis:7"),
        (Role.CONTAINER, "proxy", 9, "Compose service, image traefik:v3"),
        (Role.MONITORING, "Prometheus", 11, "Compose service metrics, image prom/prometheus"),
    }


def test_broken_compose_is_ignored() -> None:
    system = System()
    compose_parts(system, "compose.yml", "services: [unclosed")
    assert system.parts == {}


def test_dockerfile() -> None:
    system = System()
    text = 'FROM python:3.12-slim\nCOPY . .\nCMD ["uvicorn", "app:app"]\n'
    dockerfile_parts(system, "backend/Dockerfile", text, "shop")
    dockerfile_parts(system, "Dockerfile", "FROM node:20\n", "shop")
    assert system.parts[(Role.SERVICE, "backend")].clues == [
        Clue("backend/Dockerfile", 1, 'Dockerfile, runs ["uvicorn", "app:app"]')
    ]
    assert system.parts[(Role.SERVICE, "shop")].clues == [Clue("Dockerfile", 1, "Dockerfile")]


def test_render_and_procfile() -> None:
    system = System()
    render = "services:\n  - type: web\n    name: shop\ndatabases:\n  - name: shop-db\n"
    render_parts(system, "render.yaml", render)
    procfile_parts(system, "Procfile", "web: gunicorn app:app\nworker: celery -A app worker\n")
    assert {(p.role, p.name) for p in system.parts.values()} == {
        (Role.SERVICE, "shop"),
        (Role.STORE, "PostgreSQL"),
        (Role.SERVICE, "web"),
        (Role.SERVICE, "worker"),
    }


def test_find_system_skips_devcontainer(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("shop")
    repo.commit(
        {
            "docker-compose.yml": COMPOSE,
            ".devcontainer/Dockerfile": "FROM mcr.microsoft.com/devcontainers/java\n",
            "examples/demo/Dockerfile": "FROM alpine\n",
        }
    )
    system = find_system(repo.path, build_inventory(repo.path), "shop")
    assert [p.name for p in system.of(Role.SERVICE)] == ["api"]


def test_dependency_part() -> None:
    assert dependency_part("psycopg") == (Role.STORE, "PostgreSQL")
    assert dependency_part("org.springframework.kafka:spring-kafka") == (Role.STORE, "Apache Kafka")
    assert dependency_part("@aws-sdk/client-s3") == (Role.OUTSIDE, "AWS")
    assert dependency_part("org.mongodb:mongodb-driver-sync") == (Role.STORE, "MongoDB")
    assert dependency_part("google-cloud-storage") == (Role.OUTSIDE, "Google Cloud")
    assert dependency_part("fastapi") is None


def test_dependency_parts_merge_with_compose() -> None:
    system = System()
    compose_parts(system, "docker-compose.yml", COMPOSE)
    dependency_parts(system, [Dependency("python", "asyncpg", "pyproject.toml", 7)])
    clues = system.parts[(Role.STORE, "PostgreSQL")].clues
    assert [c.detail for c in clues] == [
        "Compose service db, image postgres:16-alpine",
        "dependency asyncpg",
    ]


def test_config_and_code_signs(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("shop")
    repo.commit(
        {
            "src/main/resources/application.yml": (
                "spring:\n  datasource:\n    url: jdbc:postgresql://db/shop\n"
                "  kafka:\n    bootstrap-servers: ${KAFKA_SERVERS:localhost:9092}\n"
            ),
            ".env.example": "REDIS_URL=redis://localhost:6379\n",
            "app/store.py": "import json\nimport sqlite3\n",
            "tests/test_store.py": "DB = 'mongodb://x'\n",
        }
    )
    system = System()
    config_parts(system, repo.path, build_inventory(repo.path))
    found = {(p.name, c.path, c.line) for p in system.parts.values() for c in p.clues}
    assert found == {
        ("PostgreSQL", "src/main/resources/application.yml", 3),
        ("Apache Kafka", "src/main/resources/application.yml", 5),
        ("Redis", ".env.example", 1),
        ("SQLite", "app/store.py", 2),
    }


def test_find_settings(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("shop")
    repo.commit(
        {
            "app/config.py": (
                'import os\nURL = os.environ["DATABASE_URL"]\nKEY = os.getenv("API_KEY")\n'
            ),
            "web/src/api.ts": "const base = import.meta.env.VITE_API_URL;\n",
            "server.js": "const port = process.env.PORT || 3000;\nconst s = `${MID}`;\n",
            ".github/workflows/ci.yml": "run: echo ${GITHUB_SHA}\n",
            "Dockerfile": "FROM python\nCMD serve --port ${PORT}\n",
            "README.md": 'os.environ["NOT_CODE"]\n',
        }
    )
    settings = find_settings(repo.path, build_inventory(repo.path))
    assert list(settings) == ["API_KEY", "DATABASE_URL", "PORT", "VITE_API_URL"]
    assert [(c.path, c.line) for c in settings["PORT"]] == [("Dockerfile", 2), ("server.js", 1)]


def test_find_migrations() -> None:
    def info(path: str, category: Category = Category.SOURCE) -> FileInfo:
        return FileInfo(path, None, category, 10, 100)

    files = [
        info("backend/app/alembic/versions/e2412789c190_initialize.py"),
        info("backend/app/alembic/versions/1a31ce608336_add_cascade.py"),
        info("backend/app/alembic/env.py"),
        info("src/main/resources/db/migration/V1__create_events.sql", Category.DATA),
        info("src/main/resources/db/migration/V2__add_index.sql", Category.DATA),
        info("shop/migrations/0001_initial.py"),
        info("shop/migrations/__init__.py"),
        info("node_modules/x/migrations/0001_a.py", Category.VENDORED),
    ]
    found = [(m.tool, m.folder, len(m.files)) for m in find_migrations(files)]
    assert found == [
        ("Alembic", "backend/app/alembic/versions", 2),
        ("Django", "shop/migrations", 1),
        ("Flyway", "src/main/resources/db/migration", 2),
    ]
