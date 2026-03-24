"""
Tournament Hub — Participant Dashboard & Match Lobby (v3).

The Hub is the player's unified "Mission Control" combining:
- Command Center (overview, countdown, announcements)
- Match Lobby (check-in, veto, result submission)
- Squad Management (roster, diagnostics)
- Tournament Intel (bracket, standings, schedule)

This replaces the Sprint 5 lobby (checkin.py) and Sprint 10 lobby (lobby.py)
with a single, SPA-style page driven by JSON API endpoints for real-time data.
"""

import json
import logging
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.contrib import messages

from apps.tournaments.models import (
    Tournament,
    Registration,
    TournamentLobby,
    CheckIn,
    LobbyAnnouncement,
    TournamentSponsor,
    PrizeClaim,
    TournamentStaff,
    HubSupportTicket,
)
from apps.tournaments.models.bracket import Bracket, BracketNode
from apps.tournaments.models.group import Group, GroupStanding
from apps.tournaments.models.match import Match
from apps.tournaments.models.prize import PrizeTransaction
from apps.tournaments.services.lobby_service import LobbyService

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def _is_tournament_staff_or_organizer(user, tournament):
    """Check if user is the organizer, a site admin, or assigned tournament staff."""
    if not user or not user.is_authenticated:
        return False
    # Organizer / superuser / site staff
    if user == tournament.organizer or user.is_staff or user.is_superuser:
        return True
    # Legacy TournamentStaff assignments
    if TournamentStaff.objects.filter(tournament=tournament, user=user).exists():
        return True
    # Phase 7 StaffAssignment
    from apps.tournaments.models.staffing import TournamentStaffAssignment
    if TournamentStaffAssignment.objects.filter(tournament=tournament, user=user).exists():
        return True
    return False


def _get_user_registration(user, tournament):
    """Return the user's active Registration for this tournament (individual or team)."""
    from apps.organizations.models import TeamMembership

    reg = Registration.objects.filter(
        user=user,
        tournament=tournament,
        is_deleted=False,
        status__in=[
            Registration.PENDING,
            Registration.PAYMENT_SUBMITTED,
            Registration.CONFIRMED,
            Registration.AUTO_APPROVED,
            Registration.NEEDS_REVIEW,
        ],
    ).first()
    if reg:
        return reg

    # Check team registrations
    user_team_ids = TeamMembership.objects.filter(
        user=user,
        status=TeamMembership.Status.ACTIVE,
    ).values_list('team_id', flat=True)

    return Registration.objects.filter(
        tournament=tournament,
        team_id__in=user_team_ids,
        is_deleted=False,
        status__in=[
            Registration.PENDING,
            Registration.PAYMENT_SUBMITTED,
            Registration.CONFIRMED,
            Registration.AUTO_APPROVED,
            Registration.NEEDS_REVIEW,
        ],
    ).first()


def _resolve_hub_view_mode(request, tournament, registration):
    """Resolve whether this Hub request should render as staff or participant view."""
    is_staff_or_organizer = _is_tournament_staff_or_organizer(request.user, tournament)
    can_toggle_view_mode = bool(is_staff_or_organizer and registration)
    view_as = (request.GET.get('view_as') or '').strip().lower()
    is_participant_view = can_toggle_view_mode and view_as == 'participant'
    is_staff_view = bool(is_staff_or_organizer and not is_participant_view)

    query_suffix = ''
    if is_participant_view:
        query_suffix = '?' + urlencode({'view_as': 'participant'})

    return {
        'is_staff_or_organizer': is_staff_or_organizer,
        'is_staff_view': is_staff_view,
        'is_participant_view': is_participant_view,
        'can_toggle_view_mode': can_toggle_view_mode,
        'query_suffix': query_suffix,
    }


def _is_registration_verified_for_critical_actions(registration):
    """Only confirmed/auto-approved registrations may perform critical Hub actions."""
    if not registration:
        return False
    return registration.status in (Registration.CONFIRMED, Registration.AUTO_APPROVED)


def _critical_lock_reason(registration):
    if not registration:
        return 'Registration required before critical actions are available.'
    status_map = {
        Registration.PENDING: 'Your registration is pending organizer approval. Critical actions are locked.',
        Registration.PAYMENT_SUBMITTED: 'Payment verification is pending. Critical actions are locked until verification completes.',
        Registration.NEEDS_REVIEW: 'Your registration is under manual review. Critical actions are locked for now.',
        Registration.SUBMITTED: 'Your registration submission is still processing. Critical actions are locked.',
        Registration.DRAFT: 'Complete your registration first. Critical actions are locked.',
    }
    return status_map.get(registration.status, 'Critical actions are currently locked for this registration state.')


def _critical_actions_locked(user, tournament, registration):
    if _is_tournament_staff_or_organizer(user, tournament):
        return False
    return not _is_registration_verified_for_critical_actions(registration)


def _forbidden_if_critical_locked(request, tournament, registration):
    if _critical_actions_locked(request.user, tournament, registration):
        return JsonResponse({
            'error': 'critical_actions_locked',
            'reason': _critical_lock_reason(registration),
        }, status=403)
    return None


