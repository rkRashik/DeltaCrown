"""
Organization Detail Service
Provides context for organization detail page.
"""

from django.shortcuts import get_object_or_404
from apps.organizations.models.organization import Organization
from apps.organizations.permissions import get_permission_context


# In-memory cache for game lookups (populated once per request)
_game_cache = {}


def _get_game_data(game_id):
    """
    Look up Game model data by ID. Caches results to avoid N+1 queries.
    Returns dict with name, display_name, short_code, icon_url or None.
    """
    if game_id in _game_cache:
        return _game_cache[game_id]
    
    try:
        from apps.games.models.game import Game
        game = Game.objects.filter(id=game_id).values(
            'name', 'display_name', 'short_code', 'icon', 'slug'
        ).first()
        _game_cache[game_id] = game
        return game
    except Exception:
        _game_cache[game_id] = None
        return None


def _safe_game_label(team):
    """
    Get safe game label for team.
    vNext Team has game_id (int), not FK. Looks up actual Game name.
    """
    game_id = getattr(team, 'game_id', None)
    if game_id:
        game_data = _get_game_data(game_id)
        if game_data:
            return game_data.get('display_name') or game_data.get('name') or f"Game #{game_id}"
        return f"Game #{game_id}"
    return "—"


def _safe_game_short_code(team):
    """Get game short code (e.g. 'VAL', 'CS2') for team."""
    game_id = getattr(team, 'game_id', None)
    if game_id:
        game_data = _get_game_data(game_id)
        if game_data:
            return game_data.get('short_code', '')
    return ''


def _safe_game_icon(team):
    """Get game icon URL for team."""
    game_id = getattr(team, 'game_id', None)
    if game_id:
        game_data = _get_game_data(game_id)
        if game_data and game_data.get('icon'):
            return f"/media/{game_data['icon']}"
    return ''


