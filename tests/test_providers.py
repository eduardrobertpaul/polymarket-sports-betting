import pytest

from app.providers.odds_api import OddsAPIProvider
from app.providers.prop_odds import PropOddsProvider


@pytest.mark.asyncio
async def test_odds_api_returns_empty_without_key() -> None:
    provider = OddsAPIProvider(api_key=None)
    assert await provider.fetch_fixture_odds("fake") == []


@pytest.mark.asyncio
async def test_prop_odds_returns_empty_without_key() -> None:
    provider = PropOddsProvider(api_key=None)
    assert await provider.fetch_fixture_odds("fake") == []
