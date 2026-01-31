"""
Organization Detail Service
Provides context for organization detail page.
"""

from django.shortcuts import get_object_or_404
from apps.organizations.models.organization import Organization
from apps.organizations.permissions import get_permission_context


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
    # Note: Organization has NO teams relation yet (Option C - Legacy Team authoritative)
    try:
        organization = Organization.objects.select_related(
            'ceo'
        ).get(slug=org_slug)
    except Organization.DoesNotExist:
        from django.http import Http404
        raise Http404(f'Organization with slug "{org_slug}" does not exist.')
    
    # Permission: CEO OR org MANAGER/ADMIN OR staff
    # Use centralized permission module
    permissions = get_permission_context(viewer, organization)
    
    # TODO PHASE 6: Organizations do NOT own teams yet (Legacy Team is authoritative)
    # organization.teams relation does not exist until migration complete
    # Stubbing team list until org-team FK is activated
    active_teams = []
    active_teams_count = 0
    
    # TODO PHASE 6: Build squad data once org-team FK activated
    # Currently stubbed - Organizations do not own teams yet
    squads = []
    
    return {
        'organization': organization,
        'teams': [],  # TODO PHASE 6: Organization→Teams ownership deferred (Option C)
        'teams_count': 0,  # TODO PHASE 6: Will populate after org-team FK activated
        'active_teams_count': active_teams_count,
        'squads': squads,
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
