# apps/teams/models/ranking.py
"""
Team Ranking System Models

This module provides:
1. RankingCriteria - Configurable point values for different achievements
2. TeamRankingHistory - Audit trail of point changes
3. TeamRankingCalculator - Service class for computing points

Phase 5 Changes:
- Added LegacyWriteEnforcementMixin to TeamRankingBreakdown (P5-T2)
"""
from __future__ import annotations

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Dict, Any, Optional, List

# Phase 5: Legacy write enforcement
from apps.teams.mixins import LegacyWriteEnforcementMixin, LegacyQuerySetMixin

User = get_user_model()

class RankingCriteria(models.Model):
    """
    Singleton model to store configurable point values for team ranking criteria.
    Admins can edit these values to control the ranking system without code changes.
    """
    
    # Tournament-based points
    tournament_participation = models.PositiveIntegerField(
        default=50,
        help_text="Points awarded for tournament participation (once per tournament)"
    )
    tournament_winner = models.PositiveIntegerField(
        default=500,
        help_text="Points awarded for winning a tournament"
    )
    tournament_runner_up = models.PositiveIntegerField(
        default=300,
        help_text="Points awarded for tournament runner-up position"
    )
    tournament_top_4 = models.PositiveIntegerField(
        default=150,
        help_text="Points awarded for reaching tournament top 4"
    )
    
    # Team composition points
    points_per_member = models.PositiveIntegerField(
        default=10,
        help_text="Points awarded per active team member"
    )
    
    # Team longevity points
    points_per_month_age = models.PositiveIntegerField(
        default=30,
        help_text="Points awarded per full month since team creation"
    )
    
    # Achievement points
    achievement_points = models.PositiveIntegerField(
        default=100,
        help_text="Default points for notable achievements"
    )
    
    # System settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this criteria set is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams_ranking_criteria"
        verbose_name = "Ranking Criteria"
        verbose_name_plural = "Ranking Criteria"
        ordering = ['-is_active', '-updated_at']

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Ranking Criteria ({status}) - Updated {self.updated_at.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        # Ensure only one active criteria set
        if self.is_active:
            RankingCriteria.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_criteria(cls) -> 'RankingCriteria':
        """Get the currently active ranking criteria, create default if none exists."""
        try:
            return cls.objects.filter(is_active=True).first() or cls.objects.create()
        except Exception:
            return cls.objects.create()

    def get_point_values(self) -> Dict[str, int]:
        """Return all point values as a dictionary."""
        return {
            'tournament_participation': self.tournament_participation,
            'tournament_winner': self.tournament_winner,
            'tournament_runner_up': self.tournament_runner_up,
            'tournament_top_4': self.tournament_top_4,
            'points_per_member': self.points_per_member,
            'points_per_month_age': self.points_per_month_age,
            'achievement_points': self.achievement_points,
        }


class TeamRankingHistory(models.Model):
    """
    Audit trail for team ranking point changes.
    Tracks both automatic calculations and manual admin adjustments.
    """
    
    POINT_SOURCE_CHOICES = [
        ('tournament_participation', 'Tournament Participation'),
        ('tournament_winner', 'Tournament Winner'),
        ('tournament_runner_up', 'Tournament Runner-up'),
        ('tournament_top_4', 'Tournament Top 4'),
        ('member_count', 'Team Member Count'),
        ('team_age', 'Team Age Bonus'),
        ('achievement', 'Achievement Points'),
        ('manual_adjustment', 'Manual Admin Adjustment'),
        ('recalculation', 'System Recalculation'),
    ]
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='ranking_history'
    )
    
    points_change = models.IntegerField(
        help_text="Points added (+) or subtracted (-) in this transaction"
    )
    
    points_before = models.PositiveIntegerField(
        help_text="Team's total points before this change"
    )
    
    points_after = models.PositiveIntegerField(
        help_text="Team's total points after this change"
    )
    
    source = models.CharField(
        max_length=30,
        choices=POINT_SOURCE_CHOICES,
        help_text="Source of the point change"
    )
    
    reason = models.TextField(
        blank=True,
        help_text="Detailed explanation for the point change"
    )
    
    # Reference to related object (tournament, achievement, etc.)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    
    # Admin information for manual changes
    admin_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Admin user who made manual adjustment"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "teams_ranking_history"
        verbose_name = "Team Ranking History"
        verbose_name_plural = "Team Ranking History"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', '-created_at']),
            models.Index(fields=['source', '-created_at']),
        ]

    def __str__(self):
        sign = "+" if self.points_change >= 0 else ""
        return f"{self.team.name}: {sign}{self.points_change} pts ({self.get_source_display()})"

    def clean(self):
        """Validate that points_after = points_before + points_change."""
        if self.points_before + self.points_change != self.points_after:
            raise ValidationError("Points calculation doesn't match: before + change ≠ after")