def get_org_detail_context(org_slug, viewer):
    """
    Returns context for organization detail page.
    
    Args:
        org_slug: Organization slug
        viewer: Requesting user
    
    Returns:
        dict with:
            - organization: Organization instance
            - can_manage_org: Boolean permission
            - active_teams_count: Number of active teams
            - squads: List of active teams with IGL/Manager info and rankings
    """
    from django.conf import settings
    
    # Query organization with proper related data
    try:
        organization = Organization.objects.select_related(
            'ceo', 'profile'
        ).get(slug=org_slug)
    except Organization.DoesNotExist:
        from django.http import Http404
        raise Http404(f'Organization with slug "{org_slug}" does not exist.')
    
    # Permission: CEO OR org MANAGER/ADMIN OR staff
    # Use centralized permission module
    permissions = get_permission_context(viewer, organization)
    
    # Phase 10: Fetch org teams with rankings from CompetitionService
    from apps.organizations.models import Team
    
    # Note: Team has game_id (IntegerField), not a ForeignKey, so we can't select_related('game')
    active_teams = Team.objects.filter(
        organization=organization,
        status='ACTIVE'
    ).select_related('created_by').order_by('-created_at')[:20]
    
    active_teams_count = active_teams.count()
    
    # Build squad data with team ranks
    squads = []
    competition_enabled = getattr(settings, 'COMPETITION_APP_ENABLED', True)
    
    if competition_enabled:
        try:
            from apps.competition.services import CompetitionService
            
            for team in active_teams:
                # Get team rank
                rank_data = CompetitionService.get_team_rank(team.id)
                
                squads.append({
                    'team': team,
                    'team_name': team.name,
                    'team_slug': team.slug,
                    'game_label': _safe_game_label(team),
                    'game_short_code': _safe_game_short_code(team),
                    'game_icon': _safe_game_icon(team),
                    'rank': rank_data.get('rank') if rank_data else None,
                    'tier': rank_data.get('tier', 'UNRANKED') if rank_data else 'UNRANKED',
                    'score': rank_data.get('score', 0) if rank_data else 0,
                })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not fetch team ranks for org {org_slug}: {e}")
            # Fallback: squads without ranks
            for team in active_teams:
                squads.append({
                    'team': team,
                    'team_name': team.name,
                    'team_slug': team.slug,
                    'game_label': _safe_game_label(team),
                    'game_short_code': _safe_game_short_code(team),
                    'game_icon': _safe_game_icon(team),
                    'rank': None,
                    'tier': 'UNRANKED',
                    'score': 0,
                })
    else:
        # Competition disabled: squads without ranks
        for team in active_teams:
            squads.append({
                'team': team,
                'team_name': team.name,
                'team_slug': team.slug,
                'game_label': _safe_game_label(team),
                'game_short_code': _safe_game_short_code(team),
                'game_icon': _safe_game_icon(team),
                'rank': None,
                'tier': 'UNRANKED',
                'score': 0,
            })
    
    # Get org empire score if competition enabled
    org_empire_score = {
        'rank': None,
        'percentile': None,
        'bar_width': 0,
        'total_earnings': 'N/A',
        'trophies': 0,
        'trophies_this_season': 0,
        'major_titles': 0,
    }
    if competition_enabled:
        try:
            from apps.competition.services import CompetitionService
            raw = CompetitionService.get_org_empire_score(organization.id)
            if raw:
                org_empire_score.update({
                    'rank': raw.get('rank'),
                    'percentile': raw.get('percentile'),
                    'bar_width': raw.get('percentile') or 0,
                    'total_earnings': raw.get('total_earnings', 'N/A'),
                    'trophies': raw.get('trophies', 0),
                    'trophies_this_season': raw.get('trophies_this_season', 0),
                    'major_titles': raw.get('major_titles', 0),
                })
        except Exception:
            pass
    
    # Fetch org staff members
    from apps.organizations.models import OrganizationMembership
    org_memberships = OrganizationMembership.objects.filter(
        organization=organization
    ).select_related('user').order_by('role', 'joined_at')
    
    member_count = org_memberships.count()
    
    # Build template-friendly staff dicts
    org_members = []
    for m in org_memberships:
        avatar = ''
        if hasattr(m.user, 'profile'):
            try:
                avatar = m.user.profile.avatar.url if m.user.profile.avatar else ''
            except (ValueError, AttributeError):
                avatar = ''
        org_members.append({
            'id': m.id,
            'user_id': m.user_id,
            'username': m.user.username,
            'avatar': avatar,
            'role': m.role,
            'is_ceo': m.role == 'CEO',
            'joined_at': m.joined_at,
        })
    
    return {
        'organization': organization,
        'teams': list(active_teams),
        'teams_count': active_teams_count,
        'active_teams_count': active_teams_count,
        'squads': squads,
        'org_empire_score': org_empire_score,
        'org_members': org_members,
        'member_count': member_count,
        # Empty placeholders for future wiring
        'activity_logs': [],
        'staff_members': [],
        'streams': [],
        # Permissions from centralized module
        **permissions,
        # UI role for legacy template compatibility
        'ui_role': 'OWNER' if permissions['can_manage_org'] else 'PUBLIC',
        'ui_type': 'PRO',  # Safe default; can be enhanced later based on org tier
    }


def get_control_plane_context(org_slug, viewer):
    """
    Returns context for the organization control plane.
    Extends get_org_detail_context() with management-specific data.

    Args:
        org_slug: Organization slug
        viewer: Requesting user

    Returns:
        dict with all detail context fields plus:
            - org_slug: Slug string for JS API calls
            - org_take_pct: Revenue split org percentage
            - player_take_pct: Revenue split player percentage
            - staff_members: Actual OrganizationMembership queryset (replaces empty placeholder)
    """
    context = get_org_detail_context(org_slug=org_slug, viewer=viewer)
    organization = context['organization']

    # Slug for JS API calls (e.g. /api/vnext/orgs/{slug}/settings/)
    context['org_slug'] = organization.slug

    # Revenue split config (parsed from JSONField)
    split_config = organization.revenue_split_config or {}
    context['org_take_pct'] = split_config.get('org_take', 30)
    context['player_take_pct'] = 100 - context['org_take_pct']

    # Brand enforcement
    context['enforce_brand'] = organization.enforce_brand

    # Replace empty staff_members placeholder with actual org_members
    context['staff_members'] = context['org_members']

    return context
