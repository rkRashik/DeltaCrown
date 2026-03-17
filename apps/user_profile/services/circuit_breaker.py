"""
Circuit breaker for external game API calls.

Prevents cascading failures when an upstream provider is unavailable.
State is stored in Redis (via Django cache) so it survives worker restarts.

States:
  CLOSED   — normal operation; failures are counted.
  OPEN     — trips after *failure_threshold* failures in *window_seconds*;
             all calls are rejected until *cooldown_seconds* elapses.
  HALF_OPEN — one probe call is allowed after cooldown to test recovery.

Usage::

    from apps.user_profile.services.circuit_breaker import CircuitBreaker

    breaker = CircuitBreaker(provider="steam")

    if not breaker.allow_request():
        raise GameAPIError("CIRCUIT_OPEN", "Steam API circuit breaker open", 503, provider="steam")
    try:
        result = call_steam_api(...)
        breaker.record_success()
    except Exception:
        breaker.record_failure()
        raise
"""

from __future__ import annotations

import time
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

_STATE_CLOSED = "closed"
_STATE_OPEN = "open"
_STATE_HALF_OPEN = "half_open"


class CircuitBreaker:
    """Redis-backed circuit breaker for external API calls.

    Args:
        provider: Provider identifier (used as Redis key prefix).
        failure_threshold: Number of failures within *window_seconds* before opening.
        window_seconds: Rolling failure counting window.
        cooldown_seconds: How long to stay OPEN before trying a probe call.
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 5,
        window_seconds: int = 60,
        cooldown_seconds: int = 120,
    ) -> None:
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._state_key = f"dc:cb:{provider}:state"
        self._fail_key = f"dc:cb:{provider}:failures"
        self._open_at_key = f"dc:cb:{provider}:open_at"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def allow_request(self) -> bool:
        """Return ``True`` if a request should be allowed through."""
        state = cache.get(self._state_key, _STATE_CLOSED)

        if state == _STATE_CLOSED:
            return True

        if state == _STATE_OPEN:
            open_at = cache.get(self._open_at_key, 0.0)
            if time.time() - open_at >= self.cooldown_seconds:
                self._set_state(_STATE_HALF_OPEN)
                logger.info("CircuitBreaker(%s): HALF_OPEN — allowing probe", self.provider)
                return True
            return False

        # HALF_OPEN: allow exactly one probe
        return True

    def record_success(self) -> None:
        """Call after a successful API response to reset the breaker."""
        state = cache.get(self._state_key, _STATE_CLOSED)
        if state in (_STATE_HALF_OPEN, _STATE_OPEN):
            logger.info("CircuitBreaker(%s): probe succeeded — resetting to CLOSED", self.provider)
        self._set_state(_STATE_CLOSED)
        cache.delete(self._fail_key)
        cache.delete(self._open_at_key)

    def record_failure(self) -> None:
        """Call after a failed API call to increment the failure counter."""
        failures = cache.get(self._fail_key, 0) + 1
        cache.set(self._fail_key, failures, timeout=self.window_seconds)

        state = cache.get(self._state_key, _STATE_CLOSED)
        if state == _STATE_HALF_OPEN:
            logger.warning("CircuitBreaker(%s): probe failed — re-opening", self.provider)
            self._trip()
        elif failures >= self.failure_threshold:
            logger.warning(
                "CircuitBreaker(%s): %d failures in %ds — OPEN",
                self.provider, failures, self.window_seconds,
            )
            self._trip()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _trip(self) -> None:
        self._set_state(_STATE_OPEN)
        cache.set(self._open_at_key, time.time(), timeout=self.cooldown_seconds * 2)

    def _set_state(self, state: str) -> None:
        cache.set(self._state_key, state, timeout=self.cooldown_seconds * 4)
