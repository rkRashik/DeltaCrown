"""
Game service adapter for cross-domain game configuration access.

Provides TournamentOps with access to game configs, identity field definitions,
and validation rules without direct imports from apps.games.models.

This adapter reflects the game configuration system defined in Phase 2:
- GamePlayerIdentityConfig (Riot ID, Steam ID, etc.)
- GameTournamentConfig (supported formats, scoring)
- GameScoringRule (points calculation)

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.1 & Phase 2
"""

from typing import Protocol, runtime_checkable, Dict, Any, List

from .base import BaseAdapter


@runtime_checkable
class GameAdapterProtocol(Protocol):
    """
    Protocol defining the interface for game configuration access.
    
    All methods must return DTOs (not ORM models) once DTOs are implemented.
    
    TODO: Replace Dict[str, Any] with GameDTO, GameIdentityConfigDTO, etc.
          once tournament_ops/dtos/ is implemented (Epic 1.3).
    """
    
    def get_game_config(self, game_slug: str) -> Dict[str, Any]:
        """
        Fetch complete game configuration by slug.
        
        Args:
            game_slug: Game identifier (e.g., 'valorant', 'csgo')
            
        Returns:
            Dict containing game config (name, team_size, formats, etc.)
            
        Raises:
            GameNotFoundError: If game does not exist
            
        TODO: Return GameDTO instead of dict.
        """
        ...
    
    def get_identity_fields(self, game_slug: str) -> List[Dict[str, Any]]:
        """
        Get player identity field configurations for a game.
        
        Returns identity fields like Riot ID, Steam ID, Epic ID, etc.
        with their validation rules, display names, and required status.
        
        Args:
            game_slug: Game identifier
            
        Returns:
            List of dicts containing identity field configs
            Example: [{'field_name': 'riot_id', 'display_name': 'Riot ID',
                       'is_required': True, 'validation_regex': '...'}]
            
        TODO: Return List[GameIdentityConfigDTO] instead of list of dicts.
        
        Reference: GamePlayerIdentityConfig model (Phase 2, Epic 2.1)
        """
        ...
    
    def validate_game_identity(
        self,
        game_slug: str,
        identity_payload: Dict[str, Any]
    ) -> bool:
        """
        Validate game identity data against game's identity field rules.
        
        Args:
            game_slug: Game identifier
            identity_payload: Dict mapping field names to values
                             Example: {'riot_id': 'Player#NA1'}
            
        Returns:
            bool: True if valid, False otherwise
            
        Reference: GameValidationService (Phase 2, Epic 2.2)
        """
        ...
    
    def get_supported_formats(self, game_slug: str) -> List[str]:
        """
        Get list of tournament formats supported by this game.
        
        Args:
            game_slug: Game identifier
            
        Returns:
            List of format identifiers (e.g., ['single_elimination', 'round_robin'])
            
        Reference: GameTournamentConfig model (Phase 2, Epic 2.1)
        """
        ...
    
    def get_scoring_rules(self, game_slug: str) -> Dict[str, Any]:
        """
        Get scoring rules configuration for a game.
        
        Args:
            game_slug: Game identifier
            
        Returns:
            Dict containing scoring rule config
            
        TODO: Return GameScoringRuleDTO instead of dict.
        
        Reference: GameScoringRule model (Phase 2, Epic 2.1)
        """
        ...


