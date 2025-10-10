"""
Game-Specific Analytics Schema Definitions (Task 6)

This module defines the expected data structures for game-specific statistics
across different games supported by DeltaCrown.
"""

# Valorant Game-Specific Stats Schema
VALORANT_TEAM_STATS_SCHEMA = {
    'total_rounds_played': 0,
    'rounds_won': 0,
    'rounds_lost': 0,
    'attack_rounds_won': 0,
    'defense_rounds_won': 0,
    'maps_played': {},  # {map_name: {played: int, won: int}}
    'agent_usage': {},  # {agent_name: times_picked}
    'average_round_duration': 0.0,
    'clutch_rounds_won': 0,
    'eco_round_wins': 0,
    'first_bloods': 0,
    'aces': 0,
}

VALORANT_PLAYER_STATS_SCHEMA = {
    'kills': 0,
    'deaths': 0,
    'assists': 0,
    'kda_ratio': 0.0,
    'headshot_percentage': 0.0,
    'average_combat_score': 0.0,
    'first_bloods': 0,
    'clutches': 0,
    'aces': 0,
    'plants': 0,
    'defuses': 0,
    'favorite_agent': '',
    'agent_stats': {},  # {agent_name: {kills, deaths, matches_played}}
}

VALORANT_MATCH_STATS_SCHEMA = {
    'map': '',
    'total_rounds': 0,
    'attack_rounds_won': 0,
    'defense_rounds_won': 0,
    'team_combat_score': 0,
    'first_bloods': 0,
    'plants': 0,
    'defuses': 0,
    'overtime_rounds': 0,
}

# CS2 (Counter-Strike 2) Game-Specific Stats Schema
CS2_TEAM_STATS_SCHEMA = {
    'total_rounds_played': 0,
    'rounds_won': 0,
    'rounds_lost': 0,
    'rounds_won_ct': 0,
    'rounds_won_t': 0,
    'maps_played': {},  # {map_name: {played: int, won: int}}
    'bomb_plants': 0,
    'bomb_defuses': 0,
    'average_round_duration': 0.0,
    'eco_round_wins': 0,
    'force_buy_wins': 0,
    'clutch_rounds_won': 0,
}

CS2_PLAYER_STATS_SCHEMA = {
    'kills': 0,
    'deaths': 0,
    'assists': 0,
    'kd_ratio': 0.0,
    'adr': 0.0,  # Average Damage per Round
    'hltv_rating': 0.0,
    'headshot_percentage': 0.0,
    'clutches': 0,
    'clutch_success_rate': 0.0,
    '1v1_won': 0,
    'multi_kills': {'2k': 0, '3k': 0, '4k': 0, '5k': 0},
    'favorite_weapon': '',
    'mvp_stars': 0,
}

CS2_MATCH_STATS_SCHEMA = {
    'map': '',
    'total_rounds': 0,
    'ct_rounds_won': 0,
    't_rounds_won': 0,
    'total_damage': 0,
    'bomb_plants': 0,
    'bomb_defuses': 0,
    'overtime': False,
}

# Dota 2 Game-Specific Stats Schema
DOTA2_TEAM_STATS_SCHEMA = {
    'total_kills': 0,
    'total_deaths': 0,
    'total_assists': 0,
    'average_match_duration': 0.0,
    'towers_destroyed': 0,
    'barracks_destroyed': 0,
    'roshan_kills': 0,
    'side_preference': {'radiant': 0, 'dire': 0},
    'side_winrate': {'radiant': 0.0, 'dire': 0.0},
    'average_gpm': 0.0,  # Gold per minute
    'average_xpm': 0.0,  # Experience per minute
    'hero_picks': {},  # {hero_name: times_picked}
}

