# apps/tournaments/views/hub_enhanced.py
"""
Enhanced Hub View with Optimized Database Queries and Real-time Stats
"""
from __future__ import annotations
from typing import Any, Dict, List

from django.apps import apps
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta

# Schedule helpers
from apps.tournaments.utils.schedule_helpers import optimize_queryset_for_schedule

# Capacity helpers
from apps.tournaments.utils.capacity_helpers import optimize_queryset_for_capacity

# Finance helpers
from apps.tournaments.utils.finance_helpers import optimize_queryset_for_finance

# Models
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")

def calculate_platform_stats() -> Dict[str, Any]:
    """
    Calculate real-time platform statistics for hero section.
    Cached for 5 minutes to reduce database load.
    """
    cache_key = 'platform:stats:v1'
    stats = cache.get(cache_key)
    
    if stats is not None:
        return stats
    
    now = timezone.now()
    month_ago = now - timedelta(days=30)
    week_start = now - timedelta(days=7)
    
    # Active tournaments (published or running, starting in future)
    total_active = Tournament.objects.filter(
        status__in=['PUBLISHED', 'RUNNING'],
        start_at__gte=now
    ).count()
    
    # Unique players this month (confirmed registrations)
    players_this_month = Registration.objects.filter(
        created_at__gte=month_ago,
        status='CONFIRMED'
    ).values('user').distinct().count()
    
    # Total prize pool this month (tournaments that started this month)
    prize_pool_month = Tournament.objects.filter(
        start_at__gte=month_ago,
        start_at__lte=now,
        prize_pool_bdt__isnull=False
    ).aggregate(
        total=Sum('prize_pool_bdt')
    )['total'] or 0
    
    # Tournaments completed
    tournaments_completed = Tournament.objects.filter(
        status='COMPLETED'
    ).count()
    
    # New tournaments this week
    new_this_week = Tournament.objects.filter(
        created_at__gte=week_start,
        status__in=['PUBLISHED', 'RUNNING']
    ).count()
    
    stats = {
        'total_active': total_active,
        'players_this_month': players_this_month,
        'prize_pool_month': int(prize_pool_month) if prize_pool_month else 0,
        'tournaments_completed': tournaments_completed,
        'new_this_week': new_this_week,
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, stats, 300)
    
    return stats


def get_game_stats(base_qs: QuerySet) -> List[Dict[str, Any]]:
    """
    Get tournament count per game for the game grid.
    """
    from .helpers import GAME_REGISTRY
    
    # Count tournaments per game
    game_counts = base_qs.values('game').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Convert to dict for easy lookup
    counts_dict = {item['game']: item['count'] for item in game_counts}
    
    # Build game cards with counts
    games = []
    for game_slug, game_info in GAME_REGISTRY.items():
        count = counts_dict.get(game_slug, 0)
        if count > 0:  # Only show games with tournaments
            games.append({
                'slug': game_slug,
                'name': game_info.get('name', game_slug.title()),
                'count': count,
                'icon': game_info.get('icon'),
                'card_image': game_info.get('card_image'),
                'primary_color': game_info.get('primary'),
            })
    
    return games


def apply_filters(request: HttpRequest, qs: QuerySet) -> QuerySet:
    """
    Apply URL query parameters to filter tournaments.
    Supports: q (search), game, status, fee, prize, sort
    """
    now = timezone.now()
    
    # Search query
    if q := request.GET.get('q', '').strip():
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(game__icontains=q) |
            Q(short_description__icontains=q)
        )
    
    # Game filter
    if game := request.GET.get('game'):
        qs = qs.filter(game=game)
    
    # Status filter
    if status := request.GET.get('status'):
        if status == 'open':
            # Registration open
            qs = qs.filter(
                status='PUBLISHED',
                reg_open_at__lte=now,
                reg_close_at__gte=now
            )
        elif status == 'live':
            qs = qs.filter(status='RUNNING')
        elif status == 'upcoming':
            qs = qs.filter(
                status='PUBLISHED',
                start_at__gt=now
            )
        elif status == 'completed':
            qs = qs.filter(status='COMPLETED')
    
    # Entry fee filter
    if fee := request.GET.get('fee'):
        if fee == 'free':
            qs = qs.filter(Q(entry_fee_bdt__isnull=True) | Q(entry_fee_bdt=0))
        elif fee == 'paid':
            qs = qs.filter(entry_fee_bdt__gt=0)
    
    # Prize pool filter
    if prize := request.GET.get('prize'):
        if prize == 'high':
            qs = qs.filter(prize_pool_bdt__gte=50000)  # 50k+ BDT
        elif prize == 'medium':
            qs = qs.filter(prize_pool_bdt__gte=10000, prize_pool_bdt__lt=50000)
        elif prize == 'low':
            qs = qs.filter(prize_pool_bdt__gt=0, prize_pool_bdt__lt=10000)
    
    # Sorting
    if sort := request.GET.get('sort'):
        if sort == 'newest':
            qs = qs.order_by('-created_at')
        elif sort == 'starting_soon':
            qs = qs.filter(start_at__gte=now).order_by('start_at')
        elif sort == 'prize_high':
            qs = qs.filter(prize_pool_bdt__isnull=False).order_by('-prize_pool_bdt')
        elif sort == 'prize_low':
            qs = qs.filter(prize_pool_bdt__isnull=False).order_by('prize_pool_bdt')
        elif sort == 'popular':
            # Sort by registration count
            qs = qs.annotate(
                reg_count=Count('registrations')
            ).order_by('-reg_count')
    
    return qs


