"""
Game Registry - Core Registry Module
=====================================

THE SINGLE SOURCE OF TRUTH FOR ALL GAME CONFIGURATION.

This module defines the GameSpec dataclass and provides the public API for
accessing game configuration across the entire platform.

DO NOT access game configuration from any other module. Always use this registry.

PUBLIC API:
-----------
- get_all_games() → List[GameSpec]
- get_game(slug) → GameSpec
- get_choices() → List[Tuple[str, str]]
- get_profile_id_label(slug) → str
- get_theme_variables(slug) → dict
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import logging

from .assets import GAME_ASSETS, get_asset_data
from .loaders import (
    load_roster_config,
    load_theme_variables,
    load_result_logic,
    get_profile_id_field_mapping,
    load_database_game,
    get_all_database_games,
)
from .normalization import normalize_slug as _normalize_slug, get_all_aliases

logger = logging.getLogger(__name__)


# ============================================================================
# GAME SPECIFICATION DATACLASS
# ============================================================================

@dataclass
class GameSpec:
    """
    Complete specification for a game.
    
    This is the canonical representation of a game in DeltaCrown.
    All game-related code should use this dataclass.
    
    Attributes:
        slug: Canonical lowercase slug (e.g., 'valorant', 'cs2')
        name: Short name (e.g., 'Valorant', 'CS2')
        display_name: Full display name (e.g., 'Counter-Strike 2')
        code: Uppercase code for legacy compatibility (e.g., 'VALORANT')
        
        # Media Assets
        icon: Icon file path
        banner: Banner image path
        logo: Logo image path
        card: Card image path
        
        # Styling
        colors: Dict with 'primary', 'secondary', 'accent', etc.
        
        # Team Configuration
        min_team_size: Minimum players per team
        max_team_size: Maximum players per team
        min_substitutes: Minimum substitutes allowed
        max_substitutes: Maximum substitutes allowed
        
        # Roles & Roster
        roles: List of role names
        role_descriptions: Dict mapping role to description
        regions: List of (code, name) tuples for regions
        requires_unique_roles: Whether roles must be unique
        allows_multi_role: Whether players can have multiple roles
        
        # Player Identity
        profile_id_field: UserProfile field name for player ID
        player_id_label: Display label for player ID (e.g., "Riot ID")
        player_id_format: Format description
        player_id_placeholder: Placeholder example
        
        # Result Logic
        result_type: 'map_score', 'best_of', 'point_based', or 'game_score'
        result_format: Human-readable format description
        result_settings: Tournament-specific settings
        
        # Metadata
        category: Game category (FPS, MOBA, Sports, Battle Royale)
        game_type: Tournament type (Team vs Team, 1v1, Battle Royale)
        platforms: List of platforms (PC, Mobile, Console)
        
        # Legacy Support
        legacy_aliases: List of old codes that map to this game
        
        # Database Integration
        database_id: Optional database Game model ID
        is_active: Whether game is actively supported
    """
    
    # Core Identity
    slug: str
    name: str
    display_name: str
    code: str  # Uppercase for legacy compatibility
    
    # Media Assets
    icon: str = ''
    banner: str = ''
    logo: str = ''
    card: str = ''
    
    # Styling
    colors: Dict[str, str] = field(default_factory=dict)
    
    # Team Configuration
    min_team_size: int = 1
    max_team_size: int = 5
    min_substitutes: int = 0
    max_substitutes: int = 2
    
    # Roles & Roster
    roles: List[str] = field(default_factory=list)
    role_descriptions: Dict[str, str] = field(default_factory=dict)
    regions: List[Tuple[str, str]] = field(default_factory=list)
    requires_unique_roles: bool = False
    allows_multi_role: bool = True
    
    # Player Identity
    profile_id_field: str = 'game_id'
    player_id_label: str = 'Player ID'
    player_id_format: str = ''
    player_id_placeholder: str = ''
    
    # Result Logic
    result_type: str = 'map_score'
    result_format: str = ''
    result_settings: str = ''
    
    # Metadata
    category: str = 'Gaming'
    game_type: str = 'Team vs Team'
    platforms: List[str] = field(default_factory=lambda: ['PC'])
    
    # Legacy Support
    legacy_aliases: List[str] = field(default_factory=list)
    
    # Database Integration
    database_id: Optional[int] = None
    is_active: bool = True
    
    # Additional Configuration
    description: str = ''
    extra_config: Dict = field(default_factory=dict)
    
    def get_roster_size_range(self) -> str:
        """Get roster size as a display string."""
        min_total = self.min_team_size
        max_total = self.max_team_size + self.max_substitutes
        if min_total == max_total:
            return str(min_total)
        return f"{min_total}-{max_total}"
    
    def get_team_size_display(self) -> str:
        """Get team size as display string (e.g., '5v5', '1v1')."""
        if self.min_team_size == self.max_team_size:
            return f"{self.max_team_size}v{self.max_team_size}"
        return f"{self.min_team_size}-{self.max_team_size}"
    
    def has_role(self, role: str) -> bool:
        """Check if a role is valid for this game."""
        return role in self.roles
    
    def get_color(self, color_type: str = 'primary') -> str:
        """Get a specific color, with fallback."""
        return self.colors.get(color_type, '#7c3aed')


# ============================================================================
# GAME REGISTRY CACHE
# ============================================================================

_REGISTRY_CACHE: Optional[Dict[str, GameSpec]] = None


def _build_registry() -> Dict[str, GameSpec]:
    """
    Build the complete game registry by merging data from all sources.
    
    NEW MERGE ORDER (Database-First Approach):
    1. Database Game model (PRIMARY - editable via Django admin)
    2. GAME_CONFIGS (roster rules, roles, regions)
    3. GAME_ASSETS (colors, default artwork for missing assets)
    4. Result logic from Game_Spec.md
    5. Defaults
    
    Database fields ALWAYS override other sources.
    
    Returns:
        Dictionary mapping canonical slugs to GameSpec objects
    """
    registry = {}
    
    # STEP 1: Load all database games first (PRIMARY SOURCE)
    db_games = get_all_database_games()
    
    if db_games:
        logger.info(f"Loading {len(db_games)} games from database (primary source)")
        
        for db_game in db_games:
            slug = _normalize_slug(db_game['slug'])
            
            # Start with database data (HIGHEST PRIORITY)
            spec = GameSpec(
                slug=slug,
                name=db_game['name'],
                display_name=db_game['name'],  # Use DB name as display name
                code=db_game['name'].upper().replace(' ', ''),
                
                # Database fields (ALWAYS USED)
                database_id=db_game['database_id'],
                is_active=db_game['is_active'],
                description=db_game['description'],
                
                # Media assets from DB (HIGHEST PRIORITY)
                icon=db_game.get('icon', ''),
                banner=db_game.get('banner', ''),
                logo=db_game.get('logo', ''),
                card=db_game.get('card_image', ''),
                
                # Presentation fields from DB
                colors={
                    'primary': db_game.get('primary_color') or '#7c3aed',
                    'secondary': db_game.get('secondary_color') or '#1a1a1a',
                },
                
                # Metadata from DB
                category=db_game.get('category', 'Gaming'),
                platforms=[db_game.get('platform')] if db_game.get('platform') else ['PC'],
                
                # Team configuration from DB
                min_team_size=db_game.get('min_team_size', 1),
                max_team_size=db_game.get('max_team_size', 5),
                
                # Profile field from DB
                profile_id_field=db_game['profile_id_field'] or 'game_id',
            )
            
            # Roles from DB (if available)
            if db_game.get('roles'):
                spec.roles = db_game['roles']
            
            # Result logic from DB (if available)
            if db_game.get('result_logic'):
                db_result = db_game['result_logic']
                spec.result_type = db_result.get('type', 'map_score')
                spec.result_format = db_result.get('format', '')
                spec.result_settings = db_result.get('settings', '')
            
            # STEP 2: Merge roster configuration (roles, regions, team size details)
            # Only merge roles if DB doesn't provide them
            roster_config = load_roster_config(slug)
            if roster_config:
                # Use DB team sizes if set, otherwise use roster config
                if db_game.get('min_team_size') == 1 and db_game.get('max_team_size') == 5:
                    # These are defaults, prefer roster config
                    spec.min_team_size = roster_config.get('min_starters', spec.min_team_size)
                    spec.max_team_size = roster_config.get('max_starters', spec.max_team_size)
                
                spec.max_substitutes = roster_config.get('max_substitutes', 2)
                
                # Only use roster roles if DB doesn't have them
                if not spec.roles:
                    spec.roles = roster_config.get('roles', [])
                
                spec.role_descriptions = roster_config.get('role_descriptions', {})
                spec.regions = roster_config.get('regions', [])
                spec.requires_unique_roles = roster_config.get('requires_unique_roles', False)
                spec.allows_multi_role = roster_config.get('allows_multi_role', True)
            
            # STEP 3: Merge asset data (ONLY for missing fields)
            asset_data = get_asset_data(slug.upper())
            if asset_data:
                # Only use asset media if DB doesn't have it
                if not spec.icon and asset_data.get('icon'):
                    spec.icon = asset_data['icon']
                    logger.info(f"Using asset icon for '{spec.name}' (DB icon missing)")
                
                if not spec.banner and asset_data.get('banner'):
                    spec.banner = asset_data['banner']
                    logger.info(f"Using asset banner for '{spec.name}' (DB banner missing)")
                
                if not spec.logo and asset_data.get('logo'):
                    spec.logo = asset_data['logo']
                    logger.info(f"Using asset logo for '{spec.name}' (DB logo missing)")
                
                if not spec.card and asset_data.get('card'):
                    spec.card = asset_data['card']
                    logger.info(f"Using asset card for '{spec.name}' (DB card missing)")
                
                # Only use asset colors if DB doesn't have them
                if spec.colors['primary'] == '#7c3aed':  # Default value
                    spec.colors['primary'] = asset_data.get('color_primary', '#7c3aed')
                if spec.colors['secondary'] == '#1a1a1a':  # Default value
                    spec.colors['secondary'] = asset_data.get('color_secondary', '#1a1a1a')
                
                # Only use asset metadata if DB doesn't have it
                if spec.category == 'Gaming':
                    spec.category = asset_data.get('category', 'Gaming')
                
                if not db_game.get('platform'):
                    spec.platforms = asset_data.get('platform', ['PC'])
                
                # Player ID labels (always from assets if available)
                spec.player_id_label = asset_data.get('player_id_label', 'Player ID')
                spec.player_id_format = asset_data.get('player_id_format', '')
                spec.player_id_placeholder = asset_data.get('player_id_placeholder', '')
                
                # Game type (only from assets)
                spec.game_type = asset_data.get('type', 'Team vs Team')
            
            # STEP 4: Merge theme variables (CSS colors)
            theme_vars = load_theme_variables(slug)
            if theme_vars:
                spec.colors.update({
                    'accent': theme_vars.get('accent', spec.colors.get('primary')),
                    'accent-soft': theme_vars.get('accent-soft', ''),
                    'accent-glow': theme_vars.get('accent-glow', ''),
                    'bg-elevated': theme_vars.get('bg-elevated', ''),
                    'bg-surface': theme_vars.get('bg-surface', ''),
                    'bg-hero-overlay': theme_vars.get('bg-hero-overlay', ''),
                })
            
            # STEP 5: Merge result logic (only if DB doesn't have it)
            if not db_game.get('result_logic'):
                result_logic = load_result_logic(slug)
                if result_logic:
                    spec.result_type = result_logic.get('type', 'map_score')
                    spec.result_format = result_logic.get('format', '')
                    spec.result_settings = result_logic.get('settings', '')
            
            # Get legacy aliases for normalization
            spec.legacy_aliases = get_all_aliases(slug)
            
            # Store extra config from JSONB
            spec.extra_config = db_game.get('game_config', {})
            
            registry[slug] = spec
    
    else:
        # FALLBACK: No database available, use asset-based loading
        logger.warning("No database games found - falling back to asset-based registry")
        
        for game_code, asset_data in GAME_ASSETS.items():
            slug = _normalize_slug(asset_data.get('slug', game_code.lower()))
            
            # Skip duplicates
            if slug in registry:
                continue
            
            spec = GameSpec(
                slug=slug,
                name=asset_data.get('name', game_code),
                display_name=asset_data.get('display_name', asset_data.get('name', game_code)),
                code=game_code,
                
                # Assets
                icon=asset_data.get('icon', ''),
                banner=asset_data.get('banner', ''),
                logo=asset_data.get('logo', ''),
                card=asset_data.get('card', ''),
                
                # Colors
                colors={
                    'primary': asset_data.get('color_primary', '#7c3aed'),
                    'secondary': asset_data.get('color_secondary', '#1a1a1a'),
                },
                
                # Metadata
                category=asset_data.get('category', 'Gaming'),
                game_type=asset_data.get('type', 'Team vs Team'),
                platforms=asset_data.get('platform', ['PC']),
                
                # Player ID
                player_id_label=asset_data.get('player_id_label', 'Player ID'),
                player_id_format=asset_data.get('player_id_format', ''),
                player_id_placeholder=asset_data.get('player_id_placeholder', ''),
            )
            
            # Merge roster configuration
            roster_config = load_roster_config(slug)
            if roster_config:
                spec.min_team_size = roster_config.get('min_starters', 1)
                spec.max_team_size = roster_config.get('max_starters', 5)
                spec.max_substitutes = roster_config.get('max_substitutes', 2)
                spec.roles = roster_config.get('roles', [])
                spec.role_descriptions = roster_config.get('role_descriptions', {})
                spec.regions = roster_config.get('regions', [])
                spec.requires_unique_roles = roster_config.get('requires_unique_roles', False)
                spec.allows_multi_role = roster_config.get('allows_multi_role', True)
            
            # Merge theme variables
            theme_vars = load_theme_variables(slug)
            if theme_vars:
                spec.colors.update({
                    'accent': theme_vars.get('accent', spec.colors.get('primary')),
                    'accent-soft': theme_vars.get('accent-soft', ''),
                    'accent-glow': theme_vars.get('accent-glow', ''),
                    'bg-elevated': theme_vars.get('bg-elevated', ''),
                    'bg-surface': theme_vars.get('bg-surface', ''),
                    'bg-hero-overlay': theme_vars.get('bg-hero-overlay', ''),
                })
            
            # Merge result logic
            result_logic = load_result_logic(slug)
            if result_logic:
                spec.result_type = result_logic.get('type', 'map_score')
                spec.result_format = result_logic.get('format', '')
                spec.result_settings = result_logic.get('settings', '')
            
            # Set profile ID field
            spec.profile_id_field = get_profile_id_field_mapping(slug)
            
            # Get legacy aliases
            spec.legacy_aliases = get_all_aliases(slug)
            
            registry[slug] = spec
    
    # Validation warnings for games in GAME_ASSETS but not in DB
    if db_games:
        db_slugs = {_normalize_slug(g['slug']) for g in db_games}
        asset_slugs = {_normalize_slug(asset.get('slug', code.lower())) 
                      for code, asset in GAME_ASSETS.items()}
        
        missing_in_db = asset_slugs - db_slugs
        if missing_in_db:
            logger.warning(
                f"Games defined in GAME_ASSETS but missing from database: {', '.join(sorted(missing_in_db))}"
            )
        
        missing_in_assets = db_slugs - asset_slugs
        if missing_in_assets:
            logger.info(
                f"Games in database without asset definitions (will use defaults): {', '.join(sorted(missing_in_assets))}"
            )
    
    logger.info(f"Built game registry with {len(registry)} games")
    return registry


def _get_registry() -> Dict[str, GameSpec]:
    """Get or build the registry cache."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        _REGISTRY_CACHE = _build_registry()
    return _REGISTRY_CACHE


