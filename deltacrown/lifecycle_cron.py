"""
Free-Tier Lifecycle Cron Endpoint
=================================
Lightweight HTTP endpoint that replaces Celery Beat for critical tournament
lifecycle tasks on Render free/starter tier (512 MB RAM).

Designed to be called every 2-5 minutes by an external free cron service
(e.g., cron-job.org, UptimeRobot, or Render Cron Job).

Security:
    Requires ``Authorization: Bearer <CRON_SECRET>`` header.
    The CRON_SECRET env var must be set in Render dashboard.

Tasks executed (in order):
    1. auto_advance_tournaments — status transitions based on date thresholds
    2. check_tournament_wrapup — LIVE → COMPLETED when all matches done
    3. check_no_show_matches — auto-forfeit no-show matches
    4. auto_close_expired_lobbies — close expired match lobbies
    5. expire_overdue_payments — cancel unpaid registrations
    6. reconcile_group_playoff_transitions — fix stuck GROUP_PLAYOFF tournaments
    7. auto_confirm_stale_submissions — auto-confirm unresponded results past deadline
    8. dispute_escalation — escalate overdue disputes

Beat-only daily tasks (auto_archive, ranking snapshots, analytics) are
intentionally excluded — they are low-priority and can run when Beat is
eventually enabled on a paid tier.

Duplicate-execution protection:
    Uses Django cache (Redis in production) as an atomic lock.  ``cache.add()``
    is atomic — the first caller wins, subsequent callers within the TTL get a
    409 Conflict.  The lock auto-expires after LOCK_TTL_SECONDS (default 4 min)
    so a crashed run cannot permanently block future executions.
"""

from __future__ import annotations

import logging
import os
import time

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

_CRON_SECRET = os.environ.get('CRON_SECRET', '')
_LOCK_KEY = 'lifecycle_cron:running'
_LOCK_TTL_SECONDS = int(os.environ.get('CRON_LOCK_TTL', '240'))  # 4 min default
_SLOW_THRESHOLD_MS = 5000


@csrf_exempt
@require_POST
def lifecycle_cron(request):
    """
    POST /api/lifecycle/cron/

    Headers:
        Authorization: Bearer <CRON_SECRET>

    Returns JSON summary of each task's outcome.
    """
    # ── Auth ────────────────────────────────────────────────────────
    if not _CRON_SECRET:
        return JsonResponse(
            {'error': 'CRON_SECRET not configured'},
            status=503,
        )

    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth != f'Bearer {_CRON_SECRET}':
        return JsonResponse({'error': 'unauthorized'}, status=401)

    # ── Duplicate-execution lock ────────────────────────────────────
    # cache.add() is atomic: returns True only if the key didn't exist.
    # Lock auto-expires after _LOCK_TTL_SECONDS so a crash can't deadlock.
    if not cache.add(_LOCK_KEY, True, timeout=_LOCK_TTL_SECONDS):
        logger.warning('[lifecycle_cron] skipped — another run is still in progress')
        return JsonResponse(
            {'status': 'skipped', 'reason': 'concurrent execution'},
            status=409,
        )

    t0 = time.monotonic()
    logger.info('[lifecycle_cron] started')

    try:
        results = {}
        tasks = [
            ('auto_advance', _run_auto_advance),
            ('wrapup', _run_wrapup),
            ('no_show', _run_no_show),
            ('lobby_close', _run_lobby_close),
            ('payment_expiry', _run_payment_expiry),
            ('group_playoff_reconcile', _run_group_playoff_reconcile),
            ('auto_confirm_submissions', _run_auto_confirm_submissions),
            ('dispute_escalation', _run_dispute_escalation),
        ]

        for name, runner in tasks:
            task_t0 = time.monotonic()
            results[name] = runner()
            task_ms = round((time.monotonic() - task_t0) * 1000)
            results[name]['elapsed_ms'] = task_ms

            level = logging.WARNING if task_ms > _SLOW_THRESHOLD_MS else logging.DEBUG
            logger.log(level, '[lifecycle_cron] task=%s elapsed=%dms result=%s', name, task_ms, results[name])

        elapsed_ms = round((time.monotonic() - t0) * 1000)

        if elapsed_ms > _SLOW_THRESHOLD_MS:
            logger.warning('[lifecycle_cron] SLOW RUN completed in %dms', elapsed_ms)
        else:
            logger.info('[lifecycle_cron] completed in %dms', elapsed_ms)

        return JsonResponse({
            'status': 'ok',
            'elapsed_ms': elapsed_ms,
            'results': results,
        })
    except Exception:
        elapsed_ms = round((time.monotonic() - t0) * 1000)
        logger.exception('[lifecycle_cron] FATAL unhandled error after %dms', elapsed_ms)
        return JsonResponse(
            {'status': 'error', 'error': 'internal server error', 'elapsed_ms': elapsed_ms},
            status=500,
        )
    finally:
        cache.delete(_LOCK_KEY)


