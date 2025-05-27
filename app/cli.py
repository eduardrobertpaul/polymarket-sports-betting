from __future__ import annotations   # ← first line, nothing before it

import json
import sys
from typing import Any, Dict, List

import asyncio
import typer
from rich import print

from app.logging_config import configure_logging, logger
from app.polymarket.aggregation import snapshots_to_true_probs, ProviderSnapshot, OutcomeOdds
from app.polymarket.staking import recommend, compute_edge
from app.providers import get_active_providers
from app.polymarket.client import fetch_market_probs

configure_logging()

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

    try:
        data = asyncio.run(_run())
    except Exception as exc:  # broad, but CLI shouldn’t crash
        logger.exception(f"CLI command failed: {exc}")
        typer.Exit(code=1)

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

    try:
        result = asyncio.run(_run())
    except Exception as exc:  # broad, but CLI shouldn’t crash
        logger.exception(f"CLI command failed: {exc}")
        typer.Exit(code=1)
    print(json.dumps(result, indent=2))


@app.command(help="Run back-test, update metrics, and print summary.")
def backtest(
    write: bool = typer.Option(False, help="Write results into provider_metrics"),
):
    import asyncio
    from app.backtest import summary, update_provider_metrics

    scores, table = asyncio.run(summary())
    print(table)
    if write:
        asyncio.run(update_provider_metrics())
        print("[green]Metrics table updated.[/green]")


@app.command(help="Run background scheduler (Ctrl+C to stop).")
def scheduler():
    from app.scheduler import run as run_scheduler

    run_scheduler()


if __name__ == "__main__":
    app()
