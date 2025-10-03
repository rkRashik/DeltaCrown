"""
Helper utilities for TournamentCapacity access

Provides backward-compatible functions for accessing capacity data
during the migration period. Uses 3-tier fallback system:
1. Try tournament.capacity (new model)
2. Fall back to tournament.slot_size (old field)
3. Return default value

Author: DeltaCrown Development Team
Date: October 3, 2025
"""

from typing import Optional, Tuple
from django.db.models import QuerySet


def get_capacity_field(tournament, field_name: str, default=None):
    """
    Get a capacity field with 3-tier fallback.
    
    Args:
        tournament: Tournament instance
        field_name: Field name to retrieve
        default: Default value if all methods fail
        
    Returns:
        Field value or default
        
    Example:
        slot_size = get_capacity_field(tournament, 'slot_size', 16)
    """
    try:
        # Tier 1: Try new capacity model
        if hasattr(tournament, 'capacity') and tournament.capacity:
            return getattr(tournament.capacity, field_name, default)
    except Exception:
        pass
    
    # Tier 2: Try old tournament field (for backward compatibility)
    if hasattr(tournament, field_name):
        value = getattr(tournament, field_name, None)
        if value is not None:
            return value
    
    # Tier 3: Return default
    return default


def is_tournament_full(tournament) -> bool:
    """
    Check if tournament is at capacity.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        bool: True if tournament is full
        
    Example:
        if is_tournament_full(tournament):
            return "Tournament is full"
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            return tournament.capacity.is_full
    except Exception:
        pass
    
    # Fallback: Check registrations vs slot_size
    if hasattr(tournament, 'slot_size') and tournament.slot_size:
        from apps.tournaments.models.registration import TournamentRegistration
        current = TournamentRegistration.objects.filter(
            tournament=tournament,
            status__in=['pending', 'approved']
        ).count()
        return current >= tournament.slot_size
    
    return False


def get_available_slots(tournament) -> int:
    """
    Get number of available slots.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        int: Number of available slots (0 if full or no capacity)
        
    Example:
        slots = get_available_slots(tournament)
        print(f"{slots} slots remaining")
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            return tournament.capacity.available_slots
    except Exception:
        pass
    
    # Fallback: Calculate from slot_size
    if hasattr(tournament, 'slot_size') and tournament.slot_size:
        from apps.tournaments.models.registration import TournamentRegistration
        current = TournamentRegistration.objects.filter(
            tournament=tournament,
            status__in=['pending', 'approved']
        ).count()
        return max(0, tournament.slot_size - current)
    
    return 0


def can_accept_registrations(tournament) -> bool:
    """
    Check if tournament can accept new registrations.
    
    Considers registration mode, capacity, and waitlist settings.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        bool: True if can accept registrations
        
    Example:
        if can_accept_registrations(tournament):
            # Show registration button
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            return tournament.capacity.can_accept_registrations
    except Exception:
        pass
    
    # Fallback: Just check if not full
    return not is_tournament_full(tournament)


def validate_team_size(tournament, team_size: int) -> Tuple[bool, str]:
    """
    Validate if team size is acceptable for tournament.
    
    Args:
        tournament: Tournament instance
        team_size: Number of players in team
        
    Returns:
        tuple: (is_valid: bool, message: str)
        
    Example:
        is_valid, msg = validate_team_size(tournament, 5)
        if not is_valid:
            return JsonResponse({'error': msg}, status=400)
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            return tournament.capacity.validate_team_size(team_size)
    except Exception:
        pass
    
    # Fallback: Game-specific validation
    if tournament.game == 'valorant':
        min_size, max_size = 5, 7
        if team_size < min_size:
            return False, f'Valorant teams must have at least {min_size} players'
        if team_size > max_size:
            return False, f'Valorant teams cannot exceed {max_size} players'
        return True, 'Team size is valid'
    
    elif tournament.game == 'efootball':
        if team_size != 1:
            return False, 'eFootball is 1v1 - only solo players allowed'
        return True, 'Team size is valid'
    
    # Default: Allow 1-10 players
    if team_size < 1:
        return False, 'Team must have at least 1 player'
    if team_size > 10:
        return False, 'Team cannot exceed 10 players'
    return True, 'Team size is valid'


