"""
Typer-powered CLI entry point.

Usage examples:
    python -m app.cli fetch --fixture 123
    python -m app.cli recommend --fixture 123 --edge-threshold 0.03
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, Dict, List
import app.scheduler
import typer
from rich import print

from app.polymarket.aggregation import snapshots_to_true_probs
from app.polymarket.staking import recommend, compute_edge
from app.providers import get_active_providers
from app.polymarket.client import fetch_market_probs
from app.polymarket.aggregation import ProviderSnapshot, OutcomeOdds

app = typer.Typer(add_completion=False, no_args_is_help=True)


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #
async def _collect_provider_snaps(fixture_id: str) -> List[ProviderSnapshot]:
    snaps: List[ProviderSnapshot] = []
    for name, provider in get_active_providers().items():
        odds_rows = await provider.fetch_fixture_odds(fixture_id)
        if not odds_rows:
            continue
        odds = [OutcomeOdds(o["outcome"], o["decimal_odds"]) for o in odds_rows]
        snaps.append(
            ProviderSnapshot(
                provider=name,
                fixture_id=fixture_id,
                ts=datetime.utcnow(),
                odds=odds,
            )
        )
    return snaps


# --------------------------------------------------------------------------- #
#  Commands                                                                   #
# --------------------------------------------------------------------------- #
@app.command(help="Fetch raw odds/prices and dump JSON.")
def fetch(
    fixture: str = typer.Option(..., help="Fixture ID shared across providers"),
    pretty: bool = typer.Option(False, help="Pretty-print JSON"),
):
    import asyncio

    async def _run() -> Dict[str, Any]:
        provider_snaps = await _collect_provider_snaps(fixture)
        market_probs_rows = await fetch_market_probs(fixture)
        return {
            "provider_snaps": [snap.__dict__ for snap in provider_snaps],
            "market_probs": market_probs_rows,
        }

    data = asyncio.run(_run())
    dump = json.dumps(data, indent=2) if pretty else json.dumps(data)
    print(dump)


@app.command(help="Run full pipeline → recommendations.")
def recommend_cmd(
    fixture: str = typer.Option(..., help="Fixture ID / Polymarket slug"),
    edge_threshold: float = typer.Option(0.02, help="Minimum edge to trigger"),
    bankroll: float = typer.Option(100.0, help="Bankroll units"),
):
    import asyncio

    async def _run() -> Dict[str, Any]:
        provider_snaps = await _collect_provider_snaps(fixture)
        true_probs = snapshots_to_true_probs(provider_snaps)
        market_probs_rows = await fetch_market_probs(fixture)
        market_probs = {row["outcome"]: row["prob"] for row in market_probs_rows}
        edges = compute_edge(true_probs, market_probs)
        recs = recommend(
            true_probs,
            market_probs,
            edge_threshold=edge_threshold,
            bankroll=bankroll,
        )
        return {
            "true_probs": true_probs,
            "market_probs": market_probs,
            "edges": edges,
            "recommendations": recs,
        }

    result = asyncio.run(_run())
    print(json.dumps(result, indent=2))


@app.command(help="Backtest placeholder (to be implemented).")
def backtest():
    print("[yellow]Backtest engine is TODO – coming in Section 14.[/yellow]")
    sys.exit(0)

@app.command(help="Run background scheduler (Ctrl+C to stop).")
def scheduler():
    from app.scheduler import run as run_scheduler

    run_scheduler()


if __name__ == "__main__":
    app()
