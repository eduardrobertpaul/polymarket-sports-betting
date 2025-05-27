from __future__ import annotations

import abc
import time
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Tuple, TypeVar
from aiohttp import ClientError  # add to imports
from app.logging_config import logger  # new import
import aiohttp
from aiolimiter import AsyncLimiter

_JSON = Dict[str, Any]
_T = TypeVar("_T")

# --------------------------------------------------------------------------- #
#  In-memory TTL cache (60 s)                                                 #
# --------------------------------------------------------------------------- #
_CACHE: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 60  # seconds


def _cache_key(url: str, params: Dict[str, Any]) -> str:
    return f"{url}|{tuple(sorted(params.items()))}"


def _ttl_cache(
    func: Callable[["OddsProvider", str, Dict[str, Any]], Awaitable[_T]],
) -> Callable[["OddsProvider", str, Dict[str, Any]], Awaitable[_T]]:
    """Async TTL cache decorator."""

    @wraps(func)
    async def wrapper(self: "OddsProvider", url: str, params: Dict[str, Any]) -> _T:
        key = _cache_key(url, params)
        ts, data = _CACHE.get(key, (0.0, None))
        if time.time() - ts < _CACHE_TTL:
            return data  # type: ignore[return-value]

        data = await func(self, url, params)
        _CACHE[key] = (time.time(), data)
        return data

    return wrapper


# --------------------------------------------------------------------------- #
#  Abstract base provider                                                     #
# --------------------------------------------------------------------------- #
_rate_limiter = AsyncLimiter(max_rate=1, time_period=1)  # 1 req / s


class OddsProvider(abc.ABC):
    """Abstract async odds provider."""

    name: str
    base_url: str
    monthly_quota: int | None = None

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––– #
    #  Helpers                                                               #
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––– #
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    @_ttl_cache
    async def _get_json(self, url: str, params: Dict[str, Any]) -> _JSON | None:
        """Rate-limited GET returning JSON (or None on error)."""
        async with _rate_limiter:
            session = await self._get_session()
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    logger.warning(
                        f"[provider:{self.name}] HTTP {resp.status} for {url}"
                    )
            except ClientError as e:
                logger.error(f"[provider:{self.name}] Network error: {e}")
        return None

    @abc.abstractmethod
    async def fetch_fixture_odds(
        self, fixture_id: str, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Return `[{'outcome': str, 'decimal_odds': float}, …]`"""
        ...

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
