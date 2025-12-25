# apps/user_profile/models/game_passport_schema.py
"""
Game Passport Schema Model

Defines per-game identity field requirements, region/rank/role choices,
and normalization rules. This model serves as the configuration layer
that makes Game Passports dynamic based on the selected game.

Architecture:
- One schema per Game (ForeignKey to apps.games.models.Game)
- Stores identity field names (e.g., riot_name + tagline for Valorant)
- Stores allowed region/rank/role choices as JSON
- Defines normalization rules (case folding, stripping, etc.)
"""

from django.db import models
from django.core.exceptions import ValidationError
import json


class GamePassportSchema(models.Model):
    """
    Per-game passport field schema and validation rules.
    
    This model defines what fields are required for each game's
    passport and what choices are available for regions/ranks/roles.
    """
    
    # Link to Game (source of truth)
    game = models.OneToOneField(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='passport_schema',
        help_text="Game this schema applies to"
    )
    
    # Identity Fields Configuration
    identity_fields = models.JSONField(
        default=dict,
        help_text="""
        Required identity fields for this game.
        Format: {
            "riot_name": {"label": "Riot ID", "required": True, "max_length": 50},
            "tagline": {"label": "Tagline", "required": True, "max_length": 5}
        }
        """
    )
    
    identity_format = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Format template (e.g., '{riot_name}#{tagline}' for Riot games)"
    )
    
    identity_key_format = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Normalization format for uniqueness check (e.g., '{riot_name_lower}#{tagline_lower}')"
    )
    
    # Region Choices
    region_choices = models.JSONField(
        default=list,
        help_text="""
        Allowed region choices for this game.
        Format: [
            {"value": "NA", "label": "North America"},
            {"value": "EU", "label": "Europe"}
        ]
        """
    )
    region_required = models.BooleanField(
        default=False,
        help_text="Whether region selection is mandatory"
    )
    
    # Role Choices
    role_choices = models.JSONField(
        default=list,
        help_text="""
        Available role choices for this game.
        Format: [
            {"value": "duelist", "label": "Duelist"},
            {"value": "controller", "label": "Controller"}
        ]
        """
    )
    
    # Rank System Configuration
    rank_system = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Rank system identifier (e.g., 'valorant_competitive', 'dota2_mmr')"
    )
    rank_choices = models.JSONField(
        default=list,
        help_text="""
        Available rank choices for this game.
        Format: [
            {"value": "iron", "label": "Iron", "tier": 1},
            {"value": "bronze", "label": "Bronze", "tier": 2}
        ]
        """
    )
    
    # Validation Rules
    normalization_rules = models.JSONField(
        default=dict,
        help_text="""
        Rules for normalizing identity values.
        Format: {
            "riot_name": {"lowercase": true, "strip": true, "max_length": 50},
            "tagline": {"lowercase": true, "strip": true, "max_length": 5}
        }
        """
    )
    
    # Platform-Specific Settings
    platform_specific = models.BooleanField(
        default=False,
        help_text="Whether identity is platform-specific (PC, Mobile, Console)"
    )
    requires_verification = models.BooleanField(
        default=False,
        help_text="Whether this game requires external verification (for Phase 2+)"
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Admin notes about this schema configuration"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Game Passport Schema"
        verbose_name_plural = "Game Passport Schemas"
        ordering = ['game__name']
    
    def __str__(self):
        return f"Schema: {self.game.name}"
    
    def get_identity_field_names(self):
        """Get list of identity field names"""
        return list(self.identity_fields.keys())
    
    def get_required_identity_fields(self):
        """Get list of required identity field names"""
        return [
            name for name, config in self.identity_fields.items()
            if config.get('required', False)
        ]
    
    def validate_identity_data(self, identity_data):
        """
        Validate identity data against schema.
        
        Args:
            identity_data: dict of field_name -> value
            
        Returns:
            tuple: (is_valid, errors_dict)
        """
        errors = {}
        
        # Check required fields
        for field_name in self.get_required_identity_fields():
            if not identity_data.get(field_name):
                field_config = self.identity_fields[field_name]
                label = field_config.get('label', field_name)
                errors[field_name] = f"{label} is required"
        
        # Check max lengths
        for field_name, value in identity_data.items():
            if field_name in self.identity_fields:
                field_config = self.identity_fields[field_name]
                max_length = field_config.get('max_length')
                if max_length and len(str(value)) > max_length:
                    label = field_config.get('label', field_name)
                    errors[field_name] = f"{label} must be {max_length} characters or less"
        
        return (len(errors) == 0, errors)
    
    def normalize_identity_data(self, identity_data):
        """
        Normalize identity data according to rules.
        
        Args:
            identity_data: dict of field_name -> value
            
        Returns:
            dict: normalized identity data
        """
        normalized = {}
        
        for field_name, value in identity_data.items():
            if field_name not in self.normalization_rules:
                normalized[field_name] = value
                continue
            
            rules = self.normalization_rules[field_name]
            normalized_value = str(value)
            
            if rules.get('strip', False):
                normalized_value = normalized_value.strip()
            
            if rules.get('lowercase', False):
                normalized_value = normalized_value.lower()
            
            if rules.get('uppercase', False):
                normalized_value = normalized_value.upper()
            
            normalized[field_name] = normalized_value
        
        return normalized
    
    def format_identity(self, identity_data):
        """
        Format identity data into display string.
        
        Args:
            identity_data: dict of field_name -> value
            
        Returns:
            str: formatted identity string
        """
        if not self.identity_format:
            # Fallback: join all values
            return " | ".join(str(v) for v in identity_data.values())
        
        try:
            return self.identity_format.format(**identity_data)
        except (KeyError, ValueError):
            # If formatting fails, fallback
            return " | ".join(f"{k}: {v}" for k, v in identity_data.items())
    
    def compute_identity_key(self, identity_data):
        """
        Compute normalized identity key for uniqueness checks.
        
        Args:
            identity_data: dict of field_name -> value (already normalized)
            
        Returns:
            str: identity key
        """
        if not self.identity_key_format:
            # Fallback: join all values with pipe
            return "|".join(str(v) for v in sorted(identity_data.items()))
        
        try:
            # Prepare data with _lower suffixes for format string
            format_data = {}
            for k, v in identity_data.items():
                format_data[k] = v
                format_data[f"{k}_lower"] = str(v).lower()
            
            return self.identity_key_format.format(**format_data)
        except (KeyError, ValueError):
            # If formatting fails, fallback
            return "|".join(f"{k}:{v}" for k, v in sorted(identity_data.items()))
    
    def validate_region(self, region_value):
        """Validate region against allowed choices"""
        if not region_value:
            return not self.region_required
        
        allowed_values = [choice['value'] for choice in self.region_choices]
        return region_value in allowed_values
    
    def validate_role(self, role_value):
        """Validate role against allowed choices"""
        if not role_value:
            return True  # Roles are typically optional
        
        allowed_values = [choice['value'] for choice in self.role_choices]
        return role_value in allowed_values
    
    def get_region_choices_for_form(self):
        """Get region choices in Django form format"""
        if not self.region_choices:
            return []
        return [(choice['value'], choice['label']) for choice in self.region_choices]
    
    def get_role_choices_for_form(self):
        """Get role choices in Django form format"""
        if not self.role_choices:
            return []
        return [(choice['value'], choice['label']) for choice in self.role_choices]
    
    def get_rank_choices_for_form(self):
        """Get rank choices in Django form format"""
        if not self.rank_choices:
            return []
        return [(choice['value'], choice['label']) for choice in self.rank_choices]
