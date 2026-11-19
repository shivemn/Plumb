from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from plumb.inventory import build_inventory
from plumb.libapi import find_public_api, java_api, js_api
from plumb.publicapi import NameKind
from tests.conftest import RepoBuilder

Make = Callable[[str], RepoBuilder]


def repo_with(make_repo: Make, files: dict[str, str | bytes]) -> Path:
    repo = make_repo("repo")
    repo.run("init", "-q")
    repo.commit(files)
    return repo.path


FRONT = """package org.soup;

/**
 * The front door. Second sentence.
 */
public class Soup {
    /** Parse HTML into a {@link Document}. */
    public static Document parse(String html) { return null; }
    public static Document parse(String html, String baseUri) { return null; }
    public Document instance() { return null; }
    static void hidden() {}
}

class PackagePrivate {}
"""


def test_java_root_package_first_with_static_methods(make_repo: Make) -> None:
    root = repo_with(
        make_repo,
        {
            "pom.xml": "<project/>",
            "src/main/java/org/soup/Soup.java": FRONT,
            "src/main/java/org/soup/nodes/Document.java": (
                "package org.soup.nodes;\n/** A document. */\npublic final class Document {}\n"
            ),
            "src/main/java/org/soup/nodes/ParseError.java": (
                "package org.soup.nodes;\npublic class ParseError extends RuntimeException {}\n"
            ),
            "src/main/java/org/soup/internal/Util.java": (
                "package org.soup.internal;\npublic class Util {}\n"
            ),
        },
    )
    api = java_api(root, build_inventory(root), [])
    assert api is not None and api.package == "org.soup" and api.root == "pom.xml"
    names = [(n.name, n.kind) for n in api.names]
    assert names == [
        ("Soup", NameKind.CLASS),
        ("Soup.parse", NameKind.FUNCTION),
        ("Document", NameKind.CLASS),
        ("ParseError", NameKind.EXCEPTION),
    ]
    soup, parse = api.names[0], api.names[1]
    assert soup.summary == "The front door."
    assert parse.signature == "html" and parse.forms == 2
    assert parse.summary == "Parse HTML into a Document."


INDEX = """
/** Make a client. */
export function createClient(baseUrl: string, { retries = 1 } = {}) {}
export class HttpError extends Error {}
export const VERSION = "1";
export const get = (url: string) => fetch(url);
export type Options = { retries: number };
export { Pool as ConnectionPool } from "./pool";
export * from "./util";
export default createClient;
"""


def test_js_exports_follow_package_json_to_source(make_repo: Make) -> None:
    root = repo_with(
        make_repo,
        {
            "package.json": (
                '{"name": "fetchy", "main": "dist/index.js", "types": "dist/index.d.ts"}'
            ),
            "src/index.ts": INDEX,
            "src/pool.ts": "/** Keeps connections. */\nexport class Pool {}\n",
            "src/util/index.ts": "export function retry(times: number, run?: () => void) {}\n",
        },
    )
    api = js_api(root, build_inventory(root))
    assert api is not None and api.package == "fetchy" and api.root == "src/index.ts"
    names = {n.name: n for n in api.names}
    assert list(names) == [
        "createClient",
        "HttpError",
        "VERSION",
        "get",
        "Options",
        "ConnectionPool",
        "retry",
        "default",
    ]
    assert names["createClient"].signature == "baseUrl, options"
    assert names["createClient"].summary == "Make a client."
    assert names["HttpError"].kind is NameKind.EXCEPTION
    assert names["get"].kind is NameKind.FUNCTION
    assert names["Options"].kind is NameKind.INTERFACE
    pool = names["ConnectionPool"]
    assert pool.path == "src/pool.ts" and pool.exported_from == "src/index.ts"
    assert pool.summary == "Keeps connections."
    assert names["retry"].path == "src/util/index.ts" and names["retry"].signature == "times, run"


def test_finder_follows_the_main_language(make_repo: Make) -> None:
    root = repo_with(
        make_repo,
        {
            "package.json": '{"name": "tooling"}',
            "index.js": "export const x = 1;\n",
            "lib/__init__.py": "def run():\n    pass\n" * 30,
        },
    )
    api = find_public_api(root, build_inventory(root), [])
    assert api is not None and api.package == "lib"
