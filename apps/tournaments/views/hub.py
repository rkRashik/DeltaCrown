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

import logging
from datetime import timedelta

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


def _build_hub_context(request, tournament, registration):
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
        if is_team and registration.team_id:
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
    if is_team and registration.team_id:
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
                    'is_captain': tm.is_tournament_captain if tm else False,
                    'is_igl': is_igl,
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
                    'is_captain': m.is_tournament_captain,
                    'is_igl': False,
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

    # IGL info
    igl_info = None
    if igl_user_id:
        igl_member = next((m for m in squad if m['user_id'] == igl_user_id), None)
        if igl_member:
            igl_info = {
                'name': igl_member['display_name'],
                'user_id': igl_user_id,
            }
    # Fallback: detect IGL from registration_data coordinator_role
    if not igl_info and registration:
        reg_data = registration.registration_data or {}
        coord_role = reg_data.get('coordinator_role', '')
        if 'igl' in coord_role.lower():
            coord_is_self = reg_data.get('coordinator_is_self', True)
            if coord_is_self and user:
                igl_member = next((m for m in squad if m['user_id'] == user.id), None)
                if igl_member:
                    igl_info = {'name': igl_member['display_name'], 'user_id': user.id}
                    igl_member['is_igl'] = True

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
    if is_team and registration.team_id:
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

        # Check if current user is captain
        is_captain = any(m['user_id'] == user.id and m['is_captain'] for m in squad)

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

        # Game theme (for per-game visual styling)
        'game_slug': tournament.game.slug if tournament.game else '',
        'game_primary_color': tournament.game.primary_color if tournament.game else '#00F0FF',
        'game_secondary_color': tournament.game.secondary_color if tournament.game else '#0C0C10',
        'game_accent_color': (tournament.game.accent_color or '#FFFFFF') if tournament.game else '#FFFFFF',
        'game_icon_url': tournament.game.icon.url if tournament.game and tournament.game.icon else '',
        'game_logo_url': tournament.game.logo.url if tournament.game and hasattr(tournament.game, 'logo') and tournament.game.logo else '',
        'game_card_url': tournament.game.card_image.url if tournament.game and hasattr(tournament.game, 'card_image') and tournament.game.card_image else '',

        # API endpoints (JS will poll these)
        'api_state_url': f'/tournaments/{tournament.slug}/hub/api/state/',
        'api_checkin_url': f'/tournaments/{tournament.slug}/hub/api/check-in/',
        'api_announcements_url': f'/tournaments/{tournament.slug}/hub/api/announcements/',
        'api_roster_url': f'/tournaments/{tournament.slug}/hub/api/roster/',
        'api_squad_url': f'/tournaments/{tournament.slug}/hub/api/squad/',
        'api_resources_url': f'/tournaments/{tournament.slug}/hub/api/resources/',
        'api_prize_claim_url': f'/tournaments/{tournament.slug}/hub/api/prize-claim/',
        'api_bracket_url': f'/tournaments/{tournament.slug}/hub/api/bracket/',
        'api_standings_url': f'/tournaments/{tournament.slug}/hub/api/standings/',
        'api_matches_url': f'/tournaments/{tournament.slug}/hub/api/matches/',
        'api_participants_url': f'/tournaments/{tournament.slug}/hub/api/participants/',

        # Social / Contact
        'discord_url': tournament.social_discord or (lobby.discord_server_url if lobby else ''),
        'contact_email': tournament.contact_email or '',
        'organizer_name': tournament.organizer.get_full_name() or tournament.organizer.username if tournament.organizer else 'Organizer',
        'social_twitter': tournament.social_twitter or '',
        'social_instagram': tournament.social_instagram or '',
        'social_youtube': tournament.social_youtube or '',
        'social_website': tournament.social_website or '',

        # Support system API
        'api_support_url': f'/tournaments/{tournament.slug}/hub/api/support/',
    }
    return context


