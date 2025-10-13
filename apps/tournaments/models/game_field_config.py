"""
Game Field Configuration Model

Stores dynamic form field definitions for each game (Riot ID, Steam ID, MLBB User ID, etc.).
This enables automatic form generation based on game requirements.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class GameFieldConfiguration(models.Model):
    """
    Defines custom form fields required for each game's registration.
    
    Each game can have unique fields (e.g., Riot ID for Valorant, Steam ID for CS2).
    Supports validation rules, help text, and conditional display.
    
    Example:
        Valorant: Riot ID (format: Username#TAG), Discord ID (optional)
        CS2: Steam ID (numeric), Steam Profile URL (optional)
    """
    
    FIELD_TYPES = [
        ('text', _('Text Input')),
        ('email', _('Email Input')),
        ('tel', _('Phone Number')),
        ('number', _('Number Input')),
        ('url', _('URL Input')),
        ('select', _('Dropdown Select')),
        ('textarea', _('Text Area')),
        ('file', _('File Upload')),
    ]
    
    # Relationship
    game = models.ForeignKey(
        'GameConfiguration',
        on_delete=models.CASCADE,
        related_name='field_configurations',
        help_text=_("The game this field belongs to")
    )
    
    # Field identification
    field_name = models.CharField(
        max_length=100,
        help_text=_("Internal field name (e.g., 'riot_id', 'steam_id', 'discord_id')")
    )
    
    field_label = models.CharField(
        max_length=200,
        help_text=_("Label displayed to user (e.g., 'Riot ID', 'Steam ID')")
    )
    
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPES,
        default='text',
        help_text=_("HTML input type for the field")
    )
    
    # Validation
    is_required = models.BooleanField(
        default=True,
        help_text=_("Is this field mandatory?")
    )
    
    validation_regex = models.CharField(
        max_length=500,
        blank=True,
        help_text=_("Regular expression for validation (e.g., '^[a-zA-Z0-9]+#[a-zA-Z0-9]+$' for Riot ID)")
    )
    
    validation_error_message = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Error message to show when validation fails")
    )
    
    min_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Minimum character length")
    )
    
    max_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum character length")
    )
    
    # Display
    placeholder = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Placeholder text (e.g., 'Username#1234')")
    )
    
    help_text = models.TextField(
        blank=True,
        help_text=_("Instructional text displayed below the field")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which fields appear (lower numbers first)")
    )
    
    # For select/dropdown fields
    choices = models.JSONField(
        null=True,
        blank=True,
        help_text=_("JSON array of choices for select fields: [{\"value\": \"pc\", \"label\": \"PC\"}, ...]")
    )
    
    # Conditional display
    show_condition = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("JavaScript condition for showing this field (e.g., 'tournament_type == \"team\"')")
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_("Is this field currently active?")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournaments_game_field_configuration'
        verbose_name = _("Game Field Configuration")
        verbose_name_plural = _("Game Field Configurations")
        ordering = ['game', 'display_order', 'field_name']
        unique_together = [['game', 'field_name']]
        indexes = [
            models.Index(fields=['game', 'is_active']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        required = "*" if self.is_required else ""
        return f"{self.game.display_name} - {self.field_label}{required}"
    
    def clean(self):
        """Validate model constraints."""
        super().clean()
        
        # Validate regex if provided
        if self.validation_regex:
            import re
            try:
                re.compile(self.validation_regex)
            except re.error as e:
                raise ValidationError({
                    'validation_regex': _(f"Invalid regular expression: {e}")
                })
        
        # Select fields must have choices
        if self.field_type == 'select' and not self.choices:
            raise ValidationError({
                'choices': _("Select fields must have choices defined.")
            })
        
        # Min/max length validation
        if self.min_length and self.max_length:
            if self.min_length > self.max_length:
                raise ValidationError(
                    _("Minimum length cannot be greater than maximum length.")
                )
    
    def get_choices_list(self):
        """
        Return choices as a list of tuples for Django forms.
        
        Returns:
            List of (value, label) tuples
        """
        if not self.choices:
            return []
        
        return [(choice['value'], choice['label']) for choice in self.choices]
    
    def validate_value(self, value):
        """
        Validate a field value against this configuration.
        
        Args:
            value: The value to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Required check
        if self.is_required and not value:
            return False, f"{self.field_label} is required."
        
        if not value:
            return True, None
        
        value_str = str(value)
        
        # Length checks
        if self.min_length and len(value_str) < self.min_length:
            return False, f"{self.field_label} must be at least {self.min_length} characters."
        
        if self.max_length and len(value_str) > self.max_length:
            return False, f"{self.field_label} must not exceed {self.max_length} characters."
        
        # Regex validation
        if self.validation_regex:
            import re
            pattern = re.compile(self.validation_regex)
            if not pattern.match(value_str):
                error_msg = self.validation_error_message or f"{self.field_label} format is invalid."
                return False, error_msg
        
        return True, None