def get_registration_mode(tournament) -> str:
    """
    Get registration mode for tournament.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        str: Registration mode ('open', 'approval', 'invite')
        
    Example:
        mode = get_registration_mode(tournament)
        if mode == 'invite':
            return "This is an invite-only tournament"
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            return tournament.capacity.registration_mode
    except Exception:
        pass
    
    # Default: open registration
    return 'open'


def get_capacity_status_text(tournament) -> str:
    """
    Get human-readable capacity status.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        str: Status text like "8/16 (8 slots remaining)" or "FULL"
        
    Example:
        status = get_capacity_status_text(tournament)
        # Returns: "12/16 (4 slots remaining)"
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            return tournament.capacity.get_capacity_display()
    except Exception:
        pass
    
    # Fallback: Build from slot_size
    if hasattr(tournament, 'slot_size') and tournament.slot_size:
        from apps.tournaments.models.registration import TournamentRegistration
        current = TournamentRegistration.objects.filter(
            tournament=tournament,
            status__in=['pending', 'approved']
        ).count()
        
        if current >= tournament.slot_size:
            return f'FULL ({current}/{tournament.slot_size})'
        
        remaining = tournament.slot_size - current
        return f'{current}/{tournament.slot_size} ({remaining} slots remaining)'
    
    return 'Capacity not configured'


def optimize_queryset_for_capacity(queryset: QuerySet) -> QuerySet:
    """
    Optimize queryset to prefetch capacity data.
    
    Adds select_related('capacity') to prevent N+1 queries.
    
    Args:
        queryset: Tournament QuerySet
        
    Returns:
        QuerySet: Optimized queryset
        
    Example:
        tournaments = Tournament.objects.filter(status='PUBLISHED')
        tournaments = optimize_queryset_for_capacity(tournaments)
    """
    # Check if already has select_related
    if hasattr(queryset, 'query') and queryset.query.select_related:
        # Add capacity to existing select_related
        return queryset.select_related('capacity')
    
    return queryset.select_related('capacity')


def get_capacity_context(tournament) -> dict:
    """
    Get complete capacity data for template context.
    
    Returns dictionary with all capacity information for easy
    use in templates and views.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        dict: Complete capacity context
        
    Example:
        context = get_capacity_context(tournament)
        return render(request, 'tournament.html', context)
    """
    context = {
        'slot_size': get_capacity_field(tournament, 'slot_size', 0),
        'max_teams': get_capacity_field(tournament, 'max_teams', 0),
        'min_team_size': get_capacity_field(tournament, 'min_team_size', 1),
        'max_team_size': get_capacity_field(tournament, 'max_team_size', 10),
        'registration_mode': get_registration_mode(tournament),
        'is_full': is_tournament_full(tournament),
        'available_slots': get_available_slots(tournament),
        'can_register': can_accept_registrations(tournament),
        'status_text': get_capacity_status_text(tournament),
    }
    
    # Add capacity object if available
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            context['capacity'] = tournament.capacity
            context['has_capacity_model'] = True
            context['registration_progress'] = tournament.capacity.registration_progress_percent
            context['is_solo_tournament'] = tournament.capacity.is_solo_tournament
            context['waitlist_enabled'] = tournament.capacity.waitlist_enabled
        else:
            context['has_capacity_model'] = False
    except Exception:
        context['has_capacity_model'] = False
    
    return context


# Convenience functions for common operations
def increment_tournament_registrations(tournament, count: int = 1):
    """
    Safely increment tournament registration count.
    
    Args:
        tournament: Tournament instance
        count: Number to increment by
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            tournament.capacity.increment_registrations(count)
    except Exception:
        pass  # Silently fail for tournaments without capacity


def decrement_tournament_registrations(tournament, count: int = 1):
    """
    Safely decrement tournament registration count.
    
    Args:
        tournament: Tournament instance
        count: Number to decrement by
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            tournament.capacity.decrement_registrations(count)
    except Exception:
        pass  # Silently fail for tournaments without capacity


def refresh_tournament_capacity(tournament) -> int:
    """
    Refresh tournament capacity count from database.
    
    Args:
        tournament: Tournament instance
        
    Returns:
        int: Current registration count
    """
    try:
        if hasattr(tournament, 'capacity') and tournament.capacity:
            return tournament.capacity.refresh_registration_count()
    except Exception:
        pass
    
    # Fallback: Count manually
    from apps.tournaments.models.registration import TournamentRegistration
    return TournamentRegistration.objects.filter(
        tournament=tournament,
        status__in=['pending', 'approved']
    ).count()
