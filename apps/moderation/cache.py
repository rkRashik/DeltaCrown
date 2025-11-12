"""
Sanction-state cache for moderation enforcement.

Read-through cache for get_all_active_policies() with:
- Key: moderation:user:{user_id}:sanctions
- TTL: 60 seconds
- Flag: MODERATION_POLICY_CACHE_ENABLED (default False)
- Invalidation: On create_sanction and revoke_sanction

All cached values are IDs-only (NO PII: no username/email/IP).
"""
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def should_use_cache() -> bool:
    """Check if policy caching is enabled."""
    return getattr(settings, 'MODERATION_POLICY_CACHE_ENABLED', False)


def cache_key_for_user(user_id: int, tournament_id: Optional[int] = None) -> str:
    """
    Generate cache key for user sanctions.
    
    Format: moderation:user:{user_id}:sanctions
    Or: moderation:user:{user_id}:tournament:{tournament_id}:sanctions
    """
    if tournament_id:
        return f"moderation:user:{user_id}:tournament:{tournament_id}:sanctions"
    return f"moderation:user:{user_id}:sanctions"


def get_cached_policies(
    user_id: int,
    tournament_id: Optional[int] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve cached sanction policies for a user.
    
    Returns:
        List of sanctions if cached, None if cache miss or disabled
    """
    if not should_use_cache():
        return None
    
    key = cache_key_for_user(user_id, tournament_id)
    cached = cache.get(key)
    
    if cached is not None:
        logger.debug(f"Cache HIT for {key}")
        return cached
    
    logger.debug(f"Cache MISS for {key}")
    return None


def set_cached_policies(
    user_id: int,
    policies: List[Dict[str, Any]],
    tournament_id: Optional[int] = None
) -> None:
    """
    Store sanction policies in cache with TTL=60s.
    
    Validates NO PII in cached data (only IDs).
    """
    if not should_use_cache():
        return
    
    # PII guard: ensure NO username/email/IP in policies
    _validate_no_pii_in_policies(policies)
    
    key = cache_key_for_user(user_id, tournament_id)
    ttl = 60  # 60 seconds
    
    cache.set(key, policies, ttl)
    logger.debug(f"Cache SET for {key} (TTL={ttl}s, count={len(policies)})")


def invalidate_user_sanctions(user_id: int) -> None:
    """
    Invalidate all cached sanctions for a user.
    
    Call this on create_sanction and revoke_sanction.
    Clears both global and all tournament-scoped caches.
    """
    if not should_use_cache():
        return
    
    # Invalidate global sanctions cache
    global_key = cache_key_for_user(user_id)
    cache.delete(global_key)
    logger.info(f"Cache INVALIDATE for user {user_id} (global)")
    
    # Note: We can't enumerate all tournaments, so we use a wildcard pattern
    # In production, consider using cache tags or Redis SCAN for pattern deletion
    # For now, we invalidate known patterns on specific operations
    
    # Attempt pattern-based deletion if Redis backend supports it
    try:
        pattern = f"moderation:user:{user_id}:tournament:*:sanctions"
        if hasattr(cache, 'delete_pattern'):
            deleted = cache.delete_pattern(pattern)
            logger.info(f"Cache INVALIDATE pattern {pattern}: {deleted} keys deleted")
    except Exception as e:
        logger.warning(f"Pattern deletion failed (not supported by cache backend): {e}")


def invalidate_tournament_sanctions(user_id: int, tournament_id: int) -> None:
    """
    Invalidate tournament-scoped sanctions cache for a user.
    
    Call this for tournament-scoped sanction operations.
    """
    if not should_use_cache():
        return
    
    # Invalidate both global (because global sanctions apply to all tournaments)
    # and tournament-specific cache
    invalidate_user_sanctions(user_id)
    
    tournament_key = cache_key_for_user(user_id, tournament_id)
    cache.delete(tournament_key)
    logger.info(f"Cache INVALIDATE for user {user_id}, tournament {tournament_id}")


def _validate_no_pii_in_policies(policies: List[Dict[str, Any]]) -> None:
    """
    Validate that cached policies contain NO PII.
    
    Raises ValueError if username/email/IP detected.
    """
    policies_str = str(policies).lower()
    
    pii_fields = ['username', 'email', 'ip', 'ip_address', 'user_email', 'email_address']
    for field in pii_fields:
        if field in policies_str:
            raise ValueError(f"PII leak in cache: '{field}' found in policies")


def warm_cache_for_user(user_id: int, policies: List[Dict[str, Any]]) -> None:
    """
    Warm the cache with pre-fetched policies.
    
    Useful for bulk operations or pre-warming during low-traffic periods.
    """
    set_cached_policies(user_id, policies)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics (if supported by backend).
    
    Returns dict with hits, misses, keys, etc.
    """
    stats = {
        'enabled': should_use_cache(),
        'backend': str(type(cache).__name__)
    }
    
    # Try to get Redis info if available
    try:
        if hasattr(cache, '_cache') and hasattr(cache._cache, 'info'):
            redis_info = cache._cache.info('stats')
            stats['hits'] = redis_info.get('keyspace_hits', 0)
            stats['misses'] = redis_info.get('keyspace_misses', 0)
    except Exception:
        pass
    
    return stats
