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
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.views import View
from django.contrib import messages

from apps.tournaments.models import (
    Tournament,
    Registration,
    TournamentLobby,
    CheckIn,
    LobbyAnnouncement,
    TournamentAnnouncement,
    TournamentSponsor,
    PrizeClaim,
    TournamentStaff,
    HubSupportTicket,
    RescheduleRequest,
)
from apps.notifications.models import Notification
from apps.tournaments.models.bracket import Bracket, BracketNode
from apps.tournaments.models.group import Group, GroupStanding
from apps.tournaments.models.match import Match
from apps.tournaments.models.prize import PrizeTransaction
from apps.tournaments.services.lobby_service import LobbyService
from apps.tournaments.services.match_lobby_service import ensure_match_lobby_info, hydrate_match_lobby_info

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
    if TournamentStaffAssignment.objects.filter(
        tournament=tournament,
        user=user,
        is_active=True,
    ).exists():
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
            Registration.WAITLISTED,
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
            Registration.WAITLISTED,
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

    payment = getattr(registration, 'payment', None)

    if registration.status == Registration.WAITLISTED:
        return 'You are currently on the waitlist. Full Hub actions unlock after call-up and payment.'

    if registration.status == Registration.PENDING:
        if payment and payment.status == 'rejected':
            return 'Your payment was rejected. Please resubmit payment from Quick Actions to unlock Hub actions.'
        if payment and payment.status in ('pending', 'submitted'):
            return 'Payment verification is pending. Critical actions are locked until verification completes.'
        return 'Complete your tournament payment from Quick Actions to unlock critical Hub actions.'

    status_map = {
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


def _announcement_visuals_from_text(title, message, is_important=False):
    text = f"{title or ''} {message or ''}".lower()
    if is_important or any(k in text for k in ('urgent', 'immediate', 'asap', 'critical', 'now')):
        return {'type': 'urgent', 'icon': 'siren', 'symbol': '🚨'}
    if any(k in text for k in ('draw', 'group draw', 'bracket', 'seed', 'schedule', 'time')):
        return {'type': 'warning', 'icon': 'calendar-clock', 'symbol': '📅'}
    if any(k in text for k in ('live', 'stream', 'broadcast', 'watch')):
        return {'type': 'info', 'icon': 'radio', 'symbol': '📡'}
    if any(k in text for k in ('result', 'winner', 'qualified', 'complete', 'final')):
        return {'type': 'success', 'icon': 'trophy', 'symbol': '🏆'}
    if any(k in text for k in ('check-in', 'check in', 'attendance', 'confirm')):
        return {'type': 'warning', 'icon': 'user-check', 'symbol': '✅'}
    return {'type': 'info', 'icon': 'megaphone', 'symbol': '📣'}


def _build_hub_announcements(tournament, now=None, limit=20, offset=0):
    now = now or timezone.now()
    items = []
    limit = max(1, int(limit or 20))
    offset = max(0, int(offset or 0))

    toc_rows = TournamentAnnouncement.objects.filter(
        tournament=tournament,
    ).select_related('created_by').order_by('-is_pinned', '-created_at')[offset:offset + limit]

    for row in toc_rows:
        visuals = _announcement_visuals_from_text(row.title, row.message, row.is_important)
        items.append({
            'id': f'toc-{row.id}',
            'title': row.title,
            'message': row.message,
            'type': visuals['type'],
            'icon': visuals['icon'],
            'symbol': visuals['symbol'],
            'is_pinned': bool(row.is_pinned),
            'is_important': bool(row.is_important),
            'posted_by': row.created_by.username if row.created_by else 'Organizer',
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'sort_ts': (row.created_at.timestamp() if row.created_at else 0),
            'time_ago': _time_ago(row.created_at, now) if row.created_at else '',
        })

    # Fallback to legacy lobby announcements only when no TOC announcements exist.
    if not items:
        lobby = getattr(tournament, 'lobby', None)
        if lobby:
            legacy_rows = LobbyAnnouncement.objects.filter(
                lobby=lobby,
                is_visible=True,
                is_deleted=False,
            ).select_related('posted_by').order_by('-is_pinned', '-created_at')[offset:offset + limit]
            for row in legacy_rows:
                visuals = _announcement_visuals_from_text(row.title, row.message, row.announcement_type == 'urgent')
                items.append({
                    'id': f'lobby-{row.id}',
                    'title': row.title,
                    'message': row.message,
                    'type': row.announcement_type or visuals['type'],
                    'icon': visuals['icon'],
                    'symbol': visuals['symbol'],
                    'is_pinned': bool(row.is_pinned),
                    'is_important': row.announcement_type == 'urgent',
                    'posted_by': row.posted_by.username if row.posted_by else 'Organizer',
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'sort_ts': (row.created_at.timestamp() if row.created_at else 0),
                    'time_ago': _time_ago(row.created_at, now) if row.created_at else '',
                })

    items.sort(key=lambda entry: (0 if entry.get('is_pinned') else 1, -float(entry.get('sort_ts') or 0)))
    return items[:limit]


def _format_currency_amount(value):
    if value is None or value == '':
        return ''
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _resolve_hub_participant_id(tournament, registration, user):
    if tournament.participation_type == 'team':
        return registration.team_id if registration and registration.team_id else None
    return user.id if user and user.is_authenticated else None


def _resolve_hub_command_center(
    tournament,
    registration,
    user,
    *,
    now=None,
    check_in=None,
    check_in_status='not_configured',
    hub_critical_locked=False,
    is_staff_view=False,
):
    now = now or timezone.now()

    payload = {
        'show': False,
        'badge_label': 'Standby',
        'badge_tone': 'info',
        'title': 'Waiting for matchups',
        'subtitle': 'As soon as matches are generated, your next action will appear here.',
        'countdown_label': 'Next Update',
        'countdown_target': '',
        'countdown_mode': 'static',
        'countdown_text': 'Awaiting schedule',
        'hint': 'Track mission progress while match operations are staged.',
        'cta_label': 'View Schedule',
        'cta_action': 'view_schedule',
        'cta_url': '',
        'cta_disabled': False,
        'match_id': None,
        'match_room_url': '',
        'opponent_name': '',
        'match_state': '',
        'scheduled_at': None,
        'lobby_window_open': False,
        'within_priority_window': False,
    }

    participant_id = _resolve_hub_participant_id(tournament, registration, user)
    if not participant_id and not is_staff_view:
        return payload

    terminal_states = {
        Match.COMPLETED,
        Match.FORFEIT,
        Match.CANCELLED,
        Match.DISPUTED,
    }
    active_states = {
        Match.CHECK_IN,
        Match.READY,
        Match.LIVE,
        Match.PENDING_RESULT,
    }

    match_qs = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
    ).exclude(
        state__in=terminal_states,
    )
    if not is_staff_view:
        match_qs = match_qs.filter(
            models.Q(participant1_id=participant_id) | models.Q(participant2_id=participant_id)
        )

    match_rows = list(
        match_qs.only(
            'id',
            'round_number',
            'match_number',
            'state',
            'scheduled_time',
            'participant1_id',
            'participant2_id',
            'participant1_name',
            'participant2_name',
        ).order_by('scheduled_time', 'round_number', 'match_number', 'id')[:30]
    )
    if not match_rows:
        return payload

    state_priority = {
        Match.LIVE: 0,
        Match.PENDING_RESULT: 1,
        Match.READY: 2,
        Match.CHECK_IN: 3,
        Match.SCHEDULED: 4,
    }

    def _match_rank(match_obj):
        state_weight = state_priority.get(match_obj.state, 9)
        ts_weight = match_obj.scheduled_time or (now + timedelta(days=3650))
        return state_weight, ts_weight, match_obj.id

    target = sorted(match_rows, key=_match_rank)[0]
    scheduled_at = target.scheduled_time
    seconds_to_match = None
    if scheduled_at:
        seconds_to_match = int((scheduled_at - now).total_seconds())

    within_priority_window = bool(
        seconds_to_match is not None and 15 * 60 <= seconds_to_match <= 60 * 60
    )
    lobby_window_minutes_before = 30
    lobby_window_opens_at = (
        scheduled_at - timedelta(minutes=lobby_window_minutes_before)
        if scheduled_at else None
    )
    lobby_window_open = bool(
        target.state in {Match.READY, Match.LIVE, Match.PENDING_RESULT}
        or (lobby_window_opens_at and now >= lobby_window_opens_at)
    )

    if is_staff_view:
        opponent_name = (target.participant2_name or target.participant1_name or 'Opponent')
    else:
        if target.participant1_id == participant_id:
            opponent_name = target.participant2_name or 'Opponent'
        else:
            opponent_name = target.participant1_name or 'Opponent'

    show_command = bool(target.state in active_states or within_priority_window)
    if tournament.status in {Tournament.DRAFT, Tournament.REGISTRATION_OPEN}:
        show_command = bool(target.state in active_states)

    cta_action = 'view_schedule'
    cta_label = 'View Schedule'
    cta_url = ''
    badge_label = 'Up Next'
    badge_tone = 'info'
    title = f"VS {opponent_name}"
    subtitle = 'Your next match assignment is staged.'
    hint = 'Follow mission progress while the bracket advances.'
    countdown_label = 'Match Starts In'
    countdown_target = scheduled_at.isoformat() if scheduled_at else ''
    countdown_mode = 'countdown' if countdown_target else 'static'
    countdown_text = '--:--' if countdown_target else 'Awaiting schedule'

    if target.state == Match.LIVE:
        badge_label = 'Live Match'
        badge_tone = 'danger'
        cta_action = 'enter_lobby'
        cta_label = 'Enter Lobby'
        cta_url = reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': target.id})
        subtitle = 'Match is live now. Enter lobby for real-time operations.'
        hint = 'Coordinate with opponent and submit results from lobby controls.'
        countdown_label = 'Status'
        countdown_mode = 'live'
        countdown_text = 'LIVE NOW'
        countdown_target = ''
    elif lobby_window_open:
        badge_label = 'Lobby Open'
        badge_tone = 'success'
        cta_action = 'enter_lobby'
        cta_label = 'Enter Lobby'
        cta_url = reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': target.id})
        subtitle = 'Lobby window is open. Enter now to finalize match prep.'
        hint = 'Use lobby chat and final readiness checks before kickoff.'
        countdown_label = 'Match Starts In'
        countdown_target = scheduled_at.isoformat() if scheduled_at else ''
        countdown_mode = 'countdown' if countdown_target else 'static'
    elif target.state == Match.CHECK_IN or (check_in_status == 'open' and not (check_in and check_in.is_checked_in)):
        badge_label = 'Check-In Required'
        badge_tone = 'warning'
        cta_action = 'check_in'
        cta_label = 'Check In Now'
        subtitle = 'Check in now to avoid no-show forfeit risk.'
        hint = 'Check-in confirms your presence for this match window.'
        if lobby_window_opens_at and not lobby_window_open:
            countdown_label = 'Lobby Opens In'
            countdown_target = lobby_window_opens_at.isoformat()
            countdown_mode = 'countdown'
    elif target.state in {Match.READY, Match.PENDING_RESULT}:
        badge_label = 'Match Ready'
        badge_tone = 'success'
        cta_action = 'enter_lobby'
        cta_label = 'Open Match Ops'
        cta_url = reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': target.id})
        subtitle = 'Pre-match workflow is active. Continue in the match room.'
        hint = 'Use the room controls to complete your current operation step.'

    cta_disabled = bool(hub_critical_locked and cta_action in {'check_in', 'enter_lobby'})
    if cta_disabled:
        cta_action = 'open_support'
        cta_label = 'Contact Support'
        cta_url = ''
        hint = _critical_lock_reason(registration)
        cta_disabled = False

    payload.update({
        'show': show_command,
        'badge_label': badge_label,
        'badge_tone': badge_tone,
        'title': title,
        'subtitle': subtitle,
        'countdown_label': countdown_label,
        'countdown_target': countdown_target,
        'countdown_mode': countdown_mode,
        'countdown_text': countdown_text,
        'hint': hint,
        'cta_label': cta_label,
        'cta_action': cta_action,
        'cta_url': cta_url,
        'cta_disabled': cta_disabled,
        'match_id': target.id,
        'match_room_url': reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': target.id}) if show_command else '',
        'opponent_name': opponent_name,
        'match_state': target.state,
        'scheduled_at': scheduled_at.isoformat() if scheduled_at else None,
        'lobby_window_open': bool(lobby_window_open),
        'within_priority_window': bool(within_priority_window),
    })
    return payload


