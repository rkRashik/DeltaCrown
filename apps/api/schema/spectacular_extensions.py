"""
Phase 9, Epic 9.1 - drf-spectacular Schema Extensions

Custom preprocessing hooks and component schemas for DTOs and façade services.
Ensures accurate OpenAPI schema generation for DeltaCrown's DTO-based architecture.
"""

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from typing import Any, Dict


def preprocess_dto_serializers(endpoints):
    """
    Preprocessing hook for drf-spectacular to handle DTO serializers.
    
    This hook runs before schema generation and can modify endpoint definitions
    to ensure DTOs are properly represented in the OpenAPI schema.
    
    Args:
        endpoints: List of endpoint tuples (path, path_regex, method, callback)
        
    Returns:
        Modified endpoints list
    """
    # For now, return endpoints unchanged
    # Future: Add custom DTO schema transformations here
    return endpoints


# Component schema definitions for common DTOs
# These are referenced in SPECTACULAR_SETTINGS['COMPONENT_SCHEMAS']

TOURNAMENT_DTO_SCHEMA = {
    "type": "object",
    "properties": {
        "tournament_id": {"type": "integer", "description": "Unique tournament identifier"},
        "name": {"type": "string", "description": "Tournament name"},
        "game_slug": {"type": "string", "description": "Game identifier (e.g., 'valorant', 'csgo')"},
        "format": {
            "type": "string",
            "enum": ["single_elimination", "double_elimination", "round_robin", "swiss", "group_stage"],
            "description": "Tournament format",
        },
        "status": {
            "type": "string",
            "enum": ["draft", "registration_open", "registration_closed", "in_progress", "completed", "cancelled"],
            "description": "Tournament status",
        },
        "max_participants": {"type": "integer", "description": "Maximum participants allowed"},
        "entry_fee": {"type": "number", "format": "decimal", "description": "Entry fee amount"},
        "prize_pool": {"type": "number", "format": "decimal", "description": "Total prize pool"},
        "start_date": {"type": "string", "format": "date-time", "description": "Tournament start date"},
        "registration_deadline": {"type": "string", "format": "date-time", "description": "Registration deadline"},
    },
    "required": ["tournament_id", "name", "game_slug", "format", "status"],
}

REGISTRATION_DTO_SCHEMA = {
    "type": "object",
    "properties": {
        "registration_id": {"type": "integer", "description": "Unique registration identifier"},
        "tournament_id": {"type": "integer", "description": "Tournament ID"},
        "participant_type": {
            "type": "string",
            "enum": ["user", "team"],
            "description": "Type of participant",
        },
        "participant_id": {"type": "integer", "description": "User or team ID"},
        "status": {
            "type": "string",
            "enum": ["pending", "approved", "rejected", "withdrawn"],
            "description": "Registration status",
        },
        "payment_status": {
            "type": "string",
            "enum": ["not_required", "pending", "completed", "failed", "refunded"],
            "description": "Payment status",
        },
        "registered_at": {"type": "string", "format": "date-time", "description": "Registration timestamp"},
    },
    "required": ["registration_id", "tournament_id", "participant_type", "participant_id", "status"],
}

MATCH_DTO_SCHEMA = {
    "type": "object",
    "properties": {
        "match_id": {"type": "integer", "description": "Unique match identifier"},
        "tournament_id": {"type": "integer", "description": "Tournament ID"},
        "round_number": {"type": "integer", "description": "Round number in bracket"},
        "match_number": {"type": "integer", "description": "Match number within round"},
        "participant1_type": {"type": "string", "enum": ["user", "team"], "description": "First participant type"},
        "participant1_id": {"type": "integer", "description": "First participant ID", "nullable": True},
        "participant2_type": {"type": "string", "enum": ["user", "team"], "description": "Second participant type"},
        "participant2_id": {"type": "integer", "description": "Second participant ID", "nullable": True},
        "status": {
            "type": "string",
            "enum": ["scheduled", "in_progress", "completed", "cancelled", "disputed"],
            "description": "Match status",
        },
        "scheduled_at": {"type": "string", "format": "date-time", "description": "Scheduled time", "nullable": True},
        "winner_type": {"type": "string", "enum": ["user", "team"], "description": "Winner type", "nullable": True},
        "winner_id": {"type": "integer", "description": "Winner ID", "nullable": True},
        "score": {"type": "object", "description": "Match score (game-specific format)", "nullable": True},
    },
    "required": ["match_id", "tournament_id", "round_number", "match_number", "status"],
}

