"""
Game Configuration API Serializers

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.2)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Game Model)

Description:
DRF serializers for game configuration CRUD operations via REST API.
Provides read-only config viewing and staff-only updates with validation.

Architecture Decisions:
- ADR-001: Service Layer Pattern - Delegates to GameConfigService
- ADR-004: PostgreSQL JSONB - Serializes game_config field
"""

from rest_framework import serializers
from apps.tournaments.models.tournament import Game
from apps.tournaments.services.game_config_service import GameConfigService


class GameConfigSerializer(serializers.Serializer):
    """
    Read-only serializer for game configuration.
    
    Returns the full game_config JSONB or default schema.
    
    Example response:
    {
        "schema_version": "1.0",
        "allowed_formats": ["single_elimination", "double_elimination"],
        "team_size_range": [1, 5],
        "custom_field_schemas": [],
        "match_settings": {"default_best_of": 1, "available_maps": []}
    }
    """
    schema_version = serializers.CharField(read_only=True)
    allowed_formats = serializers.ListField(child=serializers.CharField(), read_only=True)
    team_size_range = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    custom_field_schemas = serializers.ListField(child=serializers.DictField(), read_only=True)
    match_settings = serializers.DictField(read_only=True)
    
    def to_representation(self, instance):
        """
        Get game config via service layer.
        
        Args:
            instance: Game model instance
        
        Returns:
            dict: Game configuration
        """
        config = GameConfigService.get_config(instance.id)
        return config


class GameConfigUpdateSerializer(serializers.Serializer):
    """
    Write-only serializer for updating game configuration.
    
    Accepts partial updates that will be deep-merged into existing config.
    Staff-only via permission checks in view.
    
    Example request body:
    {
        "allowed_formats": ["single_elimination", "double_elimination"],
        "team_size_range": [5, 5],
        "match_settings": {
            "default_best_of": 3,
            "available_maps": ["Ascent", "Bind", "Haven"]
        }
    }
    """
    schema_version = serializers.CharField(required=False, allow_blank=False)
    allowed_formats = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False
    )
    team_size_range = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        min_length=2,
        max_length=2
    )
    custom_field_schemas = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    match_settings = serializers.DictField(required=False)
    
    def validate(self, attrs):
        """
        Validate config data via service layer.
        
        Args:
            attrs: Serialized data
        
        Returns:
            dict: Validated data
        
        Raises:
            ValidationError: If config is invalid
        """
        # Service layer validation will be called in view's perform_update
        return attrs
    
    def update(self, instance, validated_data):
        """
        Update game config via service layer.
        
        Args:
            instance: Game model instance
            validated_data: Validated config data
        
        Returns:
            Game: Updated game instance
        """
        user = self.context['request'].user
        GameConfigService.create_or_update_config(
            game_id=instance.id,
            config_data=validated_data,
            user=user
        )
        instance.refresh_from_db()
        return instance


class GameConfigSchemaSerializer(serializers.Serializer):
    """
    Serializer for game configuration JSON Schema.
    
    Returns JSON Schema (draft-07) describing the structure of game_config.
    Used for API documentation and client-side validation.
    
    Example response:
    {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Valorant Configuration Schema",
        "type": "object",
        "properties": {
            "schema_version": {"type": "string"},
            "allowed_formats": {"type": "array", "items": {"type": "string"}},
            ...
        },
        "required": ["schema_version", "allowed_formats", "team_size_range"]
    }
    """
    def to_representation(self, instance):
        """
        Get JSON Schema via service layer.
        
        Args:
            instance: Game model instance
        
        Returns:
            dict: JSON Schema for game config
        """
        return GameConfigService.get_config_schema(instance.id)
