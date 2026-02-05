"""
Cache invalidation helpers for vNext organizations and teams.

Provides backend-agnostic cache invalidation that never crashes requests.
Works with Redis (delete_pattern), LocMemCache (skip), or any other backend.
"""

from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def safe_cache_delete_pattern(pattern: str) -> None:
    """
    Delete cache keys matching pattern if backend supports it.
    
    MUST NEVER raise exceptions. If the cache backend doesn't support
    delete_pattern (e.g., LocMemCache), this is a no-op.
    
    Args:
        pattern: Redis-style pattern (e.g., 'hub:vnext:*')
    
    Returns:
        None - this function never fails
    """
    try:
        delete_pattern = getattr(cache, "delete_pattern", None)
        if callable(delete_pattern):
            deleted_count = delete_pattern(pattern)
            logger.debug(
                f"Cache pattern invalidation successful: {pattern} ({deleted_count} keys deleted)"
            )
            return
        
        # Fallback: backend doesn't support pattern deletion
        # This is expected for LocMemCache and is non-fatal
        logger.info(
            f"Cache backend has no delete_pattern support; skipping invalidation: {pattern}"
        )
    except Exception as e:
        # Log but never crash the request
        logger.exception(
            f"Cache pattern invalidation failed (non-fatal): {pattern}",
            extra={
                'pattern': pattern,
                'exception_type': type(e).__name__,
                'exception_message': str(e),
            }
        )


def invalidate_vnext_hub_cache() -> None:
    """
    Invalidate all vNext hub cache entries.
    
    Called when:
    - New team created
    - Team visibility/status changed
    - Featured team list should refresh
    
    This is a best-effort operation and never fails the request.
    """
    safe_cache_delete_pattern('hub:featured_teams:*')
    safe_cache_delete_pattern('hub:vnext:*')
    safe_cache_delete_pattern('hero_carousel_*')


def invalidate_team_cache(team_slug: str) -> None:
    """
    Invalidate cache entries for a specific team.
    
    Called when:
    - Team settings updated
    - Team members added/removed
    - Team roster changed
    
    Args:
        team_slug: Team slug identifier
    """
    safe_cache_delete_pattern(f'team:{team_slug}:*')
    safe_cache_delete_pattern(f'team_detail:{team_slug}')
    
    # Also invalidate hub cache if team visibility changed
    invalidate_vnext_hub_cache()


def invalidate_organization_cache(org_slug: str) -> None:
    """
    Invalidate cache entries for a specific organization.
    
    Args:
        org_slug: Organization slug identifier
    """
    safe_cache_delete_pattern(f'org:{org_slug}:*')
    safe_cache_delete_pattern(f'org_detail:{org_slug}')
