"""
Phase 2 Enhanced Hub View with Complete Model Integration

Displays tournament listings with data from all 6 Phase 1 models.
"""
from __future__ import annotations
from typing import Any, Dict, List

from django.apps import apps
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator

# Phase 1 Models
Tournament = apps.get_model("tournaments", "Tournament")
TournamentSchedule = apps.get_model("tournaments", "TournamentSchedule")
TournamentCapacity = apps.get_model("tournaments", "TournamentCapacity")
TournamentFinance = apps.get_model("tournaments", "TournamentFinance")
TournamentMedia = apps.get_model("tournaments", "TournamentMedia")
TournamentRules = apps.get_model("tournaments", "TournamentRules")
TournamentArchive = apps.get_model("tournaments", "TournamentArchive")


def get_optimized_tournament_queryset():
    """
    Get optimized tournament queryset with all Phase 1 models preloaded.
    Prevents N+1 queries for list views.
    """
    return Tournament.objects.select_related(
        'game',
        'organizer',
        'schedule',
        'capacity',
        'finance',
        'media',
        'rules',
        'archive',
    ).filter(
        # Only show non-archived, published tournaments
        archive__is_archived=False,
        status__in=['PUBLISHED', 'RUNNING', 'COMPLETED']
    ).order_by('-created_at')


def annotate_tournament_card(tournament: Tournament) -> Dict[str, Any]:
    """
    Create a card data dict for a tournament using Phase 1 models.
    Used for displaying tournament cards in lists.
    """
    card = {
        'id': tournament.id,
        'name': tournament.name,
        'slug': tournament.slug if hasattr(tournament, 'slug') else '',
        'game': tournament.game.name if tournament.game else 'Unknown',
        'game_slug': tournament.game.slug if tournament.game else '',
        'status': tournament.status if hasattr(tournament, 'status') else 'UNKNOWN',
        'organizer': tournament.organizer.username if tournament.organizer else 'Unknown',
    }
    
    # Schedule data
    if hasattr(tournament, 'schedule') and tournament.schedule:
        schedule = tournament.schedule
        card['schedule'] = {
            'registration_open': schedule.is_registration_open(),
            'registration_upcoming': schedule.is_registration_upcoming(),
            'is_in_progress': schedule.is_in_progress(),
            'has_ended': schedule.has_ended(),
            'tournament_start': schedule.tournament_start,
            'tournament_end': schedule.tournament_end,
            'registration_end': schedule.registration_end,
            'days_until_start': schedule.get_days_until_start(),
        }
    else:
        card['schedule'] = {'registration_open': False}
    
    # Capacity data
    if hasattr(tournament, 'capacity') and tournament.capacity:
        capacity = tournament.capacity
        card['capacity'] = {
            'current': capacity.current_teams,
            'max': capacity.max_teams,
            'available': capacity.get_available_slots(),
            'fill_percentage': capacity.get_fill_percentage(),
            'is_full': capacity.is_full,
            'status': capacity.capacity_status,
            'can_register': capacity.can_accept_more_teams(),
        }
    else:
        card['capacity'] = {'current': 0, 'max': 0, 'can_register': False}
    
    # Finance data
    if hasattr(tournament, 'finance') and tournament.finance:
        finance = tournament.finance
        card['finance'] = {
            'entry_fee': finance.entry_fee,
            'entry_fee_formatted': finance.get_formatted_entry_fee(),
            'prize_pool': finance.prize_pool,
            'prize_pool_formatted': finance.get_formatted_prize_pool(),
            'is_free': finance.is_free_tournament(),
            'has_prizes': finance.has_prize_pool(),
        }
    else:
        card['finance'] = {'entry_fee': 0, 'is_free': True}
    
    # Media data
    if hasattr(tournament, 'media') and tournament.media:
        media = tournament.media
        card['media'] = {
            'logo_url': media.logo.url if media.logo else None,
            'banner_url': media.banner.url if media.banner else None,
            'thumbnail_url': media.thumbnail.url if media.thumbnail else None,
            'show_logo': media.show_logo_on_card,
            'show_banner': media.show_banner_on_card,
            'has_stream': bool(media.stream_url),
        }
    else:
        card['media'] = {'logo_url': None, 'banner_url': None}
    
    # Archive data
    if hasattr(tournament, 'archive') and tournament.archive:
        archive = tournament.archive
        card['archive'] = {
            'is_archived': archive.is_archived,
            'is_clone': archive.is_clone(),
            'archive_type': archive.archive_type,
        }
    else:
        card['archive'] = {'is_archived': False, 'is_clone': False}
    
    # Rules data (for requirements badge)
    if hasattr(tournament, 'rules') and tournament.rules:
        rules = tournament.rules
        requirements = []
        if rules.require_discord:
            requirements.append('Discord')
        if rules.require_game_id:
            requirements.append('Game ID')
        if rules.require_team_logo:
            requirements.append('Logo')
        card['requirements'] = requirements
        card['has_restrictions'] = (
            rules.has_age_restriction() or 
            rules.has_region_restriction() or 
            rules.has_rank_restriction()
        )
    else:
        card['requirements'] = []
        card['has_restrictions'] = False
    
    # Compute status badges
    badges = []
    
    if card['schedule']['registration_open']:
        badges.append({'text': 'Registration Open', 'color': 'success'})
    elif card['schedule']['registration_upcoming']:
        badges.append({'text': 'Opening Soon', 'color': 'info'})
    
    if card['capacity']['is_full']:
        badges.append({'text': 'Full', 'color': 'danger'})
    elif card['capacity']['fill_percentage'] >= 80:
        badges.append({'text': 'Filling Fast', 'color': 'warning'})
    
    if card['finance']['is_free']:
        badges.append({'text': 'Free Entry', 'color': 'success'})
    
    if card['finance']['has_prizes']:
        badges.append({'text': f"Prize: {card['finance']['prize_pool_formatted']}", 'color': 'primary'})
    
    if card['media']['has_stream']:
        badges.append({'text': 'Live Stream', 'color': 'danger'})
    
    if card['schedule']['is_in_progress']:
        badges.append({'text': 'Live Now', 'color': 'danger', 'pulse': True})
    
    card['badges'] = badges
    
    # Compute can_register flag
    card['can_register'] = (
        card['schedule']['registration_open'] and
        card['capacity']['can_register'] and
        not card['archive']['is_archived']
    )
    
    return card


