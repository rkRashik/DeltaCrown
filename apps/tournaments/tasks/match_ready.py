"""
Match Ready Notification Task.

Periodic Celery task that fires 5-minute pre-match alerts to match participants.

Beat schedule: every 5 minutes (registered in deltacrown/celery.py).

Algorithm:
- Find all matches with scheduled_time in [now+3min, now+8min] window
- This 5-minute window, swept every 5 minutes, ensures each match is
  notified approximately once (standard time-window deduplication)
- Skip matches already in terminal states or that have been live
- Fire fire_auto_event('match_ready') per tournament with match context
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Window: notify matches scheduled 3–8 minutes from now
NOTIFY_WINDOW_MIN_MINUTES = 3
NOTIFY_WINDOW_MAX_MINUTES = 8

# States where notification is irrelevant (already started or done)
SKIP_STATES = {'live', 'pending_result', 'completed', 'disputed', 'forfeit', 'cancelled'}


@shared_task(
    name='apps.tournaments.tasks.notify_match_ready',
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    ignore_result=True,
)
def notify_match_ready(self):
    """
    Scan for matches starting in 3–8 minutes and fire match_ready notifications.

    Runs every 5 minutes via Celery Beat.
    """
    from apps.tournaments.models.match import Match
    from apps.tournaments.api.toc.notifications_service import TOCNotificationsService

    now = timezone.now()
    window_start = now + timezone.timedelta(minutes=NOTIFY_WINDOW_MIN_MINUTES)
    window_end = now + timezone.timedelta(minutes=NOTIFY_WINDOW_MAX_MINUTES)

    upcoming = Match.objects.filter(
        scheduled_time__gte=window_start,
        scheduled_time__lte=window_end,
        is_deleted=False,
    ).exclude(
        state__in=list(SKIP_STATES),
    ).select_related('tournament').order_by('tournament_id', 'scheduled_time')

    count = 0
    for match in upcoming.iterator():
        tournament = match.tournament
        if not tournament or tournament.status not in ('live', 'registration_closed'):
            continue

        try:
            TOCNotificationsService.fire_auto_event(
                tournament,
                'match_ready',
                {
                    'match_id': match.id,
                    'round': match.round_number,
                    'match_number': match.match_number,
                    'participant1': match.participant1_name or str(match.participant1_id),
                    'participant2': match.participant2_name or str(match.participant2_id),
                    'scheduled_time': str(match.scheduled_time),
                    'minutes_until': NOTIFY_WINDOW_MIN_MINUTES,
                },
            )
            count += 1
            logger.info(
                "[match_ready] Notified: tournament=%s match=%s (R%d M%d) @ %s",
                tournament.slug,
                match.id,
                match.round_number,
                match.match_number,
                match.scheduled_time,
            )
        except Exception as exc:
            logger.warning(
                "[match_ready] Failed for match %s in %s: %s",
                match.id,
                tournament.slug,
                exc,
            )

    if count:
        logger.info("[match_ready] Fired %d match_ready notification(s)", count)

    return {'notified': count}
