"""
Game Registry - Asset Paths Module
===================================

Centralized storage for all game media assets (logos, banners, icons, cards).
This module contains the raw asset data previously in apps/common/game_assets.py

IMPORTANT: This is now part of the Game Registry.
Access assets through the registry API, not directly from this module.
"""

from django.templatetags.static import static

# ============================================================================
# GAME ASSET DEFINITIONS
# ============================================================================
# These are the canonical asset paths for all supported games.
# Keys are UPPERCASE for historical compatibility, but the registry
# normalizes everything to lowercase slugs.

GAME_ASSETS = {
    'VALORANT': {
        'name': 'Valorant',
        'display_name': 'Valorant',
        'slug': 'valorant',
        'logo': 'img/game_logos/Valorant_logo.jpg',
        'card': 'img/game_cards/Valorant.jpg',
        'icon': 'img/game_logos/logos/valorant.svg',
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
        'icon': 'img/game_logos/logos/efootball.svg',
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
        'icon': 'img/game_logos/logos/fc26.svg',
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
        'icon': 'img/game_logos/logos/mlbb.svg',
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
    
    # Legacy CS:GO entry (maps to CS2)
    'CSGO': {
        'name': 'CS:GO',
        'display_name': 'Counter-Strike: Global Offensive',
        'slug': 'csgo',
        'logo': 'img/game_logos/CS2_logo.jpeg',  # Reuse CS2 assets
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
}

# Default fallback for unknown games
DEFAULT_GAME_ASSETS = {
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


# ============================================================================
# UTILITY FUNCTIONS (for backwards compatibility)
# ============================================================================

def get_asset_data(game_code: str) -> dict:
    """
    Get asset data for a game code.
    
    Args:
        game_code: Game code (case-insensitive)
        
    Returns:
        Dictionary of asset paths and metadata
    """
    return GAME_ASSETS.get(game_code.upper(), DEFAULT_GAME_ASSETS.copy())


def get_asset_url(game_code: str, asset_type: str, use_static: bool = True) -> str:
    """
    Get a specific asset URL for a game.
    
    Args:
        game_code: Game code
        asset_type: 'logo', 'card', 'icon', or 'banner'
        use_static: Whether to return static URL or just path
        
    Returns:
        Asset URL or path
    """
    asset_data = get_asset_data(game_code)
    asset_path = asset_data.get(asset_type, '')
    
    if not asset_path:
        return ''
    
    if use_static:
        return static(asset_path)
    return asset_path
