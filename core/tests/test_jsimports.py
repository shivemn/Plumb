import json
from collections.abc import Callable
from pathlib import Path

from plumb.inventory import build_inventory
from plumb.jsimports import JsImport, JsResolver, PathAliases, js_edges, js_imports, strip_jsonc
from tests.conftest import RepoBuilder

TSX = b"""\
import React, { useState } from "react";
import type { Order } from "./types";
import * as api from "../lib/api";
export { formatMoney } from "./money";
import "./styles.css";
const legacy = require("./legacy");
const Home = lazy(() => import("./pages/Home"));
const later = import(`./pages/${name}`);
"""


def test_js_imports() -> None:
    assert js_imports("src/App.tsx", TSX) == [
        JsImport("react", 1),
        JsImport("./types", 2),
        JsImport("../lib/api", 3),
        JsImport("./money", 4),
        JsImport("./styles.css", 5),
        JsImport("./legacy", 6),
        JsImport("./pages/Home", 7),
    ]


def test_plain_javascript_with_jsx() -> None:
    source = b'import Button from "./Button";\nexport default () => <Button />;\n'
    assert js_imports("src/App.jsx", source) == [JsImport("./Button", 1)]


def test_strip_jsonc_keeps_slashes_inside_strings() -> None:
    text = """{
      // a comment
      "compilerOptions": {
        "baseUrl": ".", /* another */
        "paths": { "@/*": ["./src/*"], },
      },
    }"""
    data = json.loads(strip_jsonc(text))
    assert data["compilerOptions"]["paths"] == {"@/*": ["./src/*"]}


def test_resolver() -> None:
    tracked = {
        "web/src/App.tsx",
        "web/src/types.ts",
        "web/src/lib/api.ts",
        "web/src/pages/Home/index.tsx",
        "web/src/util.js",
    }
    aliases = [PathAliases("web", (("@/*", ("web/src/*",)),))]
    resolver = JsResolver(tracked, aliases)
    app = "web/src/App.tsx"
    assert resolver.resolve(app, "./types") == "web/src/types.ts"
    assert resolver.resolve(app, "./lib/api.js") == "web/src/lib/api.ts"
    assert resolver.resolve(app, "./pages/Home") == "web/src/pages/Home/index.tsx"
    assert resolver.resolve(app, "@/lib/api") == "web/src/lib/api.ts"
    assert resolver.resolve(app, "./util.js") == "web/src/util.js"
    assert resolver.resolve(app, "react") is None
    assert resolver.resolve(app, "./missing") is None
    # An alias only applies under the folder of its tsconfig.
    assert resolver.resolve("other/x.ts", "@/lib/api") is None


def test_js_edges(make_repo: Callable[[str], RepoBuilder], tmp_path: Path) -> None:
    repo = make_repo("web")
    repo.commit(
        {
            "web/tsconfig.json": '{ "compilerOptions": { "paths": { "@/*": ["./src/*"] } } }',
            "web/src/main.tsx": 'import App from "./App";\n',
            "web/src/App.tsx": 'import { get } from "@/api";\nimport "./App.css";\n',
            "web/src/api.ts": 'import axios from "axios";\n',
            "web/src/App.css": "body {}\n",
            "web/node_modules/axios/index.js": "module.exports = {}\n",
        }
    )
    edges = {(e.source, e.target, e.line) for e in js_edges(repo.path, build_inventory(repo.path))}
    assert edges == {
        ("web/src/main.tsx", "web/src/App.tsx", 1),
        ("web/src/App.tsx", "web/src/api.ts", 1),
    }