def filter_tournaments(queryset, filters: Dict[str, Any]):
    """
    Apply filters to tournament queryset using Phase 1 models.
    
    Supported filters:
    - status: PUBLISHED, RUNNING, COMPLETED
    - game: game slug
    - registration_open: bool
    - has_prizes: bool
    - is_free: bool
    - capacity_available: bool
    """
    now = timezone.now()
    
    # Status filter
    if filters.get('status'):
        queryset = queryset.filter(status=filters['status'])
    
    # Game filter
    if filters.get('game'):
        queryset = queryset.filter(game__slug=filters['game'])
    
    # Registration open filter (using Phase 1 Schedule)
    if filters.get('registration_open'):
        queryset = queryset.filter(
            schedule__registration_start__lte=now,
            schedule__registration_end__gte=now
        )
    
    # Prize filter (using Phase 1 Finance)
    if filters.get('has_prizes'):
        queryset = queryset.filter(finance__prize_pool__gt=0)
    
    # Free entry filter (using Phase 1 Finance)
    if filters.get('is_free'):
        queryset = queryset.filter(finance__entry_fee=0)
    
    # Capacity available filter (using Phase 1 Capacity)
    if filters.get('capacity_available'):
        queryset = queryset.filter(capacity__is_full=False)
    
    # Search query
    if filters.get('q'):
        query = filters['q']
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(game__name__icontains=query)
        )
    
    return queryset


def get_tournament_stats():
    """
    Get overall tournament statistics using Phase 1 models.
    """
    now = timezone.now()
    
    # Total tournaments
    total = Tournament.objects.filter(
        archive__is_archived=False
    ).count()
    
    # Active (published or running)
    active = Tournament.objects.filter(
        archive__is_archived=False,
        status__in=['PUBLISHED', 'RUNNING']
    ).count()
    
    # Registration open (using Phase 1 Schedule)
    registration_open = Tournament.objects.filter(
        archive__is_archived=False,
        schedule__registration_start__lte=now,
        schedule__registration_end__gte=now
    ).count()
    
    # With prizes (using Phase 1 Finance)
    with_prizes = Tournament.objects.filter(
        archive__is_archived=False,
        finance__prize_pool__gt=0
    ).count()
    
    # Free entry (using Phase 1 Finance)
    free_entry = Tournament.objects.filter(
        archive__is_archived=False,
        finance__entry_fee=0
    ).count()
    
    # Available capacity (using Phase 1 Capacity)
    available_spots = Tournament.objects.filter(
        archive__is_archived=False,
        capacity__is_full=False,
        schedule__registration_start__lte=now,
        schedule__registration_end__gte=now
    ).count()
    
    return {
        'total': total,
        'active': active,
        'registration_open': registration_open,
        'with_prizes': with_prizes,
        'free_entry': free_entry,
        'available_spots': available_spots,
    }


