"""
Back-testing utilities.

Workflow:
1. Load odds_snapshots joined with results.
2. Compute Brier score per provider.
3. Compute simple ROI using Kelly stake fractions (optional).
4. Update provider_metrics table.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Dict, Tuple

from sqlalchemy import text, select, func
from sqlalchemy.exc import OperationalError
from app.db.base import async_session_factory
from app.db.models import ProviderMetrics


async def compute_brier_scores() -> Dict[str, float]:
    """
    Returns {provider: brier_score}.
    Lower is better, perfect = 0.
    """
    try:
        sql = text(
            """
            SELECT provider_id,
                   outcome = winner AS correct,
                   implied_norm
            FROM odds_snapshots
            JOIN results USING (fixture_id, outcome)
            """
        )

        sums: Dict[str, float] = defaultdict(float)
        counts: Dict[str, int] = defaultdict(int)

        async with async_session_factory() as sess:
            result = await sess.execute(sql)
            rows = result.fetchall()
    except Exception:
        # Table missing or other DB error -> empty scores
        return {}

    for provider, correct, prob in rows:
        error = (1.0 - prob) ** 2 if correct else (0.0 - prob) ** 2
        sums[provider] += error
        counts[provider] += 1

    return {p: sums[p] / counts[p] for p in sums}


async def update_provider_metrics():
    scores = await compute_brier_scores()
    async with async_session_factory() as sess:
        for provider, brier in scores.items():
            await sess.merge(
                ProviderMetrics(provider_id=provider, brier_score=brier)
            )
        await sess.commit()


async def summary() -> Tuple[Dict[str, float], str]:
    scores = await compute_brier_scores()
    pretty = "\n".join(
        f"{p:15}  Brier={b:.4f}" for p, b in sorted(scores.items(), key=lambda x: x[1])
    )
    return scores, pretty