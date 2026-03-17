"""Steam CS2 player stats service.

Fetches aggregate CS2 statistics for a Steam user via the public Steam Web API.
Note: Valve does not expose a per-match CS2 history endpoint through the public
Steam Web API.  This service provides lifetime aggregate stats (K/D ratio, win
rate, total playtime, etc.) which are surfaced on the Active Roster card.

API used:
    ISteamUserStats/GetUserStatsForGame/v2/?appid=730&steamid=<steam_id>

Rate limiting:
    Uses ``RateLimiter(provider="steam", rate_per_second=5.0, burst=10)``
    Steam Web API allows ~10k requests/day per API key.

Circuit breaker:
    Uses ``CircuitBreaker(provider="steam", failure_threshold=5, cooldown_seconds=120)``

Usage::

    from apps.user_profile.services.steam_cs2_stats_service import fetch_cs2_stats

    stats = fetch_cs2_stats(steam_id="76561198000000000")
    # stats: {"steam_id": ..., "total_kills": ..., "kd_ratio": ..., ...}
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

from apps.user_profile.services.base_game_api import GameAPIError
from apps.user_profile.services.circuit_breaker import CircuitBreaker
from apps.user_profile.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_CS2_APP_ID = 730
_STATS_URL = "https://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v2/"
_TIMEOUT = 10

_PROVIDER = "steam"
_rate_limiter = RateLimiter(provider=_PROVIDER, rate_per_second=5.0, burst=10)
_circuit_breaker = CircuitBreaker(provider=_PROVIDER, failure_threshold=5, cooldown_seconds=120)

# Stat keys from Steam API mapped to our normalized field names
_STAT_MAP: dict[str, str] = {
    "total_kills": "total_kills",
    "total_deaths": "total_deaths",
    "total_time_played": "total_time_played_seconds",
    "total_wins": "total_wins",
    "total_rounds_played": "total_rounds_played",
    "total_mvps": "total_mvps",
    "total_headshots": "total_headshots",
    "total_damage_done": "total_damage_done",
    "total_wins_pistolround": "total_pistol_round_wins",
    "total_gun_game_rounds_won": "total_gun_game_wins",
}


class CS2StatsError(GameAPIError):
    """Raised by CS2 stats service. Subclass of GameAPIError for uniform handling."""


def fetch_cs2_stats(steam_id: str) -> dict[str, Any]:
    """Fetch lifetime CS2 aggregate stats for a Steam user.

    Args:
        steam_id: 17-digit Steam ID string.

    Returns:
        Normalized stats dict with at minimum ``{"steam_id", "total_kills",
        "total_deaths", "kd_ratio", "total_wins", "total_rounds_played",
        "win_rate", "headshot_rate", "total_time_played_seconds"}``.

    Raises:
        CS2StatsError: on any failure (network, auth, missing data, rate-limit).
    """
    api_key = getattr(settings, "STEAM_API_KEY", "").strip()
    if not api_key:
        raise CS2StatsError(
            "STEAM_CONFIG_MISSING",
            "STEAM_API_KEY is not configured",
            500,
            provider=_PROVIDER,
            metadata={"missing": ["STEAM_API_KEY"]},
        )

    if not _circuit_breaker.allow_request():
        raise CS2StatsError(
            "STEAM_CIRCUIT_OPEN",
            "Steam API circuit breaker is open — upstream may be unavailable",
            503,
            provider=_PROVIDER,
        )

    if not _rate_limiter.try_acquire():
        raise CS2StatsError(
            "STEAM_RATE_LIMITED",
            "Steam API rate limit exceeded — retry later",
            429,
            provider=_PROVIDER,
        )

    params = {
        "key": api_key,
        "steamid": steam_id,
        "appid": _CS2_APP_ID,
    }

    try:
        response = requests.get(_STATS_URL, params=params, timeout=_TIMEOUT)
    except requests.Timeout as exc:
        _circuit_breaker.record_failure()
        raise CS2StatsError("STEAM_TIMEOUT", "Steam stats request timed out", 504, provider=_PROVIDER) from exc
    except requests.RequestException as exc:
        _circuit_breaker.record_failure()
        raise CS2StatsError("STEAM_NETWORK_ERROR", "Unable to reach Steam Web API", 502, provider=_PROVIDER) from exc

    if response.status_code == 403:
        _circuit_breaker.record_failure()
        raise CS2StatsError(
            "STEAM_PRIVATE_PROFILE",
            "Steam profile is private — CS2 stats not accessible",
            403,
            provider=_PROVIDER,
            metadata={"steam_id": steam_id},
        )

    if response.status_code >= 400:
        _circuit_breaker.record_failure()
        raise CS2StatsError(
            "STEAM_STATS_FAILED",
            f"Steam stats API returned {response.status_code}",
            502,
            provider=_PROVIDER,
            metadata={"steam_id": steam_id, "status_code": response.status_code},
        )

    try:
        payload = response.json()
    except ValueError as exc:
        _circuit_breaker.record_failure()
        raise CS2StatsError("STEAM_STATS_PARSE_ERROR", "Steam stats response was not valid JSON", 502, provider=_PROVIDER) from exc

    _circuit_breaker.record_success()

    stats_list: list[dict] = (
        payload.get("playerstats", {}).get("stats", [])
        if isinstance(payload, dict)
        else []
    )

    if not stats_list:
        raise CS2StatsError(
            "STEAM_NO_STATS",
            "No CS2 stats found — player may not have played CS2 or stats are private",
            404,
            provider=_PROVIDER,
            metadata={"steam_id": steam_id},
        )

    raw: dict[str, int] = {s["name"]: int(s.get("value", 0)) for s in stats_list if "name" in s}

    return _normalize_cs2_stats(steam_id, raw)


def _normalize_cs2_stats(steam_id: str, raw: dict[str, int]) -> dict[str, Any]:
    """Map raw Steam stat names to normalized fields and compute derived ratios."""
    normalized: dict[str, Any] = {"steam_id": steam_id}

    for steam_key, our_key in _STAT_MAP.items():
        normalized[our_key] = raw.get(steam_key, 0)

    kills = normalized.get("total_kills", 0)
    deaths = max(1, normalized.get("total_deaths", 1))
    rounds = max(1, normalized.get("total_rounds_played", 1))

    normalized["kd_ratio"] = round(kills / deaths, 2)
    normalized["win_rate"] = round(normalized.get("total_wins", 0) / rounds * 100, 1)
    normalized["headshot_rate"] = round(normalized.get("total_headshots", 0) / max(1, kills) * 100, 1)

    return normalized
