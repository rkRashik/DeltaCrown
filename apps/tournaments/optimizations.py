# apps/tournaments/optimizations.py
"""
Performance Optimization Utilities for Tournament System

Provides caching, query optimization, and performance utilities.
"""
from functools import wraps
from django.core.cache import cache
from django.db.models import Prefetch, Count, Q, F
from django.utils import timezone


def cache_tournament_state(timeout=30):
    """
    Decorator to cache tournament state for given timeout (seconds).
    
    Usage:
        @cache_tournament_state(timeout=60)
        def get_tournament_data(tournament_slug):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            cache_key = f"tournament_state_{func.__name__}_{args}_{kwargs}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Calculate and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator


class TournamentQueryOptimizer:
    """Optimized queries for tournament data."""
    
    @staticmethod
    def get_tournament_with_related(slug):
        """
        Get tournament with all related data in a single query.
        
        Optimized query that reduces N+1 problems.
        """
        from apps.tournaments.models import Tournament
        
        return Tournament.objects.select_related(
            'settings',
            'schedule',  # Include schedule for optimized access
        ).prefetch_related(
            'registrations',
            'registrations__user',
            'registrations__team',
        ).get(slug=slug)
    
    @staticmethod
    def get_hub_tournaments():
        """
        Get tournaments for hub page with optimized query.
        
        Annotates with registration counts to avoid additional queries.
        """
        from apps.tournaments.models import Tournament
        
        return Tournament.objects.filter(
            status__in=['PUBLISHED', 'RUNNING']
        ).select_related(
            'settings',
            'schedule',  # Include schedule for optimized access
        ).annotate(
            registration_count=Count('registrations'),
        ).order_by('-start_at')
    
    @staticmethod
    def get_user_registrations(user):
        """
        Get user's registrations with tournament data.
        
        Prefetches tournament data to avoid N+1 queries.
        """
        from apps.tournaments.models import Registration
        
        return Registration.objects.filter(
            user=user
        ).select_related(
            'tournament',
            'tournament__settings',
            'tournament__schedule',  # Include schedule for optimized access
            'team',
        ).order_by('-created_at')
    
    @staticmethod
    def get_tournament_participants(tournament):
        """
        Get tournament participants with user profiles.
        
        Optimized for participant listing pages.
        """
        from apps.tournaments.models import Registration
        
        return Registration.objects.filter(
            tournament=tournament
        ).select_related(
            'user',
            'team',
        ).order_by('created_at')


class StateCacheManager:
    """Manage caching for tournament states."""
    
    CACHE_PREFIX = 'tournament_state'
    DEFAULT_TIMEOUT = 30  # 30 seconds
    
    @classmethod
    def get_cache_key(cls, tournament_slug):
        """Generate cache key for tournament state."""
        return f"{cls.CACHE_PREFIX}:{tournament_slug}"
    
    @classmethod
    def get_state(cls, tournament_slug):
        """Get cached tournament state."""
        cache_key = cls.get_cache_key(tournament_slug)
        return cache.get(cache_key)
    
    @classmethod
    def set_state(cls, tournament_slug, state_dict, timeout=None):
        """Cache tournament state."""
        cache_key = cls.get_cache_key(tournament_slug)
        timeout = timeout or cls.DEFAULT_TIMEOUT
        cache.set(cache_key, state_dict, timeout)
    
    @classmethod
    def invalidate(cls, tournament_slug):
        """Invalidate cached tournament state."""
        cache_key = cls.get_cache_key(tournament_slug)
        cache.delete(cache_key)
    
    @classmethod
    def invalidate_pattern(cls, pattern='*'):
        """Invalidate all tournament state caches matching pattern."""
        cache_pattern = f"{cls.CACHE_PREFIX}:{pattern}"
        # Note: This requires Redis or similar cache backend
        # For simple cache backends, you may need to track keys separately
        try:
            cache.delete_pattern(cache_pattern)
        except AttributeError:
            # Fallback: cache backend doesn't support delete_pattern
            pass


class RegistrationCountCache:
    """Cache registration counts for tournaments."""
    
    CACHE_PREFIX = 'tournament_reg_count'
    TIMEOUT = 60  # 1 minute
    
    @classmethod
    def get_count(cls, tournament_id):
        """Get cached registration count."""
        cache_key = f"{cls.CACHE_PREFIX}:{tournament_id}"
        count = cache.get(cache_key)
        
        if count is None:
            # Calculate and cache
            from apps.tournaments.models import Registration
            count = Registration.objects.filter(
                tournament_id=tournament_id
            ).count()
            cache.set(cache_key, count, cls.TIMEOUT)
        
        return count
    
    @classmethod
    def invalidate(cls, tournament_id):
        """Invalidate cached count for tournament."""
        cache_key = f"{cls.CACHE_PREFIX}:{tournament_id}"
        cache.delete(cache_key)


def bulk_get_tournament_states(tournament_slugs):
    """
    Get states for multiple tournaments efficiently.
    
    Args:
        tournament_slugs: List of tournament slugs
    
    Returns:
        Dict mapping slug to state dict
    """
    from apps.tournaments.models import Tournament
    
    # Get tournaments with related data in one query
    tournaments = Tournament.objects.filter(
        slug__in=tournament_slugs
    ).select_related('settings').prefetch_related('registrations')
    
    # Calculate states
    results = {}
    for tournament in tournaments:
        state_dict = tournament.state.to_dict()
        results[tournament.slug] = state_dict
    
    return results


def optimize_tournament_list_query(queryset):
    """
    Optimize a tournament queryset for listing pages.
    
    Args:
        queryset: Base Tournament queryset
    
    Returns:
        Optimized queryset with annotations
    """
    return queryset.select_related(
        'settings',
    ).annotate(
        registration_count=Count('registrations'),
    )


# Performance monitoring decorator
def monitor_performance(func):
    """
    Decorator to monitor function performance.
    
    Logs execution time for functions taking > 100ms.
    """
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000  # ms
        
        if duration > 100:
            logger.warning(
                f"Slow function: {func.__name__} took {duration:.2f}ms"
            )
        
        return result
    
    return wrapper
