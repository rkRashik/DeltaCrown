"""
Team Ranking Adapter - Data access layer for team ELO rankings.

Phase 8, Epic 8.3: Team Stats & Ranking System
Provides data access for TeamRanking model with ORM isolation.
"""

from typing import List, Optional, Protocol


class TeamRankingAdapterProtocol(Protocol):
    """Protocol interface for dependency injection and testing."""
    
    def get_team_ranking(self, team_id: int, game_slug: str):
        """Get ranking for a specific team + game."""
        ...
    
    def update_elo_rating(
        self,
        team_id: int,
        game_slug: str,
        elo_change: int,
        is_winner: bool,
        is_draw: bool,
    ):
        """Atomically update ELO rating after match."""
        ...
    
    def get_rankings_by_game(self, game_slug: str, limit: int = 100) -> List:
        """Get top rankings for a game, ordered by ELO."""
        ...
    
    def create_or_update_ranking(
        self,
        team_id: int,
        game_slug: str,
        elo_rating: int = 1200,
    ):
        """Create or update ranking record."""
        ...


class TeamRankingAdapter:
    """
    Data access adapter for TeamRanking model.
    
    Provides ORM operations with method-level imports to maintain
    service layer isolation from Django models.
    
    Reference: Phase 8, Epic 8.3 - ELO Rating System
    """
    
    def get_team_ranking(self, team_id: int, game_slug: str):
        """
        Get ranking for a specific team + game.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            
        Returns:
            TeamRankingDTO or None if not found
        """
        from apps.leaderboards.models import TeamRanking
        from apps.tournament_ops.dtos import TeamRankingDTO
        
        try:
            ranking = TeamRanking.objects.get(team_id=team_id, game_slug=game_slug)
            return TeamRankingDTO.from_model(ranking)
        except TeamRanking.DoesNotExist:
            return None
    
    def update_elo_rating(
        self,
        team_id: int,
        game_slug: str,
        elo_change: int,
        is_winner: bool,
        is_draw: bool,
    ):
        """
        Atomically update ELO rating after match.
        
        Uses F() expressions for atomic updates (race condition safe).
        Creates ranking record if it doesn't exist yet (default ELO 1200).
        Updates peak_elo if new rating exceeds current peak.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            elo_change: ELO rating change (+/-)
            is_winner: True if team won the match
            is_draw: True if match was a draw
            
        Returns:
            TeamRankingDTO with updated values
        """
        from apps.leaderboards.models import TeamRanking
        from apps.tournament_ops.dtos import TeamRankingDTO
        from django.db.models import F
        from django.utils import timezone
        
        # Create or get existing ranking
        ranking, created = TeamRanking.objects.get_or_create(
            team_id=team_id,
            game_slug=game_slug,
            defaults={
                "elo_rating": 1200,
                "peak_elo": 1200,
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "rank": None,
                "last_updated": timezone.now(),
            }
        )
        
        # Atomic update using F() expressions
        update_fields = {
            "elo_rating": F("elo_rating") + elo_change,
            "games_played": F("games_played") + 1,
            "last_updated": timezone.now(),
        }
        
        if is_winner:
            update_fields["wins"] = F("wins") + 1
        elif is_draw:
            update_fields["draws"] = F("draws") + 1
        else:
            update_fields["losses"] = F("losses") + 1
        
        TeamRanking.objects.filter(
            team_id=team_id,
            game_slug=game_slug
        ).update(**update_fields)
        
        # Refresh to get updated values
        ranking.refresh_from_db()
        
        # Update peak_elo if new rating is higher
        ranking.update_peak_elo()
        ranking.save(update_fields=["peak_elo"])
        
        return TeamRankingDTO.from_model(ranking)
    
    def get_rankings_by_game(self, game_slug: str, limit: int = 100) -> List:
        """
        Get top rankings for a game, ordered by ELO.
        
        Args:
            game_slug: Game identifier
            limit: Maximum number of results (default 100)
            
        Returns:
            List[TeamRankingDTO] ordered by elo_rating DESC
        """
        from apps.leaderboards.models import TeamRanking
        from apps.tournament_ops.dtos import TeamRankingDTO
        
        rankings = (
            TeamRanking.objects
            .filter(game_slug=game_slug)
            .order_by("-elo_rating", "-games_played")[:limit]
        )
        return [TeamRankingDTO.from_model(r) for r in rankings]
    
    def create_or_update_ranking(
        self,
        team_id: int,
        game_slug: str,
        elo_rating: int = 1200,
    ):
        """
        Create or update ranking record.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            elo_rating: Initial or updated ELO rating (default 1200)
            
        Returns:
            TeamRankingDTO
        """
        from apps.leaderboards.models import TeamRanking
        from apps.tournament_ops.dtos import TeamRankingDTO
        from django.utils import timezone
        
        ranking, created = TeamRanking.objects.update_or_create(
            team_id=team_id,
            game_slug=game_slug,
            defaults={
                "elo_rating": elo_rating,
                "peak_elo": elo_rating if created else None,  # Update peak only on create
                "last_updated": timezone.now(),
            }
        )
        
        if created:
            ranking.peak_elo = elo_rating
            ranking.save(update_fields=["peak_elo"])
        else:
            # Update peak if needed
            ranking.update_peak_elo()
            ranking.save(update_fields=["peak_elo"])
        
        return TeamRankingDTO.from_model(ranking)
    
    def recalculate_ranks_for_game(self, game_slug: str) -> int:
        """
        Recalculate rank positions for all teams in a game.
        
        Assigns ranks based on ELO rating (1 = highest).
        Should be called periodically or after significant rating changes.
        
        Args:
            game_slug: Game identifier
            
        Returns:
            Number of rankings updated
        """
        from apps.leaderboards.models import TeamRanking
        from django.db.models import Window, F
        from django.db.models.functions import RowNumber
        
        # Use window function to assign ranks based on ELO
        rankings = (
            TeamRanking.objects
            .filter(game_slug=game_slug)
            .annotate(
                new_rank=Window(
                    expression=RowNumber(),
                    order_by=F("elo_rating").desc()
                )
            )
        )
        
        updated_count = 0
        for ranking in rankings:
            if ranking.rank != ranking.new_rank:
                ranking.rank = ranking.new_rank
                ranking.save(update_fields=["rank"])
                updated_count += 1
        
        return updated_count
    
    def delete_ranking(self, team_id: int, game_slug: str) -> bool:
        """
        Delete ranking for a specific team + game.
        
        Used for admin operations or data cleanup.
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            
        Returns:
            True if deleted, False if not found
        """
        from apps.leaderboards.models import TeamRanking
        
        deleted_count, _ = TeamRanking.objects.filter(
            team_id=team_id,
            game_slug=game_slug
        ).delete()
        
        return deleted_count > 0
