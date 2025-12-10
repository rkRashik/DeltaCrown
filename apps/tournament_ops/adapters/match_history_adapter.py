"""
Phase 8, Epic 8.4: Match History Adapter

Data access layer for match history records with strict ORM isolation.
Provides CRUD operations for UserMatchHistory and TeamMatchHistory models.

Reference: ROADMAP_AND_EPICS_PART_4.md, Epic 8.4
Architecture: Method-level ORM imports only
"""

from typing import Protocol, List, Optional
from datetime import datetime

from apps.tournament_ops.dtos import (
    UserMatchHistoryDTO,
    TeamMatchHistoryDTO,
    MatchHistoryFilterDTO,
)


class MatchHistoryAdapter(Protocol):
    """
    Protocol for match history data access.
    
    Defines interface for recording and querying match history.
    Implementations must use method-level ORM imports only.
    """
    
    def record_user_match_history(
        self,
        user_id: int,
        match_id: int,
        tournament_id: int,
        game_slug: str,
        is_winner: bool,
        is_draw: bool,
        opponent_user_id: Optional[int],
        opponent_name: str,
        score_summary: str,
        kills: int,
        deaths: int,
        assists: int,
        had_dispute: bool,
        is_forfeit: bool,
        completed_at: datetime,
    ) -> UserMatchHistoryDTO:
        """
        Record a user match history entry.
        
        Args:
            user_id: User participating in match
            match_id: Match ID reference
            tournament_id: Tournament ID reference
            game_slug: Game identifier (valorant, csgo, etc.)
            is_winner: Whether user won the match
            is_draw: Whether match was a draw
            opponent_user_id: Opponent user ID (for 1v1)
            opponent_name: Opponent display name
            score_summary: Score summary string
            kills/deaths/assists: Match stats
            had_dispute: Whether match had dispute
            is_forfeit: Whether match ended in forfeit
            completed_at: Match completion timestamp
            
        Returns:
            UserMatchHistoryDTO of created record
            
        Raises:
            ValueError: If user_id, match_id, or tournament_id invalid
        """
        ...
    
    def record_team_match_history(
        self,
        team_id: int,
        match_id: int,
        tournament_id: int,
        game_slug: str,
        is_winner: bool,
        is_draw: bool,
        opponent_team_id: Optional[int],
        opponent_team_name: str,
        score_summary: str,
        elo_before: Optional[int],
        elo_after: Optional[int],
        elo_change: int,
        had_dispute: bool,
        is_forfeit: bool,
        completed_at: datetime,
    ) -> TeamMatchHistoryDTO:
        """
        Record a team match history entry.
        
        Args:
            team_id: Team participating in match
            match_id: Match ID reference
            tournament_id: Tournament ID reference
            game_slug: Game identifier
            is_winner: Whether team won
            is_draw: Whether match was a draw
            opponent_team_id: Opponent team ID
            opponent_team_name: Opponent team name
            score_summary: Score summary string
            elo_before/after/change: ELO rating tracking
            had_dispute: Whether match had dispute
            is_forfeit: Whether match ended in forfeit
            completed_at: Match completion timestamp
            
        Returns:
            TeamMatchHistoryDTO of created record
            
        Raises:
            ValueError: If team_id, match_id, or tournament_id invalid
        """
        ...
    
    def list_user_history(
        self,
        filter_dto: MatchHistoryFilterDTO,
    ) -> List[UserMatchHistoryDTO]:
        """
        List user match history with filters and pagination.
        
        Args:
            filter_dto: Query filters (user_id, game_slug, tournament_id, date range, pagination)
            
        Returns:
            List of UserMatchHistoryDTO, ordered by completed_at DESC
            
        Raises:
            ValueError: If filter_dto.user_id is None
        """
        ...
    
    def list_team_history(
        self,
        filter_dto: MatchHistoryFilterDTO,
    ) -> List[TeamMatchHistoryDTO]:
        """
        List team match history with filters and pagination.
        
        Args:
            filter_dto: Query filters (team_id, game_slug, tournament_id, date range, pagination)
            
        Returns:
            List of TeamMatchHistoryDTO, ordered by completed_at DESC
            
        Raises:
            ValueError: If filter_dto.team_id is None
        """
        ...
    
    def get_user_history_count(
        self,
        filter_dto: MatchHistoryFilterDTO,
    ) -> int:
        """
        Count total user match history entries matching filters.
        
        Args:
            filter_dto: Query filters (excludes pagination)
            
        Returns:
            Total count of matching entries
        """
        ...
    
    def get_team_history_count(
        self,
        filter_dto: MatchHistoryFilterDTO,
    ) -> int:
        """
        Count total team match history entries matching filters.
        
        Args:
            filter_dto: Query filters (excludes pagination)
            
        Returns:
            Total count of matching entries
        """
        ...