DOTA2_PLAYER_STATS_SCHEMA = {
    'kills': 0,
    'deaths': 0,
    'assists': 0,
    'kda_ratio': 0.0,
    'average_gpm': 0.0,
    'average_xpm': 0.0,
    'hero_damage': 0,
    'tower_damage': 0,
    'hero_healing': 0,
    'last_hits': 0,
    'denies': 0,
    'favorite_hero': '',
    'favorite_role': '',  # carry, support, mid, offlane, jungle
    'hero_stats': {},  # {hero_name: {matches, wins, kda}}
    'rampage_count': 0,
    'ultra_kill_count': 0,
}

DOTA2_MATCH_STATS_SCHEMA = {
    'match_duration': 0,  # minutes
    'side': '',  # radiant or dire
    'total_kills': 0,
    'total_deaths': 0,
    'towers_destroyed': 0,
    'barracks_destroyed': 0,
    'roshan_kills': 0,
    'team_gold': 0,
    'team_xp': 0,
}

# MLBB (Mobile Legends: Bang Bang) Game-Specific Stats Schema
MLBB_TEAM_STATS_SCHEMA = {
    'total_kills': 0,
    'total_deaths': 0,
    'total_assists': 0,
    'average_match_duration': 0.0,
    'turrets_destroyed': 0,
    'lord_kills': 0,
    'turtle_kills': 0,
    'savage_count': 0,
    'maniac_count': 0,
    'hero_picks': {},  # {hero_name: times_picked}
    'gold_lead': 0,
}

MLBB_PLAYER_STATS_SCHEMA = {
    'kills': 0,
    'deaths': 0,
    'assists': 0,
    'kda_ratio': 0.0,
    'savage_count': 0,
    'maniac_count': 0,
    'triple_kill_count': 0,
    'mvp_count': 0,
    'gold_earned': 0,
    'damage_dealt': 0,
    'damage_taken': 0,
    'favorite_hero': '',
    'favorite_role': '',  # tank, fighter, assassin, mage, marksman, support
    'hero_stats': {},  # {hero_name: {matches, wins, kda}}
}

MLBB_MATCH_STATS_SCHEMA = {
    'match_duration': 0,  # minutes
    'total_kills': 0,
    'total_deaths': 0,
    'turrets_destroyed': 0,
    'lord_secured': False,
    'turtle_kills': 0,
    'team_gold': 0,
    'team_damage': 0,
}

# PUBG (Battle Royale) Game-Specific Stats Schema
PUBG_TEAM_STATS_SCHEMA = {
    'total_kills': 0,
    'total_deaths': 0,
    'total_assists': 0,
    'total_damage': 0,
    'average_placement': 0.0,
    'chicken_dinners': 0,  # Wins
    'top_10_finishes': 0,
    'survival_time': 0,  # Total minutes survived
    'distance_traveled': 0.0,  # km
    'revives': 0,
    'headshot_kills': 0,
    'longest_kill': 0.0,  # meters
    'map_stats': {},  # {map_name: {matches, wins, kills}}
}

PUBG_PLAYER_STATS_SCHEMA = {
    'kills': 0,
    'deaths': 0,
    'assists': 0,
    'damage_dealt': 0,
    'kd_ratio': 0.0,
    'average_damage': 0.0,
    'headshot_kills': 0,
    'headshot_percentage': 0.0,
    'survival_time': 0,  # Total minutes
    'distance_traveled': 0.0,  # km
    'revives': 0,
    'items_used': 0,
    'vehicles_destroyed': 0,
    'longest_kill': 0.0,  # meters
}

PUBG_MATCH_STATS_SCHEMA = {
    'map': '',
    'placement': 0,
    'team_kills': 0,
    'team_damage': 0,
    'survival_time': 0,  # minutes
    'revives': 0,
    'distance_traveled': 0.0,
}

# Free Fire Game-Specific Stats Schema
FREEFIRE_TEAM_STATS_SCHEMA = {
    'total_kills': 0,
    'total_deaths': 0,
    'booyahs': 0,  # Wins
    'top_3_finishes': 0,
    'total_damage': 0,
    'headshot_kills': 0,
    'survival_time': 0,
    'revives': 0,
    'character_usage': {},  # {character_name: times_used}
}

