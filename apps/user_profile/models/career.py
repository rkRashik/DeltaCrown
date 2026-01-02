"""
Career & Matchmaking Preference Models (Phase 2A)
Extends UserProfile with career status and bounty/matchmaking preferences.
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import json


# Career Status Choices
CAREER_STATUS_CHOICES = [
    ('SIGNED', 'Signed to Team'),
    ('FREE_AGENT', 'Free Agent'),
    ('LOOKING', 'Actively Looking'),
    ('NOT_LOOKING', 'Not Looking'),
]

AVAILABILITY_CHOICES = [
    ('FULL_TIME', 'Full Time'),
    ('PART_TIME', 'Part Time'),
    ('WEEKENDS', 'Weekends Only'),
    ('CUSTOM', 'Custom Schedule'),
]

CONTRACT_TYPE_CHOICES = [
    ('TEAM', 'Team Contract'),
    ('ORG', 'Organization Contract'),
    ('SPONSORSHIP', 'Sponsorship'),
    ('STREAMING', 'Streaming/Content'),
]

RECRUITER_VISIBILITY_CHOICES = [
    ('PUBLIC', 'Public (Anyone)'),
    ('VERIFIED_SCOUTS', 'Verified Scouts Only'),
    ('PRIVATE', 'Private (Hidden)'),
]


class CareerProfile(models.Model):
    """
    Career and LFT (Looking For Team) preferences.
    OneToOne extension of UserProfile for recruitment/scouting.
    """
    user_profile = models.OneToOneField(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='career_profile'
    )
    
    # Career Status
    career_status = models.CharField(
        max_length=20,
        choices=CAREER_STATUS_CHOICES,
        default='NOT_LOOKING',
        help_text="Current recruitment status"
    )
    lft_enabled = models.BooleanField(
        default=False,
        help_text="Show 'Looking for Team' badge on profile"
    )
    
    # Roles & Preferences
    primary_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Primary esports roles (IGL, Duelist, Support, etc.)"
    )
    secondary_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Secondary roles willing to play"
    )
    preferred_region = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Preferred region for teams (e.g., NA, EU, AS)"
    )
    
    # Availability
    availability = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default='PART_TIME',
        help_text="Time commitment availability"
    )
    
    # Compensation
    salary_expectation_min = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum monthly salary expectation (in local currency or DC)"
    )
    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_TYPE_CHOICES,
        default='TEAM',
        help_text="Preferred contract type"
    )
    
    # Privacy & Visibility
    recruiter_visibility = models.CharField(
        max_length=20,
        choices=RECRUITER_VISIBILITY_CHOICES,
        default='PUBLIC',
        help_text="Who can view career profile"
    )
    allow_direct_contracts = models.BooleanField(
        default=True,
        help_text="Allow managers to send draft contracts via DM"
    )
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_profile_career_profile'
        verbose_name = 'Career Profile'
        verbose_name_plural = 'Career Profiles'
    
    def clean(self):
        """Validate career profile rules"""
        # Rule: If LFT enabled, cannot be SIGNED
        if self.lft_enabled and self.career_status == 'SIGNED':
            raise ValidationError({
                'lft_enabled': "Cannot enable LFT while status is 'Signed to Team'"
            })
        
        # Rule: Salary must be non-negative
        if self.salary_expectation_min is not None and self.salary_expectation_min < 0:
            raise ValidationError({
                'salary_expectation_min': "Salary expectation cannot be negative"
            })
        
        # Rule: Roles must be non-empty lists
        if not isinstance(self.primary_roles, list):
            raise ValidationError({
                'primary_roles': "Primary roles must be a list"
            })
        if not isinstance(self.secondary_roles, list):
            raise ValidationError({
                'secondary_roles': "Secondary roles must be a list"
            })
    
    def __str__(self):
        return f"{self.user_profile.user.username} Career Profile ({self.career_status})"


class MatchmakingPreferences(models.Model):
    """
    Bounty and matchmaking preferences for challenge/match invitations.
    Controls auto-accept, bounty thresholds, and matchmaking filters.
    """
    user_profile = models.OneToOneField(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='matchmaking_prefs'
    )
    
    # Enable/Disable
    enabled = models.BooleanField(
        default=True,
        help_text="Accept matchmaking/bounty challenges"
    )
    
    # Game Filters
    games_enabled = models.JSONField(
        default=list,
        blank=True,
        help_text="List of game slugs enabled for matchmaking (e.g., ['valorant', 'cs2'])"
    )
    preferred_modes = models.JSONField(
        default=list,
        blank=True,
        help_text="Preferred game modes (e.g., ['ranked', '1v1', 'team'])"
    )
    
    # Bounty Filters
    min_bounty = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum bounty amount (DC) to consider"
    )
    max_bounty = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum bounty amount (DC) - for risk management"
    )
    auto_accept = models.BooleanField(
        default=False,
        help_text="Auto-accept challenges meeting criteria"
    )
    auto_reject_below_min = models.BooleanField(
        default=False,
        help_text="Auto-reject challenges below min_bounty"
    )
    
    # Skill/Rank Filters
    region_lock = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Only accept challenges from specific region (empty = any)"
    )
    skill_range_min = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum skill rating of opponents"
    )
    skill_range_max = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum skill rating of opponents"
    )
    
    # Team Bounties
    allow_team_bounties = models.BooleanField(
        default=True,
        help_text="Accept team vs team bounty challenges"
    )
    
    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_profile_matchmaking_preferences'
        verbose_name = 'Matchmaking Preferences'
        verbose_name_plural = 'Matchmaking Preferences'
    
    def clean(self):
        """Validate matchmaking preferences"""
        # Rule: min_bounty <= max_bounty
        if (self.min_bounty is not None and self.max_bounty is not None 
            and self.min_bounty > self.max_bounty):
            raise ValidationError({
                'max_bounty': "Max bounty must be greater than or equal to min bounty"
            })
        
        # Rule: Bounty amounts must be non-negative
        if self.min_bounty is not None and self.min_bounty < 0:
            raise ValidationError({
                'min_bounty': "Minimum bounty cannot be negative"
            })
        if self.max_bounty is not None and self.max_bounty < 0:
            raise ValidationError({
                'max_bounty': "Maximum bounty cannot be negative"
            })
        
        # Rule: Skill range validation
        if (self.skill_range_min is not None and self.skill_range_max is not None 
            and self.skill_range_min > self.skill_range_max):
            raise ValidationError({
                'skill_range_max': "Max skill rating must be greater than or equal to min skill rating"
            })
        
        # Rule: Games enabled must be a list
        if not isinstance(self.games_enabled, list):
            raise ValidationError({
                'games_enabled': "Games enabled must be a list"
            })
        if not isinstance(self.preferred_modes, list):
            raise ValidationError({
                'preferred_modes': "Preferred modes must be a list"
            })
        
        # Rule: All game slugs must be valid and active
        from apps.games.models import Game
        if self.games_enabled:
            for game_slug in self.games_enabled:
                if not isinstance(game_slug, str):
                    raise ValidationError({
                        'games_enabled': f"Invalid game slug type: {type(game_slug).__name__}"
                    })
                try:
                    game = Game.objects.get(slug=game_slug)
                    if not game.is_active:
                        raise ValidationError({
                            'games_enabled': f"Game '{game_slug}' is not currently active"
                        })
                except Game.DoesNotExist:
                    raise ValidationError({
                        'games_enabled': f"Unknown game slug: '{game_slug}'"
                    })
    
    def __str__(self):
        return f"{self.user_profile.user.username} Matchmaking Prefs"
