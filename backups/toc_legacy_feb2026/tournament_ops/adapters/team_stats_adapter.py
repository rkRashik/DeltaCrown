"""
Team Stats Adapter - Data access layer for team statistics.

Phase 8, Epic 8.3: Team Stats & Ranking System
Provides data access for TeamStats model with ORM isolation.
"""

from typing import List, Optional, Protocol
from decimal import Decimal
from datetime import datetime


class TeamStatsAdapterProtocol(Protocol):
    """Protocol interface for dependency injection and testing."""
    
    def get_team_stats(self, team_id: int, game_slug: str):
        """Get stats for a specific team + game."""
        ...
    
    def get_all_team_stats(self, team_id: int) -> List:
        """Get stats for a team across all games."""
        ...
    
    def increment_stats_for_match(
        self,
        team_id: int,
        game_slug: str,
        is_winner: bool,
        is_draw: bool,
    ):
        """Atomically increment match stats after match completion."""
        ...
    
    def get_stats_by_game(self, game_slug: str, limit: int = 100) -> List:
        """Get all team stats for a game, ordered by win rate."""
        ...
    
    def increment_tournament_participation(
        self,
        team_id: int,
        game_slug: str,
        is_winner: bool,
    ):
        """Increment tournament participation count (and win if applicable)."""
        ...


class TeamStatsAdapter:
    """
    Data access adapter for TeamStats model.
    
    Provides ORM operations with method-level imports to maintain
    service layer isolation from Django models.
    
    Reference: Phase 8, Epic 8.3 - Service-Adapter Architecture
    """
    
    def get_team_stats(self, team_id: int, game_slug: str):
        """
        Get stats for a specific team + game.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            
        Returns:
            TeamStatsDTO or None if not found
        """
        from apps.leaderboards.models import TeamStats
        from apps.tournament_ops.dtos import TeamStatsDTO
        
        try:
            stats = TeamStats.objects.get(team_id=team_id, game_slug=game_slug)
            return TeamStatsDTO.from_model(stats)
        except TeamStats.DoesNotExist:
            return None
    
    def get_all_team_stats(self, team_id: int) -> List:
        """
        Get stats for a team across all games.
        
        Args:
            team_id: Team primary key
            
        Returns:
            List[TeamStatsDTO]
        """
        from apps.leaderboards.models import TeamStats
        from apps.tournament_ops.dtos import TeamStatsDTO
        
        stats = TeamStats.objects.filter(team_id=team_id).order_by("game_slug")
        return [TeamStatsDTO.from_model(s) for s in stats]
    
    def increment_stats_for_match(
        self,
        team_id: int,
        game_slug: str,
        is_winner: bool,
        is_draw: bool,
    ):
        """
        Atomically increment match stats after match completion.
        
        Uses F() expressions for atomic updates (race condition safe).
        Creates stats record if it doesn't exist yet.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            is_winner: True if team won the match
            is_draw: True if match was a draw
            
        Returns:
            TeamStatsDTO with updated values
        """
        from apps.leaderboards.models import TeamStats
        from apps.tournament_ops.dtos import TeamStatsDTO
        from django.db.models import F
        from django.utils import timezone
        
        # Create or get existing stats
        stats, created = TeamStats.objects.get_or_create(
            team_id=team_id,
            game_slug=game_slug,
            defaults={
                "matches_played": 0,
                "matches_won": 0,
                "matches_lost": 0,
                "matches_drawn": 0,
                "tournaments_played": 0,
                "tournaments_won": 0,
                "win_rate": Decimal("0.00"),
                "last_match_at": None,
            }
        )
        
        # Atomic update using F() expressions
        update_fields = {
            "matches_played": F("matches_played") + 1,
            "last_match_at": timezone.now(),
        }
        
        if is_winner:
            update_fields["matches_won"] = F("matches_won") + 1
        elif is_draw:
            update_fields["matches_drawn"] = F("matches_drawn") + 1
        else:
            update_fields["matches_lost"] = F("matches_lost") + 1
        
        TeamStats.objects.filter(
            team_id=team_id,
            game_slug=game_slug
        ).update(**update_fields)
        
        # Refresh to get updated values
        stats.refresh_from_db()
        
        # Recalculate win rate
        stats.calculate_win_rate()
        stats.save(update_fields=["win_rate"])
        
        return TeamStatsDTO.from_model(stats)
    
    def get_stats_by_game(self, game_slug: str, limit: int = 100) -> List:
        """
        Get all team stats for a game, ordered by win rate.
        
        Args:
            game_slug: Game identifier
            limit: Maximum number of results (default 100)
            
        Returns:
            List[TeamStatsDTO] ordered by win_rate DESC, matches_played DESC
        """
        from apps.leaderboards.models import TeamStats
        from apps.tournament_ops.dtos import TeamStatsDTO
        
        stats = (
            TeamStats.objects
            .filter(game_slug=game_slug)
            .order_by("-win_rate", "-matches_played")[:limit]
        )
        return [TeamStatsDTO.from_model(s) for s in stats]
    
    def increment_tournament_participation(
        self,
        team_id: int,
        game_slug: str,
        is_winner: bool,
    ):
        """
        Increment tournament participation count (and win if applicable).
        
        Called when tournament completes to update tournament_played/won counters.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            is_winner: True if team won the tournament
            
        Returns:
            TeamStatsDTO with updated values
        """
        from apps.leaderboards.models import TeamStats
        from apps.tournament_ops.dtos import TeamStatsDTO
        from django.db.models import F
        
        # Create or get existing stats
        stats, created = TeamStats.objects.get_or_create(
            team_id=team_id,
            game_slug=game_slug,
            defaults={
                "matches_played": 0,
                "matches_won": 0,
                "matches_lost": 0,
                "matches_drawn": 0,
                "tournaments_played": 0,
                "tournaments_won": 0,
                "win_rate": Decimal("0.00"),
                "last_match_at": None,
            }
        )
        
        # Atomic increment
        update_fields = {
            "tournaments_played": F("tournaments_played") + 1,
        }
        
        if is_winner:
            update_fields["tournaments_won"] = F("tournaments_won") + 1
        
        TeamStats.objects.filter(
            team_id=team_id,
            game_slug=game_slug
        ).update(**update_fields)
        
        # Refresh to get updated values
        stats.refresh_from_db()
        
        return TeamStatsDTO.from_model(stats)
    
    def delete_stats(self, team_id: int, game_slug: str) -> bool:
        """
        Delete stats for a specific team + game.
        
        Used for admin operations or data cleanup.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            
        Returns:
            True if deleted, False if not found
        """
        from apps.leaderboards.models import TeamStats
        
        deleted_count, _ = TeamStats.objects.filter(
            team_id=team_id,
            game_slug=game_slug
        ).delete()
        
        return deleted_count > 0
