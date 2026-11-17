"""Work out the running parts of a system from deploy files, dependencies and code.

Each part (a service built from this repo, a database, a queue, an outside
service) collects every piece of evidence found for it, so one box in the
system design diagram can link to all the files that prove it exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import cast

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

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


def dockerfile_parts(system: System, path: str, text: str, repo_name: str) -> None:
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


def find_system(repo: Path, files: list[FileInfo], repo_name: str) -> System:
    system = System()
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
