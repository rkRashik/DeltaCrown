# apps/teams/game_config.py
"""
Game-specific configuration for team roster management.

This module defines the rules, constraints, and roles for each supported game.
Makes it easy to add new games without changing core model logic.
"""
from typing import Dict, List, NamedTuple


class GameRosterConfig(NamedTuple):
    """Configuration for a game's team roster rules."""
    name: str
    code: str
    min_starters: int
    max_starters: int
    max_substitutes: int
    roles: List[str]
    role_descriptions: Dict[str, str]
    regions: List[tuple] = []  # Game-specific regions
    requires_unique_roles: bool = False
    allows_multi_role: bool = True


# ═══════════════════════════════════════════════════════════════════════════
# GAME ROSTER CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════════════

VALORANT_CONFIG = GameRosterConfig(
    name="Valorant",
    code="valorant",
    min_starters=5,
    max_starters=5,
    max_substitutes=2,
    roles=[
        "Duelist",
        "Controller", 
        "Initiator",
        "Sentinel",
        "IGL",
        "Flex",
    ],
    role_descriptions={
        "Duelist": "Entry fragger, aggressive playmaker",
        "Controller": "Smoke specialist, map control",
        "Initiator": "Information gatherer, set up plays",
        "Sentinel": "Defensive anchor, site holder",
        "IGL": "In-game leader, shot caller",
        "Flex": "Multi-role player, fills gaps",
    },
    regions=[
        ("SA", "South Asia (Bangladesh, India, Pakistan, Nepal, Sri Lanka)"),
        ("PAC", "Pacific (Indonesia, Malaysia, Philippines, Singapore, Thailand)"),
        ("EA", "East Asia (Japan, Korea, Taiwan)"),
        ("EMEA", "EMEA (Europe, Middle East, Africa)"),
        ("AMER", "Americas (North America, LATAM, Brazil)"),
        ("OCE", "Oceania (Australia, New Zealand)"),
    ],
    allows_multi_role=True,
)

CS2_CONFIG = GameRosterConfig(
    name="Counter-Strike 2",
    code="cs2",
    min_starters=5,
    max_starters=5,
    max_substitutes=2,
    roles=[
        "IGL",
        "Entry Fragger",
        "AWPer",
        "Lurker",
        "Support",
        "Rifler",
    ],
    role_descriptions={
        "IGL": "In-game leader, strategist",
        "Entry Fragger": "First contact, opens sites",
        "AWPer": "Sniper specialist",
        "Lurker": "Late-round player, flanks",
        "Support": "Utility user, assists team",
        "Rifler": "Versatile gunner",
    },
    regions=[
        ("ASIA", "Asia (South Asia, SEA, East Asia)"),
        ("EU_W", "Europe West"),
        ("EU_E", "Europe East"),
        ("NA", "North America"),
        ("SA", "South America"),
        ("CIS", "CIS (Commonwealth of Independent States)"),
        ("MEA", "Middle East & Africa"),
        ("OCE", "Oceania"),
    ],
    allows_multi_role=True,
)

DOTA2_CONFIG = GameRosterConfig(
    name="Dota 2",
    code="dota2",
    min_starters=5,
    max_starters=5,
    max_substitutes=2,
    roles=[
        "Position 1 (Carry)",
        "Position 2 (Mid)",
        "Position 3 (Offlane)",
        "Position 4 (Soft Support)",
        "Position 5 (Hard Support)",
    ],
    role_descriptions={
        "Position 1 (Carry)": "Main damage dealer, farm priority",
        "Position 2 (Mid)": "Mid lane, tempo controller",
        "Position 3 (Offlane)": "Offlane, space creator",
        "Position 4 (Soft Support)": "Roaming support, playmaker",
        "Position 5 (Hard Support)": "Ward buyer, protector",
    },
    regions=[
        ("SEA", "Southeast Asia"),
        ("SA", "South Asia"),
        ("CN", "China"),
        ("EEU", "Eastern Europe"),
        ("WEU", "Western Europe"),
        ("NA", "North America"),
        ("SAM", "South America"),
        ("MEA", "Middle East & Africa"),
    ],
    requires_unique_roles=True,  # Each position should be unique
    allows_multi_role=False,
)

MLBB_CONFIG = GameRosterConfig(
    name="Mobile Legends: Bang Bang",
    code="mlbb",
    min_starters=5,
    max_starters=5,
    max_substitutes=2,
    roles=[
        "Gold Laner",
        "EXP Laner",
        "Mid Laner",
        "Jungler",
        "Roamer",
    ],
    role_descriptions={
        "Gold Laner": "Bot lane farmer, marksman",
        "EXP Laner": "Top lane, tank/fighter",
        "Mid Laner": "Mid lane mage/assassin",
        "Jungler": "Jungle core, ganker",
        "Roamer": "Support, rotator",
    },
    regions=[
        ("SEA_PH", "Southeast Asia (Philippines)"),
        ("SEA_ID", "Southeast Asia (Indonesia)"),
        ("SEA_MY", "Southeast Asia (Malaysia)"),
        ("SEA_SG", "Southeast Asia (Singapore)"),
        ("SEA_TH", "Southeast Asia (Thailand)"),
        ("SA", "South Asia (Bangladesh, India, Pakistan, Nepal)"),
        ("EA", "East Asia (China, Taiwan, Japan)"),
        ("MENA", "Middle East & North Africa"),
        ("EU", "Europe"),
        ("LATAM", "Latin America"),
    ],
    requires_unique_roles=False,
    allows_multi_role=True,
)

