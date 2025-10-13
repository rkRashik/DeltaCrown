"""
Game Configuration Model

Stores metadata and configuration for each supported game (Valorant, CS2, Dota 2, etc.).
This enables dynamic tournament registration forms based on game requirements.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class GameConfiguration(models.Model):
    """
    Stores configuration for each supported esports game.
    
    Defines team sizes, registration requirements, and whether the game
    supports solo and/or team tournaments.
    
    Example:
        Valorant: 5 starters + 2 subs, supports team tournaments
        eFootball: 1 player solo OR 2 starters + 1 sub for team
    """
    
    # Game identification
    game_code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Unique identifier for the game (e.g., 'valorant', 'cs2', 'dota2')")
    )
    
    display_name = models.CharField(
        max_length=100,
        help_text=_("Human-readable game name (e.g., 'VALORANT', 'Counter-Strike 2')")
    )
    
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("CSS icon class or image filename (e.g., 'fas fa-crosshairs', 'valorant.png')")
    )
    
    # Team composition
    team_size = models.PositiveIntegerField(
        default=5,
        help_text=_("Number of starting players required for team tournaments")
    )
    
    sub_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of substitute players allowed")
    )
    
    # Tournament type support
    is_solo = models.BooleanField(
        default=False,
        help_text=_("Does this game support solo (1v1) tournaments?")
    )
    
    is_team = models.BooleanField(
        default=True,
        help_text=_("Does this game support team tournaments?")
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_("Is this game currently available for tournament creation?")
    )
    
    # Metadata
    description = models.TextField(
        blank=True,
        help_text=_("Brief description or notes about the game")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournaments_game_configuration'
        verbose_name = _("Game Configuration")
        verbose_name_plural = _("Game Configurations")
        ordering = ['display_name']
        indexes = [
            models.Index(fields=['game_code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.display_name} ({self.game_code})"
    
    def clean(self):
        """Validate model constraints."""
        super().clean()
        
        # At least one tournament type must be supported
        if not self.is_solo and not self.is_team:
            raise ValidationError(
                _("Game must support at least one tournament type (solo or team).")
            )
        
        # Team size validation
        if self.is_team and self.team_size < 1:
            raise ValidationError(
                _("Team size must be at least 1 for team-based games.")
            )
        
        # Sub count validation
        if self.sub_count < 0:
            raise ValidationError(
                _("Substitute count cannot be negative.")
            )
    
    @property
    def total_roster_size(self):
        """Total players including subs."""
        return self.team_size + self.sub_count
    
    @property
    def roster_description(self):
        """Human-readable roster description."""
        if self.is_solo and not self.is_team:
            return "Solo (1 player)"
        elif self.is_team and not self.is_solo:
            if self.sub_count > 0:
                return f"{self.team_size} starters + {self.sub_count} subs"
            else:
                return f"{self.team_size} players"
        else:
            # Both solo and team supported
            if self.sub_count > 0:
                return f"Solo or Team ({self.team_size}+{self.sub_count})"
            else:
                return f"Solo or Team ({self.team_size})"
    
    def get_field_configurations(self):
        """Get all field configurations for this game."""
        return self.field_configurations.filter(is_active=True).order_by('display_order')
    
    def get_role_configurations(self):
        """Get all role configurations for this game."""
        return self.role_configurations.filter(is_active=True).order_by('display_order')