def _build_hub_context(request, tournament, registration, query_suffix=''):
    """Build the full context dict for the hub template."""
    from apps.organizations.models import TeamMembership
    from apps.games.services import game_service

    user = request.user
    now = timezone.now()
    is_team = tournament.participation_type == 'team'

    # ── Lobby & Check-in ────────────────────────────────
    lobby = getattr(tournament, 'lobby', None)
    check_in = None
    check_in_status = 'not_configured'
    check_in_countdown = 0

    if lobby:
        check_in_status = lobby.check_in_status
        check_in_countdown = lobby.check_in_countdown_seconds

        # Personal check-in record
        if is_team and registration and registration.team_id:
            check_in = CheckIn.objects.filter(
                tournament=tournament,
                team_id=registration.team_id,
                is_deleted=False,
            ).first()
        else:
            check_in = CheckIn.objects.filter(
                tournament=tournament,
                user=user,
                is_deleted=False,
            ).first()

    # ── Phase Countdown ─────────────────────────────────
    phase_event = _get_next_phase_event(tournament, lobby, now)

    # ── Roster / Squad ──────────────────────────────────
    squad = []
    squad_warnings = []
    igl_user_id = None
    if is_team and registration and registration.team_id:
        # Prefer lineup_snapshot from registration (frozen at registration time)
        lineup_snapshot = getattr(registration, 'lineup_snapshot', None) or []

        # Build lookup of active team members for fresh avatar/passport data
        members = TeamMembership.objects.filter(
            team_id=registration.team_id,
            status=TeamMembership.Status.ACTIVE,
        ).select_related('user', 'user__profile')
        member_by_user_id = {m.user_id: m for m in members}

        if lineup_snapshot and isinstance(lineup_snapshot, list) and len(lineup_snapshot) > 0:
            # ── Use lineup_snapshot as source of truth ──
            for entry in lineup_snapshot:
                user_id = entry.get('user_id')
                tm = member_by_user_id.get(user_id)
                user_obj = tm.user if tm else None

                # Fresh passport lookup
                has_passport = True
                game_id = entry.get('game_id', '')
                if user_obj and tournament.game:
                    try:
                        from apps.user_profile.services.game_passport_service import GamePassportService
                        passport = GamePassportService.get_passport(user_obj, tournament.game.slug)
                        if passport and passport.ign:
                            game_id = passport.ign
                            if passport.discriminator:
                                d = passport.discriminator
                                if not d.startswith('#') and not d.startswith('-'):
                                    d = f'#{d}'
                                game_id = f"{passport.ign}{d}"
                        else:
                            has_passport = False
                    except Exception:
                        has_passport = bool(game_id)
                elif not game_id:
                    has_passport = False

                is_igl = entry.get('is_igl', False)
                if is_igl:
                    igl_user_id = user_id

                member_data = {
                    'id': tm.id if tm else 0,
                    'user_id': user_id,
                    'username': entry.get('username', ''),
                    'display_name': entry.get('display_name', '') or entry.get('username', 'Unknown'),
                    'role': entry.get('role', 'PLAYER'),
                    'player_role': entry.get('player_role', ''),
                    'roster_slot': entry.get('roster_slot', 'STARTER'),
                    'is_captain_igl': is_igl,  # Unified: set from snapshot first, refined below
                    'game_id': game_id,
                    'has_passport': has_passport,
                    'avatar_url': _get_avatar_url(user_obj) if user_obj else entry.get('avatar', ''),
                }
                squad.append(member_data)

                if not has_passport and member_data['roster_slot'] in ('STARTER', 'SUBSTITUTE'):
                    squad_warnings.append(
                        f"{member_data['display_name']} is missing their Game ID"
                    )
        else:
            # ── Fallback: live TeamMembership (no snapshot) ──
            for m in members:
                has_passport = True
                game_id = ''
                try:
                    from apps.user_profile.services.game_passport_service import GamePassportService
                    passport = GamePassportService.get_passport(m.user, tournament.game.slug)
                    if passport and passport.ign:
                        game_id = passport.ign
                        if passport.discriminator:
                            d = passport.discriminator
                            if not d.startswith('#') and not d.startswith('-'):
                                d = f'#{d}'
                            game_id = f"{passport.ign}{d}"
                    else:
                        has_passport = False
                except Exception:
                    has_passport = False

                # Properly determine roster_slot from TeamMembership role
                if m.role in ('HEAD_COACH', 'COACH'):
                    effective_roster_slot = 'COACH'
                elif m.role == 'MANAGER':
                    effective_roster_slot = m.roster_slot or 'SUBSTITUTE'
                else:
                    effective_roster_slot = m.roster_slot or 'STARTER'

                member_data = {
                    'id': m.id,
                    'user_id': m.user_id,
                    'username': m.user.username,
                    'display_name': m.display_name or m.user.get_full_name() or m.user.username,
                    'role': m.role,
                    'player_role': m.player_role or '',
                    'roster_slot': effective_roster_slot,
                    'is_captain_igl': m.is_tournament_captain,  # Unified flag
                    'game_id': game_id,
                    'has_passport': has_passport,
                    'avatar_url': _get_avatar_url(m.user),
                }
                squad.append(member_data)

                if not has_passport and effective_roster_slot in ('STARTER', 'SUBSTITUTE'):
                    squad_warnings.append(
                        f"{member_data['display_name']} is missing their Game ID"
                    )

    # ── Game info ────────────────────────────────────────
    game_spec = None
    try:
        canonical = game_service.normalize_slug(tournament.game.slug)
        game_spec = game_service.get_game(canonical)
    except Exception:
        pass

    # ── Roster limits ────────────────────────────────────
    try:
        rl = game_service.get_roster_limits(tournament.game)
        min_roster = rl.get('min_team_size', 1)
        max_roster = rl.get('max_roster_size', 20)
    except Exception:
        min_roster = 1
        max_roster = 20

    starters = [s for s in squad if s['roster_slot'] in ('STARTER', None, '')]
    subs = [s for s in squad if s['roster_slot'] == 'SUBSTITUTE']
    coaches = [s for s in squad if s['roster_slot'] == 'COACH']

    # ── Unified Captain/IGL resolution ────────────────────
    # Captain and IGL are the SAME role on this platform.
    # Priority: 1) lineup_snapshot is_igl, 2) registration coordinator_role, 3) TeamMembership is_tournament_captain
    igl_info = None
    captain_igl_user_id = igl_user_id  # From lineup_snapshot is_igl

    # Fallback: detect from registration_data coordinator_role
    if not captain_igl_user_id and registration:
        reg_data = registration.registration_data or {}
        coord_role = reg_data.get('coordinator_role', '')
        if 'captain' in coord_role.lower() or 'igl' in coord_role.lower():
            coord_is_self = reg_data.get('coordinator_is_self', True)
            coord_member_id = reg_data.get('coordinator_member_id')
            if coord_is_self and user:
                captain_igl_user_id = user.id
            elif not coord_is_self and coord_member_id:
                coord_m = next((m for m in squad if m['id'] == coord_member_id), None)
                if coord_m:
                    captain_igl_user_id = coord_m['user_id']

    # Fallback: TeamMembership is_tournament_captain (only if nothing from registration)
    if not captain_igl_user_id:
        tc_member = next((m for m in squad if m.get('_tm_is_captain')), None)
        if tc_member:
            captain_igl_user_id = tc_member['user_id']

    # Apply unified flag: clear all first, then set the one true captain/IGL
    for m in squad:
        m['is_captain_igl'] = (m['user_id'] == captain_igl_user_id) if captain_igl_user_id else False

    if captain_igl_user_id:
        captain_member = next((m for m in squad if m['user_id'] == captain_igl_user_id), None)
        if captain_member:
            igl_info = {'name': captain_member['display_name'], 'user_id': captain_igl_user_id}

    squad_ready = len(starters) >= min_roster and not squad_warnings

    # ── Announcements ────────────────────────────────────
    announcements = []
    if lobby:
        ann_qs = LobbyAnnouncement.objects.filter(
            lobby=lobby,
            is_visible=True,
            is_deleted=False,
        ).select_related('posted_by').order_by('-is_pinned', '-created_at')[:20]
        for a in ann_qs:
            announcements.append({
                'id': a.id,
                'title': a.title,
                'message': a.message,
                'type': a.announcement_type,
                'is_pinned': a.is_pinned,
                'posted_by': a.posted_by.username if a.posted_by else 'Organizer',
                'created_at': a.created_at.isoformat(),
                'time_ago': _time_ago(a.created_at, now),
            })

    # ── Registration count ───────────────────────────────
    reg_count = Registration.objects.filter(
        tournament=tournament,
        is_deleted=False,
        status__in=[Registration.CONFIRMED, Registration.AUTO_APPROVED],
    ).count()

    # ── User status label ────────────────────────────────
    user_status = _registration_status_label(registration, check_in)

    hub_critical_locked = _critical_actions_locked(request.user, tournament, registration)
    hub_payment_verified = _is_registration_verified_for_critical_actions(registration) if registration else False
    hub_lock_reason = _critical_lock_reason(registration) if hub_critical_locked else ''

    # ── Status detail for modal ──────────────────────────
    status_detail = _build_status_detail(registration, check_in, tournament, now)

    # ── Team info ────────────────────────────────────────
    team = None
    team_name = ''
    team_tag = ''
    team_logo_url = ''
    team_detail_url = ''
    is_captain = False
    roster_locked = False
    if is_team and registration and registration.team_id:
        from apps.organizations.models import Team
        try:
            team = Team.objects.get(id=registration.team_id)
            team_name = team.name
            team_tag = team.tag or team.name[:3].upper()
            if hasattr(team, 'logo') and team.logo:
                team_logo_url = team.logo.url
            roster_locked = getattr(team, 'roster_locked', False)
            team_detail_url = f'/teams/{team.slug}/' if hasattr(team, 'slug') and team.slug else ''
        except Exception:
            pass

        # Check if current user is captain/IGL
        is_captain = any(m['user_id'] == user.id and m['is_captain_igl'] for m in squad)

    # ── Registration metadata (IGL / Coordinator) ─────
    registered_by_name = ''
    coordinator_info = {}
    if registration:
        # Who registered this entry
        if registration.user:
            registered_by_name = registration.user.get_full_name() or registration.user.username
        # Coordinator / IGL from registration_data
        reg_data = registration.registration_data or {}
        coord_role = reg_data.get('coordinator_role', '')
        coord_is_self = reg_data.get('coordinator_is_self', True)
        coord_member_id = reg_data.get('coordinator_member_id')
        if coord_role:
            coord_name = registered_by_name
            if not coord_is_self and coord_member_id:
                coord_member = next((m for m in squad if m['id'] == coord_member_id), None)
                if coord_member:
                    coord_name = coord_member['display_name']
            coordinator_info = {
                'role': coord_role,
                'name': coord_name,
            }

    platform_display_text = _platform_display_text(tournament)

    context = {
        'tournament': tournament,
        'registration': registration,
        'lobby': lobby,
        'is_team': is_team,

        # Status
        'user_status': user_status,
        'status_detail': status_detail,
        'check_in': check_in,
        'check_in_status': check_in_status,
        'check_in_countdown': check_in_countdown,
        'is_checked_in': check_in.is_checked_in if check_in else False,

        # Phase
        'phase_event': phase_event,

        # Squad
        'team': team,
        'team_name': team_name,
        'team_tag': team_tag,
        'team_logo_url': team_logo_url,
        'team_detail_url': team_detail_url,
        'is_captain': is_captain,
        'roster_locked': roster_locked,
        'registered_by_name': registered_by_name,
        'coordinator_info': coordinator_info,
        'igl_info': igl_info,
        'squad': squad,
        'starters': starters,
        'subs': subs,
        'coaches': coaches,
        'squad_warnings': squad_warnings,
        'squad_ready': squad_ready,
        'min_roster': min_roster,
        'max_roster': max_roster,

        # Announcements
        'announcements': announcements,

        # Tournament meta
        'reg_count': reg_count,
        'game_name': tournament.game.name if tournament.game else '',
        'game_spec': game_spec,
        'platform_display_text': platform_display_text,

        # Game theme (for per-game visual styling)
        'game_slug': tournament.game.slug if tournament.game else '',
        'game_primary_color': tournament.game.primary_color if tournament.game else '#00F0FF',
        'game_secondary_color': tournament.game.secondary_color if tournament.game else '#0C0C10',
        'game_accent_color': (tournament.game.accent_color or '#FFFFFF') if tournament.game else '#FFFFFF',
        'game_icon_url': tournament.game.icon.url if tournament.game and tournament.game.icon else '',
        'game_logo_url': tournament.game.logo.url if tournament.game and hasattr(tournament.game, 'logo') and tournament.game.logo else '',
        'game_card_url': tournament.game.card_image.url if tournament.game and hasattr(tournament.game, 'card_image') and tournament.game.card_image else '',

        # API endpoints (JS will poll these)
        'api_state_url': f'/tournaments/{tournament.slug}/hub/api/state/{query_suffix}',
        'api_checkin_url': f'/tournaments/{tournament.slug}/hub/api/check-in/{query_suffix}',
        'api_announcements_url': f'/tournaments/{tournament.slug}/hub/api/announcements/{query_suffix}',
        'api_roster_url': f'/tournaments/{tournament.slug}/hub/api/roster/{query_suffix}',
        'api_squad_url': f'/tournaments/{tournament.slug}/hub/api/squad/{query_suffix}',
        'api_resources_url': f'/tournaments/{tournament.slug}/hub/api/resources/{query_suffix}',
        'api_prize_claim_url': f'/tournaments/{tournament.slug}/hub/api/prize-claim/{query_suffix}',
        'api_bracket_url': f'/tournaments/{tournament.slug}/hub/api/bracket/{query_suffix}',
        'api_standings_url': f'/tournaments/{tournament.slug}/hub/api/standings/{query_suffix}',
        'api_matches_url': f'/tournaments/{tournament.slug}/hub/api/matches/{query_suffix}',
        'api_participants_url': f'/tournaments/{tournament.slug}/hub/api/participants/{query_suffix}',

        # Social / Contact
        'discord_url': tournament.social_discord or (lobby.discord_server_url if lobby else ''),
        'contact_email': tournament.contact_email or '',
        'contact_phone': getattr(tournament, 'contact_phone', '') or '',
        'organizer_name': tournament.organizer.get_full_name() or tournament.organizer.username if tournament.organizer else 'Organizer',
        'social_twitter': tournament.social_twitter or '',
        'social_instagram': tournament.social_instagram or '',
        'social_youtube': tournament.social_youtube or '',
        'social_website': tournament.social_website or '',
        'social_facebook': getattr(tournament, 'social_facebook', '') or '',
        'social_tiktok': getattr(tournament, 'social_tiktok', '') or '',
        'support_info': getattr(tournament, 'support_info', '') or '',

        # Streaming URLs
        'stream_twitch_url': getattr(tournament, 'stream_twitch_url', '') or '',
        'stream_youtube_url': getattr(tournament, 'stream_youtube_url', '') or '',

        # Support system API
        'api_support_url': f'/tournaments/{tournament.slug}/hub/api/support/{query_suffix}',

        # Registration/payment lock state
        'hub_critical_locked': hub_critical_locked,
        'hub_payment_verified': hub_payment_verified,
        'hub_lock_reason': hub_lock_reason,
    }
    return context


