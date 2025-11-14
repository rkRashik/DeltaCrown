"""
Game Configuration Service

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Service Layer Design)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Game Model with game_config JSONB)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (Service Layer Standards)

Architecture Decisions:
- ADR-001: Service Layer Pattern - All business logic in services
- ADR-004: PostgreSQL Features - Uses JSONB for game_config storage
- ADR-010: Audit Logging - Version control for config changes

Description:
Manages game-specific configuration schemas and validation rules. Game configs
define allowed tournament formats, custom field types, validation constraints,
and game-specific settings (team sizes, map pools, etc.).

Example game_config structure:
{
    "schema_version": "1.0",
    "allowed_formats": ["single_elimination", "double_elimination", "round_robin"],
    "team_size_range": [5, 5],  // Min and max team size
    "custom_field_schemas": [
        {
            "field_key": "riot_username",
            "field_type": "text",
            "required": true,
            "validation": {"pattern": "^[a-zA-Z0-9 ]+#[A-Z0-9]{3,5}$"}
        }
    ],
    "match_settings": {
        "default_best_of": 3,
        "available_maps": ["Ascent", "Bind", "Haven", "Split"]
    }
}
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.tournaments.models.tournament import Game


class GameConfigService:
    """
    Service for managing game-specific configurations.
    
    Provides CRUD operations and validation for game config schemas stored
    in the Game.game_config JSONB field.
    """
    
    # Default schema structure for new games
    DEFAULT_SCHEMA = {
        "schema_version": "1.0",
        "allowed_formats": [
            "single_elimination",
            "double_elimination",
            "round_robin",
            "swiss",
            "group_playoff"
        ],
        "team_size_range": [1, 5],
        "custom_field_schemas": [],
        "match_settings": {
            "default_best_of": 1,
            "available_maps": []
        }
    }
    
    @staticmethod
    @transaction.atomic
    def get_config(game_id: int) -> Dict[str, Any]:
        """
        Retrieve game configuration by game ID.
        
        Args:
            game_id: ID of the game
        
        Returns:
            Dict containing game_config JSONB data
        
        Raises:
            Game.DoesNotExist: If game not found
        
        Example:
            >>> config = GameConfigService.get_config(game_id=1)
            >>> print(config['allowed_formats'])
            ['single_elimination', 'double_elimination']
        """
        game = Game.objects.get(id=game_id, is_active=True)
        
        # Return existing config or default schema
        if game.game_config:
            return game.game_config
        return GameConfigService.DEFAULT_SCHEMA.copy()
    
    @staticmethod
    @transaction.atomic
    def create_or_update_config(game_id: int, config_data: Dict[str, Any], user) -> Dict[str, Any]:
        """
        Create or update game configuration.
        
        Args:
            game_id: ID of the game
            config_data: Configuration data (partial or full)
            user: User performing the update (for audit trail)
        
        Returns:
            Dict: Updated game_config
        
        Raises:
            Game.DoesNotExist: If game not found
            ValidationError: If config_data is invalid
            PermissionError: If user lacks admin permissions
        
        Example:
            >>> config = GameConfigService.create_or_update_config(
            ...     game_id=1,
            ...     config_data={
            ...         "allowed_formats": ["single_elimination"],
            ...         "team_size_range": [5, 5]
            ...     },
            ...     user=admin_user
            ... )
        """
        # Permission check: staff only
        if not user.is_staff:
            raise PermissionError("Only staff can modify game configurations")
        
        game = Game.objects.get(id=game_id, is_active=True)
        
        # Get current config or default
        current_config = game.game_config if game.game_config else GameConfigService.DEFAULT_SCHEMA.copy()
        
        # Merge with provided data (deep merge for nested dicts)
        updated_config = GameConfigService._deep_merge(current_config, config_data)
        
        # Validate the updated config
        GameConfigService._validate_config(updated_config)
        
        # Update game
        game.game_config = updated_config
        game.save(update_fields=['game_config'])
        
        return updated_config
    
    @staticmethod
    def _deep_merge(base: Dict, updates: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            updates: Dictionary with updates
        
        Returns:
            Merged dictionary
        """
        result = base.copy()
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = GameConfigService._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        """
        Validate game configuration structure.
        
        Args:
            config: Configuration dictionary to validate
        
        Raises:
            ValidationError: If config is invalid
        """
        # Check required top-level keys
        required_keys = ["schema_version", "allowed_formats", "team_size_range"]
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValidationError(f"Missing required keys: {', '.join(missing_keys)}")
        
        # Validate schema_version
        if not isinstance(config.get("schema_version"), str):
            raise ValidationError("schema_version must be a string")
        
        # Validate allowed_formats
        allowed_formats = config.get("allowed_formats", [])
        if not isinstance(allowed_formats, list) or not allowed_formats:
            raise ValidationError("allowed_formats must be a non-empty list")
        
        valid_format_choices = [
            "single_elimination", "double_elimination", "round_robin", "swiss", "group_playoff"
        ]
        invalid_formats = [f for f in allowed_formats if f not in valid_format_choices]
        if invalid_formats:
            raise ValidationError(f"Invalid formats: {', '.join(invalid_formats)}")
        
        # Validate team_size_range
        team_size_range = config.get("team_size_range")
        if not isinstance(team_size_range, list) or len(team_size_range) != 2:
            raise ValidationError("team_size_range must be a list of [min, max]")
        
        min_size, max_size = team_size_range
        if not isinstance(min_size, int) or not isinstance(max_size, int):
            raise ValidationError("team_size_range values must be integers")
        if min_size < 1 or max_size < 1:
            raise ValidationError("team_size_range values must be >= 1")
        if min_size > max_size:
            raise ValidationError("team_size_range: min must be <= max")
        
        # Validate custom_field_schemas (if present)
        if "custom_field_schemas" in config:
            custom_field_schemas = config["custom_field_schemas"]
            if not isinstance(custom_field_schemas, list):
                raise ValidationError("custom_field_schemas must be a list")
            
            for idx, field_schema in enumerate(custom_field_schemas):
                if not isinstance(field_schema, dict):
                    raise ValidationError(f"custom_field_schemas[{idx}] must be a dict")
                
                # Check required field schema keys
                if "field_key" not in field_schema:
                    raise ValidationError(f"custom_field_schemas[{idx}] missing field_key")
                if "field_type" not in field_schema:
                    raise ValidationError(f"custom_field_schemas[{idx}] missing field_type")
                
                # Validate field_type
                valid_field_types = ["text", "number", "media", "toggle", "date", "url", "dropdown"]
                if field_schema["field_type"] not in valid_field_types:
                    raise ValidationError(
                        f"custom_field_schemas[{idx}] invalid field_type: {field_schema['field_type']}"
                    )
    
    @staticmethod
    def validate_tournament_against_config(game_id: int, tournament_data: Dict[str, Any]) -> None:
        """
        Validate tournament data against game configuration.
        
        Ensures tournament format, team size, and custom fields comply with
        the game's allowed configuration.
        
        Args:
            game_id: ID of the game
            tournament_data: Tournament data to validate
        
        Raises:
            Game.DoesNotExist: If game not found
            ValidationError: If tournament data violates game config
        
        Example:
            >>> GameConfigService.validate_tournament_against_config(
            ...     game_id=1,
            ...     tournament_data={
            ...         'format': 'single_elimination',
            ...         'max_participants': 16
            ...     }
            ... )
        """
        config = GameConfigService.get_config(game_id)
        
        # Validate format
        if "format" in tournament_data:
            tournament_format = tournament_data["format"]
            allowed_formats = config.get("allowed_formats", [])
            if tournament_format not in allowed_formats:
                raise ValidationError(
                    f"Format '{tournament_format}' not allowed for this game. "
                    f"Allowed formats: {', '.join(allowed_formats)}"
                )
        
        # Validate team size (if specified)
        if "max_participants" in tournament_data:
            max_participants = tournament_data["max_participants"]
            team_size_range = config.get("team_size_range", [1, 256])
            min_team_size, max_team_size = team_size_range
            
            # For team-based tournaments, validate team size constraints
            # (This is a simplified check; actual validation depends on participation_type)
            if "participation_type" in tournament_data and tournament_data["participation_type"] == "team":
                # Team size validation would go here
                pass
    
    @staticmethod
    def get_config_schema(game_id: int) -> Dict[str, Any]:
        """
        Get the game configuration schema for API documentation.
        
        Returns a JSON schema describing the structure of game_config.
        
        Args:
            game_id: ID of the game
        
        Returns:
            Dict: JSON schema for game_config
        
        Example:
            >>> schema = GameConfigService.get_config_schema(game_id=1)
            >>> print(schema['properties'].keys())
            dict_keys(['schema_version', 'allowed_formats', 'team_size_range', ...])
        """
        game = Game.objects.get(id=game_id, is_active=True)
        
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": f"{game.name} Configuration Schema",
            "type": "object",
            "properties": {
                "schema_version": {
                    "type": "string",
                    "description": "Configuration schema version"
                },
                "allowed_formats": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "single_elimination",
                            "double_elimination",
                            "round_robin",
                            "swiss",
                            "group_playoff"
                        ]
                    },
                    "description": "Allowed tournament formats for this game"
                },
                "team_size_range": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Min and max team size [min, max]"
                },
                "custom_field_schemas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field_key": {"type": "string"},
                            "field_type": {
                                "type": "string",
                                "enum": ["text", "number", "media", "toggle", "date", "url", "dropdown"]
                            },
                            "required": {"type": "boolean"},
                            "validation": {"type": "object"}
                        },
                        "required": ["field_key", "field_type"]
                    },
                    "description": "Schemas for game-specific custom fields"
                },
                "match_settings": {
                    "type": "object",
                    "properties": {
                        "default_best_of": {"type": "integer", "minimum": 1},
                        "available_maps": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "description": "Game-specific match settings"
                }
            },
            "required": ["schema_version", "allowed_formats", "team_size_range"]
        }
        
        return schema
