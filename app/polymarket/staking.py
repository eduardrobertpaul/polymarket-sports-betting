"""
Edge calculation and fractional-Kelly staking utilities.

* Polymarket expresses prices as probabilities (0–1).  
* Traditional bookmaker odds (decimal) must be converted by caller if needed.
"""

from __future__ import annotations

from typing import Dict


# --------------------------------------------------------------------------- #
#  Edge                                                                       #
# --------------------------------------------------------------------------- #
def compute_edge(
    true_probs: Dict[str, float],
    market_probs: Dict[str, float],
) -> Dict[str, float]:
    """
    Edge = our 'true' probability minus market probability for each outcome.

    Outcomes present in `true_probs` but missing in `market_probs` are treated
    as market prob = 0.
    """
    return {
        outcome: true_probs[outcome] - market_probs.get(outcome, 0.0)
        for outcome in true_probs
    }


# --------------------------------------------------------------------------- #
#  Fractional Kelly                                                           #
# --------------------------------------------------------------------------- #
def fractional_kelly(
    p_true: float,
    price: float,
    *,
    kelly_fraction: float = 0.5,
    max_cap: float = 0.10,
) -> float:
    """
    Return stake fraction of bankroll suggested by fractional Kelly.

    * `price` is Polymarket probability (cost of a $1 share).
    * Uses the standard binary-payout Kelly formula:
        f* = (p*(b+1) - 1) / b,   where b = 1/price - 1
    * Applies `kelly_fraction` (0.5 = half-Kelly) and caps at `max_cap`.
    """
    if not 0.0 < p_true < 1.0:
        raise ValueError("p_true must be in (0,1)")
    if not 0.0 < price < 1.0:
        raise ValueError("price must be in (0,1)")
    if price >= 1.0:
        return 0.0

    b = 1 / price - 1
    f_star = (p_true * (b + 1) - 1) / b
    stake = max(0.0, kelly_fraction * f_star)
    return min(stake, max_cap)


# --------------------------------------------------------------------------- #
#  Recommendation                                                             #
# --------------------------------------------------------------------------- #
def recommend(
    true_probs: Dict[str, float],
    market_probs: Dict[str, float],
    *,
    edge_threshold: float = 0.02,
    bankroll: float = 100.0,
    kelly_fraction: float = 0.5,
    max_cap: float = 0.10,
) -> Dict[str, float]:
    """
    Return `{outcome: stake_units}` for outcomes where edge ≥ threshold.

    `stake_units` = fraction * bankroll.
    """
    recs: Dict[str, float] = {}
    edges = compute_edge(true_probs, market_probs)

    for outcome, edge in edges.items():
        if edge < edge_threshold:
            continue
        stake_frac = fractional_kelly(
            p_true=true_probs[outcome],
            price=market_probs[outcome],
            kelly_fraction=kelly_fraction,
            max_cap=max_cap,
        )
        if stake_frac > 0.0:
            recs[outcome] = round(stake_frac * bankroll, 2)

    return recs