def invalidate_cache():
    """Invalidate the registry cache. Called on Django reload."""
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None
    logger.info("Game registry cache invalidated")


# ============================================================================
# PUBLIC API
# ============================================================================

def get_all_games() -> List[GameSpec]:
    """
    Get all registered games.
    
    Returns:
        List of GameSpec objects for all supported games
        
    Example:
        >>> games = get_all_games()
        >>> for game in games:
        ...     print(f"{game.name}: {game.slug}")
        Valorant: valorant
        Counter-Strike 2: cs2
        ...
    """
    registry = _get_registry()
    return list(registry.values())


def get_game(slug: str) -> GameSpec:
    """
    Get a game by its slug.
    
    This function normalizes the input slug, so you can pass any variant:
    - 'VALORANT', 'valorant', 'Valorant' → all work
    - 'CS:GO', 'csgo', 'cs-go' → all return CS2
    - 'pubg-mobile', 'PUBG', 'pubgm' → all return PUBG
    
    Args:
        slug: Game slug (any case, with or without hyphens/underscores)
        
    Returns:
        GameSpec object
        
    Raises:
        KeyError: If game is not found (even after normalization)
        
    Example:
        >>> game = get_game('valorant')
        >>> print(game.name)
        Valorant
        >>> print(game.colors['primary'])
        #FF4655
        
        >>> game = get_game('CS:GO')  # Legacy code
        >>> print(game.slug)
        cs2
    """
    registry = _get_registry()
    normalized = _normalize_slug(slug)
    
    if normalized not in registry:
        raise KeyError(
            f"Game '{slug}' not found in registry. "
            f"Normalized to '{normalized}'. "
            f"Available games: {', '.join(sorted(registry.keys()))}"
        )
    
    return registry[normalized]


