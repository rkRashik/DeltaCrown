"""
Analytics Engine Service — User/Team performance analytics layer.

This service computes advanced analytics: ELO estimation, tier assignment,
percentile ranking, rolling averages, and multi-dimensional leaderboards.

The canonical tournament-level analytics (organizer dashboards, CSV export,
materialized view routing) lives in:
    apps.tournaments.services.analytics_service.AnalyticsService

This engine is accessible from that canonical service via bridge methods:
    AnalyticsService.get_user_analytics(user_id)
    AnalyticsService.get_team_analytics(team_id)

NO ORM IMPORTS — Uses AnalyticsAdapter only.

Reference: Phase 8, Epic 8.5 — Advanced Analytics & Ranking Tiers
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import statistics

from apps.tournament_ops.dtos import (
    UserAnalyticsDTO,
    TeamAnalyticsDTO,
    LeaderboardEntryDTO,
    SeasonDTO,
    AnalyticsQueryDTO,
    TierBoundaries,
    UserStatsDTO,
    TeamStatsDTO,
    TeamRankingDTO,
    MatchHistoryEntryDTO,
)
from apps.tournament_ops.adapters import (
    AnalyticsAdapter,
    UserStatsAdapter,
    TeamStatsAdapter,
    TeamRankingAdapter,
    MatchHistoryAdapter,
)


class AnalyticsEngineService:
    """
    Analytics engine for computing performance metrics, tier assignments, and leaderboards.
    
    Responsibilities:
    - Compute user analytics (rolling averages, streaks, percentile, tier)
    - Compute team analytics (ELO volatility, synergy, activity score)
    - Generate multi-dimensional leaderboards (global, game, seasonal, MMR, ELO, tier)
    - Apply decay rules for seasonal rankings
    - Trigger analytics jobs and metrics
    
    Architecture: NO ORM - uses adapters only for data access.
    """
    
    def __init__(
        self,
        analytics_adapter: AnalyticsAdapter,
        user_stats_adapter: UserStatsAdapter,
        team_stats_adapter: TeamStatsAdapter,
        team_ranking_adapter: TeamRankingAdapter,
        match_history_adapter: MatchHistoryAdapter,
    ):
        """
        Initialize analytics engine with required adapters.
        
        Args:
            analytics_adapter: Analytics data access adapter
            user_stats_adapter: User stats adapter (Epic 8.2)
            team_stats_adapter: Team stats adapter (Epic 8.3)
            team_ranking_adapter: Team ranking adapter (Epic 8.3)
            match_history_adapter: Match history adapter (Epic 8.4)
        """
        self.analytics_adapter = analytics_adapter
        self.user_stats_adapter = user_stats_adapter
        self.team_stats_adapter = team_stats_adapter
        self.team_ranking_adapter = team_ranking_adapter
        self.match_history_adapter = match_history_adapter
    
    # =============================================================================
    # User Analytics Computation
    # =============================================================================
    
    def compute_user_analytics(
        self,
        user_id: int,
        game_slug: str
    ) -> UserAnalyticsDTO:
        """
        Compute comprehensive analytics for a user in a specific game.
        
        Computes:
        - MMR/ELO snapshot
        - Win rate (overall + rolling 7d/30d)
        - KDA ratio
        - Match volume (7d/30d)
        - Current streak (win/loss)
        - Longest win streak
        - Tier assignment (based on ELO)
        - Percentile ranking
        
        Args:
            user_id: User ID
            game_slug: Game identifier
        
        Returns:
            UserAnalyticsDTO with computed analytics
        """
        # Get base stats from Epic 8.2
        user_stats = self.user_stats_adapter.get_user_stats(user_id, game_slug)
        if not user_stats:
            # No stats yet - return default analytics
            return self._create_default_user_analytics(user_id, game_slug)
        
        # Get match history from Epic 8.4 for rolling averages
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        # Get recent match history (last 30 days)
        recent_matches = self._get_user_recent_matches(user_id, game_slug, thirty_days_ago)
        
        # Compute rolling averages
        matches_7d = [m for m in recent_matches if m["completed_at"] >= seven_days_ago]
        matches_30d = recent_matches
        
        win_rate_7d = self._calculate_win_rate([m for m in matches_7d])
        win_rate_30d = self._calculate_win_rate([m for m in matches_30d])
        
        # Detect streaks
        current_streak = self._calculate_current_streak(recent_matches)
        longest_win_streak = self._calculate_longest_win_streak(recent_matches)
        
        # Calculate tier from ELO/MMR
        # For users, we use UserStats win_rate as proxy for ELO
        # (In real implementation, use actual ELO from ranking system if available)
        estimated_elo = self._estimate_user_elo(user_stats)
        tier = TierBoundaries.calculate_tier(estimated_elo)
        
        # Calculate percentile ranking
        percentile = self._calculate_user_percentile(user_id, game_slug, estimated_elo)
        
        # Build analytics snapshot data
        snapshot_data = {
            "mmr_snapshot": estimated_elo,
            "elo_snapshot": estimated_elo,
            "win_rate": user_stats.win_rate,
            "kda_ratio": user_stats.kd_ratio,
            "matches_last_7d": len(matches_7d),
            "matches_last_30d": len(matches_30d),
            "win_rate_7d": win_rate_7d,
            "win_rate_30d": win_rate_30d,
            "current_streak": current_streak,
            "longest_win_streak": longest_win_streak,
            "tier": tier,
            "percentile_rank": percentile,
        }
        
        # Save snapshot to database via adapter
        return self.analytics_adapter.update_user_snapshot(user_id, game_slug, snapshot_data)
    
    def _create_default_user_analytics(self, user_id: int, game_slug: str) -> UserAnalyticsDTO:
        """Create default analytics for user with no match history."""
        snapshot_data = {
            "mmr_snapshot": 1200,
            "elo_snapshot": 1200,
            "win_rate": Decimal("0.0"),
            "kda_ratio": Decimal("0.0"),
            "matches_last_7d": 0,
            "matches_last_30d": 0,
            "win_rate_7d": Decimal("0.0"),
            "win_rate_30d": Decimal("0.0"),
            "current_streak": 0,
            "longest_win_streak": 0,
            "tier": "bronze",
            "percentile_rank": Decimal("50.0"),
        }
        return self.analytics_adapter.update_user_snapshot(user_id, game_slug, snapshot_data)
    
    def _get_user_recent_matches(
        self,
        user_id: int,
        game_slug: str,
        since: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get recent user matches from match history.
        
        Returns list of dicts with: is_winner, is_draw, completed_at
        """
        # Get match history via adapter
        match_history = self.match_history_adapter.get_user_match_history(
            user_id=user_id,
            game_slug=game_slug,
            limit=100  # Last 100 matches should cover 30 days for active users
        )
        
        # Filter by date and convert to simplified dict
        matches = []
        for entry in match_history:
            if entry.completed_at >= since:
                matches.append({
                    "is_winner": entry.is_winner,
                    "is_draw": entry.is_draw,
                    "completed_at": entry.completed_at,
                })
        
        return matches
    
    def _calculate_win_rate(self, matches: List[Dict[str, Any]]) -> Decimal:
        """Calculate win rate from match list."""
        if not matches:
            return Decimal("0.0")
        
        wins = sum(1 for m in matches if m["is_winner"])
        return Decimal(str((wins / len(matches)) * 100))
    
    def _calculate_current_streak(self, matches: List[Dict[str, Any]]) -> int:
        """
        Calculate current win/loss streak.
        
        Positive = win streak, Negative = loss streak.
        Returns 0 if no recent matches or last match was draw.
        """
        if not matches:
            return 0
        
        # Sort by completed_at descending (most recent first)
        sorted_matches = sorted(matches, key=lambda m: m["completed_at"], reverse=True)
        
        # Check most recent match
        latest = sorted_matches[0]
        if latest["is_draw"]:
            return 0
        
        is_win_streak = latest["is_winner"]
        streak = 0
        
        for match in sorted_matches:
            if match["is_draw"]:
                break
            if match["is_winner"] == is_win_streak:
                streak += 1
            else:
                break
        
        return streak if is_win_streak else -streak
    
    def _calculate_longest_win_streak(self, matches: List[Dict[str, Any]]) -> int:
        """Calculate longest consecutive win streak."""
        if not matches:
            return 0
        
        # Sort by completed_at ascending (oldest first)
        sorted_matches = sorted(matches, key=lambda m: m["completed_at"])
        
        longest = 0
        current = 0
        
        for match in sorted_matches:
            if match["is_winner"]:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        
        return longest
    
    def _estimate_user_elo(self, user_stats: UserStatsDTO) -> int:
        """
        Estimate user ELO from stats.
        
        Uses win rate and match count to estimate competitive rating.
        Real implementation should use actual ELO if available.
        """
        if user_stats.matches_played == 0:
            return 1200  # Default starting ELO
        
        # Simple estimation: map win rate to ELO range
        # 0% win rate → 800 ELO
        # 50% win rate → 1200 ELO (default)
        # 100% win rate → 2800 ELO
        win_rate_decimal = float(user_stats.win_rate) / 100
        base_elo = 800 + (win_rate_decimal * 2000)
        
        # Adjust for experience (more matches = more confident rating)
        experience_factor = min(1.0, user_stats.matches_played / 50)
        final_elo = int(base_elo * (0.8 + 0.2 * experience_factor))
        
        return max(800, min(2800, final_elo))
    
    def _calculate_user_percentile(
        self,
        user_id: int,
        game_slug: str,
        user_elo: int
    ) -> Decimal:
        """
        Calculate percentile ranking for user.
        
        Percentile = (users with lower ELO / total users) * 100
        """
        # Get all user snapshots for game
        query = AnalyticsQueryDTO(
            game_slug=game_slug,
            limit=10000,  # Get all users for accurate percentile
        )
        all_snapshots = self.analytics_adapter.list_user_snapshots(query)
        
        if not all_snapshots:
            return Decimal("50.0")  # Default if no data
        
        # Count users with lower ELO
        lower_count = sum(1 for s in all_snapshots if s.elo_snapshot < user_elo)
        percentile = (lower_count / len(all_snapshots)) * 100
        
        return Decimal(str(round(percentile, 2)))
    
    # =============================================================================
    # Team Analytics Computation
    # =============================================================================
    
    def compute_team_analytics(
        self,
        team_id: int,
        game_slug: str
    ) -> TeamAnalyticsDTO:
        """
        Compute comprehensive analytics for a team in a specific game.
        
        Computes:
        - ELO snapshot + volatility
        - Average member skill (from team members' analytics)
        - Win rate (overall + rolling 7d/30d)
        - Synergy score (performance consistency)
        - Activity score (recent match participation)
        - Tier assignment
        - Percentile ranking
        
        Args:
            team_id: Team ID
            game_slug: Game identifier
        
        Returns:
            TeamAnalyticsDTO with computed analytics
        """
        # Get team stats and ranking from Epic 8.3
        team_stats = self.team_stats_adapter.get_team_stats(team_id, game_slug)
        team_ranking = self.team_ranking_adapter.get_team_ranking(team_id, game_slug)
        
        if not team_stats or not team_ranking:
            return self._create_default_team_analytics(team_id, game_slug)
        
        # Get recent match history
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        recent_matches = self._get_team_recent_matches(team_id, game_slug, thirty_days_ago)
        
        # Compute rolling averages
        matches_7d = [m for m in recent_matches if m["completed_at"] >= seven_days_ago]
        matches_30d = recent_matches
        
        win_rate_7d = self._calculate_win_rate(matches_7d)
        win_rate_30d = self._calculate_win_rate(matches_30d)
        
        # Calculate ELO volatility from recent ELO changes
        elo_volatility = self._calculate_elo_volatility(recent_matches)
        
        # Calculate synergy score (consistency of performance)
        synergy_score = self._calculate_synergy_score(matches_30d)
        
        # Calculate activity score (match participation frequency)
        activity_score = self._calculate_activity_score(len(matches_7d), len(matches_30d))
        
        # Calculate average member skill (would need team members' analytics)
        # For now, use team ELO as proxy
        avg_member_skill = Decimal(str(team_ranking.elo_rating))
        
        # Calculate tier and percentile
        tier = TierBoundaries.calculate_tier(team_ranking.elo_rating)
        percentile = self._calculate_team_percentile(team_id, game_slug, team_ranking.elo_rating)
        
        # Build analytics snapshot data
        snapshot_data = {
            "elo_snapshot": team_ranking.elo_rating,
            "elo_volatility": elo_volatility,
            "avg_member_skill": avg_member_skill,
            "win_rate": team_stats.win_rate,
            "win_rate_7d": win_rate_7d,
            "win_rate_30d": win_rate_30d,
            "synergy_score": synergy_score,
            "activity_score": activity_score,
            "matches_last_7d": len(matches_7d),
            "matches_last_30d": len(matches_30d),
            "tier": tier,
            "percentile_rank": percentile,
        }
        
        return self.analytics_adapter.update_team_snapshot(team_id, game_slug, snapshot_data)
    
    def _create_default_team_analytics(self, team_id: int, game_slug: str) -> TeamAnalyticsDTO:
        """Create default analytics for team with no match history."""
        snapshot_data = {
            "elo_snapshot": 1200,
            "elo_volatility": Decimal("0.0"),
            "avg_member_skill": Decimal("1200.0"),
            "win_rate": Decimal("0.0"),
            "win_rate_7d": Decimal("0.0"),
            "win_rate_30d": Decimal("0.0"),
            "synergy_score": Decimal("0.0"),
            "activity_score": Decimal("0.0"),
            "matches_last_7d": 0,
            "matches_last_30d": 0,
            "tier": "bronze",
            "percentile_rank": Decimal("50.0"),
        }
        return self.analytics_adapter.update_team_snapshot(team_id, game_slug, snapshot_data)
    
    def _get_team_recent_matches(
        self,
        team_id: int,
        game_slug: str,
        since: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get recent team matches from match history.
        
        Returns list of dicts with: is_winner, is_draw, elo_change, completed_at
        """
        match_history = self.match_history_adapter.get_team_match_history(
            team_id=team_id,
            game_slug=game_slug,
            limit=100
        )
        
        matches = []
        for entry in match_history:
            if entry.completed_at >= since:
                matches.append({
                    "is_winner": entry.is_winner,
                    "is_draw": entry.is_draw,
                    "elo_change": entry.elo_change,
                    "completed_at": entry.completed_at,
                })
        
        return matches
    
    def _calculate_elo_volatility(self, matches: List[Dict[str, Any]]) -> Decimal:
        """
        Calculate ELO volatility (standard deviation of ELO changes).
        
        Higher volatility = more inconsistent performance.
        """
        if len(matches) < 2:
            return Decimal("0.0")
        
        elo_changes = [m["elo_change"] for m in matches if m["elo_change"] is not None]
        
        if not elo_changes:
            return Decimal("0.0")
        
        # Calculate standard deviation
        mean = statistics.mean(elo_changes)
        variance = sum((x - mean) ** 2 for x in elo_changes) / len(elo_changes)
        std_dev = variance ** 0.5
        
        return Decimal(str(round(std_dev, 2)))
    
    def _calculate_synergy_score(self, matches: List[Dict[str, Any]]) -> Decimal:
        """
        Calculate team synergy score (0-100).
        
        Higher score = more consistent win/loss patterns (good teamwork).
        Lower score = inconsistent/random results.
        
        Simplified: based on win rate consistency.
        """
        if len(matches) < 5:
            return Decimal("0.0")  # Need minimum data
        
        # Calculate win rate variance across time windows
        # High variance = inconsistent, Low variance = consistent
        
        # Split matches into 5-game windows
        window_size = 5
        win_rates = []
        
        for i in range(0, len(matches) - window_size + 1, window_size):
            window = matches[i:i+window_size]
            wins = sum(1 for m in window if m["is_winner"])
            win_rate = wins / window_size
            win_rates.append(win_rate)
        
        if not win_rates:
            return Decimal("50.0")
        
        # Calculate consistency (inverse of variance)
        mean_wr = statistics.mean(win_rates)
        variance = sum((wr - mean_wr) ** 2 for wr in win_rates) / len(win_rates)
        consistency = 1 - variance  # 0 = inconsistent, 1 = perfectly consistent
        
        synergy = consistency * 100
        return Decimal(str(round(synergy, 2)))
    
    def _calculate_activity_score(
        self,
        matches_7d: int,
        matches_30d: int
    ) -> Decimal:
        """
        Calculate activity score (0-100) based on recent match participation.
        
        Considers both frequency and consistency of activity.
        """
        # Ideal: ~10 matches per 7 days = highly active
        # Acceptable: ~5 matches per 7 days = moderately active
        # Low: <2 matches per 7 days = inactive
        
        # Recent activity (70% weight)
        recent_score = min(100, (matches_7d / 10) * 100) * 0.7
        
        # Overall activity (30% weight)
        overall_score = min(100, (matches_30d / 40) * 100) * 0.3
        
        total = recent_score + overall_score
        return Decimal(str(round(total, 2)))
    
    def _calculate_team_percentile(
        self,
        team_id: int,
        game_slug: str,
        team_elo: int
    ) -> Decimal:
        """Calculate percentile ranking for team."""
        query = AnalyticsQueryDTO(
            game_slug=game_slug,
            limit=10000,
        )
        all_snapshots = self.analytics_adapter.list_team_snapshots(query)
        
        if not all_snapshots:
            return Decimal("50.0")
        
        lower_count = sum(1 for s in all_snapshots if s.elo_snapshot < team_elo)
        percentile = (lower_count / len(all_snapshots)) * 100
        
        return Decimal(str(round(percentile, 2)))
    
    # =============================================================================
    # Leaderboard Aggregation
    # =============================================================================
    
    def generate_leaderboard(
        self,
        leaderboard_type: str,
        game_slug: Optional[str] = None,
        season_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LeaderboardEntryDTO]:
        """
        Generate leaderboard entries based on type.
        
        Supported types:
        - "global_user": Global user rankings (all games)
        - "game_user": Game-specific user rankings
        - "team": Team rankings
        - "seasonal": Seasonal user rankings
        - "mmr": MMR-based rankings
        - "elo": ELO-based rankings
        - "tier": Tier-based rankings (Crown → Diamond → Gold → Silver → Bronze)
        
        Args:
            leaderboard_type: Type of leaderboard
            game_slug: Optional game filter
            season_id: Optional season filter
            limit: Maximum entries
        
        Returns:
            List of LeaderboardEntryDTO sorted by rank
        """
        if leaderboard_type == "global_user":
            return self._generate_global_user_leaderboard(limit)
        elif leaderboard_type == "game_user":
            if not game_slug:
                raise ValueError("game_slug required for game_user leaderboard")
            return self._generate_game_user_leaderboard(game_slug, limit)
        elif leaderboard_type == "team":
            return self._generate_team_leaderboard(game_slug, limit)
        elif leaderboard_type == "seasonal":
            if not season_id:
                raise ValueError("season_id required for seasonal leaderboard")
            return self._generate_seasonal_leaderboard(game_slug, season_id, limit)
        elif leaderboard_type in ["mmr", "elo"]:
            return self._generate_elo_leaderboard(game_slug, limit)
        elif leaderboard_type == "tier":
            return self._generate_tier_leaderboard(game_slug, limit)
        else:
            raise ValueError(f"Unknown leaderboard type: {leaderboard_type}")
    
    def _generate_global_user_leaderboard(self, limit: int) -> List[LeaderboardEntryDTO]:
        """Generate global user leaderboard (aggregated across all games)."""
        # Get all user snapshots, aggregate by user
        query = AnalyticsQueryDTO(limit=10000)
        all_snapshots = self.analytics_adapter.list_user_snapshots(query)
        
        # Aggregate by user (sum ELO across games)
        user_totals = defaultdict(lambda: {"elo": 0, "wins": 0, "losses": 0, "games": 0})
        
        for snapshot in all_snapshots:
            user_totals[snapshot.user_id]["elo"] += snapshot.elo_snapshot
            user_totals[snapshot.user_id]["games"] += 1
        
        # Calculate average ELO and rank
        ranked_users = []
        for user_id, data in user_totals.items():
            avg_elo = data["elo"] // data["games"]
            ranked_users.append((user_id, avg_elo))
        
        # Sort by ELO descending
        ranked_users.sort(key=lambda x: x[1], reverse=True)
        
        # Create leaderboard entries
        entries = []
        for rank, (user_id, elo) in enumerate(ranked_users[:limit], start=1):
            entries.append(LeaderboardEntryDTO(
                leaderboard_type="global_user",
                rank=rank,
                reference_id=user_id,
                score=elo,
                payload={"tier": TierBoundaries.calculate_tier(elo)},
            ))
        
        return entries
    
    def _generate_game_user_leaderboard(
        self,
        game_slug: str,
        limit: int
    ) -> List[LeaderboardEntryDTO]:
        """Generate game-specific user leaderboard."""
        query = AnalyticsQueryDTO(game_slug=game_slug, limit=limit, order_by="-elo_snapshot")
        snapshots = self.analytics_adapter.list_user_snapshots(query)
        
        entries = []
        for rank, snapshot in enumerate(snapshots, start=1):
            entries.append(LeaderboardEntryDTO(
                leaderboard_type="game_user",
                rank=rank,
                reference_id=snapshot.user_id,
                game_slug=game_slug,
                score=snapshot.elo_snapshot,
                wins=0,  # Would need to fetch from stats
                losses=0,
                win_rate=snapshot.win_rate,
                payload={
                    "tier": snapshot.tier,
                    "percentile": float(snapshot.percentile_rank),
                    "kda": float(snapshot.kda_ratio),
                    "streak": snapshot.current_streak,
                },
            ))
        
        return entries
    
    def _generate_team_leaderboard(
        self,
        game_slug: Optional[str],
        limit: int
    ) -> List[LeaderboardEntryDTO]:
        """Generate team leaderboard."""
        query = AnalyticsQueryDTO(game_slug=game_slug, limit=limit, order_by="-elo_snapshot")
        snapshots = self.analytics_adapter.list_team_snapshots(query)
        
        entries = []
        for rank, snapshot in enumerate(snapshots, start=1):
            entries.append(LeaderboardEntryDTO(
                leaderboard_type="team",
                rank=rank,
                reference_id=snapshot.team_id,
                game_slug=game_slug,
                score=snapshot.elo_snapshot,
                win_rate=snapshot.win_rate,
                payload={
                    "tier": snapshot.tier,
                    "percentile": float(snapshot.percentile_rank),
                    "synergy": float(snapshot.synergy_score),
                    "activity": float(snapshot.activity_score),
                },
            ))
        
        return entries
    
    def _generate_seasonal_leaderboard(
        self,
        game_slug: Optional[str],
        season_id: str,
        limit: int
    ) -> List[LeaderboardEntryDTO]:
        """
        Generate seasonal leaderboard with decay rules.
        
        Applies seasonal decay rules to rankings.
        """
        # Get current season
        season = self.analytics_adapter.get_current_season()
        if not season or season.season_id != season_id:
            # If not current season, get historical leaderboard
            return self.analytics_adapter.get_leaderboard("seasonal", game_slug, season_id, limit)
        
        # Generate fresh leaderboard with decay
        query = AnalyticsQueryDTO(game_slug=game_slug, limit=limit, order_by="-elo_snapshot")
        snapshots = self.analytics_adapter.list_user_snapshots(query)
        
        # Apply decay rules
        decay_rules = season.decay_rules
        entries = []
        
        for rank, snapshot in enumerate(snapshots, start=1):
            # Apply decay if configured
            decayed_elo = self._apply_decay(
                elo=snapshot.elo_snapshot,
                recalculated_at=snapshot.recalculated_at,
                decay_rules=decay_rules
            )
            
            entries.append(LeaderboardEntryDTO(
                leaderboard_type="seasonal",
                rank=rank,
                reference_id=snapshot.user_id,
                game_slug=game_slug,
                season_id=season_id,
                score=decayed_elo,
                win_rate=snapshot.win_rate,
                payload={
                    "tier": TierBoundaries.calculate_tier(decayed_elo),
                    "original_elo": snapshot.elo_snapshot,
                    "decay_applied": snapshot.elo_snapshot - decayed_elo,
                },
            ))
        
        return entries
    
    def _generate_elo_leaderboard(
        self,
        game_slug: Optional[str],
        limit: int
    ) -> List[LeaderboardEntryDTO]:
        """Generate ELO-based leaderboard (same as game_user for now)."""
        return self._generate_game_user_leaderboard(game_slug, limit) if game_slug else []
    
    def _generate_tier_leaderboard(
        self,
        game_slug: Optional[str],
        limit: int
    ) -> List[LeaderboardEntryDTO]:
        """
        Generate tier-based leaderboard (grouped by tier).
        
        Returns top players from each tier (Crown → Diamond → Gold → Silver → Bronze).
        """
        all_entries = []
        
        for tier in ["crown", "diamond", "gold", "silver", "bronze"]:
            query = AnalyticsQueryDTO(
                game_slug=game_slug,
                tier=tier,
                limit=20,  # Top 20 per tier
                order_by="-elo_snapshot"
            )
            snapshots = self.analytics_adapter.list_user_snapshots(query)
            
            for snapshot in snapshots:
                all_entries.append(LeaderboardEntryDTO(
                    leaderboard_type="tier",
                    rank=0,  # Will be set later
                    reference_id=snapshot.user_id,
                    game_slug=game_slug,
                    score=snapshot.elo_snapshot,
                    win_rate=snapshot.win_rate,
                    payload={"tier": snapshot.tier},
                ))
        
        # Sort by tier priority (Crown > Diamond > Gold > Silver > Bronze), then ELO
        tier_priority = {"crown": 5, "diamond": 4, "gold": 3, "silver": 2, "bronze": 1}
        all_entries.sort(key=lambda e: (tier_priority[e.payload["tier"]], e.score), reverse=True)
        
        # Assign ranks
        for rank, entry in enumerate(all_entries[:limit], start=1):
            entry.rank = rank
        
        return all_entries[:limit]
    
    def _apply_decay(
        self,
        elo: int,
        recalculated_at: datetime,
        decay_rules: Dict[str, Any]
    ) -> int:
        """
        Apply seasonal decay rules to ELO.
        
        Decay rules format:
        {
            "enabled": bool,
            "days_inactive": int,
            "decay_percentage": float,
            "min_elo": int
        }
        """
        if not decay_rules.get("enabled", False):
            return elo
        
        days_inactive_threshold = decay_rules.get("days_inactive", 14)
        decay_percentage = decay_rules.get("decay_percentage", 5.0)
        min_elo = decay_rules.get("min_elo", 800)
        
        # Calculate days since last recalculation
        now = datetime.now()
        days_inactive = (now - recalculated_at).days
        
        if days_inactive < days_inactive_threshold:
            return elo
        
        # Apply decay
        decay_amount = int(elo * (decay_percentage / 100))
        decayed_elo = max(min_elo, elo - decay_amount)
        
        return decayed_elo
    
    # =============================================================================
    # Batch Operations
    # =============================================================================
    
    def refresh_all_user_analytics(self, game_slug: Optional[str] = None) -> int:
        """
        Refresh analytics for all users in a game (or all games).
        
        Used by nightly Celery job.
        
        Returns:
            Count of users refreshed
        """
        # Get all user stats
        if game_slug:
            # Get users for specific game
            # Would need adapter method to list all users with stats for game
            # For now, simplified implementation
            count = 0
            # In real implementation: iterate all users with stats for game
            return count
        else:
            # Get all users across all games
            # Would batch process all users
            return 0
    
    def refresh_all_team_analytics(self, game_slug: Optional[str] = None) -> int:
        """
        Refresh analytics for all teams in a game (or all games).
        
        Used by nightly Celery job.
        
        Returns:
            Count of teams refreshed
        """
        # Similar to user refresh
        return 0
    
    def refresh_all_leaderboards(self) -> Dict[str, int]:
        """
        Refresh all leaderboards.
        
        Used by hourly Celery job.
        
        Returns:
            Dict mapping leaderboard type to entry count
        """
        results = {}
        
        # Get all active games (would need game adapter)
        games = ["valorant", "csgo", "lol"]  # Hardcoded for now
        
        # Refresh game-specific leaderboards
        for game in games:
            entries = self.generate_leaderboard("game_user", game_slug=game, limit=100)
            count = self.analytics_adapter.save_leaderboard_entries(entries)
            results[f"game_user_{game}"] = count
        
        # Refresh team leaderboards
        for game in games:
            entries = self.generate_leaderboard("team", game_slug=game, limit=100)
            count = self.analytics_adapter.save_leaderboard_entries(entries)
            results[f"team_{game}"] = count
        
        # Refresh global leaderboard
        entries = self.generate_leaderboard("global_user", limit=100)
        count = self.analytics_adapter.save_leaderboard_entries(entries)
        results["global_user"] = count
        
        return results