def hub_phase2(request: HttpRequest) -> HttpResponse:
    """
    Phase 2 Enhanced Tournament Hub View
    
    Features:
    - Displays tournaments using all 6 Phase 1 models
    - Optimized queries (single DB hit per tournament with select_related)
    - Advanced filtering using Phase 1 model fields
    - Real-time statistics
    - Responsive pagination
    """
    
    # Get filters from query params
    filters = {
        'status': request.GET.get('status'),
        'game': request.GET.get('game'),
        'registration_open': request.GET.get('registration_open') == 'true',
        'has_prizes': request.GET.get('has_prizes') == 'true',
        'is_free': request.GET.get('is_free') == 'true',
        'capacity_available': request.GET.get('capacity_available') == 'true',
        'q': request.GET.get('q'),
    }
    
    # Get optimized queryset
    queryset = get_optimized_tournament_queryset()
    
    # Apply filters
    queryset = filter_tournaments(queryset, filters)
    
    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(queryset, 12)  # 12 tournaments per page
    page_obj = paginator.get_page(page_number)
    
    # Annotate tournaments for display
    tournament_cards = [annotate_tournament_card(t) for t in page_obj]
    
    # Get statistics
    stats = get_tournament_stats()
    
    # Get available games for filter
    Game = apps.get_model("tournaments", "Game")
    available_games = Game.objects.filter(
        tournament__archive__is_archived=False
    ).distinct()
    
    # Build context
    ctx = {
        'tournaments': tournament_cards,
        'page_obj': page_obj,
        'stats': stats,
        'filters': filters,
        'available_games': available_games,
        'total_count': queryset.count(),
    }
    
    return render(request, 'tournaments/hub_phase2.html', ctx)


def tournaments_by_status_phase2(request: HttpRequest, status: str) -> HttpResponse:
    """
    View tournaments filtered by status using Phase 1 models.
    
    Statuses: published, running, completed, upcoming
    """
    queryset = get_optimized_tournament_queryset()
    
    now = timezone.now()
    
    if status == 'published':
        queryset = queryset.filter(status='PUBLISHED')
        title = 'Published Tournaments'
    elif status == 'running':
        queryset = queryset.filter(status='RUNNING')
        title = 'Live Tournaments'
    elif status == 'completed':
        queryset = queryset.filter(status='COMPLETED')
        title = 'Completed Tournaments'
    elif status == 'upcoming':
        queryset = queryset.filter(
            schedule__tournament_start__gt=now
        ).order_by('schedule__tournament_start')
        title = 'Upcoming Tournaments'
    else:
        queryset = queryset.none()
        title = 'Tournaments'
    
    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(page_number)
    
    # Annotate tournaments
    tournament_cards = [annotate_tournament_card(t) for t in page_obj]
    
    ctx = {
        'tournaments': tournament_cards,
        'page_obj': page_obj,
        'title': title,
        'status_filter': status,
    }
    
    return render(request, 'tournaments/list_by_status.html', ctx)


def registration_open_phase2(request: HttpRequest) -> HttpResponse:
    """
    Show tournaments with open registration using Phase 1 Schedule model.
    """
    now = timezone.now()
    
    queryset = get_optimized_tournament_queryset().filter(
        schedule__registration_start__lte=now,
        schedule__registration_end__gte=now,
        capacity__is_full=False
    ).order_by('schedule__registration_end')
    
    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(page_number)
    
    # Annotate tournaments
    tournament_cards = [annotate_tournament_card(t) for t in page_obj]
    
    ctx = {
        'tournaments': tournament_cards,
        'page_obj': page_obj,
        'title': 'Open for Registration',
        'subtitle': 'Register now for these upcoming tournaments',
    }
    
    return render(request, 'tournaments/registration_open.html', ctx)