def get_game_safe(slug: str) -> Optional[GameSpec]:
    """
    Get a game by slug, returning None if not found.
    
    Safe version of get_game() that doesn't raise exceptions.
    
    Args:
        slug: Game slug
        
    Returns:
        GameSpec object or None
    """
    try:
        return get_game(slug)
    except KeyError:
        return None


def get_choices() -> List[Tuple[str, str]]:
    """
    Get game choices for Django model fields.
    
    Returns:
        List of (slug, display_name) tuples suitable for choices parameter
        
    Example:
        >>> choices = get_choices()
        >>> print(choices)
        [('valorant', 'Valorant'), ('cs2', 'Counter-Strike 2'), ...]
        
    Usage in models:
        class Tournament(models.Model):
            game = models.CharField(
                max_length=20,
                choices=get_choices()
            )
    """
    games = get_all_games()
    return [(game.slug, game.display_name) for game in sorted(games, key=lambda g: g.display_name)]


def get_profile_id_label(slug: str) -> str:
    """
    Get the player ID label for a game.
    
    Args:
        slug: Game slug
        
    Returns:
        Player ID label (e.g., "Riot ID", "Steam ID", "IGN / UID")
        
    Example:
        >>> get_profile_id_label('valorant')
        'Riot ID'
        >>> get_profile_id_label('cs2')
        'Steam ID'
        >>> get_profile_id_label('mlbb')
        'User ID + Zone ID'
    """
    try:
        game = get_game(slug)
        return game.player_id_label
    except KeyError:
        return 'Player ID'