USER_STATS_DTO_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {"type": "integer", "description": "User identifier"},
        "game_slug": {"type": "string", "description": "Game identifier"},
        "matches_played": {"type": "integer", "description": "Total matches played"},
        "matches_won": {"type": "integer", "description": "Total matches won"},
        "matches_lost": {"type": "integer", "description": "Total matches lost"},
        "matches_drawn": {"type": "integer", "description": "Total matches drawn"},
        "win_rate": {"type": "number", "format": "decimal", "description": "Win rate percentage (0-100)"},
        "current_streak": {"type": "integer", "description": "Current win/loss streak (+/-)"},
        "longest_win_streak": {"type": "integer", "description": "Longest consecutive wins"},
        "total_kills": {"type": "integer", "description": "Total kills"},
        "total_deaths": {"type": "integer", "description": "Total deaths"},
        "total_assists": {"type": "integer", "description": "Total assists"},
        "kd_ratio": {"type": "number", "format": "decimal", "description": "Kill/Death ratio"},
        "elo_rating": {"type": "integer", "description": "ELO rating"},
        "mmr": {"type": "integer", "description": "Matchmaking rating"},
    },
    "required": ["user_id", "game_slug", "matches_played"],
}

TEAM_STATS_DTO_SCHEMA = {
    "type": "object",
    "properties": {
        "team_id": {"type": "integer", "description": "Team identifier"},
        "game_slug": {"type": "string", "description": "Game identifier"},
        "matches_played": {"type": "integer", "description": "Total matches played"},
        "matches_won": {"type": "integer", "description": "Total matches won"},
        "matches_lost": {"type": "integer", "description": "Total matches lost"},
        "matches_drawn": {"type": "integer", "description": "Total matches drawn"},
        "win_rate": {"type": "number", "format": "decimal", "description": "Win rate percentage (0-100)"},
        "elo_rating": {"type": "integer", "description": "ELO rating"},
        "tier": {
            "type": "string",
            "enum": ["bronze", "silver", "gold", "diamond", "crown"],
            "description": "Current tier",
        },
        "synergy_score": {"type": "number", "format": "decimal", "description": "Team synergy score (0-100)"},
        "activity_score": {"type": "number", "format": "decimal", "description": "Team activity score (0-100)"},
    },
    "required": ["team_id", "game_slug", "matches_played"],
}

ANALYTICS_DTO_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {"type": "integer", "description": "User identifier", "nullable": True},
        "team_id": {"type": "integer", "description": "Team identifier", "nullable": True},
        "game_slug": {"type": "string", "description": "Game identifier"},
        "mmr_snapshot": {"type": "integer", "description": "MMR snapshot"},
        "elo_snapshot": {"type": "integer", "description": "ELO snapshot"},
        "win_rate": {"type": "number", "format": "decimal", "description": "Win rate percentage"},
        "kda_ratio": {"type": "number", "format": "decimal", "description": "KDA ratio"},
        "tier": {
            "type": "string",
            "enum": ["bronze", "silver", "gold", "diamond", "crown"],
            "description": "Current tier",
        },
        "percentile_rank": {"type": "number", "format": "decimal", "description": "Percentile rank (0-100)"},
        "recalculated_at": {"type": "string", "format": "date-time", "description": "Last recalculation time"},
    },
    "required": ["game_slug"],
}

LEADERBOARD_ENTRY_DTO_SCHEMA = {
    "type": "object",
    "properties": {
        "leaderboard_type": {
            "type": "string",
            "enum": ["global_user", "game_user", "team", "seasonal", "mmr", "elo", "tier"],
            "description": "Leaderboard type",
        },
        "rank": {"type": "integer", "description": "Current rank"},
        "reference_id": {"type": "integer", "description": "User or team ID"},
        "game_slug": {"type": "string", "description": "Game identifier", "nullable": True},
        "season_id": {"type": "string", "description": "Season identifier", "nullable": True},
        "score": {"type": "integer", "description": "Score/rating"},
        "wins": {"type": "integer", "description": "Total wins"},
        "losses": {"type": "integer", "description": "Total losses"},
        "win_rate": {"type": "number", "format": "decimal", "description": "Win rate percentage"},
        "payload": {"type": "object", "description": "Additional metadata"},
        "computed_at": {"type": "string", "format": "date-time", "description": "Computation timestamp"},
    },
    "required": ["leaderboard_type", "rank", "reference_id", "score"],
}

# Export all component schemas for use in SPECTACULAR_SETTINGS
COMPONENT_SCHEMAS = {
    "TournamentDTO": TOURNAMENT_DTO_SCHEMA,
    "RegistrationDTO": REGISTRATION_DTO_SCHEMA,
    "MatchDTO": MATCH_DTO_SCHEMA,
    "UserStatsDTO": USER_STATS_DTO_SCHEMA,
    "TeamStatsDTO": TEAM_STATS_DTO_SCHEMA,
    "AnalyticsDTO": ANALYTICS_DTO_SCHEMA,
    "LeaderboardEntryDTO": LEADERBOARD_ENTRY_DTO_SCHEMA,
}
