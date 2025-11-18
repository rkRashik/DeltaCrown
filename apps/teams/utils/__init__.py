"""
Teams App Utilities - Performance, Caching & Security

This package contains utilities for optimizing team queries, caching results,
and enforcing security policies.

Usage Examples:
    
    # Query Optimization
    from apps.teams.utils.query_optimizer import TeamQueryOptimizer
    teams = TeamQueryOptimizer.get_teams_with_related()
    
    # Caching
    from apps.teams.utils.cache import cached_query, invalidate_team_cache, CacheTTL
    
    @cached_query(timeout=CacheTTL.MEDIUM)
    def expensive_function():
        return query_results
    
    # Security
    from apps.teams.utils.security import (
        TeamPermissions, 
        require_team_permission,
        FileUploadValidator,
        require_rate_limit
    )
"""

# Query Optimization
from .query_optimizer import TeamQueryOptimizer

# Caching
from .cache import (
    cached_query,
    invalidate_team_cache,
    warm_cache_for_team,
    CacheTTL,
    CacheStats,
)

# Security
from .security import (
    TeamPermissions,
    require_team_permission,
    FileUploadValidator,
    RateLimiter,
    require_rate_limit,
)

__all__ = [
    # Query Optimization
    'TeamQueryOptimizer',
    
    # Caching
    'cached_query',
    'invalidate_team_cache',
    'warm_cache_for_team',
    'CacheTTL',
    'CacheStats',
    
    # Security
    'TeamPermissions',
    'require_team_permission',
    'FileUploadValidator',
    'RateLimiter',
    'require_rate_limit',
]
