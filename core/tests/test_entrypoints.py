from plumb.entrypoints import (
    EntryKind,
    EntryPoint,
    java_entry_points,
    js_entry_points,
    package_json_entry_points,
    pyproject_scripts,
    python_entry_points,
)

FASTAPI = b"""\
from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/items", tags=["items"])

@app.get("/health")
def health(): ...

@router.post("/{item_id}/buy", status_code=201)
async def buy(item_id: int): ...

@router.api_route("/sync", methods=["GET", "POST"])
def sync(): ...

@app.get(some_path)
def unknown(): ...

data = {}.get("not a route")
"""

FLASK_AND_CLI = b"""\
import typer

app = typer.Typer()
bp = Blueprint("shop", __name__, url_prefix="/shop")

@bp.route("/cart", methods=["POST"])
def cart(): ...

@app.command()
def run_backtest(): ...

@app.command("serve")
def start(): ...

def build_parser():
    sub = parser.add_subparsers()
    sub.add_parser("replay")

@shared_task
def send_email(): ...

if __name__ == "__main__":
    app()
"""


def test_fastapi_routes() -> None:
    assert python_entry_points("app/main.py", FASTAPI) == [
        EntryPoint(EntryKind.HTTP, "GET /health", "app/main.py", 6, "fastapi"),
        EntryPoint(EntryKind.HTTP, "POST /items/{item_id}/buy", "app/main.py", 9, "fastapi"),
        EntryPoint(EntryKind.HTTP, "GET,POST /items/sync", "app/main.py", 12, "fastapi"),
    ]


def test_flask_typer_argparse_celery_and_main() -> None:
    found = {(e.kind, e.name, e.framework) for e in python_entry_points("x.py", FLASK_AND_CLI)}
    assert found == {
        (EntryKind.HTTP, "POST /shop/cart", "flask"),
        (EntryKind.COMMAND, "run-backtest", "typer"),
        (EntryKind.COMMAND, "serve", "typer"),
        (EntryKind.COMMAND, "replay", "argparse"),
        (EntryKind.TASK, "send_email", "celery"),
        (EntryKind.MAIN, "run as a script", None),
    }


def test_pyproject_scripts() -> None:
    source = b'[project]\nname = "shop"\n\n[project.scripts]\nshop = "shop.cli:main"\n'
    assert pyproject_scripts("pyproject.toml", source) == [
        EntryPoint(EntryKind.COMMAND, "shop (shop.cli:main)", "pyproject.toml", 5, "package")
    ]


def test_bad_pyproject_is_ignored() -> None:
    assert pyproject_scripts("pyproject.toml", b"not [valid") == []


SPRING = b"""\
package com.shop.web;

@RestController
@RequestMapping("/api")
public class OrderController {
    @GetMapping
    public List<Order> all() { return null; }

    @PostMapping(value = {"/orders", "/orders/new"})
    public Order create() { return null; }

    @RequestMapping(path = "/legacy", method = RequestMethod.PUT)
    public void legacy() {}

    @DeleteMapping(Paths.ORDER)
    public void remove() {}

    @KafkaListener(topics = "${app.topic}", groupId = "billing")
    public void onEvent(String message) {}

    @RabbitListener(queues = {"emails", "sms"})
    public void notify(String message) {}

    @Scheduled(cron = "0 0 * * * *")
    public void hourly() {}

    @Scheduled(fixedRate = 5000)
    public void tick() {}

    public static void main(String[] args) {}
}
"""


def test_spring_entry_points() -> None:
    found = [(e.kind, e.name, e.framework, e.line) for e in java_entry_points("A.java", SPRING)]
    assert found == [
        (EntryKind.HTTP, "GET /api", "spring", 6),
        (EntryKind.HTTP, "POST /api/orders", "spring", 9),
        (EntryKind.HTTP, "POST /api/orders/new", "spring", 9),
        (EntryKind.HTTP, "PUT /api/legacy", "spring", 12),
        (EntryKind.HTTP, "DELETE /api/{Paths.ORDER}", "spring", 15),
        (EntryKind.CONSUMER, "${app.topic}, group billing", "kafka", 18),
        (EntryKind.CONSUMER, "emails", "rabbitmq", 21),
        (EntryKind.CONSUMER, "sms", "rabbitmq", 21),
        (EntryKind.SCHEDULED, "hourly (cron 0 0 * * * *)", "spring", 24),
        (EntryKind.SCHEDULED, "tick (every 5000 ms)", "spring", 27),
        (EntryKind.MAIN, "OrderController", None, 30),
    ]


EXPRESS = b"""\
const express = require("express");
const app = express();
const router = express.Router();

app.get("/health", (req, res) => res.send("ok"));
router.post("/orders/:id", handler);
app.use("/api", router);
app.all("/legacy", legacy);
cache.get("/not-a-route");
"""


def test_express_routes() -> None:
    found = [(e.name, e.line) for e in js_entry_points("server/index.js", EXPRESS)]
    assert found == [("GET /health", 5), ("POST /orders/:id", 6), ("ANY /legacy", 8)]


def test_next_route_files() -> None:
    found = js_entry_points(
        "web/app/(shop)/orders/[id]/route.ts", b"export async function GET() {}"
    )
    assert [(e.name, e.framework) for e in found] == [("ANY /orders/[id]", "next.js")]
    api = js_entry_points("pages/api/users/index.ts", b"export default function h() {}")
    assert [e.name for e in api] == ["ANY /api/users"]


def test_package_json() -> None:
    source = b"""{
  "name": "shop",
  "bin": { "shop": "./bin/shop.js" },
  "scripts": { "dev": "vite", "lint": "eslint .", "build": "vite build" }
}"""
    found = [(e.kind, e.name, e.line) for e in package_json_entry_points("package.json", source)]
    assert found == [
        (EntryKind.COMMAND, "shop (./bin/shop.js)", 3),
        (EntryKind.SCRIPT, "npm run dev: vite", 4),
        (EntryKind.SCRIPT, "npm run build: vite build", 4),
    ]
