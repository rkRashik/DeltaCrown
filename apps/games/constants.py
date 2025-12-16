"""
DeltaCrown Platform - Supported Games Configuration
===================================================
Central configuration for all 11 games supported on the platform (December 2025).
"""

# Official list of 11 supported games on DeltaCrown platform
SUPPORTED_GAMES = {
    'valorant': {
        'name': 'Valorant',
        'display_name': 'VALORANT',
        'short_code': 'VAL',
        'category': 'FPS',
        'id_field': 'riot_id',
        'id_label': 'Riot ID',
        'id_placeholder': 'PlayerName#TAG',
        'id_help': 'Your Riot ID with tagline (e.g., TenZ#1234)',
    },
    'cs2': {
        'name': 'Counter-Strike 2',
        'display_name': 'Counter-Strike 2',
        'short_code': 'CS2',
        'category': 'FPS',
        'id_field': 'steam_id',
        'id_label': 'Steam ID',
        'id_placeholder': '76561198000000000',
        'id_help': 'Your 17-digit Steam ID64',
    },
    'dota2': {
        'name': 'Dota 2',
        'display_name': 'Dota 2',
        'short_code': 'DOTA',
        'category': 'MOBA',
        'id_field': 'steam_id',
        'id_label': 'Steam ID',
        'id_placeholder': '76561198000000000',
        'id_help': 'Your 17-digit Steam ID64',
    },
    'ea-fc': {
        'name': 'EA Sports FC 26',
        'display_name': 'EA SPORTS FC™ 26',
        'short_code': 'FC26',
        'category': 'SPORTS',
        'id_field': 'ea_id',
        'id_label': 'EA ID',
        'id_placeholder': 'YourEAID',
        'id_help': 'Your EA Account ID',
    },
    'efootball': {
        'name': 'eFootball',
        'display_name': 'eFootball™ 2026',
        'short_code': 'EFB',
        'category': 'SPORTS',
        'id_field': 'efootball_id',
        'id_label': 'eFootball ID',
        'id_placeholder': 'PlayerID',
        'id_help': 'Your eFootball user ID',
    },
    'pubgm': {
        'name': 'PUBG Mobile',
        'display_name': 'PUBG MOBILE',
        'short_code': 'PUBGM',
        'category': 'BR',
        'id_field': 'pubgm_id',
        'id_label': 'Character ID',
        'id_placeholder': '5123456789',
        'id_help': 'Your PUBG Mobile Character ID (found in profile)',
    },
    'mlbb': {
        'name': 'Mobile Legends: Bang Bang',
        'display_name': 'Mobile Legends: Bang Bang',
        'short_code': 'MLBB',
        'category': 'MOBA',
        'id_field': 'mlbb_id',
        'id_label': 'Game ID',
        'id_placeholder': '123456789',
        'id_help': 'Your MLBB Game ID (found in profile)',
    },
    'freefire': {
        'name': 'Free Fire',
        'display_name': 'Free Fire',
        'short_code': 'FF',
        'category': 'BR',
        'id_field': 'freefire_id',
        'id_label': 'Player ID',
        'id_placeholder': '1234567890',
        'id_help': 'Your Free Fire Player ID',
    },
    'codm': {
        'name': 'Call of Duty: Mobile',
        'display_name': 'Call of Duty®: Mobile',
        'short_code': 'CODM',
        'category': 'FPS',
        'id_field': 'codm_uid',
        'id_label': 'UID',
        'id_placeholder': '6000000000',
        'id_help': 'Your COD Mobile UID (found in profile)',
    },
    'rocketleague': {
        'name': 'Rocket League',
        'display_name': 'Rocket League',
        'short_code': 'RL',
        'category': 'SPORTS',
        'id_field': 'epic_id',
        'id_label': 'Epic Games ID',
        'id_placeholder': 'YourEpicID',
        'id_help': 'Your Epic Games account name',
    },
    'r6siege': {
        'name': 'Rainbow Six Siege',
        'display_name': 'Tom Clancy\'s Rainbow Six® Siege',
        'short_code': 'R6',
        'category': 'FPS',
        'id_field': 'ubisoft_id',
        'id_label': 'Ubisoft Username',
        'id_placeholder': 'YourUbisoftName',
        'id_help': 'Your Ubisoft Connect username',
    },
}

# List of all game slugs
ALL_GAMES = list(SUPPORTED_GAMES.keys())

# Featured games (shown on homepage)
FEATURED_GAMES = ['valorant', 'cs2', 'dota2', 'ea-fc', 'pubgm', 'mlbb', 'rocketleague', 'r6siege']

# Games by category
GAMES_BY_CATEGORY = {
    'FPS': ['valorant', 'cs2', 'codm', 'r6siege'],
    'MOBA': ['dota2', 'mlbb'],
    'SPORTS': ['ea-fc', 'efootball', 'rocketleague'],
    'BR': ['pubgm', 'freefire'],
}


def get_game_info(game_slug):
    """Get game information by slug."""
    return SUPPORTED_GAMES.get(game_slug, None)


def get_game_choices():
    """Get choices for Django form fields."""
    return [(slug, info['display_name']) for slug, info in SUPPORTED_GAMES.items()]


def is_game_supported(game_slug):
    """Check if a game is supported."""
    return game_slug in SUPPORTED_GAMES


def get_featured_games():
    """Get list of featured game slugs."""
    return FEATURED_GAMES
