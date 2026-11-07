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
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple

from celery import shared_task
from django.db import transaction
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
# In-flight claims: {marker_key: {'sig', 'at', 'attempts'}}. A claim is taken under a row lock
# before sending, so concurrent sweeps (cron + thread, overlapping deploy instances) skip it.
REMINDER_CLAIMS_KEY = 'auto_reminder_claims'
CLAIM_TTL_SECONDS = 180      # an unfinished claim becomes retryable after this
MAX_ATTEMPTS = 3             # then give up for this match/window/time
SWEEP_MATCH_LIMIT = 100      # matches examined per sweep
SWEEP_TIME_BUDGET_SECONDS = 40


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


def _lobby_parts(lobby_info):
    lobby = dict(lobby_info) if isinstance(lobby_info, dict) else {}
    marks = lobby.get(REMINDER_MARKERS_KEY)
    claims = lobby.get(REMINDER_CLAIMS_KEY)
    lobby[REMINDER_MARKERS_KEY] = dict(marks) if isinstance(marks, dict) else {}
    lobby[REMINDER_CLAIMS_KEY] = dict(claims) if isinstance(claims, dict) else {}
    return lobby


def _claim_reminder(match_id, marker_key, signature, now):
    """Atomically claim one reminder. Returns (claimed, reason).

    Re-validates under the row lock, so a match cancelled, completed, started or
    rescheduled since the scan is not reminded (rescheduling changes the signature).
    """
    from apps.tournaments.models.match import Match

    with transaction.atomic():
        match = Match.objects.select_for_update().filter(pk=match_id, is_deleted=False).first()
        if match is None or match.state in SKIP_STATES or not match.scheduled_time:
            return False, 'stale'
        if match.scheduled_time <= now or _marker_signature(marker_key, match.scheduled_time) != signature:
            return False, 'stale'

        lobby = _lobby_parts(match.lobby_info)
        if lobby[REMINDER_MARKERS_KEY].get(marker_key) == signature:
            return False, 'done'

        attempts = 1
        claim = lobby[REMINDER_CLAIMS_KEY].get(marker_key)
        if isinstance(claim, dict) and claim.get('sig') == signature:
            try:
                age = (now - datetime.fromisoformat(claim.get('at'))).total_seconds()
            except (TypeError, ValueError):
                age = CLAIM_TTL_SECONDS + 1
            if age < CLAIM_TTL_SECONDS:
                return False, 'in_progress'
            attempts = int(claim.get('attempts', 1)) + 1
            if attempts > MAX_ATTEMPTS:
                return False, 'gave_up'

        lobby[REMINDER_CLAIMS_KEY][marker_key] = {
            'sig': signature, 'at': now.isoformat(), 'attempts': attempts,
        }
        match.lobby_info = lobby
        match.save(update_fields=['lobby_info', 'updated_at'])
        return True, 'claimed'


def _mark_reminder_sent(match_id, marker_key, signature):
    """Persist the sent marker under a row lock, re-reading so other lobby_info data is kept."""
    from apps.tournaments.models.match import Match

    with transaction.atomic():
        match = Match.objects.select_for_update().filter(pk=match_id).first()
        if match is None:
            return
        lobby = _lobby_parts(match.lobby_info)
        lobby[REMINDER_MARKERS_KEY][marker_key] = signature
        lobby[REMINDER_CLAIMS_KEY].pop(marker_key, None)
        match.lobby_info = lobby
        match.save(update_fields=['lobby_info', 'updated_at'])


def run_match_ready_reminder_sweep(now=None):
    """Scan candidate matches and fire windowed reminder notifications.

    Safe to run concurrently and repeatedly: each (match, window, scheduled time) is
    claimed under a row lock, sent outside any transaction, then marked sent. A failed
    send leaves the claim, which is retried after CLAIM_TTL_SECONDS (up to MAX_ATTEMPTS).
    Delivery is at-least-once: a crash after the send but before the marker commits, or a
    failure part-way through a recipient batch, can re-send to some recipients on retry.
    """
    from apps.tournaments.api.toc.brackets_service import TOCBracketsService
    from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
    from apps.tournaments.models.match import Match

    started = time.monotonic()
    now = now or timezone.now()
    window_start = now + timedelta(minutes=SUPPORT_WINDOW_MINUTES)
    window_end = now + timedelta(minutes=SUPPORT_WINDOW_MAX_MINUTES)

    candidates = list(
        Match.objects.filter(
            scheduled_time__gte=window_start,
            scheduled_time__lte=window_end,
            is_deleted=False,
        ).exclude(
            state__in=list(SKIP_STATES),
        ).select_related('tournament').order_by('scheduled_time', 'id')[:SWEEP_MATCH_LIMIT + 1]
    )
    truncated = len(candidates) > SWEEP_MATCH_LIMIT
    candidates = candidates[:SWEEP_MATCH_LIMIT]

    counters: Dict[str, int] = {event_name: 0 for event_name, *_ in REMINDER_WINDOWS}
    stats = {'scanned': 0, 'failed': 0, 'in_progress': 0, 'gave_up': 0, 'deferred': 0}

    for index, match in enumerate(candidates):
        if time.monotonic() - started > SWEEP_TIME_BUDGET_SECONDS:
            stats['deferred'] = len(candidates) - index
            break
        stats['scanned'] += 1

        tournament = match.tournament
        if not tournament or tournament.status not in ('live', 'registration_closed'):
            continue

        try:
            minutes_until = max(0, int((match.scheduled_time - now).total_seconds() // 60))
            markers = _lobby_parts(match.lobby_info)[REMINDER_MARKERS_KEY]
            due = [
                w for w in REMINDER_WINDOWS
                if _in_window(minutes_until, w[1], w[2])
                and markers.get(w[3]) != _marker_signature(w[3], match.scheduled_time)
            ]
            if not due:
                continue

            target_user_ids = TOCBracketsService._match_participant_user_ids(tournament, match)
            if not target_user_ids:
                continue
        except Exception:
            stats['failed'] += 1
            logger.exception("[match_reminder] Failed to prepare match %s", match.id)
            continue

        for event_name, _lower, _upper, marker_key in due:
            signature = _marker_signature(marker_key, match.scheduled_time)
            try:
                claimed, reason = _claim_reminder(match.id, marker_key, signature, now)
                if not claimed:
                    if reason in ('in_progress', 'gave_up'):
                        stats[reason] += 1
                        if reason == 'gave_up':
                            logger.error(
                                "[match_reminder] Giving up after %d attempts: match=%s window=%s",
                                MAX_ATTEMPTS, match.id, marker_key,
                            )
                    continue

                # Sent outside any transaction; strict makes dispatch failures raise.
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
                        'strict': True,
                        'url': f'/tournaments/{tournament.slug}/hub/',
                    },
                )
                _mark_reminder_sent(match.id, marker_key, signature)
                counters[event_name] += 1
                logger.info(
                    "[match_reminder] event=%s tournament=%s match=%s (R%d M%d) @ %s",
                    event_name, tournament.slug, match.id,
                    match.round_number, match.match_number, match.scheduled_time,
                )
            except Exception:
                stats['failed'] += 1
                logger.exception(
                    "[match_reminder] Dispatch failed (will retry): match=%s window=%s",
                    match.id, marker_key,
                )

    total_sent = sum(counters.values())
    if total_sent or stats['failed']:
        log = logger.warning if stats['failed'] else logger.info
        log("[match_reminder] sent=%d %s %s truncated=%s", total_sent, counters, stats, truncated)

    return {'notified': total_sent, 'windows': counters, 'truncated': truncated, **stats}
