"""
GameAPIProvider — shared protocol and error type for all external game API clients.

All game-specific service modules (Riot, Steam, Epic) should expose a thin wrapper
that conforms to this Protocol so the background sync tasks can call them uniformly.

Usage example::

    from apps.user_profile.services.base_game_api import GameAPIProvider, GameAPIError

    def sync_provider(provider: GameAPIProvider, identity_key: str) -> dict:
        try:
            return provider.fetch_match_history(identity_key)
        except GameAPIError as exc:
            ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class GameAPIError(Exception):
    """Normalized error raised by any game API provider.

    Callers should catch ``GameAPIError`` rather than provider-specific exceptions
    so sync tasks can handle all providers uniformly.

    Attributes:
        error_code: Machine-readable error code (e.g. ``STEAM_TIMEOUT``).
        message: Human-readable description.
        status_code: HTTP-like status (400=client, 401=auth, 429=rate-limit, 502=upstream, 504=timeout).
        provider: Provider name (e.g. ``"steam"``, ``"riot"``, ``"epic"``).
        metadata: Optional extra context forwarded to logging / error responses.
    """

    error_code: str
    message: str
    status_code: int = 400
    provider: str = ""
    metadata: dict[str, Any] | None = None


@runtime_checkable
class GameAPIProvider(Protocol):
    """Minimal interface all external game API clients should satisfy.

    Implementations are NOT required to inherit from this class — duck typing via
    ``runtime_checkable`` Protocol is sufficient.  The contract:

    * ``provider_name``: stable string identifier, used as the rate-limiter / circuit-breaker key.
    * ``fetch_match_history``: returns a dict with at minimum ``{"matches": [...], "identity_key": ...}``.
    * ``fetch_match_detail``: returns a dict with at minimum ``{"match_id": ..., "stats": {...}}``.

    Both methods may raise ``GameAPIError`` on any failure (network, auth, rate-limit, parse).
    They MUST NOT raise provider-specific exceptions to external callers.
    """

    provider_name: str

    def fetch_match_history(self, identity_key: str, **kwargs: Any) -> dict[str, Any]:
        """Return recent match list for *identity_key*.

        Args:
            identity_key: Provider-specific player identifier (e.g. Steam ID, PUUID, account_id).
            **kwargs: Provider-specific options (region, limit, game_mode, etc.).

        Returns:
            ``{"identity_key": str, "matches": [{"match_id": ..., ...}, ...]}``

        Raises:
            GameAPIError: on any failure.
        """
        ...

    def fetch_match_detail(self, match_id: str, **kwargs: Any) -> dict[str, Any]:
        """Return detailed stats for a single match.

        Args:
            match_id: Provider-specific match identifier.
            **kwargs: Provider-specific options (region, etc.).

        Returns:
            ``{"match_id": str, "stats": {...}}``

        Raises:
            GameAPIError: on any failure.
        """
        ...
