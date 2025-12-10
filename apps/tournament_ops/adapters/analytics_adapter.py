"""
Analytics Adapter for Epic 8.5 - Advanced Analytics, Ranking Tiers & Real-Time Leaderboards.

Data access layer for analytics snapshots, leaderboards, and seasons.
Uses method-level ORM imports only to maintain architecture boundaries.

Reference: Phase 8, Epic 8.5 - Advanced Analytics & Ranking Tiers
"""

from typing import List, Optional, Protocol
from datetime import datetime
from decimal import Decimal

from apps.tournament_ops.dtos import (
    UserAnalyticsDTO,
    TeamAnalyticsDTO,
    LeaderboardEntryDTO,
    SeasonDTO,
    AnalyticsQueryDTO,
)


class AnalyticsAdapterProtocol(Protocol):
    """Protocol defining analytics adapter interface."""
    
    def get_user_snapshot(
        self, 
        user_id: int, 
        game_slug: str
    ) -> Optional[UserAnalyticsDTO]:
        """Get user analytics snapshot for a specific game."""
        ...
    
    def update_user_snapshot(
        self,
        user_id: int,
        game_slug: str,
        snapshot_data: dict
    ) -> UserAnalyticsDTO:
        """Update or create user analytics snapshot."""
        ...
    
    def list_user_snapshots(
        self,
        query: AnalyticsQueryDTO
    ) -> List[UserAnalyticsDTO]:
        """List user analytics snapshots with filtering."""
        ...
    
    def get_team_snapshot(
        self,
        team_id: int,
        game_slug: str
    ) -> Optional[TeamAnalyticsDTO]:
        """Get team analytics snapshot for a specific game."""
        ...
    
    def update_team_snapshot(
        self,
        team_id: int,
        game_slug: str,
        snapshot_data: dict
    ) -> TeamAnalyticsDTO:
        """Update or create team analytics snapshot."""
        ...
    
    def list_team_snapshots(
        self,
        query: AnalyticsQueryDTO
    ) -> List[TeamAnalyticsDTO]:
        """List team analytics snapshots with filtering."""
        ...
    
    def save_leaderboard_entries(
        self,
        entries: List[LeaderboardEntryDTO]
    ) -> int:
        """Bulk save leaderboard entries, return count saved."""
        ...
    
    def get_leaderboard(
        self,
        leaderboard_type: str,
        game_slug: Optional[str] = None,
        season_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LeaderboardEntryDTO]:
        """Get leaderboard entries with filtering."""
        ...
    
    def get_current_season(self) -> Optional[SeasonDTO]:
        """Get currently active season."""
        ...
    
    def list_seasons(
        self,
        include_inactive: bool = False
    ) -> List[SeasonDTO]:
        """List all seasons, optionally including inactive ones."""
        ...