class DjangoMatchHistoryAdapter:
    """
    Django ORM implementation of MatchHistoryAdapter.
    
    Uses method-level imports to maintain strict ORM isolation.
    All queries ordered by completed_at DESC for timeline display.
    """
    
    def record_user_match_history(
        self,
        user_id: int,
        match_id: int,
        tournament_id: int,
        game_slug: str,
        is_winner: bool,
        is_draw: bool,
        opponent_user_id: Optional[int],
        opponent_name: str,
        score_summary: str,
        kills: int,
        deaths: int,
        assists: int,
        had_dispute: bool,
        is_forfeit: bool,
        completed_at: datetime,
    ) -> UserMatchHistoryDTO:
        """Record user match history entry (idempotent)."""
        from apps.leaderboards.models import UserMatchHistory
        
        # Idempotent: get_or_create by (user, match)
        history_entry, created = UserMatchHistory.objects.get_or_create(
            user_id=user_id,
            match_id=match_id,
            defaults={
                "tournament_id": tournament_id,
                "game_slug": game_slug,
                "is_winner": is_winner,
                "is_draw": is_draw,
                "opponent_user_id": opponent_user_id,
                "opponent_name": opponent_name,
                "score_summary": score_summary,
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "had_dispute": had_dispute,
                "is_forfeit": is_forfeit,
                "completed_at": completed_at,
            }
        )
        
        # Update if already exists (in case of result changes)
        if not created:
            history_entry.is_winner = is_winner
            history_entry.is_draw = is_draw
            history_entry.score_summary = score_summary
            history_entry.kills = kills
            history_entry.deaths = deaths
            history_entry.assists = assists
            history_entry.had_dispute = had_dispute
            history_entry.is_forfeit = is_forfeit
            history_entry.save(update_fields=[
                "is_winner", "is_draw", "score_summary",
                "kills", "deaths", "assists",
                "had_dispute", "is_forfeit",
            ])
        
        return UserMatchHistoryDTO.from_model(history_entry)
    
    def record_team_match_history(
        self,
        team_id: int,
        match_id: int,
        tournament_id: int,
        game_slug: str,
        is_winner: bool,
        is_draw: bool,
        opponent_team_id: Optional[int],
        opponent_team_name: str,
        score_summary: str,
        elo_before: Optional[int],
        elo_after: Optional[int],
        elo_change: int,
        had_dispute: bool,
        is_forfeit: bool,
        completed_at: datetime,
    ) -> TeamMatchHistoryDTO:
        """Record team match history entry (idempotent)."""
        from apps.leaderboards.models import TeamMatchHistory
        
        # Idempotent: get_or_create by (team, match)
        history_entry, created = TeamMatchHistory.objects.get_or_create(
            team_id=team_id,
            match_id=match_id,
            defaults={
                "tournament_id": tournament_id,
                "game_slug": game_slug,
                "is_winner": is_winner,
                "is_draw": is_draw,
                "opponent_team_id": opponent_team_id,
                "opponent_team_name": opponent_team_name,
                "score_summary": score_summary,
                "elo_before": elo_before,
                "elo_after": elo_after,
                "elo_change": elo_change,
                "had_dispute": had_dispute,
                "is_forfeit": is_forfeit,
                "completed_at": completed_at,
            }
        )
        
        # Update if already exists
        if not created:
            history_entry.is_winner = is_winner
            history_entry.is_draw = is_draw
            history_entry.score_summary = score_summary
            history_entry.elo_before = elo_before
            history_entry.elo_after = elo_after
            history_entry.elo_change = elo_change
            history_entry.had_dispute = had_dispute
            history_entry.is_forfeit = is_forfeit
            history_entry.save(update_fields=[
                "is_winner", "is_draw", "score_summary",
                "elo_before", "elo_after", "elo_change",
                "had_dispute", "is_forfeit",
            ])
        
        return TeamMatchHistoryDTO.from_model(history_entry)
    
    def list_user_history(
        self,
        filter_dto: MatchHistoryFilterDTO,
    ) -> List[UserMatchHistoryDTO]:
        """List user match history with filters and pagination."""
        from apps.leaderboards.models import UserMatchHistory
        
        if not filter_dto.user_id:
            raise ValueError("filter_dto.user_id is required for user history")
        
        # Base query
        queryset = UserMatchHistory.objects.filter(user_id=filter_dto.user_id)
        
        # Apply filters
        if filter_dto.tournament_id:
            queryset = queryset.filter(tournament_id=filter_dto.tournament_id)
        
        if filter_dto.game_slug:
            queryset = queryset.filter(game_slug=filter_dto.game_slug)
        
        if filter_dto.from_date:
            queryset = queryset.filter(completed_at__gte=filter_dto.from_date)
        
        if filter_dto.to_date:
            queryset = queryset.filter(completed_at__lte=filter_dto.to_date)
        
        # Result filters
        if filter_dto.only_wins:
            queryset = queryset.filter(is_winner=True)
        
        if filter_dto.only_losses:
            queryset = queryset.filter(is_winner=False, is_draw=False)
        
        # Order by completed_at DESC (most recent first)
        queryset = queryset.order_by("-completed_at")
        
        # Pagination
        queryset = queryset[filter_dto.offset:filter_dto.offset + filter_dto.limit]
        
        # Select related for efficient DTO conversion
        queryset = queryset.select_related("user", "tournament")
        
        return [UserMatchHistoryDTO.from_model(entry) for entry in queryset]
    
    def list_team_history(
        self,
        filter_dto: MatchHistoryFilterDTO,
    ) -> List[TeamMatchHistoryDTO]:
        """List team match history with filters and pagination."""
        from apps.leaderboards.models import TeamMatchHistory
        
        if not filter_dto.team_id:
            raise ValueError("filter_dto.team_id is required for team history")
        
        # Base query
        queryset = TeamMatchHistory.objects.filter(team_id=filter_dto.team_id)
        
        # Apply filters
        if filter_dto.tournament_id:
            queryset = queryset.filter(tournament_id=filter_dto.tournament_id)
        
        if filter_dto.game_slug:
            queryset = queryset.filter(game_slug=filter_dto.game_slug)
        
        if filter_dto.from_date:
            queryset = queryset.filter(completed_at__gte=filter_dto.from_date)
        
        if filter_dto.to_date:
            queryset = queryset.filter(completed_at__lte=filter_dto.to_date)
        
        # Result filters
        if filter_dto.only_wins:
            queryset = queryset.filter(is_winner=True)
        
        if filter_dto.only_losses:
            queryset = queryset.filter(is_winner=False, is_draw=False)
        
        # Order by completed_at DESC
        queryset = queryset.order_by("-completed_at")
        
        # Pagination
        queryset = queryset[filter_dto.offset:filter_dto.offset + filter_dto.limit]
        
        # Select related
        queryset = queryset.select_related("team", "tournament")
        
        return [TeamMatchHistoryDTO.from_model(entry) for entry in queryset]
    
    def get_user_history_count(
        self,
        filter_dto: MatchHistoryFilterDTO,
    ) -> int:
        """Count total user match history entries."""
        from apps.leaderboards.models import UserMatchHistory
        
        if not filter_dto.user_id:
            raise ValueError("filter_dto.user_id is required")
        
        # Base query
        queryset = UserMatchHistory.objects.filter(user_id=filter_dto.user_id)
        
        # Apply filters (same as list_user_history, but no pagination)
        if filter_dto.tournament_id:
            queryset = queryset.filter(tournament_id=filter_dto.tournament_id)
        
        if filter_dto.game_slug:
            queryset = queryset.filter(game_slug=filter_dto.game_slug)
        
        if filter_dto.from_date:
            queryset = queryset.filter(completed_at__gte=filter_dto.from_date)
        
        if filter_dto.to_date:
            queryset = queryset.filter(completed_at__lte=filter_dto.to_date)
        
        if filter_dto.only_wins:
            queryset = queryset.filter(is_winner=True)
        
        if filter_dto.only_losses:
            queryset = queryset.filter(is_winner=False, is_draw=False)
        
        return queryset.count()
    
    def get_team_history_count(
        self,
        filter_dto: MatchHistoryFilterDTO,
    ) -> int:
        """Count total team match history entries."""
        from apps.leaderboards.models import TeamMatchHistory
        
        if not filter_dto.team_id:
            raise ValueError("filter_dto.team_id is required")
        
        # Base query
        queryset = TeamMatchHistory.objects.filter(team_id=filter_dto.team_id)
        
        # Apply filters
        if filter_dto.tournament_id:
            queryset = queryset.filter(tournament_id=filter_dto.tournament_id)
        
        if filter_dto.game_slug:
            queryset = queryset.filter(game_slug=filter_dto.game_slug)
        
        if filter_dto.from_date:
            queryset = queryset.filter(completed_at__gte=filter_dto.from_date)
        
        if filter_dto.to_date:
            queryset = queryset.filter(completed_at__lte=filter_dto.to_date)
        
        if filter_dto.only_wins:
            queryset = queryset.filter(is_winner=True)
        
        if filter_dto.only_losses:
            queryset = queryset.filter(is_winner=False, is_draw=False)
        
        return queryset.count()
