"""
Token-bucket rate limiter backed by Django's Redis cache.

Designed for per-provider throttling in background sync tasks.  One bucket
per ``(provider, bucket_key)`` pair; excess requests are either rejected
(non-blocking) or the caller sleeps until a token is available.

Usage::

    from apps.user_profile.services.rate_limiter import RateLimiter

    limiter = RateLimiter(provider="steam", rate_per_second=5.0, burst=10)

    # Non-blocking check:
    if not limiter.try_acquire():
        raise GameAPIError("RATE_LIMITED", "Too many Steam API calls", 429, provider="steam")

    # Blocking (sleep until allowed):
    limiter.acquire(timeout_seconds=30)
"""

from __future__ import annotations

import time
import logging
from typing import Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)

_BUCKET_TTL_SECONDS = 120  # Redis TTL for bucket keys — garbage collect stale entries


class RateLimiter:
    """Simple token-bucket rate limiter using Redis atomic float operations.

    Args:
        provider: Provider identifier used as part of the Redis key.
        rate_per_second: Token refill rate (tokens/second).
        burst: Maximum tokens in the bucket at any time.
        bucket_key: Optional sub-key to partition (e.g. per-region).
    """

    def __init__(
        self,
        provider: str,
        rate_per_second: float = 5.0,
        burst: int = 10,
        bucket_key: str = "default",
    ) -> None:
        self.provider = provider
        self.rate_per_second = max(0.001, rate_per_second)
        self.burst = max(1, burst)
        self._key = f"dc:rl:{provider}:{bucket_key}"

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire *tokens* without blocking.

        Returns:
            ``True`` if tokens were available and consumed; ``False`` if rate-limited.
        """
        now = time.monotonic()
        state = cache.get(self._key) or {"tokens": float(self.burst), "last": now}

        elapsed = max(0.0, now - state["last"])
        refilled = min(float(self.burst), state["tokens"] + elapsed * self.rate_per_second)

        if refilled < tokens:
            return False

        state["tokens"] = refilled - tokens
        state["last"] = now
        cache.set(self._key, state, timeout=_BUCKET_TTL_SECONDS)
        return True

    def acquire(self, tokens: int = 1, timeout_seconds: float = 60.0) -> None:
        """Block until *tokens* are available or *timeout_seconds* elapses.

        Raises:
            TimeoutError: if tokens are not available within *timeout_seconds*.
        """
        deadline = time.monotonic() + timeout_seconds
        while True:
            if self.try_acquire(tokens=tokens):
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"RateLimiter({self.provider}): timed out waiting for {tokens} token(s)"
                )
            sleep_for = min(0.1, remaining)
            time.sleep(sleep_for)