class TeamRankingBreakdownQuerySet(LegacyQuerySetMixin, models.QuerySet):
    """Custom QuerySet with legacy write enforcement for bulk operations."""
    pass


class TeamRankingBreakdown(LegacyWriteEnforcementMixin, models.Model):
    """
    Current point breakdown for each team.
    Shows where each team's points come from for transparency.
    
    Phase 5: Write operations blocked during migration.
    Use apps.organizations.TeamRanking for vNext system.
    """
    
    team = models.OneToOneField(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='ranking_breakdown',
        primary_key=True
    )
    
    # Tournament points
    tournament_participation_points = models.PositiveIntegerField(default=0)
    tournament_winner_points = models.PositiveIntegerField(default=0)
    tournament_runner_up_points = models.PositiveIntegerField(default=0)
    tournament_top_4_points = models.PositiveIntegerField(default=0)
    
    # Team composition points
    member_count_points = models.PositiveIntegerField(default=0)
    team_age_points = models.PositiveIntegerField(default=0)
    achievement_points = models.PositiveIntegerField(default=0)
    
    # Manual adjustments
    manual_adjustment_points = models.IntegerField(default=0)
    
    # Calculated totals
    calculated_total = models.PositiveIntegerField(
        default=0,
        help_text="Sum of all automatic point calculations"
    )
    
    final_total = models.PositiveIntegerField(
        default=0,
        help_text="Final total including manual adjustments"
    )
    
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams_ranking_breakdown"
        verbose_name = "Team Ranking Breakdown"
        verbose_name_plural = "Team Ranking Breakdowns"
    
    # Custom manager with Phase 5 write enforcement
    objects = TeamRankingBreakdownQuerySet.as_manager()

    def __str__(self):
        return f"{self.team.name} - {self.final_total} points breakdown"

    def get_breakdown_dict(self) -> Dict[str, int]:
        """Return point breakdown as a dictionary."""
        return {
            'Tournament Participation': self.tournament_participation_points,
            'Tournament Wins': self.tournament_winner_points,
            'Tournament Runner-up': self.tournament_runner_up_points,
            'Tournament Top 4': self.tournament_top_4_points,
            'Team Members': self.member_count_points,
            'Team Age': self.team_age_points,
            'Achievements': self.achievement_points,
            'Manual Adjustments': self.manual_adjustment_points,
        }

    def calculate_total(self) -> int:
        """Calculate and return the current total points."""
        self.calculated_total = (
            self.tournament_participation_points +
            self.tournament_winner_points +
            self.tournament_runner_up_points +
            self.tournament_top_4_points +
            self.member_count_points +
            self.team_age_points +
            self.achievement_points
        )
        
        self.final_total = max(0, self.calculated_total + self.manual_adjustment_points)
        return self.final_total

    def save(self, *args, **kwargs):
        """Auto-calculate totals on save."""
        self.calculate_total()
        super().save(*args, **kwargs)
    
    def get_tournament_points_total(self) -> int:
        """Get total tournament points."""
        return (
            self.tournament_participation_points +
            self.tournament_winner_points +
            self.tournament_runner_up_points +
            self.tournament_top_4_points
        )
    
    def get_team_composition_total(self) -> int:
        """Get total team composition points."""
        return (
            self.member_count_points +
            self.team_age_points +
            self.achievement_points
        )
    
    def get_detailed_breakdown(self) -> Dict[str, Any]:
        """Get detailed breakdown for frontend display."""
        return {
            'tournament': {
                'participation': self.tournament_participation_points,
                'winner': self.tournament_winner_points,
                'runner_up': self.tournament_runner_up_points,
                'top_4': self.tournament_top_4_points,
                'total': self.get_tournament_points_total()
            },
            'team': {
                'members': self.member_count_points,
                'age': self.team_age_points,
                'achievements': self.achievement_points,
                'total': self.get_team_composition_total()
            },
            'adjustments': {
                'manual': self.manual_adjustment_points,
                'is_positive': self.manual_adjustment_points >= 0
            },
            'totals': {
                'calculated': self.calculated_total,
                'final': self.final_total,
                'last_updated': self.last_calculated
            }
        }
    
    def get_recent_changes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent point changes for this team."""
        from .ranking import TeamRankingHistory
        
        history = TeamRankingHistory.objects.filter(
            team=self.team
        ).order_by('-created_at')[:limit]
        
        return [
            {
                'date': record.created_at,
                'source': record.source,
                'points_change': record.points_change,
                'points_after': record.points_after,
                'reason': record.reason,
                'admin_user': record.admin_user.username if record.admin_user else 'System'
            }
            for record in history
        ]
    
    def to_frontend_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for frontend consumption."""
        return {
            'team_id': self.team.pk,
            'team_name': self.team.name,
            'team_tag': self.team.tag,
            'final_points': self.final_total,
            'breakdown': self.get_detailed_breakdown(),
            'recent_changes': self.get_recent_changes(),
            'last_updated': self.last_calculated.isoformat() if self.last_calculated else None
        }
        
        # Update the team's total_points field
        if hasattr(self, 'team') and self.team:
            self.team.total_points = self.final_total
            self.team.save(update_fields=['total_points'])


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2 - TASK 7.1: GAME-SPECIFIC RANKINGS
# ═══════════════════════════════════════════════════════════════════════════