def get_theme_variables(slug: str) -> Dict[str, str]:
    """
    Get CSS theme variables for a game.
    
    Returns a dictionary of CSS custom property values that can be used
    in templates or stylesheets.
    
    Args:
        slug: Game slug
        
    Returns:
        Dictionary of theme variables (accent, bg-elevated, etc.)
        
    Example:
        >>> theme = get_theme_variables('valorant')
        >>> print(theme['accent'])
        #ff4655
        >>> print(theme['bg-surface'])
        #0b1018
        
    Usage in templates:
        {% load game_registry %}
        {% get_theme_vars 'valorant' as theme %}
        <div style="background: {{ theme.accent }}">...</div>
    """
    try:
        game = get_game(slug)
        return game.colors
    except KeyError:
        return {
            'primary': '#7c3aed',
            'secondary': '#1a1a1a',
            'accent': '#7c3aed',
        }


def game_exists(slug: str) -> bool:
    """
    Check if a game exists in the registry.
    
    Args:
        slug: Game slug (will be normalized)
        
    Returns:
        True if game exists, False otherwise
        
    Example:
        >>> game_exists('valorant')
        True
        >>> game_exists('unknown-game')
        False
    """
    return get_game_safe(slug) is not None


def get_games_by_category(category: str) -> List[GameSpec]:
    """
    Get all games in a specific category.
    
    Args:
        category: Category name (FPS, MOBA, Sports, Battle Royale)
        
    Returns:
        List of GameSpec objects in that category
    """
    return [
        game for game in get_all_games()
        if game.category.lower() == category.lower()
    ]


def get_games_by_platform(platform: str) -> List[GameSpec]:
    """
    Get all games available on a specific platform.
    
    Args:
        platform: Platform name (PC, Mobile, Console)
        
    Returns:
        List of GameSpec objects available on that platform
    """
    return [
        game for game in get_all_games()
        if platform in game.platforms
    ]


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================

def get_game_config(slug: str) -> GameSpec:
    """Alias for get_game() for backwards compatibility."""
    return get_game(slug)


def get_all_game_codes() -> List[str]:
    """Get list of all game slugs."""
    return [game.slug for game in get_all_games()]


def get_all_game_names() -> List[str]:
    """Get list of all game display names."""
    return [game.display_name for game in get_all_games()]
