"""
Leaderboard Ranking Engine V2 (Phase F).

High-performance in-memory ranking computation with:
- Delta tracking (rank changes)
- Partial update mode (affected participants only)
- Incremental caching (Redis with 10-30s TTL)
- Battle Royale tiebreaker rules (points > kills > wins > matches_played)

Architecture:
    1. Compute rankings from Match results + LeaderboardEntry snapshots
    2. Track rank deltas (previous_rank → current_rank)
    3. Cache full rankings + deltas separately
    4. Support partial updates (only affected participants after match/dispute)

Feature Flags:
    LEADERBOARDS_ENGINE_V2_ENABLED: Enable V2 engine (default: False)
    LEADERBOARDS_CACHE_ENABLED: Enable Redis caching (from Phase E)

Observability:
    Uses existing apps.leaderboards.metrics instrumentation
    Logs: scope, source (engine_v2|snapshot|cache), duration_ms, IDs only

Performance Targets:
    - Tournament (10k participants): <500ms compute, <50ms cached read
    - Season (100k participants): <2s compute, <100ms cached read
    - All-time: Snapshot-only (no live compute)

IDs-Only Discipline:
    All outputs use participant_id, team_id, tournament_id (no PII).
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set, Tuple
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, F, Sum, Count, Max, Min, Prefetch
from django.utils import timezone

from apps.leaderboards.models import LeaderboardEntry, LeaderboardSnapshot
from apps.tournaments.models import Tournament, Match, Registration
from apps.teams.models import Team
from apps.accounts.models import User
from apps.leaderboards.metrics import record_leaderboard_request


logger = logging.getLogger(__name__)


# ============================================================================
# DTOs (Data Transfer Objects) - Engine V2
# ============================================================================

@dataclass
class RankDeltaDTO:
    """
    Rank change tracking (IDs-only).
    
    Attributes:
        participant_id: Player user ID (for solo tournaments)
        team_id: Team ID (for team tournaments)
        previous_rank: Rank before update (None if new entry)
        current_rank: Rank after update
        rank_change: Difference (negative = improvement, positive = decline)
        points: Current points
        last_updated: Timestamp of this ranking
    """
    participant_id: Optional[int]
    team_id: Optional[int]
    previous_rank: Optional[int]
    current_rank: int
    rank_change: int  # negative = moved up, positive = moved down
    points: int
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "participant_id": self.participant_id,
            "team_id": self.team_id,
            "previous_rank": self.previous_rank,
            "current_rank": self.current_rank,
            "rank_change": self.rank_change,
            "points": self.points,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class RankedParticipantDTO:
    """
    Fully ranked participant with stats (IDs-only).
    
    Attributes:
        rank: Current rank (1-indexed)
        participant_id: Player user ID (for solo tournaments)
        team_id: Team ID (for team tournaments)
        points: Total points
        kills: Total kills (Battle Royale tiebreaker 1)
        wins: Total wins (Battle Royale tiebreaker 2)
        losses: Total losses
        matches_played: Total matches (Battle Royale tiebreaker 3)
        earliest_win: Earliest win timestamp (Battle Royale tiebreaker 4)
        win_rate: Win percentage (0.00-100.00)
        last_updated: Timestamp of last ranking
    """
    rank: int
    participant_id: Optional[int]
    team_id: Optional[int]
    points: int
    kills: int
    wins: int
    losses: int
    matches_played: int
    earliest_win: Optional[datetime]
    win_rate: float
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "rank": self.rank,
            "participant_id": self.participant_id,
            "team_id": self.team_id,
            "points": self.points,
            "kills": self.kills,
            "wins": self.wins,
            "losses": self.losses,
            "matches_played": self.matches_played,
            "earliest_win": self.earliest_win.isoformat() if self.earliest_win else None,
            "win_rate": round(self.win_rate, 2),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class RankingResponseDTO:
    """
    Complete ranking response with metadata (IDs-only).
    
    Attributes:
        scope: "tournament", "season", or "all_time"
        rankings: List of ranked participants
        deltas: List of rank changes (empty if no previous snapshot)
        metadata: Source, timing, counts
    """
    scope: str
    rankings: List[RankedParticipantDTO]
    deltas: List[RankDeltaDTO]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "scope": self.scope,
            "rankings": [r.to_dict() for r in self.rankings],
            "deltas": [d.to_dict() for d in self.deltas],
            "metadata": self.metadata,
        }


# ============================================================================
# Cache Key Generation
# ============================================================================

def _get_engine_cache_key_rankings(scope: str, ref_id: Optional[int] = None) -> str:
    """
    Generate cache key for full rankings.
    
    Args:
        scope: "tournament", "season", or "all_time"
        ref_id: Tournament ID, season ID, or None for all-time
        
    Returns:
        Cache key string
        
    Examples:
        ranking:full:tournament:123
        ranking:full:season:2025_S1
        ranking:full:all_time
    """
    if ref_id:
        return f"ranking:full:{scope}:{ref_id}"
    return f"ranking:full:{scope}"


def _get_engine_cache_key_deltas(scope: str, ref_id: Optional[int] = None) -> str:
    """
    Generate cache key for rank deltas.
    
    Args:
        scope: "tournament", "season", or "all_time"
        ref_id: Tournament ID, season ID, or None for all-time
        
    Returns:
        Cache key string
        
    Examples:
        ranking:delta:tournament:123
        ranking:delta:season:2025_S1
        ranking:delta:all_time
    """
    if ref_id:
        return f"ranking:delta:{scope}:{ref_id}"
    return f"ranking:delta:{scope}"


# ============================================================================
# Core Ranking Computation Engine
# ============================================================================

class RankingEngine:
    """
    High-performance ranking computation engine (Phase F).
    
    Methods:
        compute_tournament_rankings(): Compute tournament leaderboard
        compute_season_rankings(): Compute season leaderboard
        compute_all_time_rankings(): Compute all-time leaderboard
        compute_partial_update(): Recompute only affected participants
        
    Ranking Rules (Battle Royale Tiebreakers):
        1. Points DESC (primary sort)
        2. Kills DESC (tiebreaker 1)
        3. Wins DESC (tiebreaker 2)
        4. Matches Played ASC (tiebreaker 3 - fewer matches = better)
        5. Earliest Win ASC (tiebreaker 4 - older win = better)
        6. Participant ID ASC (final tiebreaker for deterministic ordering)
    """
    
    def __init__(self, cache_ttl: int = 30):
        """
        Initialize ranking engine.
        
        Args:
            cache_ttl: Cache TTL in seconds (default: 30s for fast spectator updates)
        """
        self.cache_ttl = cache_ttl
        self.cache_enabled = getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False)
        self.engine_enabled = getattr(settings, "LEADERBOARDS_ENGINE_V2_ENABLED", False)
    
    def compute_tournament_rankings(
        self,
        tournament_id: int,
        limit: Optional[int] = None,
        use_cache: bool = True
    ) -> RankingResponseDTO:
        """
        Compute tournament leaderboard with rank deltas.
        
        Args:
            tournament_id: Tournament ID to compute rankings for
            limit: Optional limit on number of results (default: all)
            use_cache: Whether to use cache (default: True)
            
        Returns:
            RankingResponseDTO with full rankings + deltas
            
        Behavior:
            1. Check cache if enabled + use_cache=True
            2. On cache miss: Query Match results + aggregate stats
            3. Apply Battle Royale tiebreaker rules
            4. Compute rank deltas (compare to previous snapshot)
            5. Write to cache (full rankings + deltas separately)
            6. Return response DTO
            
        Performance:
            - Cache hit: <50ms (Redis read)
            - Cache miss (10k participants): ~500ms
            
        Examples:
            >>> engine = RankingEngine()
            >>> response = engine.compute_tournament_rankings(tournament_id=123)
            >>> print(response.rankings[:3])  # Top 3
            >>> print(response.deltas[:5])    # Recent movers
        """
        start_time = time.time()
        
        # Check if engine is enabled
        if not self.engine_enabled:
            logger.info(f"Engine V2 disabled for tournament {tournament_id}")
            return RankingResponseDTO(
                scope="tournament",
                rankings=[],
                deltas=[],
                metadata={
                    "tournament_id": tournament_id,
                    "source": "disabled",
                    "engine_v2_enabled": False,
                    "count": 0,
                }
            )
        
        # Check cache first
        if use_cache and self.cache_enabled:
            cache_key_rankings = _get_engine_cache_key_rankings("tournament", tournament_id)
            cache_key_deltas = _get_engine_cache_key_deltas("tournament", tournament_id)
            
            cached_rankings = cache.get(cache_key_rankings)
            cached_deltas = cache.get(cache_key_deltas)
            
            if cached_rankings and cached_deltas:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(f"Engine V2 cache HIT for tournament {tournament_id} ({duration_ms}ms)")
                
                return RankingResponseDTO(
                    scope="tournament",
                    rankings=[RankedParticipantDTO(**r) for r in cached_rankings],
                    deltas=[RankDeltaDTO(**d) for d in cached_deltas],
                    metadata={
                        "tournament_id": tournament_id,
                        "source": "cache",
                        "cache_hit": True,
                        "count": len(cached_rankings),
                        "duration_ms": duration_ms,
                    }
                )
        
        # Cache miss - compute rankings
        logger.info(f"Engine V2 cache MISS for tournament {tournament_id}, computing...")
        
        # Fetch tournament
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            logger.error(f"Tournament {tournament_id} not found")
            return RankingResponseDTO(
                scope="tournament",
                rankings=[],
                deltas=[],
                metadata={
                    "tournament_id": tournament_id,
                    "source": "error",
                    "error": "tournament_not_found",
                    "count": 0,
                }
            )
        
        # Aggregate match stats (Battle Royale scoring)
        match_stats = self._aggregate_tournament_stats(tournament_id, tournament.is_team_based)
        
        # Get previous rankings for delta computation
        previous_rankings = self._get_previous_rankings("tournament", tournament_id)
        
        # Compute rankings with BR tiebreaker rules
        rankings = self._apply_ranking_rules(match_stats, tournament.is_team_based)
        
        # Compute deltas
        deltas = self._compute_deltas(rankings, previous_rankings)
        
        # Apply limit if specified
        if limit:
            rankings = rankings[:limit]
            # Filter deltas to only include participants in limited rankings
            limited_ids = {
                (r.participant_id, r.team_id) for r in rankings
            }
            deltas = [
                d for d in deltas
                if (d.participant_id, d.team_id) in limited_ids
            ]
        
        # Write to cache
        if self.cache_enabled:
            cache_key_rankings = _get_engine_cache_key_rankings("tournament", tournament_id)
            cache_key_deltas = _get_engine_cache_key_deltas("tournament", tournament_id)
            
            cache.set(
                cache_key_rankings,
                [asdict(r) for r in rankings],
                timeout=self.cache_ttl
            )
            cache.set(
                cache_key_deltas,
                [asdict(d) for d in deltas],
                timeout=self.cache_ttl
            )
            logger.info(f"Cached {len(rankings)} rankings + {len(deltas)} deltas (TTL={self.cache_ttl}s)")
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Computed tournament {tournament_id} rankings in {duration_ms}ms ({len(rankings)} participants)")
        
        return RankingResponseDTO(
            scope="tournament",
            rankings=rankings,
            deltas=deltas,
            metadata={
                "tournament_id": tournament_id,
                "source": "engine_v2",
                "cache_hit": False,
                "count": len(rankings),
                "delta_count": len(deltas),
                "duration_ms": duration_ms,
                "computed_at": timezone.now().isoformat(),
            }
        )
    
    def compute_season_rankings(
        self,
        season_id: str,
        game_code: str,
        limit: Optional[int] = None,
        use_cache: bool = True
    ) -> RankingResponseDTO:
        """
        Compute season leaderboard across multiple tournaments.
        
        Args:
            season_id: Season identifier (e.g., "2025_S1")
            game_code: Game code filter (e.g., "valorant", "cs2")
            limit: Optional limit on number of results
            use_cache: Whether to use cache (default: True)
            
        Returns:
            RankingResponseDTO with full rankings + deltas
            
        Behavior:
            1. Query all tournaments for season + game
            2. Aggregate stats across tournaments
            3. Apply ranking rules
            4. Compute deltas vs previous season snapshot
            5. Cache results (1-hour TTL)
            
        Performance:
            - Cache hit: <100ms
            - Cache miss (100k participants): ~2s
            
        Examples:
            >>> engine = RankingEngine()
            >>> response = engine.compute_season_rankings(
            ...     season_id="2025_S1",
            ...     game_code="valorant",
            ...     limit=100
            ... )
        """
        start_time = time.time()
        
        if not self.engine_enabled:
            logger.info(f"Engine V2 disabled for season {season_id}")
            return RankingResponseDTO(
                scope="season",
                rankings=[],
                deltas=[],
                metadata={
                    "season_id": season_id,
                    "game_code": game_code,
                    "source": "disabled",
                    "engine_v2_enabled": False,
                    "count": 0,
                }
            )
        
        # Check cache
        cache_key_id = f"{season_id}:{game_code}"
        if use_cache and self.cache_enabled:
            cache_key_rankings = _get_engine_cache_key_rankings("season", cache_key_id)
            cache_key_deltas = _get_engine_cache_key_deltas("season", cache_key_id)
            
            cached_rankings = cache.get(cache_key_rankings)
            cached_deltas = cache.get(cache_key_deltas)
            
            if cached_rankings and cached_deltas:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(f"Engine V2 cache HIT for season {season_id}/{game_code} ({duration_ms}ms)")
                
                return RankingResponseDTO(
                    scope="season",
                    rankings=[RankedParticipantDTO(**r) for r in cached_rankings],
                    deltas=[RankDeltaDTO(**d) for d in cached_deltas],
                    metadata={
                        "season_id": season_id,
                        "game_code": game_code,
                        "source": "cache",
                        "cache_hit": True,
                        "count": len(cached_rankings),
                        "duration_ms": duration_ms,
                    }
                )
        
        logger.info(f"Engine V2 cache MISS for season {season_id}/{game_code}, computing...")
        
        # Aggregate stats across all season tournaments
        match_stats = self._aggregate_season_stats(season_id, game_code)
        
        # Get previous rankings
        previous_rankings = self._get_previous_rankings("season", cache_key_id)
        
        # Compute rankings
        rankings = self._apply_ranking_rules(match_stats, is_team_based=False)  # Cross-tournament = solo aggregation
        
        # Compute deltas
        deltas = self._compute_deltas(rankings, previous_rankings)
        
        # Apply limit
        if limit:
            rankings = rankings[:limit]
            limited_ids = {(r.participant_id, r.team_id) for r in rankings}
            deltas = [d for d in deltas if (d.participant_id, d.team_id) in limited_ids]
        
        # Write to cache (1-hour TTL for season)
        if self.cache_enabled:
            cache_key_rankings = _get_engine_cache_key_rankings("season", cache_key_id)
            cache_key_deltas = _get_engine_cache_key_deltas("season", cache_key_id)
            
            cache.set(cache_key_rankings, [asdict(r) for r in rankings], timeout=3600)
            cache.set(cache_key_deltas, [asdict(d) for d in deltas], timeout=3600)
            logger.info(f"Cached {len(rankings)} season rankings (TTL=3600s)")
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Computed season {season_id}/{game_code} rankings in {duration_ms}ms ({len(rankings)} participants)")
        
        return RankingResponseDTO(
            scope="season",
            rankings=rankings,
            deltas=deltas,
            metadata={
                "season_id": season_id,
                "game_code": game_code,
                "source": "engine_v2",
                "cache_hit": False,
                "count": len(rankings),
                "delta_count": len(deltas),
                "duration_ms": duration_ms,
                "computed_at": timezone.now().isoformat(),
            }
        )
    
    def compute_all_time_rankings(
        self,
        game_code: Optional[str] = None,
        limit: Optional[int] = None
    ) -> RankingResponseDTO:
        """
        Compute all-time leaderboard (snapshot-only, no live compute).
        
        Args:
            game_code: Optional game filter (None = cross-game)
            limit: Optional limit on number of results
            
        Returns:
            RankingResponseDTO with rankings from latest snapshot
            
        Behavior:
            - All-time rankings are TOO EXPENSIVE to compute live
            - This method returns pre-computed snapshots only
            - Snapshots updated by Celery task (daily/weekly)
            - No deltas (all-time delta tracking not useful)
            
        Performance:
            - Snapshot read: <200ms (database query)
            
        Examples:
            >>> engine = RankingEngine()
            >>> response = engine.compute_all_time_rankings(game_code="valorant", limit=100)
        """
        start_time = time.time()
        
        logger.info(f"Fetching all-time rankings snapshot (game={game_code})")
        
        # Query latest snapshot
        filters = Q(leaderboard_type="all_time")
        if game_code:
            filters &= Q(game=game_code)
        
        snapshot = LeaderboardSnapshot.objects.filter(filters).order_by('-snapshot_date').first()
        
        if not snapshot:
            logger.warning(f"No all-time snapshot found (game={game_code})")
            return RankingResponseDTO(
                scope="all_time",
                rankings=[],
                deltas=[],
                metadata={
                    "game_code": game_code,
                    "source": "snapshot",
                    "error": "no_snapshot_found",
                    "count": 0,
                }
            )
        
        # Deserialize snapshot data
        rankings_data = snapshot.data.get("rankings", [])
        rankings = [
            RankedParticipantDTO(
                rank=r["rank"],
                participant_id=r.get("participant_id"),
                team_id=r.get("team_id"),
                points=r["points"],
                kills=r.get("kills", 0),
                wins=r["wins"],
                losses=r["losses"],
                matches_played=r["matches_played"],
                earliest_win=datetime.fromisoformat(r["earliest_win"]) if r.get("earliest_win") else None,
                win_rate=r["win_rate"],
                last_updated=datetime.fromisoformat(r["last_updated"]),
            )
            for r in rankings_data
        ]
        
        # Apply limit
        if limit:
            rankings = rankings[:limit]
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Fetched {len(rankings)} all-time rankings from snapshot in {duration_ms}ms")
        
        return RankingResponseDTO(
            scope="all_time",
            rankings=rankings,
            deltas=[],  # No deltas for all-time
            metadata={
                "game_code": game_code,
                "source": "snapshot",
                "snapshot_date": snapshot.snapshot_date.isoformat(),
                "count": len(rankings),
                "duration_ms": duration_ms,
            }
        )
    
    def compute_partial_update(
        self,
        tournament_id: int,
        affected_participant_ids: Set[int],
        affected_team_ids: Set[int]
    ) -> RankingResponseDTO:
        """
        Recompute rankings for only affected participants (partial update).
        
        Args:
            tournament_id: Tournament ID
            affected_participant_ids: Set of participant IDs to recompute
            affected_team_ids: Set of team IDs to recompute
            
        Returns:
            RankingResponseDTO with updated rankings for affected participants
            
        Behavior:
            1. Fetch current cached rankings (or compute if missing)
            2. Recompute stats for affected participants only
            3. Merge updated stats with existing rankings
            4. Re-sort entire leaderboard (ranks may shift)
            5. Compute deltas for affected participants
            6. Update cache
            
        Use Cases:
            - After match completion: Recompute only match participants
            - After dispute resolution: Recompute only disputed participants
            - After sanction: Recompute only sanctioned participant
            
        Performance:
            - Partial update (10 affected out of 10k): ~50ms
            - Full recompute fallback: ~500ms
            
        Examples:
            >>> engine = RankingEngine()
            >>> # Match 123 ended with players 456, 789
            >>> response = engine.compute_partial_update(
            ...     tournament_id=123,
            ...     affected_participant_ids={456, 789},
            ...     affected_team_ids=set()
            ... )
            >>> # Only players 456, 789 have updated stats in response.deltas
        """
        start_time = time.time()
        
        logger.info(f"Partial update for tournament {tournament_id}: {len(affected_participant_ids)} participants, {len(affected_team_ids)} teams")
        
        # Fetch current rankings (from cache or compute)
        current_response = self.compute_tournament_rankings(tournament_id, use_cache=True)
        
        if not current_response.rankings:
            # No existing rankings, fallback to full compute
            logger.warning(f"No existing rankings for tournament {tournament_id}, falling back to full compute")
            return self.compute_tournament_rankings(tournament_id, use_cache=False)
        
        # Build map of current rankings
        current_map = {}
        for r in current_response.rankings:
            key = (r.participant_id, r.team_id)
            current_map[key] = r
        
        # Recompute stats for affected participants only
        tournament = Tournament.objects.get(id=tournament_id)
        affected_stats = self._aggregate_tournament_stats_partial(
            tournament_id,
            tournament.is_team_based,
            affected_participant_ids,
            affected_team_ids
        )
        
        # Merge updated stats with existing rankings
        for stats in affected_stats:
            key = (stats.get("participant_id"), stats.get("team_id"))
            # Remove old entry if exists
            if key in current_map:
                del current_map[key]
        
        # Convert remaining current rankings back to stats format
        remaining_stats = [
            {
                "participant_id": r.participant_id,
                "team_id": r.team_id,
                "points": r.points,
                "kills": r.kills,
                "wins": r.wins,
                "losses": r.losses,
                "matches_played": r.matches_played,
                "earliest_win": r.earliest_win,
                "last_updated": r.last_updated,
            }
            for r in current_map.values()
        ]
        
        # Merge affected + remaining
        merged_stats = affected_stats + remaining_stats
        
        # Re-apply ranking rules (full re-sort)
        rankings = self._apply_ranking_rules(merged_stats, tournament.is_team_based)
        
        # Compute deltas (only for affected participants)
        previous_rankings = {
            (r.participant_id, r.team_id): r
            for r in current_response.rankings
        }
        
        deltas = []
        for r in rankings:
            key = (r.participant_id, r.team_id)
            if key[0] in affected_participant_ids or key[1] in affected_team_ids:
                prev = previous_rankings.get(key)
                prev_rank = prev.rank if prev else None
                
                if prev_rank is None or r.rank != prev_rank:
                    deltas.append(RankDeltaDTO(
                        participant_id=r.participant_id,
                        team_id=r.team_id,
                        previous_rank=prev_rank,
                        current_rank=r.rank,
                        rank_change=r.rank - prev_rank if prev_rank else 0,
                        points=r.points,
                        last_updated=r.last_updated,
                    ))
        
        # Update cache
        if self.cache_enabled:
            cache_key_rankings = _get_engine_cache_key_rankings("tournament", tournament_id)
            cache_key_deltas = _get_engine_cache_key_deltas("tournament", tournament_id)
            
            cache.set(cache_key_rankings, [asdict(r) for r in rankings], timeout=self.cache_ttl)
            cache.set(cache_key_deltas, [asdict(d) for d in deltas], timeout=self.cache_ttl)
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Partial update complete in {duration_ms}ms ({len(deltas)} affected participants)")
        
        return RankingResponseDTO(
            scope="tournament",
            rankings=rankings,
            deltas=deltas,
            metadata={
                "tournament_id": tournament_id,
                "source": "partial_update",
                "affected_count": len(affected_participant_ids) + len(affected_team_ids),
                "delta_count": len(deltas),
                "duration_ms": duration_ms,
                "computed_at": timezone.now().isoformat(),
            }
        )
    
    # ========================================================================
    # Internal Helper Methods
    # ========================================================================
    
    def _aggregate_tournament_stats(
        self,
        tournament_id: int,
        is_team_based: bool
    ) -> List[Dict[str, Any]]:
        """
        Aggregate match stats for all participants in tournament.
        
        Returns:
            List of stat dicts with keys:
            - participant_id / team_id
            - points, kills, wins, losses, matches_played
            - earliest_win
            - last_updated
        """
        # Query all completed matches
        # Module 9.1: Optimized with select_related for tournament, teams, participants
        # Planning ref: PART_5.2 Section 4.4 (Query Optimization)
        matches = Match.objects.filter(
            tournament_id=tournament_id,
            status="completed"
        ).select_related(
            "tournament",
            "winner_participant",
            "winner_team",
            "participant1",
            "participant2",
            "team1",
            "team2"
        )
        
        stats = {}
        
        for match in matches:
            # Extract participants from match
            if is_team_based:
                participants = [
                    ("team", match.team1_id),
                    ("team", match.team2_id),
                ]
            else:
                participants = [
                    ("participant", match.participant1_id),
                    ("participant", match.participant2_id),
                ]
            
            for ptype, pid in participants:
                if pid is None:
                    continue
                
                key = ("team", pid) if ptype == "team" else ("participant", pid)
                
                if key not in stats:
                    stats[key] = {
                        "participant_id": pid if ptype == "participant" else None,
                        "team_id": pid if ptype == "team" else None,
                        "points": 0,
                        "kills": 0,
                        "wins": 0,
                        "losses": 0,
                        "matches_played": 0,
                        "earliest_win": None,
                        "last_updated": timezone.now(),
                    }
                
                # Increment match count
                stats[key]["matches_played"] += 1
                
                # Check if winner
                if is_team_based:
                    is_winner = match.winner_team_id == pid
                else:
                    is_winner = match.winner_participant_id == pid
                
                if is_winner:
                    stats[key]["wins"] += 1
                    # Track earliest win
                    if stats[key]["earliest_win"] is None:
                        stats[key]["earliest_win"] = match.completed_at or match.updated_at
                    else:
                        win_time = match.completed_at or match.updated_at
                        if win_time < stats[key]["earliest_win"]:
                            stats[key]["earliest_win"] = win_time
                else:
                    stats[key]["losses"] += 1
                
                # Add points from match scores
                if is_team_based:
                    if match.team1_id == pid:
                        stats[key]["points"] += match.team1_score or 0
                        stats[key]["kills"] += match.team1_kills or 0
                    elif match.team2_id == pid:
                        stats[key]["points"] += match.team2_score or 0
                        stats[key]["kills"] += match.team2_kills or 0
                else:
                    if match.participant1_id == pid:
                        stats[key]["points"] += match.participant1_score or 0
                        stats[key]["kills"] += match.participant1_kills or 0
                    elif match.participant2_id == pid:
                        stats[key]["points"] += match.participant2_score or 0
                        stats[key]["kills"] += match.participant2_kills or 0
        
        return list(stats.values())
    
    def _aggregate_tournament_stats_partial(
        self,
        tournament_id: int,
        is_team_based: bool,
        affected_participant_ids: Set[int],
        affected_team_ids: Set[int]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate match stats for only affected participants (partial update).
        """
        if is_team_based:
            matches = Match.objects.filter(
                tournament_id=tournament_id,
                status="completed"
            ).filter(
                Q(team1_id__in=affected_team_ids) | Q(team2_id__in=affected_team_ids)
            )
        else:
            matches = Match.objects.filter(
                tournament_id=tournament_id,
                status="completed"
            ).filter(
                Q(participant1_id__in=affected_participant_ids) | Q(participant2_id__in=affected_participant_ids)
            )
        
        stats = {}
        
        for match in matches:
            if is_team_based:
                participants = [
                    ("team", match.team1_id),
                    ("team", match.team2_id),
                ]
            else:
                participants = [
                    ("participant", match.participant1_id),
                    ("participant", match.participant2_id),
                ]
            
            for ptype, pid in participants:
                if pid is None:
                    continue
                
                # Only process affected participants
                if ptype == "team" and pid not in affected_team_ids:
                    continue
                if ptype == "participant" and pid not in affected_participant_ids:
                    continue
                
                key = ("team", pid) if ptype == "team" else ("participant", pid)
                
                if key not in stats:
                    stats[key] = {
                        "participant_id": pid if ptype == "participant" else None,
                        "team_id": pid if ptype == "team" else None,
                        "points": 0,
                        "kills": 0,
                        "wins": 0,
                        "losses": 0,
                        "matches_played": 0,
                        "earliest_win": None,
                        "last_updated": timezone.now(),
                    }
                
                stats[key]["matches_played"] += 1
                
                if is_team_based:
                    is_winner = match.winner_team_id == pid
                else:
                    is_winner = match.winner_participant_id == pid
                
                if is_winner:
                    stats[key]["wins"] += 1
                    if stats[key]["earliest_win"] is None:
                        stats[key]["earliest_win"] = match.completed_at or match.updated_at
                    else:
                        win_time = match.completed_at or match.updated_at
                        if win_time < stats[key]["earliest_win"]:
                            stats[key]["earliest_win"] = win_time
                else:
                    stats[key]["losses"] += 1
                
                if is_team_based:
                    if match.team1_id == pid:
                        stats[key]["points"] += match.team1_score or 0
                        stats[key]["kills"] += match.team1_kills or 0
                    elif match.team2_id == pid:
                        stats[key]["points"] += match.team2_score or 0
                        stats[key]["kills"] += match.team2_kills or 0
                else:
                    if match.participant1_id == pid:
                        stats[key]["points"] += match.participant1_score or 0
                        stats[key]["kills"] += match.participant1_kills or 0
                    elif match.participant2_id == pid:
                        stats[key]["points"] += match.participant2_score or 0
                        stats[key]["kills"] += match.participant2_kills or 0
        
        return list(stats.values())
    
    def _aggregate_season_stats(
        self,
        season_id: str,
        game_code: str
    ) -> List[Dict[str, Any]]:
        """
        Aggregate match stats across all tournaments in season.
        """
        # Query tournaments for season + game
        tournaments = Tournament.objects.filter(
            season=season_id,
            game__code=game_code
        )
        
        stats = {}
        
        for tournament in tournaments:
            tournament_stats = self._aggregate_tournament_stats(
                tournament.id,
                tournament.is_team_based
            )
            
            # Merge with existing stats
            for ts in tournament_stats:
                key = (ts["participant_id"], ts["team_id"])
                
                if key not in stats:
                    stats[key] = ts
                else:
                    # Aggregate across tournaments
                    stats[key]["points"] += ts["points"]
                    stats[key]["kills"] += ts["kills"]
                    stats[key]["wins"] += ts["wins"]
                    stats[key]["losses"] += ts["losses"]
                    stats[key]["matches_played"] += ts["matches_played"]
                    
                    # Keep earliest win
                    if ts["earliest_win"]:
                        if stats[key]["earliest_win"] is None:
                            stats[key]["earliest_win"] = ts["earliest_win"]
                        else:
                            if ts["earliest_win"] < stats[key]["earliest_win"]:
                                stats[key]["earliest_win"] = ts["earliest_win"]
        
        return list(stats.values())
    
    def _apply_ranking_rules(
        self,
        stats: List[Dict[str, Any]],
        is_team_based: bool
    ) -> List[RankedParticipantDTO]:
        """
        Apply Battle Royale tiebreaker rules and assign ranks.
        
        Ranking Rules:
            1. Points DESC (primary)
            2. Kills DESC (tiebreaker 1)
            3. Wins DESC (tiebreaker 2)
            4. Matches Played ASC (tiebreaker 3 - fewer matches = better)
            5. Earliest Win ASC (tiebreaker 4 - older win = better)
            6. Participant/Team ID ASC (final deterministic tiebreaker)
        """
        # Sort by BR rules
        sorted_stats = sorted(
            stats,
            key=lambda s: (
                -s["points"],                          # Points DESC
                -s["kills"],                           # Kills DESC
                -s["wins"],                            # Wins DESC
                s["matches_played"],                   # Matches ASC (fewer = better)
                s["earliest_win"] or datetime.max,     # Earliest win ASC (older = better)
                s["participant_id"] or s["team_id"],   # ID ASC (deterministic)
            )
        )
        
        # Assign ranks
        rankings = []
        for rank, s in enumerate(sorted_stats, start=1):
            win_rate = (s["wins"] / s["matches_played"] * 100) if s["matches_played"] > 0 else 0.0
            
            rankings.append(RankedParticipantDTO(
                rank=rank,
                participant_id=s["participant_id"],
                team_id=s["team_id"],
                points=s["points"],
                kills=s["kills"],
                wins=s["wins"],
                losses=s["losses"],
                matches_played=s["matches_played"],
                earliest_win=s["earliest_win"],
                win_rate=win_rate,
                last_updated=s["last_updated"],
            ))
        
        return rankings
    
    def _get_previous_rankings(
        self,
        scope: str,
        ref_id: Any
    ) -> Dict[Tuple[Optional[int], Optional[int]], int]:
        """
        Fetch previous rankings for delta computation.
        
        Returns:
            Dict mapping (participant_id, team_id) -> previous_rank
        """
        # Try cache first
        cache_key = _get_engine_cache_key_rankings(scope, ref_id)
        cached = cache.get(cache_key)
        
        if cached:
            return {
                (r["participant_id"], r["team_id"]): r["rank"]
                for r in cached
            }
        
        # Fallback: Query latest snapshot
        filters = Q(leaderboard_type=scope)
        if scope == "tournament":
            filters &= Q(tournament_id=ref_id)
        elif scope == "season":
            # ref_id is "season_id:game_code"
            season_id, game_code = str(ref_id).split(":")
            filters &= Q(season=season_id, game=game_code)
        
        snapshot = LeaderboardSnapshot.objects.filter(filters).order_by('-snapshot_date').first()
        
        if not snapshot:
            return {}
        
        rankings_data = snapshot.data.get("rankings", [])
        return {
            (r.get("participant_id"), r.get("team_id")): r["rank"]
            for r in rankings_data
        }
    
    def _compute_deltas(
        self,
        current_rankings: List[RankedParticipantDTO],
        previous_rankings: Dict[Tuple[Optional[int], Optional[int]], int]
    ) -> List[RankDeltaDTO]:
        """
        Compute rank deltas between current and previous rankings.
        
        Returns:
            List of RankDeltaDTO for participants with rank changes
        """
        deltas = []
        
        for r in current_rankings:
            key = (r.participant_id, r.team_id)
            prev_rank = previous_rankings.get(key)
            
            # Only create delta if rank changed or participant is new
            if prev_rank is None or r.rank != prev_rank:
                rank_change = r.rank - prev_rank if prev_rank else 0
                
                deltas.append(RankDeltaDTO(
                    participant_id=r.participant_id,
                    team_id=r.team_id,
                    previous_rank=prev_rank,
                    current_rank=r.rank,
                    rank_change=rank_change,
                    points=r.points,
                    last_updated=r.last_updated,
                ))
        
        return deltas


# ============================================================================
# Convenience Functions
# ============================================================================

def invalidate_ranking_cache(scope: str, ref_id: Optional[int] = None) -> bool:
    """
    Invalidate cached rankings for given scope.
    
    Args:
        scope: "tournament", "season", or "all_time"
        ref_id: Tournament ID, season ID, or None for all-time
        
    Returns:
        True if cache was cleared, False if caching disabled
        
    Examples:
        >>> invalidate_ranking_cache("tournament", 123)
        >>> invalidate_ranking_cache("season", "2025_S1:valorant")
    """
    if not getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False):
        return False
    
    cache_key_rankings = _get_engine_cache_key_rankings(scope, ref_id)
    cache_key_deltas = _get_engine_cache_key_deltas(scope, ref_id)
    
    cache.delete(cache_key_rankings)
    cache.delete(cache_key_deltas)
    
    logger.info(f"Invalidated ranking cache for {scope}:{ref_id}")
    return True
