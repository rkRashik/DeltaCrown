"""
Phase 8, Epic 8.4: Match History Service

Business logic for match history tracking and retrieval.
NO ORM IMPORTS - uses MatchHistoryAdapter only.

Reference: ROADMAP_AND_EPICS_PART_4.md, Epic 8.4
Architecture: Service layer with NO ORM imports
"""

from typing import List, Optional, Tuple
from datetime import datetime
import logging

from apps.tournament_ops.adapters.match_history_adapter import MatchHistoryAdapter, DjangoMatchHistoryAdapter
from apps.tournament_ops.dtos import (
    UserMatchHistoryDTO,
    TeamMatchHistoryDTO,
    MatchHistoryFilterDTO,
)
from apps.tournament_ops.exceptions import ValidationError

logger = logging.getLogger(__name__)


class MatchHistoryService:
    """
    Business logic for match history.
    
    Responsibilities:
    - Record match history entries from match completion events
    - Provide history retrieval with filtering and pagination
    - Validate history payloads
    - Count total entries for pagination metadata
    
    Architecture Compliance:
    - NO ORM imports (uses adapter only)
    - All data exchange via DTOs
    - Returns DTOs only, never ORM models
    """
    
    def __init__(self, adapter: Optional[MatchHistoryAdapter] = None):
        """
        Initialize service with optional adapter injection.
        
        Args:
            adapter: MatchHistoryAdapter instance (or None to create default)
        """
        self._adapter = adapter or DjangoMatchHistoryAdapter()
    
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
        kills: int = 0,
        deaths: int = 0,
        assists: int = 0,
        had_dispute: bool = False,
        is_forfeit: bool = False,
        completed_at: Optional[datetime] = None,
    ) -> UserMatchHistoryDTO:
        """
        Record a user match history entry.
        
        Called by event handlers after match completion/finalization.
        Idempotent: will update existing entry if called multiple times.
        
        Args:
            user_id: User participating in match
            match_id: Match ID reference
            tournament_id: Tournament ID reference
            game_slug: Game identifier
            is_winner: Whether user won
            is_draw: Whether match was a draw
            opponent_user_id: Opponent user ID (for 1v1)
            opponent_name: Opponent display name
            score_summary: Score summary string
            kills/deaths/assists: Match stats
            had_dispute: Whether match had dispute
            is_forfeit: Whether match ended in forfeit
            completed_at: Match completion timestamp (defaults to now)
            
        Returns:
            UserMatchHistoryDTO of created/updated record
            
        Raises:
            ValidationError: If required fields invalid
        """
        # Validate required fields
        if user_id is None or user_id <= 0:
            raise ValidationError("user_id must be a positive integer")
        
        if match_id is None or match_id <= 0:
            raise ValidationError("match_id must be a positive integer")
        
        if tournament_id is None or tournament_id <= 0:
            raise ValidationError("tournament_id must be a positive integer")
        
        if not game_slug or not game_slug.strip():
            raise ValidationError("game_slug is required")
        
        if kills < 0 or deaths < 0 or assists < 0:
            raise ValidationError("kills, deaths, and assists must be non-negative")
        
        # Default completed_at to now if not provided
        if not completed_at:
            from django.utils import timezone
            completed_at = timezone.now()
        
        # Default opponent_name if empty
        if not opponent_name or not opponent_name.strip():
            opponent_name = "Unknown"
        
        logger.info(
            f"Recording user match history: user={user_id}, match={match_id}, "
            f"game={game_slug}, winner={is_winner}"
        )
        
        return self._adapter.record_user_match_history(
            user_id=user_id,
            match_id=match_id,
            tournament_id=tournament_id,
            game_slug=game_slug.strip(),
            is_winner=is_winner,
            is_draw=is_draw,
            opponent_user_id=opponent_user_id,
            opponent_name=opponent_name.strip(),
            score_summary=score_summary.strip() if score_summary else "",
            kills=kills,
            deaths=deaths,
            assists=assists,
            had_dispute=had_dispute,
            is_forfeit=is_forfeit,
            completed_at=completed_at,
        )
    
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
        elo_before: Optional[int] = None,
        elo_after: Optional[int] = None,
        elo_change: int = 0,
        had_dispute: bool = False,
        is_forfeit: bool = False,
        completed_at: Optional[datetime] = None,
    ) -> TeamMatchHistoryDTO:
        """
        Record a team match history entry.
        
        Called by event handlers after team match completion/finalization.
        Idempotent: will update existing entry if called multiple times.
        
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
            completed_at: Match completion timestamp (defaults to now)
            
        Returns:
            TeamMatchHistoryDTO of created/updated record
            
        Raises:
            ValidationError: If required fields invalid
        """
        # Validate required fields
        if team_id is None or team_id <= 0:
            raise ValidationError("team_id must be a positive integer")
        
        if match_id is None or match_id <= 0:
            raise ValidationError("match_id must be a positive integer")
        
        if tournament_id is None or tournament_id <= 0:
            raise ValidationError("tournament_id must be a positive integer")
        
        if not game_slug or not game_slug.strip():
            raise ValidationError("game_slug is required")
        
        # Validate ELO values if provided
        if elo_before is not None and (elo_before < 400 or elo_before > 3000):
            raise ValidationError("elo_before must be between 400 and 3000")
        
        if elo_after is not None and (elo_after < 400 or elo_after > 3000):
            raise ValidationError("elo_after must be between 400 and 3000")
        
        # Default completed_at
        if not completed_at:
            from django.utils import timezone
            completed_at = timezone.now()
        
        # Default opponent_team_name
        if not opponent_team_name or not opponent_team_name.strip():
            opponent_team_name = "Unknown"
        
        logger.info(
            f"Recording team match history: team={team_id}, match={match_id}, "
            f"game={game_slug}, winner={is_winner}, elo_change={elo_change}"
        )
        
        return self._adapter.record_team_match_history(
            team_id=team_id,
            match_id=match_id,
            tournament_id=tournament_id,
            game_slug=game_slug.strip(),
            is_winner=is_winner,
            is_draw=is_draw,
            opponent_team_id=opponent_team_id,
            opponent_team_name=opponent_team_name.strip(),
            score_summary=score_summary.strip() if score_summary else "",
            elo_before=elo_before,
            elo_after=elo_after,
            elo_change=elo_change,
            had_dispute=had_dispute,
            is_forfeit=is_forfeit,
            completed_at=completed_at,
        )
    
    def get_user_match_history(
        self,
        user_id: int,
        game_slug: Optional[str] = None,
        tournament_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        only_wins: bool = False,
        only_losses: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[UserMatchHistoryDTO], int]:
        """
        Get user match history with filters and pagination.
        
        Args:
            user_id: User ID (required)
            game_slug: Filter by game (optional)
            tournament_id: Filter by tournament (optional)
            from_date: Filter by date range start (optional)
            to_date: Filter by date range end (optional)
            only_wins: Show only wins (optional)
            only_losses: Show only losses (optional)
            limit: Results per page (1-100, default 20)
            offset: Offset for pagination (default 0)
            
        Returns:
            Tuple of (list of UserMatchHistoryDTO, total count)
            
        Raises:
            ValidationError: If user_id invalid or filters conflicting
        """
        # Build filter DTO with validation
        try:
            filter_dto = MatchHistoryFilterDTO.validate(
                user_id=user_id,
                game_slug=game_slug,
                tournament_id=tournament_id,
                from_date=from_date,
                to_date=to_date,
                only_wins=only_wins,
                only_losses=only_losses,
                limit=limit,
                offset=offset,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        
        logger.info(f"Fetching user match history: user={user_id}, filters={filter_dto.to_dict()}")
        
        # Get results and total count
        results = self._adapter.list_user_history(filter_dto)
        total_count = self._adapter.get_user_history_count(filter_dto)
        
        return results, total_count
    
    def get_team_match_history(
        self,
        team_id: int,
        game_slug: Optional[str] = None,
        tournament_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        only_wins: bool = False,
        only_losses: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[TeamMatchHistoryDTO], int]:
        """
        Get team match history with filters and pagination.
        
        Args:
            team_id: Team ID (required)
            game_slug: Filter by game (optional)
            tournament_id: Filter by tournament (optional)
            from_date: Filter by date range start (optional)
            to_date: Filter by date range end (optional)
            only_wins: Show only wins (optional)
            only_losses: Show only losses (optional)
            limit: Results per page (1-100, default 20)
            offset: Offset for pagination (default 0)
            
        Returns:
            Tuple of (list of TeamMatchHistoryDTO, total count)
            
        Raises:
            ValidationError: If team_id invalid or filters conflicting
        """
        # Build filter DTO with validation
        try:
            filter_dto = MatchHistoryFilterDTO.validate(
                team_id=team_id,
                game_slug=game_slug,
                tournament_id=tournament_id,
                from_date=from_date,
                to_date=to_date,
                only_wins=only_wins,
                only_losses=only_losses,
                limit=limit,
                offset=offset,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        
        logger.info(f"Fetching team match history: team={team_id}, filters={filter_dto.to_dict()}")
        
        # Get results and total count
        results = self._adapter.list_team_history(filter_dto)
        total_count = self._adapter.get_team_history_count(filter_dto)
        
        return results, total_count
