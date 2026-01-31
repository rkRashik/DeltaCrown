"""
API Serializers for vNext Organization and Team creation.

These serializers validate incoming JSON payloads for organization and team
creation endpoints. They enforce business rules and prepare data for service
layer consumption.

Performance Considerations:
- Serializers perform lightweight validation only (no DB queries)
- Heavy validation deferred to service layer
- All game_id lookups cached at service layer

Security:
- All sensitive fields sanitized
- User-controlled branding fields limited to safe JSON structure
"""

from typing import Any, Dict, Optional
from rest_framework import serializers


class OrganizationBrandingSerializer(serializers.Serializer):
    """
    Organization branding data structure.
    
    Flexible schema allows frontend to add branding fields without
    backend changes. All fields are optional to support gradual rollout.
    """
    logo_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    banner_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    primary_color = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=7,
        help_text="Hex color code (e.g., #FF5733)"
    )
    secondary_color = serializers.CharField(required=False, allow_blank=True, max_length=7)
    tagline = serializers.CharField(required=False, allow_blank=True, max_length=200)
    website_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    
    def validate_primary_color(self, value: str) -> str:
        """Validate hex color format."""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Color must be hex format (e.g., #FF5733)")
        return value
    
    def validate_secondary_color(self, value: str) -> str:
        """Validate hex color format."""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Color must be hex format (e.g., #FF5733)")
        return value


class CreateOrganizationSerializer(serializers.Serializer):
    """
    Serializer for organization creation endpoint.
    
    POST /api/vnext/organizations/create/
    
    Fields:
        name: Organization display name (required, 3-100 chars)
        slug: URL-friendly identifier (optional, auto-generated if missing)
        branding: Optional branding configuration (logo, colors, etc.)
    
    Validation:
        - Name uniqueness checked at service layer (avoids race conditions)
        - Slug auto-generation handled by OrganizationService
        - Branding structure validated but values sanitized at service layer
    
    Example Payload:
        {
            "name": "Team Liquid",
            "slug": "team-liquid",
            "branding": {
                "logo_url": "https://cdn.example.com/logo.png",
                "primary_color": "#0A4D92"
            }
        }
    """
    name = serializers.CharField(
        required=True,
        min_length=3,
        max_length=100,
        help_text="Organization display name"
    )
    slug = serializers.SlugField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="URL-friendly identifier (auto-generated if omitted)"
    )
    branding = OrganizationBrandingSerializer(required=False, allow_null=True)
    
    def validate_name(self, value: str) -> str:
        """Validate organization name."""
        # Strip whitespace
        value = value.strip()
        
        # Check for prohibited patterns
        if value.lower() in ['admin', 'api', 'vnext', 'system']:
            raise serializers.ValidationError(
                "This organization name is reserved.",
                code="reserved_name"
            )
        
        return value
    
    def validate_slug(self, value: Optional[str]) -> Optional[str]:
        """Validate slug format."""
        if value:
            value = value.strip().lower()
            
            # Check for prohibited patterns
            if value in ['admin', 'api', 'vnext', 'system', 'create', 'new']:
                raise serializers.ValidationError(
                    "This slug is reserved.",
                    code="reserved_slug"
                )
        
        return value


class TeamBrandingSerializer(serializers.Serializer):
    """
    Team branding data structure.
    
    Inherits from organization branding if team is org-owned, but can
    override individual fields.
    """
    logo_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    banner_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    primary_color = serializers.CharField(required=False, allow_blank=True, max_length=7)
    secondary_color = serializers.CharField(required=False, allow_blank=True, max_length=7)
    tagline = serializers.CharField(required=False, allow_blank=True, max_length=200)
    
    def validate_primary_color(self, value: str) -> str:
        """Validate hex color format."""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Color must be hex format (e.g., #FF5733)")
        return value
    
    def validate_secondary_color(self, value: str) -> str:
        """Validate hex color format."""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Color must be hex format (e.g., #FF5733)")
        return value


class CreateTeamSerializer(serializers.Serializer):
    """
    Serializer for team creation endpoint.
    
    POST /api/vnext/teams/create/
    
    Fields:
        name: Team display name (required, 3-50 chars)
        game_id: Integer ID of game from legacy games table (required)
        organization_id: If provided, creates org-owned team (optional)
        region: Geographic region code (optional, e.g., "NA", "EU", "APAC")
        branding: Optional branding configuration
    
    Validation:
        - game_id existence checked at service layer (avoids extra query here)
        - organization_id existence + permissions checked at view layer
        - Org-owned teams require CEO/manager permission (checked in view)
        - Independent teams automatically set creator as owner
    
    Example Payload (Independent Team):
        {
            "name": "Cloud9 Blue",
            "game_id": 1,
            "region": "NA",
            "branding": {
                "logo_url": "https://cdn.example.com/c9.png",
                "primary_color": "#0A4D92"
            }
        }
    
    Example Payload (Org-Owned Team):
        {
            "name": "Team Liquid Academy",
            "game_id": 1,
            "organization_id": 42,
            "region": "NA"
        }
    """
    name = serializers.CharField(
        required=True,
        min_length=3,
        max_length=50,
        help_text="Team display name"
    )
    game_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="Game ID from games table (deprecated - use game_slug)"
    )
    game_slug = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Game slug identifier (preferred over game_id)"
    )
    organization_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="Organization ID (for org-owned teams)"
    )
    region = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=50,
        help_text="Team home country/region (free-form, e.g. 'United States', 'BD')"
    )
    tag = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=5,
        help_text="Team tag/abbreviation (2-5 chars, optional)"
    )
    tagline = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        help_text="Team motto/tagline (optional)"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Team description/bio (optional)"
    )
    logo = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Team logo file upload (optional)"
    )
    banner = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Team banner file upload (optional)"
    )
    primary_color = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=7,
        help_text="Primary team color (hex format, e.g., #3B82F6)"
    )
    accent_color = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=7,
        help_text="Accent team color (hex format, e.g., #10B981)"
    )
    inherit_branding = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Inherit org branding (org-owned teams only)"
    )
    manager_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Email of user to invite as MANAGER (optional)"
    )
    branding = TeamBrandingSerializer(required=False, allow_null=True)
    
    def validate_name(self, value: str) -> str:
        """Validate team name."""
        value = value.strip()
        
        # Check for prohibited patterns
        if value.lower() in ['admin', 'api', 'system', 'test']:
            raise serializers.ValidationError(
                "This team name is reserved.",
                code="reserved_name"
            )
        
        return value
    
    def validate(self, data):
        """Cross-field validation - convert game_slug to game_id for vNext Team."""
        from apps.games.models import Game
        
        game_slug = data.get('game_slug')
        game_id = data.get('game_id')
        
        # Must provide either game_slug or game_id
        if not game_slug and not game_id:
            raise serializers.ValidationError({
                'game': 'Either game_slug or game_id is required.'
            })
        
        # If game_slug provided, resolve to game_id for vNext Team.game_id (IntegerField)
        if game_slug:
            try:
                game = Game.objects.get(slug=game_slug, is_active=True)
                # vNext Team uses game_id IntegerField, not game CharField
                data['game_id'] = game.id
                data['game_slug'] = game_slug  # Keep slug for reference
            except Game.DoesNotExist:
                raise serializers.ValidationError({
                    'game_slug': 'Invalid game selected.'
                })
        
        return data
