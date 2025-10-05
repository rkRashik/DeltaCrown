"""
DeltaCrown Game Assets Configuration
===================================

Centralized configuration for all game logos, ba    'CODM': {
        'name': 'COD Mobile',
        'display_name': 'Call of Duty: Mobile',
        'logo': 'img/game_logos/codm_logo.jpg',  # needs to be added
        'card': 'img/game_cards/codm_card.jpg',
        'icon': 'logos/codm.svg',  # use existing svg
        'banner': 'img/game_banners/codm_banner.jpg',
        'color_primary': '#FF6900',
        'color_secondary': '#000000',
        'category': 'FPS',
        'platform': ['Mobile'],
    },, and related assets.
This file provides a single source of truth for all game-related media paths.

Usage:
    from apps.common.game_assets import GAMES, get_game_logo, get_game_card
    
    # Get game logo
    logo_url = get_game_logo('VALORANT')
    
    # Get game card image
    card_url = get_game_card('VALORANT')
    
    # Get all game data
    game_data = GAMES.get('VALORANT', {})
"""

from django.conf import settings
from django.templatetags.static import static

# Game Assets Configuration
# Update paths here to change logos/cards across the entire application
GAMES = {
    'VALORANT': {
        'name': 'Valorant',
        'display_name': 'Valorant',
        'logo': 'img/game_logos/Valorant_logo.jpg',  # exists
        'card': 'img/game_cards/valorant_card.jpg',
        'icon': 'logos/valorant.svg',  # use existing svg
        'banner': 'img/game_banners/valorant_banner.jpg',
        'color_primary': '#FF4655',
        'color_secondary': '#0F1419',
        'category': 'FPS',
        'platform': ['PC', 'Mobile'],
    },
    
    'CSGO': {
        'name': 'CS:GO',
        'display_name': 'Counter-Strike: Global Offensive',
        'logo': 'img/game_logos/CS2_logo.jpeg',  # exists
        'card': 'img/game_cards/csgo_card.jpg',
        'icon': 'logos/csgo.svg',  # use existing svg
        'banner': 'img/game_banners/csgo_banner.jpg',
        'color_primary': '#F79100',
        'color_secondary': '#1B1B1B',
        'category': 'FPS',
        'platform': ['PC'],
    },
    
    'CS2': {
        'name': 'CS2',
        'display_name': 'Counter-Strike 2',
        'logo': 'img/game_logos/CS2_logo.jpeg',
        'card': 'img/game_cards/cs2_card.jpg',
        'icon': 'img/game_icons/cs2_icon.png',
        'banner': 'img/game_banners/cs2_banner.jpg',
        'color_primary': '#F79100',
        'color_secondary': '#1B1B1B',
        'category': 'FPS',
        'platform': ['PC'],
    },
    
    'EFOOTBALL': {
        'name': 'eFootball',
        'display_name': 'eFootball PES',
        'logo': 'img/game_logos/efootball_logo.jpeg',  # exists
        'card': 'img/game_cards/efootball_card.jpg',
        'icon': 'logos/efootball.svg',  # use existing svg
        'banner': 'img/game_banners/efootball_banner.jpg',
        'color_primary': '#00A0E4',
        'color_secondary': '#003366',
        'category': 'Sports',
        'platform': ['PC', 'Mobile', 'Console'],
    },
    
    'MLBB': {
        'name': 'Mobile Legends',
        'display_name': 'Mobile Legends: Bang Bang',
        'logo': 'img/game_logos/mobile_legend_logo.jpeg',  # exists
        'card': 'img/game_cards/mlbb_card.jpg',
        'icon': 'logos/mlbb.svg',  # use existing svg
        'banner': 'img/game_banners/mlbb_banner.jpg',
        'color_primary': '#4A90E2',
        'color_secondary': '#1E3A8A',
        'category': 'MOBA',
        'platform': ['Mobile'],
    },
    
    'FREEFIRE': {
        'name': 'Free Fire',
        'display_name': 'Garena Free Fire',
        'logo': 'img/game_logos/FreeFire.jpeg',  # exists (note capitalization)
        'card': 'img/game_cards/freefire_card.jpg',
        'icon': 'logos/freefire.png',  # use existing png
        'banner': 'img/game_banners/freefire_banner.jpg',
        'color_primary': '#FF6B35',
        'color_secondary': '#2C1810',
        'category': 'Battle Royale',
        'platform': ['Mobile'],
    },
    
    'PUBG': {
        'name': 'PUBG',
        'display_name': 'PlayerUnknown\'s Battlegrounds',
        'logo': 'img/game_logos/PUBG_logo.jpg',
        'card': 'img/game_cards/pubg_card.jpg',
        'icon': 'img/game_icons/pubg_icon.png',
        'banner': 'img/game_banners/pubg_banner.jpg',
        'color_primary': '#F4A623',
        'color_secondary': '#1C1C1E',
        'category': 'Battle Royale',
        'platform': ['PC', 'Mobile', 'Console'],
    },
    
    'FC26': {
        'name': 'FC26',
        'display_name': 'EA Sports FC 26',
        'logo': 'img/game_logos/fc26_logo.jpg',  # exists
        'card': 'img/game_cards/fc26_card.jpg',
        'icon': 'logos/fc26.svg',  # use existing svg
        'banner': 'img/game_banners/fc26_banner.jpg',
        'color_primary': '#00D4FF',
        'color_secondary': '#003366',
        'category': 'Sports',
        'platform': ['PC', 'Console'],
    },
    
    # CODM, LOL, and DOTA2 temporarily removed from active games list
    # Can be re-enabled by uncommenting below:
    # 'CODM': {
    #     'name': 'Call of Duty Mobile',
    #     'display_name': 'Call of Duty: Mobile',
    #     'logo': 'img/game_logos/codm_logo.jpg',
    #     'card': 'img/game_cards/codm_card.jpg',
    #     'icon': 'img/game_icons/codm_icon.png',
    #     'banner': 'img/game_banners/codm_banner.jpg',
    #     'color_primary': '#FF6900',
    #     'color_secondary': '#000000',
    #     'category': 'FPS',
    #     'platform': ['Mobile'],
    # },
    # 
    # 'LOL': {
    #     'name': 'League of Legends',
    #     'display_name': 'League of Legends',
    #     'logo': 'img/game_logos/lol_logo.jpg',
    #     'card': 'img/game_cards/lol_card.jpg',
    #     'icon': 'img/game_icons/lol_icon.png',
    #     'banner': 'img/game_banners/lol_banner.jpg',
    #     'color_primary': '#C89B3C',
    #     'color_secondary': '#0F2027',
    #     'category': 'MOBA',
    #     'platform': ['PC'],
    # },
    # 
    # 'DOTA2': {
    #     'name': 'Dota 2',
    #     'display_name': 'Dota 2',
    #     'logo': 'img/game_logos/dota2_logo.jpg',
    #     'card': 'img/game_cards/dota2_card.jpg',
    #     'icon': 'img/game_icons/dota2_icon.png',
    #     'banner': 'img/game_banners/dota2_banner.jpg',
    #     'color_primary': '#E62E04',
    #     'color_secondary': '#000000',
    #     'category': 'MOBA',
    #     'platform': ['PC'],
    # },
}