class TeamGameRanking(models.Model):
    """
    Per-game ranking for teams (Phase 2 - Task 7.1).
    
    Each team has one ranking record per game they compete in.
    Tracks division, points, ELO, and game-specific stats.
    """
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='game_rankings'
    )
    game = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Game slug/identifier (e.g., 'VALORANT', 'CS2', 'MLBB')"
    )
    
    # === RANKING METRICS ===
    points = models.IntegerField(
        default=0,
        help_text="Total ranking points earned in this game"
    )
    division = models.CharField(
        max_length=20,
        default='BRONZE',
        help_text="Current division based on ELO"
    )
    elo_rating = models.IntegerField(
        default=1500,  # RankingConstants.DEFAULT_ELO
        help_text="ELO rating for this game"
    )
    
    # === STREAKS & PERFORMANCE ===
    win_streak = models.IntegerField(default=0)
    loss_streak = models.IntegerField(default=0)
    matches_played = models.IntegerField(default=0)
    matches_won = models.IntegerField(default=0)
    matches_lost = models.IntegerField(default=0)
    
    # === TOURNAMENT PERFORMANCE ===
    tournaments_played = models.IntegerField(default=0)
    tournaments_won = models.IntegerField(default=0)
    tournament_podium_finishes = models.IntegerField(
        default=0,
        help_text="Top 3 finishes"
    )
    
    # === GLOBAL CROSS-GAME RATING ===
    global_elo = models.IntegerField(
        default=1500,
        help_text="Cross-game ELO (contributes to overall team ranking)"
    )
    
    # === TIMESTAMPS ===
    last_match_date = models.DateTimeField(null=True, blank=True)
    last_decay_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [('team', 'game')]
        indexes = [
            # Leaderboard queries
            models.Index(fields=['game', '-elo_rating'], name='ranking_game_elo_idx'),
            models.Index(fields=['game', '-points'], name='ranking_game_points_idx'),
            models.Index(fields=['-global_elo'], name='ranking_global_elo_idx'),
            
            # Division queries
            models.Index(fields=['game', 'division', '-elo_rating'], name='ranking_division_idx'),
            
            # Team lookup
            models.Index(fields=['team', 'game'], name='ranking_team_game_idx'),
        ]
        ordering = ['-elo_rating']
    
    def __str__(self):
        return f"{self.team.name} - {self.game} ({self.division} - {self.elo_rating} ELO)"
    
    def update_division(self):
        """Update division based on current ELO rating."""
        from apps.teams.constants import RankingConstants
        for division, (min_elo, max_elo) in RankingConstants.DIVISION_THRESHOLDS.items():
            if min_elo <= self.elo_rating <= max_elo:
                self.division = division
                break
        self.save(update_fields=['division'])
    
    @property
    def win_rate(self):
        """Calculate win rate percentage."""
        if self.matches_played == 0:
            return 0.0
        return round((self.matches_won / self.matches_played) * 100, 1)
    
    @property
    def rank_display(self):
        """Get formatted rank display."""
        return f"{self.division} ({self.elo_rating} ELO)"
