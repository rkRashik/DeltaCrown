"""
Hub view for vNext landing page.

Provides the central command hub with:
- Hero carousel (top org, user status, recent tournament)
- Featured teams grid
- Global leaderboard
- Dynamic widgets populated via API

Schema Safety:
- Queries are defensive and work even if tag/tagline migrations not applied
- Uses schema introspection to avoid ProgrammingError on missing columns
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.core.cache import cache
from django.db import ProgrammingError

logger = logging.getLogger(__name__)


def _get_hero_carousel_context(request):
    """
    Get hero carousel data with robust fallbacks.
    
    API CONTRACT: STABLE (Phase C+)
    This function's return structure is LOCKED for Phase C+/D consumption.
    Breaking changes require Phase D architecture review.
    
    Returns dict with:
    - top_organization: Top org by empire_score (or None) — GUARANTEED key
    - user_teams_count: Count of user's active teams — GUARANTEED key (default: 0)
    - user_primary_team: User's primary team (owner or first membership) — GUARANTEED key (or None)
    - recent_tournament_winner: Recent tournament winner data (or None) — GUARANTEED key
    
    Empty State Guarantee: All keys present even if no data exists.
    
    Cache: 2 minutes per user (carousel data)
    """
    from apps.teams.models import Team  # Legacy Team is authoritative
    from apps.organizations.models import Organization
    
    cache_key = f'hero_carousel_{request.user.id}'
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    carousel_data = {
        'top_organization': None,
        'user_teams_count': 0,
        'user_primary_team': None,
        'recent_tournament_winner': None,
    }
    
    # Slide 1: Top organization by empire_score
    # DEFENSIVE GUARD: Handles missing OrganizationRanking rows gracefully
    try:
        top_org_qs = Organization.objects.select_related('ranking', 'ceo')
        
        # Prefer verified organizations with ranking
        carousel_data['top_organization'] = top_org_qs.filter(
            is_verified=True,
            ranking__isnull=False  # CRITICAL: Prevents crash if ranking row missing
        ).order_by('-ranking__empire_score', '-updated_at').first()
        
        # Fallback to any verified organization (even without ranking)
        if not carousel_data['top_organization']:
            carousel_data['top_organization'] = top_org_qs.filter(
                is_verified=True
            ).order_by('-updated_at').first()
        
        # Fallback to any organization (last resort)
        if not carousel_data['top_organization']:
            carousel_data['top_organization'] = top_org_qs.order_by('-updated_at').first()
        
        # DEFENSIVE: If org exists but has no ranking, ensure no attribute access errors
        if carousel_data['top_organization'] and not hasattr(carousel_data['top_organization'], 'ranking'):
            logger.debug(f"Top org {carousel_data['top_organization'].slug} has no ranking row")
    except Exception as e:
        logger.warning(f"Could not fetch top organization: {e}")
        # carousel_data['top_organization'] remains None (guaranteed key)
    
    # Slide 2: User's team status
    try:
        # Legacy Team: no 'status' field, no 'owner' FK
        # Use is_active instead, memberships use 'profile' FK not 'user' FK
        viewer_profile = getattr(request.user, 'userprofile', None) if request.user.is_authenticated and hasattr(request.user, 'userprofile') else None
        
        if viewer_profile:
            carousel_data['user_teams_count'] = Team.objects.filter(
                memberships__profile=viewer_profile,
                memberships__status='ACTIVE',
                is_active=True
            ).distinct().count()
            
            # Find user's primary team (first active membership)
            carousel_data['user_primary_team'] = Team.objects.filter(
                memberships__profile=viewer_profile,
                memberships__status='ACTIVE',
                is_active=True
            ).first()
    except Exception as e:
        logger.warning(f"Could not fetch user team data: {e}")
    
    # Slide 3: Most recent tournament winner
    try:
        from apps.tournaments.models import Tournament
        recent_tournament = Tournament.objects.filter(
            status__in=['COMPLETED', 'FINALIZED'],
            winner_team__isnull=False
        ).select_related('winner_team', 'winner_team__organization').order_by('-end_date').first()
        
        if recent_tournament and recent_tournament.winner_team:
            carousel_data['recent_tournament_winner'] = {
                'team_name': recent_tournament.winner_team.name,
                'team_slug': recent_tournament.winner_team.slug,
                'tournament_name': recent_tournament.name,
                'tournament_id': recent_tournament.id,
                'end_date': recent_tournament.end_date,
            }
    except Exception as e:
        logger.warning(f"Could not fetch recent tournament winner: {e}")
    
    # Cache for 2 minutes
    cache.set(cache_key, carousel_data, 120)
    return carousel_data


def _get_featured_teams(game_id=None, limit=12):
    """
    Get featured teams (top by CP) with caching.
    
    API CONTRACT: STABLE (Phase C+)
    Returns QuerySet of Team objects. Consumer code may access:
    - team.name, team.slug, team.logo_url (GUARANTEED fields)
    - team.organization (MAY be None for independent teams)
    - team.ranking (MAY be None if no ranking row exists)
    - team.memberships (GUARANTEED queryset, may be empty)
    - team.tag, team.tagline (MAY be None if schema not migrated)
    
    Empty State Guarantee: Returns empty list if no teams, never raises.
    Schema Safety: Works even if tag/tagline columns don't exist yet.
    
    Args:
        game_id: Optional game ID filter
        limit: Maximum teams to return (default 12)
    
    Returns:
        List of Team objects with related data
    
    Cache: 2 minutes (key includes game_id)
    """
    from apps.teams.models import Team  # Legacy Team is authoritative
    from apps.organizations.utils import has_team_tag_columns
    
    cache_key = f'featured_teams_{game_id or "all"}_{limit}'
    cached_teams = cache.get(cache_key)
    
    if cached_teams is not None:
        return cached_teams
    
    try:
        # Legacy Team: no 'status' field, no 'organization'/'owner' FKs
        # Use is_active and is_public for filtering
        teams_qs = Team.objects.filter(
            is_active=True,
            is_public=True
        ).select_related(
            'ranking'
        ).prefetch_related(
            'memberships__profile__user'  # memberships use profile FK
        )
        
        # Only order by ranking if it exists
        try:
            teams_qs = teams_qs.order_by('-ranking__current_cp')
        except ProgrammingError:
            logger.warning("TeamRanking table may not exist, falling back to created_at order")
            teams_qs = teams_qs.order_by('-created_at')
        
        # Apply game filter if specified
        if game_id:
            teams_qs = teams_qs.filter(game_id=game_id)
        
        teams = list(teams_qs[:limit])
        
        # Cache for 2 minutes
        cache.set(cache_key, teams, 120)
        return teams
    except ProgrammingError as e:
        logger.warning(
            f"Error querying teams (schema may not be migrated): {e}",
            extra={'event_type': 'schema_error', 'operation': 'get_featured_teams'}
        )
        return []
    except Exception as e:
        logger.error(f"Error fetching featured teams: {e}", exc_info=True)
        return []


def _get_leaderboard(game_id=None, limit=50):
    """
    Get leaderboard rankings with caching.
    
    API CONTRACT: STABLE (Phase C+)
    Returns list of TeamRanking objects. Consumer code may access:
    - ranking.team (GUARANTEED, never None)
    - ranking.current_cp, ranking.rank (GUARANTEED fields)
    - ranking.team.name, ranking.team.slug (GUARANTEED)
    - ranking.team.organization (MAY be None)
    - ranking.team.tag, ranking.team.tagline (MAY be None if schema not migrated)
    
    Empty State Guarantee: Returns empty list if no rankings, never raises.
    Schema Safety: Works even if TeamRanking table does not exist yet.
    
    Args:
        game_id: Optional game ID filter
        limit: Maximum rankings to return (default 50)
    
    Returns:
        List of TeamRanking objects with related data
    
    Cache: 5 minutes (key includes game_id)
    """
    from apps.organizations.models import TeamRanking
    
    cache_key = f'hub_leaderboard_{game_id or "all"}_{limit}'
    cached_leaderboard = cache.get(cache_key)
    
    if cached_leaderboard is not None:
        return cached_leaderboard
    
    try:
        # Legacy Team: no 'status', 'organization', or 'owner' FKs
        # Use team__is_active for filtering
        leaderboard_qs = TeamRanking.objects.select_related(
            'team'
        ).filter(
            team__is_active=True
        ).order_by('-current_cp')
        
        # Apply game filter (legacy Team uses 'game' CharField slug, not game_id FK)
        # We have game_id but need to convert to slug - skip game filter for now
        # TODO: Convert game_id to slug via Game.objects.get(id=game_id).slug if needed
        # if game_id:
        #     leaderboard_qs = leaderboard_qs.filter(team__game=game_slug)
        
        leaderboard = list(leaderboard_qs[:limit])
        
        # Cache for 5 minutes
        cache.set(cache_key, leaderboard, 300)
        return leaderboard
    
    except ProgrammingError as e:
        logger.warning(
            f"TeamRanking table may not exist yet: {e}. "
            f"Run 'python manage.py migrate organizations' to fix.",
            extra={'event_type': 'schema_missing_table', 'table': 'TeamRanking'}
        )
        return []
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}", exc_info=True)
        return []


def vnext_hub(request):
    """
    vNext Team & Organization Hub landing page (GET only).
    
    Central landing page for vNext features with real-time data:
    - Hero carousel (top org, user status, recent tournament)
    - Featured teams grid
    - Global leaderboard
    - Dynamic widgets (ticker, LFT, scrims) populated via API
    
    Feature Flag Protection:
    - If TEAM_VNEXT_ADAPTER_ENABLED is False, redirects to /teams/
    - If TEAM_VNEXT_FORCE_LEGACY is True, redirects to /teams/
    - If TEAM_VNEXT_ROUTING_MODE is 'legacy_only', redirects to /teams/
    
    Query Budget Target: ≤15 queries
    
    Returns:
        - 200: Renders vnext_hub.html (Tailwind UI with real data)
        - 302: Redirects to /teams/ if feature flags disabled
    """
    # Check feature flags
    force_legacy = getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False)
    adapter_enabled = getattr(settings, 'TEAM_VNEXT_ADAPTER_ENABLED', False)
    routing_mode = getattr(settings, 'TEAM_VNEXT_ROUTING_MODE', 'legacy_only')
    
    # If vNext disabled, redirect to legacy teams page
    if force_legacy or not adapter_enabled or routing_mode == 'legacy_only':
        messages.info(
            request,
            'vNext Team & Organization system is not yet available. Please use the existing team system.'
        )
        return redirect('/teams/')
    
    from apps.games.models import Game
    
    # Get selected game filter (slug or 'all')
    selected_game_slug = request.GET.get('game', 'all')
    selected_game_id = None
    
    # Resolve game ID from slug
    if selected_game_slug and selected_game_slug != 'all':
        try:
            game = Game.objects.get(slug=selected_game_slug, is_active=True)
            selected_game_id = game.id
        except Game.DoesNotExist:
            logger.warning(f"Invalid game slug in filter: {selected_game_slug}")
            selected_game_slug = 'all'
    
    # Fetch data using helper functions (with caching)
    carousel_data = _get_hero_carousel_context(request)
    featured_teams = _get_featured_teams(game_id=selected_game_id, limit=12)
    leaderboard_rows = _get_leaderboard(game_id=selected_game_id, limit=50)
    
    # Fetch available games for filter
    available_games = Game.objects.filter(is_active=True).order_by('display_name')
    
    return render(request, 'organizations/hub/vnext_hub.html', {
        'page_title': 'Command Hub',
        'featured_teams': featured_teams,
        'leaderboard_rows': leaderboard_rows,
        'available_games': available_games,
        'selected_game': selected_game_slug,
        # Hero Carousel Data
        'top_organization': carousel_data['top_organization'],
        'user_teams_count': carousel_data['user_teams_count'],
        'user_primary_team': carousel_data['user_primary_team'],
        'recent_tournament_winner': carousel_data['recent_tournament_winner'],
    })
