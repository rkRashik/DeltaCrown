"""
TOC cache key/version helpers.

Provides scope-based cache stamping so write actions can invalidate
related read caches without backend-specific delete-pattern support.
"""

from __future__ import annotations

import hashlib

from django.core.cache import cache
from django.utils import timezone


def _stamp_key(scope: str, tournament_id: int) -> str:
    return f"toc:stamp:{scope}:{tournament_id}"


def toc_cache_key(scope: str, tournament_id: int, *parts: object) -> str:
    """Build a cache key using the current scope stamp + caller-provided parts."""
    stamp = cache.get(_stamp_key(scope, tournament_id), 0)
    raw_suffix = ":".join(str(p) for p in parts)
    suffix_hash = hashlib.sha1(raw_suffix.encode('utf-8')).hexdigest()[:20]
    return f"toc:{scope}:{tournament_id}:{stamp}:{suffix_hash}"


def bump_toc_scope(scope: str, tournament_id: int) -> int:
    """Bump a scope stamp to invalidate all existing keys derived from it."""
    value = int(timezone.now().timestamp() * 1000)
    cache.set(_stamp_key(scope, tournament_id), value, timeout=None)
    return value


def bump_toc_scopes(tournament_id: int, *scopes: str) -> None:
    """Invalidate multiple TOC scopes in one call."""
    for scope in scopes:
        bump_toc_scope(scope, tournament_id)
