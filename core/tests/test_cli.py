import json
from pathlib import Path

from typer.testing import CliRunner

from plumb import __version__
from plumb.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_schema_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "factset.schema.json"
    result = runner.invoke(app, ["schema", "--out", str(out)])
    assert result.exit_code == 0
    assert json.loads(out.read_text())["title"] == "FactSet"
