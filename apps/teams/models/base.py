# apps/teams/models/base.py
"""
Abstract base models for game-specific team management.

These base classes provide common functionality across all games
while allowing game-specific customization through inheritance.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

from ..game_config import (
    get_game_config,
    get_max_roster_size,
    get_min_roster_size,
    validate_role_for_game,
    GAME_CHOICES,
)


class BaseTeam(models.Model):
    """
    Abstract base model for all game-specific teams.
    
    Provides common fields and behavior that all team types share,
    while allowing game-specific models to extend with their own fields.
    """
    
    # Core identity fields
    name = models.CharField(
        max_length=100,
        help_text="Team name"
    )
    tag = models.CharField(
        max_length=10,
        help_text="Team tag/abbreviation (2-10 characters)"
    )
    slug = models.SlugField(
        max_length=64,
        blank=True,
        help_text="URL-friendly identifier (auto-generated)"
    )
    
    # Description
    description = models.TextField(
        max_length=500,
        blank=True,
        help_text="Brief team description"
    )
    
    # Media
    logo = models.ImageField(
        upload_to="teams/logos/",
        blank=True,
        null=True,
        help_text="Team logo image"
    )
    banner_image = models.ImageField(
        upload_to="teams/banners/",
        blank=True,
        null=True,
        help_text="Team banner image"
    )
    
    # Location
    region = models.CharField(
        max_length=100,
        blank=True,
        help_text="Geographic region (e.g., NA, EU, SEA)"
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Country"
    )
    
    # Team leadership
    captain = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_captain_teams",
        help_text="Team captain (must be a team member)"
    )
    
    # Social links
    twitter = models.URLField(blank=True, help_text="Twitter profile URL")
    instagram = models.URLField(blank=True, help_text="Instagram profile URL")
    discord = models.URLField(blank=True, help_text="Discord server URL")
    youtube = models.URLField(blank=True, help_text="YouTube channel URL")
    twitch = models.URLField(blank=True, help_text="Twitch channel URL")
    website = models.URLField(blank=True, help_text="Official website URL")
    
    # Status and visibility
    is_active = models.BooleanField(
        default=True,
        help_text="Team is active and visible"
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Team profile is publicly visible"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Officially verified team"
    )
    is_recruiting = models.BooleanField(
        default=True,
        help_text="Team is actively recruiting"
    )
    
    # Team settings
    allow_join_requests = models.BooleanField(
        default=True,
        help_text="Allow users to request to join"
    )
    require_approval = models.BooleanField(
        default=True,
        help_text="Captain must approve new members"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Game association (must be set by concrete models)
    game = models.CharField(
        max_length=20,
        choices=GAME_CHOICES,
        help_text="Game this team competes in"
    )
    
    class Meta:
        abstract = True
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.name} ({self.tag})"
    
    def clean(self):
        """Validate team data before saving."""
        super().clean()
        
        # Validate name
        if self.name:
            self.name = self.name.strip()
            if len(self.name) < 3:
                raise ValidationError({"name": "Team name must be at least 3 characters"})
            if len(self.name) > 100:
                raise ValidationError({"name": "Team name cannot exceed 100 characters"})
        
        # Validate tag
        if self.tag:
            self.tag = self.tag.strip().upper()
            if len(self.tag) < 2:
                raise ValidationError({"tag": "Team tag must be at least 2 characters"})
            if len(self.tag) > 10:
                raise ValidationError({"tag": "Team tag cannot exceed 10 characters"})
            
            import re
            if not re.match(r'^[A-Z0-9]+$', self.tag):
                raise ValidationError({"tag": "Team tag can only contain letters and numbers"})
        
        # Auto-generate slug if empty
        if not self.slug and self.name:
            self.slug = slugify(self.name)[:60]
        
        # Validate captain is a member (if set)
        if self.captain and self.pk:
            from .membership import BasePlayerMembership
            # Check if captain is an active member
            if not self.get_memberships().filter(
                profile=self.captain,
                status='ACTIVE'
            ).exists():
                # This will be handled by ensure_captain_membership
                pass
    
    def save(self, *args, **kwargs):
        """Save team and ensure captain membership."""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Ensure captain is a member
        if self.captain:
            try:
                self.ensure_captain_membership()
            except Exception:
                pass  # Fail gracefully during initial creation
    
    def get_memberships(self):
        """Get all memberships for this team. Must be implemented by concrete models."""
        raise NotImplementedError("Concrete models must implement get_memberships()")
    
    def ensure_captain_membership(self):
        """Ensure captain has an active membership."""
        if not self.captain or not self.pk:
            return
        
        memberships = self.get_memberships()
        membership_model = memberships.model
        
        membership, created = membership_model.objects.get_or_create(
            team=self,
            profile=self.captain,
            defaults={
                "role": "Captain",
                "status": "ACTIVE",
                "is_captain": True,
            }
        )
        
        if not created and not membership.is_captain:
            membership.is_captain = True
            membership.role = "Captain"
            membership.status = "ACTIVE"
            membership.save()
    
    def get_active_members_count(self):
        """Get count of active team members."""
        return self.get_memberships().filter(status='ACTIVE').count()
    
    def get_max_roster_size(self):
        """Get maximum roster size for this team's game."""
        if not self.game:
            return 10  # Default fallback
        return get_max_roster_size(self.game)
    
    def get_min_roster_size(self):
        """Get minimum roster size for this team's game."""
        if not self.game:
            return 1  # Default fallback
        return get_min_roster_size(self.game)
    
    def can_add_member(self):
        """Check if team can add more members."""
        return self.get_active_members_count() < self.get_max_roster_size()
    
    def is_roster_complete(self):
        """Check if team has minimum required members."""
        return self.get_active_members_count() >= self.get_min_roster_size()
    
    def has_member(self, profile):
        """Check if profile is an active member."""
        return self.get_memberships().filter(
            profile=profile,
            status='ACTIVE'
        ).exists()
    
    def is_captain_user(self, profile):
        """Check if profile is the team captain."""
        return self.captain == profile
    
    @property
    def display_name(self):
        """Get formatted display name."""
        if self.tag and self.name:
            return f"{self.name} [{self.tag}]"
        return self.name or f"Team #{self.pk}"
    
    @property
    def logo_url(self):
        """Get logo URL or None."""
        return self.logo.url if self.logo else None
    
    @property
    def banner_url(self):
        """Get banner URL or None."""
        return self.banner_image.url if self.banner_image else None


