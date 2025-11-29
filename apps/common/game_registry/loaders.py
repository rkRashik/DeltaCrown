"""
Game Registry - Data Loaders Module
====================================

Loads and merges game configuration data from multiple sources:
1. Database Game model (apps.tournaments.models.Game) - PRIMARY SOURCE
2. Teams roster config (apps.teams.game_config.GAME_CONFIGS)
3. Asset definitions (game_registry.assets.GAME_ASSETS)
4. CSS theme variables (static/tournaments/detailPages/css/detail_theme.css)

The loader prioritizes database values (editable via Django admin) over static config.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ROSTER CONFIGURATIONS
# ============================================================================
# Imported from apps.teams.game_config to maintain single source

ROSTER_CONFIGS = {
    'valorant': {
        'min_starters': 5,
        'max_starters': 5,
        'max_substitutes': 3,
        'max_coach': 1,
        'max_analyst': 0,
        'total_max_roster': 9,
        'roles': ['Duelist', 'Controller', 'Initiator', 'Sentinel', 'Flex'],
        'role_descriptions': {
            'Duelist': 'Entry fragger, aggressive playmaker',
            'Controller': 'Smoke specialist, map control',
            'Initiator': 'Information gatherer, set up plays',
            'Sentinel': 'Defensive anchor, site holder',
            'IGL': 'In-game leader, shot caller',
            'Flex': 'Multi-role player, fills gaps',
        },
        'regions': [
            ('SA', 'South Asia (Bangladesh, India, Pakistan, Nepal, Sri Lanka)'),
            ('PAC', 'Pacific (Indonesia, Malaysia, Philippines, Singapore, Thailand)'),
            ('EA', 'East Asia (Japan, Korea, Taiwan)'),
            ('EMEA', 'EMEA (Europe, Middle East, Africa)'),
            ('AMER', 'Americas (North America, LATAM, Brazil)'),
            ('OCE', 'Oceania (Australia, New Zealand)'),
        ],
        'requires_unique_roles': False,
        'allows_multi_role': True,
    },
    'cs2': {
        'min_starters': 5,
        'max_starters': 5,
        'max_substitutes': 2,
        'max_coach': 1,
        'max_analyst': 0,
        'total_max_roster': 8,
        'roles': ['Entry Fragger', 'AWPer', 'Lurker', 'Support', 'Rifler'],
        'role_descriptions': {
            'IGL': 'In-game leader, strategist',
            'Entry Fragger': 'First contact, opens sites',
            'AWPer': 'Sniper specialist',
            'Lurker': 'Late-round player, flanks',
            'Support': 'Utility user, assists team',
            'Rifler': 'Versatile gunner',
        },
        'regions': [
            ('ASIA', 'Asia (South Asia, SEA, East Asia)'),
            ('EU_W', 'Europe West'),
            ('EU_E', 'Europe East'),
            ('NA', 'North America'),
            ('SA', 'South America'),
            ('CIS', 'CIS (Commonwealth of Independent States)'),
            ('MEA', 'Middle East & Africa'),
            ('OCE', 'Oceania'),
        ],
        'requires_unique_roles': False,
        'allows_multi_role': True,
    },
    'dota2': {
        'min_starters': 5,
        'max_starters': 5,
        'max_substitutes': 2,
        'max_coach': 1,
        'max_analyst': 0,
        'total_max_roster': 8,
        'roles': ['Position 1 (Carry)', 'Position 2 (Mid)', 'Position 3 (Offlane)', 
                  'Position 4 (Soft Support)', 'Position 5 (Hard Support)'],
        'role_descriptions': {
            'Position 1 (Carry)': 'Main damage dealer, farm priority',
            'Position 2 (Mid)': 'Mid lane, tempo controller',
            'Position 3 (Offlane)': 'Offlane, space creator',
            'Position 4 (Soft Support)': 'Roaming support, playmaker',
            'Position 5 (Hard Support)': 'Ward buyer, protector',
        },
        'regions': [
            ('SEA', 'Southeast Asia'),
            ('SA', 'South Asia'),
            ('CN', 'China'),
            ('EEU', 'Eastern Europe'),
            ('WEU', 'Western Europe'),
            ('NA', 'North America'),
            ('SAM', 'South America'),
            ('MEA', 'Middle East & Africa'),
        ],
        'requires_unique_roles': True,
        'allows_multi_role': False,
    },
    'mlbb': {
        'min_starters': 5,
        'max_starters': 5,
        'max_substitutes': 2,
        'max_coach': 1,
        'max_analyst': 1,
        'total_max_roster': 9,
        'roles': ['Gold Laner', 'EXP Laner', 'Mid Laner', 'Jungler', 'Roamer'],
        'role_descriptions': {
            'Gold Laner': 'Bot lane farmer, marksman',
            'EXP Laner': 'Top lane, tank/fighter',
            'Mid Laner': 'Mid lane mage/assassin',
            'Jungler': 'Jungle core, ganker',
            'Roamer': 'Support, rotator',
        },
        'regions': [
            ('SEA_PH', 'Southeast Asia (Philippines)'),
            ('SEA_ID', 'Southeast Asia (Indonesia)'),
            ('SEA_MY', 'Southeast Asia (Malaysia)'),
            ('SA', 'South Asia (Bangladesh, India, Pakistan, Nepal)'),
        ],
        'requires_unique_roles': False,
        'allows_multi_role': True,
    },
    'pubg': {
        'min_starters': 4,
        'max_starters': 4,
        'max_substitutes': 2,
        'max_coach': 1,
        'max_analyst': 0,
        'total_max_roster': 7,
        'roles': ['Assaulter/Fragger', 'Support', 'Sniper/Scout', 'Flex'],
        'role_descriptions': {
            'IGL/Shot Caller': 'Team leader, strategy caller',
            'Assaulter/Fragger': 'Aggressive pusher, entry',
            'Support': 'Utility user, healer',
            'Sniper/Scout': 'Long-range specialist',
        },
        'regions': [
            ('SA', 'South Asia (Bangladesh, India, Nepal, Pakistan)'),
            ('SEA', 'Southeast Asia (Indonesia, Vietnam, Malaysia)'),
        ],
        'requires_unique_roles': False,
        'allows_multi_role': True,
    },
    'freefire': {
        'min_starters': 4,
        'max_starters': 4,
        'max_substitutes': 2,
        'max_coach': 1,
        'max_analyst': 0,
        'total_max_roster': 7,
        'roles': ['Rusher', 'Flanker', 'Support', 'Defender'],
        'role_descriptions': {
            'Rusher': 'Aggressive entry, first contact',
            'Flanker': 'Side attacker, rotator',
            'Support': 'Team support, utility',
            'Shot Caller': 'Leader, strategist',
        },
        'regions': [
            ('SA', 'South Asia'),
            ('SEA', 'Southeast Asia'),
        ],
        'requires_unique_roles': False,
        'allows_multi_role': True,
    },
    'efootball': {
        'min_starters': 1,
        'max_starters': 2,
        'max_substitutes': 1,
        'max_coach': 1,
        'max_analyst': 0,
        'total_max_roster': 4,
        'roles': ['Player', 'Co-op Partner'],
        'role_descriptions': {
            'Player': 'Main player',
            'Co-op Partner': 'Co-op teammate',
        },
        'regions': [
            ('ASIA', 'Asia (Bangladesh, India, Japan, Korea)'),
            ('EU', 'Europe'),
        ],
        'requires_unique_roles': False,
        'allows_multi_role': False,
    },
    'fc26': {
        'min_starters': 1,
        'max_starters': 2,
        'max_substitutes': 1,
        'max_coach': 1,
        'max_analyst': 0,
        'total_max_roster': 4,
        'roles': ['Player'],
        'role_descriptions': {
            'Player': 'Individual player',
        },
        'regions': [
            ('ASIA', 'Asia'),
            ('EU', 'Europe'),
        ],
        'requires_unique_roles': False,
        'allows_multi_role': False,
    },
    'codm': {
        'min_starters': 5,
        'max_starters': 5,
        'max_substitutes': 1,
        'max_coach': 1,
        'max_analyst': 0,
        'total_max_roster': 7,
        'roles': ['Slayer', 'Anchor', 'Support', 'Objective Player', 'Flex'],
        'role_descriptions': {
            'IGL': 'In-game leader',
            'Slayer': 'High-kill fragger',
            'Anchor': 'Defensive holder',
            'Support': 'Team utility',
            'Objective Player': 'OBJ focused',
        },
        'regions': [
            ('ASIA', 'Asia'),
            ('EU', 'Europe'),
        ],
        'requires_unique_roles': False,
        'allows_multi_role': True,
    },
}


# ============================================================================
# CSS THEME VARIABLES
# ============================================================================
# Extracted from static/tournaments/detailPages/css/detail_theme.css

CSS_THEMES = {
    'valorant': {
        'accent': '#ff4655',
        'accent-soft': '#ff9aa4',
        'accent-glow': 'rgba(255, 70, 85, 0.5)',
        'bg-elevated': '#111823',
        'bg-surface': '#0b1018',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(17, 24, 35, 0.95), rgba(11, 16, 24, 0.98))',
    },
    'efootball': {
        'accent': '#00b0ff',
        'accent-soft': '#6fd0ff',
        'accent-glow': 'rgba(0, 176, 255, 0.5)',
        'bg-elevated': '#07101f',
        'bg-surface': '#050b14',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(7, 16, 31, 0.95), rgba(5, 11, 20, 0.98))',
    },
    'pubg-mobile': {
        'accent': '#f39c12',
        'accent-soft': '#f9c74f',
        'accent-glow': 'rgba(243, 156, 18, 0.5)',
        'bg-elevated': '#1a1410',
        'bg-surface': '#0f0b08',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(26, 20, 16, 0.95), rgba(15, 11, 8, 0.98))',
    },
    'fifa': {
        'accent': '#00ff87',
        'accent-soft': '#7fff9f',
        'accent-glow': 'rgba(0, 255, 135, 0.5)',
        'bg-elevated': '#0a1a12',
        'bg-surface': '#05100a',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(10, 26, 18, 0.95), rgba(5, 16, 10, 0.98))',
    },
    'free-fire': {
        'accent': '#ff6b35',
        'accent-soft': '#ff9470',
        'accent-glow': 'rgba(255, 107, 53, 0.5)',
        'bg-elevated': '#1a0f0a',
        'bg-surface': '#100805',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(26, 15, 10, 0.95), rgba(16, 8, 5, 0.98))',
    },
    'call-of-duty-mobile': {
        'accent': '#ff9500',
        'accent-soft': '#ffb84d',
        'accent-glow': 'rgba(255, 149, 0, 0.5)',
        'bg-elevated': '#1a1510',
        'bg-surface': '#0f0c08',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(26, 21, 16, 0.95), rgba(15, 12, 8, 0.98))',
    },
    'mobile-legends': {
        'accent': '#8e44ad',
        'accent-soft': '#b384c7',
        'accent-glow': 'rgba(142, 68, 173, 0.5)',
        'bg-elevated': '#15101a',
        'bg-surface': '#0b080f',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(21, 16, 26, 0.95), rgba(11, 8, 15, 0.98))',
    },
    'clash-of-clans': {
        'accent': '#ff6f00',
        'accent-soft': '#ff9f4d',
        'accent-glow': 'rgba(255, 111, 0, 0.5)',
        'bg-elevated': '#1a1208',
        'bg-surface': '#0f0a05',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(26, 18, 8, 0.95), rgba(15, 10, 5, 0.98))',
    },
    'league-of-legends': {
        'accent': '#0ac8b9',
        'accent-soft': '#5ae0d5',
        'accent-glow': 'rgba(10, 200, 185, 0.5)',
        'bg-elevated': '#081214',
        'bg-surface': '#040a0c',
        'bg-hero-overlay': 'linear-gradient(135deg, rgba(8, 18, 20, 0.95), rgba(4, 10, 12, 0.98))',
    },
}


# ============================================================================
# RESULT LOGIC DEFINITIONS
# ============================================================================
# From Documents/Games/Game_Spec.md

RESULT_LOGIC = {
    'valorant': {
        'type': 'map_score',
        'format': 'Map Score (e.g., 13-9)',
        'settings': 'Map Veto (Ban/Pick) system',
    },
    'cs2': {
        'type': 'map_score',
        'format': 'Map Score (e.g., 13-9)',
        'settings': 'Map Veto (Ban/Pick) system',
    },
    'dota2': {
        'type': 'best_of',
        'format': 'Best of X (e.g., 2-1)',
        'settings': 'Character Draft/Ban phase',
    },
    'efootball': {
        'type': 'game_score',
        'format': 'Game Score (e.g., 2-1)',
        'settings': 'Platform selection, cross-play toggle',
    },
    'fc26': {
        'type': 'game_score',
        'format': 'Game Score (e.g., 3-0)',
        'settings': 'Platform selection',
    },
    'mlbb': {
        'type': 'best_of',
        'format': 'Best of X (e.g., 2-1)',
        'settings': 'Character Draft/Ban phase',
    },
    'codm': {
        'type': 'best_of',
        'format': 'Best of 5 (across different modes like Hardpoint, S&D)',
        'settings': 'Item/Scorestreak/Perk bans',
    },
    'freefire': {
        'type': 'point_based',
        'format': 'Point-based (Kills + Final Placement)',
        'settings': 'Teams get points for Kills + Final Placement (e.g., 1st=12pts, 2nd=9pts)',
    },
    'pubg': {
        'type': 'point_based',
        'format': 'Point-based (Kills + Final Placement)',
        'settings': 'Teams get points for Kills + Final Placement',
    },
}


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_roster_config(slug: str) -> Optional[dict]:
    """Load roster configuration for a game."""
    return ROSTER_CONFIGS.get(slug)


def load_theme_variables(slug: str) -> Optional[dict]:
    """
    Load CSS theme variables for a game.
    
    Note: CSS uses different slug conventions (e.g., 'call-of-duty-mobile' vs 'codm')
    """
    # Try direct lookup first
    if slug in CSS_THEMES:
        return CSS_THEMES[slug]
    
    # Try CSS slug variations
    css_slug_map = {
        'codm': 'call-of-duty-mobile',
        'mlbb': 'mobile-legends',
        'pubg': 'pubg-mobile',
        'freefire': 'free-fire',
        'fc26': 'fifa',  # FIFA theme can be used for FC26
    }
    
    css_slug = css_slug_map.get(slug, slug)
    return CSS_THEMES.get(css_slug)


def load_result_logic(slug: str) -> Optional[dict]:
    """Load result logic configuration for a game."""
    return RESULT_LOGIC.get(slug)


def get_profile_id_field_mapping(slug: str) -> str:
    """
    Get the UserProfile field name for a game's player ID.
    
    Maps to actual field names in apps.user_profile.models.UserProfile
    """
    field_mapping = {
        'valorant': 'riot_id',
        'cs2': 'steam_id',
        'dota2': 'steam_id',
        'efootball': 'konami_id',
        'fc26': 'ea_id',
        'mlbb': 'mlbb_id',
        'codm': 'codm_id',
        'freefire': 'freefire_id',
        'pubg': 'pubg_id',
    }
    return field_mapping.get(slug, 'game_id')


def load_database_game(slug: str) -> Optional[dict]:
    """
    Load game data from the database Game model.
    
    This is now the PRIMARY data source for game specs.
    Database fields override all other sources (GAME_CONFIGS, assets, etc.)
    
    Returns None if database is not available or game doesn't exist.
    """
    try:
        from apps.tournaments.models import Game
        
        try:
            game = Game.objects.get(slug=slug, is_active=True)
            
            # Build complete data structure with all DB fields
            data = {
                'database_id': game.id,
                'name': game.name,
                'slug': game.slug,
                'description': game.description,
                'is_active': game.is_active,
                
                # Media assets (prioritize DB)
                'icon': game.icon.url if game.icon else None,
                'icon_field': game.icon,  # Keep field object for later checks
                'banner': game.banner.url if game.banner else None,
                'banner_field': game.banner,
                'card_image': game.card_image.url if game.card_image else None,
                'card_image_field': game.card_image,
                'logo': game.logo.url if game.logo else None,
                'logo_field': game.logo,
                
                # Presentation fields
                'primary_color': game.primary_color,
                'secondary_color': game.secondary_color,
                
                # Metadata fields
                'category': game.category,
                'platform': game.platform,
                
                # Team configuration
                'default_team_size': game.default_team_size,
                'min_team_size': game.min_team_size,
                'max_team_size': game.max_team_size,
                'roster_rules': game.roster_rules or {},
                'profile_id_field': game.profile_id_field,
                
                # Roles (optional)
                'roles': game.roles or [],
                
                # Result logic
                'default_result_type': game.default_result_type,
                'result_logic': game.result_logic or {},
                
                # Extra configuration (JSONB)
                'game_config': game.game_config or {},
                
                # Timestamps
                'created_at': game.created_at,
            }
            
            # Warn if critical fields are missing
            warnings = []
            if not game.icon:
                warnings.append(f"Game '{game.name}' ({slug}) is missing icon in database")
            if not game.description:
                warnings.append(f"Game '{game.name}' ({slug}) has no description in database")
            if not game.profile_id_field:
                warnings.append(f"Game '{game.name}' ({slug}) is missing profile_id_field in database")
            
            if warnings:
                for warning in warnings:
                    logger.warning(warning)
            
            return data
            
        except Game.DoesNotExist:
            logger.debug(f"No database Game found for slug: {slug}")
            return None
            
    except Exception as e:
        logger.debug(f"Could not load database game for {slug}: {e}")
        return None


def get_all_database_games() -> List[dict]:
    """
    Get all active games from the database.
    
    Returns:
        List of game data dictionaries from the database.
        Empty list if database is not available.
    """
    try:
        from apps.tournaments.models import Game
        
        games = Game.objects.filter(is_active=True)
        result = []
        
        for game in games:
            data = {
                'database_id': game.id,
                'name': game.name,
                'slug': game.slug,
                'description': game.description,
                'is_active': game.is_active,
                
                # Media assets (prioritize DB)
                'icon': game.icon.url if game.icon else None,
                'icon_field': game.icon,
                'banner': game.banner.url if game.banner else None,
                'banner_field': game.banner,
                'card_image': game.card_image.url if game.card_image else None,
                'card_image_field': game.card_image,
                'logo': game.logo.url if game.logo else None,
                'logo_field': game.logo,
                
                # Presentation fields
                'primary_color': game.primary_color,
                'secondary_color': game.secondary_color,
                
                # Metadata fields
                'category': game.category,
                'platform': game.platform,
                
                # Team configuration
                'default_team_size': game.default_team_size,
                'min_team_size': game.min_team_size,
                'max_team_size': game.max_team_size,
                'roster_rules': game.roster_rules or {},
                'profile_id_field': game.profile_id_field,
                
                # Roles (optional)
                'roles': game.roles or [],
                
                # Result logic
                'default_result_type': game.default_result_type,
                'result_logic': game.result_logic or {},
                
                # Extra configuration (JSONB)
                'game_config': game.game_config or {},
                
                # Timestamps
                'created_at': game.created_at,
            }
            result.append(data)
        
        return result
        
    except Exception as e:
        logger.debug(f"Could not load database games: {e}")
        return []