FREEFIRE_PLAYER_STATS_SCHEMA = {
    'kills': 0,
    'deaths': 0,
    'kd_ratio': 0.0,
    'damage_dealt': 0,
    'headshot_kills': 0,
    'headshot_percentage': 0.0,
    'survival_time': 0,
    'revives': 0,
    'favorite_character': '',
    'favorite_weapon': '',
}

FREEFIRE_MATCH_STATS_SCHEMA = {
    'placement': 0,
    'team_kills': 0,
    'team_damage': 0,
    'survival_time': 0,  # minutes
    'revives': 0,
}

# eFootball / FC26 Game-Specific Stats Schema
EFOOTBALL_TEAM_STATS_SCHEMA = {
    'goals_scored': 0,
    'goals_conceded': 0,
    'clean_sheets': 0,
    'shots_on_target': 0,
    'shots_total': 0,
    'possession_avg': 0.0,
    'pass_accuracy': 0.0,
    'tackles_won': 0,
    'fouls_committed': 0,
    'yellow_cards': 0,
    'red_cards': 0,
    'formation_usage': {},  # {formation: times_used}
}

EFOOTBALL_PLAYER_STATS_SCHEMA = {
    'goals': 0,
    'assists': 0,
    'shots': 0,
    'shots_on_target': 0,
    'pass_accuracy': 0.0,
    'tackles': 0,
    'interceptions': 0,
    'saves': 0,  # for goalkeepers
    'clean_sheets': 0,  # for goalkeepers
    'yellow_cards': 0,
    'red_cards': 0,
    'minutes_played': 0,
    'favorite_position': '',
    'rating_avg': 0.0,
}

EFOOTBALL_MATCH_STATS_SCHEMA = {
    'goals_scored': 0,
    'goals_conceded': 0,
    'shots': 0,
    'shots_on_target': 0,
    'possession': 0.0,
    'pass_accuracy': 0.0,
    'tackles': 0,
    'fouls': 0,
    'yellow_cards': 0,
    'red_cards': 0,
    'formation': '',
}

# CODM (Call of Duty Mobile) Game-Specific Stats Schema
CODM_TEAM_STATS_SCHEMA = {
    'total_kills': 0,
    'total_deaths': 0,
    'total_assists': 0,
    'kd_ratio': 0.0,
    'domination_wins': 0,
    'snd_wins': 0,  # Search and Destroy
    'hardpoint_wins': 0,
    'tdm_wins': 0,  # Team Deathmatch
    'map_stats': {},  # {map_name: {matches, wins}}
    'mode_preference': {},  # {mode: matches_played}
}

CODM_PLAYER_STATS_SCHEMA = {
    'kills': 0,
    'deaths': 0,
    'assists': 0,
    'kd_ratio': 0.0,
    'accuracy': 0.0,
    'headshot_percentage': 0.0,
    'scorestreaks_earned': 0,
    'objectives_captured': 0,
    'favorite_weapon': '',
    'favorite_mode': '',
    'weapon_stats': {},  # {weapon: {kills, accuracy}}
}

CODM_MATCH_STATS_SCHEMA = {
    'mode': '',  # TDM, Domination, S&D, Hardpoint
    'map': '',
    'team_kills': 0,
    'team_deaths': 0,
    'objectives_captured': 0,
    'scorestreaks_used': 0,
}

