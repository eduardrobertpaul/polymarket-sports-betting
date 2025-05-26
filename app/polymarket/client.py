"""
Async client for Polymarket's public GraphQL API.

Only the moneyline-style markets (Yes/No or Home/Draw/Away) are needed
for this project, so we expose a single high-level function:

    await fetch_market_probs("will-bitcoin-exceed-80k-by-2025")

Which returns something like:
    [{"outcome": "Yes", "prob": 0.43}, {"outcome": "No", "prob": 0.57}]
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import aiohttp
from aiolimiter import AsyncLimiter

_POLY_URL = "https://www.polymarket.com/gql"
_RATE_LIMITER = AsyncLimiter(1, 1)  # 1 request/second
_SESSION: aiohttp.ClientSession | None = None

_QUERY = """
query Market($slug: String!) {
  market(slug: $slug) {
    title
    outcomes {
      name
      price
    }
  }
}
"""


async def _get_session() -> aiohttp.ClientSession:
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession(
            headers={"content-type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=10),
        )
    return _SESSION


async def fetch_market_probs(slug: str) -> List[Dict[str, float]]:
    """
    Fetch outcomes + prices for a single Polymarket market.

    `price` is already a probability (0-1) representing the cost of a
    1-USDC share, so no further normalisation is required.
    """
    payload: Dict[str, Any] = {"query": _QUERY, "variables": {"slug": slug}}

    async with _RATE_LIMITER:
        session = await _get_session()
        async with session.post(_POLY_URL, json=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(
                    f"Polymarket API error {resp.status}: {await resp.text()}"
                )
            data = await resp.json()

    try:
        outcomes = data["data"]["market"]["outcomes"]
    except (KeyError, TypeError):
        raise ValueError(f"Market slug '{slug}' not found or malformed response")

    return [
        {"outcome": o["name"], "prob": float(o["price"])} for o in outcomes
    ]


# --------------------------------------------------------------------------- #
#  Convenience helper for quick CLI testing                                   #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    import json, sys

    async def _demo() -> None:
        slug = sys.argv[1] if len(sys.argv) > 1 else "will-bitcoin-exceed-80k-by-2025"
        probs = await fetch_market_probs(slug)
        print(json.dumps(probs, indent=2))

    asyncio.run(_demo())
