"""Lightweight safe cache helpers for site UI contexts.

These wrappers ensure Redis/cache backend failures do not crash page rendering.
A short in-process cooldown (circuit breaker) reduces repeated failing cache calls.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)

_CACHE_FAIL_UNTIL_MONO = 0.0
_CACHE_FAIL_COOLDOWN_SECONDS = 60.0


def _cache_available() -> bool:
    return time.monotonic() >= _CACHE_FAIL_UNTIL_MONO


def _mark_cache_failure(exc: Exception) -> None:
    global _CACHE_FAIL_UNTIL_MONO
    _CACHE_FAIL_UNTIL_MONO = time.monotonic() + _CACHE_FAIL_COOLDOWN_SECONDS
    logger.warning("[siteui.cache_safe] cache backend unavailable; using fallback", exc_info=exc)


def safe_cache_get(key: str, default: Any = None) -> Any:
    if not _cache_available():
        return default
    try:
        return cache.get(key, default)
    except Exception as exc:
        _mark_cache_failure(exc)
        return default


def safe_cache_set(key: str, value: Any, timeout: int | None = None) -> bool:
    if not _cache_available():
        return False
    try:
        cache.set(key, value, timeout)
        return True
    except Exception as exc:
        _mark_cache_failure(exc)
        return False
