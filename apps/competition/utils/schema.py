"""Schema detection utilities for competition app.

This module provides lazy schema detection to avoid database introspection
during app initialization (AppConfig.ready()) or module import time.
"""
from django.db import connection


def competition_schema_ready(using='default') -> bool:
    """Check if competition schema tables exist in database.
    
    This function performs database introspection lazily when called,
    not during app initialization. Safe to call from admin.py or views.
    
    Args:
        using: Database alias to check (default: 'default')
    
    Returns:
        bool: True if all required competition tables exist, False otherwise
    
    Example:
        >>> from apps.competition.utils.schema import competition_schema_ready
        >>> if competition_schema_ready():
        ...     # Safe to import and register models
        ...     from apps.competition.models import GameRankingConfig
    """
    try:
        with connection.cursor() as cursor:
            # Get list of all tables in current database
            table_names = connection.introspection.table_names(cursor)
            
            # Check for core competition tables
            required_tables = {
                'competition_game_ranking_config',
                'competition_match_report',
                'competition_match_verification',
                'competition_team_game_ranking_snapshot',
                'competition_team_global_ranking_snapshot',
            }
            
            # Schema is ready if all required tables exist
            return required_tables.issubset(set(table_names))
    except Exception:
        # If we can't check (e.g., no database connection), assume not ready
        return False