def _build_hub_lifecycle_pipeline(tournament, *, command_center=None):
    has_draw_signal = Bracket.objects.filter(tournament=tournament).exists() or GroupStanding.objects.filter(
        group__tournament=tournament,
        group__is_deleted=False,
        is_deleted=False,
    ).exists()
    has_matches = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
    ).exists()

    status = str(tournament.status or '').lower()
    active_key = 'registered'

    if status == Tournament.COMPLETED:
        active_key = 'rewards'
    elif status == Tournament.LIVE:
        active_key = 'live_ops' if (command_center and command_center.get('show')) else 'scheduled'
    elif status in {'check_in', Tournament.REGISTRATION_CLOSED}:
        if has_matches:
            active_key = 'scheduled'
        elif has_draw_signal:
            active_key = 'drawn'
        else:
            active_key = 'registered'
    elif status in {Tournament.DRAFT, Tournament.REGISTRATION_OPEN}:
        active_key = 'registered'
    else:
        if has_matches:
            active_key = 'scheduled'
        elif has_draw_signal:
            active_key = 'drawn'
        else:
            active_key = 'registered'

    if command_center and command_center.get('show') and active_key in {'drawn', 'scheduled'}:
        active_key = 'live_ops'

    steps = [
        {'key': 'registered', 'label': 'Registered', 'icon': 'check'},
        {'key': 'drawn', 'label': 'Drawn', 'icon': 'shuffle'},
        {'key': 'scheduled', 'label': 'Scheduled', 'icon': 'calendar-check'},
        {'key': 'live_ops', 'label': 'Live Ops', 'icon': 'crosshair'},
        {'key': 'rewards', 'label': 'Rewards', 'icon': 'trophy'},
    ]
    step_index = {step['key']: idx for idx, step in enumerate(steps)}
    active_idx = step_index.get(active_key, 0)

    for idx, step in enumerate(steps):
        step['completed'] = idx < active_idx
        step['active'] = idx == active_idx

    progress_percent = int((active_idx / max(len(steps) - 1, 1)) * 100)
    return {
        'steps': steps,
        'active_key': active_key,
        'active_index': active_idx,
        'phase_label': f'PHASE {active_idx + 1}/{len(steps)}',
        'progress_percent': progress_percent,
    }


def _build_hub_official_pass(user, tournament, registration, *, team_name='', is_team=False, is_captain=False, hub_critical_locked=False):
    username = user.username if user and user.is_authenticated else 'Participant'
    display_name = (user.get_full_name() or username) if user and user.is_authenticated else 'Participant'
    initials = ''.join(part[0] for part in display_name.split()[:2]).upper() or username[:2].upper()

    participant_label = 'Solo Participant'
    if is_team and team_name:
        participant_label = team_name
        if is_captain:
            participant_label = f'{team_name} (C)'

    reg_status = registration.status if registration else ''
    is_verified = bool(
        registration and reg_status in {Registration.CONFIRMED, Registration.AUTO_APPROVED} and not hub_critical_locked
    )

    pass_id = ''
    if registration:
        pass_id = str(
            getattr(registration, 'registration_id', '')
            or getattr(registration, 'registration_number', '')
            or registration.id
        )
    if not pass_id:
        pass_id = str(user.id if user and user.is_authenticated else 'N/A')

    if tournament.has_entry_fee and tournament.entry_fee_amount:
        fee_text = f"{_format_currency_amount(tournament.entry_fee_amount)} {tournament.entry_fee_currency}"
    else:
        fee_text = 'Free Entry'

    return {
        'display_name': display_name,
        'username': username,
        'initials': initials[:2],
        'participant_label': participant_label,
        'pass_id': pass_id,
        'entry_verified': is_verified,
        'entry_status_label': 'Verified' if is_verified else 'Pending',
        'fee_text': fee_text,
    }