PUBG_CONFIG = GameRosterConfig(
    name="PUBG Mobile",
    code="pubg",
    min_starters=4,
    max_starters=4,
    max_substitutes=2,
    roles=[
        "IGL/Shot Caller",
        "Assaulter/Fragger",
        "Support",
        "Sniper/Scout",
    ],
    role_descriptions={
        "IGL/Shot Caller": "Team leader, strategy caller",
        "Assaulter/Fragger": "Aggressive pusher, entry",
        "Support": "Utility user, healer",
        "Sniper/Scout": "Long-range specialist",
    },
    regions=[
        ("SA", "South Asia (Bangladesh, India, Nepal, Pakistan)"),
        ("SEA", "Southeast Asia (Indonesia, Vietnam, Malaysia)"),
        ("EA", "East Asia (China, Japan, Korea)"),
        ("MEA", "Middle East & Africa"),
        ("EU", "Europe"),
        ("AMER", "Americas"),
        ("OCE", "Oceania"),
    ],
    allows_multi_role=True,
)

FREEFIRE_CONFIG = GameRosterConfig(
    name="Free Fire",
    code="freefire",
    min_starters=4,
    max_starters=4,
    max_substitutes=2,
    roles=[
        "Rusher",
        "Flanker",
        "Support",
        "Shot Caller",
    ],
    role_descriptions={
        "Rusher": "Aggressive entry, first contact",
        "Flanker": "Side attacker, rotator",
        "Support": "Team support, utility",
        "Shot Caller": "Leader, strategist",
    },
    regions=[
        ("SA", "South Asia"),
        ("SEA", "Southeast Asia"),
        ("MENA", "Middle East"),
        ("EU", "Europe"),
        ("LATAM", "Latin America"),
        ("AF", "Africa"),
        ("BR", "Brazil"),
        ("NA", "North America"),
    ],
    allows_multi_role=True,
)

EFOOTBALL_CONFIG = GameRosterConfig(
    name="eFootball",
    code="efootball",
    min_starters=1,  # Can be solo
    max_starters=2,  # Co-op teams
    max_substitutes=1,
    roles=[
        "Player",
        "Co-op Partner",
    ],
    role_descriptions={
        "Player": "Main player",
        "Co-op Partner": "Co-op teammate",
    },
    regions=[
        ("ASIA", "Asia (Bangladesh, India, Japan, Korea)"),
        ("EU", "Europe"),
        ("NA", "North America"),
        ("SAM", "South America"),
        ("AF", "Africa"),
        ("ME", "Middle East"),
        ("OCE", "Oceania"),
    ],
    allows_multi_role=False,
)

FC26_CONFIG = GameRosterConfig(
    name="FC 26",
    code="fc26",
    min_starters=1,  # Solo player
    max_starters=1,
    max_substitutes=1,
    roles=[
        "Player",
    ],
    role_descriptions={
        "Player": "Individual player",
    },
    regions=[
        ("ASIA", "Asia"),
        ("EU", "Europe"),
        ("NA", "North America"),
        ("SAM", "South America"),
        ("AF", "Africa"),
        ("ME", "Middle East"),
        ("OCE", "Oceania"),
    ],
    allows_multi_role=False,
)

CODM_CONFIG = GameRosterConfig(
    name="Call of Duty Mobile",
    code="codm",
    min_starters=5,
    max_starters=5,
    max_substitutes=2,
    roles=[
        "IGL",
        "Slayer",
        "Anchor",
        "Support",
        "Objective Player",
    ],
    role_descriptions={
        "IGL": "In-game leader",
        "Slayer": "High-kill fragger",
        "Anchor": "Defensive holder",
        "Support": "Team utility",
        "Objective Player": "OBJ focused",
    },
    regions=[
        ("ASIA", "Asia"),
        ("EU", "Europe"),
        ("NA", "North America"),
        ("SAM", "South America"),
        ("MEA", "Middle East & Africa"),
        ("OCE", "Oceania"),
    ],
    allows_multi_role=True,
)

CSGO_CONFIG = GameRosterConfig(
    name="Counter-Strike: Global Offensive",
    code="csgo",
    min_starters=5,
    max_starters=5,
    max_substitutes=2,
    roles=[
        "IGL",
        "Entry Fragger",
        "AWPer",
        "Lurker",
        "Support",
        "Rifler",
    ],
    role_descriptions={
        "IGL": "In-game leader, strategist",
        "Entry Fragger": "First contact, opens sites",
        "AWPer": "Sniper specialist",
        "Lurker": "Late-round player, flanks",
        "Support": "Utility user, assists team",
        "Rifler": "Versatile gunner",
    },
    regions=[
        ("ASIA", "Asia (South Asia, SEA, East Asia)"),
        ("EU_W", "Europe West"),
        ("EU_E", "Europe East"),
        ("NA", "North America"),
        ("SA", "South America"),
        ("CIS", "CIS (Commonwealth of Independent States)"),
        ("MEA", "Middle East & Africa"),
        ("OCE", "Oceania"),
    ],
    allows_multi_role=True,
)


