from __future__ import annotations

import os
from typing import Any, Dict, List, cast

from .base import OddsProvider


class OddsAPIProvider(OddsProvider):
    """Free-tier *The Odds API* client (moneyline only)."""

    name = "the_odds_api"
    base_url = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str | None = None) -> None:
        api_key = api_key or os.getenv("ODDS_API_KEY")
        super().__init__(api_key)

    # --------------------------------------------------------------------- #
    #  Public                                                                 #
    # --------------------------------------------------------------------- #
    async def fetch_fixture_odds(  # type: ignore[override]
        self,
        fixture_id: str,
        *,
        sport: str = "soccer",
        market: str = "h2h",
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []

        endpoint = f"{self.base_url}/sports/{sport}/odds"
        params: Dict[str, Any] = {
            "regions": "us",
            "markets": market,
            "apiKey": self.api_key,
            "bookmakers": "pinnacle",
            "dateFormat": "iso",
        }

        raw = await self._get_json(endpoint, params)
        if not raw:
            return []

        events = cast(List[Dict[str, Any]], raw)

        for event in events:
            if str(event.get("id")) == str(fixture_id):
                try:
                    outcomes = event["bookmakers"][0]["markets"][0]["outcomes"]
                except (KeyError, IndexError):
                    break
                return [
                    {"outcome": o["name"], "decimal_odds": float(o["price"])}
                    for o in outcomes
                ]
        return []
