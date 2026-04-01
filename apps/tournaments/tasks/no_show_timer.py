"""
No-Show Timer / Auto-DQ Task
=============================
Runs every 2 minutes. For each tournament with `enable_no_show_timer=True`,
finds READY/LIVE matches whose scheduled_time has passed the configured
`no_show_timeout_minutes` window and auto-forfeits them.

Logic:
  - deadline = scheduled_time + no_show_timeout_minutes
  - If now > deadline and match is still READY or LIVE  → auto-forfeit
  - Winner is the participant that *did* check in; if both missed → cancel
  - Audit trail stored in match.lobby_info['no_show_auto_dq']
  - Fires 'match_forfeit' notification event per forfeit issued
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.tournaments.tasks.check_no_show_matches', bind=True, max_retries=1)
def check_no_show_matches(self):
    """
    Celery beat task — auto-forfeit no-show matches.

    Beat schedule: every 2 minutes (see deltacrown/celery.py).
    """
    from apps.tournaments.models import Match, Tournament
    from apps.tournaments.services.match_service import MatchService

    now = timezone.now()
    forfeit_count = 0
    cancel_count = 0
    error_count = 0

    # Only query tournaments with no-show timer enabled and currently active
    active_tournaments = Tournament.objects.filter(
        enable_no_show_timer=True,
        status__in=['registration_open', 'registration_closed', 'check_in', 'live'],
    ).values_list('id', 'no_show_timeout_minutes')

    if not active_tournaments:
        return {'checked': 0, 'forfeited': 0, 'cancelled': 0}

    # Build per-tournament timeout map
    timeout_map = {t_id: mins for t_id, mins in active_tournaments}
    tournament_ids = list(timeout_map.keys())

    # Get candidate matches: READY or LIVE, with a scheduled_time set
    candidates = Match.objects.filter(
        tournament_id__in=tournament_ids,
        state__in=[Match.READY, Match.LIVE],
        scheduled_time__isnull=False,
    ).select_related('tournament').order_by('tournament_id', 'scheduled_time')

    processed_ids = set()

    for match in candidates:
        if match.id in processed_ids:
            continue

        timeout_mins = timeout_map.get(match.tournament_id, 5)
        deadline = match.scheduled_time + timedelta(minutes=timeout_mins)

        if now <= deadline:
            continue  # Still within window

        processed_ids.add(match.id)

        try:
            with transaction.atomic():
                _auto_forfeit_match(match, now)

            # Determine outcome for counters
            if match.state == Match.CANCELLED:
                cancel_count += 1
            else:
                forfeit_count += 1

        except Exception as exc:
            error_count += 1
            logger.warning(
                'no_show_timer: failed to process match %s (%s): %s',
                match.id, match.state, exc
            )

    logger.info(
        'no_show_timer: checked=%d forfeited=%d cancelled=%d errors=%d',
        len(processed_ids), forfeit_count, cancel_count, error_count
    )
    return {
        'checked': len(processed_ids),
        'forfeited': forfeit_count,
        'cancelled': cancel_count,
        'errors': error_count,
    }


def _auto_forfeit_match(match, now):
    """
    Determine which participant(s) no-showed and apply forfeit or cancel.

    Uses check-in flags (participant1_checked_in / participant2_checked_in).
    If both failed to check in → cancel the match instead of forfeiting.
    """
    from apps.tournaments.models import Match
    from apps.tournaments.services.match_service import MatchService

    p1_ok = bool(match.participant1_checked_in)
    p2_ok = bool(match.participant2_checked_in)

    # Both missed — cancel (no winner is fair)
    if not p1_ok and not p2_ok:
        match.state = Match.CANCELLED
        if not isinstance(match.lobby_info, dict):
            match.lobby_info = {}
        match.lobby_info['no_show_auto_dq'] = True
        match.lobby_info['no_show_reason'] = 'both_no_show'
        match.lobby_info['no_show_at'] = now.isoformat()
        match.completed_at = now
        match.save(update_fields=['state', 'lobby_info', 'completed_at'])
        _fire_notification(match, 'match_cancelled', 'both_no_show')
        return

    # Exactly one participant no-showed → forfeit them
    forfeiting_id = None
    if not p1_ok and p2_ok:
        forfeiting_id = match.participant1_id
    elif p1_ok and not p2_ok:
        forfeiting_id = match.participant2_id

    # Reload to avoid stale state conflicts
    match.refresh_from_db()
    if match.state not in [Match.READY, Match.LIVE]:
        return  # Race condition: already resolved

    updated = MatchService.forfeit_match(
        match=match,
        reason='no_show_auto_dq',
        forfeiting_participant_id=forfeiting_id,
    )
    # Stamp audit trail
    if not isinstance(updated.lobby_info, dict):
        updated.lobby_info = {}
    updated.lobby_info['no_show_auto_dq'] = True
    updated.lobby_info['no_show_at'] = now.isoformat()
    updated.save(update_fields=['lobby_info'])

    _fire_notification(updated, 'match_forfeit', 'no_show')


def _fire_notification(match, event: str, reason: str):
    """Silently fire a TOC auto-notification for the match forfeit/cancel."""
    try:
        from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
        context = {
            'match_id': match.id,
            'round': match.round_number,
            'match_number': match.match_number,
            'participant1': getattr(match, 'participant1_name', 'TBD'),
            'participant2': getattr(match, 'participant2_name', 'TBD'),
            'reason': reason,
            'winner_id': getattr(match, 'winner_id', None),
        }
        TOCNotificationsService.fire_auto_event(match.tournament, event, context)
    except Exception as exc:
        logger.debug('no_show_timer: notification failed: %s', exc)