def _build_status_detail(registration, check_in, tournament, now):
    """Build detailed status info for the status modal."""
    if not registration:
        return {
            'raw_status': 'staff',
            'label': 'Staff / Organizer',
            'registered_at': '',
            'registered_at_display': '',
            'tournament_name': tournament.name,
            'steps': [{'label': 'Organizer Access', 'done': True, 'icon': 'shield-check'}],
            'steps_json': json.dumps([{'label': 'Organizer Access', 'done': True, 'icon': 'shield-check'}]),
        }

    status = registration.status
    detail = {
        'raw_status': status,
        'label': _registration_status_label(registration, check_in),
        'registered_at': registration.created_at.isoformat() if registration.created_at else '',
        'registered_at_display': registration.created_at.strftime('%b %d, %Y at %I:%M %p') if registration.created_at else '',
        'tournament_name': tournament.name,
        'steps': [],
    }

    # Build status timeline steps
    steps = [
        {
            'label': 'Registration Submitted',
            'done': True,
            'icon': 'check-circle',
        },
    ]

    if status in ('confirmed', 'auto_approved'):
        steps.append({'label': 'Registration Confirmed', 'done': True, 'icon': 'check-circle'})
    elif status == 'pending':
        steps.append({'label': 'Awaiting Organizer Approval', 'done': False, 'icon': 'clock', 'active': True})
    elif status == 'payment_submitted':
        steps.append({'label': 'Payment Under Review', 'done': False, 'icon': 'credit-card', 'active': True})
    elif status == 'needs_review':
        steps.append({'label': 'Under Manual Review', 'done': False, 'icon': 'eye', 'active': True})

    # Check-in step
    if check_in and check_in.is_checked_in:
        steps.append({'label': 'Checked In', 'done': True, 'icon': 'check-circle'})
    elif check_in and check_in.is_forfeited:
        steps.append({'label': 'Eliminated', 'done': True, 'icon': 'x-circle', 'error': True})
    else:
        lobby = getattr(tournament, 'lobby', None)
        if lobby and lobby.check_in_opens_at:
            if now < lobby.check_in_opens_at:
                steps.append({'label': 'Check-In Not Yet Open', 'done': False, 'icon': 'clock'})
            elif lobby.check_in_closes_at and now < lobby.check_in_closes_at:
                steps.append({'label': 'Check-In Open — Action Required', 'done': False, 'icon': 'alert-circle', 'active': True})
            else:
                steps.append({'label': 'Check-In Window Closed', 'done': False, 'icon': 'lock'})
        else:
            steps.append({'label': 'Check-In', 'done': False, 'icon': 'clock'})

    # Tournament start
    if tournament.status == 'live':
        steps.append({'label': 'Tournament In Progress', 'done': True, 'icon': 'zap', 'active': True})
    elif tournament.status == 'completed':
        steps.append({'label': 'Tournament Completed', 'done': True, 'icon': 'flag'})
    else:
        steps.append({'label': 'Tournament Starts', 'done': False, 'icon': 'play'})

    detail['steps'] = steps
    detail['steps_json'] = json.dumps(steps)
    return detail


def _get_next_phase_event(tournament, lobby, now):
    """Determine the next critical event for the countdown."""
    events = []

    if tournament.registration_start and now < tournament.registration_start:
        events.append({
            'label': 'Registration Opens',
            'target': tournament.registration_start.isoformat(),
            '_target_dt': tournament.registration_start,
            'type': 'info',
        })

    if tournament.registration_end and now < tournament.registration_end:
        events.append({
            'label': 'Registration Closes',
            'target': tournament.registration_end.isoformat(),
            '_target_dt': tournament.registration_end,
            'type': 'warning',
        })

    if lobby and lobby.check_in_opens_at and now < lobby.check_in_opens_at:
        events.append({
            'label': 'Check-In Opens',
            'target': lobby.check_in_opens_at.isoformat(),
            '_target_dt': lobby.check_in_opens_at,
            'type': 'info',
        })

    if lobby and lobby.check_in_closes_at and now < lobby.check_in_closes_at:
        events.append({
            'label': 'Check-In Closes',
            'target': lobby.check_in_closes_at.isoformat(),
            '_target_dt': lobby.check_in_closes_at,
            'type': 'danger',
        })

    if tournament.tournament_start and now < tournament.tournament_start:
        events.append({
            'label': 'Tournament Starts',
            'target': tournament.tournament_start.isoformat(),
            '_target_dt': tournament.tournament_start,
            'type': 'info',
        })

    # Return earliest upcoming event
    if events:
        events.sort(key=lambda e: e['_target_dt'])
        event = events[0]
        event.pop('_target_dt', None)
        return event
    return {
        'label': 'Tournament In Progress',
        'target': None,
        'type': 'success',
    }


def _registration_status_label(registration, check_in):
    """Human-readable status for the top bar."""
    if check_in and check_in.is_forfeited:
        return 'Eliminated'
    if check_in and check_in.is_checked_in:
        return 'Checked In'
    if not registration:
        return 'Staff / Organizer'
    status_map = {
        'confirmed': 'Registered',
        'auto_approved': 'Registered',
        'pending': 'Pending Approval',
        'payment_submitted': 'Payment Under Review',
        'needs_review': 'Under Review',
    }
    return status_map.get(registration.status, 'Registered')


