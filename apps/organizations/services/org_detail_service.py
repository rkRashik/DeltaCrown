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
            - squads: List of active teams with IGL/Manager info and rankings
    """
    from django.conf import settings
    
    # Query organization with proper related data
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
    
    # Phase 10: Fetch org teams with rankings from CompetitionService
    from apps.organizations.models import Team
    
    active_teams = Team.objects.filter(
        organization=organization,
        status='ACTIVE'
    ).select_related('game', 'created_by').order_by('-created_at')[:20]
    
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
                'rank': None,
                'tier': 'UNRANKED',
                'score': 0,
            })
    
    # Get org empire score if competition enabled
    org_empire_score = None
    if competition_enabled:
        try:
            from apps.competition.services import CompetitionService
            org_empire_score = CompetitionService.get_org_empire_score(organization.id)
        except Exception:
            pass
    
    # Fetch org staff members
    from apps.organizations.models import OrganizationMembership
    org_members = OrganizationMembership.objects.filter(
        organization=organization
    ).select_related('user').order_by('role', 'joined_at')
    
    member_count = org_members.count()
    
    return {
        'organization': organization,
        'teams': list(active_teams),
        'teams_count': active_teams_count,
        'active_teams_count': active_teams_count,
        'squads': squads,
        'org_empire_score': org_empire_score,
        'org_members': list(org_members),
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
