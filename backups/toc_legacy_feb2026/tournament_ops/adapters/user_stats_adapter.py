"""
User Stats Adapter

Phase 8, Epic 8.2: User Stats Service
Data access layer for user statistics and performance metrics.
Uses method-level ORM imports only.
"""

from typing import List, Optional, Protocol
from datetime import datetime
from decimal import Decimal
from apps.tournament_ops.dtos import (
    UserStatsDTO,
    MatchStatsUpdateDTO,
)


class UserStatsAdapterProtocol(Protocol):
    """Protocol defining user stats adapter interface."""
    
    def get_user_stats(
        self, 
        user_id: int, 
        game_slug: Optional[str] = None
    ) -> Optional[UserStatsDTO]:
        """Get user stats for specific game or aggregate across all games."""
        ...
    
    def get_all_user_stats(self, user_id: int) -> List[UserStatsDTO]:
        """Get all stats for a user across all games."""
        ...
    
    def increment_stats_for_match(
        self, 
        match_update: MatchStatsUpdateDTO
    ) -> UserStatsDTO:
        """Increment user stats based on match completion."""
        ...
    
    def get_stats_by_game(self, game_slug: str, limit: int = 100) -> List[UserStatsDTO]:
        """Get top stats for a specific game (for leaderboards)."""
        ...


class UserStatsAdapter:
    """
    Concrete adapter for user stats data access.
    Uses method-level ORM imports to maintain architecture boundaries.
    """
    
    def get_user_stats(
        self, 
        user_id: int, 
        game_slug: Optional[str] = None
    ) -> Optional[UserStatsDTO]:
        """
        Get user stats for specific game.
        
        Args:
            user_id: User ID
            game_slug: Game identifier (e.g., 'valorant', 'csgo')
            
        Returns:
            UserStatsDTO instance or None if not found
        """
        # Method-level ORM import
        from apps.leaderboards.models import UserStats
        
        if not game_slug:
            # If no game specified, return None (must specify game)
            return None
        
        try:
            stats = UserStats.objects.get(
                user_id=user_id,
                game_slug=game_slug
            )
            return UserStatsDTO.from_model(stats)
        except UserStats.DoesNotExist:
            return None
    
    def get_all_user_stats(self, user_id: int) -> List[UserStatsDTO]:
        """
        Get all stats for a user across all games.
        
        Args:
            user_id: User ID
            
        Returns:
            List of UserStatsDTO instances
        """
        # Method-level ORM import
        from apps.leaderboards.models import UserStats
        
        stats = UserStats.objects.filter(user_id=user_id).order_by('-matches_played')
        return [UserStatsDTO.from_model(s) for s in stats]
    
    def increment_stats_for_match(
        self, 
        match_update: MatchStatsUpdateDTO
    ) -> UserStatsDTO:
        """
        Increment user stats based on match completion.
        
        Creates UserStats record if it doesn't exist.
        Updates matches played/won/lost, K/D stats, last_match_at.
        
        Args:
            match_update: MatchStatsUpdateDTO with match outcome data
            
        Returns:
            Updated UserStatsDTO instance
        """
        # Method-level ORM imports
        from apps.leaderboards.models import UserStats
        from django.db.models import F
        from django.utils import timezone
        
        # Validate DTO
        match_update.validate()
        
        # Get or create stats record
        stats, created = UserStats.objects.get_or_create(
            user_id=match_update.user_id,
            game_slug=match_update.game_slug,
            defaults={
                'matches_played': 0,
                'matches_won': 0,
                'matches_lost': 0,
                'matches_drawn': 0,
                'tournaments_played': 0,
                'tournaments_won': 0,
                'win_rate': Decimal('0.0'),
                'total_kills': 0,
                'total_deaths': 0,
                'kd_ratio': Decimal('0.0'),
            }
        )
        
        # Increment match counts
        stats.matches_played = F('matches_played') + 1
        
        if match_update.is_winner:
            stats.matches_won = F('matches_won') + 1
        elif match_update.is_draw:
            stats.matches_drawn = F('matches_drawn') + 1
        else:
            stats.matches_lost = F('matches_lost') + 1
        
        # Increment K/D stats
        if match_update.kills > 0:
            stats.total_kills = F('total_kills') + match_update.kills
        if match_update.deaths > 0:
            stats.total_deaths = F('total_deaths') + match_update.deaths
        
        # Update timestamp
        stats.last_match_at = match_update.match_completed_at or timezone.now()
        
        # Save with F() expressions
        stats.save(update_fields=[
            'matches_played',
            'matches_won',
            'matches_lost',
            'matches_drawn',
            'total_kills',
            'total_deaths',
            'last_match_at',
        ])
        
        # Refresh to get actual values (F() expressions resolved)
        stats.refresh_from_db()
        
        # Recalculate derived fields
        stats.calculate_win_rate()
        stats.calculate_kd_ratio()
        stats.save(update_fields=['win_rate', 'kd_ratio'])
        
        # Return DTO
        return UserStatsDTO.from_model(stats)
    
    def get_stats_by_game(self, game_slug: str, limit: int = 100) -> List[UserStatsDTO]:
        """
        Get top stats for a specific game (ordered by win rate, then matches played).
        
        Args:
            game_slug: Game identifier
            limit: Maximum number of results
            
        Returns:
            List of UserStatsDTO instances
        """
        # Method-level ORM import
        from apps.leaderboards.models import UserStats
        
        stats = UserStats.objects.filter(
            game_slug=game_slug,
            matches_played__gt=0  # Only users with matches played
        ).order_by('-win_rate', '-matches_played')[:limit]
        
        return [UserStatsDTO.from_model(s) for s in stats]
    
    def increment_tournament_participation(
        self,
        user_id: int,
        game_slug: str,
        is_winner: bool = False
    ) -> UserStatsDTO:
        """
        Increment tournament participation counters.
        
        Should be called when user completes a tournament.
        
        Args:
            user_id: User ID
            game_slug: Game identifier
            is_winner: Whether user won the tournament
            
        Returns:
            Updated UserStatsDTO instance
        """
        # Method-level ORM imports
        from apps.leaderboards.models import UserStats
        from django.db.models import F
        
        # Get or create stats record
        stats, created = UserStats.objects.get_or_create(
            user_id=user_id,
            game_slug=game_slug,
            defaults={
                'matches_played': 0,
                'matches_won': 0,
                'matches_lost': 0,
                'matches_drawn': 0,
                'tournaments_played': 0,
                'tournaments_won': 0,
                'win_rate': Decimal('0.0'),
                'total_kills': 0,
                'total_deaths': 0,
                'kd_ratio': Decimal('0.0'),
            }
        )
        
        # Increment tournament counts
        stats.tournaments_played = F('tournaments_played') + 1
        if is_winner:
            stats.tournaments_won = F('tournaments_won') + 1
        
        stats.save(update_fields=['tournaments_played', 'tournaments_won'])
        stats.refresh_from_db()
        
        return UserStatsDTO.from_model(stats)