def _platform_display_text(tournament):
    """Return platform labels using same normalization as smart success view."""
    platform_value = getattr(tournament, 'platform', None)
    if not platform_value:
        return ''

    platform_choice_map = {
        str(key).lower(): str(label)
        for key, label in getattr(Tournament, 'PLATFORM_CHOICES', [])
    }

    parsed_platforms = None
    if isinstance(platform_value, list):
        parsed_platforms = platform_value
    else:
        raw_platform = str(platform_value).strip()
        if raw_platform.startswith('[') and raw_platform.endswith(']'):
            try:
                maybe_list = json.loads(raw_platform)
                if isinstance(maybe_list, list):
                    parsed_platforms = maybe_list
            except (TypeError, ValueError, json.JSONDecodeError):
                parsed_platforms = None
        if parsed_platforms is None:
            if ',' in raw_platform:
                parsed_platforms = [item.strip() for item in raw_platform.split(',') if item and item.strip()]
            else:
                parsed_platforms = [raw_platform]

    labels = []
    for token in parsed_platforms or []:
        key = str(token).strip().lower()
        if not key:
            continue
        label = platform_choice_map.get(key)
        if not label:
            label = str(token).replace('_', ' ').strip().title()
        if label not in labels:
            labels.append(label)

    return ', '.join(labels)


