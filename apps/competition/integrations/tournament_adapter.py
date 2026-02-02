"""
Tournament Adapter

Phase 3A-D: Integration layer for tournament data.
Provides safe access to tournament participation and placement data
for ranking calculations. Fails gracefully if tournaments app incomplete.
"""

from typing import Optional, Dict, List
from django.core.exceptions import ImproperlyConfigured
from django.apps import apps


class TournamentAdapter:
    """
    Adapter for safely accessing tournament data.
    
    Used by RankingComputeService to incorporate tournament
    participation and placements into ranking calculations.
    """
    
    @staticmethod
    def is_available() -> bool:
        """
        Check if tournaments app is available and usable.
        
        Returns:
            True if tournaments data can be safely queried
        """
        try:
            # Check if tournaments app is installed
            if not apps.is_installed('apps.tournaments'):
                return False
            
            # Try to import required models
            from apps.tournaments.models import TournamentRegistration, TournamentResult
            
            # Check if models are migrated (table exists)
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT to_regclass('public.tournaments_tournamentregistration')"
                )
                if cursor.fetchone()[0] is None:
                    return False
            
            return True
        except (ImportError, Exception):
            return False
    
    @staticmethod
    def get_team_tournament_wins(team, game_id: Optional[str] = None) -> int:
        """
        Get count of tournament wins for a team.
        
        Args:
            team: Team instance
            game_id: Optional game filter (e.g., 'LOL')
            
        Returns:
            Number of tournament wins (0 if tournaments unavailable)
        """
        if not TournamentAdapter.is_available():
            return 0
        
        try:
            from apps.tournaments.models import TournamentResult
            
            query = TournamentResult.objects.filter(
                team=team,
                placement=1  # 1st place = win
            )
            
            if game_id:
                query = query.filter(tournament__game_id=game_id)
            
            return query.count()
        except Exception:
            return 0
    
    @staticmethod
    def get_team_tournament_placements(
        team,
        game_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get tournament placement history for a team.
        
        Args:
            team: Team instance
            game_id: Optional game filter
            
        Returns:
            List of placement dicts with {tournament_id, placement, points}
            Empty list if tournaments unavailable
        """
        if not TournamentAdapter.is_available():
            return []
        
        try:
            from apps.tournaments.models import TournamentResult
            
            query = TournamentResult.objects.filter(team=team).select_related('tournament')
            
            if game_id:
                query = query.filter(tournament__game_id=game_id)
            
            placements = []
            for result in query:
                placements.append({
                    'tournament_id': result.tournament.id,
                    'tournament_name': result.tournament.name,
                    'placement': result.placement,
                    'points': result.points_awarded or 0,
                })
            
            return placements
        except Exception:
            return []
    
    @staticmethod
    def get_team_tournament_score(
        team,
        game_id: Optional[str] = None,
        win_weight: int = 500
    ) -> int:
        """
        Calculate tournament contribution to ranking score.
        
        Args:
            team: Team instance
            game_id: Optional game filter
            win_weight: Points per tournament win (from GameRankingConfig)
            
        Returns:
            Total tournament points (0 if tournaments unavailable)
        """
        if not TournamentAdapter.is_available():
            return 0
        
        try:
            # Simple implementation: count wins * weight
            # More complex scoring could weight by tournament tier
            wins = TournamentAdapter.get_team_tournament_wins(team, game_id)
            return wins * win_weight
        except Exception:
            return 0
