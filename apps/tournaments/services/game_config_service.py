"""
Game Configuration Service

Provides centralized access to game configurations, fields, and roles.
Includes caching for performance optimization.
"""

from typing import Dict, List, Optional, Any
from django.core.cache import cache
from django.core.exceptions import ValidationError
from apps.tournaments.models import (
    GameConfiguration,
    GameFieldConfiguration,
    PlayerRoleConfiguration
)
from apps.tournaments.validators import get_validator


class GameConfigService:
    """
    Service for retrieving and managing game configurations.
    
    All methods are cached to minimize database queries.
    Cache is automatically invalidated when configurations change.
    """
    
    CACHE_TIMEOUT = 3600  # 1 hour
    CACHE_PREFIX = "game_config:"
    
    @classmethod
    def get_game_config(cls, game_code: str) -> Optional[GameConfiguration]:
        """
        Get game configuration by game code.
        
        Args:
            game_code: The game identifier (e.g., 'valorant', 'cs2')
            
        Returns:
            GameConfiguration object or None if not found
            
        Example:
            >>> game = GameConfigService.get_game_config('valorant')
            >>> print(f"{game.display_name}: {game.roster_description}")
            VALORANT: 5 starters + 2 subs
        """
        cache_key = f"{cls.CACHE_PREFIX}game:{game_code}"
        game = cache.get(cache_key)
        
        if game is None:
            try:
                game = GameConfiguration.objects.get(
                    game_code=game_code,
                    is_active=True
                )
                cache.set(cache_key, game, cls.CACHE_TIMEOUT)
            except GameConfiguration.DoesNotExist:
                return None
        
        return game
    
    @classmethod
    def get_field_configs(cls, game_code: str) -> List[GameFieldConfiguration]:
        """
        Get all active field configurations for a game.
        
        Args:
            game_code: The game identifier
            
        Returns:
            List of GameFieldConfiguration objects ordered by display_order
            
        Example:
            >>> fields = GameConfigService.get_field_configs('valorant')
            >>> for field in fields:
            ...     print(f"{field.field_label}: required={field.is_required}")
            Riot ID: required=True
            Discord ID: required=False
        """
        cache_key = f"{cls.CACHE_PREFIX}fields:{game_code}"
        fields = cache.get(cache_key)
        
        if fields is None:
            game = cls.get_game_config(game_code)
            if game is None:
                return []
            
            fields = list(game.get_field_configurations())
            cache.set(cache_key, fields, cls.CACHE_TIMEOUT)
        
        return fields
    
    @classmethod
    def get_role_configs(cls, game_code: str) -> List[PlayerRoleConfiguration]:
        """
        Get all active role configurations for a game.
        
        Args:
            game_code: The game identifier
            
        Returns:
            List of PlayerRoleConfiguration objects ordered by display_order
            
        Example:
            >>> roles = GameConfigService.get_role_configs('dota2')
            >>> for role in roles:
            ...     print(f"{role.role_name}: unique={role.is_unique}")
            Position 1 - Carry: unique=True
            Position 2 - Mid: unique=True
        """
        cache_key = f"{cls.CACHE_PREFIX}roles:{game_code}"
        roles = cache.get(cache_key)
        
        if roles is None:
            game = cls.get_game_config(game_code)
            if game is None:
                return []
            
            roles = list(game.get_role_configurations())
            cache.set(cache_key, roles, cls.CACHE_TIMEOUT)
        
        return roles
    
    @classmethod
    def get_full_config(cls, game_code: str) -> Optional[Dict[str, Any]]:
        """
        Get complete game configuration including game, fields, and roles.
        
        Args:
            game_code: The game identifier
            
        Returns:
            Dictionary with game info, fields, and roles, or None if game not found
            
        Example:
            >>> config = GameConfigService.get_full_config('valorant')
            >>> print(config['game']['display_name'])
            VALORANT
            >>> print(f"Fields: {len(config['fields'])}, Roles: {len(config['roles'])}")
            Fields: 2, Roles: 5
        """
        game = cls.get_game_config(game_code)
        if game is None:
            return None
        
        fields = cls.get_field_configs(game_code)
        roles = cls.get_role_configs(game_code)
        
        return {
            'game': cls._serialize_game(game),
            'fields': [cls._serialize_field(f) for f in fields],
            'roles': [cls._serialize_role(r) for r in roles]
        }
    
    @classmethod
    def get_all_games(cls, include_inactive: bool = False) -> List[GameConfiguration]:
        """
        Get all game configurations.
        
        Args:
            include_inactive: If True, include inactive games
            
        Returns:
            List of GameConfiguration objects
        """
        cache_key = f"{cls.CACHE_PREFIX}all_games:{include_inactive}"
        games = cache.get(cache_key)
        
        if games is None:
            queryset = GameConfiguration.objects.all()
            if not include_inactive:
                queryset = queryset.filter(is_active=True)
            
            games = list(queryset.order_by('display_name'))
            cache.set(cache_key, games, cls.CACHE_TIMEOUT)
        
        return games
    
    @classmethod
    def validate_field_value(cls, game_code: str, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a field value against its configuration.
        
        Uses game-specific validators when available, otherwise falls back
        to field configuration validation (regex patterns).
        
        Args:
            game_code: The game identifier
            field_name: The field name to validate
            value: The value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Example:
            >>> is_valid, error = GameConfigService.validate_field_value(
            ...     'valorant', 'riot_id', 'Player#1234'
            ... )
            >>> print(f"Valid: {is_valid}")
            Valid: True
        """
        # Try to use game-specific validator first
        validator = get_validator(field_name)
        if validator:
            return validator(value)
        
        # Fallback to field configuration validation
        fields = cls.get_field_configs(game_code)
        
        for field in fields:
            if field.field_name == field_name:
                return field.validate_value(value)
        
        return False, f"Field '{field_name}' not found for game '{game_code}'"
    
    @classmethod
    def validate_team_roles(cls, game_code: str, role_assignments: List[str]) -> tuple[bool, List[str]]:
        """
        Validate a team's role assignments.
        
        Args:
            game_code: The game identifier
            role_assignments: List of role codes assigned to team members
            
        Returns:
            Tuple of (is_valid, list_of_errors)
            
        Example:
            >>> is_valid, errors = GameConfigService.validate_team_roles(
            ...     'valorant', ['duelist', 'duelist', 'controller', 'sentinel', 'igl']
            ... )
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(error)
        """
        return PlayerRoleConfiguration.validate_team_roles(game_code, role_assignments)
    
    @classmethod
    def clear_cache(cls, game_code: Optional[str] = None):
        """
        Clear cached game configurations.
        
        Args:
            game_code: If provided, clear cache for specific game only.
                      If None, clear all game config caches.
        """
        if game_code:
            cache.delete(f"{cls.CACHE_PREFIX}game:{game_code}")
            cache.delete(f"{cls.CACHE_PREFIX}fields:{game_code}")
            cache.delete(f"{cls.CACHE_PREFIX}roles:{game_code}")
        else:
            # Clear all game config caches
            cache.delete_pattern(f"{cls.CACHE_PREFIX}*")
    
    # Serialization helpers
    
    @staticmethod
    def _serialize_game(game: GameConfiguration) -> Dict[str, Any]:
        """Serialize GameConfiguration to dictionary."""
        return {
            'game_code': game.game_code,
            'display_name': game.display_name,
            'icon': game.icon,
            'team_size': game.team_size,
            'sub_count': game.sub_count,
            'total_roster_size': game.total_roster_size,
            'roster_description': game.roster_description,
            'is_solo': game.is_solo,
            'is_team': game.is_team,
            'description': game.description,
        }
    
    @staticmethod
    def _serialize_field(field: GameFieldConfiguration) -> Dict[str, Any]:
        """Serialize GameFieldConfiguration to dictionary."""
        return {
            'field_name': field.field_name,
            'field_label': field.field_label,
            'field_type': field.field_type,
            'is_required': field.is_required,
            'validation_regex': field.validation_regex,
            'validation_error_message': field.validation_error_message,
            'min_length': field.min_length,
            'max_length': field.max_length,
            'placeholder': field.placeholder,
            'help_text': field.help_text,
            'display_order': field.display_order,
            'choices': field.choices,
            'show_condition': field.show_condition,
        }
    
    @staticmethod
    def _serialize_role(role: PlayerRoleConfiguration) -> Dict[str, Any]:
        """Serialize PlayerRoleConfiguration to dictionary."""
        return {
            'role_code': role.role_code,
            'role_name': role.role_name,
            'role_abbreviation': role.role_abbreviation,
            'is_unique': role.is_unique,
            'is_required': role.is_required,
            'max_per_team': role.max_per_team,
            'description': role.description,
            'display_order': role.display_order,
            'icon': role.icon,
        }
