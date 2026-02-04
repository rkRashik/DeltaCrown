"""
Hub cache invalidation helpers.

Used to ensure hub displays fresh data after team/org changes.
"""
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def invalidate_hub_cache(game_id=None):
    """
    Invalidate hub-related cache keys.
    
    Call this after:
    - Team created
    - Team status/visibility updated
    - Team deleted
    - Organization created/updated
    
    Args:
        game_id: Optional game ID to invalidate specific game caches.
                 If None, invalidates all game caches.
    """
    keys_to_delete = []
    
    # Featured teams caches
    if game_id:
        keys_to_delete.append(f'featured_teams_{game_id}_12')
    else:
        # Invalidate "all games" cache
        keys_to_delete.append(f'featured_teams_all_12')
    
    # Leaderboard caches
    if game_id:
        keys_to_delete.append(f'hub_leaderboard_{game_id}_50')
    else:
        keys_to_delete.append(f'hub_leaderboard_all_50')
    
    # Hero carousel cache (per-user, but invalidate pattern)
    # Note: Hero carousel is user-specific, so we can't easily invalidate all users
    # It will refresh after 2 minutes anyway
    
    # Delete all identified keys
    for key in keys_to_delete:
        try:
            cache.delete(key)
            logger.debug(f"Invalidated hub cache: {key}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache key {key}: {e}")
    
    logger.info(f"Hub cache invalidated for game_id={game_id or 'all'}")


def invalidate_all_hub_caches():
    """
    Nuclear option: invalidate ALL hub caches.
    
    Use sparingly - only for major data migrations or emergency fixes.
    """
    # In a production system, you'd use cache.delete_pattern()
    # For now, invalidate known keys
    invalidate_hub_cache(game_id=None)
    logger.info("All hub caches invalidated")