# Default fallback assets
DEFAULT_GAME = {
    'name': 'Unknown Game',
    'display_name': 'Unknown Game',
    'logo': 'img/game_logos/default_game_logo.jpg',
    'card': 'img/game_cards/default_game_card.jpg',
    'icon': 'img/game_icons/default_game_icon.png',
    'banner': 'img/game_banners/default_game_banner.jpg',
    'color_primary': '#6B7280',
    'color_secondary': '#1F2937',
    'category': 'Other',
    'platform': ['PC'],
}

# Utility Functions
def get_game_data(game_code):
    """
    Get complete game data for a game code.
    
    Args:
        game_code (str): Game code (e.g., 'VALORANT', 'CSGO')
        
    Returns:
        dict: Complete game data dictionary
    """
    return GAMES.get(game_code.upper(), DEFAULT_GAME.copy())

def get_game_logo(game_code, use_static=True):
    """
    Get the logo URL for a game.
    
    Args:
        game_code (str): Game code (e.g., 'VALORANT', 'CSGO')
        use_static (bool): Whether to return a static URL or just the path
        
    Returns:
        str: Logo URL or path
    """
    game_data = get_game_data(game_code)
    logo_path = game_data['logo']
    
    if use_static:
        return static(logo_path)
    return logo_path

def get_game_card(game_code, use_static=True):
    """
    Get the card image URL for a game.
    
    Args:
        game_code (str): Game code (e.g., 'VALORANT', 'CSGO')
        use_static (bool): Whether to return a static URL or just the path
        
    Returns:
        str: Card image URL or path
    """
    game_data = get_game_data(game_code)
    card_path = game_data['card']
    
    if use_static:
        return static(card_path)
    return card_path