# Game Schema Registry
GAME_STATS_SCHEMAS = {
    'valorant': {
        'team': VALORANT_TEAM_STATS_SCHEMA,
        'player': VALORANT_PLAYER_STATS_SCHEMA,
        'match': VALORANT_MATCH_STATS_SCHEMA,
    },
    'cs2': {
        'team': CS2_TEAM_STATS_SCHEMA,
        'player': CS2_PLAYER_STATS_SCHEMA,
        'match': CS2_MATCH_STATS_SCHEMA,
    },
    'dota2': {
        'team': DOTA2_TEAM_STATS_SCHEMA,
        'player': DOTA2_PLAYER_STATS_SCHEMA,
        'match': DOTA2_MATCH_STATS_SCHEMA,
    },
    'mlbb': {
        'team': MLBB_TEAM_STATS_SCHEMA,
        'player': MLBB_PLAYER_STATS_SCHEMA,
        'match': MLBB_MATCH_STATS_SCHEMA,
    },
    'pubg': {
        'team': PUBG_TEAM_STATS_SCHEMA,
        'player': PUBG_PLAYER_STATS_SCHEMA,
        'match': PUBG_MATCH_STATS_SCHEMA,
    },
    'freefire': {
        'team': FREEFIRE_TEAM_STATS_SCHEMA,
        'player': FREEFIRE_PLAYER_STATS_SCHEMA,
        'match': FREEFIRE_MATCH_STATS_SCHEMA,
    },
    'efootball': {
        'team': EFOOTBALL_TEAM_STATS_SCHEMA,
        'player': EFOOTBALL_PLAYER_STATS_SCHEMA,
        'match': EFOOTBALL_MATCH_STATS_SCHEMA,
    },
    'fc26': {  # Same as eFootball
        'team': EFOOTBALL_TEAM_STATS_SCHEMA,
        'player': EFOOTBALL_PLAYER_STATS_SCHEMA,
        'match': EFOOTBALL_MATCH_STATS_SCHEMA,
    },
    'codm': {
        'team': CODM_TEAM_STATS_SCHEMA,
        'player': CODM_PLAYER_STATS_SCHEMA,
        'match': CODM_MATCH_STATS_SCHEMA,
    },
}


def get_game_schema(game: str, stat_type: str) -> dict:
    """
    Get the statistics schema for a specific game and stat type.
    
    Args:
        game: Game identifier (e.g., 'valorant', 'cs2')
        stat_type: Type of stats ('team', 'player', or 'match')
    
    Returns:
        Dictionary schema for the requested game and stat type
    
    Raises:
        KeyError: If game or stat_type not found
    """
    game_lower = game.lower()
    if game_lower not in GAME_STATS_SCHEMAS:
        raise KeyError(f"Unknown game: {game}. Available: {list(GAME_STATS_SCHEMAS.keys())}")
    
    if stat_type not in GAME_STATS_SCHEMAS[game_lower]:
        raise KeyError(f"Unknown stat_type: {stat_type}. Available: team, player, match")
    
    return GAME_STATS_SCHEMAS[game_lower][stat_type].copy()


def validate_game_stats(game: str, stat_type: str, stats_data: dict) -> tuple[bool, list]:
    """
    Validate game-specific statistics data against the schema.
    
    Args:
        game: Game identifier
        stat_type: Type of stats ('team', 'player', or 'match')
        stats_data: The statistics data to validate
    
    Returns:
        Tuple of (is_valid, errors_list)
    """
    try:
        schema = get_game_schema(game, stat_type)
    except KeyError as e:
        return False, [str(e)]
    
    errors = []
    
    # Check for unexpected keys
    extra_keys = set(stats_data.keys()) - set(schema.keys())
    if extra_keys:
        errors.append(f"Unexpected keys: {extra_keys}")
    
    # Check data types match schema
    for key, expected_value in schema.items():
        if key in stats_data:
            actual_value = stats_data[key]
            expected_type = type(expected_value)
            actual_type = type(actual_value)
            
            if expected_type != actual_type:
                errors.append(
                    f"Type mismatch for '{key}': expected {expected_type.__name__}, "
                    f"got {actual_type.__name__}"
                )
    
    return len(errors) == 0, errors
