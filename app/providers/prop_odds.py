from __future__ import annotations

import os
from typing import Any, Dict, List

from .base import OddsProvider


class PropOddsProvider(OddsProvider):
    """Free-tier *Prop_Odds* client (moneyline only)."""

    name = "prop_odds_api"
    base_url = "https://api.prop-odds.com/beta"

    def __init__(self, api_key: str | None = None) -> None:
        api_key = api_key or os.getenv("PROP_ODDS_API_KEY")
        super().__init__(api_key)

    async def fetch_fixture_odds(  # type: ignore[override]
        self,
        fixture_id: str,
        *,
        sport: str = "soccer",
        market: str = "h2h",
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []

        endpoint = f"{self.base_url}/{sport}/odds"
        params: Dict[str, Any] = {
            "regions": "us",
            "markets": market,
            "apiKey": self.api_key,
        }

        data = await self._get_json(endpoint, params)
        if not data or "events" not in data:
            return []

        for event in data["events"]:
            if str(event.get("id")) == str(fixture_id):
                try:
                    outcomes = event["markets"][0]["outcomes"]
                except (KeyError, IndexError):
                    break
                return [
                    {
                        "outcome": o["name"],
                        "decimal_odds": float(o.get("oddsDecimal") or o.get("price")),
                    }
                    for o in outcomes
                ]
        return []