def _build_status_detail(registration, check_in, tournament, now):
    """Build detailed status info for the status modal."""
    import json

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
            'type': 'info',
        })

    if tournament.registration_end and now < tournament.registration_end:
        events.append({
            'label': 'Registration Closes',
            'target': tournament.registration_end.isoformat(),
            'type': 'warning',
        })

    if lobby and lobby.check_in_opens_at and now < lobby.check_in_opens_at:
        events.append({
            'label': 'Check-In Opens',
            'target': lobby.check_in_opens_at.isoformat(),
            'type': 'info',
        })

    if lobby and lobby.check_in_closes_at and now < lobby.check_in_closes_at:
        events.append({
            'label': 'Check-In Closes',
            'target': lobby.check_in_closes_at.isoformat(),
            'type': 'danger',
        })

    if tournament.tournament_start and now < tournament.tournament_start:
        events.append({
            'label': 'Tournament Starts',
            'target': tournament.tournament_start.isoformat(),
            'type': 'info',
        })

    # Return earliest upcoming event
    return events[0] if events else {
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
    status_map = {
        'confirmed': 'Registered',
        'auto_approved': 'Registered',
        'pending': 'Pending Approval',
        'payment_submitted': 'Payment Under Review',
        'needs_review': 'Under Review',
    }
    return status_map.get(registration.status, 'Registered')


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

        registration = _get_user_registration(request.user, tournament)
        if not registration:
            messages.warning(
                request,
                "You must be registered for this tournament to access The Hub."
            )
            return redirect('tournaments:detail', slug=slug)

        context = _build_hub_context(request, tournament, registration)
        return render(request, self.template_name, context)


class HubStateAPIView(LoginRequiredMixin, View):
    """
    JSON endpoint: returns current hub state for real-time polling.
    Called every 15-30s by the JS engine.
    """

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        now = timezone.now()
        lobby = getattr(tournament, 'lobby', None)

        # Check-in state
        check_in = None
        if lobby:
            from apps.organizations.models import TeamMembership
            if tournament.participation_type == 'team' and registration.team_id:
                check_in = CheckIn.objects.filter(
                    tournament=tournament,
                    team_id=registration.team_id,
                    is_deleted=False,
                ).first()
            else:
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
        return JsonResponse(data)


class HubCheckInAPIView(LoginRequiredMixin, View):
    """POST: perform check-in for the current user/team."""

    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        try:
            team_id = None
            if tournament.participation_type == 'team' and registration.team_id:
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
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        lobby = getattr(tournament, 'lobby', None)
        if not lobby:
            return JsonResponse({'announcements': []})

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
        return JsonResponse({'announcements': data})


class HubRosterAPIView(LoginRequiredMixin, View):
    """GET: full tournament roster with check-in status."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        try:
            roster_data = LobbyService.get_roster(tournament.id)
            return JsonResponse(roster_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class HubSquadAPIView(LoginRequiredMixin, View):
    """
    POST: swap a team member's roster slot (STARTER <-> SUBSTITUTE).
    Only team captains can perform swaps, and only when roster isn't locked.
    """

    def post(self, request, slug):
        import json
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        if tournament.participation_type != 'team' or not registration.team_id:
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
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

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

        return JsonResponse({
            'rules': rules,
            'social_links': social_links,
            'contact_email': contact_email,
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
        })


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
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

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

        return JsonResponse({
            'prize_pool': prize_pool,
            'your_prizes': prizes,
            'overview': overview,
            'tournament_status': tournament.status,
        })

    def post(self, request, slug):
        import json

        tournament = get_object_or_404(Tournament, slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

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
    """GET: Returns bracket structure and match data for visualization."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        try:
            bracket = Bracket.objects.get(tournament=tournament)
        except Bracket.DoesNotExist:
            return JsonResponse({
                'generated': False,
                'format': tournament.format,
                'format_display': tournament.get_format_display(),
            })

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
                'scheduled_at': m.scheduled_at.isoformat() if hasattr(m, 'scheduled_at') and m.scheduled_at else None,
            })

        return JsonResponse({
            'generated': True,
            'format': bracket.format,
            'format_display': bracket.get_format_display(),
            'total_rounds': bracket.total_rounds,
            'total_matches': bracket.total_matches,
            'is_finalized': bracket.is_finalized,
            'rounds': list(rounds.values()),
        })


# ────────────────────────────────────────────────────────────
# Module 7: Standings API
# ────────────────────────────────────────────────────────────