def _build_hub_context(request, tournament, registration, query_suffix='', is_staff_view=False):
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
                    '_tm_is_captain': m.is_tournament_captain,
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

    # Apply unified flag only when a canonical captain/IGL could be resolved.
    # If not resolved, preserve existing flags from snapshot/team membership.
    if captain_igl_user_id:
        for m in squad:
            m['is_captain_igl'] = (m['user_id'] == captain_igl_user_id)

    if captain_igl_user_id:
        captain_member = next((m for m in squad if m['user_id'] == captain_igl_user_id), None)
        if captain_member:
            igl_info = {'name': captain_member['display_name'], 'user_id': captain_igl_user_id}

    squad_ready = len(starters) >= min_roster and not squad_warnings

    # ── Announcements ────────────────────────────────────
    announcements = _build_hub_announcements(tournament, now=now, limit=20)

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

    payment = getattr(registration, 'payment', None) if registration else None

    hub_payment_action_url = ''
    hub_payment_action_label = ''
    hub_payment_action_hint = ''
    hub_payment_action_variant = ''
    hub_payment_action_enabled = False
    if registration and tournament.has_entry_fee:
        if registration.status == Registration.WAITLISTED:
            hub_payment_action_hint = 'Payment opens only after you are called up from the waitlist.'
            hub_payment_action_variant = 'info'
        elif registration.status in (Registration.PENDING, Registration.NEEDS_REVIEW):
            if payment and payment.status in ('submitted', 'pending'):
                hub_payment_action_hint = 'Payment is under verification. You will be notified after review.'
                hub_payment_action_variant = 'info'
            else:
                hub_payment_action_url = reverse('tournaments:payment_complete', kwargs={'registration_id': registration.id})
                hub_payment_action_enabled = True
                if payment and payment.status == 'rejected':
                    hub_payment_action_label = 'Retry Payment'
                    hub_payment_action_hint = 'Your previous proof was rejected. Resubmit now to regain eligibility.'
                    hub_payment_action_variant = 'danger'
                else:
                    hub_payment_action_label = 'Complete Payment'
                    hub_payment_action_hint = 'Submit payment now to unlock match lobby and other critical actions.'
                    hub_payment_action_variant = 'warning'
        elif registration.status == Registration.PAYMENT_SUBMITTED:
            hub_payment_action_hint = 'Payment submitted. Verification is in progress.'
            hub_payment_action_variant = 'info'

    hub_recent_alerts = []
    if user and user.is_authenticated:
        payment_status = ((getattr(payment, 'status', '') if registration else '') or '').strip().lower()
        requires_payment_now = bool(
            registration
            and tournament.has_entry_fee
            and registration.status in (Registration.PENDING, Registration.NEEDS_REVIEW, Registration.SUBMITTED)
            and payment_status not in {'submitted', 'verified', 'waived'}
        )

        alert_qs = Notification.objects.filter(
            recipient=user,
            tournament_id=tournament.id,
        ).order_by('-created_at')[:20]
        seen_alert_keys = set()
        for alert in alert_qs:
            target_url = (
                (getattr(alert, 'action_url', '') or '').strip()
                or (getattr(alert, 'url', '') or '').strip()
                or f'/tournaments/{tournament.slug}/hub/'
            )
            body_text = (
                (getattr(alert, 'message', '') or '').strip()
                or (getattr(alert, 'body', '') or '').strip()
            )
            title_text = (getattr(alert, 'title', '') or 'Tournament Alert').strip()
            action_label = (getattr(alert, 'action_label', '') or '').strip() or 'Open'
            text_for_classification = f"{title_text} {body_text}".lower()
            is_waitlist_update = any(token in text_for_classification for token in ('waitlist', 'called up', 'promotion', 'promoted'))

            alert_icon = 'bell-ring'
            alert_tone = 'info'
            alert_type_label = 'Update'
            if any(token in text_for_classification for token in ('reject', 'declin', 'failed', 'invalid')):
                alert_icon = 'shield-alert'
                alert_tone = 'danger'
                alert_type_label = 'Action Required'
            elif any(token in text_for_classification for token in ('verified', 'confirm', 'approved', 'success')):
                alert_icon = 'badge-check'
                alert_tone = 'success'
                alert_type_label = 'Resolved'
            elif any(token in text_for_classification for token in ('waitlist', 'called up', 'promotion')):
                alert_icon = 'users-round'
                alert_tone = 'warning'
                alert_type_label = 'Queue Update'
            elif any(token in text_for_classification for token in ('payment', 'proof', 'verification', 'receipt')):
                alert_icon = 'receipt-text'
                alert_tone = 'warning'
                alert_type_label = 'Payment'

            if action_label.lower() in {'open', 'view', 'details', 'see details'}:
                if is_waitlist_update and requires_payment_now:
                    action_label = 'Complete Payment'
                    target_url = reverse('tournaments:payment_complete', kwargs={'registration_id': registration.id})
                elif 'payment' in text_for_classification and any(token in text_for_classification for token in ('reject', 'failed', 'invalid', 'resubmit', 'retry')):
                    action_label = 'Retry Payment'
                elif alert_tone == 'success':
                    action_label = 'View Confirmation'
                elif is_waitlist_update:
                    action_label = 'Check Status'
                else:
                    action_label = 'Open Hub'

            # Hide stale success confirmations that conflict with current registration/payment state.
            is_stale_success = (
                alert_tone == 'success'
                and any(token in text_for_classification for token in ('payment', 'verified', 'registration', 'confirmed', 'all set'))
            )
            if registration and registration.status == Registration.WAITLISTED and is_stale_success and not is_waitlist_update:
                continue
            if registration and requires_payment_now and is_stale_success and not is_waitlist_update:
                continue

            dedupe_key = (
                title_text.lower(),
                body_text.lower(),
                target_url,
                action_label.lower(),
            )
            if dedupe_key in seen_alert_keys:
                continue
            seen_alert_keys.add(dedupe_key)
            hub_recent_alerts.append({
                'id': alert.id,
                'title': title_text,
                'body': body_text,
                'target_url': target_url,
                'action_label': action_label,
                'icon': alert_icon,
                'tone': alert_tone,
                'type_label': alert_type_label,
                'time_ago': _time_ago(alert.created_at, now),
                'created_at_display': timezone.localtime(alert.created_at).strftime('%d %b %Y, %I:%M %p'),
                'is_read': bool(getattr(alert, 'is_read', False)),
            })
            if len(hub_recent_alerts) >= 5:
                break

    hub_primary_alert = hub_recent_alerts[0] if hub_recent_alerts else None

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
    hub_command_center = _resolve_hub_command_center(
        tournament,
        registration,
        user,
        now=now,
        check_in=check_in,
        check_in_status=check_in_status,
        hub_critical_locked=hub_critical_locked,
        is_staff_view=is_staff_view,
    )
    hub_lifecycle_pipeline = _build_hub_lifecycle_pipeline(
        tournament,
        command_center=hub_command_center,
    )
    hub_official_pass = _build_hub_official_pass(
        user,
        tournament,
        registration,
        team_name=team_name,
        is_team=is_team,
        is_captain=is_captain,
        hub_critical_locked=hub_critical_locked,
    )

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
        'hub_command_center': hub_command_center,
        'hub_lifecycle_pipeline': hub_lifecycle_pipeline,
        'hub_official_pass': hub_official_pass,

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
        'api_reschedule_settings_url': f'/tournaments/{tournament.slug}/hub/api/reschedule/settings/{query_suffix}',

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
        'hub_payment_action_url': hub_payment_action_url,
        'hub_payment_action_label': hub_payment_action_label,
        'hub_payment_action_hint': hub_payment_action_hint,
        'hub_payment_action_variant': hub_payment_action_variant,
        'hub_payment_action_enabled': hub_payment_action_enabled,
        'hub_recent_alerts': hub_recent_alerts,
        'hub_primary_alert': hub_primary_alert,
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
    elif status == 'waitlisted':
        steps.append({'label': 'On Waitlist Queue', 'done': False, 'icon': 'hourglass', 'active': True})
    elif status == 'pending':
        payment = getattr(registration, 'payment', None)
        if payment and payment.status == 'rejected':
            steps.append({'label': 'Payment Rejected — Retry Required', 'done': False, 'icon': 'alert-triangle', 'active': True, 'error': True})
        elif payment and payment.status in ('pending', 'submitted'):
            steps.append({'label': 'Payment Under Review', 'done': False, 'icon': 'credit-card', 'active': True})
        elif tournament.has_entry_fee:
            steps.append({'label': 'Payment Required', 'done': False, 'icon': 'wallet', 'active': True})
        else:
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
        'waitlisted': 'Waitlisted',
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


def _build_participant_media_map(tournament, participant_ids):
    """Return {participant_id: logo_or_avatar_url} for team or solo tournaments."""
    normalized_ids = set()
    for raw_id in participant_ids or []:
        if not raw_id:
            continue
        try:
            normalized_ids.add(int(raw_id))
        except (TypeError, ValueError):
            continue

    if not normalized_ids:
        return {}

    media_map = {}
    is_team = tournament.participation_type == 'team'

    if is_team:
        from apps.organizations.models import Team

        for team in Team.objects.filter(id__in=normalized_ids).only('id', 'logo'):
            logo_url = ''
            try:
                if hasattr(team, 'logo') and team.logo:
                    logo_url = team.logo.url
            except Exception:
                logo_url = ''
            media_map[team.id] = logo_url
        return media_map

    from django.contrib.auth import get_user_model

    User = get_user_model()
    users = User.objects.filter(id__in=normalized_ids).select_related('profile')
    for user in users:
        media_map[user.id] = _get_avatar_url(user)
    return media_map


