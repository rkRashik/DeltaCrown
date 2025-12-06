"""
Player identity configuration for game-specific player IDs.
"""

from django.db import models
from django.core.validators import RegexValidator
import re


class GamePlayerIdentityConfig(models.Model):
    """
    Defines required player identity fields for a game.
    E.g., Valorant requires Riot ID, PUBG Mobile requires Character ID + UID.
    """
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='identity_configs'
    )
    
    # === FIELD CONFIGURATION ===
    field_name = models.CharField(
        max_length=50,
        help_text="Technical field name (e.g., 'riot_id', 'steam_id', 'uid')"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Human-readable name (e.g., 'Riot ID', 'Steam ID', 'Character ID')"
    )
    field_type = models.CharField(
        max_length=20,
        choices=[
            ('TEXT', 'Text'),
            ('NUMBER', 'Number'),
            ('EMAIL', 'Email'),
            ('URL', 'URL'),
        ],
        default='TEXT'
    )
    
    # === VALIDATION ===
    is_required = models.BooleanField(
        default=True,
        help_text="Is this field mandatory?"
    )
    validation_regex = models.CharField(
        max_length=500,
        blank=True,
        help_text="Regex pattern for validation (optional)"
    )
    validation_error_message = models.CharField(
        max_length=200,
        blank=True,
        help_text="Custom error message for validation failure"
    )
    min_length = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum character length"
    )
    max_length = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum character length"
    )
    
    # === DISPLAY ===
    placeholder = models.CharField(
        max_length=200,
        blank=True,
        help_text="Placeholder text for input field (e.g., 'PlayerName#1234')"
    )
    help_text = models.TextField(
        blank=True,
        help_text="Additional help text for users"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order (lower = shown first)"
    )
    
    # === METADATA ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games_player_identity_config'
        verbose_name = 'Player Identity Config'
        verbose_name_plural = 'Player Identity Configs'
        ordering = ['game', 'order']
        unique_together = [('game', 'field_name')]
    
    def __str__(self):
        return f"{self.game.name} - {self.display_name}"
    
    def validate_value(self, value):
        """
        Validate a player identity value against this config.
        
        Args:
            value: The value to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not value and self.is_required:
            return False, f"{self.display_name} is required"
        
        if not value:
            return True, None
        
        value_str = str(value)
        
        # Length validation
        if self.min_length and len(value_str) < self.min_length:
            return False, f"{self.display_name} must be at least {self.min_length} characters"
        
        if self.max_length and len(value_str) > self.max_length:
            return False, f"{self.display_name} must be at most {self.max_length} characters"
        
        # Regex validation
        if self.validation_regex:
            try:
                if not re.match(self.validation_regex, value_str):
                    error_msg = self.validation_error_message or f"{self.display_name} format is invalid"
                    return False, error_msg
            except re.error:
                # Invalid regex pattern - log error but don't fail validation
                pass
        
        return True, None
