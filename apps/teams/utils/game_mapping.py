"""
Game code mapping and normalization utilities.

NOW DELEGATES TO apps.common.game_registry for unified game handling.
Maintains backwards compatibility for existing code.
"""

from apps.common.game_registry import (
    normalize_slug,
    get_game,
    get_choices as get_game_choices_from_registry
)

# Legacy game code mappings
LEGACY_GAME_CODES = {
    'pubg-mobile': 'PUBG',
    'pubgm': 'PUBG',
    'pubg_mobile': 'PUBG',
    'csgo': 'CS2',  # CS:GO evolved to CS2
    'cs-go': 'CS2',
    'counter-strike': 'CS2',
    'ml': 'MLBB',
    'mobile-legends': 'MLBB',
    'cod-mobile': 'CODM',
    'codmobile': 'CODM',
    'free-fire': 'FREEFIRE',
    'ff': 'FREEFIRE',
    'efootball-pes': 'EFOOTBALL',
    'pes': 'EFOOTBALL',
    'fifa': 'FC26',  # FIFA rebranded to FC
    'fc-26': 'FC26',
    'fc_26': 'FC26',
}


def normalize_game_code(game_code):
    """
    Normalize a game code to its canonical form.
    
    NOW DELEGATES TO GAME REGISTRY for platform-wide consistency.
    Maintains backwards compatibility.
    
    Args:
        game_code (str): Game code that might be legacy or non-standard
        
    Returns:
        str: Normalized game code (lowercase canonical slug)
    """
    if not game_code:
        return None
    
    # Delegate to Game Registry's normalize_slug for consistency
    return normalize_slug(game_code)


def get_game_config(game_code):
    """
    Get game configuration with legacy code support.
    
    NOW USES GAME REGISTRY for complete game specifications.
    
    Args:
        game_code (str): Game code (may be legacy)
        
    Returns:
        GameSpec: Complete game specification from Game Registry
    """
    normalized = normalize_game_code(game_code)
    return get_game(normalized) if normalized else None


def is_valid_game_code(game_code):
    """
    Check if a game code is valid (including legacy codes).
    
    NOW USES GAME REGISTRY for validation.
    
    Args:
        game_code (str): Game code to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not game_code:
        return False
    
    try:
        normalized = normalize_game_code(game_code)
        game_spec = get_game(normalized)
        return game_spec is not None
    except:
        return False


def get_all_game_choices():
    """
    Get all game choices for use in forms.
    
    NOW DELEGATES TO GAME REGISTRY.
    
    Returns:
        list: List of (code, display_name) tuples
    """
    return get_game_choices_from_registry()


def get_game_display_name(game_code):
    """
    Get display name for a game code (with legacy support).
    
    NOW USES GAME REGISTRY GameSpec.
    
    Args:
        game_code (str): Game code (may be legacy)
        
    Returns:
        str: Display name for the game
    """
    game_spec = get_game_config(game_code)
    if game_spec and hasattr(game_spec, 'display_name'):
        return game_spec.display_name
    return game_code.upper() if game_code else 'Unknown Game'
