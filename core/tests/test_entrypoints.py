from plumb.entrypoints import EntryKind, EntryPoint, pyproject_scripts, python_entry_points

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
