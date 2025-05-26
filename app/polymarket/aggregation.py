"""
Odds normalisation, smoothing, and cross-provider aggregation utilities.

These functions are *pure* (no DB or HTTP) so they can be unit-tested easily
and reused in CLI, web, or background jobs.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import math
import pandas as pd


# --------------------------------------------------------------------------- #
#  Data containers                                                             #
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class OutcomeOdds:
    outcome: str
    decimal_odds: float


@dataclass(slots=True)
class ProviderSnapshot:
    provider: str
    fixture_id: str
    ts: datetime
    odds: List[OutcomeOdds]


# --------------------------------------------------------------------------- #
#  Core maths                                                                  #
# --------------------------------------------------------------------------- #
def decimal_to_implied(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be > 1.0")
    return 1.0 / decimal_odds


def normalise_snapshot(snapshot: ProviderSnapshot) -> Dict[str, float]:
    """
    Return a dict {outcome: normalised_prob} that sums to 1.0 for this provider.
    Also returns overround separately if caller needs it.
    """
    implied = {o.outcome: decimal_to_implied(o.decimal_odds) for o in snapshot.odds}
    total = sum(implied.values())
    if math.isclose(total, 0.0):
        raise ValueError("Snapshot total implied prob is zero.")
    return {k: v / total for k, v in implied.items()}


def ewma_probs(
    history: List[Dict[str, float]],
    alpha: float = 0.6,
) -> Dict[str, float]:
    """
    Exponentially-weighted moving average of a list of probability dicts.
    Each newer dict has higher weight.  Keys (outcomes) are unioned.
    """
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha must be in (0, 1]")
    if not history:
        return {}

    # Initialise with the oldest snapshot
    smoothed: Dict[str, float] = dict(history[0])
    for probs in history[1:]:
        for outcome, p in probs.items():
            prev = smoothed.get(outcome, p)
            smoothed[outcome] = alpha * p + (1 - alpha) * prev
    # Renormalise (EWMA may drift slightly)
    total = sum(smoothed.values())
    return {k: v / total for k, v in smoothed.items()}


def aggregate_providers(
    provider_probs: Dict[str, Dict[str, float]],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Combine normalised probability dicts from multiple providers.

    * If `weights` dict is None, simple arithmetic mean is used.
    * Otherwise weight per provider = weights[provider] (will be renormalised).
    """
    if not provider_probs:
        return {}

    # Default weight = 1 for each provider
    w = {p: 1.0 for p in provider_probs} if weights is None else weights.copy()
    # Renormalise weights to sum 1
    w_total = sum(w.values())
    w = {p: v / w_total for p, v in w.items()}

    agg: Dict[str, float] = defaultdict(float)
    for provider, probs in provider_probs.items():
        for outcome, p in probs.items():
            agg[outcome] += w.get(provider, 0.0) * p

    # Ensure exact sum -> 1.0
    total = sum(agg.values())
    return {k: v / total for k, v in agg.items()}


# --------------------------------------------------------------------------- #
#  Convenience wrapper                                                         #
# --------------------------------------------------------------------------- #
def snapshots_to_true_probs(
    snapshots: Iterable[ProviderSnapshot],
    history_window: int = 3,
    alpha: float = 0.6,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Full pipeline:

    1. Normalise each snapshot.
    2. EWMA-smooth per provider over the last `history_window` snapshots.
    3. Weighted average across providers → “true” probability estimate.
    """
    by_provider: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    for snap in snapshots:
        by_provider[snap.provider].append(normalise_snapshot(snap))

    # Keep only last N per provider, then smooth
    provider_smoothed: Dict[str, Dict[str, float]] = {
        p: ewma_probs(hist[-history_window:], alpha=alpha)
        for p, hist in by_provider.items()
    }

    return aggregate_providers(provider_smoothed, weights=weights)


# --------------------------------------------------------------------------- #
#  Optional helper: to/from pandas                                             #
# --------------------------------------------------------------------------- #
def snapshots_to_dataframe(snapshots: Iterable[ProviderSnapshot]) -> pd.DataFrame:
    """
    Flatten snapshots → DataFrame for easier ad-hoc analysis:
    columns = provider, fixture_id, ts, outcome, decimal_odds
    """
    rows = []
    for snap in snapshots:
        for o in snap.odds:
            rows.append(
                {
                    "provider": snap.provider,
                    "fixture_id": snap.fixture_id,
                    "ts": snap.ts,
                    "outcome": o.outcome,
                    "decimal_odds": o.decimal_odds,
                }
            )
    return pd.DataFrame(rows)
