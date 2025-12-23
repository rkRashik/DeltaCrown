"""
Tournament & Team Stats Integration Service (UP-M4)

DESIGN PRINCIPLES:
1. SOURCE OF TRUTH:
   - Match model (matches_played, matches_won)
   - Tournament/Registration models (tournaments_played, tournaments_won, tournaments_top3)
   - Team/TeamMembership models (teams_joined, current_team)

2. DERIVED DATA:
   - UserProfileStats (read model, projection)
   - Computed from source tables ONLY
   - Never manually updated
   - Always recomputable

3. IDEMPOTENCY:
   - Safe to call recompute multiple times
   - Deterministic results (same input → same output)
   - No side effects

Usage:
    from apps.user_profile.services.tournament_stats import TournamentStatsService
    
    # Recompute all stats for a user
    stats = TournamentStatsService.recompute_user_stats(user_id)
    
    # Recompute specific stat categories
    TournamentStatsService.recompute_match_stats(user_id)
    TournamentStatsService.recompute_tournament_stats(user_id)
    TournamentStatsService.recompute_team_stats(user_id)
"""

from django.db import transaction
from django.db.models import Q, Count, Sum, F
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Dict, Optional
import logging

from apps.user_profile.models.stats import UserProfileStats
from apps.user_profile.models_main import UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class TournamentStatsService:
    """
    Service for computing tournament & team stats for UserProfile.
    
    All methods are IDEMPOTENT and DETERMINISTIC.
    Stats are derived from source tables (Match, Tournament, Registration, Team).
    """
    
    @classmethod
    @transaction.atomic
    def recompute_user_stats(cls, user_id: int, *, create_if_missing: bool = True) -> UserProfileStats:
        """
        Recompute ALL stats for a user from source tables.
        
        Args:
            user_id: User ID to recompute stats for
            create_if_missing: Create UserProfileStats if it doesn't exist
            
        Returns:
            UserProfileStats: Updated stats object
            
        Raises:
            UserProfile.DoesNotExist: If user has no profile
        """
        profile = UserProfile.objects.select_related('user').get(user_id=user_id)
        
        # Get or create stats
        if create_if_missing:
            stats, created = UserProfileStats.objects.get_or_create(user_profile=profile)
            if created:
                logger.info(f"Created UserProfileStats for user_id={user_id}")
        else:
            stats = UserProfileStats.objects.get(user_profile=profile)
        
        # Recompute each category
        match_stats = cls._compute_match_stats(user_id)
        tournament_stats = cls._compute_tournament_stats(user_id)
        team_stats = cls._compute_team_stats(user_id)
        
        # Update stats object
        stats.matches_played = match_stats['matches_played']
        stats.matches_won = match_stats['matches_won']
        stats.last_match_at = match_stats['last_match_at']
        
        stats.tournaments_played = tournament_stats['tournaments_played']
        stats.tournaments_won = tournament_stats['tournaments_won']
        stats.tournaments_top3 = tournament_stats['tournaments_top3']
        stats.first_tournament_at = tournament_stats['first_tournament_at']
        stats.last_tournament_at = tournament_stats['last_tournament_at']
        
        # Save with updated timestamp
        stats.save()
        
        logger.info(
            f"Recomputed stats for user_id={user_id}: "
            f"matches={stats.matches_played}/{stats.matches_won}, "
            f"tournaments={stats.tournaments_played}/{stats.tournaments_won}"
        )
        
        return stats
    
    @classmethod
    def _compute_match_stats(cls, user_id: int) -> Dict:
        """
        Compute match stats from Match model.
        
        Returns:
            dict: {
                'matches_played': int,
                'matches_won': int,
                'last_match_at': datetime | None
            }
        """
        from apps.tournaments.models.match import Match
        
        # Find all completed matches where user participated
        # Match.winner_id is user_id or registration.user_id
        # For now, we'll use Registration to find user's matches
        from apps.tournaments.models.registration import Registration
        
        # Get user's registrations
        user_registrations = Registration.objects.filter(
            user_id=user_id,
            status=Registration.CONFIRMED
        ).values_list('id', flat=True)
        
        if not user_registrations:
            return {
                'matches_played': 0,
                'matches_won': 0,
                'last_match_at': None
            }
        
        # Count matches played (any match where user's registration participated)
        # For solo tournaments: participant1_id or participant2_id = registration_id
        completed_matches = Match.objects.filter(
            Q(state=Match.COMPLETED) | Q(state=Match.FORFEIT),
            Q(participant1_id__in=user_registrations) | Q(participant2_id__in=user_registrations)
        )
        
        matches_played = completed_matches.count()
        
        # Count matches won (winner_id matches user's registration)
        matches_won = completed_matches.filter(
            winner_id__in=user_registrations
        ).count()
        
        # Get last match timestamp
        last_match = completed_matches.order_by('-completed_at').first()
        last_match_at = last_match.completed_at if last_match else None
        
        return {
            'matches_played': matches_played,
            'matches_won': matches_won,
            'last_match_at': last_match_at
        }
    
    @classmethod
    def _compute_tournament_stats(cls, user_id: int) -> Dict:
        """
        Compute tournament stats from Tournament and Registration models.
        
        Returns:
            dict: {
                'tournaments_played': int,
                'tournaments_won': int,
                'tournaments_top3': int,
                'first_tournament_at': datetime | None,
                'last_tournament_at': datetime | None
            }
        """
        from apps.tournaments.models.registration import Registration
        from apps.tournaments.models.result import TournamentResult
        
        # Get user's confirmed registrations
        registrations = Registration.objects.filter(
            user_id=user_id,
            status=Registration.CONFIRMED
        ).select_related('tournament')
        
        if not registrations.exists():
            return {
                'tournaments_played': 0,
                'tournaments_won': 0,
                'tournaments_top3': 0,
                'first_tournament_at': None,
                'last_tournament_at': None
            }
        
        tournaments_played = registrations.count()
        
        # Get tournament results for this user
        registration_ids = list(registrations.values_list('id', flat=True))
        
        results = TournamentResult.objects.filter(
            registration_id__in=registration_ids
        )
        
        tournaments_won = results.filter(placement=1).count()
        tournaments_top3 = results.filter(placement__lte=3).count()
        
        # Timestamps (use registration created_at as proxy for participation)
        first_reg = registrations.order_by('created_at').first()
        last_reg = registrations.order_by('-created_at').first()
        
        return {
            'tournaments_played': tournaments_played,
            'tournaments_won': tournaments_won,
            'tournaments_top3': tournaments_top3,
            'first_tournament_at': first_reg.created_at if first_reg else None,
            'last_tournament_at': last_reg.created_at if last_reg else None
        }
    
    @classmethod
    def _compute_team_stats(cls, user_id: int) -> Dict:
        """
        Compute team stats from Team and TeamMembership models.
        
        Returns:
            dict: {
                'teams_joined': int,
                'current_team_id': int | None,
                'current_team_name': str | None
            }
        """
        try:
            profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return {
                'teams_joined': 0,
                'current_team_id': None,
                'current_team_name': None
            }
        
        from apps.teams.models._legacy import TeamMembership, Team
        
        # Count all teams user has joined (past + present)
        memberships = TeamMembership.objects.filter(
            profile=profile,
            status=TeamMembership.Status.ACTIVE
        )
        
        teams_joined = memberships.count()
        
        # Get current team (most recent active membership)
        current_membership = memberships.order_by('-joined_at').first()
        current_team_id = current_membership.team_id if current_membership else None
        current_team_name = current_membership.team.name if current_membership else None
        
        return {
            'teams_joined': teams_joined,
            'current_team_id': current_team_id,
            'current_team_name': current_team_name
        }
    
    @classmethod
    def get_user_tournament_history(cls, user_id: int) -> list:
        """
        Get detailed tournament history for a user.
        
        Returns:
            list: [
                {
                    'tournament_id': int,
                    'tournament_name': str,
                    'placement': int | None,
                    'registered_at': datetime
                },
                ...
            ]
        """
        from apps.tournaments.models.registration import Registration
        from apps.tournaments.models.result import TournamentResult
        
        registrations = Registration.objects.filter(
            user_id=user_id,
            status=Registration.CONFIRMED
        ).select_related('tournament').order_by('-created_at')
        
        history = []
        for reg in registrations:
            try:
                result = TournamentResult.objects.get(registration_id=reg.id)
                placement = result.placement
            except TournamentResult.DoesNotExist:
                placement = None
            
            history.append({
                'tournament_id': reg.tournament_id,
                'tournament_name': reg.tournament.name,
                'placement': placement,
                'registered_at': reg.created_at
            })
        
        return history