class BasePlayerMembership(models.Model):
    """
    Abstract base model for player membership in teams.
    
    Represents a player's role and status within a team,
    with game-specific role validation.
    """
    
    # Player reference
    profile = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="%(class)s_memberships",
        help_text="Player profile"
    )
    
    # Role and position
    role = models.CharField(
        max_length=50,
        help_text="Player role (e.g., Duelist, IGL, Carry)"
    )
    secondary_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Secondary/backup role"
    )
    
    # Player status
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("SUBSTITUTE", "Substitute"),
        ("INACTIVE", "Inactive"),
        ("PENDING", "Pending"),
        ("REMOVED", "Removed"),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        help_text="Membership status"
    )
    
    # Leadership flag
    is_captain = models.BooleanField(
        default=False,
        help_text="Is team captain"
    )
    is_starter = models.BooleanField(
        default=True,
        help_text="Starting lineup member"
    )
    
    # Player-specific info
    in_game_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="In-game name (IGN)"
    )
    jersey_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Jersey/player number"
    )
    
    # Stats and performance
    games_played = models.PositiveIntegerField(
        default=0,
        help_text="Games played with team"
    )
    
    # Timestamps
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    
    # Game-specific data (JSON for flexibility)
    game_specific_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional game-specific player data"
    )
    
    class Meta:
        abstract = True
        ordering = ["-is_captain", "-is_starter", "role", "joined_at"]
    
    def __str__(self):
        captain_str = " (C)" if self.is_captain else ""
        return f"{self.profile.user.username} - {self.role}{captain_str}"
    
    def clean(self):
        """Validate membership data."""
        super().clean()
        
        # Get team's game
        team = getattr(self, 'team', None)
        if not team or not team.game:
            return  # Can't validate without game context
        
        # Validate role is allowed for this game
        if self.role and not validate_role_for_game(team.game, self.role):
            config = get_game_config(team.game)
            raise ValidationError({
                "role": f"Invalid role '{self.role}' for {config.name}. "
                        f"Valid roles: {', '.join(config.roles)}"
            })
        
        # Validate secondary role if set
        if self.secondary_role and not validate_role_for_game(team.game, self.secondary_role):
            config = get_game_config(team.game)
            raise ValidationError({
                "secondary_role": f"Invalid secondary role '{self.secondary_role}' for {config.name}."
            })
        
        # Validate roster size
        if self.status == 'ACTIVE' and not self.pk:
            # Check if team is at capacity
            active_count = team.get_memberships().filter(status='ACTIVE').count()
            max_size = team.get_max_roster_size()
            
            if active_count >= max_size:
                raise ValidationError(
                    f"Team roster is full ({active_count}/{max_size} members). "
                    f"Cannot add more active members."
                )
        
        # Validate starters count
        if self.is_starter and self.status == 'ACTIVE':
            config = get_game_config(team.game)
            starters_count = team.get_memberships().filter(
                status='ACTIVE',
                is_starter=True
            ).exclude(pk=self.pk).count()
            
            if starters_count >= config.max_starters:
                raise ValidationError(
                    f"Team already has maximum starters ({config.max_starters}). "
                    f"Set player as substitute instead."
                )
        
        # Validate unique IGN within team
        if self.in_game_name:
            team = getattr(self, 'team', None)
            if team:
                duplicate = team.get_memberships().filter(
                    in_game_name__iexact=self.in_game_name
                ).exclude(pk=self.pk).exists()
                
                if duplicate:
                    raise ValidationError({
                        "in_game_name": f"IGN '{self.in_game_name}' is already used by another team member."
                    })
    
    def save(self, *args, **kwargs):
        """Save membership with validation."""
        self.full_clean()
        
        # Auto-update left_at when status changes to REMOVED/INACTIVE
        if self.status in ['REMOVED', 'INACTIVE'] and not self.left_at:
            self.left_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        # If this member is marked as captain, update team captain
        if self.is_captain:
            team = getattr(self, 'team', None)
            if team and team.captain != self.profile:
                team.captain = self.profile
                team.save(update_fields=['captain'])
    
    @property
    def display_name(self):
        """Get display name with IGN if available."""
        if self.in_game_name:
            return f"{self.profile.user.username} ({self.in_game_name})"
        return self.profile.user.username
    
    @property
    def status_display(self):
        """Get formatted status display."""
        status_map = {
            "ACTIVE": "✓ Active",
            "SUBSTITUTE": "⚠ Substitute",
            "INACTIVE": "✗ Inactive",
            "PENDING": "⏳ Pending",
            "REMOVED": "✗ Removed",
        }
        return status_map.get(self.status, self.status)
