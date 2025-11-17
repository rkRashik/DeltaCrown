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
# Synced with Documents/Games/Game_Spec.md
GAMES = {
    'VALORANT': {
        'name': 'Valorant',
        'display_name': 'Valorant',
        'slug': 'valorant',
        'logo': 'img/game_logos/Valorant_logo.jpg',
        'card': 'img/game_cards/Valorant.jpg',
        'icon': 'logos/valorant.svg',
        'banner': 'img/game_banners/valorant_banner.jpg',
        'color_primary': '#FF4655',
        'color_secondary': '#0F1419',
        'category': 'FPS',
        'type': 'Team vs Team',
        'platform': ['PC'],
        'team_size': '5v5',
        'roster_size': '5-7',
        'player_id_label': 'Riot ID',
        'player_id_format': 'PlayerName#TAG',
        'player_id_placeholder': 'Example: Player#1234',
    },
    
    'CS2': {
        'name': 'CS2',
        'display_name': 'Counter-Strike 2',
        'slug': 'cs2',
        'logo': 'img/game_logos/CS2_logo.jpeg',
        'card': 'img/game_cards/CS2.jpg',
        'icon': 'img/game_icons/cs2_icon.png',
        'banner': 'img/game_banners/cs2_banner.jpg',
        'color_primary': '#F79100',
        'color_secondary': '#1B1B1B',
        'category': 'FPS',
        'type': 'Team vs Team',
        'platform': ['PC'],
        'team_size': '5v5',
        'roster_size': '5-7',
        'player_id_label': 'Steam ID',
        'player_id_format': 'steamID64',
        'player_id_placeholder': 'Example: 76561198123456789',
    },
    
    'DOTA2': {
        'name': 'Dota 2',
        'display_name': 'Dota 2',
        'slug': 'dota2',
        'logo': 'img/game_logos/Dota2_logo.jpg',
        'card': 'img/game_cards/Dota2.jpg',
        'icon': 'img/game_logos/Dota2_logo.jpg',
        'banner': 'img/game_cards/Dota2.jpg',
        'color_primary': '#E62E04',
        'color_secondary': '#000000',
        'category': 'MOBA',
        'type': 'Team vs Team',
        'platform': ['PC'],
        'team_size': '5v5',
        'roster_size': '5-7',
        'player_id_label': 'Steam ID',
        'player_id_format': 'steamID64',
        'player_id_placeholder': 'Example: 76561198123456789',
    },
    
    'EFOOTBALL': {
        'name': 'eFootball',
        'display_name': 'eFootball PES',
        'slug': 'efootball',
        'logo': 'img/game_logos/efootball_logo.jpeg',
        'card': 'img/game_cards/efootball.jpeg',
        'icon': 'logos/efootball.svg',
        'banner': 'img/game_banners/efootball_banner.jpg',
        'color_primary': '#00A0E4',
        'color_secondary': '#003366',
        'category': 'Sports',
        'type': '1v1 (Solo)',
        'platform': ['PC', 'Mobile', 'Console'],
        'team_size': '1v1',
        'roster_size': '1-2',
        'player_id_label': 'Konami ID',
        'player_id_format': 'Username',
        'player_id_placeholder': 'Example: PlayerName',
    },
    
    'FC26': {
        'name': 'FC26',
        'display_name': 'EA Sports FC 26',
        'slug': 'fc26',
        'logo': 'img/game_logos/fc26_logo.jpg',
        'card': 'img/game_cards/FC26.jpg',
        'icon': 'logos/fc26.svg',
        'banner': 'img/game_banners/fc26_banner.jpg',
        'color_primary': '#00D4FF',
        'color_secondary': '#003366',
        'category': 'Sports',
        'type': '1v1 (Solo)',
        'platform': ['PC', 'Console', 'Mobile'],
        'team_size': '1v1',
        'roster_size': '1',
        'player_id_label': 'EA ID',
        'player_id_format': 'Username, PSN, or Xbox',
        'player_id_placeholder': 'Example: PlayerName',
    },
    
    'MLBB': {
        'name': 'Mobile Legends',
        'display_name': 'Mobile Legends: Bang Bang',
        'slug': 'mlbb',
        'logo': 'img/game_logos/mobile_legend_logo.jpeg',
        'card': 'img/game_cards/MobileLegend.jpg',
        'icon': 'logos/mlbb.svg',
        'banner': 'img/game_banners/mlbb_banner.jpg',
        'color_primary': '#4A90E2',
        'color_secondary': '#1E3A8A',
        'category': 'MOBA',
        'type': 'Team vs Team',
        'platform': ['Mobile'],
        'team_size': '5v5',
        'roster_size': '5-6',
        'player_id_label': 'User ID + Zone ID',
        'player_id_format': 'User ID (Zone ID)',
        'player_id_placeholder': 'Example: 123456 (7890)',
    },
    
    'CODM': {
        'name': 'Call of Duty Mobile',
        'display_name': 'Call of Duty: Mobile',
        'slug': 'codm',
        'logo': 'img/game_logos/CallOfDutyMobile_logo.jpg',
        'card': 'img/game_cards/CallOfDutyMobile.jpg',
        'icon': 'img/game_logos/CallOfDutyMobile_logo.jpg',
        'banner': 'img/game_cards/CallOfDutyMobile.jpg',
        'color_primary': '#FF6900',
        'color_secondary': '#000000',
        'category': 'FPS',
        'type': 'Team vs Team',
        'platform': ['Mobile'],
        'team_size': '5v5',
        'roster_size': '5-6',
        'player_id_label': 'IGN / UID',
        'player_id_format': 'In-Game Name or UID',
        'player_id_placeholder': 'Example: PlayerName or 1234567890',
    },
    
    'FREEFIRE': {
        'name': 'Free Fire',
        'display_name': 'Free Fire',
        'slug': 'freefire',
        'logo': 'img/game_logos/FreeFire_logo.jpg',
        'card': 'img/game_cards/FreeFire.jpeg',
        'icon': 'img/game_logos/FreeFire_logo.jpg',
        'banner': 'img/game_banners/freefire_banner.jpg',
        'color_primary': '#FF6B35',
        'color_secondary': '#2C1810',
        'category': 'Battle Royale',
        'type': 'Battle Royale',
        'platform': ['Mobile'],
        'team_size': '4-Player Squads',
        'roster_size': '4',
        'player_id_label': 'IGN / UID',
        'player_id_format': 'In-Game Name or UID',
        'player_id_placeholder': 'Example: PlayerName or 1234567890',
    },
    
    'PUBG': {
        'name': 'PUBG',
        'display_name': 'PlayerUnknown\'s Battlegrounds',
        'slug': 'pubg',
        'logo': 'img/game_logos/pubg_logo.png',
        'card': 'img/game_cards/PUBG.jpeg',
        'icon': 'img/game_logos/pubg_logo.png',
        'banner': 'img/game_banners/pubg_banner.jpg',
        'color_primary': '#F4A623',
        'color_secondary': '#1C1C1E',
        'category': 'Battle Royale',
        'type': 'Battle Royale',
        'platform': ['PC', 'Mobile', 'Console'],
        'team_size': '4-Player Squads',
        'roster_size': '4',
        'player_id_label': 'IGN / UID',
        'player_id_format': 'In-Game Name or UID',
        'player_id_placeholder': 'Example: PlayerName or 1234567890',
    },
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