def _json_response(payload, status=200, cache_control=None):
    resp = JsonResponse(payload, status=status)
    if cache_control:
        resp['Cache-Control'] = cache_control
    return resp


def _participant_reschedule_policy(tournament):
    """Return participant-rescheduling policy from tournament config."""
    config = tournament.config if isinstance(tournament.config, dict) else {}
    policy = config.get('participant_rescheduling')
    if not isinstance(policy, dict):
        policy = {}

    allow = bool(policy.get('allow_participant_rescheduling', False))

    raw_deadline_minutes = policy.get('deadline_minutes_before')
    if raw_deadline_minutes is None:
        raw_deadline_hours = policy.get('deadline_hours_before')
        if raw_deadline_hours is None:
            deadline_minutes = 120
        else:
            try:
                deadline_minutes = int(float(raw_deadline_hours) * 60)
            except (TypeError, ValueError):
                deadline_minutes = 120
    else:
        try:
            deadline_minutes = int(raw_deadline_minutes)
        except (TypeError, ValueError):
            deadline_minutes = 120

    deadline_minutes = max(5, min(deadline_minutes, 10080))
    return {
        'allow_participant_rescheduling': allow,
        'deadline_minutes_before': deadline_minutes,
        'deadline_hours_before': round(deadline_minutes / 60, 2),
    }


def _set_participant_reschedule_policy(tournament, *, allow, deadline_minutes, updated_by_id=None):
    """Persist participant rescheduling policy in tournament config."""
    config = tournament.config if isinstance(tournament.config, dict) else {}
    policy = config.get('participant_rescheduling') if isinstance(config.get('participant_rescheduling'), dict) else {}

    policy['allow_participant_rescheduling'] = bool(allow)
    policy['deadline_minutes_before'] = int(max(5, min(int(deadline_minutes), 10080)))
    policy['updated_at'] = timezone.now().isoformat()
    policy['updated_by'] = updated_by_id

    config['participant_rescheduling'] = policy
    tournament.config = config
    tournament.save(update_fields=['config'])


def _resolve_user_match_side(user, tournament, match, registration=None):
    """Resolve whether the user is participant1 (1) or participant2 (2) for this match."""
    if not user or not user.is_authenticated:
        return None

    if tournament.participation_type == 'team':
        team_ids = set()
        if registration and registration.team_id:
            team_ids.add(registration.team_id)
        else:
            from apps.organizations.models import TeamMembership

            team_ids = set(
                TeamMembership.objects.filter(
                    user=user,
                    status=TeamMembership.Status.ACTIVE,
                ).values_list('team_id', flat=True)
            )

        if match.participant1_id in team_ids:
            return 1
        if match.participant2_id in team_ids:
            return 2
        return None

    if match.participant1_id == user.id:
        return 1
    if match.participant2_id == user.id:
        return 2
    return None


def _match_registered_user_ids(tournament, match):
    """Resolve registered user ids associated with both match participants."""
    participant_ids = [pid for pid in (match.participant1_id, match.participant2_id) if pid]
    if not participant_ids:
        return []

    regs = Registration.objects.filter(
        tournament=tournament,
        status__in=[Registration.CONFIRMED, Registration.AUTO_APPROVED],
        is_deleted=False,
        user__isnull=False,
    ).filter(
        models.Q(user_id__in=participant_ids) | models.Q(team_id__in=participant_ids)
    )
    return list(regs.values_list('user_id', flat=True).distinct())


def _participant_user_ids_for_side(tournament, participant_id):
    """Resolve registered user IDs for a specific participant id (team or solo)."""
    if not participant_id:
        return []

    regs = Registration.objects.filter(
        tournament=tournament,
        status__in=[Registration.CONFIRMED, Registration.AUTO_APPROVED],
        is_deleted=False,
        user__isnull=False,
    ).filter(
        models.Q(user_id=participant_id) | models.Q(team_id=participant_id)
    )
    return list(regs.values_list('user_id', flat=True).distinct())


def _serialize_reschedule_request(req):
    if not req:
        return None
    return {
        'id': str(req.id),
        'match_id': req.match_id,
        'status': req.status,
        'proposer_side': req.proposer_side,
        'requested_by_id': req.requested_by_id,
        'reviewed_by_id': req.reviewed_by_id,
        'old_time': req.old_time.isoformat() if req.old_time else None,
        'new_time': req.new_time.isoformat() if req.new_time else None,
        'reason': req.reason,
        'response_note': getattr(req, 'response_note', '') or '',
        'expires_at': req.expires_at.isoformat() if getattr(req, 'expires_at', None) else None,
        'reviewed_at': req.reviewed_at.isoformat() if getattr(req, 'reviewed_at', None) else None,
        'created_at': req.created_at.isoformat() if req.created_at else None,
        'updated_at': req.updated_at.isoformat() if req.updated_at else None,
    }


def _group_projection_token(group_name: str) -> str:
    """Convert group names into compact projection labels (e.g. Group A -> A)."""
    raw = str(group_name or '').strip()
    if not raw:
        return ''

    lower = raw.lower()
    if lower.startswith('group '):
        token = raw[6:].strip()
        if token:
            return token

    return raw


