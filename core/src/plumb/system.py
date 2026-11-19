"""Work out the running parts of a system from deploy files, dependencies and code.

Each part (a service built from this repo, a database, a queue, an outside
service) collects every piece of evidence found for it, so one box in the
system design diagram can link to all the files that prove it exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import cast

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from plumb.deps import Dependency
from plumb.inventory import Category, FileInfo


class Role(StrEnum):
    SERVICE = "service"  # runs from this repo
    STORE = "store"  # database, cache, queue or search engine
    MONITORING = "monitoring"
    CONTAINER = "container"  # another container the setup starts
    OUTSIDE = "outside"  # an outside service reached over the network


@dataclass(frozen=True)
class Clue:
    path: str
    line: int
    detail: str  # what was found there, in a few words


@dataclass
class Part:
    role: Role
    name: str
    clues: list[Clue] = field(default_factory=list[Clue])


class System:
    def __init__(self) -> None:
        self.parts: dict[tuple[Role, str], Part] = {}

    def add(self, role: Role, name: str, clue: Clue) -> None:
        part = self.parts.setdefault((role, name), Part(role, name))
        if clue not in part.clues:
            part.clues.append(clue)

    def of(self, role: Role) -> list[Part]:
        return sorted((p for p in self.parts.values() if p.role is role), key=lambda p: p.name)


# Container images that are well-known infrastructure, by name prefix.
IMAGES: dict[str, tuple[Role, str]] = {
    "postgres": (Role.STORE, "PostgreSQL"),
    "postgis/postgis": (Role.STORE, "PostgreSQL"),
    "bitnami/postgresql": (Role.STORE, "PostgreSQL"),
    "mysql": (Role.STORE, "MySQL"),
    "mariadb": (Role.STORE, "MariaDB"),
    "mongo": (Role.STORE, "MongoDB"),
    "redis": (Role.STORE, "Redis"),
    "valkey/valkey": (Role.STORE, "Redis"),
    "bitnami/redis": (Role.STORE, "Redis"),
    "confluentinc/cp-kafka": (Role.STORE, "Apache Kafka"),
    "bitnami/kafka": (Role.STORE, "Apache Kafka"),
    "apache/kafka": (Role.STORE, "Apache Kafka"),
    "redpandadata/redpanda": (Role.STORE, "Apache Kafka"),
    "confluentinc/cp-zookeeper": (Role.STORE, "ZooKeeper"),
    "zookeeper": (Role.STORE, "ZooKeeper"),
    "rabbitmq": (Role.STORE, "RabbitMQ"),
    "elasticsearch": (Role.STORE, "Elasticsearch"),
    "docker.elastic.co/elasticsearch/elasticsearch": (Role.STORE, "Elasticsearch"),
    "opensearchproject/opensearch": (Role.STORE, "OpenSearch"),
    "minio/minio": (Role.STORE, "MinIO"),
    "apacheignite/ignite": (Role.STORE, "Apache Ignite"),
    "cassandra": (Role.STORE, "Cassandra"),
    "memcached": (Role.STORE, "Memcached"),
    "prom/prometheus": (Role.MONITORING, "Prometheus"),
    "grafana/grafana": (Role.MONITORING, "Grafana"),
    "jaegertracing/all-in-one": (Role.MONITORING, "Jaeger"),
}


def image_part(image: str) -> tuple[Role, str] | None:
    bare = image.split("@", 1)[0]
    name = bare.rsplit(":", 1)[0] if ":" in bare.rsplit("/", 1)[-1] else bare
    name = name.removeprefix("docker.io/").removeprefix("library/")
    return IMAGES.get(name)


def _load_nodes(text: str) -> Node | None:
    try:
        return yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        return None


def _get(node: Node | None, key: str) -> Node | None:
    if not isinstance(node, MappingNode):
        return None
    for key_node, value in cast("list[tuple[Node, Node]]", node.value):
        if isinstance(key_node, ScalarNode) and key_node.value == key:
            return value
    return None


def _items(node: Node | None) -> list[tuple[str, Node, int]]:
    if not isinstance(node, MappingNode):
        return []
    pairs = cast("list[tuple[Node, Node]]", node.value)
    return [(str(k.value), v, k.start_mark.line + 1) for k, v in pairs if isinstance(k, ScalarNode)]


def _scalar(node: Node | None) -> str | None:
    return str(node.value) if isinstance(node, ScalarNode) else None


def compose_parts(system: System, path: str, text: str) -> None:
    root = _load_nodes(text)
    for name, service, line in _items(_get(root, "services")):
        image = _scalar(_get(service, "image"))
        build = _get(service, "build")
        known = image_part(image) if image else None
        if known is not None:
            role, part = known
            system.add(role, part, Clue(path, line, f"Compose service {name}, image {image}"))
        elif build is not None:
            context = _scalar(build) or _scalar(_get(build, "context")) or "."
            system.add(
                Role.SERVICE, name, Clue(path, line, f"Compose service built from {context}")
            )
        elif image:
            # Built elsewhere in the same setup (often tagged by another file), or a
            # third-party container. Say only what the file says.
            system.add(Role.CONTAINER, name, Clue(path, line, f"Compose service, image {image}"))


# Folders whose Dockerfiles build packages or run tools rather than the app.
_TOOLING_DIRS = frozenset({
    "packaging", "extras", "scripts", "tools", "ci", "docs", "test", "tests", "e2e", "benchmarks",
})  # fmt: skip


def dockerfile_parts(system: System, path: str, text: str, repo_name: str) -> None:
    if any(part in _TOOLING_DIRS for part in PurePosixPath(path).parts[:-1]):
        return
    folder = str(PurePosixPath(path).parent)
    name = repo_name if folder == "." else PurePosixPath(folder).name
    start_line = 0
    command = ""
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        word = line.split(" ", 1)[0].upper()
        if word == "FROM" and not start_line:
            start_line = number
        elif word in ("CMD", "ENTRYPOINT"):
            command = line.split(" ", 1)[1] if " " in line else ""
            start_line = start_line or number
    if not start_line:
        return
    detail = f"Dockerfile, runs {command}" if command else "Dockerfile"
    system.add(Role.SERVICE, name, Clue(path, start_line, detail))


def render_parts(system: System, path: str, text: str) -> None:
    root = _load_nodes(text)
    services = _get(root, "services")
    if isinstance(services, SequenceNode):
        for service in cast("list[Node]", services.value):
            name = _scalar(_get(service, "name")) or "service"
            kind = _scalar(_get(service, "type")) or "web"
            line = service.start_mark.line + 1
            system.add(Role.SERVICE, name, Clue(path, line, f"Render {kind} service"))
    databases = _get(root, "databases")
    if isinstance(databases, SequenceNode):
        for database in cast("list[Node]", databases.value):
            line = database.start_mark.line + 1
            system.add(Role.STORE, "PostgreSQL", Clue(path, line, "Render managed database"))


def procfile_parts(system: System, path: str, text: str) -> None:
    for number, raw in enumerate(text.splitlines(), start=1):
        name, sep, command = raw.partition(":")
        if sep and name.strip() and not name.startswith("#"):
            detail = f"Procfile process, runs {command.strip()}"
            system.add(Role.SERVICE, name.strip(), Clue(path, number, detail))


def _is_compose(name: str) -> bool:
    lower = name.lower()
    return lower.startswith(("docker-compose", "compose")) and lower.endswith((".yml", ".yaml"))


def find_system(
    repo: Path, files: list[FileInfo], repo_name: str, deps: list[Dependency] | None = None
) -> System:
    system = System()
    dependency_parts(system, deps or [])
    config_parts(system, repo, files)
    for info in files:
        if info.category in (Category.VENDORED, Category.GENERATED, Category.EXAMPLE):
            continue
        pure = PurePosixPath(info.path)
        if ".devcontainer" in pure.parts:
            continue  # a development environment, not part of the running system
        name = pure.name
        reader_text = None
        if _is_compose(name) or name in ("render.yaml", "Procfile") or name == "Dockerfile":
            reader_text = (repo / info.path).read_text(encoding="utf-8", errors="replace")
        if reader_text is None:
            continue
        if _is_compose(name):
            compose_parts(system, info.path, reader_text)
        elif name == "render.yaml":
            render_parts(system, info.path, reader_text)
        elif name == "Procfile":
            procfile_parts(system, info.path, reader_text)
        else:
            dockerfile_parts(system, info.path, reader_text, repo_name)
    return system


# Dependencies that mean a repo talks to a store or an outside service.
# Keys are dependency names as plumb.deps normalises them. A key ending in
# "/" or ":" matches every name that starts with it.
DEPENDENCIES: dict[str, tuple[Role, str]] = {
    # PostgreSQL
    "psycopg": (Role.STORE, "PostgreSQL"),
    "psycopg2": (Role.STORE, "PostgreSQL"),
    "psycopg2-binary": (Role.STORE, "PostgreSQL"),
    "psycopg-binary": (Role.STORE, "PostgreSQL"),
    "asyncpg": (Role.STORE, "PostgreSQL"),
    "org.postgresql:postgresql": (Role.STORE, "PostgreSQL"),
    "pg": (Role.STORE, "PostgreSQL"),
    "postgres": (Role.STORE, "PostgreSQL"),
    "@neondatabase/serverless": (Role.STORE, "PostgreSQL"),
    # MySQL and MariaDB
    "pymysql": (Role.STORE, "MySQL"),
    "mysqlclient": (Role.STORE, "MySQL"),
    "mysql-connector-python": (Role.STORE, "MySQL"),
    "com.mysql:mysql-connector-j": (Role.STORE, "MySQL"),
    "mysql:mysql-connector-java": (Role.STORE, "MySQL"),
    "mysql2": (Role.STORE, "MySQL"),
    "org.mariadb.jdbc:mariadb-java-client": (Role.STORE, "MariaDB"),
    # Embedded and other databases
    "com.h2database:h2": (Role.STORE, "H2"),
    "org.hsqldb:hsqldb": (Role.STORE, "HSQLDB"),
    "org.xerial:sqlite-jdbc": (Role.STORE, "SQLite"),
    "better-sqlite3": (Role.STORE, "SQLite"),
    "aiosqlite": (Role.STORE, "SQLite"),
    "pymongo": (Role.STORE, "MongoDB"),
    "motor": (Role.STORE, "MongoDB"),
    "mongodb": (Role.STORE, "MongoDB"),
    "mongoose": (Role.STORE, "MongoDB"),
    "org.mongodb:": (Role.STORE, "MongoDB"),
    "org.springframework.boot:spring-boot-starter-data-mongodb": (Role.STORE, "MongoDB"),
    "cassandra-driver": (Role.STORE, "Cassandra"),
    "elasticsearch": (Role.STORE, "Elasticsearch"),
    "@elastic/elasticsearch": (Role.STORE, "Elasticsearch"),
    "org.apache.ignite:ignite-core": (Role.STORE, "Apache Ignite"),
    "pyignite": (Role.STORE, "Apache Ignite"),
    # Caches
    "redis": (Role.STORE, "Redis"),
    "ioredis": (Role.STORE, "Redis"),
    "org.springframework.boot:spring-boot-starter-data-redis": (Role.STORE, "Redis"),
    "redis.clients:jedis": (Role.STORE, "Redis"),
    "io.lettuce:lettuce-core": (Role.STORE, "Redis"),
    "pymemcache": (Role.STORE, "Memcached"),
    # Queues and streams
    "kafka-python": (Role.STORE, "Apache Kafka"),
    "confluent-kafka": (Role.STORE, "Apache Kafka"),
    "aiokafka": (Role.STORE, "Apache Kafka"),
    "kafkajs": (Role.STORE, "Apache Kafka"),
    "org.springframework.kafka:spring-kafka": (Role.STORE, "Apache Kafka"),
    "org.apache.kafka:kafka-clients": (Role.STORE, "Apache Kafka"),
    "pika": (Role.STORE, "RabbitMQ"),
    "aio-pika": (Role.STORE, "RabbitMQ"),
    "amqplib": (Role.STORE, "RabbitMQ"),
    "org.springframework.boot:spring-boot-starter-amqp": (Role.STORE, "RabbitMQ"),
    # Monitoring
    "io.micrometer:micrometer-registry-prometheus": (Role.MONITORING, "Prometheus"),
    "prometheus-client": (Role.MONITORING, "Prometheus"),
    "prom-client": (Role.MONITORING, "Prometheus"),
    "sentry-sdk": (Role.OUTSIDE, "Sentry"),
    "@sentry/": (Role.OUTSIDE, "Sentry"),
    "io.sentry:": (Role.OUTSIDE, "Sentry"),
    # Outside services reached through their SDKs
    "boto3": (Role.OUTSIDE, "AWS"),
    "@aws-sdk/": (Role.OUTSIDE, "AWS"),
    "software.amazon.awssdk:": (Role.OUTSIDE, "AWS"),
    "stripe": (Role.OUTSIDE, "Stripe"),
    "com.stripe:stripe-java": (Role.OUTSIDE, "Stripe"),
    "twilio": (Role.OUTSIDE, "Twilio"),
    "sendgrid": (Role.OUTSIDE, "SendGrid"),
    "@sendgrid/mail": (Role.OUTSIDE, "SendGrid"),
    "resend": (Role.OUTSIDE, "Resend"),
    "openai": (Role.OUTSIDE, "OpenAI API"),
    "anthropic": (Role.OUTSIDE, "Anthropic API"),
    "@anthropic-ai/sdk": (Role.OUTSIDE, "Anthropic API"),
    "firebase-admin": (Role.OUTSIDE, "Firebase"),
    "firebase": (Role.OUTSIDE, "Firebase"),
    "@supabase/supabase-js": (Role.OUTSIDE, "Supabase"),
    "supabase": (Role.OUTSIDE, "Supabase"),
    "slack-sdk": (Role.OUTSIDE, "Slack"),
    "@slack/web-api": (Role.OUTSIDE, "Slack"),
    "google-cloud-": (Role.OUTSIDE, "Google Cloud"),
    "@google-cloud/": (Role.OUTSIDE, "Google Cloud"),
}


def dependency_part(name: str) -> tuple[Role, str] | None:
    hit = DEPENDENCIES.get(name)
    if hit is not None:
        return hit
    for key, value in DEPENDENCIES.items():
        if key.endswith(("/", ":", "-")) and name.startswith(key):
            return value
    return None


def dependency_parts(system: System, deps: list[Dependency]) -> None:
    for dep in deps:
        hit = dependency_part(dep.name)
        if hit is not None:
            role, name = hit
            system.add(role, name, Clue(dep.path, dep.line, f"dependency {dep.name}"))


# Connection strings and settings in config files.
_CONFIG_SIGNS: tuple[tuple[re.Pattern[str], Role, str], ...] = (
    (re.compile(r"jdbc:postgresql:|postgres(?:ql)?(?:\+\w+)?://"), Role.STORE, "PostgreSQL"),
    (re.compile(r"jdbc:mysql:|mysql(?:\+\w+)?://"), Role.STORE, "MySQL"),
    (re.compile(r"jdbc:mariadb:"), Role.STORE, "MariaDB"),
    (re.compile(r"jdbc:h2:"), Role.STORE, "H2"),
    (re.compile(r"jdbc:hsqldb:"), Role.STORE, "HSQLDB"),
    (re.compile(r"sqlite(?:\+\w+)?:///|jdbc:sqlite:"), Role.STORE, "SQLite"),
    (re.compile(r"mongodb(?:\+srv)?://"), Role.STORE, "MongoDB"),
    (re.compile(r"rediss?://|spring\.data\.redis|spring\.redis\."), Role.STORE, "Redis"),
    (re.compile(r"amqps?://|spring\.rabbitmq\."), Role.STORE, "RabbitMQ"),
    (re.compile(r"bootstrap[-_.]servers"), Role.STORE, "Apache Kafka"),
)
_CONFIG_FILE = re.compile(
    r"(^|/)(application[\w-]*\.(ya?ml|properties)|\.env\.(example|sample|template)"
    r"|settings\.py|config\.py|alembic\.ini|.*\.env)$"
)
_PRISMA_PROVIDER = re.compile(r"datasource\s+\w+\s*\{[^}]*?provider\s*=\s*\"(\w+)\"", re.S)
_PRISMA_NAMES = {
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "sqlserver": "SQL Server",
    "cockroachdb": "CockroachDB",
}
_SQLITE_IMPORT = re.compile(rb"^\s*import sqlite3\b|^\s*from sqlite3 import", re.M)


def config_parts(system: System, repo: Path, files: list[FileInfo]) -> None:
    for info in files:
        if info.category in (Category.VENDORED, Category.GENERATED, Category.EXAMPLE):
            continue
        if info.category is Category.TEST:
            continue
        if _CONFIG_FILE.search(info.path):
            text = (repo / info.path).read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                for pattern, role, name in _CONFIG_SIGNS:
                    match = pattern.search(line)
                    if match:
                        clue = Clue(info.path, number, f"setting mentions {match.group(0)}")
                        system.add(role, name, clue)
        if PurePosixPath(info.path).name == "settings.py" or "/settings/" in info.path:
            from plumb.django import django_databases

            text = (repo / info.path).read_text(encoding="utf-8", errors="replace")
            for name, line in django_databases(text):
                system.add(Role.STORE, name, Clue(info.path, line, "Django DATABASES ENGINE"))
        if info.path.endswith(".prisma"):
            text = (repo / info.path).read_text(encoding="utf-8", errors="replace")
            for match in _PRISMA_PROVIDER.finditer(text):
                name = _PRISMA_NAMES.get(match.group(1).lower())
                if name:
                    line = text.count("\n", 0, match.start(1)) + 1
                    clue = Clue(info.path, line, f"Prisma datasource, provider {match.group(1)}")
                    system.add(Role.STORE, name, clue)
        if info.language == "python" and info.category is Category.SOURCE:
            source = (repo / info.path).read_bytes()
            match = _SQLITE_IMPORT.search(source)
            if match:
                line = source.count(b"\n", 0, match.start()) + 1
                system.add(Role.STORE, "SQLite", Clue(info.path, line, "imports sqlite3"))


# Settings read from the environment.
_ENV_READS: tuple[re.Pattern[bytes], ...] = (
    re.compile(rb"os\.environ(?:\.get)?\s*[\[(]\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
    re.compile(rb"os\.getenv\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
    re.compile(rb"process\.env\.([A-Z][A-Z0-9_]+)"),
    re.compile(rb"process\.env\[\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
    re.compile(rb"import\.meta\.env\.([A-Z][A-Z0-9_]+)"),
    re.compile(rb"System\.getenv\(\s*\"([A-Z][A-Z0-9_]+)\""),
)
# ${NAME} only counts in config files: in JavaScript it is template-string syntax.
_ENV_IN_CONFIG = re.compile(rb"\$\{([A-Z][A-Z0-9_]+)(?::[^}]*)?\}")


def find_settings(repo: Path, files: list[FileInfo]) -> dict[str, list[Clue]]:
    """Environment variables the code or config reads, with where each is read."""
    settings: dict[str, list[Clue]] = {}
    for info in files:
        if info.category not in (Category.SOURCE, Category.CONFIG):
            continue
        if info.size > 1_000_000 or info.path.startswith((".github/", ".devcontainer/")):
            continue
        source = (repo / info.path).read_bytes()
        patterns = (_ENV_IN_CONFIG,) if info.category is Category.CONFIG else _ENV_READS
        for pattern in patterns:
            for match in pattern.finditer(source):
                name = match.group(1).decode()
                line = source.count(b"\n", 0, match.start()) + 1
                clues = settings.setdefault(name, [])
                if len(clues) < 3 and all(c.path != info.path for c in clues):
                    clues.append(Clue(info.path, line, "reads it"))
    return dict(sorted(settings.items()))


@dataclass(frozen=True)
class Migrations:
    tool: str
    folder: str
    files: tuple[str, ...]  # in name order, which is the order they run in


_MIGRATION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Alembic", re.compile(r"^(?P<folder>(?:.*/)?(?:alembic|migrations)/versions)/[^/]+\.py$")),
    ("Flyway", re.compile(r"^(?P<folder>(?:.*/)?db/migration)/[VRU][^/]*__[^/]+\.sql$")),
    ("Django", re.compile(r"^(?P<folder>(?:.*/)?migrations)/\d{4}_[^/]+\.py$")),
    ("Prisma", re.compile(r"^(?P<folder>(?:.*/)?prisma/migrations)/[^/]+/migration\.sql$")),
    ("Liquibase", re.compile(r"^(?P<folder>(?:.*/)?db/changelog)/[^/]+\.(?:xml|ya?ml|sql)$")),
    ("Knex", re.compile(r"^(?P<folder>(?:.*/)?migrations)/\d{8,}_[^/]+\.(?:js|ts)$")),
)


def find_migrations(files: list[FileInfo]) -> list[Migrations]:
    """Folders of database migrations. These files are run by a tool, not imported,
    so they never show up in the import graph on their own."""
    found: dict[tuple[str, str], list[str]] = {}
    for info in files:
        if info.category in (Category.VENDORED, Category.GENERATED, Category.EXAMPLE):
            continue
        if PurePosixPath(info.path).name == "__init__.py":
            continue
        for tool, pattern in _MIGRATION_RULES:
            match = pattern.match(info.path)
            if match:
                found.setdefault((tool, match["folder"]), []).append(info.path)
                break
    return [
        Migrations(tool, folder, tuple(sorted(paths)))
        for (tool, folder), paths in sorted(found.items(), key=lambda item: item[0][1])
    ]
