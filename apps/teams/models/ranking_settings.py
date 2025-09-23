# apps/teams/models/ranking_settings.py
"""
Team Ranking Settings model for configurable point system.
Allows admin control over team ranking calculation parameters.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings


class TeamRankingSettings(models.Model):
    """
    Singleton model for team ranking point system configuration.
    Admin can adjust these values to change how teams are ranked.
    """
    # Achievement-based points
    tournament_victory_points = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Points awarded for each tournament victory (1st place)"
    )
    
    runner_up_points = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(1)],
        help_text="Points awarded for each runner-up finish (2nd place)"
    )
    
    top4_finish_points = models.PositiveIntegerField(
        default=40,
        validators=[MinValueValidator(1)],
        help_text="Points awarded for each top 4 tournament finish"
    )
    
    top8_finish_points = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(1)],
        help_text="Points awarded for each top 8 tournament finish"
    )
    
    participation_points = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Points awarded for each tournament participation"
    )
    
    general_achievement_points = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1)],
        help_text="Points awarded per general achievement/trophy"
    )
    
    # Team composition points
    member_points = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Points awarded per active team member"
    )
    
    # Team age/establishment points
    monthly_age_points = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1)],
        help_text="Points awarded per month since team creation"
    )
    
    # Bonus multipliers
    verified_team_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.10,
        validators=[MinValueValidator(1.0)],
        help_text="Multiplier for verified teams (e.g., 1.10 = 10% bonus)"
    )
    
    featured_team_bonus = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0)],
        help_text="Flat bonus points for featured teams"
    )
    
    # System settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this ranking system is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Last admin who updated these settings"
    )
    
    class Meta:
        verbose_name = "Team Ranking Settings"
        verbose_name_plural = "Team Ranking Settings"
        db_table = "teams_ranking_settings"
    
    def __str__(self):
        return f"Team Ranking Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        # Ensure only one active settings record exists
        if self.is_active:
            TeamRankingSettings.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_settings(cls):
        """Get the currently active ranking settings, create default if none exists."""
        try:
            return cls.objects.filter(is_active=True).first() or cls.objects.create(is_active=True)
        except Exception:
            return cls.objects.create(is_active=True)
    
    def calculate_team_score(self, team):
        """
        Calculate a team's ranking score based on current settings.
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        score = 0
        
        # Achievement-based scoring
        achievements = team.achievements.all()
        for achievement in achievements:
            if achievement.placement == 'WINNER':
                score += self.tournament_victory_points
            elif achievement.placement == 'RUNNER_UP':
                score += self.runner_up_points
            elif achievement.placement == 'TOP4':
                score += self.top4_finish_points
            elif achievement.placement == 'TOP8':
                score += self.top8_finish_points
            elif achievement.placement == 'PARTICIPANT':
                score += self.participation_points
            
            # General achievement bonus
            score += self.general_achievement_points
        
        # Member count bonus
        member_count = getattr(team, 'memberships_count', 0) or team.memberships.filter(status='ACTIVE').count()
        score += member_count * self.member_points
        
        # Team age bonus
        if team.created_at:
            months_old = relativedelta(timezone.now(), team.created_at).months
            months_old += relativedelta(timezone.now(), team.created_at).years * 12
            score += months_old * self.monthly_age_points
        
        # Apply multipliers and bonuses
        if getattr(team, 'is_verified', False):
            score = int(score * float(self.verified_team_multiplier))
        
        if getattr(team, 'is_featured', False):
            score += self.featured_team_bonus
        
        return max(score, 0)  # Ensure non-negative score