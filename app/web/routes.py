from __future__ import annotations
from app.logging_config import logger

import asyncio
from typing import Any, Dict

from flask import render_template, request

from . import app
from app.providers import get_active_providers
from app.polymarket.aggregation import (
    ProviderSnapshot,
    OutcomeOdds,
    snapshots_to_true_probs,
)
from app.polymarket.client import fetch_market_probs
from app.polymarket.staking import compute_edge, recommend
from datetime import datetime

# Hard-coded fixture list for demo
FIXTURES = {
    "123": "Team A vs Team B",
    "456": "Team C vs Team D",
}


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #
async def _pipeline(fixture_id: str) -> Dict[str, Any]:
    try:
        # 1. Provider odds
        snaps = []
        for name, provider in get_active_providers().items():
            rows = await provider.fetch_fixture_odds(fixture_id)
            if not rows:
                continue
            odds = [OutcomeOdds(r["outcome"], r["decimal_odds"]) for r in rows]
            snaps.append(
                ProviderSnapshot(
                    provider=name,
                    fixture_id=fixture_id,
                    ts=datetime.utcnow(),
                    odds=odds,
                )
            )
        
        # 2. True probs
        true_p = snapshots_to_true_probs(snaps)

        # 3. Polymarket
        market_rows = await fetch_market_probs(fixture_id)
        market_p = {r["outcome"]: r["prob"] for r in market_rows}

        # 4. Edge & reco
        edges = compute_edge(true_p, market_p)
        recs = recommend(
            true_p,
            market_p,
            bankroll=100,
        )
        return {
            "true_probs": true_p,
            "market_probs": market_p,
            "edges": edges,
            "recs": recs,
        }
    except Exception as exc:
        logger.exception(f"Pipeline error for fixture {fixture_id}: {exc}")
        # Fallback: no recommendations
        return {
            "true_probs": {},
            "market_probs": {},
            "edges": {},
            "recs": {},
        }


# --------------------------------------------------------------------------- #
#  Routes                                                                     #
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("index.html", fixtures=FIXTURES)


@app.route("/fixture/<fixture_id>")
def fixture_page(fixture_id: str):
    if fixture_id not in FIXTURES:
        return "Fixture not found", 404
    return render_template(
        "fixture.html",
        fixture_id=fixture_id,
        fixture_label=FIXTURES[fixture_id],
    )


@app.route("/fixture/<fixture_id>/recommendation")
def fixture_recommendation(fixture_id: str):
    data = asyncio.run(_pipeline(fixture_id))
    return render_template("recommendation_snippet.html", **data)
