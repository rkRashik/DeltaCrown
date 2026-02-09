"""
Leaderboards Service Layer.

Provides read-only access to pre-computed leaderboard data with Redis caching.
All operations are flag-gated and PII-free (IDs + aggregates only).

Feature Flags:
    LEADERBOARDS_COMPUTE_ENABLED: Enable leaderboard computation (Celery tasks)
    LEADERBOARDS_CACHE_ENABLED: Enable Redis caching for reads
    LEADERBOARDS_API_ENABLED: Enable public API endpoints

Observability (Phase E Section 10):
    Metrics instrumentation via apps.leaderboards.metrics module.
    Logs include: scope, source (cache|snapshot|live|disabled), duration_ms, IDs only.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from apps.leaderboards.models import LeaderboardEntry, LeaderboardSnapshot
from apps.tournaments.models import Tournament, Match, Registration
from apps.organizations.models import Team
from apps.accounts.models import User
from apps.leaderboards.metrics import record_leaderboard_request


logger = logging.getLogger(__name__)


# ============================================================================
# DTOs (Data Transfer Objects) - PII-Free
# ============================================================================

@dataclass
class LeaderboardEntryDTO:
    """
    PII-free leaderboard entry representation.
    
    Attributes:
        rank: Current rank (1-indexed)
        player_id: Player user ID (PII-free)
        team_id: Team ID if team tournament (PII-free)
        points: Total points accumulated
        wins: Number of wins
        losses: Number of losses
        win_rate: Win percentage (0.00-100.00)
        last_updated: Timestamp of last update
    """
    rank: int
    player_id: Optional[int]
    team_id: Optional[int]
    points: int
    wins: int
    losses: int
    win_rate: float
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "rank": self.rank,
            "player_id": self.player_id,
            "team_id": self.team_id,
            "points": self.points,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.win_rate, 2),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class PlayerHistoryDTO:
    """
    Player's historical leaderboard positions (PII-free).
    
    Attributes:
        player_id: Player user ID
        snapshots: List of historical rank/points by date
    """
    player_id: int
    snapshots: List[Dict[str, Any]]  # [{date, rank, points, tournament_id}, ...]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "player_id": self.player_id,
            "history": self.snapshots,
            "count": len(self.snapshots),
        }


@dataclass
class LeaderboardResponseDTO:
    """
    Complete leaderboard response with metadata.
    
    Attributes:
        scope: Leaderboard scope (tournament/season/all_time)
        entries: List of leaderboard entries
        metadata: Additional context (cache hit, count, etc.)
    """
    scope: str
    entries: List[LeaderboardEntryDTO]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "scope": self.scope,
            "entries": [e.to_dict() for e in self.entries],
            "metadata": self.metadata,
        }


# ============================================================================
# Cache Key Helpers
# ============================================================================

def _get_cache_key_tournament(tournament_id: int) -> str:
    """Generate cache key for tournament leaderboard."""
    return f"lb:tournament:{tournament_id}"


def _get_cache_key_season(season_id: str, game_code: Optional[str] = None) -> str:
    """Generate cache key for seasonal leaderboard."""
    game_suffix = game_code if game_code else "ALL"
    return f"lb:season:{season_id}:{game_suffix}"


def _get_cache_key_all_time(game_code: Optional[str] = None) -> str:
    """Generate cache key for all-time leaderboard."""
    game_suffix = game_code if game_code else "ALL"
    return f"lb:all_time:{game_suffix}"


def _get_cache_key_player_history(player_id: int) -> str:
    """Generate cache key for player history."""
    return f"lb:player_history:{player_id}"


# ============================================================================
# Serialization Helpers
# ============================================================================

def _serialize_entries(entries: List[LeaderboardEntry]) -> List[LeaderboardEntryDTO]:
    """
    Convert LeaderboardEntry queryset to DTOs.
    
    Args:
        entries: Queryset or list of LeaderboardEntry objects
        
    Returns:
        List of LeaderboardEntryDTO (PII-free)
    """
    dtos = []
    for entry in entries:
        dtos.append(LeaderboardEntryDTO(
            rank=entry.rank,
            player_id=entry.player_id,
            team_id=entry.team_id,
            points=entry.points,
            wins=entry.wins,
            losses=entry.losses,
            win_rate=entry.win_rate,
            last_updated=entry.last_updated,
        ))
    return dtos


def _serialize_snapshots(snapshots: List[LeaderboardSnapshot]) -> List[Dict[str, Any]]:
    """
    Convert LeaderboardSnapshot queryset to JSON-serializable dicts.
    
    Args:
        snapshots: Queryset or list of LeaderboardSnapshot objects
        
    Returns:
        List of dicts with {date, rank, points}
    """
    return [
        {
            "date": snap.date.isoformat(),
            "rank": snap.rank,
            "points": snap.points,
            "leaderboard_type": snap.leaderboard_type,
        }
        for snap in snapshots
    ]


# ============================================================================
# Service Functions
# ============================================================================

def get_tournament_leaderboard(tournament_id: int) -> LeaderboardResponseDTO:
    """
    Get leaderboard for a specific tournament.
    
    Args:
        tournament_id: Tournament ID
        
    Returns:
        LeaderboardResponseDTO with entries or empty list if disabled
        
    Behavior:
        - If LEADERBOARDS_COMPUTE_ENABLED=False: Returns empty DTO
        - If LEADERBOARDS_CACHE_ENABLED=True: Check Redis first
        - On cache miss: Query LeaderboardEntry, write to cache
        
    Example:
        >>> response = get_tournament_leaderboard(123)
        >>> print(f"Rank 1: Player {response.entries[0].player_id}")
    """
    # Check if computation is enabled
    if not getattr(settings, "LEADERBOARDS_COMPUTE_ENABLED", False):
        with record_leaderboard_request(scope='tournament', source='disabled'):
            logger.info(
                "Leaderboards disabled, returning empty",
                extra={
                    'scope': 'tournament',
                    'source': 'disabled',
                    'tournament_id': tournament_id,
                }
            )
            return LeaderboardResponseDTO(
                scope="tournament",
                entries=[],
                metadata={
                    "tournament_id": tournament_id,
                    "count": 0,
                    "cache_hit": False,
                    "computation_enabled": False,
                }
            )
    
    cache_key = _get_cache_key_tournament(tournament_id)
    cache_enabled = getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False)
    
    # Try cache first
    if cache_enabled:
        cached = cache.get(cache_key)
        if cached:
            with record_leaderboard_request(scope='tournament', source='cache'):
                logger.info(
                    "Cache HIT for tournament leaderboard",
                    extra={
                        'scope': 'tournament',
                        'source': 'cache',
                        'tournament_id': tournament_id,
                    }
                )
                return LeaderboardResponseDTO(
                    scope="tournament",
                    entries=[
                        LeaderboardEntryDTO(**entry_data)
                        for entry_data in cached["entries"]
                    ],
                    metadata={
                        "tournament_id": tournament_id,
                        "count": len(cached["entries"]),
                        "cache_hit": True,
                        "cached_at": cached["cached_at"],
                    }
                )
    
    # Cache miss - query database
    with record_leaderboard_request(scope='tournament', source='live'):
        logger.info(
            "Cache MISS for tournament leaderboard, querying DB",
            extra={
                'scope': 'tournament',
                'source': 'live',
                'tournament_id': tournament_id,
            }
        )
        entries = LeaderboardEntry.objects.filter(
            leaderboard_type="tournament",
            tournament_id=tournament_id,
            is_active=True
        ).select_related('player', 'team').order_by('rank')
        
        entry_dtos = _serialize_entries(entries)
        
        # Write to cache if enabled
        if cache_enabled and entry_dtos:
            cache_data = {
                "entries": [dto.__dict__ for dto in entry_dtos],
                "cached_at": datetime.utcnow().isoformat(),
            }
            # TTL: 5 minutes for tournament (real-time updates)
            cache.set(cache_key, cache_data, timeout=300)
            logger.info(
                f"Cached {len(entry_dtos)} entries for tournament leaderboard",
                extra={
                    'scope': 'tournament',
                    'tournament_id': tournament_id,
                    'entry_count': len(entry_dtos),
                }
            )
        
        return LeaderboardResponseDTO(
            scope="tournament",
            entries=entry_dtos,
            metadata={
                "tournament_id": tournament_id,
                "count": len(entry_dtos),
                "cache_hit": False,
                "queried_at": datetime.utcnow().isoformat(),
            }
        )


def get_player_leaderboard_history(player_id: int) -> PlayerHistoryDTO:
    """
    Get player's historical leaderboard positions across all tournaments.
    
    Args:
        player_id: Player user ID
        
    Returns:
        PlayerHistoryDTO with snapshot list or empty if disabled
        
    Behavior:
        - If LEADERBOARDS_COMPUTE_ENABLED=False: Returns empty DTO
        - If LEADERBOARDS_CACHE_ENABLED=True: Check Redis first
        - On cache miss: Query LeaderboardSnapshot, write to cache
        - Ordered by date descending (most recent first)
        
    Example:
        >>> history = get_player_leaderboard_history(456)
        >>> print(f"Player 456 had {len(history.snapshots)} tournament entries")
    """
    # Check if computation is enabled
    if not getattr(settings, "LEADERBOARDS_COMPUTE_ENABLED", False):
        logger.info(f"Leaderboards disabled, returning empty history for player {player_id}")
        return PlayerHistoryDTO(
            player_id=player_id,
            snapshots=[]
        )
    
    cache_key = _get_cache_key_player_history(player_id)
    cache_enabled = getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False)
    
    # Try cache first
    if cache_enabled:
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for player history {player_id}")
            return PlayerHistoryDTO(
                player_id=player_id,
                snapshots=cached["snapshots"]
            )
    
    # Cache miss - query database
    logger.info(f"Cache MISS for player history {player_id}, querying DB")
    snapshots = LeaderboardSnapshot.objects.filter(
        player_id=player_id
    ).order_by('-date')  # Most recent first
    
    snapshot_dicts = _serialize_snapshots(snapshots)
    
    # Write to cache if enabled
    if cache_enabled:
        cache_data = {
            "snapshots": snapshot_dicts,
            "cached_at": datetime.utcnow().isoformat(),
        }
        # TTL: 1 hour for player history
        cache.set(cache_key, cache_data, timeout=3600)
        logger.info(f"Cached {len(snapshot_dicts)} snapshots for player {player_id}")
    
    return PlayerHistoryDTO(
        player_id=player_id,
        snapshots=snapshot_dicts
    )


def get_scoped_leaderboard(
    scope: str,
    game_code: Optional[str] = None,
    season_id: Optional[str] = None
) -> LeaderboardResponseDTO:
    """
    Get leaderboard for a specific scope (season or all-time).
    
    Args:
        scope: Leaderboard scope ("season" or "all_time")
        game_code: Optional game filter (e.g., "valorant", "cs2")
        season_id: Required for scope="season" (e.g., "2025_S1")
        
    Returns:
        LeaderboardResponseDTO with entries or empty list if disabled
        
    Raises:
        ValueError: If scope="season" but season_id is None
        ValueError: If scope not in ["season", "all_time"]
        
    Behavior:
        - If LEADERBOARDS_COMPUTE_ENABLED=False: Returns empty DTO
        - If LEADERBOARDS_CACHE_ENABLED=True: Check Redis first
        - On cache miss: Query LeaderboardEntry, write to cache
        - game_code=None returns cross-game aggregated leaderboard
        
    Examples:
        >>> # Season leaderboard for Valorant
        >>> response = get_scoped_leaderboard("season", game_code="valorant", season_id="2025_S1")
        
        >>> # All-time leaderboard (all games)
        >>> response = get_scoped_leaderboard("all_time")
        
        >>> # All-time leaderboard for CS2 only
        >>> response = get_scoped_leaderboard("all_time", game_code="cs2")
    """
    # Validate scope
    if scope not in ["season", "all_time"]:
        raise ValueError(f"Invalid scope: {scope}. Must be 'season' or 'all_time'")
    
    if scope == "season" and not season_id:
        raise ValueError("season_id is required when scope='season'")
    
    # Check if computation is enabled
    if not getattr(settings, "LEADERBOARDS_COMPUTE_ENABLED", False):
        logger.info(f"Leaderboards disabled, returning empty for {scope}")
        return LeaderboardResponseDTO(
            scope=scope,
            entries=[],
            metadata={
                "scope": scope,
                "game_code": game_code,
                "season_id": season_id,
                "count": 0,
                "cache_hit": False,
                "computation_enabled": False,
            }
        )
    
    # Generate cache key
    if scope == "season":
        cache_key = _get_cache_key_season(season_id, game_code)
    else:  # all_time
        cache_key = _get_cache_key_all_time(game_code)
    
    cache_enabled = getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False)
    
    # Try cache first
    if cache_enabled:
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for {scope} (game={game_code}, season={season_id})")
            return LeaderboardResponseDTO(
                scope=scope,
                entries=[
                    LeaderboardEntryDTO(**entry_data)
                    for entry_data in cached["entries"]
                ],
                metadata={
                    "scope": scope,
                    "game_code": game_code,
                    "season_id": season_id,
                    "count": len(cached["entries"]),
                    "cache_hit": True,
                    "cached_at": cached["cached_at"],
                }
            )
    
    # Cache miss - query database
    logger.info(f"Cache MISS for {scope} (game={game_code}, season={season_id}), querying DB")
    
    # Build query filters
    filters = Q(leaderboard_type=scope, is_active=True)
    
    if game_code:
        filters &= Q(game=game_code)
    
    if scope == "season" and season_id:
        filters &= Q(season=season_id)
    
    entries = LeaderboardEntry.objects.filter(filters).select_related(
        'player', 'team'
    ).order_by('rank')
    
    entry_dtos = _serialize_entries(entries)
    
    # Write to cache if enabled
    if cache_enabled and entry_dtos:
        cache_data = {
            "entries": [dto.__dict__ for dto in entry_dtos],
            "cached_at": datetime.utcnow().isoformat(),
        }
        # TTL: 1 hour for seasonal/game-specific, 24 hours for all-time
        ttl = 3600 if scope == "season" else 86400
        cache.set(cache_key, cache_data, timeout=ttl)
        logger.info(f"Cached {len(entry_dtos)} entries for {scope} (TTL={ttl}s)")
    
    return LeaderboardResponseDTO(
        scope=scope,
        entries=entry_dtos,
        metadata={
            "scope": scope,
            "game_code": game_code,
            "season_id": season_id,
            "count": len(entry_dtos),
            "cache_hit": False,
            "queried_at": datetime.utcnow().isoformat(),
        }
    )


def invalidate_tournament_cache(tournament_id: int) -> bool:
    """
    Invalidate cached leaderboard for a tournament.
    
    Args:
        tournament_id: Tournament ID to invalidate
        
    Returns:
        True if cache was cleared, False if caching disabled
        
    Usage:
        Call this after tournament leaderboard changes (e.g., match completion).
    """
    if not getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False):
        return False
    
    cache_key = _get_cache_key_tournament(tournament_id)
    cache.delete(cache_key)
    logger.info(f"Invalidated cache for tournament {tournament_id}")
    return True


def invalidate_player_history_cache(player_id: int) -> bool:
    """
    Invalidate cached player history.
    
    Args:
        player_id: Player ID to invalidate
        
    Returns:
        True if cache was cleared, False if caching disabled
        
    Usage:
        Call this after player's leaderboard entry changes.
    """
    if not getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False):
        return False
    
    cache_key = _get_cache_key_player_history(player_id)
    cache.delete(cache_key)
    logger.info(f"Invalidated player history cache for player {player_id}")
    return True


def invalidate_scoped_cache(
    scope: str,
    game_code: Optional[str] = None,
    season_id: Optional[str] = None
) -> bool:
    """
    Invalidate cached scoped leaderboard.
    
    Args:
        scope: "season" or "all_time"
        game_code: Optional game filter
        season_id: Required for scope="season"
        
    Returns:
        True if cache was cleared, False if caching disabled
        
    Usage:
        Call this after seasonal/all-time leaderboard recomputation.
    """
    if not getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False):
        return False
    
    if scope == "season":
        if not season_id:
            raise ValueError("season_id required for scope='season'")
        cache_key = _get_cache_key_season(season_id, game_code)
    else:
        cache_key = _get_cache_key_all_time(game_code)
    
    cache.delete(cache_key)
    logger.info(f"Invalidated cache for {scope} (game={game_code}, season={season_id})")
    return True


# ============================================================================
# Legacy Computation Service (Preserved for Celery Tasks)
# ============================================================================

class LeaderboardService:
    """
    Service for computing and retrieving leaderboards.
    
    Usage:
        service = LeaderboardService()
        service.compute_tournament_leaderboard(tournament_id=501)
        entries = service.get_leaderboard("tournament", tournament_id=501, limit=50)
    """
    
    # Point values for tournament placements
    PLACEMENT_POINTS = {
        1: 1000,
        2: 750,
        3: 500,
        4: 250,
        5: 250,
        6: 250,
        7: 250,
        8: 250,
        # 9-16: 100 points
        # 17+: 25 points (participation)
    }
    
    # Tier multipliers for seasonal rankings
    TIER_MULTIPLIERS = {
        "premier": 1.0,
        "standard": 0.5,
        "community": 0.25,
    }
    
    def get_placement_points(self, placement: int) -> int:
        """
        Get points for a given tournament placement.
        
        Args:
            placement: Tournament placement (1=1st, 2=2nd, etc.)
        
        Returns:
            Points earned for this placement.
        """
        if placement in self.PLACEMENT_POINTS:
            return self.PLACEMENT_POINTS[placement]
        elif 9 <= placement <= 16:
            return 100
        else:
            return 25  # Participation points
    
    def compute_tournament_leaderboard(self, tournament_id: int) -> List[LeaderboardEntry]:
        """
        Compute real-time tournament leaderboard.
        
        Ranks teams within a tournament based on:
        1. Placement (lower = better)
        2. Match wins
        3. Total points
        4. Registration timestamp (tie-breaker)
        
        Args:
            tournament_id: Tournament to compute leaderboard for
        
        Returns:
            List of LeaderboardEntry objects (not saved, just computed)
        """
        tournament = Tournament.objects.select_related('game', 'organizer').get(id=tournament_id)
        
        # Get all team registrations for this tournament
        # Module 9.1: Optimized with select_related for tournament, team
        # Planning ref: PART_5.2 Section 4.4 (Query Optimization)
        registrations = Registration.objects.filter(
            tournament=tournament,
            team_id__isnull=False,
            status='confirmed'
        ).select_related('tournament', 'team', 'user')
        
        entries = []
        for reg in registrations:
            team_id = reg.team_id
            # Count match wins/losses
            wins = Match.objects.filter(
                tournament=tournament,
                winner_id=team_id
            ).count()
            
            total_matches = Match.objects.filter(
                Q(team1_id=team_id) | Q(team2_id=team_id),
                tournament=tournament
            ).count()
            
            losses = total_matches - wins
            win_rate = (wins / total_matches * 100) if total_matches > 0 else 0.0
            
            # Calculate points (placement points + win bonus)
            # Note: placement data would need to be tracked elsewhere (e.g., in Match results)
            placement_points = 25  # Default points
            win_bonus = wins * 10  # 10 points per win
            total_points = placement_points + win_bonus
            
            entries.append({
                "team_id": team_id,
                "placement": 999,  # Placement not tracked in Registration model
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "points": total_points,
                "registered_at": tt.registered_at,
            })
        
        # Sort by placement, wins, points, registration time
        entries.sort(key=lambda e: (
            e["placement"],
            -e["wins"],  # More wins = higher rank
            -e["points"],  # More points = higher rank
            e["registered_at"]  # Earlier registration = tie-breaker
        ))
        
        # Assign ranks
        leaderboard_entries = []
        for rank, entry in enumerate(entries, start=1):
            leaderboard_entries.append(
                LeaderboardEntry(
                    leaderboard_type="tournament",
                    tournament=tournament,
                    team=entry["team"],
                    rank=rank,
                    points=entry["points"],
                    wins=entry["wins"],
                    losses=entry["losses"],
                    win_rate=entry["win_rate"],
                    is_active=True,
                )
            )
        
        return leaderboard_entries
    
    def save_tournament_leaderboard(self, tournament_id: int):
        """
        Compute and save tournament leaderboard to database.
        
        Clears existing entries and replaces with fresh computation.
        """
        entries = self.compute_tournament_leaderboard(tournament_id)
        
        # Delete old entries
        LeaderboardEntry.objects.filter(
            leaderboard_type="tournament",
            tournament_id=tournament_id
        ).delete()
        
        # Bulk create new entries
        LeaderboardEntry.objects.bulk_create(entries)
    
    def get_leaderboard(
        self,
        leaderboard_type: str,
        tournament_id: Optional[int] = None,
        game: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LeaderboardEntry]:
        """
        Retrieve leaderboard entries from database.
        
        Args:
            leaderboard_type: "tournament", "seasonal", "all_time", "team", "game_specific"
            tournament_id: Filter by tournament (for "tournament" type)
            game: Filter by game (for "game_specific" type)
            season: Filter by season (for "seasonal" type)
            limit: Max results to return
            offset: Pagination offset
        
        Returns:
            List of LeaderboardEntry objects
        """
        queryset = LeaderboardEntry.objects.filter(
            leaderboard_type=leaderboard_type,
            is_active=True
        ).order_by("rank")
        
        if tournament_id:
            queryset = queryset.filter(tournament_id=tournament_id)
        
        if game:
            queryset = queryset.filter(game=game)
        
        if season:
            queryset = queryset.filter(season=season)
        
        # Select related for efficient queries
        queryset = queryset.select_related("player", "team", "tournament")
        
        return list(queryset[offset:offset + limit])
    
    def get_player_rank(
        self,
        player_id: int,
        leaderboard_type: str,
        game: Optional[str] = None,
        season: Optional[str] = None
    ) -> Optional[LeaderboardEntry]:
        """
        Get specific player's rank in a leaderboard.
        
        Args:
            player_id: Player to look up
            leaderboard_type: Leaderboard type
            game: Game filter (optional)
            season: Season filter (optional)
        
        Returns:
            LeaderboardEntry if player is ranked, else None
        """
        filters = {
            "leaderboard_type": leaderboard_type,
            "player_id": player_id,
            "is_active": True,
        }
        
        if game:
            filters["game"] = game
        
        if season:
            filters["season"] = season
        
        try:
            return LeaderboardEntry.objects.get(**filters)
        except LeaderboardEntry.DoesNotExist:
            return None
    
    def snapshot_leaderboards(self):
        """
        Create daily snapshots of all leaderboards for historical tracking.
        
        Called by daily Celery task at 00:00 UTC.
        """
        today = timezone.now().date()
        
        # Snapshot all active leaderboard entries
        entries = LeaderboardEntry.objects.filter(is_active=True)
        
        snapshots = []
        for entry in entries:
            snapshots.append(
                LeaderboardSnapshot(
                    date=today,
                    leaderboard_type=entry.leaderboard_type,
                    player=entry.player,
                    team=entry.team,
                    rank=entry.rank,
                    points=entry.points,
                )
            )
        
        # Bulk create snapshots (upsert on conflict)
        LeaderboardSnapshot.objects.bulk_create(
            snapshots,
            update_conflicts=True,
            update_fields=["rank", "points"],
            unique_fields=["date", "leaderboard_type", "player", "team"]
        )
    
    def get_player_rank_history(
        self,
        player_id: int,
        leaderboard_type: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get player's rank history over time.
        
        Args:
            player_id: Player to look up
            leaderboard_type: Leaderboard type
            days: Number of days of history to retrieve
        
        Returns:
            List of dicts: [{"date": "2025-11-13", "rank": 5, "points": 2400}, ...]
        """
        start_date = timezone.now().date() - timedelta(days=days)
        
        snapshots = LeaderboardSnapshot.objects.filter(
            player_id=player_id,
            leaderboard_type=leaderboard_type,
            date__gte=start_date
        ).order_by("date")
        
        history = []
        for snapshot in snapshots:
            history.append({
                "date": snapshot.date.isoformat(),
                "rank": snapshot.rank,
                "points": snapshot.points,
            })
        
        return history
    
    def mark_inactive_players(self, days_threshold: int = 30):
        """
        Mark players as inactive if no activity in last N days.
        
        Args:
            days_threshold: Days of inactivity before marking inactive
        """
        cutoff = timezone.now() - timedelta(days=days_threshold)
        
        # Find players with no recent tournament participation
        inactive_players = User.objects.filter(
            registration__created_at__lt=cutoff
        ).distinct()
        
        # Mark leaderboard entries as inactive
        LeaderboardEntry.objects.filter(
            player__in=inactive_players
        ).update(is_active=False)


# Singleton instance
_leaderboard_service = LeaderboardService()


def get_leaderboard_service() -> LeaderboardService:
    """Get singleton leaderboard service instance."""
    return _leaderboard_service
