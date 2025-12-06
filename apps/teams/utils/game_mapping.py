"""
Game code mapping and normalization utilities.

NOW DELEGATES TO apps.games.services.game_service for unified game handling.
Maintains backwards compatibility for existing code.
"""

from apps.games.services import game_service

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
    
    NOW DELEGATES TO GAME SERVICE for platform-wide consistency.
    Maintains backwards compatibility.
    
    Args:
        game_code (str): Game code that might be legacy or non-standard
        
    Returns:
        str: Normalized game code (lowercase canonical slug)
    """
    if not game_code:
        return None
    
    # Delegate to GameService's normalize_slug for consistency
    return game_service.normalize_slug(game_code)


def get_game_config(game_code):
    """
    Get game configuration with legacy code support.
    
    NOW USES GAME SERVICE for complete game specifications.
    
    Args:
        game_code (str): Game code (may be legacy)
        
    Returns:
        Game instance or None
    """
    normalized = normalize_game_code(game_code)
    return game_service.get_game(normalized) if normalized else None


def is_valid_game_code(game_code):
    """
    Check if a game code is valid (including legacy codes).
    
    NOW USES GAME SERVICE for validation.
    
    Args:
        game_code (str): Game code to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not game_code:
        return False
    
    try:
        normalized = normalize_game_code(game_code)
        game = game_service.get_game(normalized)
        return game is not None
    except:
        return False


def get_all_game_choices():
    """
    Get all game choices for use in forms.
    
    NOW DELEGATES TO GAME SERVICE.
    
    Returns:
        list: List of (slug, display_name) tuples
    """
    return game_service.get_choices()


def get_game_display_name(game_code):
    """
    Get display name for a game code (with legacy support).
    
    NOW USES GAME SERVICE Game model.
    
    Args:
        game_code (str): Game code (may be legacy)
        
    Returns:
        str: Display name for the game
    """
    game = get_game_config(game_code)
    if game:
        return game.display_name
    return game_code.upper() if game_code else 'Unknown Game'
