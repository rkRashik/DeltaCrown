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
from apps.common.seo import absolute_url, breadcrumb_schema, build_seo, truncate_meta
from apps.organizations.templatetags.org_media import safe_href

logger = logging.getLogger(__name__)


@login_required
def team_invites(request):
    """
    Team invites dashboard (GET only).
    
    Displays user's pending team invitations with AJAX accept/decline.
    Loads both membership and email-based invites via API.
    
    Feature Flag Protection:
    - Only TEAM_VNEXT_FORCE_LEGACY blocks access (emergency killswitch)
    
    Query Budget Target: 0 (all data loaded via AJAX)
    
    Returns:
        - 200: Renders team_invites.html
        - 302: Redirects to /teams/my_invites/ if FORCE_LEGACY enabled
    """
    # Emergency killswitch only
    force_legacy = getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False)
    
    if force_legacy:
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
    - Only TEAM_VNEXT_FORCE_LEGACY blocks access (emergency killswitch)
    
    Returns:
        - 200: Renders team_create.html (Tailwind UI)
        - 302: Redirects to home if FORCE_LEGACY enabled
    """
    # Emergency killswitch — only FORCE_LEGACY blocks team creation
    force_legacy = getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False)
    
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
    
    # B1.1: Get active games (prefetch roster_config for dynamic slot sizing)
    games = GameService.list_active_games().select_related('roster_config')
    
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
    from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
    from apps.organizations.services.team_authority import (
        can_access_team_hq as _ta_can_access_team_hq,
        can_disband_team as _ta_can_disband_team,
        can_manage_competitive_settings as _ta_can_manage_competitive_settings,
        can_manage_discord as _ta_can_manage_discord,
        can_manage_roster as _ta_can_manage_roster,
        can_manage_team_profile as _ta_can_manage_team_profile,
        can_manage_team_settings as _ta_can_manage_team_settings,
        can_manage_training as _ta_can_manage_training,
        can_transfer_ownership as _ta_can_transfer_ownership,
        get_team_actor,
    )
    from django.http import Http404

    try:
        team = Team.objects.select_related(
            'organization', 'organization__ranking', 'created_by', 'created_by__profile',
        ).get(slug=team_slug)

        if team.status != TeamStatus.ACTIVE:
            messages.error(request, "This team is not active and cannot be managed.")
            return redirect('organizations:team_detail', team_slug=team_slug)

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
        actor = get_team_actor(request.user, team)

        if not _ta_can_access_team_hq(request.user, team):
            messages.error(request, "You must be a team member to access this page.")
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

        # Game name + roster config + game roles
        from apps.games.models import Game
        game_display = "Unknown"
        roster_config = None
        game_roles = []
        game = None
        try:
            game = Game.objects.select_related('roster_config').get(id=team.game_id)
            game_display = game.name
            roster_config = getattr(game, 'roster_config', None)
            # Fetch game-specific roles for the Edit Role modal
            from apps.games.models.role import GameRole
            game_roles = list(
                GameRole.objects.filter(game=game, is_active=True)
                .order_by('order', 'role_name')
                .values('id', 'role_name', 'role_code', 'description', 'icon', 'color')
            )
        except Game.DoesNotExist:
            pass

        # ── Attach game passport data to each member (for info popover) ──
        for m in members:
            m.gp_ign = ''
            m.gp_discriminator = ''
            m.gp_in_game_name = ''
            m.gp_platform = ''
            m.gp_rank_name = ''
            m.gp_rank_image_url = ''
            m.gp_rank_points = ''
            m.gp_peak_rank = ''
            m.gp_main_role = ''
            m.gp_region = ''
            m.gp_matches_played = 0
            m.gp_win_rate = 0
            m.gp_kd_ratio = None
            m.gp_hours_played = ''
            m.gp_is_lft = False
            m.gp_verification_status = ''
            m.game_profile = {}

        if game and members:
            from apps.user_profile.models_main import GameProfile
            member_user_ids = [m.user_id for m in members]
            gp_map = {}
            try:
                for gp in GameProfile.objects.filter(
                    user_id__in=member_user_ids,
                    game_id=team.game_id,
                    status=GameProfile.STATUS_ACTIVE,
                ).only(
                    'user_id', 'game_id', 'ign', 'discriminator', 'in_game_name',
                    'platform', 'rank_name', 'rank_image', 'rank_points',
                    'peak_rank', 'main_role', 'region',
                    'matches_played', 'win_rate', 'kd_ratio', 'hours_played',
                    'is_lft', 'verification_status',
                ):
                    gp_map[gp.user_id] = gp
            except Exception:
                pass
            for m in members:
                gp = gp_map.get(m.user_id)
                m.gp_ign = gp.ign if gp else ''
                m.gp_discriminator = gp.discriminator if gp else ''
                # Build full Game ID on the fly (ign + discriminator) — resilient to stale in_game_name
                if gp and gp.ign:
                    if gp.discriminator:
                        disc = gp.discriminator
                        # Ensure separator character is present (some records lack #)
                        if not disc.startswith('#') and not disc.startswith('-'):
                            disc = f'#{disc}'
                        m.gp_in_game_name = f"{gp.ign}{disc}"
                    else:
                        m.gp_in_game_name = gp.ign
                else:
                    m.gp_in_game_name = ''
                m.gp_platform = gp.platform if gp else ''
                m.gp_rank_name = gp.rank_name if gp else ''
                m.gp_rank_image_url = gp.rank_image.url if gp and gp.rank_image else ''
                m.gp_rank_points = gp.rank_points if gp and gp.rank_points else ''
                m.gp_peak_rank = gp.peak_rank if gp else ''
                m.gp_main_role = gp.main_role if gp else ''
                m.gp_region = gp.region if gp else ''
                m.gp_matches_played = gp.matches_played if gp else 0
                m.gp_win_rate = gp.win_rate if gp else 0
                m.gp_kd_ratio = gp.kd_ratio if gp else None
                m.gp_hours_played = gp.hours_played if gp and gp.hours_played else ''
                m.gp_is_lft = gp.is_lft if gp else False
                m.gp_verification_status = gp.verification_status if gp else ''
                if gp:
                    m.game_profile = {
                        'game_id': gp.game_id,
                        'ign': m.gp_in_game_name,
                        'in_game_name': m.gp_in_game_name,
                        'platform': m.gp_platform,
                        'rank': m.gp_rank_name,
                        'rank_name': m.gp_rank_name,
                        'rank_points': m.gp_rank_points,
                        'peak_rank': m.gp_peak_rank,
                        'main_role': m.gp_main_role,
                        'region': m.gp_region,
                        'matches_played': m.gp_matches_played,
                        'win_rate': m.gp_win_rate,
                        'kd_ratio': m.gp_kd_ratio,
                        'hours_played': m.gp_hours_played,
                        'is_lft': m.gp_is_lft,
                        'verification_status': m.gp_verification_status,
                        'has_passport': True,
                    }

        is_owner = actor.role == MembershipRole.OWNER or actor.is_creator
        is_admin = actor.is_team_admin
        is_coach = actor.role == MembershipRole.COACH
        is_member = actor.membership is not None
        user_role = actor.role if actor.role not in ("NONE", "") else (
            "OWNER" if (actor.is_creator or actor.is_superuser) else "GUEST"
        )
        can_access_hq = True
        can_manage_training = _ta_can_manage_training(request.user, team)

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
        is_org_ceo = actor.org_authority == "CEO"
        org_control_plane_url = ''
        org_policies = {}
        org_staff = []
        if org:
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

            # ── Org staff with authority over this team ──
            from apps.organizations.models import OrganizationMembership
            org_staff_qs = OrganizationMembership.objects.filter(
                organization=org,
                role__in=['CEO', 'MANAGER'],
            ).select_related('user', 'user__profile').order_by('role', 'joined_at')
            org_staff = []
            for sm in org_staff_qs:
                org_staff.append({
                    'user': sm.user,
                    'username': sm.user.username,
                    'role': sm.role,
                    'role_display': sm.get_role_display(),
                    'avatar_url': sm.user.profile.avatar.url if hasattr(sm.user, 'profile') and sm.user.profile.avatar else '',
                })
            # Also include CEO from org.ceo if not already in staff memberships
            ceo_user = org.ceo
            if ceo_user and not any(s['user'].id == ceo_user.id for s in org_staff):
                org_staff.insert(0, {
                    'user': ceo_user,
                    'username': ceo_user.username,
                    'role': 'CEO',
                    'role_display': 'CEO (Owner)',
                    'avatar_url': ceo_user.profile.avatar.url if hasattr(ceo_user, 'profile') and ceo_user.profile.avatar else '',
                })

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

        # ── Tournament & Match data (Competition Hub) ──
        team_tournaments = []
        team_tournament_count = 0
        team_upcoming_matches = []
        team_tournament_history = []
        try:
            from apps.tournaments.models import Registration, Tournament, Match
            team_regs = (
                Registration.objects.filter(
                    team_id=team.id, is_deleted=False,
                )
                .exclude(status__in=['cancelled', 'rejected', 'draft'])
                .select_related('tournament', 'tournament__game')
                .order_by('-created_at')
            )
            team_tournament_count = team_regs.values('tournament').distinct().count()
            for reg in team_regs[:10]:
                t = reg.tournament
                if t:
                    _eff = t.get_effective_status() if hasattr(t, 'get_effective_status') else t.status
                    entry = {
                        'id': t.id,
                        'name': t.name,
                        'slug': getattr(t, 'slug', ''),
                        'status': _eff,
                        'game_name': t.game.display_name if t.game else '',
                        'game_icon': t.game.icon.url if t.game and t.game.icon else None,
                        'tournament_start': getattr(t, 'tournament_start', None),
                        'prize_pool': getattr(t, 'prize_pool', None),
                        'format': getattr(t, 'format', ''),
                        'reg_status': getattr(reg, 'status', ''),
                        'is_live': _eff == 'live',
                    }
                    if _eff == 'completed':
                        team_tournament_history.append(entry)
                    else:
                        team_tournaments.append(entry)

            # Upcoming matches for this team
            upcoming_states = ['scheduled', 'check_in', 'ready', 'live']
            team_registration_ids = list(
                Registration.objects.filter(
                    team_id=team.id,
                    is_deleted=False,
                ).values_list('id', flat=True)
            )
            team_participant_ids = {team.id, *team_registration_ids}
            team_matches = (
                Match.objects.filter(
                    models.Q(participant1_id__in=team_participant_ids) |
                    models.Q(participant2_id__in=team_participant_ids),
                    state__in=upcoming_states,
                    is_deleted=False,
                )
                .select_related('tournament')
                .order_by('scheduled_time', 'round_number', 'match_number')[:6]
            )
            team_matches = list(team_matches)
            match_participant_ids = {
                participant_id
                for m in team_matches
                for participant_id in (m.participant1_id, m.participant2_id)
                if participant_id
            }
            registration_team_rows = list(
                Registration.objects.filter(
                    id__in=match_participant_ids,
                    is_deleted=False,
                    team_id__isnull=False,
                ).values_list('id', 'team_id')
            )
            registration_team_ids = {team_id for _, team_id in registration_team_rows if team_id}
            team_name_map = {
                t.id: t.name
                for t in Team.objects.filter(id__in=registration_team_ids).only('id', 'name')
            }
            registration_team_names = {
                reg_id: team_name_map.get(team_id, '')
                for reg_id, team_id in registration_team_rows
                if team_name_map.get(team_id)
            }
            for m in team_matches:
                is_p1 = m.participant1_id in team_participant_ids
                opponent_id = m.participant2_id if is_p1 else m.participant1_id
                opponent_fallback = m.participant2_name if is_p1 else m.participant1_name
                opponent = registration_team_names.get(opponent_id) or opponent_fallback
                team_upcoming_matches.append({
                    'match_id': m.id,
                    'tournament_name': m.tournament.name if m.tournament else '',
                    'tournament_slug': m.tournament.slug if m.tournament else '',
                    'opponent': opponent or 'TBD',
                    'scheduled_time': m.scheduled_time,
                    'round_number': m.round_number,
                    'state': m.state,
                    'is_live': m.state == 'live',
                })
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
            'user_membership_id': user_membership.id if user_membership else None,
            'is_owner': is_owner,
            'is_admin': is_admin,
            'is_coach': is_coach,
            'is_member': is_member,
            'user_role': user_role,
            # Permission convenience flags (used by templates)
            'can_access_hq': can_access_hq,
            'can_manage_roster': _ta_can_manage_roster(request.user, team),
            'can_edit_team_profile': _ta_can_manage_team_profile(request.user, team),
            'can_manage_discord': _ta_can_manage_discord(request.user, team),
            'can_manage_settings': _ta_can_manage_team_settings(request.user, team),
            'can_manage_training': can_manage_training,
            'can_assign_captain_title': is_owner,
            'can_assign_managers': is_owner,
            'can_assign_coach': is_admin,
            'can_change_player_role': is_admin,
            'can_register_tournaments': actor.is_competitive_authority or is_admin,
            'can_delete_team': _ta_can_disband_team(request.user, team),
            'can_transfer_ownership': _ta_can_transfer_ownership(request.user, team),
            # Roster info
            'current_roster_size': len(members),
            'has_staff': any(m.role in (MembershipRole.MANAGER, MembershipRole.COACH, MembershipRole.ANALYST, MembershipRole.SCOUT) for m in members),
            'has_captain': any(m.is_tournament_captain for m in members),
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
            'game_id_label': (game.game_id_label if game and game.game_id_label else 'Game ID'),
            'game_roles': game_roles,
            'visibility_choices': [
                ('PUBLIC', 'Public'),
                ('PRIVATE', 'Private'),
                ('UNLISTED', 'Unlisted'),
            ],
            'platform_choices': [
                ('PC', 'PC'),
                ('Mobile', 'Mobile'),
                ('Console', 'Console'),
                ('Cross-Platform', 'Cross-Platform'),
            ],
            # Phase 4: Org integration
            'org_context': org_context,
            'org_staff': org_staff if org else [],
            'is_org_ceo': is_org_ceo,
            'org_control_plane_url': org_control_plane_url,
            'org_policies': org_policies,
            # Phase 4: Economy
            'wallet_context': wallet_context,
            # Competition Hub data
            'team_tournaments': team_tournaments,
            'team_tournament_count': team_tournament_count,
            'team_upcoming_matches': team_upcoming_matches,
            'team_tournament_history': team_tournament_history,
            # Discord bot invite URL
            'discord_bot_invite_url': (
                f'https://discord.com/api/oauth2/authorize?client_id={settings.DISCORD_CLIENT_ID}&permissions=8&scope=bot%20applications.commands'
                if settings.DISCORD_CLIENT_ID else ''
            ),
        }

        return render(request, 'organizations/team/manage_hq.html', context)

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
        # Pass pre-fetched team to avoid duplicate DB query
        context = get_team_detail_context(
            team_slug=team_slug,
            viewer=request.user if request.user.is_authenticated else None,
            request=request,
            team=team,
        )
        game_name = ''
        game_obj = context.get('game') or context.get('game_obj')
        if game_obj:
            game_name = getattr(game_obj, 'display_name', None) or getattr(game_obj, 'name', '')
        description = team.description or team.tagline or (
            f"{team.name} is a DeltaCrown esports team"
            + (f" competing in {game_name}" if game_name else "")
            + (f" from {team.region}." if team.region else ".")
        )
        image_url = team.banner.url if team.banner else (team.logo.url if team.logo else None)
        team_schema = {
            '@context': 'https://schema.org',
            '@type': 'SportsTeam',
            'name': team.name,
            'url': absolute_url(team.get_absolute_url()),
            'description': truncate_meta(description, 240),
            'sport': game_name or 'Esports',
            'areaServed': team.region,
        }
        if image_url:
            team_schema['image'] = absolute_url(image_url)
        same_as = [
            safe_url for safe_url in [
                safe_href(url) for url in [
                team.website_url,
                team.twitter_url,
                team.instagram_url,
                team.youtube_url,
                team.twitch_url,
                team.facebook_url,
                team.tiktok_url,
                team.discord_url,
                ]
            ] if safe_url
        ]
        if same_as:
            team_schema['sameAs'] = same_as[:8]
        if team.organization:
            team_schema['memberOf'] = {
                '@type': 'Organization',
                'name': team.organization.name,
                'url': absolute_url(team.organization.get_absolute_url()),
            }
        roster_count = 0
        roster = context.get('roster')
        if isinstance(roster, dict):
            roster_count = len(roster.get('members') or roster.get('starters') or [])
        context['entity_links'] = [
            {'label': 'Crown Points Rankings', 'url': '/competition/leaderboards/', 'detail': 'Compare teams across the platform'},
            {'label': f"{game_name} Rankings" if game_name else 'Game Rankings', 'url': f"/competition/leaderboards/{team.game_id}/", 'detail': 'Game-specific leaderboard'},
            {'label': 'Tournaments', 'url': '/tournaments/', 'detail': 'Find events this roster can enter'},
        ]
        if team.organization:
            context['entity_links'].insert(0, {'label': team.organization.name, 'url': team.organization.get_absolute_url(), 'detail': 'Parent organization'})
        context['seo'] = build_seo(
            title=f"{team.name} | DeltaCrown Team",
            description=description,
            canonical=absolute_url(team.get_absolute_url()),
            noindex=team.visibility != 'PUBLIC' or team.is_temporary or (not team.description and not team.tagline and roster_count == 0),
            og_image=image_url,
            schema=[
                breadcrumb_schema([
                    ('Home', '/'),
                    ('Teams', '/teams/'),
                    (team.name, team.get_absolute_url()),
                ]),
                team_schema,
            ],
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
