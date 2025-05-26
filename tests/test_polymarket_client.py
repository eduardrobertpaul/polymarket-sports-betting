import json
from typing import Any, Dict

import aiohttp
import pytest
from aioresponses import aioresponses

from app.polymarket.client import _POLY_URL, fetch_market_probs


@pytest.mark.asyncio
async def test_fetch_market_probs_parses_response() -> None:
    slug = "fake-slug"

    mock_resp: Dict[str, Any] = {
        "data": {
            "market": {
                "outcomes": [
                    {"name": "Yes", "price": 0.4},
                    {"name": "No", "price": 0.6},
                ]
            }
        }
    }

    with aioresponses() as m:
        m.post(_POLY_URL, payload=mock_resp, status=200)

        probs = await fetch_market_probs(slug)
        assert probs == [
            {"outcome": "Yes", "prob": 0.4},
            {"outcome": "No", "prob": 0.6},
        ]


@pytest.mark.asyncio
async def test_fetch_market_probs_handles_404() -> None:
    slug = "bad"
    with aioresponses() as m:
        m.post(_POLY_URL, status=404)

        with pytest.raises(RuntimeError):
            await fetch_market_probs(slug)