# ═══════════════════════════════════════════════════════════════════════════
# GAME REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

GAME_CONFIGS: Dict[str, GameRosterConfig] = {
    "valorant": VALORANT_CONFIG,
    "cs2": CS2_CONFIG,
    "dota2": DOTA2_CONFIG,
    "mlbb": MLBB_CONFIG,
    "pubg": PUBG_CONFIG,
    "freefire": FREEFIRE_CONFIG,
    "efootball": EFOOTBALL_CONFIG,
    "fc26": FC26_CONFIG,
    "codm": CODM_CONFIG,
    "csgo": CSGO_CONFIG,
}

# Game choices for model fields
GAME_CHOICES = tuple(
    (config.code, config.name) for config in GAME_CONFIGS.values()
)


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

# Game code normalization map - handles legacy/alternate names
GAME_CODE_ALIASES = {
    'pubg-mobile': 'pubg',
    'pubgm': 'pubg',
    'pubg_mobile': 'pubg',
    'free-fire': 'freefire',
    'free_fire': 'freefire',
    'cs-2': 'cs2',
    'cs_2': 'cs2',
    'counter-strike-2': 'cs2',
    'mlbb': 'mlbb',
    'mobile-legends': 'mlbb',
    'dota-2': 'dota2',
    'dota_2': 'dota2',
    'call-of-duty-mobile': 'codm',
    'cod-mobile': 'codm',
    'cod_mobile': 'codm',
    'efootball': 'efootball',
    'e-football': 'efootball',
    'fc-26': 'fc26',
    'fc_26': 'fc26',
    'counter-strike-go': 'csgo',
    'cs-go': 'csgo',
    'cs_go': 'csgo',
}


def normalize_game_code(game_code: str) -> str:
    """
    Normalize game code to standard format.
    
    Handles legacy game codes and alternate naming conventions.
    For example: 'pubg-mobile' → 'pubg', 'free-fire' → 'freefire'
    
    Args:
        game_code: Raw game identifier from database or user input
        
    Returns:
        Normalized game code that matches GAME_CONFIGS keys
    """
    if not game_code:
        return game_code
    
    # Lowercase and strip whitespace
    normalized = game_code.lower().strip()
    
    # Check if it needs aliasing
    if normalized in GAME_CODE_ALIASES:
        return GAME_CODE_ALIASES[normalized]
    
    return normalized


def get_game_config(game_code: str) -> GameRosterConfig:
    """
    Get configuration for a specific game.
    
    Args:
        game_code: Game identifier (e.g., 'valorant', 'cs2', 'pubg-mobile')
        
    Returns:
        GameRosterConfig for the game
        
    Raises:
        KeyError: If game code is not supported
    """
    # Normalize the game code first
    normalized_code = normalize_game_code(game_code)
    
    if normalized_code not in GAME_CONFIGS:
        raise KeyError(
            f"Unsupported game: {game_code} (normalized: {normalized_code}). "
            f"Available: {list(GAME_CONFIGS.keys())}"
        )
    return GAME_CONFIGS[normalized_code]


def get_max_roster_size(game_code: str) -> int:
    """
    Get maximum roster size (starters + substitutes) for a game.
    
    Args:
        game_code: Game identifier
        
    Returns:
        Maximum total roster size
    """
    config = get_game_config(game_code)
    return config.max_starters + config.max_substitutes


def get_min_roster_size(game_code: str) -> int:
    """
    Get minimum roster size for a game to be active.
    
    Args:
        game_code: Game identifier
        
    Returns:
        Minimum number of starters required
    """
    config = get_game_config(game_code)
    return config.min_starters


def get_available_roles(game_code: str) -> List[str]:
    """
    Get list of available roles for a game.
    
    Args:
        game_code: Game identifier
        
    Returns:
        List of role names
    """
    config = get_game_config(game_code)
    return config.roles


def validate_role_for_game(game_code: str, role: str) -> bool:
    """
    Check if a role is valid for a specific game.
    
    Args:
        game_code: Game identifier
        role: Role name to validate
        
    Returns:
        True if role is valid for the game
    """
    config = get_game_config(game_code)
    return role in config.roles


def get_role_description(game_code: str, role: str) -> str:
    """
    Get description for a role in a specific game.
    
    Args:
        game_code: Game identifier
        role: Role name
        
    Returns:
        Role description or empty string if not found
    """
    config = get_game_config(game_code)
    return config.role_descriptions.get(role, "")


def get_all_game_codes() -> List[str]:
    """Get list of all supported game codes."""
    return list(GAME_CONFIGS.keys())


def get_all_game_names() -> List[str]:
    """Get list of all supported game names."""
    return [config.name for config in GAME_CONFIGS.values()]
