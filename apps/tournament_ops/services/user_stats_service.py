"""
User Stats Service

Phase 8, Epic 8.2: User Stats Service
Business logic for user statistics tracking and retrieval.
NO ORM IMPORTS - uses UserStatsAdapter only.
"""

from typing import List, Optional
import logging

from apps.tournament_ops.adapters.user_stats_adapter import UserStatsAdapter
from apps.tournament_ops.dtos import (
    UserStatsDTO,
    MatchStatsUpdateDTO,
)
from apps.tournament_ops.exceptions import ValidationError

logger = logging.getLogger(__name__)


class UserStatsService:
    """
    Business logic for user statistics.
    
    Responsibilities:
    - Coordinate stats updates from match completion events
    - Provide stats retrieval for API/UI consumption
    - Validate stats update payloads
    - Handle edge cases (voided matches, missing data, etc.)
    
    Architecture Compliance:
    - NO ORM imports (uses adapter only)
    - All data exchange via DTOs
    - Returns DTOs only, never ORM models
    """
    
    def __init__(self, adapter: Optional[UserStatsAdapter] = None):
        """
        Initialize service with optional adapter injection.
        
        Args:
            adapter: UserStatsAdapter instance (or None to create default)
        """
        self._adapter = adapter or UserStatsAdapter()
    
    def get_user_stats(
        self, 
        user_id: int, 
        game_slug: str
    ) -> Optional[UserStatsDTO]:
        """
        Get user stats for a specific game.
        
        Args:
            user_id: User ID
            game_slug: Game identifier (e.g., 'valorant', 'csgo')
            
        Returns:
            UserStatsDTO or None if user has no stats for that game
            
        Raises:
            ValidationError: If inputs are invalid
        """
        if user_id is None or user_id <= 0:
            raise ValidationError("user_id must be a positive integer")
        if not game_slug:
            raise ValidationError("game_slug is required")
        
        logger.info(f"Fetching stats for user {user_id}, game {game_slug}")
        return self._adapter.get_user_stats(user_id, game_slug)
    
    def get_all_user_stats(self, user_id: int) -> List[UserStatsDTO]:
        """
        Get all stats for a user across all games.
        
        Args:
            user_id: User ID
            
        Returns:
            List of UserStatsDTO instances (one per game)
            
        Raises:
            ValidationError: If user_id is invalid
        """
        if user_id is None or user_id <= 0:
            raise ValidationError("user_id must be a positive integer")
        
        logger.info(f"Fetching all stats for user {user_id}")
        return self._adapter.get_all_user_stats(user_id)
    
    def update_stats_for_match(
        self,
        match_update: MatchStatsUpdateDTO
    ) -> UserStatsDTO:
        """
        Update user stats based on match completion.
        
        Called by MatchCompletedEvent handler to increment stats.
        
        Args:
            match_update: MatchStatsUpdateDTO with match outcome data
            
        Returns:
            Updated UserStatsDTO
            
        Raises:
            ValidationError: If match_update is invalid
        """
        # Validate DTO
        try:
            match_update.validate()
        except ValueError as e:
            raise ValidationError(f"Invalid match update: {str(e)}")
        
        logger.info(
            f"Updating stats for user {match_update.user_id}, "
            f"match {match_update.match_id}, game {match_update.game_slug}"
        )
        
        # Delegate to adapter
        updated_stats = self._adapter.increment_stats_for_match(match_update)
        
        logger.info(
            f"Stats updated: {updated_stats.matches_won}/{updated_stats.matches_played} wins, "
            f"{float(updated_stats.win_rate):.1f}% win rate"
        )
        
        return updated_stats
    
    def update_stats_for_match_batch(
        self,
        match_updates: List[MatchStatsUpdateDTO]
    ) -> List[UserStatsDTO]:
        """
        Update stats for multiple users from a single match.
        
        Typically called with 2 updates (one per player in 1v1 match)
        or more for team matches.
        
        Args:
            match_updates: List of MatchStatsUpdateDTO instances
            
        Returns:
            List of updated UserStatsDTO instances
            
        Raises:
            ValidationError: If any update is invalid
        """
        if not match_updates:
            raise ValidationError("match_updates cannot be empty")
        
        results = []
        for update in match_updates:
            try:
                updated_stats = self.update_stats_for_match(update)
                results.append(updated_stats)
            except Exception as e:
                logger.error(
                    f"Failed to update stats for user {update.user_id}: {str(e)}"
                )
                # Continue processing other updates even if one fails
                continue
        
        return results
    
    def get_top_stats_for_game(
        self,
        game_slug: str,
        limit: int = 100
    ) -> List[UserStatsDTO]:
        """
        Get top-performing users for a specific game.
        
        Ordered by win rate, then matches played.
        Used for leaderboard generation.
        
        Args:
            game_slug: Game identifier
            limit: Maximum number of results (default 100)
            
        Returns:
            List of UserStatsDTO instances
            
        Raises:
            ValidationError: If inputs are invalid
        """
        if not game_slug:
            raise ValidationError("game_slug is required")
        if limit is None or limit <= 0:
            raise ValidationError("limit must be a positive integer")
        if limit > 1000:
            raise ValidationError("limit cannot exceed 1000")
        
        logger.info(f"Fetching top {limit} stats for game {game_slug}")
        return self._adapter.get_stats_by_game(game_slug, limit)
    
    def record_tournament_completion(
        self,
        user_id: int,
        game_slug: str,
        is_winner: bool = False
    ) -> UserStatsDTO:
        """
        Record tournament participation/win for a user.
        
        Should be called when user completes a tournament (regardless of placement).
        
        Args:
            user_id: User ID
            game_slug: Game identifier
            is_winner: Whether user won the tournament (1st place)
            
        Returns:
            Updated UserStatsDTO
            
        Raises:
            ValidationError: If inputs are invalid
        """
        if user_id is None or user_id <= 0:
            raise ValidationError("user_id must be a positive integer")
        if not game_slug:
            raise ValidationError("game_slug is required")
        
        logger.info(
            f"Recording tournament {'win' if is_winner else 'participation'} "
            f"for user {user_id}, game {game_slug}"
        )
        
        return self._adapter.increment_tournament_participation(
            user_id=user_id,
            game_slug=game_slug,
            is_winner=is_winner
        )
    
    def get_user_summary(
        self,
        user_id: int,
        game_slug: Optional[str] = None
    ) -> dict:
        """
        Get summary statistics for a user.
        
        Returns aggregated view of user's performance:
        - Total matches across all games (if game_slug not provided)
        - Win rate, K/D ratio
        - Most active game
        - Recent activity
        
        Args:
            user_id: User ID
            game_slug: Optional game filter
            
        Returns:
            Dictionary with summary statistics
            
        Raises:
            ValidationError: If user_id is invalid
        """
        if user_id is None or user_id <= 0:
            raise ValidationError("user_id must be a positive integer")
        
        if game_slug:
            # Single-game summary
            stats = self.get_user_stats(user_id, game_slug)
            if not stats:
                return {
                    'user_id': user_id,
                    'game_slug': game_slug,
                    'has_stats': False,
                }
            
            return {
                'user_id': user_id,
                'game_slug': game_slug,
                'has_stats': True,
                'matches_played': stats.matches_played,
                'matches_won': stats.matches_won,
                'win_rate': float(stats.win_rate),
                'kd_ratio': float(stats.kd_ratio),
                'last_match_at': stats.last_match_at,
            }
        else:
            # Multi-game aggregate summary
            all_stats = self.get_all_user_stats(user_id)
            
            if not all_stats:
                return {
                    'user_id': user_id,
                    'has_stats': False,
                    'total_games': 0,
                }
            
            # Aggregate across all games
            total_matches = sum(s.matches_played for s in all_stats)
            total_wins = sum(s.matches_won for s in all_stats)
            total_kills = sum(s.total_kills for s in all_stats)
            total_deaths = sum(s.total_deaths for s in all_stats)
            
            overall_win_rate = (total_wins / total_matches * 100) if total_matches > 0 else 0.0
            overall_kd = (total_kills / total_deaths) if total_deaths > 0 else float(total_kills)
            
            # Find most active game
            most_active_game = max(all_stats, key=lambda s: s.matches_played)
            
            # Find most recent activity
            recent_activity = max(
                (s for s in all_stats if s.last_match_at),
                key=lambda s: s.last_match_at,
                default=None
            )
            
            return {
                'user_id': user_id,
                'has_stats': True,
                'total_games': len(all_stats),
                'total_matches': total_matches,
                'total_wins': total_wins,
                'overall_win_rate': overall_win_rate,
                'overall_kd_ratio': overall_kd,
                'most_active_game': most_active_game.game_slug,
                'last_match_at': recent_activity.last_match_at if recent_activity else None,
                'games': [
                    {
                        'game_slug': s.game_slug,
                        'matches_played': s.matches_played,
                        'win_rate': float(s.win_rate),
                    }
                    for s in all_stats
                ],
            }