class HubStandingsAPIView(LoginRequiredMixin, View):
    """GET: Returns group standings for the tournament."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        is_team = tournament.participation_type == 'team'
        groups = Group.objects.filter(
            stage__tournament=tournament,
        ).prefetch_related('standings').order_by('name')

        if not groups.exists():
            # Fallback: check overall tournament standings from match results
            return JsonResponse({'has_standings': False, 'groups': []})

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
                    is_you = s.team_id == registration.team_id
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

        return JsonResponse({
            'has_standings': True,
            'groups': groups_data,
        })


# ────────────────────────────────────────────────────────────
# Module 8: Matches API
# ────────────────────────────────────────────────────────────

class HubMatchesAPIView(LoginRequiredMixin, View):
    """GET: Returns matches relevant to the current user/team."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        is_team = tournament.participation_type == 'team'
        participant_id = registration.team_id if is_team else request.user.id

        # Get user's matches
        user_matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).filter(
            models.Q(participant1_id=participant_id) | models.Q(participant2_id=participant_id)
        ).order_by('round_number', 'match_number')

        active = []
        history = []
        for m in user_matches:
            is_p1 = m.participant1_id == participant_id
            opponent_name = m.participant2_name if is_p1 else m.participant1_name
            your_score = m.participant1_score if is_p1 else m.participant2_score
            opponent_score = m.participant2_score if is_p1 else m.participant1_score
            is_winner = m.winner_id == participant_id if m.winner_id else None

            round_name = ''
            try:
                bracket = Bracket.objects.get(tournament=tournament)
                round_name = bracket.get_round_name(m.round_number)
            except Bracket.DoesNotExist:
                round_name = f'Round {m.round_number}'

            match_data = {
                'id': m.id,
                'round_number': m.round_number,
                'round_name': round_name,
                'match_number': m.match_number,
                'state': m.state,
                'state_display': m.get_state_display(),
                'opponent_name': opponent_name or 'TBD',
                'your_score': your_score,
                'opponent_score': opponent_score,
                'is_winner': is_winner,
                'lobby_info': m.lobby_info or {},
                'scheduled_at': m.scheduled_at.isoformat() if hasattr(m, 'scheduled_at') and m.scheduled_at else None,
            }

            if m.state in ('completed', 'forfeit'):
                history.append(match_data)
            else:
                active.append(match_data)

        return JsonResponse({
            'active_matches': active,
            'match_history': history,
            'total': len(active) + len(history),
        })


# ────────────────────────────────────────────────────────────
# Module 9: Participants Directory API
# ────────────────────────────────────────────────────────────

class HubParticipantsAPIView(LoginRequiredMixin, View):
    """GET: Returns all confirmed participants/teams + user's own if pending."""

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
            return JsonResponse({'error': 'not_registered'}, status=403)

        is_team = tournament.participation_type == 'team'

        # Fetch confirmed registrations
        confirmed_regs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
            status__in=[Registration.CONFIRMED, Registration.AUTO_APPROVED],
        ).select_related('user').order_by('created_at')

        # Check if user's own registration is unverified (not in confirmed list)
        user_reg_confirmed = registration.status in ('confirmed', 'auto_approved')
        seen_ids = set()

        participants = []

        # If user's team is NOT confirmed, add it first with "pending" status
        if not user_reg_confirmed:
            user_entry = self._build_participant(
                registration, is_team, registration, tournament, request.user,
                verified=False,
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
            )
            if entry:
                participants.append(entry)

        return JsonResponse({
            'participants': participants,
            'total': len(participants),
            'max_participants': tournament.max_participants,
            'is_team': is_team,
        })

    def _build_participant(self, reg, is_team, user_registration, tournament, current_user, verified=True):
        """Build a single participant dict for the API response."""
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
                team = Team.objects.get(id=reg.team_id)
                logo_url = ''
                if hasattr(team, 'logo') and team.logo:
                    logo_url = team.logo.url
                team_detail_url = f'/teams/{team.slug}/' if hasattr(team, 'slug') and team.slug else ''

                members_qs = TM.objects.filter(
                    team_id=reg.team_id,
                    status=TM.Status.ACTIVE,
                ).select_related('user')
                member_avatars = []
                for m in members_qs[:5]:
                    avatar = ''
                    if hasattr(m.user, 'profile') and hasattr(m.user.profile, 'avatar') and m.user.profile.avatar:
                        avatar = m.user.profile.avatar.url
                    member_avatars.append({
                        'initial': (m.user.get_full_name() or m.user.username)[:1].upper(),
                        'avatar_url': avatar,
                    })

                return {
                    'id': reg.id,
                    'type': 'team',
                    'name': team.name,
                    'tag': team.tag or team.name[:3].upper(),
                    'logo_url': logo_url,
                    'detail_url': team_detail_url,
                    'is_you': reg.team_id == user_registration.team_id if user_registration.team_id else False,
                    'seed': reg.seed_number if hasattr(reg, 'seed_number') else None,
                    'member_count': members_qs.count(),
                    'member_avatars': member_avatars,
                    'verified': verified,
                    'status_label': status_label,
                    'checked_in': CheckIn.objects.filter(
                        tournament=tournament,
                        team_id=reg.team_id,
                        is_checked_in=True,
                        is_deleted=False,
                    ).exists(),
                }
            except Team.DoesNotExist:
                return None
        else:
            avatar_url = _get_avatar_url(reg.user)
            user_slug = getattr(reg.user, 'username', '')
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
                'checked_in': CheckIn.objects.filter(
                    tournament=tournament,
                    user=reg.user,
                    is_checked_in=True,
                    is_deleted=False,
                ).exists(),
            }


class HubSupportAPIView(LoginRequiredMixin, View):
    """POST: Submit a support request / dispute to the tournament organizer."""

    def post(self, request, slug):
        tournament = get_object_or_404(Tournament.objects.select_related('organizer'), slug=slug)
        registration = _get_user_registration(request.user, tournament)
        if not registration:
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
        })
