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
    # The owner (ceo field) has all powers by default and doesn't need explicit membership
    # Staff members need explicit CEO or MANAGER role assignments
    from django.db.models import Q
    user_organizations = Organization.objects.filter(
        Q(ceo=request.user) |  # Owner has all powers
        Q(staff_memberships__user=request.user, staff_memberships__role__in=['CEO', 'MANAGER'])
    ).select_related('ceo').distinct().order_by('name')
    
    return render(request, 'organizations/team/team_create.html', {
        'page_title': 'Create Team or Organization',
        'games': games,
        'user_organizations': user_organizations,
        'countries': TEAM_COUNTRIES,
    })


@login_required
def team_manage(request, team_slug, org_slug=None):
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
    
    URL Patterns:
    - Canonical: /orgs/<org_slug>/teams/<team_slug>/manage/ (when team has org)
    - Alias: /teams/<team_slug>/manage/ (redirects to canonical if org exists)
    
    Args:
        team_slug: Team URL slug
        org_slug: Organization slug (optional, validates team belongs to org)
    
    Returns:
        - 200: Renders team_manage.html (Tailwind UI)
        - 302: Redirects to canonical URL if accessed via alias
        - 404: Team not found or org_slug mismatch
    """
    import json
    from apps.organizations.services.team_service import TeamService
    from apps.organizations.services.exceptions import NotFoundError
    from apps.organizations.models import Team, TeamMembership, OrganizationMembership
    from apps.organizations.choices import MembershipRole, MembershipStatus
    from django.http import Http404
    
    try:
        # Get team object for validation and permission check
        team = Team.objects.select_related('organization').get(slug=team_slug)
        
        # Handle URL routing based on team type
        if team.organization:
            # Organization team - validate org_slug
            if org_slug:
                if team.organization.slug != org_slug:
                    raise Http404(f"Team '{team_slug}' does not belong to organization '{org_slug}'")
            else:
                # No org_slug provided - redirect to canonical org URL
                return redirect('organizations:org_team_manage', 
                              org_slug=team.organization.slug, 
                              team_slug=team_slug)
        else:
            # Independent team
            if org_slug:
                # Independent team accessed via org URL - 404
                raise Http404(f"Team '{team_slug}' is an independent team, not part of organization '{org_slug}'")
            # Continue normally for independent team
        
        # PERMISSION CHECK: Must be owner/creator, manager, or org admin
        has_permission = False
        
        # Check if user created/owns the team
        if team.created_by == request.user:
            has_permission = True
        
        # For org teams, check org-level permissions
        if team.organization and not has_permission:
            org_membership = OrganizationMembership.objects.filter(
                organization=team.organization,
                user=request.user,
                role__in=['CEO', 'MANAGER', 'ADMIN'],
                status='ACTIVE'
            ).first()
            if org_membership:
                has_permission = True
        
        # Check team-level permissions
        if not has_permission:
            team_membership = TeamMembership.objects.filter(
                team=team,
                user=request.user,
                role__in=['MANAGER', 'COACH'],
                status='ACTIVE'
            ).first()
            if team_membership:
                has_permission = True
        
        # Deny access if no permission
        if not has_permission and not request.user.is_superuser:
            messages.error(request, "You don't have permission to manage this team.")
            if team.organization:
                return redirect('organizations:org_team_detail', 
                              org_slug=team.organization.slug, 
                              team_slug=team_slug)
            else:
                return redirect('organizations:team_detail', team_slug=team_slug)
        
        # Get team data
        team_data = TeamService.get_team_detail(
            team_slug=team_slug,
            include_members=True,
            include_invites=True
        )
        
        # can_manage already determined above by permission check
        can_manage = has_permission
        
        logger.info(
            f"Team management accessed: {team_slug}",
            extra={
                'event_type': 'team_manage_accessed',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'can_manage': can_manage,
            }
        )
        
        # HQ Template Context (minimal stubs for Phase 14)
        # Template is self-contained, provide safe defaults
        context = {
            'team': team_data.get('team', {}),
            'team_data': team_data,
            'can_manage': can_manage,
            'page_title': f"{team_data.get('team', {}).get('name', 'Team')} - HQ",
            # Stubs for HQ template sections (prevent crashes)
            'roster': team_data.get('members', []),
            'pending_invites': team_data.get('invites', []),
            'stats': {},
            'recent_matches': [],
            'upcoming_events': [],
            'team_achievements': [],
            'training_sessions': [],
            'media_gallery': [],
            'settings': {},
            'org_context': {'is_org_admin': False},
        }
        
        return render(request, 'organizations/team/team_manage_hq.html', context)
    
    except NotFoundError:
        messages.error(request, f'Team "{team_slug}" not found.')
        return redirect('/teams/')


def team_detail(request, team_slug, org_slug=None):
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
    
    URL Patterns:
    - Canonical: /orgs/<org_slug>/teams/<team_slug>/ (when team has organization)
    - Alias: /teams/<team_slug>/ (redirects to canonical if org exists)
    
    Args:
        team_slug: Team URL slug
        org_slug: Organization slug (optional, validates team belongs to org)
    
    Returns:
        - 200: Renders team_detail.html (public display)
        - 302: Redirects to canonical URL if accessed via alias
        - 403: Private team, user not a member
        - 404: Team not found or org_slug mismatch
    """
    from apps.organizations.services.team_detail_context import get_team_detail_context
    from apps.organizations.models import Team
    from django.http import Http404
    
    try:
        # Get team to validate org_slug and determine canonical URL
        team = Team.objects.select_related('organization').get(slug=team_slug)
        
        # Handle URL routing based on team type
        if team.organization:
            # Organization team - validate org_slug
            if org_slug:
                if team.organization.slug != org_slug:
                    raise Http404(f"Team '{team_slug}' does not belong to organization '{org_slug}'")
            else:
                # No org_slug - redirect to canonical org URL
                return redirect('organizations:org_team_detail', 
                              org_slug=team.organization.slug, 
                              team_slug=team_slug)
        else:
            # Independent team
            if org_slug:
                # Independent team accessed via org URL - 404
                raise Http404(f"Team '{team_slug}' is an independent team, not part of organization '{org_slug}'")
            # Continue normally for independent team
        
        # Build complete context using new contract-based builder
        context = get_team_detail_context(
            team_slug=team_slug,
            viewer=request.user if request.user.is_authenticated else None,
            request=request
        )
        
        logger.info(
            f"Team detail accessed: {team_slug}",
            extra={
                'event_type': 'team_detail_accessed',
                'user_id': request.user.id if request.user.is_authenticated else None,
                'team_slug': team_slug,
                'is_authenticated': request.user.is_authenticated,
                'viewer_role': context['viewer']['role'],
            }
        )
        
        return render(request, 'organizations/team/team_detail.html', context)
    
    except Team.DoesNotExist:
        messages.error(request, f'Team "{team_slug}" not found.')
        return redirect('/teams/')
