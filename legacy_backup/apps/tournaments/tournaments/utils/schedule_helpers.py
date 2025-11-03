# apps/tournaments/utils/schedule_helpers.py
"""
Helper utilities for accessing tournament schedule data.
Provides backward-compatible access during the migration period.

Usage in views:
    from apps.tournaments.utils.schedule_helpers import get_schedule_field
    
    reg_open = get_schedule_field(tournament, 'reg_open_at')
    is_open = is_registration_open(tournament)
"""
from django.utils import timezone
from typing import Any, Optional
from datetime import datetime


def get_schedule_field(tournament, field_name: str, default=None) -> Any:
    """
    Get a schedule field, checking schedule model first, then fallback to tournament.
    
    Args:
        tournament: Tournament instance
        field_name: Field name (e.g., 'reg_open_at', 'start_at', 'end_at')
        default: Default value if field not found
        
    Returns:
        Field value or default
        
    Example:
        reg_open = get_schedule_field(tournament, 'reg_open_at')
    """
    # Try schedule model first
    if hasattr(tournament, 'schedule'):
        try:
            schedule = tournament.schedule
            if hasattr(schedule, field_name):
                value = getattr(schedule, field_name)
                if value is not None:
                    return value
        except Exception:
            pass
    
    # Fallback to tournament model
    if hasattr(tournament, field_name):
        value = getattr(tournament, field_name)
        if value is not None:
            return value
    
    return default


def is_registration_open(tournament) -> bool:
    """
    Check if registration is currently open.
    Uses schedule model if available, else falls back to tournament.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        True if registration is open, False otherwise
    """
    # Try schedule model first
    if hasattr(tournament, 'schedule'):
        try:
            schedule = tournament.schedule
            return schedule.is_registration_open
        except Exception:
            pass
    
    # Fallback to tournament property
    if hasattr(tournament, 'registration_open'):
        return tournament.registration_open
    
    # Manual check as last resort
    reg_open_at = get_schedule_field(tournament, 'reg_open_at')
    reg_close_at = get_schedule_field(tournament, 'reg_close_at')
    
    if reg_open_at and reg_close_at:
        now = timezone.now()
        return reg_open_at <= now <= reg_close_at
    
    return False


def is_tournament_live(tournament) -> bool:
    """
    Check if tournament is currently live/running.
    Uses schedule model if available, else falls back to tournament.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        True if tournament is live, False otherwise
    """
    # Try schedule model first
    if hasattr(tournament, 'schedule'):
        try:
            schedule = tournament.schedule
            return schedule.is_tournament_live
        except Exception:
            pass
    
    # Fallback to tournament property
    if hasattr(tournament, 'is_live'):
        return tournament.is_live
    
    # Manual check as last resort
    start_at = get_schedule_field(tournament, 'start_at')
    end_at = get_schedule_field(tournament, 'end_at')
    
    if start_at and end_at:
        now = timezone.now()
        return start_at <= now <= end_at
    
    return False


def get_registration_status_text(tournament) -> str:
    """
    Get human-readable registration status.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        Status text like "Open", "Closed", "Opens Oct 5, 2025"
    """
    # Try schedule model first
    if hasattr(tournament, 'schedule'):
        try:
            schedule = tournament.schedule
            return schedule.registration_status
        except Exception:
            pass
    
    # Manual computation
    reg_open_at = get_schedule_field(tournament, 'reg_open_at')
    reg_close_at = get_schedule_field(tournament, 'reg_close_at')
    
    if not reg_open_at or not reg_close_at:
        return "Not scheduled"
    
    now = timezone.now()
    if now < reg_open_at:
        return f"Opens {reg_open_at.strftime('%b %d, %Y at %H:%M')}"
    elif now > reg_close_at:
        return "Closed"
    else:
        return "Open"


def get_tournament_status_text(tournament) -> str:
    """
    Get human-readable tournament status.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        Status text like "Live", "Completed", "Starts Oct 10, 2025"
    """
    # Try schedule model first
    if hasattr(tournament, 'schedule'):
        try:
            schedule = tournament.schedule
            return schedule.tournament_status
        except Exception:
            pass
    
    # Manual computation
    start_at = get_schedule_field(tournament, 'start_at')
    end_at = get_schedule_field(tournament, 'end_at')
    
    if not start_at:
        return "Not scheduled"
    
    now = timezone.now()
    if now < start_at:
        return f"Starts {start_at.strftime('%b %d, %Y at %H:%M')}"
    elif end_at and now > end_at:
        return "Completed"
    else:
        return "Live"


def optimize_queryset_for_schedule(queryset):
    """
    Optimize queryset to include schedule data efficiently.
    Adds select_related('schedule') to avoid N+1 queries.
    
    Args:
        queryset: Tournament queryset
        
    Returns:
        Optimized queryset
        
    Example:
        tournaments = Tournament.objects.all()
        tournaments = optimize_queryset_for_schedule(tournaments)
    """
    try:
        # Add select_related if not already present
        if not hasattr(queryset, '_prefetch_related_lookups'):
            return queryset.select_related('schedule')
        
        # Check if schedule is already in select_related
        select_related_fields = getattr(queryset.query, 'select_related', {})
        if 'schedule' not in select_related_fields:
            return queryset.select_related('schedule')
    except Exception:
        pass
    
    return queryset


def get_schedule_context(tournament) -> dict:
    """
    Get complete schedule context for templates.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        Dictionary with all schedule information
        
    Example:
        context = get_schedule_context(tournament)
        # Returns: {
        #     'reg_open_at': datetime,
        #     'reg_close_at': datetime,
        #     'start_at': datetime,
        #     'end_at': datetime,
        #     'is_registration_open': bool,
        #     'is_tournament_live': bool,
        #     'registration_status': str,
        #     'tournament_status': str,
        # }
    """
    return {
        'reg_open_at': get_schedule_field(tournament, 'reg_open_at'),
        'reg_close_at': get_schedule_field(tournament, 'reg_close_at'),
        'start_at': get_schedule_field(tournament, 'start_at'),
        'end_at': get_schedule_field(tournament, 'end_at'),
        'is_registration_open': is_registration_open(tournament),
        'is_tournament_live': is_tournament_live(tournament),
        'registration_status': get_registration_status_text(tournament),
        'tournament_status': get_tournament_status_text(tournament),
    }