class AnalyticsAdapter:
    """
    Concrete adapter for analytics data access.
    Uses method-level ORM imports to maintain architecture boundaries.
    """
    
    def get_user_snapshot(
        self, 
        user_id: int, 
        game_slug: str
    ) -> Optional[UserAnalyticsDTO]:
        """
        Get user analytics snapshot for a specific game.
        
        Args:
            user_id: User ID
            game_slug: Game identifier
        
        Returns:
            UserAnalyticsDTO if snapshot exists, None otherwise
        """
        from apps.leaderboards.models import UserAnalyticsSnapshot
        
        try:
            snapshot = UserAnalyticsSnapshot.objects.get(
                user_id=user_id,
                game_slug=game_slug
            )
            return UserAnalyticsDTO.from_model(snapshot)
        except UserAnalyticsSnapshot.DoesNotExist:
            return None
    
    def update_user_snapshot(
        self,
        user_id: int,
        game_slug: str,
        snapshot_data: dict
    ) -> UserAnalyticsDTO:
        """
        Update or create user analytics snapshot.
        
        Args:
            user_id: User ID
            game_slug: Game identifier
            snapshot_data: Dictionary with analytics fields
        
        Returns:
            Updated UserAnalyticsDTO
        """
        from apps.leaderboards.models import UserAnalyticsSnapshot
        
        # Extract tier from snapshot_data or calculate from ELO
        tier = snapshot_data.get("tier")
        if not tier:
            elo = snapshot_data.get("elo_snapshot", 1200)
            tier = UserAnalyticsSnapshot.calculate_tier(elo)
        
        snapshot, created = UserAnalyticsSnapshot.objects.update_or_create(
            user_id=user_id,
            game_slug=game_slug,
            defaults={
                "mmr_snapshot": snapshot_data.get("mmr_snapshot", 1200),
                "elo_snapshot": snapshot_data.get("elo_snapshot", 1200),
                "win_rate": snapshot_data.get("win_rate", Decimal("0.0")),
                "kda_ratio": snapshot_data.get("kda_ratio", Decimal("0.0")),
                "matches_last_7d": snapshot_data.get("matches_last_7d", 0),
                "matches_last_30d": snapshot_data.get("matches_last_30d", 0),
                "win_rate_7d": snapshot_data.get("win_rate_7d", Decimal("0.0")),
                "win_rate_30d": snapshot_data.get("win_rate_30d", Decimal("0.0")),
                "current_streak": snapshot_data.get("current_streak", 0),
                "longest_win_streak": snapshot_data.get("longest_win_streak", 0),
                "tier": tier,
                "percentile_rank": snapshot_data.get("percentile_rank", Decimal("50.0")),
            }
        )
        
        # Refresh from DB to get auto_now field
        snapshot.refresh_from_db()
        return UserAnalyticsDTO.from_model(snapshot)
    
    def list_user_snapshots(
        self,
        query: AnalyticsQueryDTO
    ) -> List[UserAnalyticsDTO]:
        """
        List user analytics snapshots with filtering.
        
        Args:
            query: AnalyticsQueryDTO with filtering parameters
        
        Returns:
            List of UserAnalyticsDTO instances
        """
        from apps.leaderboards.models import UserAnalyticsSnapshot
        from django.db.models import Q
        
        queryset = UserAnalyticsSnapshot.objects.all()
        
        # Apply filters
        if query.game_slug:
            queryset = queryset.filter(game_slug=query.game_slug)
        
        if query.tier:
            queryset = queryset.filter(tier=query.tier)
        
        if query.min_elo is not None:
            queryset = queryset.filter(elo_snapshot__gte=query.min_elo)
        
        if query.max_elo is not None:
            queryset = queryset.filter(elo_snapshot__lte=query.max_elo)
        
        if query.min_percentile is not None:
            queryset = queryset.filter(percentile_rank__gte=query.min_percentile)
        
        if query.max_percentile is not None:
            queryset = queryset.filter(percentile_rank__lte=query.max_percentile)
        
        # Apply ordering
        queryset = queryset.order_by(query.order_by)
        
        # Apply pagination
        queryset = queryset[query.offset:query.offset + query.limit]
        
        return [UserAnalyticsDTO.from_model(snapshot) for snapshot in queryset]
    
    def get_team_snapshot(
        self,
        team_id: int,
        game_slug: str
    ) -> Optional[TeamAnalyticsDTO]:
        """
        Get team analytics snapshot for a specific game.
        
        Args:
            team_id: Team ID
            game_slug: Game identifier
        
        Returns:
            TeamAnalyticsDTO if snapshot exists, None otherwise
        """
        from apps.leaderboards.models import TeamAnalyticsSnapshot
        
        try:
            snapshot = TeamAnalyticsSnapshot.objects.get(
                team_id=team_id,
                game_slug=game_slug
            )
            return TeamAnalyticsDTO.from_model(snapshot)
        except TeamAnalyticsSnapshot.DoesNotExist:
            return None
    
    def update_team_snapshot(
        self,
        team_id: int,
        game_slug: str,
        snapshot_data: dict
    ) -> TeamAnalyticsDTO:
        """
        Update or create team analytics snapshot.
        
        Args:
            team_id: Team ID
            game_slug: Game identifier
            snapshot_data: Dictionary with analytics fields
        
        Returns:
            Updated TeamAnalyticsDTO
        """
        from apps.leaderboards.models import TeamAnalyticsSnapshot
        
        # Extract tier from snapshot_data or calculate from ELO
        tier = snapshot_data.get("tier")
        if not tier:
            elo = snapshot_data.get("elo_snapshot", 1200)
            tier = TeamAnalyticsSnapshot.calculate_tier(elo)
        
        snapshot, created = TeamAnalyticsSnapshot.objects.update_or_create(
            team_id=team_id,
            game_slug=game_slug,
            defaults={
                "elo_snapshot": snapshot_data.get("elo_snapshot", 1200),
                "elo_volatility": snapshot_data.get("elo_volatility", Decimal("0.0")),
                "avg_member_skill": snapshot_data.get("avg_member_skill", Decimal("1200.0")),
                "win_rate": snapshot_data.get("win_rate", Decimal("0.0")),
                "win_rate_7d": snapshot_data.get("win_rate_7d", Decimal("0.0")),
                "win_rate_30d": snapshot_data.get("win_rate_30d", Decimal("0.0")),
                "synergy_score": snapshot_data.get("synergy_score", Decimal("0.0")),
                "activity_score": snapshot_data.get("activity_score", Decimal("0.0")),
                "matches_last_7d": snapshot_data.get("matches_last_7d", 0),
                "matches_last_30d": snapshot_data.get("matches_last_30d", 0),
                "tier": tier,
                "percentile_rank": snapshot_data.get("percentile_rank", Decimal("50.0")),
            }
        )
        
        # Refresh from DB to get auto_now field
        snapshot.refresh_from_db()
        return TeamAnalyticsDTO.from_model(snapshot)
    
    def list_team_snapshots(
        self,
        query: AnalyticsQueryDTO
    ) -> List[TeamAnalyticsDTO]:
        """
        List team analytics snapshots with filtering.
        
        Args:
            query: AnalyticsQueryDTO with filtering parameters
        
        Returns:
            List of TeamAnalyticsDTO instances
        """
        from apps.leaderboards.models import TeamAnalyticsSnapshot
        
        queryset = TeamAnalyticsSnapshot.objects.all()
        
        # Apply filters
        if query.game_slug:
            queryset = queryset.filter(game_slug=query.game_slug)
        
        if query.tier:
            queryset = queryset.filter(tier=query.tier)
        
        if query.min_elo is not None:
            queryset = queryset.filter(elo_snapshot__gte=query.min_elo)
        
        if query.max_elo is not None:
            queryset = queryset.filter(elo_snapshot__lte=query.max_elo)
        
        if query.min_percentile is not None:
            queryset = queryset.filter(percentile_rank__gte=query.min_percentile)
        
        if query.max_percentile is not None:
            queryset = queryset.filter(percentile_rank__lte=query.max_percentile)
        
        # Apply ordering
        queryset = queryset.order_by(query.order_by)
        
        # Apply pagination
        queryset = queryset[query.offset:query.offset + query.limit]
        
        return [TeamAnalyticsDTO.from_model(snapshot) for snapshot in queryset]
    
    def save_leaderboard_entries(
        self,
        entries: List[LeaderboardEntryDTO]
    ) -> int:
        """
        Bulk save leaderboard entries.
        
        Args:
            entries: List of LeaderboardEntryDTO instances
        
        Returns:
            Number of entries saved
        """
        from apps.leaderboards.models import LeaderboardEntry
        from django.utils import timezone
        
        if not entries:
            return 0
        
        # Delete existing entries for the same leaderboard type/game/season
        # (to replace with fresh rankings)
        if entries:
            first_entry = entries[0]
            filters = {
                "leaderboard_type": first_entry.leaderboard_type,
            }
            if first_entry.game_slug:
                filters["game"] = first_entry.game_slug
            if first_entry.season_id:
                filters["season"] = first_entry.season_id
            
            LeaderboardEntry.objects.filter(**filters).delete()
        
        # Bulk create new entries
        now = timezone.now()
        leaderboard_objs = []
        for entry in entries:
            leaderboard_objs.append(LeaderboardEntry(
                leaderboard_type=entry.leaderboard_type,
                game=entry.game_slug,
                season=entry.season_id,
                reference_id=entry.reference_id,
                rank=entry.rank,
                points=entry.score,
                wins=entry.wins,
                losses=entry.losses,
                win_rate=entry.win_rate,
                payload_json=entry.payload,
                computed_at=now,
                is_active=True,
            ))
        
        LeaderboardEntry.objects.bulk_create(leaderboard_objs)
        return len(leaderboard_objs)
    
    def get_leaderboard(
        self,
        leaderboard_type: str,
        game_slug: Optional[str] = None,
        season_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LeaderboardEntryDTO]:
        """
        Get leaderboard entries with filtering.
        
        Args:
            leaderboard_type: Type of leaderboard (mmr, elo, tier, etc.)
            game_slug: Optional game filter
            season_id: Optional season filter
            limit: Maximum number of entries to return
        
        Returns:
            List of LeaderboardEntryDTO instances (ranked order)
        """
        from apps.leaderboards.models import LeaderboardEntry
        
        queryset = LeaderboardEntry.objects.filter(
            leaderboard_type=leaderboard_type,
            is_active=True
        )
        
        if game_slug:
            queryset = queryset.filter(game=game_slug)
        
        if season_id:
            queryset = queryset.filter(season=season_id)
        
        # Order by rank (ascending)
        queryset = queryset.order_by("rank")[:limit]
        
        return [LeaderboardEntryDTO.from_model(entry) for entry in queryset]
    
    def get_current_season(self) -> Optional[SeasonDTO]:
        """
        Get currently active season.
        
        Returns:
            SeasonDTO if active season exists, None otherwise
        """
        from apps.leaderboards.models import Season
        
        try:
            season = Season.objects.get(is_active=True)
            return SeasonDTO.from_model(season)
        except Season.DoesNotExist:
            return None
        except Season.MultipleObjectsReturned:
            # If multiple active seasons (data error), return most recent
            season = Season.objects.filter(is_active=True).order_by("-start_date").first()
            return SeasonDTO.from_model(season) if season else None
    
    def list_seasons(
        self,
        include_inactive: bool = False
    ) -> List[SeasonDTO]:
        """
        List all seasons, optionally including inactive ones.
        
        Args:
            include_inactive: Whether to include inactive seasons
        
        Returns:
            List of SeasonDTO instances (ordered by start_date descending)
        """
        from apps.leaderboards.models import Season
        
        queryset = Season.objects.all()
        
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        queryset = queryset.order_by("-start_date")
        
        return [SeasonDTO.from_model(season) for season in queryset]
    
    def get_user_snapshot_by_id(self, snapshot_id: int) -> Optional[UserAnalyticsDTO]:
        """
        Get user analytics snapshot by primary key.
        
        Args:
            snapshot_id: Primary key of UserAnalyticsSnapshot
        
        Returns:
            UserAnalyticsDTO if exists, None otherwise
        """
        from apps.leaderboards.models import UserAnalyticsSnapshot
        
        try:
            snapshot = UserAnalyticsSnapshot.objects.get(id=snapshot_id)
            return UserAnalyticsDTO.from_model(snapshot)
        except UserAnalyticsSnapshot.DoesNotExist:
            return None
    
    def get_team_snapshot_by_id(self, snapshot_id: int) -> Optional[TeamAnalyticsDTO]:
        """
        Get team analytics snapshot by primary key.
        
        Args:
            snapshot_id: Primary key of TeamAnalyticsSnapshot
        
        Returns:
            TeamAnalyticsDTO if exists, None otherwise
        """
        from apps.leaderboards.models import TeamAnalyticsSnapshot
        
        try:
            snapshot = TeamAnalyticsSnapshot.objects.get(id=snapshot_id)
            return TeamAnalyticsDTO.from_model(snapshot)
        except TeamAnalyticsSnapshot.DoesNotExist:
            return None
    
    def count_user_snapshots(self, game_slug: Optional[str] = None) -> int:
        """
        Count user analytics snapshots, optionally filtered by game.
        
        Args:
            game_slug: Optional game filter
        
        Returns:
            Count of snapshots
        """
        from apps.leaderboards.models import UserAnalyticsSnapshot
        
        queryset = UserAnalyticsSnapshot.objects.all()
        if game_slug:
            queryset = queryset.filter(game_slug=game_slug)
        
        return queryset.count()
    
    def count_team_snapshots(self, game_slug: Optional[str] = None) -> int:
        """
        Count team analytics snapshots, optionally filtered by game.
        
        Args:
            game_slug: Optional game filter
        
        Returns:
            Count of snapshots
        """
        from apps.leaderboards.models import TeamAnalyticsSnapshot
        
        queryset = TeamAnalyticsSnapshot.objects.all()
        if game_slug:
            queryset = queryset.filter(game_slug=game_slug)
        
        return queryset.count()