class GameAdapter(BaseAdapter):
    """
    Concrete game adapter implementation.
    
    This adapter is the ONLY way for TournamentOps to access game configurations.
    It must never return ORM models directly - only DTOs.
    
    Implementation Note:
    - Phase 1, Epic 1.1: Create adapter skeleton (this file)
    - Phase 1, Epic 1.3: Wire up DTOs
    - Phase 2, Epic 2.1: Wire to actual Game config models
    - Phase 1, Epic 1.1: Add unit tests with mocked game service
    
    Reference: CLEANUP_AND_TESTING_PART_6.md - §4.1 (Game Model Migration)
    """
    
    def get_game_config(self, game_slug: str) -> Dict[str, Any]:
        """
        Fetch complete game configuration by slug.
        
        Uses GameService to fetch game and returns basic config dict.
        
        TODO: Return GameDTO instead of dict once GameDTO is created.
        
        Raises:
            GameConfigNotFoundError: If game does not exist
        """
        from apps.games.services.game_service import GameService
        from apps.tournament_ops.exceptions import GameConfigNotFoundError
        
        try:
            game = GameService.get_game(game_slug)
            if not game:
                raise GameConfigNotFoundError(f"Game '{game_slug}' not found")
            
            # Return basic config dict
            # TODO: Convert to GameDTO.from_model(game) when GameDTO exists
            return {
                'id': game.id,
                'slug': game.slug,
                'name': game.name,
                'description': game.description,
                'is_active': game.is_active,
            }
        except Exception as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise GameConfigNotFoundError(f"Game '{game_slug}' not found")
            raise
    
    def get_identity_fields(self, game_slug: str) -> List[Dict[str, Any]]:
        """
        Get player identity field configurations for a game.
        
        Uses GamePlayerIdentityConfig model to fetch identity requirements.
        
        TODO: Return List[GamePlayerIdentityConfigDTO] instead of list of dicts.
        
        Raises:
            GameConfigNotFoundError: If game does not exist
        """
        from apps.games.models import GamePlayerIdentityConfig
        from apps.games.services.game_service import GameService
        from apps.tournament_ops.exceptions import GameConfigNotFoundError
        
        try:
            # Verify game exists
            game = GameService.get_game(game_slug)
            if not game:
                raise GameConfigNotFoundError(f"Game '{game_slug}' not found")
            
            # Fetch identity configs
            identity_configs = GamePlayerIdentityConfig.objects.filter(game=game)
            
            # Convert to list of dicts
            # TODO: Convert to List[GamePlayerIdentityConfigDTO.from_model(cfg)]
            return [
                {
                    'field_name': cfg.field_name,
                    'display_name': cfg.display_name,
                    'field_type': cfg.field_type,
                    'is_required': cfg.is_required,
                    'validation_regex': cfg.validation_regex,
                    'help_text': cfg.help_text,
                }
                for cfg in identity_configs
            ]
        except Exception as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise GameConfigNotFoundError(f"Game '{game_slug}' not found")
            raise
    
    def validate_game_identity(
        self,
        game_slug: str,
        identity_payload: Dict[str, Any]
    ) -> bool:
        """
        Validate game identity data against game's identity field rules.
        
        TODO: Implement via GameValidationService (Phase 2, Epic 2.2).
        For now, performs basic validation:
        - Checks that all required fields are present
        - Validates against regex patterns if defined
        
        Args:
            game_slug: Game identifier
            identity_payload: Dict of identity field values
        
        Returns:
            bool: True if valid, False otherwise
        """
        from apps.tournament_ops.exceptions import GameConfigNotFoundError
        import re
        
        try:
            identity_fields = self.get_identity_fields(game_slug)
            
            # Check required fields
            for field in identity_fields:
                if field['is_required'] and field['field_name'] not in identity_payload:
                    return False
                
                # Validate regex if field is present
                if field['field_name'] in identity_payload and field.get('validation_regex'):
                    value = identity_payload[field['field_name']]
                    if not re.match(field['validation_regex'], str(value)):
                        return False
            
            return True
        except GameConfigNotFoundError:
            return False
    
    def get_supported_formats(self, game_slug: str) -> List[str]:
        """
        Get list of tournament formats supported by this game.
        
        Queries GameTournamentConfig to find enabled formats.
        
        TODO: Wire to actual GameTournamentConfig when available (Phase 2, Epic 2.1).
        For now, returns default formats for active games.
        
        Args:
            game_slug: Game identifier
        
        Returns:
            List of format identifiers
        """
        from apps.games.services.game_service import GameService
        from apps.tournament_ops.exceptions import GameConfigNotFoundError
        
        try:
            game = GameService.get_game(game_slug)
            if not game or not game.is_active:
                raise GameConfigNotFoundError(f"Game '{game_slug}' not found or inactive")
            
            # TODO: Query GameTournamentConfig.objects.filter(game=game, is_enabled=True)
            # For Phase 1, return default supported formats
            return ['single_elimination', 'double_elimination', 'round_robin', 'swiss']
        except Exception as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise GameConfigNotFoundError(f"Game '{game_slug}' not found")
            raise
    
    def get_scoring_rules(self, game_slug: str) -> Dict[str, Any]:
        """
        Get scoring rules configuration for a game.
        
        TODO: Query GameScoringRule model (Phase 2, Epic 2.1).
        TODO: Return GameScoringRuleDTO instead of dict.
        
        For Phase 1, returns default scoring config.
        
        Args:
            game_slug: Game identifier
        
        Returns:
            Dict containing scoring rule config
        """
        from apps.games.services.game_service import GameService
        from apps.tournament_ops.exceptions import GameConfigNotFoundError
        
        try:
            game = GameService.get_game(game_slug)
            if not game:
                raise GameConfigNotFoundError(f"Game '{game_slug}' not found")
            
            # TODO: Query GameScoringRule.objects.get(game=game)
            # For Phase 1, return default scoring config
            return {
                'points_per_win': 3,
                'points_per_draw': 1,
                'points_per_loss': 0,
                'tiebreaker_rules': ['head_to_head', 'game_differential', 'points_scored'],
            }
        except Exception as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise GameConfigNotFoundError(f"Game '{game_slug}' not found")
            raise
    
    def check_health(self) -> bool:
        """
        Check if game service is accessible.
        
        Simple health check - attempt to query games.
        """
        try:
            from apps.games.models import Game
            Game.objects.exists()
            return True
        except Exception:
            return False
