"""
Team Ranking Calculator Service

This module provides the core service for calculating and updating team rankings
based on tournament performance, achievements, and team composition.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.apps import apps
from typing import Dict, Any, Optional, List
from datetime import timedelta
from decimal import Decimal


class TeamRankingCalculator:
    """
    Service class for calculating team ranking points.
    Handles both automatic calculations and manual adjustments.
    """
    
    def __init__(self, team):
        """Initialize calculator for a specific team."""
        self.team = team
        self.criteria = self._get_active_criteria()
        
    def _get_active_criteria(self):
        """Get active ranking criteria."""
        RankingCriteria = apps.get_model('teams', 'RankingCriteria')
        return RankingCriteria.get_active_criteria()
    
    def calculate_full_ranking(self) -> Dict[str, Any]:
        """
        Calculate complete ranking breakdown for the team.
        Returns detailed breakdown with point sources.
        """
        breakdown = {
            'tournament_participation': 0,
            'tournament_winner': 0,
            'tournament_runner_up': 0,
            'tournament_top_4': 0,
            'member_count': 0,
            'team_age': 0,
            'achievement': 0,
            'manual_adjustment': 0,
        }
        
        # Calculate tournament points
        tournament_points = self._calculate_tournament_points()
        breakdown.update(tournament_points)
        
        # Calculate team composition points
        breakdown['member_count'] = self._calculate_member_points()
        
        # Calculate team age points
        breakdown['team_age'] = self._calculate_age_points()
        
        # Calculate achievement points
        breakdown['achievement'] = self._calculate_achievement_points()
        
        # Get manual adjustments
        breakdown['manual_adjustment'] = self.team.adjust_points
        
        # Calculate totals
        calculated_total = sum([
            breakdown['tournament_participation'],
            breakdown['tournament_winner'],
            breakdown['tournament_runner_up'],
            breakdown['tournament_top_4'],
            breakdown['member_count'],
            breakdown['team_age'],
            breakdown['achievement'],
        ])
        
        final_total = max(0, calculated_total + breakdown['manual_adjustment'])
        
        return {
            'breakdown': breakdown,
            'calculated_total': calculated_total,
            'final_total': final_total,
            'calculation_time': timezone.now()
        }
    
    def _calculate_tournament_points(self) -> Dict[str, int]:
        """Calculate points from tournament participation and placements."""
        TeamAchievement = apps.get_model('teams', 'TeamAchievement')
        
        points = {
            'tournament_participation': 0,
            'tournament_winner': 0,
            'tournament_runner_up': 0,
            'tournament_top_4': 0,
        }
        
        # Get tournament-related achievements
        achievements = TeamAchievement.objects.filter(
            team=self.team,
            tournament__isnull=False
        ).select_related('tournament')
        
        # Count unique tournament participations
        unique_tournaments = set()
        
        for achievement in achievements:
            # Add participation point (once per tournament)
            if achievement.tournament_id not in unique_tournaments:
                points['tournament_participation'] += self.criteria.tournament_participation
                unique_tournaments.add(achievement.tournament_id)
            
            # Add placement points
            placement = achievement.placement
            
            if placement == 'WINNER':
                points['tournament_winner'] += self.criteria.tournament_winner
            elif placement == 'RUNNER_UP':
                points['tournament_runner_up'] += self.criteria.tournament_runner_up
            elif placement in ['THIRD', 'FOURTH']:
                points['tournament_top_4'] += self.criteria.tournament_top_4
        
        return points
    
    def _calculate_member_points(self) -> int:
        """Calculate points based on active member count."""
        TeamMembership = apps.get_model('teams', 'TeamMembership')
        
        active_count = TeamMembership.objects.filter(
            team=self.team,
            status='ACTIVE'
        ).count()
        
        return active_count * self.criteria.points_per_member
    
    def _calculate_age_points(self) -> int:
        """Calculate bonus points based on team age."""
        if not self.team.created_at:
            return 0
        
        # Calculate months since creation
        age = timezone.now() - self.team.created_at
        months = int(age.days / 30)  # Approximate months
        
        return months * self.criteria.points_per_month_age
    
    def _calculate_achievement_points(self) -> int:
        """Calculate points from non-tournament achievements."""
        TeamAchievement = apps.get_model('teams', 'TeamAchievement')
        
        # Get achievements not tied to tournaments
        achievements = TeamAchievement.objects.filter(
            team=self.team,
            tournament__isnull=True
        ).count()
        
        return achievements * self.criteria.achievement_points
    
    @transaction.atomic
    def update_ranking(self, reason: str = "Automatic recalculation", admin_user=None) -> Dict[str, Any]:
        """
        Update team's ranking in database and create history record.
        
        Args:
            reason: Explanation for the update
            admin_user: Admin user if manual update
            
        Returns:
            Dict with update results and new totals
        """
        TeamRankingHistory = apps.get_model('teams', 'TeamRankingHistory')
        TeamRankingBreakdown = apps.get_model('teams', 'TeamRankingBreakdown')
        
        # Calculate new ranking
        calculation = self.calculate_full_ranking()
        breakdown_data = calculation['breakdown']
        new_total = calculation['final_total']
        
        # Get current points
        old_total = self.team.total_points
        points_change = new_total - old_total
        
        # Update or create breakdown
        breakdown, created = TeamRankingBreakdown.objects.update_or_create(
            team=self.team,
            defaults={
                'tournament_participation_points': breakdown_data['tournament_participation'],
                'tournament_winner_points': breakdown_data['tournament_winner'],
                'tournament_runner_up_points': breakdown_data['tournament_runner_up'],
                'tournament_top_4_points': breakdown_data['tournament_top_4'],
                'member_count_points': breakdown_data['member_count'],
                'team_age_points': breakdown_data['team_age'],
                'achievement_points': breakdown_data['achievement'],
                'manual_adjustment_points': breakdown_data['manual_adjustment'],
            }
        )
        
        # Update team total points
        self.team.total_points = new_total
        self.team.save(update_fields=['total_points'])
        
        # Create history record only if points changed
        if points_change != 0:
            TeamRankingHistory.objects.create(
                team=self.team,
                points_change=points_change,
                points_before=old_total,
                points_after=new_total,
                source='recalculation',
                reason=reason,
                admin_user=admin_user
            )
        
        return {
            'success': True,
            'old_total': old_total,
            'new_total': new_total,
            'points_change': points_change,
            'breakdown': breakdown_data,
            'breakdown_created': created
        }
    
    def add_manual_adjustment(
        self,
        points: int,
        reason: str,
        admin_user,
        source: str = "manual_adjustment"
    ) -> Dict[str, Any]:
        """
        Manually adjust team points (admin only).
        
        Args:
            points: Points to add (positive) or subtract (negative)
            reason: Explanation for adjustment
            admin_user: Admin making the adjustment
            source: Source category for the adjustment
            
        Returns:
            Dict with adjustment results
        """
        TeamRankingHistory = apps.get_model('teams', 'TeamRankingHistory')
        
        with transaction.atomic():
            old_total = self.team.total_points
            old_adjustment = self.team.adjust_points
            
            # Update adjustment field
            self.team.adjust_points += points
            new_total = old_total + points
            
            # Ensure total doesn't go negative
            if new_total < 0:
                points = -old_total
                new_total = 0
                self.team.adjust_points = old_adjustment + points
            
            self.team.total_points = new_total
            self.team.save(update_fields=['total_points', 'adjust_points'])
            
            # Create history record
            TeamRankingHistory.objects.create(
                team=self.team,
                points_change=points,
                points_before=old_total,
                points_after=new_total,
                source=source,
                reason=reason,
                admin_user=admin_user
            )
            
            # Recalculate breakdown
            self.update_ranking(
                reason=f"After manual adjustment: {reason}",
                admin_user=admin_user
            )
        
        return {
            'success': True,
            'old_total': old_total,
            'new_total': new_total,
            'points_added': points,
            'reason': reason
        }
    
    def add_tournament_points(
        self,
        tournament,
        placement: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Add points for tournament placement.
        
        Args:
            tournament: Tournament instance
            placement: Placement code (WINNER, RUNNER_UP, THIRD, FOURTH)
            reason: Additional context
            
        Returns:
            Dict with points added
        """
        TeamRankingHistory = apps.get_model('teams', 'TeamRankingHistory')
        
        # Determine points based on placement
        points_map = {
            'WINNER': self.criteria.tournament_winner,
            'RUNNER_UP': self.criteria.tournament_runner_up,
            'THIRD': self.criteria.tournament_top_4,
            'FOURTH': self.criteria.tournament_top_4,
        }
        
        points = points_map.get(placement, 0)
        
        if points == 0:
            return {
                'success': False,
                'error': f"Invalid placement: {placement}"
            }
        
        # Determine source
        source_map = {
            'WINNER': 'tournament_winner',
            'RUNNER_UP': 'tournament_runner_up',
            'THIRD': 'tournament_top_4',
            'FOURTH': 'tournament_top_4',
        }
        
        source = source_map.get(placement, 'tournament_participation')
        
        with transaction.atomic():
            old_total = self.team.total_points
            new_total = old_total + points
            
            self.team.total_points = new_total
            self.team.save(update_fields=['total_points'])
            
            # Create history
            full_reason = f"Tournament: {tournament.name} - Placement: {placement}"
            if reason:
                full_reason += f" - {reason}"
            
            TeamRankingHistory.objects.create(
                team=self.team,
                points_change=points,
                points_before=old_total,
                points_after=new_total,
                source=source,
                reason=full_reason,
                related_object_type='tournament',
                related_object_id=tournament.id
            )
            
            # Recalculate full ranking
            self.update_ranking(
                reason=f"After tournament placement update: {tournament.name}"
            )
        
        return {
            'success': True,
            'points_added': points,
            'old_total': old_total,
            'new_total': self.team.total_points,
            'placement': placement,
            'tournament': tournament.name
        }
    
    @classmethod
    def recalculate_all_teams(
        cls,
        game: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Recalculate rankings for all teams (or filtered subset).
        
        Args:
            game: Filter by game (optional)
            limit: Maximum teams to process (optional)
            
        Returns:
            Dict with processing results
        """
        Team = apps.get_model('teams', 'Team')
        
        teams = Team.objects.filter(is_active=True)
        
        if game:
            teams = teams.filter(game=game)
        
        if limit:
            teams = teams[:limit]
        
        results = {
            'processed': 0,
            'updated': 0,
            'unchanged': 0,
            'errors': []
        }
        
        for team in teams:
            try:
                calculator = cls(team)
                result = calculator.update_ranking(
                    reason="Bulk recalculation"
                )
                
                results['processed'] += 1
                
                if result['points_change'] != 0:
                    results['updated'] += 1
                else:
                    results['unchanged'] += 1
                    
            except Exception as e:
                results['errors'].append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'error': str(e)
                })
        
        return results
    
    @classmethod
    def get_leaderboard(
        cls,
        game: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get ranked leaderboard of teams.
        
        Args:
            game: Filter by game (optional)
            region: Filter by region (optional)
            limit: Number of teams to return
            
        Returns:
            List of team dictionaries with rankings
        """
        Team = apps.get_model('teams', 'Team')
        
        teams = Team.objects.filter(
            is_active=True,
            total_points__gt=0
        ).select_related('captain')
        
        if game:
            teams = teams.filter(game=game)
        
        if region:
            teams = teams.filter(region__icontains=region)
        
        teams = teams.order_by('-total_points', '-created_at')[:limit]
        
        leaderboard = []
        
        for rank, team in enumerate(teams, start=1):
            # Get breakdown if exists
            breakdown = None
            if hasattr(team, 'ranking_breakdown'):
                breakdown = team.ranking_breakdown.get_detailed_breakdown()
            
            leaderboard.append({
                'rank': rank,
                'team_id': team.id,
                'team_name': team.name,
                'team_tag': team.tag,
                'team_logo': team.logo.url if team.logo else None,
                'captain': team.captain.display_name if team.captain else None,
                'total_points': team.total_points,
                'game': team.game,
                'region': team.region,
                'created_at': team.created_at,
                'is_verified': team.is_verified,
                'is_featured': team.is_featured,
                'breakdown': breakdown
            })
        
        return leaderboard
    
    def get_rank_position(self, game: Optional[str] = None) -> Dict[str, Any]:
        """
        Get team's current rank position.
        
        Args:
            game: Scope ranking to specific game (optional)
            
        Returns:
            Dict with rank information
        """
        Team = apps.get_model('teams', 'Team')
        
        query = Team.objects.filter(
            is_active=True,
            total_points__gte=self.team.total_points
        )
        
        if game:
            query = query.filter(game=game)
        
        rank = query.count()
        
        # Get total teams in ranking
        total_query = Team.objects.filter(is_active=True, total_points__gt=0)
        if game:
            total_query = total_query.filter(game=game)
        
        total_teams = total_query.count()
        
        # Calculate percentile
        percentile = 0
        if total_teams > 0:
            percentile = ((total_teams - rank + 1) / total_teams) * 100
        
        return {
            'rank': rank,
            'total_teams': total_teams,
            'percentile': round(percentile, 1),
            'points': self.team.total_points,
            'game': game or 'all'
        }
