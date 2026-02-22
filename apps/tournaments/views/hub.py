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
)
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
    if is_team and registration.team_id:
        members = TeamMembership.objects.filter(
            team_id=registration.team_id,
            status=TeamMembership.Status.ACTIVE,
        ).select_related('user', 'user__profile')

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

            member_data = {
                'id': m.id,
                'user_id': m.user_id,
                'username': m.user.username,
                'display_name': m.display_name or m.user.get_full_name() or m.user.username,
                'role': m.role,
                'player_role': m.player_role or '',
                'roster_slot': m.roster_slot or 'STARTER',
                'is_captain': m.is_tournament_captain,
                'game_id': game_id,
                'has_passport': has_passport,
                'avatar_url': _get_avatar_url(m.user),
            }
            squad.append(member_data)

            if not has_passport and m.role in ['PLAYER', 'SUBSTITUTE']:
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

    # ── Team info ────────────────────────────────────────
    team = None
    team_name = ''
    team_tag = ''
    if is_team and registration.team_id:
        from apps.organizations.models import Team
        try:
            team = Team.objects.get(id=registration.team_id)
            team_name = team.name
            team_tag = team.tag or team.name[:3].upper()
        except Exception:
            pass

    context = {
        'tournament': tournament,
        'registration': registration,
        'lobby': lobby,
        'is_team': is_team,

        # Status
        'user_status': user_status,
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

        # API endpoints (JS will poll these)
        'api_state_url': f'/tournaments/{tournament.slug}/hub/api/state/',
        'api_checkin_url': f'/tournaments/{tournament.slug}/hub/api/check-in/',
        'api_announcements_url': f'/tournaments/{tournament.slug}/hub/api/announcements/',
        'api_roster_url': f'/tournaments/{tournament.slug}/hub/api/roster/',
    }
    return context


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
