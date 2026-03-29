"""
Match reminder notification task.

Periodic Celery task that fires participant reminders at:
- ~60 minutes before start
- ~20 minutes before start
- ~5 minutes before start

Beat schedule: every 5 minutes (registered in deltacrown/celery.py).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, Tuple

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Reminder windows: (event_name, lower_bound_minutes, upper_bound_minutes, marker_key)
REMINDER_WINDOWS: Tuple[Tuple[str, int, int, str], ...] = (
    ('match_reminder_1h', 55, 65, 'm60'),
    ('match_reminder_20m', 17, 23, 'm20'),
    ('match_ready', 3, 8, 'm05'),
)

SUPPORT_WINDOW_MINUTES = min(window[1] for window in REMINDER_WINDOWS)
SUPPORT_WINDOW_MAX_MINUTES = max(window[2] for window in REMINDER_WINDOWS)

# States where reminders are irrelevant.
SKIP_STATES = {'live', 'pending_result', 'completed', 'disputed', 'forfeit', 'cancelled'}
REMINDER_MARKERS_KEY = 'auto_reminder_marks'


def _in_window(minutes_until: int, lower: int, upper: int) -> bool:
    return lower <= minutes_until <= upper


def _marker_signature(marker_key: str, scheduled_time) -> str:
    normalized_dt = scheduled_time
    try:
        normalized_dt = scheduled_time.replace(second=0, microsecond=0)
    except Exception:
        pass
    return f"{marker_key}:{normalized_dt.isoformat()}"


@shared_task(
    name='apps.tournaments.tasks.notify_match_ready',
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    ignore_result=True,
)
def notify_match_ready(self):
    return run_match_ready_reminder_sweep()


def run_match_ready_reminder_sweep(now=None):
    """Scan candidate matches and fire windowed reminder notifications."""
    from apps.tournaments.api.toc.brackets_service import TOCBracketsService
    from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
    from apps.tournaments.models.match import Match

    now = now or timezone.now()
    window_start = now + timedelta(minutes=SUPPORT_WINDOW_MINUTES)
    window_end = now + timedelta(minutes=SUPPORT_WINDOW_MAX_MINUTES)

    upcoming = Match.objects.filter(
        scheduled_time__gte=window_start,
        scheduled_time__lte=window_end,
        is_deleted=False,
    ).exclude(
        state__in=list(SKIP_STATES),
    ).select_related('tournament').order_by('tournament_id', 'scheduled_time')

    counters: Dict[str, int] = {event_name: 0 for event_name, *_ in REMINDER_WINDOWS}

    for match in upcoming.iterator():
        tournament = match.tournament
        if not tournament or tournament.status not in ('live', 'registration_closed'):
            continue

        try:
            target_user_ids = TOCBracketsService._match_participant_user_ids(tournament, match)
            if not target_user_ids:
                continue

            minutes_until = max(
                0,
                int((match.scheduled_time - now).total_seconds() // 60),
            ) if match.scheduled_time else SUPPORT_WINDOW_MINUTES

            raw_lobby = match.lobby_info if isinstance(match.lobby_info, dict) else {}
            lobby_info = dict(raw_lobby)
            markers = lobby_info.get(REMINDER_MARKERS_KEY)
            if not isinstance(markers, dict):
                markers = {}

            marker_changed = False
            for event_name, lower, upper, marker_key in REMINDER_WINDOWS:
                if not _in_window(minutes_until, lower, upper):
                    continue

                signature = _marker_signature(marker_key, match.scheduled_time)
                if markers.get(marker_key) == signature:
                    continue

                TOCNotificationsService.fire_auto_event(
                    tournament,
                    event_name,
                    {
                        'target_user_ids': target_user_ids,
                        'match_id': match.id,
                        'round': match.round_number,
                        'match_number': match.match_number,
                        'participant1': match.participant1_name or str(match.participant1_id),
                        'participant2': match.participant2_name or str(match.participant2_id),
                        'scheduled_time': str(match.scheduled_time),
                        'minutes_until': minutes_until,
                        'force_email': True,
                        'dedupe': False,
                        'url': f'/tournaments/{tournament.slug}/hub/',
                    },
                )

                markers[marker_key] = signature
                marker_changed = True
                counters[event_name] += 1

                logger.info(
                    "[match_reminder] event=%s tournament=%s match=%s (R%d M%d) @ %s",
                    event_name,
                    tournament.slug,
                    match.id,
                    match.round_number,
                    match.match_number,
                    match.scheduled_time,
                )

            if marker_changed:
                lobby_info[REMINDER_MARKERS_KEY] = markers
                match.lobby_info = lobby_info
                match.save(update_fields=['lobby_info', 'updated_at'])
        except Exception as exc:
            logger.warning(
                "[match_reminder] Failed for match %s in %s: %s",
                match.id,
                tournament.slug,
                exc,
            )

    total_sent = sum(counters.values())
    if total_sent:
        logger.info("[match_reminder] Fired %d reminder notification(s): %s", total_sent, counters)

    return {'notified': total_sent, 'windows': counters}
