from __future__ import annotations

from typing import Dict

from .odds_api import OddsAPIProvider
from .prop_odds import PropOddsProvider
from .base import OddsProvider


def get_active_providers() -> Dict[str, OddsProvider]:
    """
    Instantiate providers whose API keys are present.
    Returns mapping {provider_name: provider_instance}.
    """
    providers: Dict[str, OddsProvider] = {}

    odds_api = OddsAPIProvider()
    if odds_api.api_key:
        providers[odds_api.name] = odds_api

    prop_odds = PropOddsProvider()
    if prop_odds.api_key:
        providers[prop_odds.name] = prop_odds

    return providers
