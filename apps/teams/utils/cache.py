"""
Task 10: Redis caching utilities for Teams app
"""
import functools
import hashlib
import json
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


# Cache TTL constants (in seconds)
class CacheTTL:
    """Cache Time-To-Live constants"""
    VERY_SHORT = 60  # 1 minute
    SHORT = 300  # 5 minutes
    MEDIUM = 900  # 15 minutes
    LONG = 1800  # 30 minutes
    VERY_LONG = 3600  # 1 hour
    DAY = 86400  # 24 hours


def cached_query(timeout=CacheTTL.MEDIUM, key_prefix=''):
    """
    Decorator to cache database query results.
    
    Usage:
        @cached_query(timeout=CacheTTL.LONG, key_prefix='team_detail')
        def get_team_data(slug):
            return Team.objects.get(slug=slug)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = _generate_cache_key(key_prefix or func.__name__, args, kwargs)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return result
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, timeout)
            return result
        
        # Add cache invalidation method
        wrapper.invalidate = lambda *args, **kwargs: cache.delete(
            _generate_cache_key(key_prefix or func.__name__, args, kwargs)
        )
        
        return wrapper
    return decorator


def cached_property_method(timeout=CacheTTL.MEDIUM):
    """
    Decorator for model methods that should be cached.
    
    Usage:
        class Team(models.Model):
            @cached_property_method(timeout=CacheTTL.LONG)
            def get_active_members_count(self):
                return self.members.filter(status='active').count()
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            cache_key = f"{self.__class__.__name__}:{self.pk}:{func.__name__}"
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(self, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        
        wrapper.invalidate = lambda self: cache.delete(
            f"{self.__class__.__name__}:{self.pk}:{func.__name__}"
        )
        
        return wrapper
    return decorator


def invalidate_team_cache(team_id=None, slug=None):
    """
    Invalidate all cache entries related to a team.
    Call this when team data changes (roster update, new post, etc.)
    """
    patterns_to_delete = []
    
    if team_id:
        patterns_to_delete.extend([
            f"team:detail:*",
            f"team:roster:{team_id}",
            f"team:followers:{team_id}:*",
            f"team:posts:{team_id}:*",
            f"team:achievements:{team_id}",
            f"team:sponsors:{team_id}",
            f"Team:{team_id}:*",
        ])
    
    if slug:
        patterns_to_delete.append(f"team:detail:{slug}")
    
    # Always invalidate leaderboards when team changes
    patterns_to_delete.append("leaderboard:*")
    
    # Delete matching keys
    for pattern in patterns_to_delete:
        try:
            cache.delete_pattern(pattern)
            logger.info(f"Invalidated cache pattern: {pattern}")
        except AttributeError:
            # Fallback if delete_pattern not available
            cache.delete(pattern.replace('*', ''))
            logger.warning(f"Cache pattern deletion not supported, deleted single key: {pattern}")


def invalidate_user_cache(user_id):
    """
    Invalidate cache entries for a specific user.
    """
    patterns = [
        f"user:teams:{user_id}",
        f"user:following:{user_id}",
        f"user:notifications:{user_id}",
    ]
    
    for pattern in patterns:
        try:
            cache.delete_pattern(pattern)
        except AttributeError:
            cache.delete(pattern)


def warm_cache_for_team(team):
    """
    Pre-populate cache for a team's most accessed data.
    Use after major updates or during off-peak hours.
    """
    from apps.teams.utils.query_optimizer import TeamQueryOptimizer, TeamCacheKeys
    
    try:
        # Warm team detail
        team_data = TeamQueryOptimizer.get_team_detail_optimized(team.slug)
        cache.set(TeamCacheKeys.team_detail(team.slug), team_data, CacheTTL.LONG)
        
        # Warm roster
        roster_data = TeamQueryOptimizer.get_team_roster_optimized(team)
        cache.set(TeamCacheKeys.team_roster(team.id), roster_data, CacheTTL.LONG)
        
        # Warm sponsors
        sponsors = team.sponsors.filter(status='approved')
        cache.set(TeamCacheKeys.team_sponsors(team.id), sponsors, CacheTTL.VERY_LONG)
        
        logger.info(f"Warmed cache for team: {team.name}")
    except Exception as e:
        logger.error(f"Failed to warm cache for team {team.id}: {e}")


def warm_leaderboard_cache():
    """
    Pre-populate leaderboard cache.
    Run this via management command or scheduled task.
    """
    from apps.teams.utils.query_optimizer import TeamQueryOptimizer, TeamCacheKeys
    
    try:
        # All games leaderboard
        all_teams = TeamQueryOptimizer.get_leaderboard_optimized(limit=100)
        cache.set(TeamCacheKeys.leaderboard(), all_teams, CacheTTL.LONG)
        
        # Per-game leaderboards
        for game_code, game_name in [('valorant', 'Valorant'), ('efootball', 'eFootball')]:
            game_teams = TeamQueryOptimizer.get_leaderboard_optimized(game=game_code, limit=100)
            cache.set(TeamCacheKeys.leaderboard(game=game_code), game_teams, CacheTTL.LONG)
        
        logger.info("Warmed leaderboard cache")
    except Exception as e:
        logger.error(f"Failed to warm leaderboard cache: {e}")


def get_or_set_cache(key, callable_func, timeout=CacheTTL.MEDIUM):
    """
    Get value from cache or execute function and store result.
    
    Usage:
        team_data = get_or_set_cache(
            f'team:{slug}',
            lambda: Team.objects.get(slug=slug),
            timeout=CacheTTL.LONG
        )
    """
    result = cache.get(key)
    if result is not None:
        return result
    
    result = callable_func()
    cache.set(key, result, timeout)
    return result


def _generate_cache_key(prefix, args, kwargs):
    """
    Generate a consistent cache key from function arguments.
    """
    # Convert args and kwargs to a string representation
    key_parts = [prefix]
    
    if args:
        key_parts.extend([str(arg) for arg in args])
    
    if kwargs:
        # Sort kwargs for consistency
        sorted_kwargs = sorted(kwargs.items())
        key_parts.extend([f"{k}:{v}" for k, v in sorted_kwargs])
    
    # Join and hash if too long
    key_string = ":".join(key_parts)
    
    if len(key_string) > 200:
        # Hash long keys to keep them under limit
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    return key_string


class CachedQuerySet:
    """
    Wrapper for QuerySet with automatic caching.
    
    Usage:
        teams = CachedQuerySet(
            Team.objects.filter(game='valorant'),
            cache_key='valorant_teams',
            timeout=CacheTTL.LONG
        )
        for team in teams:
            print(team.name)
    """
    
    def __init__(self, queryset, cache_key, timeout=CacheTTL.MEDIUM):
        self.queryset = queryset
        self.cache_key = cache_key
        self.timeout = timeout
        self._cached_result = None
    
    def __iter__(self):
        if self._cached_result is None:
            self._cached_result = cache.get(self.cache_key)
            
            if self._cached_result is None:
                self._cached_result = list(self.queryset)
                cache.set(self.cache_key, self._cached_result, self.timeout)
        
        return iter(self._cached_result)
    
    def __len__(self):
        if self._cached_result is None:
            list(self)  # Force evaluation
        return len(self._cached_result)
    
    def invalidate(self):
        """Invalidate the cache for this queryset."""
        cache.delete(self.cache_key)
        self._cached_result = None


# Cache statistics tracking
class CacheStats:
    """
    Track cache hit/miss statistics for monitoring.
    """
    
    @staticmethod
    def record_hit(key):
        """Record a cache hit."""
        stats_key = f"cache_stats:hits:{timezone.now().date()}"
        cache.incr(stats_key, 1)
        cache.expire(stats_key, CacheTTL.DAY * 2)  # Keep for 2 days
    
    @staticmethod
    def record_miss(key):
        """Record a cache miss."""
        stats_key = f"cache_stats:misses:{timezone.now().date()}"
        cache.incr(stats_key, 1)
        cache.expire(stats_key, CacheTTL.DAY * 2)
    
    @staticmethod
    def get_stats(date=None):
        """Get cache statistics for a specific date."""
        if date is None:
            date = timezone.now().date()
        
        hits = cache.get(f"cache_stats:hits:{date}", 0)
        misses = cache.get(f"cache_stats:misses:{date}", 0)
        
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        return {
            'date': date,
            'hits': hits,
            'misses': misses,
            'total': total,
            'hit_rate': f"{hit_rate:.2f}%"
        }