def _build_projected_cross_match_pairs(groups) -> list[dict[str, str]]:
    """Build projected seeding placeholders for adjacent group cross-matches."""
    pairs: list[dict[str, str]] = []
    if not groups or len(groups) < 2:
        return pairs

    ordered = sorted(groups, key=lambda group: (group.display_order, group.id))
    for idx in range(0, len(ordered), 2):
        if idx + 1 >= len(ordered):
            break

        group_a = ordered[idx]
        group_b = ordered[idx + 1]
        token_a = _group_projection_token(group_a.name)
        token_b = _group_projection_token(group_b.name)
        if not token_a or not token_b:
            continue

        pairs.append({'p1_label': f'{token_a}1', 'p2_label': f'{token_b}2'})

        # Only render runner-up cross-match when both groups advance >= 2.
        if min(int(group_a.advancement_count or 0), int(group_b.advancement_count or 0)) >= 2:
            pairs.append({'p1_label': f'{token_b}1', 'p2_label': f'{token_a}2'})

    return pairs


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
            is_staff_view=view_mode['is_staff_view'],
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

        view_mode = _resolve_hub_view_mode(request, tournament, registration)
        now = timezone.now()
        lobby = getattr(tournament, 'lobby', None)
        hub_critical_locked = _critical_actions_locked(request.user, tournament, registration)
        check_in_status = lobby.check_in_status if lobby else 'not_configured'

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
        command_center = _resolve_hub_command_center(
            tournament,
            registration,
            request.user,
            now=now,
            check_in=check_in,
            check_in_status=check_in_status,
            hub_critical_locked=hub_critical_locked,
            is_staff_view=view_mode['is_staff_view'],
        )
        lifecycle_pipeline = _build_hub_lifecycle_pipeline(
            tournament,
            command_center=command_center,
        )

        data = {
            'tournament_status': tournament.status,
            'user_status': _registration_status_label(registration, check_in),
            'phase_event': phase_event,
            'command_center': command_center,
            'lifecycle_pipeline': lifecycle_pipeline,
            'check_in': {
                'status': check_in_status,
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

        try:
            limit = int(request.GET.get('limit', '20'))
        except (TypeError, ValueError):
            limit = 20
        limit = max(5, min(limit, 100))

        try:
            offset = int(request.GET.get('offset', '0'))
        except (TypeError, ValueError):
            offset = 0
        offset = max(0, offset)

        now = timezone.now()
        data_plus_one = _build_hub_announcements(tournament, now=now, limit=limit + 1, offset=offset)
        has_more = len(data_plus_one) > limit
        data = data_plus_one[:limit]

        return _json_response({
            'announcements': data,
            'meta': {
                'limit': limit,
                'offset': offset,
                'returned': len(data),
                'has_more': has_more,
                'next_offset': (offset + len(data)) if has_more else None,
            },
        }, cache_control='private, max-age=15')


class HubAlertDeleteAPIView(LoginRequiredMixin, View):
    """POST: delete a single Action Center alert for the current user."""

    def post(self, request, slug, notification_id):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return JsonResponse({'success': False, 'error': 'not_registered'}, status=403)

        deleted_count, _ = Notification.objects.filter(
            id=notification_id,
            recipient=request.user,
            tournament_id=tournament.id,
        ).delete()
        return JsonResponse({'success': deleted_count > 0, 'deleted_count': deleted_count})


class HubAlertsClearAPIView(LoginRequiredMixin, View):
    """POST: clear all Action Center alerts for this tournament and user."""

    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return JsonResponse({'success': False, 'error': 'not_registered'}, status=403)

        deleted_count, _ = Notification.objects.filter(
            recipient=request.user,
            tournament_id=tournament.id,
        ).delete()
        return JsonResponse({'success': True, 'deleted_count': deleted_count})


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

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

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
        If a bracket exists, rounds are returned as bracket rounds.
        If no bracket exists (group-stage/round-robin schedules), rounds are
        grouped by group + round and include per-match group metadata.

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
            bracket = None

        groups_qs = Group.objects.filter(tournament=tournament, is_deleted=False).order_by('display_order', 'id')
        group_rows = list(groups_qs)
        has_groups = len(group_rows) > 0
        groups_drawn = False
        if has_groups:
            groups_drawn = GroupStanding.objects.filter(
                group__tournament=tournament,
                group__is_deleted=False,
                is_deleted=False,
            ).exists()
        projected_pairs = []
        if tournament.format == Tournament.GROUP_PLAYOFF and has_groups:
            projected_pairs = _build_projected_cross_match_pairs(group_rows)

        # Build rounds data from matches
        matches_qs = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
        )
        if bracket is not None:
            matches_qs = matches_qs.filter(bracket=bracket)
        else:
            # Round-robin/group-derived schedules may not have a Bracket row.
            matches_qs = matches_qs.filter(bracket__isnull=True)

        matches = list(matches_qs.order_by('round_number', 'match_number', 'id'))
        if not matches:
            if has_groups and groups_drawn:
                group_status = 'drawn_waiting_matches'
                group_message = (
                    'Group draw is complete. The organizer needs to generate group-stage matches '
                    'before the bracket can be displayed.'
                )
            elif has_groups:
                group_status = 'configured_waiting_draw'
                group_message = (
                    'Group stage is configured. Bracket data will appear after the draw and '
                    'match generation steps are completed.'
                )
            else:
                group_status = 'no_group_stage'
                group_message = (
                    'The bracket will appear here once the organizer generates matchups.'
                )

            return _json_response({
                'generated': False,
                'format': tournament.format,
                'format_display': tournament.get_format_display(),
                'has_bracket_record': bracket is not None,
                'group_context': {
                    'has_groups': has_groups,
                    'groups_drawn': groups_drawn,
                    'status': group_status,
                    'message': group_message,
                    'projected_seeding_pairs': projected_pairs,
                    'projected_seeding_title': 'Projected Seeding (Cross-Match)' if projected_pairs else '',
                },
            }, cache_control='private, max-age=15')

        participant_ids = {
            pid
            for match in matches
            for pid in (match.participant1_id, match.participant2_id)
            if pid
        }
        participant_media_map = _build_participant_media_map(tournament, participant_ids)

        def _coerce_group_id(raw_group_id):
            if raw_group_id in (None, ''):
                return None
            try:
                return int(raw_group_id)
            except (TypeError, ValueError):
                return None

        group_name_by_id = {}
        if bracket is None and has_groups:
            group_name_by_id = {
                group.id: group.name
                for group in groups_qs.only('id', 'name')
            }

        def _extract_group_meta(match_obj):
            lobby = match_obj.lobby_info or {}
            group_id = _coerce_group_id(lobby.get('group_id'))
            group_name = str(
                lobby.get('group_label')
                or lobby.get('group_name')
                or group_name_by_id.get(group_id)
                or ''
            ).strip()
            if not group_name and group_id in group_name_by_id:
                group_name = group_name_by_id[group_id]
            return group_id, group_name

        rounds = {}
        group_sections = {}
        for m in matches:
            rn = m.round_number or 0
            group_id = None
            group_name = ''

            if bracket is not None:
                round_key = f'bracket:{rn}'
                round_name = bracket.get_round_name(rn)
            else:
                group_id, group_name = _extract_group_meta(m)
                group_key = group_id if group_id is not None else (group_name.lower() if group_name else 'ungrouped')
                round_key = f'group:{group_key}:{rn}'
                if group_name and rn:
                    round_name = f'{group_name} - Round {rn}'
                elif group_name:
                    round_name = group_name
                else:
                    round_name = f'Round {rn}' if rn else 'Round'

            if round_key not in rounds:
                rounds[round_key] = {
                    'round_number': rn,
                    'round_name': round_name,
                    'group_id': group_id,
                    'group_name': group_name or None,
                    'matches': [],
                }

            serialized_match = {
                'id': m.id,
                'match_number': m.match_number,
                'state': m.state,
                'state_display': m.get_state_display(),
                'participant1': {
                    'id': m.participant1_id,
                    'name': m.participant1_name or 'TBD',
                    'score': m.participant1_score,
                    'is_winner': m.winner_id == m.participant1_id if m.winner_id else False,
                    'logo_url': participant_media_map.get(m.participant1_id, ''),
                },
                'participant2': {
                    'id': m.participant2_id,
                    'name': m.participant2_name or 'TBD',
                    'score': m.participant2_score,
                    'is_winner': m.winner_id == m.participant2_id if m.winner_id else False,
                    'logo_url': participant_media_map.get(m.participant2_id, ''),
                },
                'scheduled_at': m.scheduled_time.isoformat() if m.scheduled_time else None,
            }

            if bracket is None:
                serialized_match.update({
                    'group_id': group_id,
                    'group_name': group_name or None,
                })

            rounds[round_key]['matches'].append(serialized_match)

            if bracket is None:
                section_key = group_id if group_id is not None else (group_name.lower() if group_name else 'ungrouped')
                section_name = group_name or (f'Group {group_id}' if group_id is not None else 'Ungrouped')
                if section_key not in group_sections:
                    group_sections[section_key] = {
                        'group_id': group_id,
                        'group_name': section_name,
                        'rounds': {},
                    }
                if rn not in group_sections[section_key]['rounds']:
                    group_sections[section_key]['rounds'][rn] = {
                        'round_number': rn,
                        'round_name': f'Round {rn}' if rn else 'Round',
                        'matches': [],
                    }
                group_sections[section_key]['rounds'][rn]['matches'].append(serialized_match)

        rounds_payload = list(rounds.values())
        if bracket is None:
            rounds_payload = sorted(
                rounds_payload,
                key=lambda r: (
                    1 if not r.get('group_name') else 0,
                    (r.get('group_name') or '').lower(),
                    r.get('round_number') or 0,
                ),
            )

        group_stage_payload = None
        group_context_payload = None
        if bracket is None:
            groups_payload = []
            for section in sorted(
                group_sections.values(),
                key=lambda g: (1 if not g.get('group_name') else 0, (g.get('group_name') or '').lower()),
            ):
                rounds_list = [
                    section['rounds'][round_number]
                    for round_number in sorted(section['rounds'].keys())
                ]
                groups_payload.append({
                    'group_id': section['group_id'],
                    'group_name': section['group_name'],
                    'rounds': rounds_list,
                })
            group_stage_payload = {
                'has_groups': has_groups,
                'groups': groups_payload,
            }

            terminal_states = {
                Match.COMPLETED,
                Match.FORFEIT,
                Match.CANCELLED,
            }
            legacy_no_show = getattr(Match, 'NO_SHOW', None)
            if legacy_no_show:
                terminal_states.add(legacy_no_show)

            all_group_matches_complete = bool(matches) and all(m.state in terminal_states for m in matches)
            if has_groups and tournament.format == Tournament.GROUP_PLAYOFF:
                group_context_payload = {
                    'has_groups': has_groups,
                    'groups_drawn': groups_drawn,
                    'status': 'group_stage_complete' if all_group_matches_complete else 'group_stage_active',
                    'message': (
                        'Group stage complete. Playoff bracket generation is ready.'
                        if all_group_matches_complete
                        else 'Group stage is active. Playoff bracket slots are projected from current group ordering.'
                    ),
                    'projected_seeding_pairs': projected_pairs,
                    'projected_seeding_title': 'Projected Seeding (Cross-Match)' if projected_pairs else '',
                }

        response_payload = {
            'generated': True,
            'generated_mode': 'bracket' if bracket is not None else 'group_stage',
            'format': bracket.format if bracket is not None else tournament.format,
            'format_display': bracket.get_format_display() if bracket is not None else tournament.get_format_display(),
            'total_rounds': bracket.total_rounds if bracket is not None else len(rounds),
            'total_matches': bracket.total_matches if bracket is not None else len(matches),
            'is_finalized': bracket.is_finalized if bracket is not None else False,
            'rounds': rounds_payload,
        }
        if group_stage_payload is not None:
            response_payload['group_stage'] = group_stage_payload
        if group_context_payload is not None:
            response_payload['group_context'] = group_context_payload

        return _json_response(response_payload, cache_control='private, max-age=15')


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
            is_deleted=False,
        ).order_by('display_order', 'name')

        if groups.exists():
            groups_data = []
            for group in groups:
                standings = GroupStanding.objects.filter(
                    group=group,
                    is_deleted=False,
                ).select_related('user', 'user__profile').order_by('rank', '-points', '-goal_difference', 'id')

                team_meta_map = {}
                if is_team:
                    team_ids = [s.team_id for s in standings if s.team_id]
                    if team_ids:
                        from apps.organizations.models import Team
                        for team in Team.objects.filter(id__in=team_ids).only('id', 'name', 'logo'):
                            logo_url = ''
                            try:
                                if hasattr(team, 'logo') and team.logo:
                                    logo_url = team.logo.url
                            except Exception:
                                logo_url = ''
                            team_meta_map[team.id] = {
                                'name': team.name,
                                'logo_url': logo_url,
                            }

                seen_participants = set()

                rows = []
                for s in standings:
                    participant_key = (
                        ('team', s.team_id) if s.team_id
                        else ('user', s.user_id)
                    )
                    if participant_key[1] is None or participant_key in seen_participants:
                        continue
                    seen_participants.add(participant_key)

                    name = ''
                    is_you = False
                    logo_url = ''
                    if is_team and s.team_id:
                        team_meta = team_meta_map.get(s.team_id, {})
                        name = team_meta.get('name', f'Team #{s.team_id}')
                        logo_url = team_meta.get('logo_url', '')
                        is_you = registration and s.team_id == registration.team_id
                    elif s.user_id:
                        name = s.user.get_full_name() or s.user.username if s.user else f'User #{s.user_id}'
                        logo_url = _get_avatar_url(s.user) if s.user else ''
                        is_you = s.user_id == request.user.id

                    rows.append({
                        'rank': s.rank,
                        'name': name,
                        'logo_url': logo_url,
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
        participant_media_map = _build_participant_media_map(tournament, stats.keys())

        rows = []
        for pid, s in stats.items():
            rows.append({
                'participant_id': pid,
                'name': s['name'],
                'logo_url': participant_media_map.get(pid, ''),
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
        requested_scope = (request.GET.get('scope') or '').strip().lower()
        include_all_matches = requested_scope == 'all'
        show_full_matchup = is_staff_view or include_all_matches
        participant_id = (registration.team_id if registration else None) if is_team else request.user.id

        # Get user's matches (staff/organizers see ALL matches)
        user_matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
        )
        if not is_staff_view and not include_all_matches:
            user_matches = user_matches.filter(
                models.Q(participant1_id=participant_id) | models.Q(participant2_id=participant_id)
            )
        user_matches = list(user_matches.order_by('round_number', 'match_number'))

        participant_ids = {
            pid
            for match in user_matches
            for pid in (match.participant1_id, match.participant2_id)
            if pid
        }
        participant_media_map = _build_participant_media_map(tournament, participant_ids)

        # Pre-fetch bracket once for round name lookups (avoid N+1)
        bracket = None
        try:
            bracket = Bracket.objects.get(tournament=tournament)
        except Bracket.DoesNotExist:
            pass

        reschedule_policy = _participant_reschedule_policy(tournament)
        reschedule_enabled = bool(reschedule_policy['allow_participant_rescheduling'])
        reschedule_disabled_reason = None if reschedule_enabled else 'participant_rescheduling_disabled'
        reschedule_deadline_minutes = reschedule_policy['deadline_minutes_before']
        now = timezone.now()
        lobby_window_minutes_before = 30

        pending_requests_by_match = {}
        if user_matches and reschedule_enabled:
            pending_requests = RescheduleRequest.objects.filter(
                match_id__in=[m.id for m in user_matches],
                status=RescheduleRequest.PENDING,
            ).order_by('match_id', '-created_at')
            for req in pending_requests:
                if req.match_id not in pending_requests_by_match:
                    pending_requests_by_match[req.match_id] = req

        active = []
        history = []
        for m in user_matches:
            is_my_match = bool(participant_id and (m.participant1_id == participant_id or m.participant2_id == participant_id))
            my_side = None
            if participant_id:
                if m.participant1_id == participant_id:
                    my_side = 1
                elif m.participant2_id == participant_id:
                    my_side = 2

            if is_staff_view:
                # Staff/organizer sees both sides — no "your" vs "opponent"
                is_p1 = True  # default perspective: p1 on left
                opponent_name = m.participant2_name
                your_score = m.participant1_score
                opponent_score = m.participant2_score
                is_winner = None
            elif include_all_matches and not is_my_match:
                is_p1 = False
                opponent_name = m.participant2_name or m.participant1_name
                your_score = None
                opponent_score = None
                is_winner = None
            else:
                is_p1 = m.participant1_id == participant_id
                opponent_name = m.participant2_name if is_p1 else m.participant1_name
                your_score = m.participant1_score if is_p1 else m.participant2_score
                opponent_score = m.participant2_score if is_p1 else m.participant1_score
                inferred_winner_id = m.winner_id
                if not inferred_winner_id and m.state in (Match.COMPLETED, Match.FORFEIT):
                    p1_score = m.participant1_score
                    p2_score = m.participant2_score
                    if p1_score is not None and p2_score is not None and p1_score != p2_score:
                        inferred_winner_id = m.participant1_id if p1_score > p2_score else m.participant2_id
                is_winner = inferred_winner_id == participant_id if inferred_winner_id else None

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

            lobby_info = ensure_match_lobby_info(
                m,
                create_if_missing=True,
                reset_reminder_marks=False,
            )
            pending_request = pending_requests_by_match.get(m.id)
            deadline_at = (
                (m.scheduled_time - timedelta(minutes=reschedule_deadline_minutes))
                if m.scheduled_time else None
            )
            lobby_window_opens_at_dt = (
                (m.scheduled_time - timedelta(minutes=lobby_window_minutes_before))
                if m.scheduled_time else None
            )

            is_terminal_state = m.state in (Match.COMPLETED, Match.FORFEIT, Match.CANCELLED, Match.DISPUTED)
            lobby_window_open = False
            if not is_terminal_state:
                if m.state in (Match.READY, Match.LIVE, Match.PENDING_RESULT):
                    lobby_window_open = True
                elif lobby_window_opens_at_dt:
                    lobby_window_open = now >= lobby_window_opens_at_dt

            lobby_window_starts_in_seconds = None
            if lobby_window_opens_at_dt:
                lobby_window_starts_in_seconds = int((lobby_window_opens_at_dt - now).total_seconds())

            schedule_state_mutable = m.state in (Match.SCHEDULED, Match.CHECK_IN, Match.READY)
            within_deadline = bool(deadline_at and now <= deadline_at)
            can_propose = bool(
                reschedule_enabled
                and not is_staff_view
                and is_my_match
                and my_side in (1, 2)
                and schedule_state_mutable
                and m.scheduled_time
                and within_deadline
                and not pending_request
            )
            can_respond = bool(
                reschedule_enabled
                and not is_staff_view
                and is_my_match
                and my_side in (1, 2)
                and pending_request
                and pending_request.proposer_side in (1, 2)
                and int(pending_request.proposer_side) != int(my_side)
                and schedule_state_mutable
            )
            match_room_url = reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': m.id})

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
                'is_staff_view': show_full_matchup,
                'is_my_match': is_my_match,
                'lobby_info': lobby_info,
                'match_room_url': match_room_url if (is_my_match or is_staff_view) else '',
                'scheduled_at': m.scheduled_time.isoformat() if m.scheduled_time else None,
                'lobby_window_opens_at': lobby_window_opens_at_dt.isoformat() if lobby_window_opens_at_dt else None,
                'lobby_window_open': bool(lobby_window_open),
                'lobby_window_minutes_before': int(lobby_window_minutes_before),
                'lobby_window_starts_in_seconds': lobby_window_starts_in_seconds,
                'game_scores': raw_gs,
                'best_of': best_of,
                'p1_logo_url': participant_media_map.get(m.participant1_id, ''),
                'p2_logo_url': participant_media_map.get(m.participant2_id, ''),
                'reschedule': {
                    'enabled': bool(reschedule_enabled),
                    'disabled_reason': reschedule_disabled_reason,
                    'deadline_minutes_before': int(reschedule_deadline_minutes),
                    'deadline_at': deadline_at.isoformat() if deadline_at else None,
                    'my_side': my_side,
                    'can_propose': can_propose,
                    'can_respond': can_respond,
                    'pending_request': _serialize_reschedule_request(pending_request),
                },
            }

            if include_all_matches and not is_staff_view and not is_my_match:
                match_data['lobby_info'] = {}
                match_data['match_room_url'] = ''
                match_data['reschedule'] = {
                    'enabled': bool(reschedule_enabled),
                    'disabled_reason': reschedule_disabled_reason,
                    'deadline_minutes_before': int(reschedule_deadline_minutes),
                    'deadline_at': deadline_at.isoformat() if deadline_at else None,
                    'my_side': None,
                    'can_propose': False,
                    'can_respond': False,
                    'pending_request': None,
                }

            if is_my_match and not is_staff_view and not include_all_matches:
                opponent_pid = m.participant2_id if is_p1 else m.participant1_id
                match_data['opponent_logo_url'] = participant_media_map.get(opponent_pid, '')
            elif is_my_match:
                opponent_pid = m.participant2_id if is_p1 else m.participant1_id
                match_data['opponent_logo_url'] = participant_media_map.get(opponent_pid, '')
            else:
                match_data['opponent_logo_url'] = ''

            if m.state in ('completed', 'forfeit'):
                history.append(match_data)
            else:
                active.append(match_data)

        return _json_response({
            'active_matches': active,
            'match_history': history,
            'total': len(active) + len(history),
        }, cache_control='private, max-age=10')


class HubRescheduleSettingsAPIView(LoginRequiredMixin, View):
    """GET/POST participant reschedule policy for the current tournament."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        is_staff = _is_tournament_staff_or_organizer(request.user, tournament)
        if not registration and not is_staff:
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        policy = _participant_reschedule_policy(tournament)
        return _json_response({
            **policy,
            'can_manage': bool(is_staff),
            'disabled_reason': None if policy['allow_participant_rescheduling'] else 'participant_rescheduling_disabled',
        }, cache_control='private, max-age=20')

    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        if not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'forbidden'}, status=403, cache_control='no-store')

        try:
            body = json.loads(request.body or '{}')
            if not isinstance(body, dict):
                body = {}
        except (json.JSONDecodeError, ValueError):
            return _json_response({'error': 'invalid_payload'}, status=400, cache_control='no-store')

        current_policy = _participant_reschedule_policy(tournament)
        allow = bool(body.get('allow_participant_rescheduling', current_policy['allow_participant_rescheduling']))

        deadline_minutes = current_policy['deadline_minutes_before']
        if 'deadline_minutes_before' in body:
            try:
                deadline_minutes = int(body.get('deadline_minutes_before'))
            except (TypeError, ValueError):
                return _json_response({'error': 'deadline_minutes_before must be a number.'}, status=400, cache_control='no-store')
        elif 'deadline_hours_before' in body:
            try:
                deadline_minutes = int(float(body.get('deadline_hours_before')) * 60)
            except (TypeError, ValueError):
                return _json_response({'error': 'deadline_hours_before must be a number.'}, status=400, cache_control='no-store')

        deadline_minutes = max(5, min(deadline_minutes, 10080))
        _set_participant_reschedule_policy(
            tournament,
            allow=allow,
            deadline_minutes=deadline_minutes,
            updated_by_id=request.user.id,
        )

        updated_policy = _participant_reschedule_policy(tournament)
        return _json_response({
            'success': True,
            **updated_policy,
            'can_manage': True,
        }, cache_control='no-store')


class HubMatchRescheduleProposalAPIView(LoginRequiredMixin, View):
    """POST participant proposal for match rescheduling negotiation."""

    def post(self, request, slug, match_id):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        policy = _participant_reschedule_policy(tournament)
        if not policy['allow_participant_rescheduling']:
            return _json_response({'error': 'participant_rescheduling_disabled'}, status=403, cache_control='no-store')

        match = get_object_or_404(
            Match,
            id=match_id,
            tournament=tournament,
            is_deleted=False,
        )

        if match.state not in (Match.SCHEDULED, Match.CHECK_IN, Match.READY):
            return _json_response({'error': f"cannot_reschedule_state:{match.state}"}, status=400, cache_control='no-store')

        if not match.scheduled_time:
            return _json_response({'error': 'match_not_scheduled'}, status=400, cache_control='no-store')

        actor_side = _resolve_user_match_side(request.user, tournament, match, registration)
        if actor_side not in (1, 2):
            return _json_response({'error': 'not_match_participant'}, status=403, cache_control='no-store')

        now = timezone.now()
        deadline_at = match.scheduled_time - timedelta(minutes=policy['deadline_minutes_before'])
        if now > deadline_at:
            return _json_response({'error': 'proposal_deadline_passed', 'deadline_at': deadline_at.isoformat()}, status=400, cache_control='no-store')

        existing_pending = RescheduleRequest.objects.filter(
            match=match,
            status=RescheduleRequest.PENDING,
        ).order_by('-created_at').first()
        if existing_pending:
            return _json_response({
                'error': 'pending_request_exists',
                'pending_request': _serialize_reschedule_request(existing_pending),
            }, status=409, cache_control='no-store')

        try:
            body = json.loads(request.body or '{}')
            if not isinstance(body, dict):
                body = {}
        except (json.JSONDecodeError, ValueError):
            return _json_response({'error': 'invalid_payload'}, status=400, cache_control='no-store')

        new_time_str = body.get('new_time') or body.get('scheduled_time')
        if not new_time_str:
            return _json_response({'error': 'new_time is required.'}, status=400, cache_control='no-store')

        new_time = parse_datetime(str(new_time_str))
        if not new_time:
            return _json_response({'error': 'invalid_datetime_format'}, status=400, cache_control='no-store')
        if timezone.is_naive(new_time):
            new_time = timezone.make_aware(new_time)

        if new_time <= now + timedelta(minutes=5):
            return _json_response({'error': 'new_time_must_be_future'}, status=400, cache_control='no-store')

        if match.scheduled_time and abs((new_time - match.scheduled_time).total_seconds()) < 60:
            return _json_response({'error': 'new_time_must_differ'}, status=400, cache_control='no-store')

        reason = (body.get('reason') or '').strip()
        if len(reason) > 500:
            return _json_response({'error': 'reason_too_long'}, status=400, cache_control='no-store')

        proposal = RescheduleRequest.objects.create(
            match=match,
            requested_by_id=request.user.id,
            proposer_side=actor_side,
            old_time=match.scheduled_time,
            new_time=new_time,
            reason=reason,
            status=RescheduleRequest.PENDING,
            expires_at=match.scheduled_time,
        )

        target_participant_id = match.participant2_id if actor_side == 1 else match.participant1_id
        target_user_ids = _participant_user_ids_for_side(tournament, target_participant_id)

        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService

            TOCNotificationsService.fire_auto_event(
                tournament,
                'match_reschedule_proposed',
                {
                    'target_user_ids': target_user_ids,
                    'match_id': match.id,
                    'round_number': match.round_number,
                    'match_number': match.match_number,
                    'participant1': match.participant1_name or 'Participant 1',
                    'participant2': match.participant2_name or 'Participant 2',
                    'proposed_time': timezone.localtime(new_time).strftime('%b %d, %Y %I:%M %p'),
                    'force_email': True,
                    'dedupe': False,
                    'url': f'/tournaments/{tournament.slug}/hub/?tab=matches',
                },
            )
        except Exception:
            pass

        return _json_response({
            'success': True,
            'request': _serialize_reschedule_request(proposal),
            'deadline_at': deadline_at.isoformat(),
        }, cache_control='no-store')


class HubMatchRescheduleRespondAPIView(LoginRequiredMixin, View):
    """POST accept/reject for a pending participant reschedule proposal."""

    def post(self, request, slug, match_id):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration and not _is_tournament_staff_or_organizer(request.user, tournament):
            return _json_response({'error': 'not_registered'}, status=403, cache_control='no-store')

        lock_resp = _forbidden_if_critical_locked(request, tournament, registration)
        if lock_resp:
            return lock_resp

        match = get_object_or_404(
            Match,
            id=match_id,
            tournament=tournament,
            is_deleted=False,
        )

        actor_side = _resolve_user_match_side(request.user, tournament, match, registration)
        if actor_side not in (1, 2):
            return _json_response({'error': 'not_match_participant'}, status=403, cache_control='no-store')

        try:
            body = json.loads(request.body or '{}')
            if not isinstance(body, dict):
                body = {}
        except (json.JSONDecodeError, ValueError):
            return _json_response({'error': 'invalid_payload'}, status=400, cache_control='no-store')

        action = str(body.get('action') or '').strip().lower()
        if action not in {'accept', 'reject'}:
            return _json_response({'error': 'action must be accept or reject.'}, status=400, cache_control='no-store')

        request_id = body.get('request_id')
        pending_qs = RescheduleRequest.objects.filter(
            match=match,
            status=RescheduleRequest.PENDING,
        )
        if request_id:
            pending_qs = pending_qs.filter(id=request_id)

        pending_request = pending_qs.order_by('-created_at').first()
        if not pending_request:
            return _json_response({'error': 'pending_request_not_found'}, status=404, cache_control='no-store')

        if pending_request.proposer_side in (1, 2) and int(pending_request.proposer_side) == int(actor_side):
            return _json_response({'error': 'proposer_cannot_respond'}, status=403, cache_control='no-store')

        now = timezone.now()
        if pending_request.expires_at and now > pending_request.expires_at:
            pending_request.status = RescheduleRequest.CANCELLED
            pending_request.response_note = 'Proposal expired before response.'
            pending_request.reviewed_by_id = request.user.id
            pending_request.reviewed_at = now
            pending_request.save(update_fields=['status', 'response_note', 'reviewed_by_id', 'reviewed_at', 'updated_at'])
            return _json_response({'error': 'pending_request_expired'}, status=400, cache_control='no-store')

        response_note = (body.get('response_note') or body.get('reason') or '').strip()
        if len(response_note) > 500:
            return _json_response({'error': 'response_note_too_long'}, status=400, cache_control='no-store')

        pending_request.reviewed_by_id = request.user.id
        pending_request.reviewed_at = now
        pending_request.response_note = response_note

        notification_event = 'match_reschedule_rejected'
        notification_targets = []

        if action == 'accept':
            old_time = match.scheduled_time
            match.scheduled_time = pending_request.new_time
            lobby_info, lobby_changed = hydrate_match_lobby_info(
                match,
                create_if_missing=True,
                reset_reminder_marks=True,
            )
            update_fields = ['scheduled_time']
            if lobby_changed:
                match.lobby_info = lobby_info
                update_fields.append('lobby_info')
            match.save(update_fields=update_fields)

            pending_request.status = RescheduleRequest.APPROVED
            pending_request.old_time = old_time
            notification_event = 'match_reschedule_accepted'
            notification_targets = _match_registered_user_ids(tournament, match)

            try:
                from apps.tournaments.api.toc.notifications_service import TOCNotificationsService

                TOCNotificationsService.fire_auto_event(
                    tournament,
                    'schedule_generated',
                    {
                        'target_user_ids': notification_targets,
                        'scheduled_count': 1,
                        'round_count': 1,
                        'force_email': False,
                        'dedupe': False,
                        'reason': 'participant_reschedule_accepted',
                        'url': f'/tournaments/{tournament.slug}/hub/?tab=schedule',
                    },
                )
            except Exception:
                pass
        else:
            pending_request.status = RescheduleRequest.REJECTED
            proposer_pid = match.participant1_id if pending_request.proposer_side == 1 else match.participant2_id
            notification_targets = _participant_user_ids_for_side(tournament, proposer_pid)

        pending_request.save(update_fields=[
            'status',
            'old_time',
            'reviewed_by_id',
            'reviewed_at',
            'response_note',
            'updated_at',
        ])

        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService

            TOCNotificationsService.fire_auto_event(
                tournament,
                notification_event,
                {
                    'target_user_ids': notification_targets,
                    'match_id': match.id,
                    'round_number': match.round_number,
                    'match_number': match.match_number,
                    'participant1': match.participant1_name or 'Participant 1',
                    'participant2': match.participant2_name or 'Participant 2',
                    'proposed_time': timezone.localtime(pending_request.new_time).strftime('%b %d, %Y %I:%M %p') if pending_request.new_time else '',
                    'force_email': True,
                    'dedupe': False,
                    'url': f'/tournaments/{tournament.slug}/hub/?tab=matches',
                },
            )
        except Exception:
            pass

        return _json_response({
            'success': True,
            'action': action,
            'request': _serialize_reschedule_request(pending_request),
            'scheduled_at': match.scheduled_time.isoformat() if match.scheduled_time else None,
        }, cache_control='no-store')


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

        try:
            page = max(int(request.GET.get('page', '1')), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.GET.get('page_size', '40'))
        except (TypeError, ValueError):
            page_size = 40
        page_size = max(1, min(page_size, 100))

        include_member_avatars = (request.GET.get('include_member_avatars') or '').strip().lower() in {'1', 'true', 'yes'}
        include_profile_avatars = (request.GET.get('include_profile_avatars') or '').strip().lower() in {'1', 'true', 'yes'}

        sort = (request.GET.get('sort') or 'joined_desc').strip().lower()
        allowed_sort = {'joined_desc', 'joined_asc', 'seed_asc', 'seed_desc'}
        if sort not in allowed_sort:
            sort = 'joined_desc'

        is_team = tournament.participation_type == 'team'

        # Fetch confirmed registrations (ordered base queryset)
        confirmed_regs_qs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
            status__in=[Registration.CONFIRMED, Registration.AUTO_APPROVED],
        ).select_related('user')

        if sort == 'joined_asc':
            confirmed_regs_qs = confirmed_regs_qs.order_by('created_at')
        elif sort == 'seed_asc':
            confirmed_regs_qs = confirmed_regs_qs.annotate(
                _seed_is_null=models.Case(
                    models.When(seed__isnull=True, then=1),
                    default=0,
                    output_field=models.IntegerField(),
                )
            ).order_by('_seed_is_null', 'seed', 'created_at')
        elif sort == 'seed_desc':
            confirmed_regs_qs = confirmed_regs_qs.annotate(
                _seed_is_null=models.Case(
                    models.When(seed__isnull=True, then=1),
                    default=0,
                    output_field=models.IntegerField(),
                )
            ).order_by('_seed_is_null', '-seed', '-created_at')
        else:
            confirmed_regs_qs = confirmed_regs_qs.order_by('-created_at')

        # Check if user's own registration is unverified (not in confirmed list)
        user_reg_confirmed = registration.status in ('confirmed', 'auto_approved') if registration else False
        include_unverified_self = bool(registration and not user_reg_confirmed)

        participants = []

        # Pagination math with optional unverified-self row pinned at the top.
        confirmed_total = confirmed_regs_qs.count()
        total_count = confirmed_total + (1 if include_unverified_self else 0)
        start = (page - 1) * page_size
        end = start + page_size

        confirmed_offset = start
        confirmed_limit = page_size

        if include_unverified_self:
            if start == 0:
                # Add self first, then fill the remaining page from confirmed rows.
                user_entry = self._build_participant(
                    registration, is_team, registration, tournament, request.user,
                    verified=False,
                    prefetch=None,
                    include_profile_avatars=include_profile_avatars,
                )
                if user_entry:
                    participants.append(user_entry)
                confirmed_limit = max(page_size - len(participants), 0)
                confirmed_offset = 0
            else:
                # Page 2+ shifts by one because page 1 included the self row.
                confirmed_offset = max(start - 1, 0)

        confirmed_page_regs = list(
            confirmed_regs_qs[confirmed_offset:confirmed_offset + confirmed_limit]
        ) if confirmed_limit > 0 else []

        regs_for_prefetch = list(confirmed_page_regs)
        if include_unverified_self and registration and start == 0:
            regs_for_prefetch.append(registration)

        prefetch = {
            'teams_by_id': {},
            'member_counts': {},
            'team_member_avatars': {},
            'checked_in_team_ids': set(),
            'checked_in_user_ids': set(),
        }

        if is_team:
            from apps.organizations.models import Team, TeamMembership as TM

            team_ids = {reg.team_id for reg in regs_for_prefetch if reg.team_id}

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

                if include_member_avatars:
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
            user_ids = {reg.user_id for reg in regs_for_prefetch if reg.user_id}
            if user_ids:
                prefetch['checked_in_user_ids'] = set(
                    CheckIn.objects.filter(
                        tournament=tournament,
                        user_id__in=user_ids,
                        is_checked_in=True,
                        is_deleted=False,
                    ).values_list('user_id', flat=True)
                )

        for reg in confirmed_page_regs:
            entry = self._build_participant(
                reg, is_team, registration, tournament, request.user,
                verified=True,
                prefetch=prefetch,
                include_profile_avatars=include_profile_avatars,
            )
            if entry:
                participants.append(entry)

        return _json_response({
            'participants': participants,
            'total': total_count,
            'max_participants': tournament.max_participants,
            'is_team': is_team,
            'sort': sort,
            'include_member_avatars': include_member_avatars,
            'include_profile_avatars': include_profile_avatars,
            'page': page,
            'page_size': page_size,
            'has_more': end < total_count,
        }, cache_control='private, max-age=30')

    def _build_participant(self, reg, is_team, user_registration, tournament, current_user, verified=True, prefetch=None, include_profile_avatars=True):
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
            avatar_url = _get_avatar_url(reg.user) if include_profile_avatars else ''
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