def get_game_icon(game_code, use_static=True):
    """
    Get the icon URL for a game.
    
    Args:
        game_code (str): Game code (e.g., 'VALORANT', 'CSGO')
        use_static (bool): Whether to return a static URL or just the path
        
    Returns:
        str: Icon URL or path
    """
    game_data = get_game_data(game_code)
    icon_path = game_data['icon']
    
    if use_static:
        return static(icon_path)
    return icon_path

def get_game_banner(game_code, use_static=True):
    """
    Get the banner URL for a game.
    
    Args:
        game_code (str): Game code (e.g., 'VALORANT', 'CSGO')
        use_static (bool): Whether to return a static URL or just the path
        
    Returns:
        str: Banner URL or path
    """
    game_data = get_game_data(game_code)
    banner_path = game_data['banner']
    
    if use_static:
        return static(banner_path)
    return banner_path

def get_game_colors(game_code):
    """
    Get the primary and secondary colors for a game.
    
    Args:
        game_code (str): Game code (e.g., 'VALORANT', 'CSGO')
        
    Returns:
        dict: Dictionary with 'primary' and 'secondary' color keys
    """
    game_data = get_game_data(game_code)
    return {
        'primary': game_data['color_primary'],
        'secondary': game_data['color_secondary']
    }

def get_all_games():
    """
    Get all available games.
    
    Returns:
        dict: Dictionary of all games with their data
    """
    return GAMES.copy()

def get_games_by_category(category):
    """
    Get all games in a specific category.
    
    Args:
        category (str): Category name (e.g., 'FPS', 'MOBA', 'Sports')
        
    Returns:
        dict: Dictionary of games in the specified category
    """
    return {
        code: data for code, data in GAMES.items() 
        if data['category'].upper() == category.upper()
    }

def get_games_by_platform(platform):
    """
    Get all games available on a specific platform.
    
    Args:
        platform (str): Platform name (e.g., 'PC', 'Mobile', 'Console')
        
    Returns:
        dict: Dictionary of games available on the specified platform
    """
    return {
        code: data for code, data in GAMES.items() 
        if platform in data['platform']
    }

# Template context processor
def game_assets_context(request):
    """
    Context processor to make game assets available in all templates.
    
    Add this to TEMPLATES['OPTIONS']['context_processors'] in settings.py:
    'apps.common.game_assets.game_assets_context'
    """
    return {
        'GAMES': GAMES,
        'get_game_logo': get_game_logo,
        'get_game_card': get_game_card,
        'get_game_icon': get_game_icon,
        'get_game_banner': get_game_banner,
        'get_game_colors': get_game_colors,
        'get_game_data': get_game_data,
    }