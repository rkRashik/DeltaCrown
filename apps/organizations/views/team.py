"""
Team views for vNext system.

Handles:
- Team creation wizard
- Team detail and roster management
- Team invitations dashboard
"""

import logging
from django.contrib.auth.decorators import login_required
from django.db import models
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
    Team HQ management console — renders teams/manage_hq.html.
    Powers the unified manage page for both independent and org teams.
    """
    from apps.organizations.models import Team, TeamMembership, OrganizationMembership
    from apps.organizations.models.team_invite import TeamInvite
    from apps.organizations.choices import MembershipRole, MembershipStatus
    from django.http import Http404

    try:
        team = Team.objects.select_related(
            'organization', 'organization__ranking', 'created_by', 'created_by__profile',
        ).get(slug=team_slug)

        # Org team routing
        if team.organization:
            if org_slug and team.organization.slug != org_slug:
                raise Http404(f"Team '{team_slug}' does not belong to '{org_slug}'")
            if not org_slug:
                return redirect('organizations:org_team_manage',
                                org_slug=team.organization.slug,
                                team_slug=team_slug)
        elif org_slug:
            raise Http404(f"Team '{team_slug}' is independent, not part of '{org_slug}'")

        # ── Permission check ──
        has_permission = request.user.is_superuser or team.created_by == request.user

        if team.organization and not has_permission:
            org_membership = OrganizationMembership.objects.filter(
                organization=team.organization,
                user=request.user,
                role__in=['CEO', 'MANAGER'],
            ).first()
            if org_membership:
                has_permission = True

        if not has_permission:
            team_membership = TeamMembership.objects.filter(
                team=team,
                user=request.user,
                role__in=[MembershipRole.OWNER, MembershipRole.MANAGER,
                          MembershipRole.COACH],
                status=MembershipStatus.ACTIVE,
            ).first()
            if team_membership:
                has_permission = True

        if not has_permission:
            messages.error(request, "You don't have permission to manage this team.")
            return redirect('organizations:team_detail', team_slug=team_slug)

        # ── Build context ──
        user_membership = TeamMembership.objects.filter(
            team=team, user=request.user, status=MembershipStatus.ACTIVE,
        ).first()

        members = list(
            team.vnext_memberships
            .filter(status=MembershipStatus.ACTIVE)
            .select_related('user', 'user__profile')
            .order_by('-role', '-is_tournament_captain', 'joined_at')
        )

        pending_invites = (
            team.vnext_invites
            .filter(status='PENDING')
            .select_related('invited_user', 'invited_user__profile', 'inviter', 'inviter__profile')
            .order_by('-created_at')
        )

        # Game name + roster config
        from apps.games.models import Game
        game_display = "Unknown"
        roster_config = None
        try:
            game = Game.objects.select_related('roster_config').get(id=team.game_id)
            game_display = game.name
            roster_config = getattr(game, 'roster_config', None)
        except Game.DoesNotExist:
            pass

        is_owner = (
            user_membership and user_membership.role == MembershipRole.OWNER
        ) or team.created_by == request.user
        is_admin = is_owner or (
            user_membership and user_membership.role in (
                MembershipRole.OWNER, MembershipRole.MANAGER
            )
        )

        role_choices = [
            {'value': c[0], 'label': c[1]}
            for c in MembershipRole.choices
        ]

        # Region choices
        try:
            from apps.organizations.constants.regions import COUNTRIES
            region_choices = [{'value': c[0], 'label': c[1]} for c in COUNTRIES if c[0]]
        except Exception:
            region_choices = []

        # ── Org integration context (Phase 4) ──
        org = team.organization
        org_context = None
        is_org_ceo = False
        org_control_plane_url = ''
        org_policies = {}
        if org:
            is_org_ceo = org.ceo_id == request.user.id
            org_control_plane_url = f'/orgs/{org.slug}/control-plane/'
            # Org policies that affect teams
            org_policies = {
                'roster_locked': getattr(org, 'roster_locked', False),
                'enforce_brand': getattr(org, 'enforce_brand', False),
                'revenue_split_config': getattr(org, 'revenue_split_config', {}),
            }
            # Empire Score from OrganizationRanking
            ranking = getattr(org, 'ranking', None)
            empire_score = getattr(ranking, 'empire_score', 0) if ranking else 0
            global_rank = getattr(ranking, 'global_rank', None) if ranking else None
            org_context = {
                'name': org.name,
                'slug': org.slug,
                'logo_url': org.logo.url if org.logo else '',
                'badge_url': org.badge.url if org.badge else '',
                'url': org.get_absolute_url(),
                'hub_url': org.get_hub_url(),
                'control_plane_url': org_control_plane_url,
                'is_verified': org.is_verified,
                'enforce_brand': org.enforce_brand,
                'empire_score': empire_score,
                'global_rank': global_rank,
                'ceo_id': org.ceo_id,
            }

        # ── Economy context (Phase 4) ──
        wallet_context = None
        if is_owner or is_org_ceo:
            try:
                from apps.economy.models import DeltaCrownWallet
                owner_user = team.created_by
                wallet = DeltaCrownWallet.objects.filter(
                    profile=owner_user.profile
                ).first()
                if wallet:
                    wallet_context = {
                        'balance': wallet.cached_balance,
                        'held_balance': getattr(wallet, 'pending_balance', 0),
                        'lifetime_earned': (
                            wallet.transactions
                            .filter(amount__gt=0)
                            .aggregate(total=models.Sum('amount'))['total'] or 0
                        ),
                    }
            except Exception:
                pass

        context = {
            'team': team,
            'members': members,
            'pending_invites': pending_invites,
            'join_requests': [],
            'join_request_count': 0,
            # Current user
            'user_membership': user_membership,
            'is_owner': is_owner,
            'is_admin': is_admin,
            # Permission convenience flags (used by templates)
            'can_manage_roster': is_admin,
            'can_edit_team_profile': is_admin,
            'can_assign_captain_title': is_owner,
            'can_assign_managers': is_owner,
            'can_assign_coach': is_admin,
            'can_change_player_role': is_admin,
            'can_register_tournaments': is_admin,
            'can_delete_team': is_owner,
            'can_transfer_ownership': is_owner,
            # Roster info
            'current_roster_size': len(members),
            'has_staff': any(m.role in (MembershipRole.MANAGER, MembershipRole.COACH, MembershipRole.ANALYST, MembershipRole.SCOUT) for m in members),
            'max_roster_size': roster_config.max_roster_size if roster_config else 10,
            'min_roster_size': roster_config.min_roster_size if roster_config else 1,
            'max_team_size': roster_config.max_team_size if roster_config else 5,
            'roster_config': roster_config,
            # Roster lock (org policy or owner manual lock)
            'roster_locked': getattr(team, 'roster_locked', False) or (
                team.organization and getattr(team.organization, 'roster_locked', False)
            ),
            'roster_lock_source': (
                'organization' if (team.organization and getattr(team.organization, 'roster_locked', False))
                else ('owner' if getattr(team, 'roster_locked', False) else None)
            ),
            # Dropdowns
            'role_choices': role_choices,
            'region_choices': region_choices,
            'game_display': game_display,
            'visibility_choices': [
                ('PUBLIC', 'Public'),
                ('PRIVATE', 'Private'),
                ('UNLISTED', 'Unlisted'),
            ],
            # Phase 4: Org integration
            'org_context': org_context,
            'is_org_ceo': is_org_ceo,
            'org_control_plane_url': org_control_plane_url,
            'org_policies': org_policies,
            # Phase 4: Economy
            'wallet_context': wallet_context,
        }

        return render(request, 'teams/manage_hq.html', context)

    except Team.DoesNotExist:
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
        team = Team.objects.select_related(
            'organization', 'organization__ranking', 'created_by',
        ).get(slug=team_slug)
        
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
