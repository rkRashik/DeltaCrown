"""
Derived Lifecycle Announcements — Pure-function event deriver.

Inspects canonical tournament state (status, stage, matches, brackets,
registrations) and produces a list of derived lifecycle events for display
on TOC, HUB, and Dashboard surfaces.

Returns dicts — no side effects, no persistence, fully generic.
Works for any tournament format. GROUP_PLAYOFF-specific logic is isolated.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Event types ──────────────────────────────────────────────────────────────
EVENT_REG_CLOSED = 'registrations_closed'
EVENT_GROUP_DRAW = 'group_draw_completed'
EVENT_MATCHES_GENERATED = 'matches_generated'
EVENT_SCHEDULE_PUBLISHED = 'schedule_published'
EVENT_GROUP_COMPLETE = 'group_stage_completed'
EVENT_BRACKET_PUBLISHED = 'bracket_published'
EVENT_KNOCKOUT_LIVE = 'knockout_live'
EVENT_TOURNAMENT_COMPLETED = 'tournament_completed'
EVENT_LOBBY_SOON = 'lobby_opens_soon'
EVENT_LOBBY_OPEN = 'lobby_is_open'
EVENT_LOBBY_EXPIRED = 'lobby_expired'
EVENT_RESULT_RECORDED = 'result_recorded'
EVENT_QUALIFIED_KNOCKOUT = 'qualified_to_knockout'
EVENT_OPPONENT_ASSIGNED = 'opponent_assigned'
EVENT_ADVANCED = 'advanced_to_next_round'
EVENT_ELIMINATED = 'eliminated'


# ── Visual mapping ───────────────────────────────────────────────────────────
VISUALS = {
    EVENT_REG_CLOSED:       {'icon': 'lock',          'color': 'amber',   'category': 'system'},
    EVENT_GROUP_DRAW:       {'icon': 'layers',        'color': 'cyan',    'category': 'system'},
    EVENT_MATCHES_GENERATED:{'icon': 'calendar-check','color': 'cyan',    'category': 'system'},
    EVENT_SCHEDULE_PUBLISHED:{'icon': 'calendar',     'color': 'cyan',    'category': 'system'},
    EVENT_GROUP_COMPLETE:   {'icon': 'check-circle',  'color': 'emerald', 'category': 'system'},
    EVENT_BRACKET_PUBLISHED:{'icon': 'git-branch',    'color': 'cyan',    'category': 'system'},
    EVENT_KNOCKOUT_LIVE:    {'icon': 'swords',        'color': 'emerald', 'category': 'system'},
    EVENT_TOURNAMENT_COMPLETED:{'icon': 'trophy',     'color': 'amber',   'category': 'system'},
    EVENT_LOBBY_SOON:       {'icon': 'clock',         'color': 'amber',   'category': 'personal'},
    EVENT_LOBBY_OPEN:       {'icon': 'door-open',     'color': 'amber',   'category': 'personal'},
    EVENT_LOBBY_EXPIRED:    {'icon': 'alert-circle',  'color': 'red',     'category': 'personal'},
    EVENT_RESULT_RECORDED:  {'icon': 'check-square',  'color': 'emerald', 'category': 'system'},
    EVENT_QUALIFIED_KNOCKOUT:{'icon': 'award',        'color': 'emerald', 'category': 'personal'},
    EVENT_OPPONENT_ASSIGNED:{'icon': 'crosshair',     'color': 'amber',   'category': 'personal'},
    EVENT_ADVANCED:         {'icon': 'trending-up',   'color': 'emerald', 'category': 'personal'},
    EVENT_ELIMINATED:       {'icon': 'x-circle',      'color': 'red',     'category': 'personal'},
}


def _evt(event_type: str, title: str, message: str, *,
         timestamp=None, urgent=False, scope='global') -> Dict[str, Any]:
    vis = VISUALS.get(event_type, {'icon': 'info', 'color': 'cyan', 'category': 'system'})
    return {
        'event_type': event_type,
        'title': title,
        'message': message,
        'icon': vis['icon'],
        'color': vis['color'],
        'category': vis['category'],
        'scope': scope,      # 'global' | 'personal'
        'urgent': urgent,
        'timestamp': timestamp or timezone.now(),
        'is_derived': True,   # marks as auto-generated, not manual
    }


# ── Main builder: global (TOC) events ───────────────────────────────────────
def derive_tournament_events(tournament, *, now=None) -> List[Dict[str, Any]]:
    """
    Derive lifecycle events from canonical tournament state.
    Returns global events suitable for TOC announcements tab.
    """
    now = now or timezone.now()
    events = []

    eff_status = (
        tournament.get_effective_status()
        if hasattr(tournament, 'get_effective_status')
        else getattr(tournament, 'status', '')
    )
    current_stage = (
        tournament.get_current_stage()
        if hasattr(tournament, 'get_current_stage')
        else None
    )
    is_gp = getattr(tournament, 'format', '') == 'group_playoff'

    # Lazy-load models to avoid circular imports
    from apps.brackets.models import Bracket
    from apps.tournaments.models.group import GroupStanding
    from apps.tournaments.models.match import Match

    # ── Status-derived events ──
    if eff_status in ('registration_closed', 'live', 'completed'):
        events.append(_evt(
            EVENT_REG_CLOSED,
            'Registrations Closed',
            'Registration window has ended. All confirmed participants are locked in.',
            timestamp=getattr(tournament, 'registration_end', None) or now,
        ))

    # Matches exist?
    match_qs = Match.objects.filter(tournament=tournament, is_deleted=False)
    total_matches = match_qs.count()
    if total_matches > 0:
        completed_matches = match_qs.filter(state__in=('completed', 'forfeit')).count()
        live_matches = match_qs.filter(state='live').count()
        scheduled_matches = match_qs.filter(
            state__in=('scheduled', 'check_in', 'ready'),
        ).count()

        events.append(_evt(
            EVENT_MATCHES_GENERATED,
            'Matches Generated',
            f'{total_matches} match{"es" if total_matches != 1 else ""} created for this tournament.',
            timestamp=getattr(tournament, 'tournament_start', None) or now,
        ))

        # Any scheduled with time → schedule published
        has_scheduled_times = match_qs.filter(
            scheduled_time__isnull=False,
        ).exists()
        if has_scheduled_times:
            events.append(_evt(
                EVENT_SCHEDULE_PUBLISHED,
                'Schedule Published',
                'Match schedule is available. Check the Matches tab for dates and times.',
                timestamp=getattr(tournament, 'tournament_start', None) or now,
            ))

        # Results recorded
        if completed_matches > 0:
            events.append(_evt(
                EVENT_RESULT_RECORDED,
                f'{completed_matches} Result{"s" if completed_matches != 1 else ""} Recorded',
                f'{completed_matches} of {total_matches} matches completed.',
            ))

    # GROUP_PLAYOFF specific
    if is_gp:
        # Group draw
        group_count = GroupStanding.objects.filter(
            group__tournament=tournament,
            group__is_deleted=False,
            is_deleted=False,
        ).values('group').distinct().count()
        if group_count > 0:
            events.append(_evt(
                EVENT_GROUP_DRAW,
                'Group Draw Completed',
                f'{group_count} group{"s" if group_count != 1 else ""} drawn. Participants seeded into groups.',
                timestamp=getattr(tournament, 'tournament_start', None) or now,
            ))

        # Group stage complete → knockout transition
        if current_stage == 'knockout_stage':
            events.append(_evt(
                EVENT_GROUP_COMPLETE,
                'Group Stage Completed',
                'All group matches concluded. Final standings locked.',
            ))

    # Bracket
    try:
        bracket = Bracket.objects.get(tournament=tournament)
        if bracket.is_finalized or (is_gp and current_stage == 'knockout_stage'):
            events.append(_evt(
                EVENT_BRACKET_PUBLISHED,
                'Bracket Published',
                f'{bracket.get_format_display()} bracket seeded and published.',
                timestamp=getattr(bracket, 'generated_at', None) or now,
            ))

        if current_stage == 'knockout_stage' and eff_status == 'live':
            ko_matches = match_qs.filter(bracket=bracket).count()
            events.append(_evt(
                EVENT_KNOCKOUT_LIVE,
                'Knockout Stage is Live',
                f'{ko_matches} knockout match{"es" if ko_matches != 1 else ""} in progress.',
            ))
    except Bracket.DoesNotExist:
        pass

    # Tournament completed
    if eff_status == 'completed':
        events.append(_evt(
            EVENT_TOURNAMENT_COMPLETED,
            'Tournament Completed',
            'All matches concluded. Final standings and prizes are available.',
            timestamp=getattr(tournament, 'cancelled_at', None)
            or getattr(tournament, 'tournament_end', None)
            or now,
        ))

    # Sort: newest timestamp first
    events.sort(key=lambda e: e['timestamp'] or now, reverse=True)
    return events


# ── Personal events for a specific participant ───────────────────────────────
def derive_participant_events(
    tournament, user=None, registration=None, *, now=None,
) -> List[Dict[str, Any]]:
    """
    Derive personalized lifecycle events for a specific participant.
    Suitable for HUB and Dashboard surfaces.
    """
    now = now or timezone.now()
    events = []

    if not user and not registration:
        return events

    from apps.tournaments.models.match import Match

    eff_status = (
        tournament.get_effective_status()
        if hasattr(tournament, 'get_effective_status')
        else getattr(tournament, 'status', '')
    )
    current_stage = (
        tournament.get_current_stage()
        if hasattr(tournament, 'get_current_stage')
        else None
    )
    is_gp = getattr(tournament, 'format', '') == 'group_playoff'

    # Build participant ID set for this user
    participant_ids = set()
    if registration:
        participant_ids.add(registration.id)
        if getattr(registration, 'team_id', None):
            participant_ids.add(registration.team_id)
    if user:
        participant_ids.add(user.id)
        # Also collect registration IDs
        try:
            from apps.tournaments.models.registration import Registration
            reg_ids = list(
                Registration.objects.filter(
                    tournament=tournament, user=user, is_deleted=False,
                ).values_list('id', flat=True)
            )
            participant_ids.update(reg_ids)
        except Exception:
            pass

    if not participant_ids:
        return events

    from django.db.models import Q
    q_me = Q(participant1_id__in=participant_ids) | Q(participant2_id__in=participant_ids)
    my_matches = Match.objects.filter(
        q_me, tournament=tournament, is_deleted=False,
    ).order_by('-scheduled_time')

    # Qualified to knockout (GP only)
    if is_gp and current_stage == 'knockout_stage':
        ko_matches = my_matches.filter(bracket__isnull=False).count()
        if ko_matches > 0:
            events.append(_evt(
                EVENT_QUALIFIED_KNOCKOUT,
                'Qualified for Knockout',
                'You advanced from group stage to the knockout bracket.',
                scope='personal',
            ))

    # Opponent assigned (next scheduled match)
    next_match = my_matches.filter(
        state__in=('scheduled', 'check_in', 'ready'),
    ).order_by('scheduled_time').first()

    if next_match:
        opp_name = _get_opponent_name(next_match, participant_ids)
        if opp_name and opp_name != 'TBD':
            events.append(_evt(
                EVENT_OPPONENT_ASSIGNED,
                'Opponent Assigned',
                f'You face {opp_name} in your next match.',
                scope='personal',
            ))

        # Lobby soon / open
        if next_match.scheduled_time:
            diff = (next_match.scheduled_time - now).total_seconds()
            if next_match.state == 'check_in':
                events.append(_evt(
                    EVENT_LOBBY_OPEN,
                    'Lobby is Open',
                    'Check in now to confirm your participation.',
                    scope='personal', urgent=True,
                ))
            elif next_match.state == 'ready':
                events.append(_evt(
                    EVENT_LOBBY_OPEN,
                    'Match Ready',
                    'Both sides checked in. Enter the match lobby.',
                    scope='personal', urgent=True,
                ))
            elif 0 < diff <= 1800:
                events.append(_evt(
                    EVENT_LOBBY_SOON,
                    'Lobby Opens Soon',
                    'Your match lobby opens in less than 30 minutes.',
                    scope='personal', urgent=True,
                ))

    # Completed matches — advanced / eliminated
    my_completed = my_matches.filter(state__in=('completed', 'forfeit'))
    wins = 0
    losses = 0
    for m in my_completed:
        if m.winner_id in participant_ids:
            wins += 1
        elif m.winner_id:
            losses += 1

    if wins > 0 and current_stage == 'knockout_stage':
        events.append(_evt(
            EVENT_ADVANCED,
            'Advanced in Bracket',
            f'Won {wins} knockout match{"es" if wins != 1 else ""}. Moving forward.',
            scope='personal',
        ))

    if losses > 0 and not next_match and current_stage == 'knockout_stage':
        events.append(_evt(
            EVENT_ELIMINATED,
            'Eliminated',
            'Your tournament run has ended. Check the bracket for final results.',
            scope='personal',
        ))

    # Lobby expired (missed check-in)
    missed = my_matches.filter(state='forfeit').exclude(
        winner_id__in=participant_ids,
    )
    if missed.exists():
        events.append(_evt(
            EVENT_LOBBY_EXPIRED,
            'Lobby Expired',
            'You missed the check-in window for a match.',
            scope='personal',
        ))

    return events


def _get_opponent_name(match, my_ids: set) -> str:
    if match.participant1_id in my_ids:
        return match.participant2_name or 'TBD'
    return match.participant1_name or 'TBD'
