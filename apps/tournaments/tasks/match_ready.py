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
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from celery import shared_task
from django.db import transaction
from django.db.models import Q
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
# Claims: {marker_key: {'sig', 'token', 'at', 'attempts', 'state', 'error'}}.
# state: 'sending' (lease CLAIM_TTL_SECONDS), 'failed' (retry after FAILURE_RETRY_SECONDS,
# no send is active), 'abandoned' (MAX_ATTEMPTS exhausted; operator-visible, never retried).
REMINDER_CLAIMS_KEY = 'auto_reminder_claims'
CLAIM_TTL_SECONDS = 180
FAILURE_RETRY_SECONDS = 30
MAX_ATTEMPTS = 3

# Candidates are read in keyset pages (stable order, bounded memory) so handled matches
# at the front cannot starve later ones. Limits bound work per sweep; a single
# notification call may still run longer than the soft time budget.
SWEEP_PAGE_SIZE = 100
SWEEP_ACTION_LIMIT = 100      # dispatches started per sweep (non-actionable candidates do not count)
SWEEP_SCAN_LIMIT = 2000       # matches examined per sweep; a cursor resumes after it next time
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


def _claim_age_seconds(claim, now) -> float:
    """Seconds since the claim was written; malformed data counts as long expired."""
    try:
        return (now - datetime.fromisoformat(claim.get('at'))).total_seconds()
    except (AttributeError, TypeError, ValueError):
        return float('inf')


def _claim_attempts(claim) -> int:
    try:
        return max(int(claim.get('attempts', 1)), 1)
    except (AttributeError, TypeError, ValueError):
        return 1


def _locked_match(match_id):
    from apps.tournaments.models.match import Match

    return Match.objects.select_for_update().filter(pk=match_id, is_deleted=False).first()


def _claim_reminder(match_id, marker_key, signature, now) -> Tuple[Optional[str], str]:
    """Atomically claim one reminder. Returns (token, reason); token is None if not claimed.

    Re-validates under the row lock, so a match cancelled, completed, started or
    rescheduled since the scan is not reminded (rescheduling changes the signature).
    """
    with transaction.atomic():
        match = _locked_match(match_id)
        if match is None or match.state in SKIP_STATES or not match.scheduled_time:
            return None, 'stale'
        if match.scheduled_time <= now or _marker_signature(marker_key, match.scheduled_time) != signature:
            return None, 'stale'

        lobby = _lobby_parts(match.lobby_info)
        if lobby[REMINDER_MARKERS_KEY].get(marker_key) == signature:
            return None, 'done'

        attempts, reason = 1, 'claimed'
        claim = lobby[REMINDER_CLAIMS_KEY].get(marker_key)
        if isinstance(claim, dict) and claim.get('sig') == signature:
            state = claim.get('state')
            if state == 'abandoned':
                return None, 'abandoned'
            wait = FAILURE_RETRY_SECONDS if state == 'failed' else CLAIM_TTL_SECONDS
            if _claim_age_seconds(claim, now) < wait:
                return None, 'in_progress'
            attempts = _claim_attempts(claim) + 1
            reason = 'retry' if state == 'failed' else 'reclaimed'
            if attempts > MAX_ATTEMPTS:
                claim = dict(claim, state='abandoned', at=now.isoformat())
                lobby[REMINDER_CLAIMS_KEY][marker_key] = claim
                match.lobby_info = lobby
                match.save(update_fields=['lobby_info', 'updated_at'])
                return None, 'gave_up'
        elif claim is not None and not isinstance(claim, dict):
            reason = 'reclaimed'  # malformed persisted claim: start over

        token = uuid.uuid4().hex
        lobby[REMINDER_CLAIMS_KEY][marker_key] = {
            'sig': signature, 'token': token, 'at': now.isoformat(),
            'attempts': attempts, 'state': 'sending',
        }
        match.lobby_info = lobby
        match.save(update_fields=['lobby_info', 'updated_at'])
        return token, reason


