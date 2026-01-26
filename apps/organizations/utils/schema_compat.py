"""
Schema compatibility helpers for vNext organizations app.

Provides utilities to check database schema and build queries that work
even when migrations haven't been applied yet (defensive programming).

Use Cases:
- Development: Allow hub to load before running migrations
- Testing: Support multiple migration states
- Rollback: Handle schema changes gracefully
"""

import logging
from django.db import connection

logger = logging.getLogger(__name__)

_SCHEMA_CACHE = {}


def _get_table_columns(table_name):
    """
    Get list of column names for a table using Django's introspection.
    
    Args:
        table_name: Full table name (e.g. 'organizations_team')
    
    Returns:
        set: Column names, or empty set if table doesn't exist
    
    Cache: Results cached for request lifetime (cleared on app reload)
    """
    if table_name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[table_name]
    
    try:
        with connection.cursor() as cursor:
            table_description = connection.introspection.get_table_description(
                cursor, table_name
            )
            columns = {row.name for row in table_description}
            _SCHEMA_CACHE[table_name] = columns
            return columns
    except Exception as e:
        logger.warning(f"Could not introspect table '{table_name}': {e}")
        _SCHEMA_CACHE[table_name] = set()
        return set()


def has_team_tag_columns():
    """
    Check if organizations_team table has tag and tagline columns.
    
    Returns:
        bool: True if both tag and tagline columns exist
    """
    columns = _get_table_columns('organizations_team')
    has_both = 'tag' in columns and 'tagline' in columns
    
    if not has_both:
        missing = []
        if 'tag' not in columns:
            missing.append('tag')
        if 'tagline' not in columns:
            missing.append('tagline')
        
        logger.warning(
            f"Schema mismatch detected: organizations_team missing columns: {missing}. "
            f"Hub will work in degraded mode. Run 'python manage.py migrate organizations' to fix.",
            extra={
                'event_type': 'schema_mismatch',
                'table': 'organizations_team',
                'missing_columns': missing,
            }
        )
    
    return has_both


def get_team_queryset_only_fields():
    """
    Get safe list of fields to use with Team.objects.only(...).
    
    Excludes tag/tagline if columns don't exist yet.
    
    Returns:
        list: Field names safe to use
    """
    # Base fields that always exist (from 0001_initial migration)
    base_fields = [
        'id', 'slug', 'name', 'status', 'game_id', 
        'organization_id', 'owner_id', 'created_at', 'updated_at',
    ]
    
    # Add optional fields if they exist
    if has_team_tag_columns():
        base_fields.extend(['tag', 'tagline'])
    
    return base_fields
