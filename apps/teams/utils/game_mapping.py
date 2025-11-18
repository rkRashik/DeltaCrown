"""
Game code mapping and normalization utilities.

Handles legacy game codes and provides a single source of truth
for game configuration across the Teams app.
"""

from apps.common.game_assets import GAMES, get_game_data

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
    
    Args:
        game_code (str): Game code that might be legacy or non-standard
        
    Returns:
        str: Normalized game code (uppercase)
    """
    if not game_code:
        return None
    
    # Convert to uppercase for consistency
    code = str(game_code).upper().strip()
    
    # Check if it's already a valid code
    if code in GAMES:
        return code
    
    # Try lowercase version in legacy mapping
    lower_code = game_code.lower().strip()
    if lower_code in LEGACY_GAME_CODES:
        return LEGACY_GAME_CODES[lower_code]
    
    # Try hyphen/underscore variations
    code_variations = [
        code.replace('-', '_'),
        code.replace('_', '-'),
        code.replace('-', ''),
        code.replace('_', ''),
    ]
    
    for variant in code_variations:
        if variant in GAMES:
            return variant
        lower_variant = variant.lower()
        if lower_variant in LEGACY_GAME_CODES:
            return LEGACY_GAME_CODES[lower_variant]
    
    # Return original if no mapping found
    return code


def get_game_config(game_code):
    """
    Get game configuration with legacy code support.
    
    Args:
        game_code (str): Game code (may be legacy)
        
    Returns:
        dict: Game configuration from game_assets, or default config
    """
    normalized = normalize_game_code(game_code)
    return get_game_data(normalized)


def is_valid_game_code(game_code):
    """
    Check if a game code is valid (including legacy codes).
    
    Args:
        game_code (str): Game code to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not game_code:
        return False
    
    normalized = normalize_game_code(game_code)
    return normalized in GAMES


def get_all_game_choices():
    """
    Get all game choices for use in forms.
    
    Returns:
        list: List of (code, display_name) tuples
    """
    return [(code, data['display_name']) for code, data in GAMES.items()]


def get_game_display_name(game_code):
    """
    Get display name for a game code (with legacy support).
    
    Args:
        game_code (str): Game code (may be legacy)
        
    Returns:
        str: Display name for the game
    """
    config = get_game_config(game_code)
    return config.get('display_name', game_code.upper() if game_code else 'Unknown Game')
