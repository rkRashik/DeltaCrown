# apps/teams/services/ranking_service.py
"""
Team Ranking Service

Provides centralized logic for calculating and updating team ranking points.
Handles automatic calculations from various triggers and ensures idempotency.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone as tz
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from django.db import transaction
from django.apps import apps
from django.utils import timezone
from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    
User = get_user_model()

logger = logging.getLogger(__name__)


class TeamRankingService:
    """
    Central service for managing team ranking point calculations and updates.
    """

    def __init__(self):
        """Initialize the ranking service."""
        # Dynamic imports to avoid circular dependencies
        self._team_model = None
        self._criteria_model = None
        self._history_model = None
        self._breakdown_model = None

    @property
    def Team(self):
        if not self._team_model:
            self._team_model = apps.get_model('teams', 'Team')
        return self._team_model

    @property
    def RankingCriteria(self):
        if not self._criteria_model:
            self._criteria_model = apps.get_model('teams', 'RankingCriteria')
        return self._criteria_model

    @property
    def TeamRankingHistory(self):
        if not self._history_model:
            self._history_model = apps.get_model('teams', 'TeamRankingHistory')
        return self._history_model

    @property
    def TeamRankingBreakdown(self):
        if not self._breakdown_model:
            self._breakdown_model = apps.get_model('teams', 'TeamRankingBreakdown')
        return self._breakdown_model

    def get_active_criteria(self):
        """Get the active ranking criteria."""
        return self.RankingCriteria.get_active_criteria()

    def calculate_team_age_points(self, team) -> int:
        """Calculate points based on team age in months."""
        if not team.created_at:
            return 0
        
        criteria = self.get_active_criteria()
        age_delta = timezone.now() - team.created_at
        months = int(age_delta.days / 30)  # Approximate months
        
        return months * criteria.points_per_month_age

    def calculate_member_points(self, team) -> int:
        """Calculate points based on active team members."""
        criteria = self.get_active_criteria()
        
        # Count active members
        member_count = team.memberships.filter(status='ACTIVE').count()
        
        return member_count * criteria.points_per_member

    def calculate_tournament_points(self, team) -> Dict[str, int]:
        """
        Calculate tournament-related points for a team.
        Returns breakdown of different tournament achievements.
        """
        criteria = self.get_active_criteria()
        points_breakdown = {
            'participation': 0,
            'winner': 0,
            'runner_up': 0,
            'top_4': 0,
        }
        
        try:
            # Try to get tournament-related models
            Tournament = apps.get_model('tournaments', 'Tournament')
            Registration = apps.get_model('tournaments', 'Registration')
            
            # Count tournament participations (unique tournaments)
            participations = Registration.objects.filter(
                team=team,
                status__in=['APPROVED', 'CONFIRMED', 'COMPLETED']
            ).values('tournament').distinct().count()
            
            points_breakdown['participation'] = participations * criteria.tournament_participation
            
            # Count wins, runner-ups, top 4 finishes
            # This would need to be implemented based on your tournament result structure
            # For now, we'll use placeholder logic
            
            # Example: Check tournament results if you have a results model
            # This is a placeholder - adjust based on your actual tournament structure
            
        except Exception as e:
            logger.warning(f"Could not calculate tournament points for team {team.id}: {e}")
        
        return points_breakdown

    def get_team_breakdown(self, team) -> 'TeamRankingBreakdown':
        """Get or create the ranking breakdown for a team."""
        breakdown, created = self.TeamRankingBreakdown.objects.get_or_create(
            team=team
        )
        return breakdown

    @transaction.atomic
    def recalculate_team_points(self, team, admin_user: Optional['AbstractUser'] = None, reason: str = "") -> Dict[str, Any]:
        """
        Completely recalculate all points for a team.
        Returns the calculation breakdown and updates the database.
        """
        try:
            # Get current breakdown
            breakdown = self.get_team_breakdown(team)
            old_total = breakdown.final_total

            # Calculate all point categories
            age_points = self.calculate_team_age_points(team)
            member_points = self.calculate_member_points(team)
            tournament_points = self.calculate_tournament_points(team)

            # Update breakdown
            breakdown.team_age_points = age_points
            breakdown.member_count_points = member_points
            breakdown.tournament_participation_points = tournament_points['participation']
            breakdown.tournament_winner_points = tournament_points['winner']
            breakdown.tournament_runner_up_points = tournament_points['runner_up']
            breakdown.tournament_top_4_points = tournament_points['top_4']
            
            # Keep existing manual adjustments and achievements
            # (these should only be changed through admin actions)
            
            # Save the breakdown (this also updates team.total_points)
            breakdown.save()

            new_total = breakdown.final_total
            points_change = new_total - old_total

            # Record the recalculation in history if there was a change
            if points_change != 0:
                self.TeamRankingHistory.objects.create(
                    team=team,
                    points_change=points_change,
                    points_before=old_total,
                    points_after=new_total,
                    source='recalculation',
                    reason=reason or f"Automatic recalculation: {timezone.now()}",
                    admin_user=admin_user
                )

            logger.info(f"Recalculated points for team {team.name}: {old_total} -> {new_total}")

            return {
                'success': True,
                'old_total': old_total,
                'new_total': new_total,
                'points_change': points_change,
                'breakdown': breakdown.get_breakdown_dict()
            }

        except Exception as e:
            logger.error(f"Failed to recalculate points for team {team.id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @transaction.atomic
    def adjust_team_points(self, team, points_adjustment: int, reason: str, admin_user: 'AbstractUser') -> Dict[str, Any]:
        """
        Make a manual adjustment to team points.
        This is used by admins to add or subtract points with a reason.
        """
        try:
            breakdown = self.get_team_breakdown(team)
            old_total = breakdown.final_total

            # Update manual adjustment
            breakdown.manual_adjustment_points += points_adjustment
            breakdown.save()

            new_total = breakdown.final_total

            # Record in history
            self.TeamRankingHistory.objects.create(
                team=team,
                points_change=points_adjustment,
                points_before=old_total,
                points_after=new_total,
                source='manual_adjustment',
                reason=reason,
                admin_user=admin_user
            )

            logger.info(f"Manual adjustment for team {team.name}: {points_adjustment} points by {admin_user.username}")

            return {
                'success': True,
                'old_total': old_total,
                'new_total': new_total,
                'points_change': points_adjustment
            }

        except Exception as e:
            logger.error(f"Failed to adjust points for team {team.id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @transaction.atomic
    def award_tournament_points(self, team, tournament, achievement_type: str, admin_user: Optional['AbstractUser'] = None) -> Dict[str, Any]:
        """
        Award points for tournament achievements.
        
        Args:
            team: Team model instance
            tournament: Tournament model instance  
            achievement_type: 'participation', 'winner', 'runner_up', 'top_4'
            admin_user: User making the award (optional)
        """
        try:
            criteria = self.get_active_criteria()
            breakdown = self.get_team_breakdown(team)
            old_total = breakdown.final_total

            # Determine points to award
            points_map = {
                'participation': criteria.tournament_participation,
                'winner': criteria.tournament_winner,
                'runner_up': criteria.tournament_runner_up,
                'top_4': criteria.tournament_top_4,
            }

            if achievement_type not in points_map:
                raise ValueError(f"Invalid achievement type: {achievement_type}")

            points_awarded = points_map[achievement_type]

            # Check for duplicate awards (idempotency)
            existing_award = self.TeamRankingHistory.objects.filter(
                team=team,
                source=f'tournament_{achievement_type}',
                related_object_type='tournament',
                related_object_id=tournament.id if tournament else None
            ).exists()

            if existing_award:
                logger.warning(f"Tournament {achievement_type} points already awarded to team {team.name} for tournament {tournament}")
                return {
                    'success': False,
                    'error': 'Points already awarded for this tournament achievement'
                }

            # Update breakdown
            field_name = f'tournament_{achievement_type}_points'
            current_value = getattr(breakdown, field_name, 0)
            setattr(breakdown, field_name, current_value + points_awarded)
            breakdown.save()

            new_total = breakdown.final_total

            # Record in history
            self.TeamRankingHistory.objects.create(
                team=team,
                points_change=points_awarded,
                points_before=old_total,
                points_after=new_total,
                source=f'tournament_{achievement_type}',
                reason=f"Tournament {achievement_type}: {tournament.name if tournament else 'Unknown'}",
                related_object_type='tournament',
                related_object_id=tournament.id if tournament else None,
                admin_user=admin_user
            )

            logger.info(f"Awarded {points_awarded} {achievement_type} points to team {team.name}")

            return {
                'success': True,
                'points_awarded': points_awarded,
                'old_total': old_total,
                'new_total': new_total
            }

        except Exception as e:
            logger.error(f"Failed to award tournament points: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def recalculate_all_teams(self, admin_user: Optional['AbstractUser'] = None) -> Dict[str, Any]:
        """
        Recalculate points for all teams.
        Useful for bulk updates or after criteria changes.
        """
        teams_processed = 0
        teams_updated = 0
        errors = []

        for team in self.Team.objects.all():
            result = self.recalculate_team_points(team, admin_user, "Bulk recalculation")
            teams_processed += 1
            
            if result['success']:
                if result['points_change'] != 0:
                    teams_updated += 1
            else:
                errors.append(f"Team {team.name}: {result['error']}")

        logger.info(f"Bulk recalculation completed: {teams_processed} processed, {teams_updated} updated")

        return {
            'success': True,
            'teams_processed': teams_processed,
            'teams_updated': teams_updated,
            'errors': errors
        }

    def get_team_rankings(self, limit: Optional[int] = None, game: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get team rankings ordered by total points.
        
        Args:
            limit: Maximum number of teams to return
            game: Filter by specific game (optional)
        """
        queryset = self.Team.objects.select_related('ranking_breakdown').order_by('-total_points')
        
        if game:
            queryset = queryset.filter(game=game)
            
        if limit:
            queryset = queryset[:limit]

        rankings = []
        for i, team in enumerate(queryset, 1):
            breakdown = getattr(team, 'ranking_breakdown', None)
            rankings.append({
                'rank': i,
                'team': team,
                'points': team.total_points,
                'breakdown': breakdown.get_breakdown_dict() if breakdown else {}
            })

        return rankings


# Global service instance
ranking_service = TeamRankingService()