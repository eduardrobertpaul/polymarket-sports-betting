import logging
from typer.testing import CliRunner
import pytest

from app.cli import app
from app.logging_config import logger

runner = CliRunner()

@pytest.mark.parametrize("command", [["fetch", "--fixture", "123"]])
def test_cli_handles_provider_error(monkeypatch, command, caplog) -> None:
    async def _boom(*args, **kwargs):
        raise RuntimeError("provider blew up")

    # Patch provider fetcher + polymarket to fail
    monkeypatch.setattr("app.cli._collect_provider_snaps", _boom)
    monkeypatch.setattr("app.cli.fetch_market_probs", _boom)

    caplog.set_level(logging.ERROR, logger="polymarket")

    result = runner.invoke(app, command)
    # CLI should exit non-zero but NOT throw tracebacks to stdout
    assert result.exit_code == 1
    assert "provider blew up" in caplog.text
