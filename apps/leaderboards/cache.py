"""
Leaderboard Redis Caching Layer.

Provides fast read access to leaderboards via Redis cache with TTL-based expiration.
Keys follow pattern: lb:{game}:{tournament_id}:{season}:{page}:{page_size}
"""

import json
from typing import List, Dict, Optional
from django.core.cache import cache
from django.conf import settings
from apps.leaderboards.models import LeaderboardEntry


class LeaderboardCache:
    """
    Redis caching layer for leaderboards.
    
    Usage:
        cache = LeaderboardCache()
        entries = cache.get_or_compute("tournament", tournament_id=501)
    """
    
    # TTL values (seconds)
    TTL_TOURNAMENT = 300  # 5 minutes (real-time updates)
    TTL_SEASONAL = 3600  # 1 hour (hourly recompute)
    TTL_ALL_TIME = 86400  # 24 hours (daily recompute)
    TTL_TEAM = 3600  # 1 hour
    TTL_GAME_SPECIFIC = 3600  # 1 hour
    
    def _make_key(
        self,
        leaderboard_type: str,
        game: Optional[str] = None,
        tournament_id: Optional[int] = None,
        season: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> str:
        """
        Generate Redis key for leaderboard cache.
        
        Pattern: lb:{type}:{game}:{tournament_id}:{season}:{page}:{page_size}
        
        Args:
            leaderboard_type: "tournament", "seasonal", "all_time", "team", "game_specific"
            game: Game filter (optional)
            tournament_id: Tournament ID (optional)
            season: Season identifier (optional)
            page: Page number (default: 1)
            page_size: Results per page (default: 50)
        
        Returns:
            Redis key string
        """
        parts = ["lb", leaderboard_type]
        
        if game:
            parts.append(game)
        else:
            parts.append("*")
        
        if tournament_id:
            parts.append(str(tournament_id))
        else:
            parts.append("*")
        
        if season:
            parts.append(season)
        else:
            parts.append("*")
        
        parts.extend([str(page), str(page_size)])
        
        return ":".join(parts)
    
    def get(
        self,
        leaderboard_type: str,
        game: Optional[str] = None,
        tournament_id: Optional[int] = None,
        season: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Optional[List[Dict]]:
        """
        Get leaderboard from cache.
        
        Returns:
            List of leaderboard entry dicts if cached, None if not found.
        """
        key = self._make_key(leaderboard_type, game, tournament_id, season, page, page_size)
        
        cached = cache.get(key)
        if cached:
            return json.loads(cached)
        
        return None
    
    def set(
        self,
        leaderboard_type: str,
        entries: List[LeaderboardEntry],
        game: Optional[str] = None,
        tournament_id: Optional[int] = None,
        season: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ):
        """
        Store leaderboard in cache with appropriate TTL.
        
        Args:
            leaderboard_type: Leaderboard type
            entries: List of LeaderboardEntry objects
            game: Game filter (optional)
            tournament_id: Tournament ID (optional)
            season: Season identifier (optional)
            page: Page number
            page_size: Results per page
        """
        key = self._make_key(leaderboard_type, game, tournament_id, season, page, page_size)
        
        # Serialize entries to dicts
        serialized = []
        for entry in entries:
            serialized.append({
                "rank": entry.rank,
                "points": entry.points,
                "wins": entry.wins,
                "losses": entry.losses,
                "win_rate": float(entry.win_rate),
                "player": {
                    "id": entry.player.id if entry.player else None,
                    "username": entry.player.username if entry.player else None,
                } if entry.player else None,
                "team": {
                    "id": entry.team.id if entry.team else None,
                    "name": entry.team.name if entry.team else None,
                } if entry.team else None,
            })
        
        # Determine TTL based on leaderboard type
        ttl = self._get_ttl(leaderboard_type)
        
        # Store in cache
        cache.set(key, json.dumps(serialized), timeout=ttl)
    
    def _get_ttl(self, leaderboard_type: str) -> int:
        """Get TTL for leaderboard type."""
        ttl_map = {
            "tournament": self.TTL_TOURNAMENT,
            "seasonal": self.TTL_SEASONAL,
            "all_time": self.TTL_ALL_TIME,
            "team": self.TTL_TEAM,
            "game_specific": self.TTL_GAME_SPECIFIC,
        }
        return ttl_map.get(leaderboard_type, self.TTL_SEASONAL)
    
    def invalidate(
        self,
        leaderboard_type: str,
        game: Optional[str] = None,
        tournament_id: Optional[int] = None,
        season: Optional[str] = None
    ):
        """
        Invalidate cache for a leaderboard (all pages).
        
        Use after recomputing leaderboard to force refresh.
        """
        # Delete all pages (pattern matching)
        pattern = self._make_key(leaderboard_type, game, tournament_id, season, page="*", page_size="*")
        
        # Redis pattern matching (requires redis-py with scan support)
        try:
            keys = cache.keys(pattern)
            if keys:
                cache.delete_many(keys)
        except AttributeError:
            # Fallback: delete common page sizes
            for page in range(1, 11):  # Pages 1-10
                for page_size in [10, 25, 50, 100]:
                    key = self._make_key(leaderboard_type, game, tournament_id, season, page, page_size)
                    cache.delete(key)
    
    def get_or_compute(
        self,
        leaderboard_type: str,
        compute_func,
        game: Optional[str] = None,
        tournament_id: Optional[int] = None,
        season: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[Dict]:
        """
        Get leaderboard from cache or compute if not cached.
        
        Args:
            leaderboard_type: Leaderboard type
            compute_func: Function to compute leaderboard (called if cache miss)
            game: Game filter (optional)
            tournament_id: Tournament ID (optional)
            season: Season identifier (optional)
            page: Page number
            page_size: Results per page
        
        Returns:
            List of leaderboard entry dicts
        """
        # Try cache first
        cached = self.get(leaderboard_type, game, tournament_id, season, page, page_size)
        if cached is not None:
            return cached
        
        # Cache miss: compute
        offset = (page - 1) * page_size
        entries = compute_func(
            leaderboard_type=leaderboard_type,
            game=game,
            tournament_id=tournament_id,
            season=season,
            limit=page_size,
            offset=offset
        )
        
        # Store in cache
        self.set(leaderboard_type, entries, game, tournament_id, season, page, page_size)
        
        # Return serialized
        return self.get(leaderboard_type, game, tournament_id, season, page, page_size)


# Singleton instance
_leaderboard_cache = LeaderboardCache()


def get_leaderboard_cache() -> LeaderboardCache:
    """Get singleton leaderboard cache instance."""
    return _leaderboard_cache


# Example usage in service layer
def get_cached_leaderboard(
    leaderboard_type: str,
    game: Optional[str] = None,
    tournament_id: Optional[int] = None,
    season: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
) -> List[Dict]:
    """
    Get leaderboard with caching.
    
    High-level wrapper that handles cache + compute.
    """
    from apps.leaderboards.services import get_leaderboard_service
    
    cache = get_leaderboard_cache()
    service = get_leaderboard_service()
    
    return cache.get_or_compute(
        leaderboard_type=leaderboard_type,
        compute_func=service.get_leaderboard,
        game=game,
        tournament_id=tournament_id,
        season=season,
        page=page,
        page_size=page_size
    )
