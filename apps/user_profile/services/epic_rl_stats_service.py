"""Epic Rocket League stats service.

Fetches profile data for an Epic Games account using the stored OAuth access token.

Scope limitation:
    The current Epic OAuth integration uses the ``basic_profile`` scope only.
    Full Rocket League match history and ranked stats require the ``rocketleague``
    product scope (Psyonix/Epic game-specific permissions).

    To enable full stats, add ``rocketleague`` to ``EPIC_OAUTH_SCOPES`` in settings
    and re-link accounts.  The full stats endpoint is:
        GET https://api.epicgames.dev/epic/rl/v3/player/stats?accountId=<account_id>

What this service DOES implement (with ``basic_profile``):
    - Fetches the Epic account display name via OpenID userinfo endpoint.
    - Updates ``GameProfile.ign`` and ``passport.metadata.epic_display_name``.
    - Records ``GameOAuthConnection.last_synced_at``.
    - Proactively calls ``refresh_epic_access_token()`` if the token is expired before fetching.

Rate limiting:
    Uses ``RateLimiter(provider="epic", rate_per_second=3.0, burst=6)``

Circuit breaker:
    Uses ``CircuitBreaker(provider="epic", failure_threshold=5, cooldown_seconds=120)``

Usage::

    from apps.user_profile.services.epic_rl_stats_service import fetch_epic_profile

    conn = GameOAuthConnection.objects.get(pk=...)
    profile_data = fetch_epic_profile(conn)
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.utils import timezone

from apps.user_profile.services.base_game_api import GameAPIError
from apps.user_profile.services.circuit_breaker import CircuitBreaker
from apps.user_profile.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_EPIC_USERINFO_URL = "https://api.epicgames.dev/epic/oauth/v2/userinfo"
_TIMEOUT = 10
_PROVIDER = "epic"

_rate_limiter = RateLimiter(provider=_PROVIDER, rate_per_second=3.0, burst=6)
_circuit_breaker = CircuitBreaker(provider=_PROVIDER, failure_threshold=5, cooldown_seconds=120)


class EpicStatsError(GameAPIError):
    """Raised by Epic stats service. Subclass of GameAPIError for uniform handling."""


def fetch_epic_profile(conn: Any) -> dict[str, Any]:
    """Fetch Epic account profile data using the stored OAuth access token.

    Auto-refreshes the token if it is expired or expiring within 5 minutes.

    Args:
        conn: ``GameOAuthConnection`` instance with ``provider=EPIC``.

    Returns:
        Normalized profile dict: ``{"account_id", "display_name", "last_synced_at"}``.

    Raises:
        EpicStatsError: on any failure (token refresh, network, parse).
    """
    from apps.user_profile.services.oauth_epic_service import refresh_epic_access_token, EpicOAuthError

    # Refresh token proactively if expiring within 5 minutes
    if conn.expires_at is None or conn.expires_at <= timezone.now() + timezone.timedelta(minutes=5):
        if conn.refresh_token:
            try:
                conn = refresh_epic_access_token(conn)
            except EpicOAuthError as exc:
                raise EpicStatsError(
                    "EPIC_TOKEN_REFRESH_FAILED",
                    f"Failed to refresh Epic token: {exc.message}",
                    exc.status_code,
                    provider=_PROVIDER,
                ) from exc

    if not conn.access_token:
        raise EpicStatsError(
            "EPIC_NO_ACCESS_TOKEN",
            "No access token available for Epic profile fetch",
            401,
            provider=_PROVIDER,
        )

    if not _circuit_breaker.allow_request():
        raise EpicStatsError(
            "EPIC_CIRCUIT_OPEN",
            "Epic API circuit breaker is open — upstream may be unavailable",
            503,
            provider=_PROVIDER,
        )

    if not _rate_limiter.try_acquire():
        raise EpicStatsError(
            "EPIC_RATE_LIMITED",
            "Epic API rate limit exceeded — retry later",
            429,
            provider=_PROVIDER,
        )

    try:
        response = requests.get(
            _EPIC_USERINFO_URL,
            headers={"Authorization": f"Bearer {conn.access_token}"},
            timeout=_TIMEOUT,
        )
    except requests.Timeout as exc:
        _circuit_breaker.record_failure()
        raise EpicStatsError("EPIC_TIMEOUT", "Epic userinfo request timed out", 504, provider=_PROVIDER) from exc
    except requests.RequestException as exc:
        _circuit_breaker.record_failure()
        raise EpicStatsError("EPIC_NETWORK_ERROR", "Unable to reach Epic userinfo endpoint", 502, provider=_PROVIDER) from exc

    if response.status_code == 401:
        _circuit_breaker.record_failure()
        raise EpicStatsError(
            "EPIC_TOKEN_INVALID",
            "Epic access token rejected — user must re-authenticate",
            401,
            provider=_PROVIDER,
        )

    if response.status_code >= 400:
        _circuit_breaker.record_failure()
        raise EpicStatsError(
            "EPIC_PROFILE_FETCH_FAILED",
            f"Epic userinfo API returned {response.status_code}",
            502,
            provider=_PROVIDER,
            metadata={"status_code": response.status_code},
        )

    _circuit_breaker.record_success()

    try:
        payload = response.json() if hasattr(response, "json") else {}
    except ValueError:
        payload = {}

    # Epic OpenID userinfo: sub=account_id, preferred_username=displayName
    account_id = str(payload.get("sub", "") or conn.provider_account_id).strip()
    display_name = str(payload.get("preferred_username", "") or payload.get("name", "")).strip()

    return {
        "account_id": account_id,
        "display_name": display_name or account_id,
        "last_synced_at": timezone.now().isoformat(),
    }