# ── Task Runners ────────────────────────────────────────────────────
# Each runner wraps the Celery task's inner logic (not .delay()) so it
# runs synchronously in the request process.  Errors are caught per-task
# so one failure doesn't block the rest.


def _run_auto_advance():
    try:
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        result = TournamentLifecycleService.auto_advance_all()
        advanced = result or []
        if advanced:
            for item in advanced:
                logger.info('[lifecycle_cron] auto_advance transition: %s', item)
        else:
            logger.debug('[lifecycle_cron] auto_advance: no tournaments to advance')
        return {'ok': True, 'advanced': advanced}
    except Exception as exc:
        logger.exception('[lifecycle_cron] auto_advance failed')
        return {'ok': False, 'error': str(exc)}


def _run_wrapup():
    try:
        from apps.tournaments.models.tournament import Tournament
        from apps.tournaments.models.match import Match
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

        live = Tournament.objects.filter(status=Tournament.LIVE, is_deleted=False)
        completed = 0
        for t in live.iterator():
            total = Match.objects.filter(tournament=t, is_deleted=False).count()
            if total == 0:
                continue
            incomplete = Match.objects.filter(
                tournament=t, is_deleted=False,
            ).exclude(state__in=['completed', 'cancelled', 'forfeit']).count()
            if incomplete == 0:
                try:
                    TournamentLifecycleService.transition(
                        t.id, Tournament.COMPLETED,
                        reason=f'Cron: all {total} match(es) complete',
                    )
                    logger.info(
                        '[lifecycle_cron] wrapup transition: tournament=%s LIVE→COMPLETED (%d matches)',
                        t.slug, total,
                    )
                    completed += 1
                except Exception:
                    logger.exception('[lifecycle_cron] wrapup transition failed for tournament=%s', t.slug)
        if completed == 0:
            logger.debug('[lifecycle_cron] wrapup: no tournaments ready to complete')
        return {'ok': True, 'completed': completed}
    except Exception as exc:
        logger.exception('[lifecycle_cron] wrapup failed')
        return {'ok': False, 'error': str(exc)}


def _run_no_show():
    try:
        from apps.tournaments.tasks.no_show_timer import check_no_show_matches
        result = check_no_show_matches.apply().result
        return {'ok': True, **result} if isinstance(result, dict) else {'ok': True}
    except Exception as exc:
        logger.exception('[lifecycle_cron] no_show failed')
        return {'ok': False, 'error': str(exc)}


def _run_lobby_close():
    try:
        from apps.tournaments.tasks.no_show_timer import auto_close_expired_lobbies
        result = auto_close_expired_lobbies.apply().result
        return {'ok': True, **result} if isinstance(result, dict) else {'ok': True}
    except Exception as exc:
        logger.exception('[lifecycle_cron] lobby_close failed')
        return {'ok': False, 'error': str(exc)}


def _run_payment_expiry():
    try:
        from apps.tournaments.tasks.payment_expiry import expire_overdue_payments
        result = expire_overdue_payments.apply().result
        return {'ok': True, **result} if isinstance(result, dict) else {'ok': True}
    except Exception as exc:
        logger.exception('[lifecycle_cron] payment_expiry failed')
        return {'ok': False, 'error': str(exc)}


def _run_group_playoff_reconcile():
    try:
        from apps.tournaments.tasks.lifecycle import reconcile_group_playoff_transitions
        result = reconcile_group_playoff_transitions.apply().result
        return {'ok': True, **result} if isinstance(result, dict) else {'ok': True}
    except Exception as exc:
        logger.exception('[lifecycle_cron] group_playoff_reconcile failed')
        return {'ok': False, 'error': str(exc)}


def _run_auto_confirm_submissions():
    """Sweep stale submissions past their auto_confirm_deadline."""
    try:
        from apps.tournament_ops.tasks_result_submission import auto_confirm_submission_task
        from apps.tournaments.models.result_submission import MatchResultSubmission
        from django.utils import timezone

        now = timezone.now()
        stale_ids = list(
            MatchResultSubmission.objects.filter(
                status='pending_opponent',
                auto_confirm_deadline__lt=now,
            ).values_list('id', flat=True)[:50]  # Cap per cycle
        )
        confirmed = 0
        for sid in stale_ids:
            try:
                auto_confirm_submission_task.apply(args=[sid])
                confirmed += 1
            except Exception:
                pass
        return {'ok': True, 'confirmed': confirmed, 'scanned': len(stale_ids)}
    except Exception as exc:
        logger.exception('[lifecycle_cron] auto_confirm failed')
        return {'ok': False, 'error': str(exc)}


def _run_dispute_escalation():
    try:
        from apps.tournament_ops.tasks_dispute import dispute_escalation_task
        result = dispute_escalation_task.apply().result
        return {'ok': True, **result} if isinstance(result, dict) else {'ok': True}
    except Exception as exc:
        logger.exception('[lifecycle_cron] dispute_escalation failed')
        return {'ok': False, 'error': str(exc)}
