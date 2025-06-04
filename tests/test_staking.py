import pytest

from app.polymarket.staking import (
    compute_edge,
    fractional_kelly,
    recommend,
)


def test_compute_edge() -> None:
    true_p = {"Yes": 0.55, "No": 0.45}
    market_p = {"Yes": 0.48, "No": 0.52}
    edges = compute_edge(true_p, market_p)
    assert pytest.approx(edges["Yes"], rel=1e-12) == 0.07
    assert pytest.approx(edges["No"], rel=1e-12) == -0.07


@pytest.mark.parametrize(
    "p_true, price, k_frac, stake",
    [
        # Kelly for share-price markets: f* = (p - c)/(1 - c)
        (0.55, 0.48, 0.5, 0.0673076923),  # positive edge, half-Kelly
        (0.6, 0.5, 1.0, 0.10),            # full Kelly then capped to 0.10
        (0.5, 0.5, 0.5, 0.0),             # zero edge → zero stake
    ],
)
def test_fractional_kelly(p_true, price, k_frac, stake) -> None:
    out = fractional_kelly(
        p_true=p_true,
        price=price,
        kelly_fraction=k_frac,
        max_cap=0.10,
    )
    assert pytest.approx(out, rel=1e-6) == stake


def test_fractional_kelly_handles_settled_market() -> None:
    """If price is >= 1 the market is effectively settled and stake should be 0."""
    out = fractional_kelly(p_true=0.6, price=1.0, kelly_fraction=1.0)
    assert out == 0.0


def test_recommend_filters_and_scales() -> None:
    true_p = {"Yes": 0.55, "No": 0.45}
    market_p = {"Yes": 0.48, "No": 0.52}
    recs = recommend(true_p, market_p, edge_threshold=0.02, bankroll=200)
    # stake_frac = 0.0673076923 → stake ≈ 13.46
    assert list(recs.keys()) == ["Yes"]
    assert pytest.approx(recs["Yes"], rel=1e-2) == 13.46