def _finalize_reminder(match_id, marker_key, signature, token) -> str:
    """Record the send only if this worker still owns the current claim.

    Returns 'sent', or 'stale' when the match was rescheduled/cancelled/started, or the
    claim was replaced or removed (an expired worker finishing late). A stale completion
    changes nothing; the external send it made cannot be recalled.
    """
    with transaction.atomic():
        match = _locked_match(match_id)
        if match is None or match.state in SKIP_STATES or not match.scheduled_time:
            return 'stale'
        if _marker_signature(marker_key, match.scheduled_time) != signature:
            return 'stale'
        lobby = _lobby_parts(match.lobby_info)
        claim = lobby[REMINDER_CLAIMS_KEY].get(marker_key)
        if not (isinstance(claim, dict) and claim.get('sig') == signature and claim.get('token') == token):
            return 'stale'
        lobby[REMINDER_MARKERS_KEY][marker_key] = signature
        lobby[REMINDER_CLAIMS_KEY].pop(marker_key, None)
        match.lobby_info = lobby
        match.save(update_fields=['lobby_info', 'updated_at'])
        return 'sent'


def _record_failure(match_id, marker_key, signature, token, error, now) -> None:
    """Mark our own claim failed so it can be retried soon (no send is active)."""
    with transaction.atomic():
        match = _locked_match(match_id)
        if match is None:
            return
        lobby = _lobby_parts(match.lobby_info)
        claim = lobby[REMINDER_CLAIMS_KEY].get(marker_key)
        if isinstance(claim, dict) and claim.get('sig') == signature and claim.get('token') == token:
            lobby[REMINDER_CLAIMS_KEY][marker_key] = dict(
                claim, state='failed', at=now.isoformat(), error=str(error)[:200],
            )
            match.lobby_info = lobby
            match.save(update_fields=['lobby_info', 'updated_at'])


def _claim_blocked(claim, signature, now):
    """Advisory, lock-free check on already-loaded data: why this reminder is not actionable now.

    Lets the sweep skip persistently claimed/abandoned reminders without a participant lookup
    or a row lock. The authoritative decision is still made in _claim_reminder under the lock.
    """
    if not (isinstance(claim, dict) and claim.get('sig') == signature):
        return None
    state = claim.get('state')
    if state == 'abandoned':
        return 'abandoned'
    wait = FAILURE_RETRY_SECONDS if state == 'failed' else CLAIM_TTL_SECONDS
    return 'in_progress' if _claim_age_seconds(claim, now) < wait else None


# Fairness hint: where the previous sweep stopped. Losing it (cache restart/outage) only
# restarts scanning from the front; it never affects correctness or claims.
CURSOR_CACHE_KEY = 'match_reminder_sweep_cursor'
CURSOR_TTL_SECONDS = 3600


def _load_cursor():
    from django.core.cache import cache

    try:
        value = cache.get(CURSOR_CACHE_KEY)
        return (datetime.fromisoformat(value[0]), int(value[1])) if value else None
    except Exception:
        return None


def _store_cursor(position):
    from django.core.cache import cache

    try:
        if position is None:
            cache.delete(CURSOR_CACHE_KEY)
        else:
            cache.set(CURSOR_CACHE_KEY, (position[0].isoformat(), position[1]), CURSOR_TTL_SECONDS)
    except Exception:
        logger.warning("[match_reminder] Could not persist sweep cursor", exc_info=True)


def _candidate_pages(window_start, window_end, after=None, until=None):
    """Yield pages of candidate matches in stable (scheduled_time, id) order.

    `after`/`until` are (scheduled_time, id) positions: exclusive start / inclusive end.
    """
    from apps.tournaments.models.match import Match

    base = Match.objects.filter(
        scheduled_time__gte=window_start,
        scheduled_time__lte=window_end,
        is_deleted=False,
    ).exclude(state__in=list(SKIP_STATES)).select_related('tournament').order_by('scheduled_time', 'id')
    if until is not None:
        base = base.filter(Q(scheduled_time__lt=until[0]) | Q(scheduled_time=until[0], id__lte=until[1]))

    last = after
    while True:
        qs = base
        if last is not None:
            qs = qs.filter(Q(scheduled_time__gt=last[0]) | Q(scheduled_time=last[0], id__gt=last[1]))
        page = list(qs[:SWEEP_PAGE_SIZE])
        if not page:
            return
        yield page
        if len(page) < SWEEP_PAGE_SIZE:
            return
        last = (page[-1].scheduled_time, page[-1].id)