def _time_ago(dt, now=None):
    """Return e.g. '5 min ago', '2 hours ago'."""
    now = now or timezone.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'just now'
    if seconds < 3600:
        m = int(seconds // 60)
        return f'{m} min ago'
    if seconds < 86400:
        h = int(seconds // 3600)
        return f'{h} hour{"s" if h != 1 else ""} ago'
    d = int(seconds // 86400)
    return f'{d} day{"s" if d != 1 else ""} ago'


def _get_avatar_url(user):
    """Return user avatar URL or fallback."""
    try:
        if user.profile and user.profile.avatar:
            return user.profile.avatar.url
    except Exception:
        pass
    return f"https://ui-avatars.com/api/?name={user.username[:2]}&background=0A0A0E&color=fff&size=64"


def _json_response(payload, status=200, cache_control=None):
    resp = JsonResponse(payload, status=status)
    if cache_control:
        resp['Cache-Control'] = cache_control
    return resp


# ────────────────────────────────────────────────────────────
# Views
# ────────────────────────────────────────────────────────────

class TournamentHubView(LoginRequiredMixin, View):
    """
    The Hub — participant's unified Mission Control.

    GET renders the SPA shell; all subsequent data loads happen via
    the JSON API endpoints below.
    """
    template_name = 'tournaments/hub/hub.html'

    def get(self, request, slug):
        tournament = get_object_or_404(
            Tournament.objects.select_related('game'),
            slug=slug,
        )

        # Staff / organizer bypass — they don't need a registration
        is_staff_or_organizer = _is_tournament_staff_or_organizer(request.user, tournament)

        registration = _get_user_registration(request.user, tournament)
        if not registration and not is_staff_or_organizer:
            messages.warning(
                request,
                "You must be registered for this tournament to access The Hub."
            )
            return redirect('tournaments:detail', slug=slug)

        view_mode = _resolve_hub_view_mode(request, tournament, registration)
        context = _build_hub_context(
            request,
            tournament,
            registration,
            query_suffix=view_mode['query_suffix'],
        )
        context.update(view_mode)
        context['hub_view_as_staff_url'] = request.path
        context['hub_view_as_participant_url'] = f"{request.path}?view_as=participant"
        return render(request, self.template_name, context)


class HubStateAPIView(LoginRequiredMixin, View):
    """
    JSON endpoint: returns current hub state for real-time polling.
    Called every 15-30s by the JS engine.
    """

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        now = timezone.now()
        lobby = getattr(tournament, 'lobby', None)

        # Check-in state
        check_in = None
        if lobby:
            from apps.organizations.models import TeamMembership
            if tournament.participation_type == 'team' and registration and registration.team_id:
                check_in = CheckIn.objects.filter(
                    tournament=tournament,
                    team_id=registration.team_id,
                    is_deleted=False,
                ).first()
            elif registration:
                check_in = CheckIn.objects.filter(
                    tournament=tournament,
                    user=request.user,
                    is_deleted=False,
                ).first()

        phase_event = _get_next_phase_event(tournament, lobby, now)

        data = {
            'tournament_status': tournament.status,
            'user_status': _registration_status_label(registration, check_in),
            'phase_event': phase_event,
            'check_in': {
                'status': lobby.check_in_status if lobby else 'not_configured',
                'is_open': lobby.is_check_in_open if lobby else False,
                'is_checked_in': check_in.is_checked_in if check_in else False,
                'countdown': lobby.check_in_countdown_seconds if lobby else 0,
            },
            'reg_count': Registration.objects.filter(
                tournament=tournament,
                is_deleted=False,
                status__in=[Registration.CONFIRMED, Registration.AUTO_APPROVED],
            ).count(),
            'server_time': now.isoformat(),
        }
        return _json_response(data, cache_control='no-store')


class HubCheckInAPIView(LoginRequiredMixin, View):
    """POST: perform check-in for the current user/team."""

    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return JsonResponse({'error': 'not_registered'}, status=403)

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        try:
            team_id = None
            if tournament.participation_type == 'team' and registration and registration.team_id:
                team_id = registration.team_id

            check_in = LobbyService.perform_check_in(
                tournament_id=tournament.id,
                user_id=request.user.id,
                team_id=team_id,
            )
            return JsonResponse({
                'success': True,
                'checked_in_at': check_in.checked_in_at.isoformat() if check_in.checked_in_at else None,
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class HubAnnouncementsAPIView(LoginRequiredMixin, View):
    """GET: poll announcements since a given timestamp."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        lobby = getattr(tournament, 'lobby', None)
        if not lobby:
            return _json_response({'announcements': []}, cache_control='private, max-age=15')

        now = timezone.now()
        ann_qs = LobbyAnnouncement.objects.filter(
            lobby=lobby,
            is_visible=True,
            is_deleted=False,
        ).select_related('posted_by').order_by('-is_pinned', '-created_at')[:20]

        data = []
        for a in ann_qs:
            data.append({
                'id': a.id,
                'title': a.title,
                'message': a.message,
                'type': a.announcement_type,
                'is_pinned': a.is_pinned,
                'posted_by': a.posted_by.username if a.posted_by else 'Organizer',
                'created_at': a.created_at.isoformat(),
                'time_ago': _time_ago(a.created_at, now),
            })
        return _json_response({'announcements': data}, cache_control='private, max-age=15')


class HubRosterAPIView(LoginRequiredMixin, View):
    """GET: full tournament roster with check-in status."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return JsonResponse({'error': 'not_registered'}, status=403)

        try:
            roster_data = LobbyService.get_roster(tournament.id)
            return JsonResponse(roster_data)
        except Exception as e:
            logger.error(f"Error fetching roster for {slug}: {e}", exc_info=True)
            return JsonResponse({'error': 'Failed to load roster'}, status=500)


class HubSquadAPIView(LoginRequiredMixin, View):
    """
    POST: swap a team member's roster slot (STARTER <-> SUBSTITUTE).
    Only team captains can perform swaps, and only when roster isn't locked.
    """

    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return JsonResponse({'error': 'not_registered'}, status=403)

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        if not registration or tournament.participation_type != 'team' or not registration.team_id:
            return JsonResponse({'error': 'Not a team tournament'}, status=400)

        from apps.organizations.models import Team, TeamMembership
        from apps.games.services import game_service

        # Verify captain
        try:
            captain_membership = TeamMembership.objects.get(
                team_id=registration.team_id,
                user=request.user,
                status=TeamMembership.Status.ACTIVE,
                is_tournament_captain=True,
            )
        except TeamMembership.DoesNotExist:
            return JsonResponse({'error': 'Only the team captain can modify the roster'}, status=403)

        # Check roster lock
        try:
            team = Team.objects.get(id=registration.team_id)
            if getattr(team, 'roster_locked', False):
                return JsonResponse({'error': 'Roster is locked. Changes are not allowed.'}, status=400)
        except Team.DoesNotExist:
            return JsonResponse({'error': 'Team not found'}, status=404)

        # Parse request
        try:
            body = json.loads(request.body)
            membership_id = body.get('membership_id')
            new_slot = body.get('new_slot', '').upper()
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if new_slot not in ('STARTER', 'SUBSTITUTE'):
            return JsonResponse({'error': 'Invalid slot. Must be STARTER or SUBSTITUTE.'}, status=400)

        # Get the membership
        try:
            membership = TeamMembership.objects.get(
                id=membership_id,
                team_id=registration.team_id,
                status=TeamMembership.Status.ACTIVE,
            )
        except TeamMembership.DoesNotExist:
            return JsonResponse({'error': 'Team member not found'}, status=404)

        # Don't allow moving the captain
        if membership.is_tournament_captain:
            return JsonResponse({'error': 'Cannot change the captain\'s roster slot'}, status=400)

        # Validate roster limits
        if new_slot == 'STARTER':
            try:
                rl = game_service.get_roster_limits(tournament.game)
                max_starters = rl.get('max_team_size', 99)
                current_starters = TeamMembership.objects.filter(
                    team_id=registration.team_id,
                    status=TeamMembership.Status.ACTIVE,
                    roster_slot='STARTER',
                ).count()
                if current_starters >= max_starters:
                    return JsonResponse({
                        'error': f'Maximum starters ({max_starters}) already reached'
                    }, status=400)
            except Exception:
                pass

        # Perform the swap
        old_slot = membership.roster_slot
        membership.roster_slot = new_slot
        membership.save(update_fields=['roster_slot'])

        logger.info(
            "Hub squad swap: user=%s team=%d member=%d %s -> %s (tournament=%s)",
            request.user.username, registration.team_id, membership_id, old_slot, new_slot, slug
        )

        return JsonResponse({
            'success': True,
            'membership_id': membership_id,
            'old_slot': old_slot,
            'new_slot': new_slot,
            'display_name': membership.display_name or membership.user.get_full_name() or membership.user.username,
        })


# ────────────────────────────────────────────────────────────
# Module 3: Resources Hub API
# ────────────────────────────────────────────────────────────

class HubResourcesAPIView(LoginRequiredMixin, View):
    """
    GET: Returns tournament resources — rules, social links,
    sponsors (tiered), and contact info for the Hub Resources tab.
    """

    def get(self, request, slug):
        tournament = get_object_or_404(
            Tournament.objects.select_related('game'),
            slug=slug,
        )
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        # ── Rules ──────────────────────────────────────
        rules = {
            'text': tournament.rules_text or '',
            'pdf_url': tournament.rules_pdf.url if tournament.rules_pdf else '',
            'terms': tournament.terms_and_conditions or '',
        }

        # ── Social Links ──────────────────────────────
        social_links = []
        _social_fields = [
            ('discord', 'social_discord', 'Discord'),
            ('twitter', 'social_twitter', 'Twitter / X'),
            ('instagram', 'social_instagram', 'Instagram'),
            ('youtube', 'social_youtube', 'YouTube'),
            ('facebook', 'social_facebook', 'Facebook'),
            ('tiktok', 'social_tiktok', 'TikTok'),
            ('website', 'social_website', 'Website'),
            ('twitch', 'stream_twitch_url', 'Twitch'),
            ('youtube_stream', 'stream_youtube_url', 'YouTube Stream'),
        ]
        for key, field, label in _social_fields:
            url = getattr(tournament, field, '') or ''
            if url:
                social_links.append({'key': key, 'label': label, 'url': url})

        # ── Contact ────────────────────────────────────
        contact_email = getattr(tournament, 'contact_email', '') or ''
        contact_phone = getattr(tournament, 'contact_phone', '') or ''
        support_info = getattr(tournament, 'support_info', '') or ''

        # ── Sponsors (tiered) ──────────────────────────
        sponsors_qs = TournamentSponsor.objects.filter(
            tournament=tournament,
            is_active=True,
        ).order_by('tier', 'display_order', 'name')

        sponsors = []
        for s in sponsors_qs:
            sponsors.append({
                'id': s.id,
                'name': s.name,
                'tier': s.tier,
                'tier_display': s.get_tier_display(),
                'logo_url': s.logo.url if s.logo else '',
                'banner_url': s.banner_image.url if s.banner_image else '',
                'website_url': s.website_url or '',
                'description': s.description or '',
            })

        return _json_response({
            'rules': rules,
            'social_links': social_links,
            'contact_email': contact_email,
            'contact_phone': contact_phone,
            'support_info': support_info,
            'sponsors': sponsors,
            'support_url': f'/support/?tournament={tournament.slug}',
            'tournament_page_url': f'/tournaments/{tournament.slug}/',
            'tournament_info': {
                'platform': tournament.get_platform_display() if tournament.platform else '',
                'mode': tournament.get_mode_display() if tournament.mode else '',
                'venue_name': tournament.venue_name or '',
                'refund_policy': tournament.get_refund_policy_display() if tournament.refund_policy else '',
                'refund_policy_text': tournament.refund_policy_text or '',
                'promo_video_url': tournament.promo_video_url or '',
                'description': tournament.description or '',
            },
        }, cache_control='private, max-age=300')


# ────────────────────────────────────────────────────────────
# Module 5: Bounty Board (Prize Claims) API
# ────────────────────────────────────────────────────────────

class HubPrizeClaimAPIView(LoginRequiredMixin, View):
    """
    GET:  Returns the user's prize transactions + claim status for this tournament.
    POST: Creates a PrizeClaim for an unclaimed PrizeTransaction.
    """

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        # ── Prize Pool Info ────────────────────────────
        prize_pool = {
            'total': str(tournament.prize_pool or 0),
            'currency': tournament.prize_currency or 'BDT',
            'distribution': tournament.prize_distribution or {},
            'deltacoin': tournament.prize_deltacoin or 0,
        }

        # ── User's prize transactions ─────────────────
        user_prizes = PrizeTransaction.objects.filter(
            tournament=tournament,
            participant=registration,
        ).select_related('claim').order_by('-created_at')

        prizes = []
        for pt in user_prizes:
            claim = getattr(pt, 'claim', None)
            prizes.append({
                'id': pt.id,
                'placement': pt.placement,
                'placement_display': pt.get_placement_display(),
                'amount': str(pt.amount),
                'status': pt.status,
                'claimed': claim is not None,
                'claim_status': claim.status if claim else None,
                'claim_payout_method': claim.payout_method if claim else None,
                'paid_at': claim.paid_at.isoformat() if claim and claim.paid_at else None,
            })

        # ── Tournament prizes overview (all placements) ──
        all_prizes = PrizeTransaction.objects.filter(
            tournament=tournament,
        ).values('placement').annotate(
            total=models.Sum('amount'),
            count=models.Count('id'),
        ).order_by('placement')

        overview = []
        for row in all_prizes:
            overview.append({
                'placement': row['placement'],
                'total': str(row['total'] or 0),
                'count': row['count'],
            })

        return _json_response({
            'prize_pool': prize_pool,
            'your_prizes': prizes,
            'overview': overview,
            'tournament_status': tournament.status,
        }, cache_control='no-store')

    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return JsonResponse({'error': 'not_registered'}, status=403)

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        try:
            body = json.loads(request.body)
            transaction_id = body.get('transaction_id')
            payout_method = body.get('payout_method', 'deltacoin')
            payout_destination = body.get('payout_destination', '')
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not transaction_id:
            return JsonResponse({'error': 'transaction_id is required'}, status=400)

        # Validate payout method
        valid_methods = [c[0] for c in PrizeClaim.PAYOUT_METHOD_CHOICES]
        if payout_method not in valid_methods:
            return JsonResponse({
                'error': f'Invalid payout method. Must be one of: {", ".join(valid_methods)}'
            }, status=400)

        # Verify the PrizeTransaction belongs to this user and tournament
        try:
            pt = PrizeTransaction.objects.get(
                id=transaction_id,
                tournament=tournament,
                participant=registration,
            )
        except PrizeTransaction.DoesNotExist:
            return JsonResponse({'error': 'Prize transaction not found'}, status=404)

        # Check not already claimed
        if hasattr(pt, 'claim'):
            return JsonResponse({
                'error': 'This prize has already been claimed',
                'claim_status': pt.claim.status,
            }, status=409)

        # Check transaction is in a claimable state
        if pt.status not in ('pending', 'completed'):
            return JsonResponse({
                'error': f'Prize transaction is {pt.status} and cannot be claimed'
            }, status=400)

        # Create claim
        claim = PrizeClaim.objects.create(
            prize_transaction=pt,
            claimed_by=request.user,
            payout_method=payout_method,
            payout_destination=payout_destination,
        )

        logger.info(
            "Hub prize claim: user=%s tournament=%s tx=%d method=%s",
            request.user.username, slug, transaction_id, payout_method,
        )

        return JsonResponse({
            'success': True,
            'claim_id': claim.id,
            'status': claim.status,
            'claimed_at': claim.claimed_at.isoformat() if claim.claimed_at else None,
        }, status=201)


# ────────────────────────────────────────────────────────────
# Module 6: Bracket API
# ────────────────────────────────────────────────────────────

class HubBracketAPIView(LoginRequiredMixin, View):
    """
    GET: Returns bracket structure and match data for bracket visualization.

    Endpoint: /tournaments/<slug>/hub/api/bracket/

    Purpose:
        Provides the full bracket tree for the Hub bracket tab, including
        round metadata and match details (participants, scores, state).

    Authentication:
        Requires login. User must be a registered participant or tournament
        staff/organizer.

    Response Schema:
        When bracket is NOT generated:
            {"generated": false, "format": str, "format_display": str}

        When bracket IS generated:
            {
                "generated": true,
                "format": str,              # e.g. "double_elimination"
                "format_display": str,      # e.g. "Double Elimination"
                "total_rounds": int,
                "total_matches": int,
                "is_finalized": bool,
                "rounds": [
                    {
                        "round_number": int,
                        "round_name": str,   # e.g. "UB Round 1", "LB Round 3", "Grand Final"
                        "matches": [
                            {
                                "id": int,
                                "match_number": int,
                                "state": str,        # scheduled|live|completed|forfeit|...
                                "state_display": str,
                                "participant1": {"id": int|null, "name": str, "score": int, "is_winner": bool},
                                "participant2": {"id": int|null, "name": str, "score": int, "is_winner": bool},
                                "scheduled_at": str|null  # ISO 8601
                            }
                        ]
                    }
                ]
            }

    Bracket vs Group Behavior:
        This view only returns bracket-based data. For group-stage standings,
        use HubStandingsAPIView which handles both group and bracket-derived
        standings.

    Double Elimination:
        For double_elimination format, round_name includes prefixes
        ("UB Round 1", "LB Round 2", "Grand Final") so the frontend can
        split rounds into Upper Bracket / Lower Bracket / Grand Final sections.
    """

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        try:
            bracket = Bracket.objects.get(tournament=tournament)
        except Bracket.DoesNotExist:
            return _json_response({
                'generated': False,
                'format': tournament.format,
                'format_display': tournament.get_format_display(),
            }, cache_control='private, max-age=15')

        # Build rounds data from matches
        matches = Match.objects.filter(
            tournament=tournament,
            bracket=bracket,
            is_deleted=False,
        ).order_by('round_number', 'match_number')

        rounds = {}
        for m in matches:
            rn = m.round_number
            if rn not in rounds:
                rounds[rn] = {
                    'round_number': rn,
                    'round_name': bracket.get_round_name(rn),
                    'matches': [],
                }
            rounds[rn]['matches'].append({
                'id': m.id,
                'match_number': m.match_number,
                'state': m.state,
                'state_display': m.get_state_display(),
                'participant1': {
                    'id': m.participant1_id,
                    'name': m.participant1_name or 'TBD',
                    'score': m.participant1_score,
                    'is_winner': m.winner_id == m.participant1_id if m.winner_id else False,
                },
                'participant2': {
                    'id': m.participant2_id,
                    'name': m.participant2_name or 'TBD',
                    'score': m.participant2_score,
                    'is_winner': m.winner_id == m.participant2_id if m.winner_id else False,
                },
                'scheduled_at': m.scheduled_time.isoformat() if m.scheduled_time else None,
            })

        return _json_response({
            'generated': True,
            'format': bracket.format,
            'format_display': bracket.get_format_display(),
            'total_rounds': bracket.total_rounds,
            'total_matches': bracket.total_matches,
            'is_finalized': bracket.is_finalized,
            'rounds': list(rounds.values()),
        }, cache_control='private, max-age=15')


# ────────────────────────────────────────────────────────────
# Module 7: Standings API
# ────────────────────────────────────────────────────────────

class HubStandingsAPIView(LoginRequiredMixin, View):
    """
    GET: Returns tournament standings for the Hub standings tab.

    Endpoint: /tournaments/<slug>/hub/api/standings/

    Purpose:
        Provides either group-stage standings (if groups exist) or
        bracket-derived aggregate standings (W/L/map diff/round diff)
        computed from completed match results.

    Authentication:
        Requires login. User must be a registered participant or tournament
        staff/organizer.

    Response Schema:
        When no standings exist:
            {"has_standings": false, "groups": []}

        Group-stage standings:
            {
                "has_standings": true,
                "standings_type": "groups",
                "groups": [
                    {
                        "name": str,
                        "standings": [
                            {
                                "rank": int,
                                "name": str,
                                "is_you": bool,
                                "matches_played": int,
                                "won": int, "drawn": int, "lost": int,
                                "points": str,
                                "goal_difference": int,
                                "rounds_won": int, "rounds_lost": int
                            }
                        ]
                    }
                ]
            }

        Bracket-derived standings:
            {
                "has_standings": true,
                "standings_type": "bracket",
                "rows": [
                    {
                        "rank": int,
                        "participant_id": int,
                        "name": str,
                        "is_you": bool,
                        "wins": int, "losses": int,
                        "points": int,
                        "map_diff": int, "map_wins": int, "map_losses": int,
                        "round_diff": int, "round_wins": int, "round_losses": int
                    }
                ]
            }

    Bracket vs Group Behavior:
        - If Group objects exist for the tournament, returns group standings
          with per-group data from GroupStanding model.
        - If no groups exist, falls back to aggregating W/L/map/round stats
          from all completed bracket matches. Sorted by wins desc, then
          map_diff desc, then round_diff desc.
    """

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        is_team = tournament.participation_type == 'team'
        groups = Group.objects.filter(
            tournament=tournament,
        ).prefetch_related('standings').order_by('name')

        if groups.exists():
            groups_data = []
            for group in groups:
                standings = GroupStanding.objects.filter(
                    group=group,
                ).order_by('rank', '-points', '-goal_difference')

                rows = []
                for s in standings:
                    name = ''
                    is_you = False
                    if is_team and s.team_id:
                        from apps.organizations.models import Team
                        try:
                            t = Team.objects.get(id=s.team_id)
                            name = t.name
                        except Team.DoesNotExist:
                            name = f'Team #{s.team_id}'
                        is_you = registration and s.team_id == registration.team_id
                    elif s.user_id:
                        name = s.user.get_full_name() or s.user.username if s.user else f'User #{s.user_id}'
                        is_you = s.user_id == request.user.id

                    rows.append({
                        'rank': s.rank,
                        'name': name,
                        'is_you': is_you,
                        'matches_played': s.matches_played,
                        'won': s.matches_won,
                        'drawn': s.matches_drawn,
                        'lost': s.matches_lost,
                        'points': str(s.points),
                        'goal_difference': s.goal_difference,
                        'rounds_won': s.rounds_won,
                        'rounds_lost': s.rounds_lost,
                    })

                groups_data.append({
                    'name': group.name,
                    'standings': rows,
                })

            return _json_response({
                'has_standings': True,
                'standings_type': 'groups',
                'groups': groups_data,
            }, cache_control='private, max-age=15')

        # ── Fallback: derive standings from bracket match results ──
        matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
            state__in=['completed', 'forfeit'],
        )
        if not matches.exists():
            return _json_response({'has_standings': False, 'groups': []}, cache_control='private, max-age=15')

        # Aggregate W/L per participant
        from collections import defaultdict
        stats = defaultdict(lambda: {
            'wins': 0, 'losses': 0, 'map_wins': 0, 'map_losses': 0,
            'round_wins': 0, 'round_losses': 0, 'name': 'TBD',
        })

        for m in matches:
            for pid, opp_pid, own_score, opp_score, pname in [
                (m.participant1_id, m.participant2_id, m.participant1_score, m.participant2_score, m.participant1_name),
                (m.participant2_id, m.participant1_id, m.participant2_score, m.participant1_score, m.participant2_name),
            ]:
                if not pid:
                    continue
                entry = stats[pid]
                if pname:
                    entry['name'] = pname
                if m.winner_id == pid:
                    entry['wins'] += 1
                else:
                    entry['losses'] += 1
                entry['map_wins'] += own_score or 0
                entry['map_losses'] += opp_score or 0

                # Extract round diff from game_scores JSON
                raw_gs = getattr(m, 'game_scores', None)
                if isinstance(raw_gs, str):
                    try:
                        raw_gs = json.loads(raw_gs)
                    except (ValueError, TypeError):
                        raw_gs = []
                if isinstance(raw_gs, dict) and 'maps' in raw_gs:
                    raw_gs = raw_gs.get('maps', [])
                if not isinstance(raw_gs, list):
                    raw_gs = []
                for g in raw_gs:
                    is_p1 = (pid == m.participant1_id)
                    rw = g.get('team1_rounds', 0) if is_p1 else g.get('team2_rounds', 0)
                    rl = g.get('team2_rounds', 0) if is_p1 else g.get('team1_rounds', 0)
                    entry['round_wins'] += rw or 0
                    entry['round_losses'] += rl or 0

        participant_id = None
        if registration:
            participant_id = registration.team_id if is_team else request.user.id

        rows = []
        for pid, s in stats.items():
            rows.append({
                'participant_id': pid,
                'name': s['name'],
                'is_you': pid == participant_id if participant_id else False,
                'wins': s['wins'],
                'losses': s['losses'],
                'points': s['wins'] * 3,
                'map_diff': s['map_wins'] - s['map_losses'],
                'round_diff': s['round_wins'] - s['round_losses'],
                'map_wins': s['map_wins'],
                'map_losses': s['map_losses'],
                'round_wins': s['round_wins'],
                'round_losses': s['round_losses'],
            })

        rows.sort(key=lambda r: (-r['wins'], -r['map_diff'], -r['round_diff']))
        for i, r in enumerate(rows, 1):
            r['rank'] = i

        return _json_response({
            'has_standings': True,
            'standings_type': 'bracket',
            'rows': rows,
        }, cache_control='private, max-age=15')


# ────────────────────────────────────────────────────────────
# Module 8: Matches API
# ────────────────────────────────────────────────────────────

class HubMatchesAPIView(LoginRequiredMixin, View):
    """
    GET: Returns matches relevant to the current user/team.

    Endpoint: /tournaments/<slug>/hub/api/matches/

    Purpose:
        Provides the user's active matches (check-in, ready, live,
        pending_result) and completed match history with per-map
        game_scores for the Hub matches tab.

    Authentication:
        Requires login. User must be a registered participant or tournament
        staff/organizer. Staff/organizers see ALL matches.

    Response Schema:
        {
            "active_matches": [
                {
                    "id": int,
                    "round_number": int,
                    "round_name": str,
                    "match_number": int,
                    "state": str,
                    "state_display": str,
                    "p1_name": str, "p2_name": str,
                    "opponent_name": str,
                    "your_score": int, "opponent_score": int,
                    "p1_score": int, "p2_score": int,
                    "is_winner": bool|null,
                    "is_staff_view": bool,
                    "lobby_info": dict,
                    "scheduled_at": str|null,
                    "game_scores": [{"map_name": str, "p1_score": int, "p2_score": int, "winner_side": str|null}],
                    "best_of": int
                }
            ],
            "match_history": [...],  # same schema, completed/forfeit matches
            "total": int
        }

    game_scores Format:
        The backend normalizes game_scores to a flat list of dicts.
        - Array format:  [{game, p1, p2, winner_slot}]  → passed through
        - Dict-with-maps: {maps: [{map_name, team1_rounds, team2_rounds}], best_of}
          → normalized to [{map_name, p1_score, p2_score, winner_side}]

    Bracket vs Group Behavior:
        This view returns matches regardless of bracket/group format.
        Round names are resolved from the Bracket model if available.
    """

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        is_team = tournament.participation_type == 'team'
        view_mode = _resolve_hub_view_mode(request, tournament, registration)
        is_staff_view = view_mode['is_staff_view']
        participant_id = (registration.team_id if registration else None) if is_team else request.user.id

        # Get user's matches (staff/organizers see ALL matches)
        user_matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
        )
        if not is_staff_view:
            user_matches = user_matches.filter(
                models.Q(participant1_id=participant_id) | models.Q(participant2_id=participant_id)
            )
        user_matches = user_matches.order_by('round_number', 'match_number')

        # Pre-fetch bracket once for round name lookups (avoid N+1)
        bracket = None
        try:
            bracket = Bracket.objects.get(tournament=tournament)
        except Bracket.DoesNotExist:
            pass

        active = []
        history = []
        for m in user_matches:
            if is_staff_view:
                # Staff/organizer sees both sides — no "your" vs "opponent"
                is_p1 = True  # default perspective: p1 on left
                opponent_name = m.participant2_name
                your_score = m.participant1_score
                opponent_score = m.participant2_score
                is_winner = None
            else:
                is_p1 = m.participant1_id == participant_id
                opponent_name = m.participant2_name if is_p1 else m.participant1_name
                your_score = m.participant1_score if is_p1 else m.participant2_score
                opponent_score = m.participant2_score if is_p1 else m.participant1_score
                is_winner = m.winner_id == participant_id if m.winner_id else None

            if bracket:
                round_name = bracket.get_round_name(m.round_number)
            else:
                round_name = f'Round {m.round_number}'

            # Normalize game_scores for JS consumption
            raw_gs = getattr(m, 'game_scores', None)
            if isinstance(raw_gs, str):
                try:
                    raw_gs = json.loads(raw_gs)
                except (json.JSONDecodeError, TypeError):
                    raw_gs = []
            if isinstance(raw_gs, dict) and 'maps' in raw_gs:
                best_of = raw_gs.get('best_of', 3)
                raw_gs = [
                    {
                        'map_name': mp.get('map_name', ''),
                        'p1_score': mp.get('team1_rounds', 0),
                        'p2_score': mp.get('team2_rounds', 0),
                        'winner_side': mp.get('winner_side', None),
                    }
                    for mp in raw_gs.get('maps', [])
                ]
            else:
                best_of = 3
            if not isinstance(raw_gs, list):
                raw_gs = []

            match_data = {
                'id': m.id,
                'round_number': m.round_number,
                'round_name': round_name,
                'match_number': m.match_number,
                'state': m.state,
                'state_display': m.get_state_display(),
                'p1_name': m.participant1_name or 'TBD',
                'p2_name': m.participant2_name or 'TBD',
                'opponent_name': opponent_name or 'TBD',
                'your_score': your_score,
                'opponent_score': opponent_score,
                'p1_score': m.participant1_score,
                'p2_score': m.participant2_score,
                'is_winner': is_winner,
                'winner_name': m.winner_name if hasattr(m, 'winner_name') else None,
                'is_staff_view': is_staff_view,
                'lobby_info': m.lobby_info or {},
                'scheduled_at': m.scheduled_time.isoformat() if m.scheduled_time else None,
                'game_scores': raw_gs,
                'best_of': best_of,
            }

            if m.state in ('completed', 'forfeit'):
                history.append(match_data)
            else:
                active.append(match_data)

        return _json_response({
            'active_matches': active,
            'match_history': history,
            'total': len(active) + len(history),
        }, cache_control='private, max-age=10')


# ────────────────────────────────────────────────────────────
# Module 9: Participants Directory API
# ────────────────────────────────────────────────────────────

class HubParticipantsAPIView(LoginRequiredMixin, View):
    """GET: Returns all confirmed participants/teams + user's own if pending."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        try:
            page = max(int(request.GET.get('page', '1')), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.GET.get('page_size', '40'))
        except (TypeError, ValueError):
            page_size = 40
        page_size = max(1, min(page_size, 100))

        is_team = tournament.participation_type == 'team'

        # Fetch confirmed registrations
        confirmed_regs_qs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
            status__in=[Registration.CONFIRMED, Registration.AUTO_APPROVED],
        ).select_related('user').order_by('created_at')
        confirmed_regs = list(confirmed_regs_qs)

        # Check if user's own registration is unverified (not in confirmed list)
        user_reg_confirmed = registration.status in ('confirmed', 'auto_approved') if registration else False
        seen_ids = set()

        participants = []
        prefetch = {
            'teams_by_id': {},
            'member_counts': {},
            'team_member_avatars': {},
            'checked_in_team_ids': set(),
            'checked_in_user_ids': set(),
        }

        if is_team:
            from apps.organizations.models import Team, TeamMembership as TM

            team_ids = {reg.team_id for reg in confirmed_regs if reg.team_id}
            if registration and registration.team_id:
                team_ids.add(registration.team_id)

            if team_ids:
                prefetch['teams_by_id'] = {
                    team.id: team
                    for team in Team.objects.filter(id__in=team_ids)
                }
                prefetch['member_counts'] = {
                    row['team_id']: row['count']
                    for row in TM.objects.filter(
                        team_id__in=team_ids,
                        status=TM.Status.ACTIVE,
                    ).values('team_id').annotate(count=models.Count('id'))
                }

                members = TM.objects.filter(
                    team_id__in=team_ids,
                    status=TM.Status.ACTIVE,
                ).select_related('user', 'user__profile').order_by('team_id', 'id')

                avatar_map = {}
                for member in members:
                    slots = avatar_map.setdefault(member.team_id, [])
                    if len(slots) >= 5:
                        continue
                    avatar = ''
                    if hasattr(member.user, 'profile') and hasattr(member.user.profile, 'avatar') and member.user.profile.avatar:
                        avatar = member.user.profile.avatar.url
                    slots.append({
                        'initial': (member.user.get_full_name() or member.user.username)[:1].upper(),
                        'avatar_url': avatar,
                    })
                prefetch['team_member_avatars'] = avatar_map

                prefetch['checked_in_team_ids'] = set(
                    CheckIn.objects.filter(
                        tournament=tournament,
                        team_id__in=team_ids,
                        is_checked_in=True,
                        is_deleted=False,
                    ).values_list('team_id', flat=True)
                )
        else:
            user_ids = {reg.user_id for reg in confirmed_regs if reg.user_id}
            if registration and registration.user_id:
                user_ids.add(registration.user_id)
            if user_ids:
                prefetch['checked_in_user_ids'] = set(
                    CheckIn.objects.filter(
                        tournament=tournament,
                        user_id__in=user_ids,
                        is_checked_in=True,
                        is_deleted=False,
                    ).values_list('user_id', flat=True)
                )

        # If user's team is NOT confirmed, add it first with "pending" status
        if registration and not user_reg_confirmed:
            user_entry = self._build_participant(
                registration, is_team, registration, tournament, request.user,
                verified=False,
                prefetch=prefetch,
            )
            if user_entry:
                participants.append(user_entry)
                seen_ids.add(registration.id)

        for reg in confirmed_regs:
            if reg.id in seen_ids:
                continue
            entry = self._build_participant(
                reg, is_team, registration, tournament, request.user,
                verified=True,
                prefetch=prefetch,
            )
            if entry:
                participants.append(entry)

        total_count = len(participants)
        start = (page - 1) * page_size
        end = start + page_size
        paged = participants[start:end]

        return _json_response({
            'participants': paged,
            'total': total_count,
            'max_participants': tournament.max_participants,
            'is_team': is_team,
            'page': page,
            'page_size': page_size,
            'has_more': end < total_count,
        }, cache_control='private, max-age=30')

    def _build_participant(self, reg, is_team, user_registration, tournament, current_user, verified=True, prefetch=None):
        """Build a single participant dict for the API response."""
        prefetch = prefetch or {}
        status_label = ''
        if not verified:
            status_map = {
                'pending': 'Pending',
                'payment_submitted': 'Payment Review',
                'needs_review': 'Under Review',
            }
            status_label = status_map.get(reg.status, 'Pending')

        if is_team and reg.team_id:
            from apps.organizations.models import Team, TeamMembership as TM
            try:
                team = prefetch.get('teams_by_id', {}).get(reg.team_id)
                if not team:
                    team = Team.objects.get(id=reg.team_id)
                logo_url = ''
                if hasattr(team, 'logo') and team.logo:
                    logo_url = team.logo.url
                team_detail_url = f'/teams/{team.slug}/' if hasattr(team, 'slug') and team.slug else ''

                member_avatars = prefetch.get('team_member_avatars', {}).get(reg.team_id, [])
                member_count = prefetch.get('member_counts', {}).get(reg.team_id)
                if member_count is None:
                    member_count = TM.objects.filter(
                        team_id=reg.team_id,
                        status=TM.Status.ACTIVE,
                    ).count()

                checked_in_team_ids = prefetch.get('checked_in_team_ids', set())
                checked_in = reg.team_id in checked_in_team_ids if checked_in_team_ids else CheckIn.objects.filter(
                    tournament=tournament,
                    team_id=reg.team_id,
                    is_checked_in=True,
                    is_deleted=False,
                ).exists()

                return {
                    'id': reg.id,
                    'type': 'team',
                    'name': team.name,
                    'tag': team.tag or team.name[:3].upper(),
                    'logo_url': logo_url,
                    'detail_url': team_detail_url,
                    'is_you': bool(user_registration and user_registration.team_id and reg.team_id == user_registration.team_id),
                    'seed': reg.seed_number if hasattr(reg, 'seed_number') else None,
                    'member_count': member_count,
                    'member_avatars': member_avatars,
                    'verified': verified,
                    'status_label': status_label,
                    'checked_in': checked_in,
                }
            except Team.DoesNotExist:
                return None
        else:
            avatar_url = _get_avatar_url(reg.user)
            user_slug = getattr(reg.user, 'username', '')
            checked_in_user_ids = prefetch.get('checked_in_user_ids', set())
            checked_in = reg.user_id in checked_in_user_ids if checked_in_user_ids else CheckIn.objects.filter(
                tournament=tournament,
                user=reg.user,
                is_checked_in=True,
                is_deleted=False,
            ).exists()
            return {
                'id': reg.id,
                'type': 'solo',
                'name': reg.user.get_full_name() or reg.user.username,
                'tag': reg.user.username[:3].upper(),
                'logo_url': avatar_url,
                'detail_url': f'/profile/{user_slug}/' if user_slug else '',
                'is_you': reg.user_id == current_user.id,
                'seed': reg.seed_number if hasattr(reg, 'seed_number') else None,
                'verified': verified,
                'status_label': status_label,
                'checked_in': checked_in,
            }


class HubSupportAPIView(LoginRequiredMixin, View):
    """GET/POST support requests for the tournament organizer."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        is_staff_view = _is_tournament_staff_or_organizer(request.user, tournament)
        tickets_qs = HubSupportTicket.objects.filter(tournament=tournament)

        if not is_staff_view:
            if registration and registration.team_id:
                tickets_qs = tickets_qs.filter(
                    models.Q(registration=registration) |
                    models.Q(team_id=registration.team_id) |
                    models.Q(created_by=request.user)
                )
            elif registration:
                tickets_qs = tickets_qs.filter(
                    models.Q(registration=registration) |
                    models.Q(created_by=request.user)
                )
            else:
                tickets_qs = tickets_qs.filter(created_by=request.user)

        try:
            page = max(int(request.GET.get('page', '1')), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.GET.get('page_size', '50'))
        except (TypeError, ValueError):
            page_size = 50
        page_size = max(1, min(page_size, 100))

        total_count = tickets_qs.count()
        offset = (page - 1) * page_size
        has_more = offset + page_size < total_count

        tickets = []
        for t in tickets_qs.select_related('created_by').order_by('-created_at')[offset:offset + page_size]:
            tickets.append({
                'id': t.id,
                'category': t.category,
                'category_display': t.get_category_display(),
                'subject': t.subject,
                'message': t.message,
                'match_ref': t.match_ref,
                'status': t.status,
                'status_display': t.get_status_display(),
                'created_at': t.created_at.isoformat() if t.created_at else None,
                'time_ago': _time_ago(t.created_at) if t.created_at else '',
            })

        return _json_response({
            'tickets': tickets,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'has_more': has_more,
        }, cache_control='no-store')

    def post(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('organizer'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return JsonResponse({'error': 'not_registered'}, status=403)

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid request body.'}, status=400)

        category = body.get('category', 'general')
        subject = (body.get('subject') or '').strip()
        message = (body.get('message') or '').strip()
        match_ref = (body.get('match_ref') or '').strip()

        if not subject or len(subject) < 3:
            return JsonResponse({'error': 'Subject is required (at least 3 characters).'}, status=400)
        if not message or len(message) < 10:
            return JsonResponse({'error': 'Message must be at least 10 characters.'}, status=400)

        valid_categories = ['general', 'dispute', 'technical', 'payment']
        if category not in valid_categories:
            category = 'general'

        ticket = HubSupportTicket.objects.create(
            tournament=tournament,
            registration=registration,
            created_by=request.user,
            team_id=registration.team_id if registration and registration.team_id else None,
            category=category,
            subject=subject,
            message=message,
            match_ref=match_ref,
        )

        # Log the support request
        logger.info(
            '[Hub Support] %s | Tournament: %s | User: %s | Category: %s | Subject: %s',
            tournament.slug, tournament.name, request.user.username, category, subject,
        )

        # Send email notification to organizer (if contact_email exists)
        organizer_email = tournament.contact_email
        if organizer_email:
            try:
                from django.core.mail import send_mail
                from django.conf import settings

                team_name = ''
                if registration.team:
                    team_name = f' (Team: {registration.team.name})'

                email_body = (
                    f"Support Request from {request.user.get_full_name() or request.user.username}{team_name}\n"
                    f"Tournament: {tournament.name}\n"
                    f"Category: {category.replace('_', ' ').title()}\n"
                    f"{'Match Reference: ' + match_ref + chr(10) if match_ref else ''}"
                    f"\n---\n\n"
                    f"Subject: {subject}\n\n"
                    f"{message}\n"
                    f"\n---\n"
                    f"Reply to: {request.user.email or 'N/A'}\n"
                    f"User: {request.user.username} (ID: {request.user.id})\n"
                )

                send_mail(
                    subject=f'[{tournament.name}] Support: {subject}',
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[organizer_email],
                    fail_silently=True,
                )
            except Exception:
                logger.warning('[Hub Support] Failed to send email notification', exc_info=True)

        return JsonResponse({
            'success': True,
            'message': 'Your message has been sent to the tournament organizer. You should receive a response within 24-48 hours.',
            'ticket': {
                'id': ticket.id,
                'category': ticket.category,
                'category_display': ticket.get_category_display(),
                'subject': ticket.subject,
                'message': ticket.message,
                'match_ref': ticket.match_ref,
                'status': ticket.status,
                'status_display': ticket.get_status_display(),
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'time_ago': _time_ago(ticket.created_at) if ticket.created_at else 'just now',
            },
        })
