"""
Team views for vNext system.

Handles:
- Team creation wizard
- Team detail and roster management
- Team invitations dashboard
"""

import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings

logger = logging.getLogger(__name__)


@login_required
def team_invites(request):
    """
    Team invites dashboard (GET only).
    
    Displays user's pending team invitations with AJAX accept/decline.
    Loads both membership and email-based invites via API.
    
    Feature Flag Protection:
    - Same as vnext_hub (respects TEAM_VNEXT_ADAPTER_ENABLED)
    
    Query Budget Target: 0 (all data loaded via AJAX)
    
    Returns:
        - 200: Renders team_invites.html
        - 302: Redirects to /teams/my_invites/ if feature flags disabled
    """
    # Check feature flags (same as hub)
    force_legacy = getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False)
    adapter_enabled = getattr(settings, 'TEAM_VNEXT_ADAPTER_ENABLED', False)
    routing_mode = getattr(settings, 'TEAM_VNEXT_ROUTING_MODE', 'adapter')
    
    if force_legacy or not adapter_enabled or routing_mode == 'legacy_only':
        return redirect('/teams/my_invites/')
    
    return render(request, 'organizations/team/team_invites.html', {
        'page_title': 'Team Invitations',
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
    
    # Phase B: Load real data from database
    from apps.games.services.game_service import GameService
    from apps.organizations.models import Organization
    from apps.organizations.constants import TEAM_COUNTRIES
    
    # B1.1: Get active games
    games = GameService.list_active_games()
    
    # B1.2: Get user's organizations (where they have CEO or MANAGER role)
    user_organizations = Organization.objects.filter(
        staff_memberships__user=request.user,
        staff_memberships__role__in=['CEO', 'MANAGER']
    ).select_related('ceo').distinct().order_by('name')
    
    return render(request, 'organizations/team/team_create.html', {
        'page_title': 'Create Team or Organization',
        'games': games,
        'user_organizations': user_organizations,
        'countries': TEAM_COUNTRIES,
    })


@login_required
def team_manage(request, team_slug):
    """
    Team management UI with roster operations (P3-T6).
    
    Displays team management interface with tabs for:
    - Roster: View/add/remove/change roles for team members
    - Invites: View pending invitations (placeholder)
    - Settings: Update team branding and preferences (if authorized)
    
    NOTE: This is the MANAGEMENT interface, not the public display page.
    For public display, see team_detail() function.
    
    Permission Logic:
    - Independent team: OWNER or MANAGER can manage
    - Org-owned team: Org CEO/MANAGER or team OWNER/MANAGER can manage
    
    Args:
        team_slug: Team URL slug
    
    Returns:
        - 200: Renders team_manage.html (Tailwind UI)
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
            f"Team management accessed: {team_slug}",
            extra={
                'event_type': 'team_manage_accessed',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'can_manage': can_manage,
            }
        )
        
        return render(request, 'organizations/team/team_manage.html', {
            'team': team_data['team'],
            'team_data': json.dumps(team_data),
            'can_manage': can_manage,
        })
    
    except NotFoundError:
        messages.error(request, f'Team "{team_slug}" not found.')
        return redirect('/teams/')


def team_detail(request, team_slug):
    """
    Public team detail display page (P4-T1).
    
    Public-facing read-only page showing team information, roster, and stats.
    Accessible to anonymous users for public teams, members-only for private teams.
    
    This is the PUBLIC DISPLAY page, not the management interface.
    For management operations, see team_manage() or team_control_plane().
    
    Architecture:
    - Read-only display (no forms, no mutations)
    - Uses team_detail_service.py for queries
    - Respects team privacy (public vs private)
    - Respects organization visibility settings
    
    Args:
        team_slug: Team URL slug
    
    Returns:
        - 200: Renders team_detail.html (public display)
        - 403: Private team, user not a member
        - 404: Team not found
    """
    from apps.organizations.services.team_detail_service import TeamDetailService
    from apps.organizations.services.exceptions import NotFoundError, PermissionDeniedError
    
    try:
        # Get public display data
        context = TeamDetailService.get_public_team_display(
            team_slug=team_slug,
            viewer_user=request.user if request.user.is_authenticated else None
        )
        
        # Add demo controller flag (dev-only feature for testing role/game polymorphism)
        context['enable_demo_remote'] = settings.DEBUG
        
        # Check if user can view details
        if not context['can_view_details']:
            return render(request, 'organizations/team/team_detail.html', {
                'team': context['team'],
                'can_view_details': False,
                'error_message': 'This team is private. Only members can view details.',
                'enable_demo_remote': settings.DEBUG,  # Include flag for privacy block too
            })
        
        logger.info(
            f"Team detail (public) accessed: {team_slug}",
            extra={
                'event_type': 'team_detail_public_accessed',
                'user_id': request.user.id if request.user.is_authenticated else None,
                'team_slug': team_slug,
                'is_authenticated': request.user.is_authenticated,
            }
        )
        
        return render(request, 'organizations/team/team_detail.html', context)
    
    except NotFoundError:
        messages.error(request, f'Team "{team_slug}" not found.')
        return redirect('/teams/')