def run_match_ready_reminder_sweep(now=None):
    """Scan candidate matches and fire windowed reminder notifications.

    Safe to run concurrently and repeatedly: each (match, window, scheduled time) is
    claimed under a row lock with a unique token, sent outside any transaction, then
    marked sent only if the token still owns the claim. A failed send keeps a retryable
    claim (up to MAX_ATTEMPTS, then 'abandoned').

    Delivery is at-least-once, never exactly-once. A send may repeat after a crash between
    send and marker commit, after a lease expiry while the first send is still running, or
    after a failure part-way through a recipient batch. "Sent" means the notification was
    persisted and the email backend accepted (or the email was skipped); it does not prove
    inbox delivery, and a send already started cannot be recalled if the match is cancelled.
    The time budget is soft: it is checked between matches, so one slow call can overrun it.
    """
    from apps.tournaments.api.toc.brackets_service import TOCBracketsService
    from apps.tournaments.api.toc.notifications_service import TOCNotificationsService

    started = time.monotonic()
    now = now or timezone.now()
    window_start = now + timedelta(minutes=SUPPORT_WINDOW_MINUTES)
    window_end = now + timedelta(minutes=SUPPORT_WINDOW_MAX_MINUTES)

    counters: Dict[str, int] = {event_name: 0 for event_name, *_ in REMINDER_WINDOWS}
    # scanned  = candidates examined; skipped = due reminders that were not actionable (claimed,
    # abandoned, stale, done); attempted = dispatches actually started (claims acquired).
    # Only dispatches count against SWEEP_ACTION_LIMIT, so non-actionable candidates cannot
    # starve actionable ones; they only consume the scan budget (see the cursor below).
    stats = {
        'scanned': 0, 'attempted': 0, 'skipped': 0, 'failed': 0, 'in_progress': 0, 'reclaimed': 0,
        'gave_up': 0, 'abandoned': 0, 'stale_completions': 0, 'suppressed': 0,
        'email_failed': 0, 'deferred': False,
    }
    truncated = False
    last_examined = None

    def _scan_budget_hit() -> bool:
        return (
            stats['scanned'] >= SWEEP_SCAN_LIMIT
            or time.monotonic() - started > SWEEP_TIME_BUDGET_SECONDS
        )

    def _dispatch_due(match, tournament, due, target_user_ids, minutes_until):
        for event_name, _lower, _upper, marker_key in due:
            if stats['attempted'] >= SWEEP_ACTION_LIMIT:
                return
            signature = _marker_signature(marker_key, match.scheduled_time)
            token = None
            try:
                token, reason = _claim_reminder(match.id, marker_key, signature, now)
                if token is None:
                    stats['skipped'] += 1
                    if reason in ('in_progress', 'abandoned', 'gave_up'):
                        stats[reason] += 1
                    if reason == 'gave_up':
                        logger.error(
                            "[match_reminder] Abandoned after %d attempts: match=%s window=%s",
                            MAX_ATTEMPTS, match.id, marker_key,
                        )
                    continue
                stats['attempted'] += 1
                if reason in ('reclaimed', 'retry'):
                    stats['reclaimed'] += 1
                    logger.warning(
                        "[match_reminder] Re-sending (%s): match=%s window=%s", reason, match.id, marker_key,
                    )

                # Sent outside any transaction; strict makes dispatch failures raise.
                delivery = TOCNotificationsService.fire_auto_event(
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
                if _finalize_reminder(match.id, marker_key, signature, token) != 'sent':
                    stats['stale_completions'] += 1
                    logger.warning(
                        "[match_reminder] Stale completion ignored (rescheduled, replaced claim or no "
                        "longer relevant); the send may already have happened: match=%s window=%s",
                        match.id, marker_key,
                    )
                    continue
                delivery = delivery or {}
                if not (delivery.get('created') or delivery.get('email_sent')):
                    stats['suppressed'] += 1  # disabled by organizer / no rule / nobody to notify
                    continue
                counters[event_name] += 1
                if delivery.get('email_failed'):
                    # In-app rows are persisted; retrying would duplicate them, so this is
                    # recorded as sent with a visible email failure count.
                    stats['email_failed'] += delivery['email_failed']
                    logger.warning(
                        "[match_reminder] %d email(s) rejected by the backend: match=%s window=%s",
                        delivery['email_failed'], match.id, marker_key,
                    )
                logger.info(
                    "[match_reminder] event=%s tournament=%s match=%s (R%d M%d) @ %s",
                    event_name, tournament.slug, match.id,
                    match.round_number, match.match_number, match.scheduled_time,
                )
            except Exception as exc:
                stats['failed'] += 1
                logger.exception(
                    "[match_reminder] Dispatch failed (will retry): match=%s window=%s",
                    match.id, marker_key,
                )
                if token:
                    try:
                        _record_failure(match.id, marker_key, signature, token, exc, now)
                    except Exception:
                        logger.exception("[match_reminder] Could not record failure for match %s", match.id)

    # Resume after the position where a previous truncated sweep stopped, then wrap around to
    # the front, so repeated sweeps eventually cover every candidate in the window.
    cursor = _load_cursor()
    passes = [(cursor, None), (None, cursor)] if cursor else [(None, None)]

    for after, until in passes:
        for page in _candidate_pages(window_start, window_end, after=after, until=until):
            for match in page:
                if _scan_budget_hit():
                    truncated = True
                    break
                stats['scanned'] += 1
                last_examined = (match.scheduled_time, match.id)
                tournament = match.tournament
                if not tournament or tournament.status not in ('live', 'registration_closed'):
                    continue

                try:
                    minutes_until = max(0, int((match.scheduled_time - now).total_seconds() // 60))
                    lobby = _lobby_parts(match.lobby_info)
                    due = []
                    for window in REMINDER_WINDOWS:
                        _event, lower, upper, key = window
                        signature = _marker_signature(key, match.scheduled_time)
                        if not _in_window(minutes_until, lower, upper) or lobby[REMINDER_MARKERS_KEY].get(key) == signature:
                            continue
                        blocked = _claim_blocked(lobby[REMINDER_CLAIMS_KEY].get(key), signature, now)
                        if blocked:
                            stats['skipped'] += 1
                            stats[blocked] += 1
                            continue
                        due.append(window)
                    if not due:
                        continue
                    target_user_ids = TOCBracketsService._match_participant_user_ids(tournament, match)
                    if not target_user_ids:
                        continue
                except Exception:
                    stats['failed'] += 1
                    logger.exception("[match_reminder] Failed to prepare match %s", match.id)
                    continue

                _dispatch_due(match, tournament, due, target_user_ids, minutes_until)
                if stats['attempted'] >= SWEEP_ACTION_LIMIT:
                    truncated = True
                    break
            if truncated:
                break
        if truncated:
            break

    _store_cursor(last_examined if truncated else None)
    stats['deferred'] = truncated
    total_sent = sum(counters.values())
    if total_sent or stats['failed'] or stats['gave_up'] or stats['stale_completions'] or truncated:
        noisy = stats['failed'] or stats['gave_up'] or stats['stale_completions'] or truncated
        (logger.warning if noisy else logger.info)(
            "[match_reminder] sent=%d %s %s", total_sent, counters, stats,
        )

    return {'notified': total_sent, 'windows': counters, 'truncated': truncated, **stats}
