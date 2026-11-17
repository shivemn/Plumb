from collections.abc import Callable

from plumb.entrypoints import EntryKind, EntryPoint, resolve_placeholders
from plumb.inventory import build_inventory
from plumb.springconfig import SpringSettings, load_spring_settings, read_properties, read_yaml
from tests.conftest import RepoBuilder

YAML = """\
spring:
  kafka:
    consumer:
      group-id: profile-builder
pipeline:
  topic: credit-events
  servers: ${KAFKA_SERVERS:localhost:9092}
  topics:
    - a
    - b
"""


def test_read_yaml_flattens_with_lines() -> None:
    values = read_yaml("application.yml", YAML)
    assert values["pipeline.topic"].value == "credit-events"
    assert values["pipeline.topic"].line == 6
    assert values["spring.kafka.consumer.group-id"].value == "profile-builder"
    assert values["pipeline.topics"].value == "a,b"


def test_read_properties() -> None:
    values = read_properties("application.properties", "# comment\napp.name=shop\napp.port: 8080\n")
    assert values["app.name"].value == "shop"
    assert values["app.port"].line == 3


def test_resolve() -> None:
    settings = SpringSettings(read_yaml("application.yml", YAML))
    assert settings.resolve("${pipeline.topic}")[0] == "credit-events"
    # Relaxed names: groupId finds group-id.
    assert settings.resolve("${spring.kafka.consumer.groupId}")[0] == "profile-builder"
    # A value that is itself a placeholder with a default.
    assert settings.resolve("${pipeline.servers}")[0] == "localhost:9092"
    assert settings.resolve("${missing.key:fallback}")[0] == "fallback"
    assert settings.resolve("${missing.key}")[0] == "${missing.key}"


def test_entry_points_are_resolved(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("ccp")
    repo.commit(
        {
            "src/main/resources/application.yml": YAML,
            "src/main/resources/application-prod.yml": "pipeline:\n  topic: prod-events\n",
            "src/test/resources/application.yml": "pipeline:\n  topic: test-events\n",
        }
    )
    settings = load_spring_settings(repo.path, build_inventory(repo.path))
    entry = EntryPoint(EntryKind.CONSUMER, "${pipeline.topic}, group g", "A.java", 9, "kafka")
    (resolved,) = resolve_placeholders([entry], settings)
    assert resolved.name == "credit-events, group g"
    assert resolved.resolved_from == (("src/main/resources/application.yml", 6),)
