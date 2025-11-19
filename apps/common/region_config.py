"""
DeltaCrown Region Configuration
================================

Game-specific region mappings and configurations.
Different games support different regional servers/leagues.
"""

# Global regions (used as fallback)
GLOBAL_REGIONS = [
    ('NA', 'North America'),
    ('SA', 'South America'),
    ('EU', 'Europe'),
    ('SEA', 'Southeast Asia'),
    ('EA', 'East Asia'),
    ('OCE', 'Oceania'),
    ('ME', 'Middle East'),
    ('AF', 'Africa'),
]

# Game-specific region configurations
GAME_REGIONS = {
    'VALORANT': [
        ('NA', 'North America'),
        ('LATAM', 'Latin America'),
        ('BR', 'Brazil'),
        ('EU', 'Europe'),
        ('TR', 'Turkey'),
        ('CIS', 'CIS'),
        ('MENA', 'Middle East & North Africa'),
        ('KR', 'Korea'),
        ('JP', 'Japan'),
        ('APAC', 'Asia-Pacific'),
        ('OCE', 'Oceania'),
        ('SA', 'South Asia'),
    ],
    
    'CS2': [
        ('NA', 'North America'),
        ('SA', 'South America'),
        ('EU', 'Europe'),
        ('CIS', 'CIS'),
        ('MENA', 'Middle East & North Africa'),
        ('ASIA', 'Asia'),
        ('CN', 'China'),
        ('OCE', 'Oceania'),
    ],
    
    'DOTA2': [
        ('NA', 'North America'),
        ('SA', 'South America'),
        ('WEU', 'Western Europe'),
        ('EEU', 'Eastern Europe'),
        ('CN', 'China'),
        ('SEA', 'Southeast Asia'),
    ],
    
    'MLBB': [
        ('SEA', 'Southeast Asia'),
        ('ID', 'Indonesia'),
        ('MY-SG', 'Malaysia/Singapore'),
        ('PH', 'Philippines'),
        ('TH', 'Thailand'),
        ('VN', 'Vietnam'),
        ('MM', 'Myanmar'),
        ('BD', 'Bangladesh'),
        ('IN', 'India'),
        ('LATAM', 'Latin America'),
        ('NA', 'North America'),
    ],
    
    'PUBG': [
        ('NA', 'North America'),
        ('SA', 'South America'),
        ('EU', 'Europe'),
        ('AS', 'Asia'),
        ('KR-JP', 'Korea/Japan'),
        ('SEA', 'Southeast Asia'),
        ('MENA', 'Middle East & North Africa'),
    ],
    
    'FREEFIRE': [
        ('SEA', 'Southeast Asia'),
        ('ID', 'Indonesia'),
        ('TH', 'Thailand'),
        ('VN', 'Vietnam'),
        ('BD', 'Bangladesh'),
        ('IN', 'India'),
        ('LATAM', 'Latin America'),
        ('BR', 'Brazil'),
        ('NA', 'North America'),
        ('ME', 'Middle East'),
    ],
    
    'CODM': [
        ('NA', 'North America'),
        ('LATAM', 'Latin America'),
        ('EU', 'Europe'),
        ('MEA', 'Middle East & Africa'),
        ('IN', 'India'),
        ('SEA', 'Southeast Asia'),
        ('JP', 'Japan'),
        ('KR', 'Korea'),
        ('OCE', 'Oceania'),
    ],
    
    'EFOOTBALL': [
        ('EU', 'Europe'),
        ('NA', 'North America'),
        ('SA', 'South America'),
        ('ASIA', 'Asia'),
        ('ME', 'Middle East'),
        ('OCE', 'Oceania'),
        ('GLOBAL', 'Global (Cross-Platform)'),
    ],
    
    'FC26': [
        ('EU', 'Europe'),
        ('NA', 'North America'),
        ('SA', 'South America'),
        ('ASIA', 'Asia'),
        ('ME', 'Middle East'),
        ('OCE', 'Oceania'),
        ('GLOBAL', 'Global (Cross-Platform)'),
    ],
}

def get_regions_for_game(game_code):
    """
    Get available regions for a specific game.
    
    Args:
        game_code (str): Game code (e.g., 'VALORANT', 'CS2')
        
    Returns:
        list: List of (code, name) tuples for regions
    """
    game_code = game_code.upper() if game_code else ''
    return GAME_REGIONS.get(game_code, GLOBAL_REGIONS)

def get_all_regions():
    """
    Get all possible regions across all games.
    
    Returns:
        list: Deduplicated list of all regions
    """
    all_regions = set()
    for regions in GAME_REGIONS.values():
        all_regions.update(regions)
    all_regions.update(GLOBAL_REGIONS)
    return sorted(list(all_regions), key=lambda x: x[1])
