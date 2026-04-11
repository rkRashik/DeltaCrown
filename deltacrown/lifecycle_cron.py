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
"""

from __future__ import annotations

import logging
import os
import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

_CRON_SECRET = os.environ.get('CRON_SECRET', '')


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

    # ── Run tasks ───────────────────────────────────────────────────
    results = {}
    t0 = time.monotonic()

    results['auto_advance'] = _run_auto_advance()
    results['wrapup'] = _run_wrapup()
    results['no_show'] = _run_no_show()
    results['lobby_close'] = _run_lobby_close()
    results['payment_expiry'] = _run_payment_expiry()
    results['group_playoff_reconcile'] = _run_group_playoff_reconcile()
    results['auto_confirm_submissions'] = _run_auto_confirm_submissions()
    results['dispute_escalation'] = _run_dispute_escalation()

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    logger.info('[lifecycle_cron] completed in %dms: %s', elapsed_ms, results)

    return JsonResponse({
        'status': 'ok',
        'elapsed_ms': elapsed_ms,
        'results': results,
    })


# ── Task Runners ────────────────────────────────────────────────────
# Each runner wraps the Celery task's inner logic (not .delay()) so it
# runs synchronously in the request process.  Errors are caught per-task
# so one failure doesn't block the rest.


def _run_auto_advance():
    try:
        from apps.tournaments.services.lifecycle_service import TournamentLifecycleService
        result = TournamentLifecycleService.auto_advance_all()
        return {'ok': True, 'advanced': result or []}
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
                    completed += 1
                except Exception:
                    pass
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
