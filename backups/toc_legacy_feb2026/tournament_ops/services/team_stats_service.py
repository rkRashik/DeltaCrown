"""
Team Stats Service - Business logic for team statistics and ELO ratings.

Phase 8, Epic 8.3: Team Stats & Ranking System
Implements ELO rating calculations and team stats management.
"""

from typing import List, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class TeamStatsService:
    """
    Service for team statistics and ELO rating management.
    
    Implements business logic for:
    - Match stats tracking (wins/losses/draws)
    - ELO rating calculations (K-factor = 32)
    - Tournament participation tracking
    - Team performance summaries
    
    No ORM imports - uses adapters for data access.
    
    ELO Algorithm:
    - Expected Score: E_A = 1 / (1 + 10^((Rating_B - Rating_A) / 400))
    - Rating Change: ΔRating = K * (Actual - Expected)
    - K-factor: 32 (standard for team competition)
    
    Reference: Phase 8, Epic 8.3 - Team Stats Service
    """
    
    # ELO constants
    K_FACTOR = 32  # Standard K-factor for team ELO
    ELO_DIVISOR = 400  # Standard divisor for ELO expected score
    DEFAULT_ELO = 1200  # Starting ELO for new teams
    
    def __init__(self, team_stats_adapter, team_ranking_adapter):
        """
        Initialize service with adapter dependencies.
        
        Args:
            team_stats_adapter: TeamStatsAdapterProtocol instance
            team_ranking_adapter: TeamRankingAdapterProtocol instance
        """
        self.team_stats_adapter = team_stats_adapter
        self.team_ranking_adapter = team_ranking_adapter
    
    def calculate_elo_change(
        self,
        team_rating: int,
        opponent_rating: int,
        is_winner: bool,
        is_draw: bool,
    ) -> int:
        """
        Calculate ELO rating change for a match.
        
        Uses standard ELO formula:
        - Expected: E_A = 1 / (1 + 10^((R_B - R_A) / 400))
        - Change: ΔR = K * (Actual - Expected)
        
        Args:
            team_rating: Team's current ELO rating
            opponent_rating: Opponent's current ELO rating
            is_winner: True if team won
            is_draw: True if match was a draw
            
        Returns:
            ELO rating change (positive or negative integer)
        """
        # Calculate expected score (0.0 to 1.0)
        expected_score = 1.0 / (
            1.0 + 10.0 ** ((opponent_rating - team_rating) / self.ELO_DIVISOR)
        )
        
        # Determine actual score
        if is_winner:
            actual_score = 1.0
        elif is_draw:
            actual_score = 0.5
        else:
            actual_score = 0.0
        
        # Calculate rating change
        elo_change = round(self.K_FACTOR * (actual_score - expected_score))
        
        logger.debug(
            f"ELO calculation: team={team_rating}, opponent={opponent_rating}, "
            f"expected={expected_score:.3f}, actual={actual_score}, change={elo_change}"
        )
        
        return int(elo_change)
    
    def update_stats_for_match(self, update_dto):
        """
        Update team stats and ELO rating after match completion.
        
        Atomically updates:
        1. Match stats (played/won/lost/drawn counters)
        2. ELO rating (calculated vs opponent)
        
        Args:
            update_dto: TeamMatchStatsUpdateDTO with match outcome data
            
        Returns:
            dict with updated stats and ranking DTOs
        """
        from apps.tournament_ops.dtos import TeamMatchStatsUpdateDTO
        
        # Validate input
        if not isinstance(update_dto, TeamMatchStatsUpdateDTO):
            raise ValueError("update_dto must be TeamMatchStatsUpdateDTO")
        
        update_dto.validate()
        
        # Update match stats
        stats_dto = self.team_stats_adapter.increment_stats_for_match(
            team_id=update_dto.team_id,
            game_slug=update_dto.game_slug,
            is_winner=update_dto.is_winner,
            is_draw=update_dto.is_draw,
        )
        
        # Get or create team ranking
        ranking_dto = self.team_ranking_adapter.get_team_ranking(
            team_id=update_dto.team_id,
            game_slug=update_dto.game_slug,
        )
        
        if not ranking_dto:
            # Create initial ranking with default ELO
            ranking_dto = self.team_ranking_adapter.create_or_update_ranking(
                team_id=update_dto.team_id,
                game_slug=update_dto.game_slug,
                elo_rating=self.DEFAULT_ELO,
            )
        
        # Calculate ELO change
        elo_change = self.calculate_elo_change(
            team_rating=ranking_dto.elo_rating,
            opponent_rating=update_dto.opponent_elo,
            is_winner=update_dto.is_winner,
            is_draw=update_dto.is_draw,
        )
        
        # Update ELO rating
        updated_ranking_dto = self.team_ranking_adapter.update_elo_rating(
            team_id=update_dto.team_id,
            game_slug=update_dto.game_slug,
            elo_change=elo_change,
            is_winner=update_dto.is_winner,
            is_draw=update_dto.is_draw,
        )
        
        logger.info(
            f"Updated team {update_dto.team_id} stats for match {update_dto.match_id}: "
            f"ELO {ranking_dto.elo_rating} → {updated_ranking_dto.elo_rating} "
            f"({elo_change:+d})"
        )
        
        return {
            "stats": stats_dto,
            "ranking": updated_ranking_dto,
            "elo_change": elo_change,
        }
    
    def update_stats_for_match_batch(self, update_dtos: List) -> List[dict]:
        """
        Batch update stats for multiple teams (e.g., both match participants).
        
        Args:
            update_dtos: List of TeamMatchStatsUpdateDTO
            
        Returns:
            List of update result dicts
        """
        results = []
        for update_dto in update_dtos:
            try:
                result = self.update_stats_for_match(update_dto)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to update stats for team {update_dto.team_id}: {e}"
                )
                results.append({"error": str(e)})
        
        return results
    
    def get_team_stats(self, team_id: int, game_slug: str):
        """
        Get stats for a specific team + game.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            
        Returns:
            TeamStatsDTO or None
        """
        return self.team_stats_adapter.get_team_stats(team_id, game_slug)
    
    def get_all_team_stats(self, team_id: int) -> List:
        """
        Get stats for a team across all games.
        
        Args:
            team_id: Team primary key
            
        Returns:
            List[TeamStatsDTO]
        """
        return self.team_stats_adapter.get_all_team_stats(team_id)
    
    def get_team_ranking(self, team_id: int, game_slug: str):
        """
        Get ranking for a specific team + game.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            
        Returns:
            TeamRankingDTO or None
        """
        return self.team_ranking_adapter.get_team_ranking(team_id, game_slug)
    
    def get_top_teams_by_elo(self, game_slug: str, limit: int = 100) -> List:
        """
        Get top-ranked teams for a game by ELO rating.
        
        Args:
            game_slug: Game identifier
            limit: Maximum number of teams to return
            
        Returns:
            List[TeamRankingDTO] ordered by ELO DESC
        """
        return self.team_ranking_adapter.get_rankings_by_game(game_slug, limit)
    
    def get_team_summary(self, team_id: int, game_slug: Optional[str] = None):
        """
        Get comprehensive stats summary for a team.
        
        If game_slug provided: returns single-game summary
        If game_slug is None: returns aggregated multi-game summary
        
        Args:
            team_id: Team primary key
            game_slug: Optional game identifier (None = all games)
            
        Returns:
            TeamStatsSummaryDTO or List[TeamStatsSummaryDTO]
        """
        from apps.tournament_ops.dtos import TeamStatsSummaryDTO
        
        if game_slug:
            # Single-game summary
            stats_dto = self.team_stats_adapter.get_team_stats(team_id, game_slug)
            ranking_dto = self.team_ranking_adapter.get_team_ranking(team_id, game_slug)
            
            if not stats_dto:
                return None
            
            return TeamStatsSummaryDTO.from_team_stats_dto(stats_dto, ranking_dto)
        else:
            # Multi-game summary
            all_stats = self.team_stats_adapter.get_all_team_stats(team_id)
            
            summaries = []
            for stats_dto in all_stats:
                ranking_dto = self.team_ranking_adapter.get_team_ranking(
                    team_id, stats_dto.game_slug
                )
                summary = TeamStatsSummaryDTO.from_team_stats_dto(stats_dto, ranking_dto)
                summaries.append(summary)
            
            return summaries
    
    def record_tournament_completion(
        self,
        team_id: int,
        game_slug: str,
        is_winner: bool,
    ):
        """
        Record tournament completion for a team.
        
        Increments tournaments_played (and tournaments_won if winner).
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            is_winner: True if team won the tournament
            
        Returns:
            TeamStatsDTO with updated tournament counters
        """
        return self.team_stats_adapter.increment_tournament_participation(
            team_id=team_id,
            game_slug=game_slug,
            is_winner=is_winner,
        )
    
    def recalculate_all_ranks(self, game_slug: str) -> int:
        """
        Recalculate rank positions for all teams in a game.
        
        Should be called periodically or after significant rating changes.
        
        Args:
            game_slug: Game identifier
            
        Returns:
            Number of rankings updated
        """
        return self.team_ranking_adapter.recalculate_ranks_for_game(game_slug)
