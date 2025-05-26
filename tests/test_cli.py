import json
import asyncio
from typer.testing import CliRunner
import pytest

from app.cli import app

runner = CliRunner()


@pytest.mark.asyncio
async def _noop_async(*args, **kwargs):
    """Return empty list/dict; used to patch out network I/O."""
    return []


def test_cli_fetch_smoke(monkeypatch) -> None:
    # Patch the async helpers inside app.cli so no real HTTP happens
    monkeypatch.setattr("app.cli.fetch_market_probs", _noop_async)
    monkeypatch.setattr("app.cli._collect_provider_snaps", _noop_async)

    result = runner.invoke(app, ["fetch", "--fixture", "123"])
    assert result.exit_code == 0
    json.loads(result.stdout)
