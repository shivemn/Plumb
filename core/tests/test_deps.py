from collections.abc import Callable

from plumb.deps import (
    Dependency,
    find_dependencies,
    gradle_deps,
    package_json_deps,
    pom_deps,
    pyproject_deps,
    requirements_deps,
)
from plumb.inventory import build_inventory
from tests.conftest import RepoBuilder

PYPROJECT = """\
[project]
name = "shop"
dependencies = [
    "fastapi>=0.110",
    "SQLAlchemy[asyncio]~=2.0",
    "psycopg_binary",
]

[project.optional-dependencies]
queue = ["confluent-kafka"]
"""


def test_pyproject() -> None:
    names = [(d.name, d.line) for d in pyproject_deps("pyproject.toml", PYPROJECT)]
    assert names == [
        ("fastapi", 4),
        ("sqlalchemy", 5),
        ("psycopg-binary", 6),
        ("confluent-kafka", 10),
    ]


def test_requirements() -> None:
    text = "# web\nflask==3.0\n-r base.txt\n\nredis>=5 ; python_version>'3.8'\ngit+https://x\n"
    assert [(d.name, d.line) for d in requirements_deps("requirements.txt", text)] == [
        ("flask", 2),
        ("redis", 5),
    ]


def test_pom() -> None:
    text = """<project>
  <dependencies>
    <dependency>
      <groupId>org.springframework.kafka</groupId>
      <artifactId>spring-kafka</artifactId>
    </dependency>
    <dependency>
      <groupId>org.postgresql</groupId>
      <artifactId>postgresql</artifactId>
      <scope>runtime</scope>
    </dependency>
  </dependencies>
</project>"""
    assert [(d.name, d.line) for d in pom_deps("pom.xml", text)] == [
        ("org.springframework.kafka:spring-kafka", 5),
        ("org.postgresql:postgresql", 9),
    ]


def test_gradle() -> None:
    text = 'dependencies {\n  implementation("org.mongodb:mongodb-driver-sync:4.11.0")\n'
    text += "  runtimeOnly 'com.h2database:h2'\n}\n"
    assert [(d.name, d.line) for d in gradle_deps("build.gradle", text)] == [
        ("org.mongodb:mongodb-driver-sync", 2),
        ("com.h2database:h2", 3),
    ]


def test_package_json() -> None:
    text = '{\n  "name": "web",\n  "dependencies": {\n    "pg": "^8",\n    "ioredis": "^5"\n  }\n}'
    assert package_json_deps("package.json", text) == [
        Dependency("npm", "pg", "package.json", 4),
        Dependency("npm", "ioredis", "package.json", 5),
    ]


def test_find_dependencies_skips_examples(make_repo: Callable[[str], RepoBuilder]) -> None:
    repo = make_repo("shop")
    repo.commit(
        {
            "pyproject.toml": PYPROJECT,
            "examples/demo/requirements.txt": "flask\n",
            "web/node_modules/x/package.json": '{"dependencies": {"left-pad": "1"}}',
        }
    )
    names = {d.name for d in find_dependencies(repo.path, build_inventory(repo.path))}
    assert names == {"fastapi", "sqlalchemy", "psycopg-binary", "confluent-kafka"}
