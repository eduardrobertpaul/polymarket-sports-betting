"""
Background scheduler using APScheduler AsyncIO.

Jobs:
1. fetch_all_fixtures – every 5 min
2. purge_memory_cache  – every 30 min
3. purge_old_snapshots – daily at 04:00
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from app.providers import get_active_providers
from app.polymarket.aggregation import OutcomeOdds, ProviderSnapshot
from app.polymarket.aggregation import snapshots_to_true_probs
from app.polymarket.client import fetch_market_probs
from app.polymarket.staking import compute_edge
from app.db.base import async_session_factory, engine
from app.providers.base import _CACHE

# A demo list; in production fetch from DB
TRACKED_FIXTURES = ["123", "456"]

scheduler = AsyncIOScheduler()

# --------------------------------------------------------------------------- #
#  Job 1 – Pull odds for all fixtures                                          #
# --------------------------------------------------------------------------- #
async def fetch_all_fixtures():
    for fid in TRACKED_FIXTURES:
        snaps = []
        for pname, provider in get_active_providers().items():
            rows = await provider.fetch_fixture_odds(fid)
            odds = [OutcomeOdds(r["outcome"], r["decimal_odds"]) for r in rows]
            snaps.append(
                ProviderSnapshot(
                    provider=pname,
                    fixture_id=fid,
                    ts=datetime.utcnow(),
                    odds=odds,
                )
            )

        # write to DB (simplified)
        async with async_session_factory() as sess:
            for s in snaps:
                for o in s.odds:
                    await sess.execute(
                        text(
                            "INSERT INTO odds_snapshots "
                            "(fixture_id, provider_id, ts, outcome, decimal_odds) "
                            "VALUES (:f, :p, :ts, :outcome, :odds)"
                        ),
                        dict(
                            f=s.fixture_id,
                            p=s.provider,
                            ts=s.ts,
                            outcome=o.outcome,
                            odds=o.decimal_odds,
                        ),
                    )
            await sess.commit()


# --------------------------------------------------------------------------- #
#  Job 2 – Purge in-memory provider cache                                      #
# --------------------------------------------------------------------------- #
def purge_memory_cache():
    _CACHE.clear()


# --------------------------------------------------------------------------- #
#  Job 3 – Delete DB snapshots older than 30 days                              #
# --------------------------------------------------------------------------- #
async def purge_old_snapshots():
    cutoff = datetime.utcnow() - timedelta(days=30)
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM odds_snapshots WHERE ts < :cutoff"), {"cutoff": cutoff}
        )


# --------------------------------------------------------------------------- #
#  Register jobs                                                               #
# --------------------------------------------------------------------------- #
scheduler.add_job(
    fetch_all_fixtures,
    IntervalTrigger(minutes=5),
    name="fetch_all_fixtures",
)

scheduler.add_job(
    purge_memory_cache,
    IntervalTrigger(minutes=30),
    name="purge_memory_cache",
)

scheduler.add_job(
    purge_old_snapshots,
    CronTrigger(hour=4, minute=0),
    name="purge_old_snapshots",
)


def run():
    """Entry-point for CLI."""
    scheduler.start()
    print("Scheduler running… Press Ctrl+C to exit.")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
