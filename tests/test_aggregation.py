from datetime import datetime, timedelta

import pytest

from app.polymarket.aggregation import (
    OutcomeOdds,
    ProviderSnapshot,
    aggregate_providers,
    decimal_to_implied,
    ewma_probs,
    normalise_snapshot,
    snapshots_to_true_probs,
)


def _snap(
    provider: str,
    h: float,
    home: float,
    draw: float,
    away: float,
) -> ProviderSnapshot:
    """Convenience factory."""
    return ProviderSnapshot(
        provider=provider,
        fixture_id="123",
        ts=datetime.utcnow() + timedelta(minutes=h),
        odds=[
            OutcomeOdds("home", home),
            OutcomeOdds("draw", draw),
            OutcomeOdds("away", away),
        ],
    )


@pytest.mark.parametrize(
    "decimal, implied",
    [(2.0, 0.5), (3.0, 1 / 3), (1.5, 2 / 3)],
)
def test_decimal_to_implied(decimal: float, implied: float) -> None:
    assert pytest.approx(decimal_to_implied(decimal), rel=1e-9) == implied


def test_normalise_snapshot_sums_to_one() -> None:
    snap = _snap("p1", 0, 2.0, 3.0, 4.0)
    probs = normalise_snapshot(snap)
    assert pytest.approx(sum(probs.values()), rel=1e-12) == 1.0


def test_ewma_smokes() -> None:
    hist = [
        {"a": 0.4, "b": 0.6},
        {"a": 0.5, "b": 0.5},
        {"a": 0.6, "b": 0.4},
    ]
    res = ewma_probs(hist, alpha=0.5)
    assert pytest.approx(sum(res.values()), rel=1e-12) == 1.0
    assert 0.4 < res["a"] < 0.6


def test_aggregate_providers_simple_average() -> None:
    probs = {
        "p1": {"x": 0.5, "y": 0.5},
        "p2": {"x": 0.3, "y": 0.7},
    }
    agg = aggregate_providers(probs, weights=None)
    assert pytest.approx(agg["x"], rel=1e-12) == 0.4
    assert pytest.approx(sum(agg.values()), rel=1e-12) == 1.0


def test_full_pipeline() -> None:
    snaps = [
        _snap("p1", 0, 2.0, 3.2, 4.0),
        _snap("p1", 1, 1.9, 3.4, 4.1),
        _snap("p2", 0, 2.1, 3.1, 4.0),
    ]
    true_p = snapshots_to_true_probs(snaps)
    assert pytest.approx(sum(true_p.values()), rel=1e-12) == 1.0
