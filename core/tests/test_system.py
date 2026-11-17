from collections.abc import Callable

from plumb.inventory import build_inventory
from plumb.system import (
    Clue,
    Role,
    System,
    compose_parts,
    dockerfile_parts,
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
