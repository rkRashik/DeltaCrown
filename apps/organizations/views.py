"""
UI Views for vNext Organization and Team management.

These views provide the user interface for creating and managing
organizations and teams in the vNext system.

Feature Flag Protection:
- All vNext UI views check feature flags before rendering
- If flags disabled, redirect to home with message

Security:
- All views require authentication
- Permission checks for organization/team access
"""

import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q

from apps.organizations.adapters.flags import should_use_vnext_routing

logger = logging.getLogger(__name__)


# ============================================================================
# PRIVATE HELPER FUNCTIONS FOR HUB VIEW
# ============================================================================

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
    from .models import Team, Organization
    
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
        carousel_data['user_teams_count'] = Team.objects.filter(
            memberships__user=request.user,
            memberships__status='ACTIVE',
            status='ACTIVE'
        ).distinct().count()
        
        # Find user's primary team (owner or first active membership)
        carousel_data['user_primary_team'] = Team.objects.filter(
            owner=request.user,
            status='ACTIVE'
        ).first()
        
        if not carousel_data['user_primary_team']:
            carousel_data['user_primary_team'] = Team.objects.filter(
                memberships__user=request.user,
                memberships__status='ACTIVE',
                status='ACTIVE'
            ).select_related('game').first()
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
    
    Empty State Guarantee: Returns empty list if no teams, never raises.
    
    Args:
        game_id: Optional game ID filter
        limit: Maximum teams to return (default 12)
    
    Returns:
        QuerySet of Team objects with related data
    
    Cache: 2 minutes (key includes game_id)
    """
    from .models import Team
    
    cache_key = f'featured_teams_{game_id or "all"}_{limit}'
    cached_teams = cache.get(cache_key)
    
    if cached_teams is not None:
        return cached_teams
    
    teams_qs = Team.objects.filter(
        status='ACTIVE'
    ).select_related(
        'organization',
        'owner',
        'ranking'
    ).prefetch_related(
        'memberships__user'
    ).order_by('-ranking__current_cp')
    
    # Apply game filter if specified
    if game_id:
        teams_qs = teams_qs.filter(game_id=game_id)
    
    teams = list(teams_qs[:limit])
    
    # Cache for 2 minutes
    cache.set(cache_key, teams, 120)
    return teams


def _get_leaderboard(game_id=None, limit=50):
    """
    Get leaderboard rankings with caching.
    
    API CONTRACT: STABLE (Phase C+)
    Returns list of TeamRanking objects. Consumer code may access:
    - ranking.team (GUARANTEED, never None)
    - ranking.current_cp, ranking.rank (GUARANTEED fields)
    - ranking.team.name, ranking.team.slug (GUARANTEED)
    - ranking.team.organization (MAY be None)
    
    Empty State Guarantee: Returns empty list if no rankings, never raises.
    
    Args:
        game_id: Optional game ID filter
        limit: Maximum rankings to return (default 50)
    
    Returns:
        List of TeamRanking objects with related data
    
    Cache: 5 minutes (key includes game_id)
    """
    from .models import TeamRanking
    
    cache_key = f'hub_leaderboard_{game_id or "all"}_{limit}'
    cached_leaderboard = cache.get(cache_key)
    
    if cached_leaderboard is not None:
        return cached_leaderboard
    
    leaderboard_qs = TeamRanking.objects.select_related(
        'team__organization',
        'team__owner'
    ).filter(
        team__status='ACTIVE'
    ).order_by('-current_cp')
    
    # Apply game filter
    if game_id:
        leaderboard_qs = leaderboard_qs.filter(team__game_id=game_id)
    
    leaderboard = list(leaderboard_qs[:limit])
    
    # Cache for 5 minutes
    cache.set(cache_key, leaderboard, 300)
    return leaderboard




# ============================================================================
# PUBLIC VIEWS
# ============================================================================

@login_required
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
    
    return render(request, 'teams/vnext_hub.html', {
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


@login_required
def team_create(request):
    """
    Team/Organization creation UI (GET only).
    
    Displays the 2-step Tailwind UI for creating organizations or teams.
    Actual creation handled by REST API endpoints.
    
    Feature Flag Protection:
    - If TEAM_VNEXT_ADAPTER_ENABLED is False, redirects to home
    - If TEAM_VNEXT_FORCE_LEGACY is True, redirects to home
    - If TEAM_VNEXT_ROUTING_MODE is 'legacy_only', redirects to home
    
    Returns:
        - 200: Renders team_create.html (Tailwind UI)
        - 302: Redirects to home if feature flags disabled
    """
    # Check feature flags (same logic as API endpoints)
    force_legacy = getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False)
    adapter_enabled = getattr(settings, 'TEAM_VNEXT_ADAPTER_ENABLED', False)
    routing_mode = getattr(settings, 'TEAM_VNEXT_ROUTING_MODE', 'adapter_first')
    
    # Priority: FORCE_LEGACY (highest) > ADAPTER_ENABLED > ROUTING_MODE
    if force_legacy:
        messages.warning(
            request,
            'Team creation is temporarily unavailable. Please try again later.'
        )
        logger.info(
            f"vNext UI access denied for user {request.user.id}: FORCE_LEGACY enabled",
            extra={
                'event_type': 'vnext_ui_blocked',
                'user_id': request.user.id,
                'reason': 'force_legacy',
            }
        )
        return redirect('/')
    
    if not adapter_enabled:
        messages.info(
            request,
            'This feature is not yet available. Check back soon!'
        )
        logger.info(
            f"vNext UI access denied for user {request.user.id}: Adapter disabled",
            extra={
                'event_type': 'vnext_ui_blocked',
                'user_id': request.user.id,
                'reason': 'adapter_disabled',
            }
        )
        return redirect('/')
    
    if routing_mode == 'legacy_only':
        messages.info(
            request,
            'This feature is not yet available. Check back soon!'
        )
        logger.info(
            f"vNext UI access denied for user {request.user.id}: Legacy-only mode",
            extra={
                'event_type': 'vnext_ui_blocked',
                'user_id': request.user.id,
                'reason': 'legacy_only_mode',
            }
        )
        return redirect('/')
    
    # Feature flags allow access
    logger.info(
        f"vNext UI accessed by user {request.user.id}",
        extra={
            'event_type': 'vnext_ui_accessed',
            'user_id': request.user.id,
        }
    )
    
    return render(request, 'organizations/team_create.html', {
        'page_title': 'Create Team or Organization',
    })


@login_required
def organization_detail(request, org_slug):
    """
    Organization detail and management UI (P3-T5).
    
    Displays organization information with tabs for:
    - Members: View/add/remove/change roles
    - Teams: View organization teams
    - Settings: Update branding (CEO/Manager only)
    
    Args:
        org_slug: Organization URL slug
    
    Returns:
        - 200: Renders organization_detail.html (Tailwind UI)
        - 404: Organization not found
        - 302: Redirects if not a member
    """
    import json
    from apps.organizations.services.organization_service import OrganizationService
    from apps.organizations.services.exceptions import NotFoundError
    from apps.organizations.models import OrganizationMembership
    
    try:
        # Get organization data
        org_data = OrganizationService.get_organization_detail(
            org_slug=org_slug,
            include_members=True,
            include_teams=True
        )
        
        # Check if user is a member
        membership = OrganizationMembership.objects.filter(
            organization__slug=org_slug,
            user=request.user
        ).first()
        
        # Determine if user can manage
        can_manage = False
        if membership and membership.role in ['CEO', 'MANAGER']:
            can_manage = True
        
        logger.info(
            f"Organization detail accessed: {org_slug}",
            extra={
                'event_type': 'org_detail_accessed',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'can_manage': can_manage,
            }
        )
        
        return render(request, 'organizations/organization_detail.html', {
            'org': org_data['org'],
            'org_data': json.dumps(org_data),
            'can_manage': can_manage,
        })
    
    except NotFoundError:
        messages.error(request, f'Organization "{org_slug}" not found.')
        return redirect('/teams/')


@login_required
def team_detail(request, team_slug):
    """
    Team detail and roster management UI (P3-T6).
    
    Displays team information with tabs for:
    - Roster: View/add/remove/change roles for team members
    - Invites: View pending invitations (placeholder)
    - Settings: Update team branding and preferences (if authorized)
    
    Permission Logic:
    - Independent team: OWNER or MANAGER can manage
    - Org-owned team: Org CEO/MANAGER or team OWNER/MANAGER can manage
    
    Args:
        team_slug: Team URL slug
    
    Returns:
        - 200: Renders team_detail.html (Tailwind UI)
        - 404: Team not found
        - 302: Redirects if error
    """
    import json
    from apps.organizations.services.team_service import TeamService
    from apps.organizations.services.exceptions import NotFoundError
    from apps.organizations.models import Team, TeamMembership, OrganizationMembership
    from apps.organizations.choices import MembershipRole, MembershipStatus
    
    try:
        # Get team data
        team_data = TeamService.get_team_detail(
            team_slug=team_slug,
            include_members=True,
            include_invites=True
        )
        
        # Determine if user can manage team
        can_manage = False
        
        # Get team object for permission check
        team = Team.objects.select_related('organization').get(slug=team_slug)
        
        if team.organization:
            # Org-owned team: Check if user is org CEO or MANAGER
            org_membership = OrganizationMembership.objects.filter(
                organization=team.organization,
                user=request.user,
                role__in=['CEO', 'MANAGER']
            ).first()
            
            if org_membership:
                can_manage = True
            else:
                # Also check if user is team OWNER or MANAGER
                team_membership = TeamMembership.objects.filter(
                    team=team,
                    user=request.user,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).first()
                
                if team_membership:
                    can_manage = True
        else:
            # Independent team: Check if user is OWNER or MANAGER
            team_membership = TeamMembership.objects.filter(
                team=team,
                user=request.user,
                status=MembershipStatus.ACTIVE,
                role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
            ).first()
            
            if team_membership:
                can_manage = True
        
        logger.info(
            f"Team detail accessed: {team_slug}",
            extra={
                'event_type': 'team_detail_accessed',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'can_manage': can_manage,
            }
        )
        
        return render(request, 'organizations/team_detail.html', {
            'team': team_data['team'],
            'team_data': json.dumps(team_data),
            'can_manage': can_manage,
        })
    
    except NotFoundError:
        messages.error(request, f'Team "{team_slug}" not found.')
        return redirect('/teams/')