def get_featured_tournaments(base_qs: QuerySet, limit: int = 6) -> List[Any]:
    """
    Get featured tournaments (highest prize pools or manually featured).
    """
    # Check if Tournament has a 'featured' field
    if hasattr(Tournament, 'featured'):
        featured = list(base_qs.filter(
            featured=True,
            status__in=['PUBLISHED', 'RUNNING']
        )[:limit])
        if featured:
            return featured
    
    # Fallback: highest prize pools
    return list(base_qs.filter(
        prize_pool_bdt__isnull=False,
        prize_pool_bdt__gt=0,
        status__in=['PUBLISHED', 'RUNNING']
    ).order_by('-prize_pool_bdt')[:limit])


def get_live_tournaments(base_qs: QuerySet, limit: int = 6) -> List[Any]:
    """
    Get currently running/live tournaments.
    """
    now = timezone.now()
    
    # Method 1: Check status
    live_by_status = list(base_qs.filter(
        status='RUNNING'
    )[:limit])
    
    # Method 2: Check timing (started but not ended)
    if len(live_by_status) < limit:
        live_by_time = list(base_qs.filter(
            start_at__lte=now,
            end_at__gte=now,
            status='PUBLISHED'
        ).exclude(
            id__in=[t.id for t in live_by_status]
        )[:limit - len(live_by_status)])
        
        live_by_status.extend(live_by_time)
    
    return live_by_status


def get_starting_soon(base_qs: QuerySet, days: int = 7, limit: int = 6) -> List[Any]:
    """
    Get tournaments starting within the next N days.
    """
    now = timezone.now()
    soon = now + timedelta(days=days)
    
    return list(base_qs.filter(
        start_at__gte=now,
        start_at__lte=soon,
        status='PUBLISHED'
    ).order_by('start_at')[:limit])


def get_new_tournaments(base_qs: QuerySet, days: int = 7, limit: int = 6) -> List[Any]:
    """
    Get tournaments created in the last N days.
    """
    cutoff = timezone.now() - timedelta(days=days)
    
    return list(base_qs.filter(
        created_at__gte=cutoff,
        status__in=['PUBLISHED', 'RUNNING']
    ).order_by('-created_at')[:limit])


def get_user_registrations(user) -> Dict[int, str]:
    """
    Get user's registration states for tournaments.
    Returns dict mapping tournament_id -> registration status.
    """
    if not user or not user.is_authenticated:
        return {}
    
    # Get the UserProfile instance from the User
    try:
        user_profile = user.profile
    except AttributeError:
        # If user doesn't have a profile, return empty dict
        return {}
    
    registrations = Registration.objects.filter(
        user=user_profile
    ).select_related('tournament').values('tournament_id', 'status')
    
    return {
        reg['tournament_id']: reg['status'].lower()
        for reg in registrations
    }


def paginate_tournaments(request: HttpRequest, qs: QuerySet, per_page: int = 12) -> Dict[str, Any]:
    """
    Paginate tournament queryset.
    Returns paginated results with metadata.
    """
    page_number = request.GET.get('page', 1)
    
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page_number)
    
    return {
        'tournaments': list(page_obj.object_list),
        'page': page_obj.number,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_count': paginator.count,
    }


def hub_enhanced(request: HttpRequest) -> HttpResponse:
    """
    Enhanced tournament hub view with optimized queries and real-time data.
    
    Features:
    - Optimized database queries (select_related, prefetch_related)
    - Real-time platform statistics
    - Smart filtering and search
    - Pagination
    - Caching for performance
    - Featured tournament sections
    """
    
    # Build optimized base queryset (Phase 0 + Phase 1)
    base_qs = Tournament.objects.select_related(
        'settings',
        'schedule',  # Phase 0: Schedule optimization
        'capacity',  # Phase 1: Capacity optimization
        'finance'    # Phase 1: Finance optimization
    ).prefetch_related(
        'registrations'
    ).filter(
        status__in=['PUBLISHED', 'RUNNING', 'COMPLETED']
    )
    
    # Apply filters from URL params
    filtered_qs = apply_filters(request, base_qs)
    
    # Get published tournaments for stats and featured sections
    published_qs = base_qs.filter(status__in=['PUBLISHED', 'RUNNING'])
    
    # Annotate tournaments with computed fields
    from .public import annotate_cards
    
    # Paginate main tournament list
    pagination_data = paginate_tournaments(request, filtered_qs, per_page=12)
    tournaments = annotate_cards(pagination_data['tournaments'])
    
    # Get user registration states
    my_reg_states = get_user_registrations(request.user)
    
    # Build context
    context = {
        # Main tournament list
        'tournaments': tournaments,
        'pagination': {
            'page': pagination_data['page'],
            'total_pages': pagination_data['total_pages'],
            'has_next': pagination_data['has_next'],
            'has_previous': pagination_data['has_previous'],
            'total_count': pagination_data['total_count'],
        },
        
        # Statistics
        'stats': calculate_platform_stats(),
        
        # Game grid
        'games': get_game_stats(published_qs),
        
        # Featured sections
        'live_tournaments': annotate_cards(get_live_tournaments(published_qs)),
        'starting_soon': annotate_cards(get_starting_soon(published_qs)),
        'new_this_week': annotate_cards(get_new_tournaments(published_qs)),
        'featured': annotate_cards(get_featured_tournaments(published_qs)),
        
        # User data
        'my_reg_states': my_reg_states,
        
        # Filter state (to maintain selected filters)
        'filters': {
            'q': request.GET.get('q', ''),
            'game': request.GET.get('game', ''),
            'status': request.GET.get('status', ''),
            'fee': request.GET.get('fee', ''),
            'prize': request.GET.get('prize', ''),
            'sort': request.GET.get('sort', ''),
        },
    }
    
    return render(request, 'tournaments/hub.html', context)
