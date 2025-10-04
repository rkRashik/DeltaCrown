# apps/tournaments/views/detail_enhanced.py
"""
Enhanced Detail View with Complete Data Loading
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from django.apps import apps
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.core.cache import cache

# Schedule helpers for backward compatibility
from apps.tournaments.utils.schedule_helpers import (
    get_schedule_field, is_registration_open, is_tournament_live,
    optimize_queryset_for_schedule, get_schedule_context
)

# Capacity helpers for backward compatibility
from apps.tournaments.utils.capacity_helpers import (
    get_capacity_field, is_tournament_full, get_available_slots,
    can_accept_registrations, get_capacity_status_text,
    optimize_queryset_for_capacity, get_capacity_context
)

# Finance helpers for backward compatibility
from apps.tournaments.utils.finance_helpers import (
    get_entry_fee, get_prize_pool, is_free_tournament,
    format_entry_fee, format_prize_pool, has_prize_pool,
    optimize_queryset_for_finance, get_finance_context
)

# Models
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
Match = apps.get_model("tournaments", "Match")


def can_view_sensitive(request_user, tournament: Tournament) -> bool:
    """
    Check if user can view sensitive data (participants, bracket).
    Criteria: Registered + tournament has started OR is staff/organizer
    
    Args:
        request_user: Django User object (request.user)
        tournament: Tournament instance
    """
    # Staff can always view
    if request_user and hasattr(request_user, 'is_authenticated'):
        if request_user.is_authenticated and request_user.is_staff:
            return True
    
    # Tournament must have started
    now = timezone.now()
    start_at = get_schedule_field(tournament, 'start_at')
    if start_at and now < start_at:
        return False
    
    # User must be authenticated
    if not request_user or not hasattr(request_user, 'is_authenticated') or not request_user.is_authenticated:
        return False
    
    # Get UserProfile instance
    try:
        user_profile = request_user.userprofile
    except (AttributeError, Exception):
        return False
    
    # Check if user is registered
    is_registered = Registration.objects.filter(
        tournament=tournament,
        user=user_profile,
        status='CONFIRMED'
    ).exists()
    
    return is_registered


def is_user_registered(request_user, tournament: Tournament) -> bool:
    """
    Check if user is registered for this tournament.
    
    Args:
        request_user: Django User object (request.user)
        tournament: Tournament instance
    """
    if not request_user or not hasattr(request_user, 'is_authenticated') or not request_user.is_authenticated:
        return False
    
    # Get UserProfile instance
    try:
        user_profile = request_user.userprofile
    except (AttributeError, Exception):
        return False
    
    return Registration.objects.filter(
        tournament=tournament,
        user=user_profile,
        status__in=['PENDING', 'CONFIRMED']
    ).exists()


def load_participants(tournament: Tournament) -> List[Dict[str, Any]]:
    """
    Load and format participant data for display.
    Returns list of participant dicts with relevant info.
    """
    registrations = Registration.objects.filter(
        tournament=tournament,
        status='CONFIRMED'
    ).select_related(
        'user',
        'team'
    ).order_by('created_at')
    
    participants = []
    is_team_event = False
    if hasattr(tournament, 'settings') and tournament.settings:
        min_team_size = getattr(tournament.settings, 'min_team_size', None)
        max_team_size = getattr(tournament.settings, 'max_team_size', None)
        is_team_event = (min_team_size and min_team_size > 1) or (max_team_size and max_team_size > 1)
    
    for idx, reg in enumerate(registrations, start=1):
        if is_team_event and reg.team:
            # Team tournament
            participants.append({
                'seed': idx,
                'team_name': reg.team.name,
                'name': reg.team.name,  # Alias for template consistency
                'team_logo': reg.team.logo.url if reg.team.logo else None,
                'logo': reg.team.logo.url if reg.team.logo else None,  # Alias for template consistency
                'avatar': None,  # Teams don't have avatars
                'captain': reg.team.captain.display_name if hasattr(reg.team, 'captain') and reg.team.captain else None,
                'status': reg.get_status_display(),
                'verified': reg.payment_verified if hasattr(reg, 'payment_verified') else False,
            })
        else:
            # Solo tournament
            user_profile = reg.user.profile if hasattr(reg.user, 'profile') else None
            participants.append({
                'seed': idx,
                'name': user_profile.display_name if user_profile else (
                    reg.user.username if hasattr(reg.user, 'username') else 'Unknown'
                ),
                'avatar': user_profile.avatar.url if user_profile and user_profile.avatar else None,
                'logo': None,  # Solo participants don't have logos
                'team_logo': None,  # Solo participants don't have team logos
                'status': reg.get_status_display(),
                'verified': reg.payment_verified if hasattr(reg, 'payment_verified') else False,
            })
    
    return participants


def load_standings(tournament: Tournament) -> List[Dict[str, Any]]:
    """
    Load current tournament standings/rankings.
    """
    # Check if we have standings data
    if hasattr(tournament, 'standings') and tournament.standings.exists():
        standings = tournament.standings.all().select_related(
            'team', 'player'
        ).order_by('rank')
        
        return [{
            'rank': s.rank,
            'name': s.team.name if s.team else (
                s.player.display_name if hasattr(s.player, 'display_name') 
                else (s.player.user.username if hasattr(s.player, 'user') and hasattr(s.player.user, 'username') else 'Unknown')
            ),
            'points': s.points if hasattr(s, 'points') else 0,
            'wins': s.wins if hasattr(s, 'wins') else 0,
            'losses': s.losses if hasattr(s, 'losses') else 0,
        } for s in standings]
    
    # Fallback: Calculate from match results if Match model exists
    if Match is not None:
        # This would require match result processing logic
        # For now, return empty
        pass
    
    return []


def get_bracket_data(tournament: Tournament) -> Optional[Dict[str, Any]]:
    """Get bracket data for tournament."""
    # Check if bracket URL is available
    if hasattr(tournament, 'bracket_url') and tournament.bracket_url:
        return {
            'url': tournament.bracket_url,
            'type': 'embed'
        }
    
    # Check settings for bracket
    if hasattr(tournament, 'settings') and tournament.settings:
        if hasattr(tournament.settings, 'bracket_url') and tournament.settings.bracket_url:
            return {
                'url': tournament.settings.bracket_url,
                'type': 'embed'
            }
    
    return None


def format_prizes(tournament: Tournament) -> List[Dict[str, Any]]:
    """
    Format prize data for display.
    Returns list of prizes ordered by place.
    """
    if not hasattr(tournament, 'prizes') or not tournament.prizes.exists():
        return []
    
    prizes = tournament.prizes.all().order_by('place')
    
    return [{
        'place': p.place,
        'cash': int(p.cash_bdt) if hasattr(p, 'cash_bdt') and p.cash_bdt else None,
        'coin': int(p.coin_amount) if hasattr(p, 'coin_amount') and p.coin_amount else None,
        'other': p.description if hasattr(p, 'description') else None,
    } for p in prizes]


def get_rules_data(tournament: Tournament) -> Dict[str, Any]:
    """Get tournament rules and related PDFs."""
    rules = {}
    
    # Check settings for rules
    if hasattr(tournament, 'settings') and tournament.settings:
        settings = tournament.settings
        
        if hasattr(settings, 'rules_html') and settings.rules_html:
            rules['text'] = settings.rules_html
        elif hasattr(settings, 'rules_text') and settings.rules_text:
            rules['text'] = settings.rules_text
        
        if hasattr(settings, 'rules_pdf') and settings.rules_pdf:
            rules['pdf_url'] = settings.rules_pdf.url
        
        if hasattr(settings, 'additional_rules') and settings.additional_rules:
            rules['extra'] = settings.additional_rules
    
    return rules


def get_tournament_stats(tournament: Tournament) -> Dict[str, Any]:
    """
    Get various statistics for the tournament.
    Uses capacity helpers for backward compatibility.
    """
    # Registration count
    total_registrations = Registration.objects.filter(
        tournament=tournament
    ).count()
    
    confirmed_registrations = Registration.objects.filter(
        tournament=tournament,
        status='CONFIRMED'
    ).count()
    
    # Slots - use capacity helpers with fallback
    slots_total = get_capacity_field(tournament, 'slot_size') or get_capacity_field(tournament, 'max_teams', 0)
    slots_taken = confirmed_registrations
    slots_available = get_available_slots(tournament)
    
    # Financial info - use finance helpers
    entry_fee = get_entry_fee(tournament)
    prize_pool = get_prize_pool(tournament)
    
    return {
        'total_registrations': total_registrations,
        'confirmed_registrations': confirmed_registrations,
        'slots_total': slots_total,
        'slots_taken': slots_taken,
        'slots_available': slots_available,
        'is_full': is_tournament_full(tournament),
        'capacity_status': get_capacity_status_text(tournament),
        'can_register': can_accept_registrations(tournament),
        # Financial data
        'entry_fee': entry_fee,
        'prize_pool': prize_pool,
        'is_free': is_free_tournament(tournament),
        'has_prizes': has_prize_pool(tournament),
        'formatted_entry_fee': format_entry_fee(tournament),
        'formatted_prize_pool': format_prize_pool(tournament),
    }


def get_related_tournaments(tournament: Tournament, limit: int = 4) -> List[Any]:
    """
    Get related tournaments (same game, similar timing).
    Optimized for schedule and capacity access.
    """
    related = Tournament.objects.filter(
        game=tournament.game,
        status__in=['PUBLISHED', 'RUNNING']
    ).exclude(
        id=tournament.id
    ).order_by('-created_at')[:limit]
    
    # Optimize for schedule, capacity, and finance access (prevents N+1 queries)
    related = optimize_queryset_for_schedule(related)
    related = optimize_queryset_for_capacity(related)
    related = optimize_queryset_for_finance(related)
    
    # Annotate with computed fields
    from .public import annotate_cards
    return annotate_cards(list(related))


def build_tabs(tournament: Tournament, user) -> List[str]:
    """
    Build list of available tabs based on tournament data.
    """
    tabs = ['overview', 'info', 'prizes']
    
    # Add participants tab if can view
    if can_view_sensitive(user, tournament):
        tabs.append('participants')
        tabs.append('bracket')
    
    # Add standings if available
    if hasattr(tournament, 'standings') and tournament.standings.exists():
        tabs.append('standings')
    
    # Add live tab if tournament is running
    if tournament.status == 'RUNNING':
        tabs.append('live')
    
    # Always add rules and support
    tabs.extend(['rules', 'policy', 'support'])
    
    return tabs


def build_schedule_context(tournament: Tournament) -> Dict[str, Any]:
    """Build schedule information for display."""
    # Try schedule model first, then settings, then tournament
    if hasattr(tournament, 'schedule'):
        schedule = tournament.schedule
        starts_at = schedule.start_at
        ends_at = schedule.end_at
        reg_open = schedule.reg_open_at
        reg_close = schedule.reg_close_at
        check_in_open_mins = schedule.check_in_open_mins
        check_in_close_mins = schedule.check_in_close_mins
    else:
        settings = tournament.settings if hasattr(tournament, 'settings') and tournament.settings else None
        starts_at = tournament.start_at or (getattr(settings, 'start_at', None) if settings else None)
        ends_at = tournament.end_at
        reg_open = getattr(settings, 'reg_open_at', None) if settings else getattr(tournament, 'reg_open_at', None)
        reg_close = getattr(settings, 'reg_close_at', None) if settings else getattr(tournament, 'reg_close_at', None)
        check_in_open_mins = getattr(settings, 'check_in_open_mins', None) if settings else None
        check_in_close_mins = getattr(settings, 'check_in_close_mins', None) if settings else None

    # Derive check-in open/close datetimes from minutes offsets if available
    checkin_open = None
    checkin_close = None
    if starts_at:
        from datetime import timedelta
        if check_in_open_mins:
            checkin_open = starts_at - timedelta(minutes=int(check_in_open_mins))
        if check_in_close_mins:
            checkin_close = starts_at - timedelta(minutes=int(check_in_close_mins))

    return {
        'starts_at': starts_at,
        'ends_at': ends_at,
        'reg_open': reg_open,
        'reg_close': reg_close,
        'checkin_open': checkin_open,
        'checkin_close': checkin_close,
    }


def build_format_context(tournament: Tournament) -> Dict[str, Any]:
    """Build format information for display."""
    settings = tournament.settings if hasattr(tournament, 'settings') and tournament.settings else None
    # Compute is_team_event from min/max team size if available
    min_team_size = getattr(settings, 'min_team_size', None) if settings else None
    max_team_size = getattr(settings, 'max_team_size', None) if settings else None
    is_team_event = (min_team_size and min_team_size > 1) or (max_team_size and max_team_size > 1)

    return {
        'type': getattr(settings, 'tournament_type', None) if settings else None,
        'best_of': getattr(settings, 'best_of', None) if settings and hasattr(settings, 'best_of') else None,
        'team_min': min_team_size,
        'team_max': max_team_size,
        'check_in_required': getattr(settings, 'auto_check_in', False) if settings else False,
        'is_team_event': bool(is_team_event),
    }


def build_slots_context(tournament: Tournament) -> Dict[str, Any]:
    """Build slots information."""
    stats = get_tournament_stats(tournament)
    
    return {
        'capacity': stats['slots_total'],
        'current': stats['slots_taken'],
        'available': stats['slots_available'],
        'is_full': stats['is_full'],
    }


def detail_enhanced(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Enhanced tournament detail view with complete data loading.
    
    Features:
    - Comprehensive context with all tab data
    - Proper permission checks for sensitive data
    - Optimized queries with select_related/prefetch_related
    - Real-time statistics
    - Related tournaments
    """
    
    # Get tournament with related data
    tournament = get_object_or_404(
        Tournament.objects.select_related('settings')
                          .prefetch_related('registrations'),
        slug=slug
    )
    
    # Permission checks
    user_profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    user_can_view_sensitive = can_view_sensitive(user_profile, tournament)
    user_is_registered = is_user_registered(user_profile, tournament)
    
    # Build comprehensive context
    ctx = {
        # Tournament data
        't': tournament,
        'title': tournament.name,
        'short_desc': tournament.short_description,
        'desc_html': tournament.settings.description_html if hasattr(tournament, 'settings') and tournament.settings and hasattr(tournament.settings, 'description_html') else None,
        'banner': tournament.banner_url,
        'game': tournament.game_name,
        'game_slug': tournament.game,
        
        # Financial
        'entry_fee': tournament.entry_fee,
        'entry_fee_fmt': f"{int(tournament.entry_fee):,}" if tournament.entry_fee else None,
        'prize_pool': tournament.prize_pool,
        'prize_pool_fmt': f"{int(tournament.prize_pool):,}" if tournament.prize_pool else None,
        
        # Schedule & Format
        'schedule': build_schedule_context(tournament),
        'format': build_format_context(tournament),
        'slots': build_slots_context(tournament),
        
        # Platform info
        'region': 'Bangladesh',  # Could be from settings
        'platform': tournament.game_name,
        
        # Permissions
        'can_view_sensitive': user_can_view_sensitive,
        'is_registered_user': user_is_registered,
        
        # Data for tabs
        'participants': load_participants(tournament) if user_can_view_sensitive else [],
        'standings': load_standings(tournament),
        'bracket': get_bracket_data(tournament),
        'prizes': format_prizes(tournament),
        'rules': get_rules_data(tournament),
        'coin_policy': tournament.settings.coin_policy if hasattr(tournament, 'settings') and tournament.settings and hasattr(tournament.settings, 'coin_policy') else None,
        
        # UI state
        'tabs': build_tabs(tournament, request.user),
        'active_tab': request.GET.get('tab', 'overview'),
        'ui': {
            'show_live': tournament.status == 'RUNNING',
            'user_registration': user_is_registered,
        },
        
        # Additional data
        'stats': get_tournament_stats(tournament),
        'related': get_related_tournaments(tournament),
        
        # URLs
        'register_url': tournament.register_url if hasattr(tournament, 'register_url') else f'/tournaments/register-modern/{slug}/',
    }
    
    return render(request, 'tournaments/detail.html', {'ctx': ctx})
