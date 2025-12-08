"""
Game service layer - business logic for game operations.
"""

from typing import Optional, List, Tuple
from django.core.exceptions import ValidationError
from apps.games.models import (
    Game,
    GameRosterConfig,
    GamePlayerIdentityConfig,
    GameTournamentConfig,
    GameRole,
    GameMatchResultSchema,
    GameScoringRule,
)


class GameService:
    """
    Service layer for game-related operations.
    Replaces hardcoded game logic throughout the application.
    """
    
    @staticmethod
    def get_game(slug: str) -> Optional[Game]:
        """
        Get game by slug.
        
        Args:
            slug: Game slug (e.g., 'valorant', 'mlbb')
            
        Returns:
            Game instance or None
        """
        try:
            return Game.objects.select_related(
                'roster_config',
                'tournament_config'
            ).get(slug=slug, is_active=True)
        except Game.DoesNotExist:
            return None
    
    @staticmethod
    def get_game_by_id(game_id: int) -> Optional[Game]:
        """Get game by ID."""
        try:
            return Game.objects.select_related(
                'roster_config',
                'tournament_config'
            ).get(id=game_id, is_active=True)
        except Game.DoesNotExist:
            return None
    
    @staticmethod
    def list_active_games() -> List[Game]:
        """Get all active games."""
        return Game.objects.filter(is_active=True).order_by('name')
    
    @staticmethod
    def list_featured_games() -> List[Game]:
        """Get featured games for homepage."""
        return Game.objects.filter(
            is_active=True,
            is_featured=True
        ).order_by('name')
    
    @staticmethod
    def get_choices() -> List[Tuple[str, str]]:
        """
        Get game choices for Django model/form fields.
        
        Returns:
            List of (slug, display_name) tuples suitable for choices parameter
            
        Example:
            >>> from apps.games.services import game_service
            >>> choices = game_service.get_choices()
            >>> print(choices)
            [('valorant', 'VALORANT'), ('cs2', 'Counter-Strike 2'), ...]
            
        Usage in forms:
            class TeamForm(forms.ModelForm):
                game = forms.ChoiceField(
                    choices=game_service.get_choices()
                )
        """
        return [
            (game.slug, game.display_name)
            for game in Game.objects.filter(is_active=True).order_by('display_name')
        ]
    
    @staticmethod
    def normalize_slug(game_code: str) -> str:
        """
        Normalize a game code/slug to canonical form.
        
        Args:
            game_code: Game code that might be non-standard (e.g., 'PUBGM', 'codm', 'valorant')
            
        Returns:
            Normalized slug (lowercase, canonical) or original if unknown
            
        Example:
            >>> game_service.normalize_slug('PUBGM')
            'pubg-mobile'
            >>> game_service.normalize_slug('CODM')
            'call-of-duty-mobile'
        """
        if not game_code:
            return ''
        
        # Normalize to lowercase
        code = str(game_code).lower().strip()
        
        # Legacy mappings for backwards compatibility
        legacy_mappings = {
            'pubgm': 'pubg-mobile',
            'pubg_mobile': 'pubg-mobile',
            'codm': 'call-of-duty-mobile',
            'cod_mobile': 'call-of-duty-mobile',
            'codmobile': 'call-of-duty-mobile',
            'mlbb': 'mobile-legends',
            'ml': 'mobile-legends',
            'mobile_legends': 'mobile-legends',
            'ff': 'free-fire',
            'free_fire': 'free-fire',
            'freefire': 'free-fire',
            'fc26': 'fifa',  # Legacy FIFA naming
            'fc_mobile': 'fc-mobile',
            'fcmobile': 'fc-mobile',
            'efootball': 'efootball',
            'pes': 'efootball',
            'csgo': 'cs2',
            'cs_go': 'cs2',
            'counter_strike': 'cs2',
        }
        
        return legacy_mappings.get(code, code)
    
    @staticmethod
    def get_roster_config(game: Game) -> Optional[GameRosterConfig]:
        """
        Get roster configuration for a game.
        
        Args:
            game: Game instance
            
        Returns:
            GameRosterConfig or None
        """
        return game.get_roster_config()
    
    @staticmethod
    def get_roster_limits(game: Game) -> dict:
        """
        Get roster size limits for a game.
        
        Args:
            game: Game instance
            
        Returns:
            dict with min/max team size, substitutes, etc.
        """
        config = GameService.get_roster_config(game)
        if not config:
            # Fallback defaults
            return {
                'min_team_size': 1,
                'max_team_size': 5,
                'min_substitutes': 0,
                'max_substitutes': 2,
                'min_roster_size': 1,
                'max_roster_size': 10,
            }
        
        return {
            'min_team_size': config.min_team_size,
            'max_team_size': config.max_team_size,
            'min_substitutes': config.min_substitutes,
            'max_substitutes': config.max_substitutes,
            'min_roster_size': config.min_roster_size,
            'max_roster_size': config.max_roster_size,
            'allow_coaches': config.allow_coaches,
            'max_coaches': config.max_coaches,
            'allow_analysts': config.allow_analysts,
            'max_analysts': config.max_analysts,
            'allow_managers': config.allow_managers,
            'max_managers': config.max_managers,
        }
    
    @staticmethod
    def validate_roster_size(game: Game, total_players: int, total_subs: int) -> Tuple[bool, Optional[str]]:
        """
        Validate roster size for a game.
        
        Args:
            game: Game instance
            total_players: Number of starting players
            total_subs: Number of substitutes
            
        Returns:
            (is_valid, error_message)
        """
        config = GameService.get_roster_config(game)
        if not config:
            return True, None
        
        return config.validate_roster_size(total_players, total_subs)
    
    @staticmethod
    def get_identity_validation_rules(game: Game) -> List[GamePlayerIdentityConfig]:
        """
        Get all player identity validation rules for a game.
        
        Args:
            game: Game instance
            
        Returns:
            List of GamePlayerIdentityConfig instances
        """
        return list(game.get_identity_configs().order_by('order'))
    
    @staticmethod
    def validate_player_identity(game: Game, field_name: str, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a player identity value for a game.
        
        Args:
            game: Game instance
            field_name: Field name (e.g., 'riot_id')
            value: Value to validate
            
        Returns:
            (is_valid, error_message)
        """
        try:
            config = game.identity_configs.get(field_name=field_name)
            return config.validate_value(value)
        except GamePlayerIdentityConfig.DoesNotExist:
            # No validation rule defined - allow any value
            return True, None
    
    @staticmethod
    def get_tournament_config(game: Game) -> Optional[GameTournamentConfig]:
        """
        Get tournament configuration for a game.
        
        Args:
            game: Game instance
            
        Returns:
            GameTournamentConfig or None
        """
        return game.get_tournament_config()
    
    @staticmethod
    def get_default_tournament_config(game: Game) -> dict:
        """
        Get default tournament configuration as dict.
        
        Args:
            game: Game instance
            
        Returns:
            dict with tournament settings
        """
        config = GameService.get_tournament_config(game)
        if not config:
            # Fallback defaults
            return {
                'match_formats': ['BO1', 'BO3', 'BO5'],
                'default_match_format': 'BO3',
                'scoring_type': 'WIN_LOSS',
                'tiebreakers': ['head_to_head', 'round_diff'],
                'allow_draws': False,
                'overtime_enabled': True,
            }
        
        return {
            'match_formats': config.available_match_formats,
            'default_match_format': config.default_match_format,
            'scoring_type': config.default_scoring_type,
            'scoring_rules': config.scoring_rules,
            'tiebreakers': config.default_tiebreakers,
            'allow_draws': config.allow_draws,
            'overtime_enabled': config.overtime_enabled,
            'check_in_required': config.require_check_in,
            'check_in_window': config.check_in_window_minutes,
        }
    
    @staticmethod
    def get_match_formats(game: Game) -> List[str]:
        """Get available match formats for a game."""
        config = GameService.get_tournament_config(game)
        if config and config.available_match_formats:
            return config.available_match_formats
        return ['BO1', 'BO3', 'BO5']
    
    @staticmethod
    def get_tiebreakers(game: Game) -> List[str]:
        """Get tiebreaker criteria for a game."""
        config = GameService.get_tournament_config(game)
        if config and config.default_tiebreakers:
            return config.default_tiebreakers
        return ['head_to_head', 'round_diff', 'rounds_won']
    
    @staticmethod
    def list_roles(game: Game) -> List[GameRole]:
        """
        Get all roles for a game.
        
        Args:
            game: Game instance
            
        Returns:
            List of GameRole instances
        """
        return list(game.get_roles().filter(is_active=True))
    
    @staticmethod
    def has_roles(game: Game) -> bool:
        """Check if a game has defined roles."""
        config = GameService.get_roster_config(game)
        return config and config.has_roles

    # ========== Phase 2: Configuration Getters ==========

    @staticmethod
    def get_player_identity_config(game_slug: str) -> List[GamePlayerIdentityConfig]:
        """
        Get player identity configuration for a game.

        Args:
            game_slug: Game slug (e.g., 'valorant')

        Returns:
            List of GamePlayerIdentityConfig instances

        Raises:
            ValueError: If game not found
        """
        game = GameService.get_game(game_slug)
        if not game:
            raise ValueError(f"Game '{game_slug}' not found")

        return list(
            GamePlayerIdentityConfig.objects.filter(game=game).order_by("order")
        )

    @staticmethod
    def get_scoring_rules(game_slug: str) -> List[GameScoringRule]:
        """
        Get scoring rules for a game.

        Args:
            game_slug: Game slug

        Returns:
            List of GameScoringRule instances, ordered by priority (highest first)

        Raises:
            ValueError: If game not found
        """
        game = GameService.get_game(game_slug)
        if not game:
            raise ValueError(f"Game '{game_slug}' not found")

        return list(
            GameScoringRule.objects.filter(game=game, is_active=True).order_by(
                "-priority", "rule_type"
            )
        )

    @staticmethod
    def get_tournament_config_by_slug(game_slug: str) -> Optional[GameTournamentConfig]:
        """
        Get tournament configuration by game slug.

        Args:
            game_slug: Game slug

        Returns:
            GameTournamentConfig instance or None

        Raises:
            ValueError: If game not found
        """
        game = GameService.get_game(game_slug)
        if not game:
            raise ValueError(f"Game '{game_slug}' not found")

        return GameService.get_tournament_config(game)

    @staticmethod
    def get_match_schema(game_slug: str) -> List[GameMatchResultSchema]:
        """
        Get match result schema for a game.

        Args:
            game_slug: Game slug

        Returns:
            List of GameMatchResultSchema instances

        Raises:
            ValueError: If game not found

        Example:
            >>> schemas = game_service.get_match_schema('valorant')
            >>> for schema in schemas:
            ...     print(f"{schema.field_name}: {schema.field_type}")
            rounds_won: integer
            kills: integer
            deaths: integer
            assists: integer
            acs: integer
        """
        game = GameService.get_game(game_slug)
        if not game:
            raise ValueError(f"Game '{game_slug}' not found")

        return list(GameMatchResultSchema.objects.filter(game=game).order_by("field_name"))


# Singleton instance
game_service = GameService()
