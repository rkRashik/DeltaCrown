"""
Organization Detail Service
Provides context for organization detail page.
"""

from django.shortcuts import get_object_or_404
from apps.organizations.models.organization import Organization


def _safe_game_label(team):
    """
    Get safe game label for team.
    vNext Team has game_id (int), not FK. Do not assume FK exists.
    """
    if getattr(team, 'game_id', None):
        return f"Game #{team.game_id}"
    return "—"


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
            - squads: List of active teams with IGL/Manager info
    """
    # Query organization with proper related data
    # Note: Organization has NO is_active field - do not filter on it
    try:
        organization = Organization.objects.select_related(
            'ceo'
        ).prefetch_related(
            'teams',
            'teams__members',
            'teams__members__player'
        ).get(slug=org_slug)
    except Organization.DoesNotExist:
        from django.http import Http404
        raise Http404(f'Organization with slug "{org_slug}" does not exist.')
    
    # Permission: CEO OR org MANAGER/ADMIN OR staff
    can_manage_org = False
    if viewer.is_authenticated:
        if viewer.is_staff:
            can_manage_org = True
        elif organization.ceo_id == viewer.id:
            can_manage_org = True
        else:
            # Check org membership
            membership = organization.memberships.filter(
                player=viewer,
                role__in=['MANAGER', 'ADMIN']
            ).first()
            can_manage_org = membership is not None
    
    # Get active teams (Team has 'status' field, not 'is_active')
    # Safe fallback: never crash on status value assumptions
    teams_qs = organization.teams.all()
    try:
        # Team.status choices: ACTIVE, DELETED, SUSPENDED, DISBANDED
        teams_qs = teams_qs.filter(status__in=['ACTIVE', 'active'])
    except Exception:
        # Never crash - fallback to all teams if status filter fails
        teams_qs = organization.teams.all()
    
    active_teams = list(teams_qs.order_by('-updated_at')[:24])
    active_teams_count = len(active_teams)
    
    # Build squad data with IGL/Manager info (privacy-aware)
    squads = []
    for team in active_teams:
        # Get IGL (always visible)
        igl_member = team.members.filter(role='IGL').first()
        igl_display = igl_member.player.username if igl_member else None
        
        # Get Manager (only if viewer can manage org)
        manager_display = None
        if can_manage_org:
            manager_member = team.members.filter(role='MANAGER').first()
            manager_display = manager_member.player.username if manager_member else None
        
        # Get game label safely (Team has game_id integer, not FK)
        game_label = _safe_game_label(team)
        
        squads.append({
            'team': team,
            'name': team.name,
            'slug': team.slug,
            'game': game_label,
            'igl': igl_display,
            'manager': manager_display,  # None for public viewers
        })
    
    return {
        'organization': organization,
        'can_manage_org': can_manage_org,
        'active_teams_count': active_teams_count,
        'squads': squads,
        # Empty placeholders for future wiring
        'activity_logs': [],
        'staff_members': [],
        'streams': [],
        # UI role and type for template
        'ui_role': 'OWNER' if can_manage_org else 'PUBLIC',
        'ui_type': 'PRO',  # Safe default; can be enhanced later based on org tier
    }
