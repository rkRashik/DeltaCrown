"""
DeltaCrown Game Registry - Single Source of Truth for Game Configuration
=========================================================================

This package provides a unified, centralized game configuration system that
consolidates all game-related data from across the platform:

- Database Game model (apps.tournaments.models.Game)
- Teams roster configuration (apps.teams.game_config)
- Asset paths and media (apps.common.game_assets)
- Game specifications (Documents/Games/Game_Spec.md)
- CSS theme variables (static/tournaments/detailPages/css/detail_theme.css)

PUBLIC API:
-----------
Use these functions as the ONLY way to access game configuration:

    from apps.common.game_registry import (
        get_all_games,      # Get all games as GameSpec objects
        get_game,           # Get a single game by slug
        get_choices,        # Get Django choices for model fields
        normalize_slug,     # Normalize any game code to canonical slug
        get_profile_id_label,  # Get player ID label for a game
        get_theme_variables,   # Get CSS theme variables for a game
    )

Example Usage:
--------------
    # Get a game
    game = get_game('valorant')
    print(game.name)  # "Valorant"
    print(game.colors['primary'])  # "#ff4655"
    
    # Normalize legacy codes
    slug = normalize_slug('pubg-mobile')  # Returns 'pubg'
    slug = normalize_slug('CSGO')  # Returns 'cs2'
    
    # Get all games for a dropdown
    choices = get_choices()  # [(slug, name), ...]
    
    # Get theme CSS variables
    theme = get_theme_variables('valorant')
    # {'accent': '#ff4655', 'accent-soft': '#ff9aa4', ...}

ARCHITECTURE:
-------------
- registry.py: Core GameSpec dataclass and registry logic
- assets.py: Asset paths (logos, banners, icons, cards)
- normalization.py: Slug normalization and alias handling
- loaders.py: Data loading from multiple sources

MIGRATION NOTES:
----------------
This is the NEW single source of truth for game configuration.
Old modules (game_config.py, game_assets.py, game_mapping.py) are kept
for backwards compatibility but will delegate to this registry.

Created: November 2025
"""

from .registry import (
    GameSpec,
    get_all_games,
    get_game,
    get_choices,
    get_profile_id_label,
    get_theme_variables,
)

from .normalization import normalize_slug

__all__ = [
    'GameSpec',
    'get_all_games',
    'get_game',
    'get_choices',
    'normalize_slug',
    'get_profile_id_label',
    'get_theme_variables',
]
