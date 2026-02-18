"""
Tournament Lifecycle Celery Tasks — Scheduled Status Transitions.

Periodic tasks that auto-advance tournaments based on date thresholds,
check for stale live tournaments, and trigger the completion pipeline.

Beat schedule entries are registered in deltacrown/celery.py.

Tasks:
    auto_advance_tournaments  — Every 5 minutes: PUBLISHED → REG_OPEN → REG_CLOSED → LIVE
    check_tournament_wrapup   — Every hour: detect LIVE tournaments with all matches complete
    auto_archive_tournaments  — Daily 4 AM: COMPLETED (>7 days) → ARCHIVED
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.tournaments.tasks.auto_advance_tournaments',
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    ignore_result=True,
)
def auto_advance_tournaments(self):
    """
    Scan all tournaments in PUBLISHED / REGISTRATION_OPEN / REGISTRATION_CLOSED
    and advance them if their date thresholds have passed.

    Runs every 5 minutes via Celery Beat.
    """
    from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

    try:
        results = TournamentLifecycleService.auto_advance_all()
        if results:
            logger.info("[auto_advance] Advanced tournaments: %s", results)
        return results
    except Exception as exc:
        logger.exception("[auto_advance] Unexpected error")
        raise self.retry(exc=exc)


@shared_task(
    name='apps.tournaments.tasks.check_tournament_wrapup',
    bind=True,
    max_retries=1,
    ignore_result=True,
)
def check_tournament_wrapup(self):
    """
    Find LIVE tournaments where all matches are completed and
    transition them to COMPLETED status.

    Runs every hour at :15 via Celery Beat.
    """
    from apps.tournaments.models.tournament import Tournament
    from apps.tournaments.models.match import Match
    from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

    live_tournaments = Tournament.objects.filter(
        status=Tournament.LIVE,
        is_deleted=False,
    )

    completed_count = 0
    for t in live_tournaments.iterator():
        # Check if all matches are in a terminal state
        total = Match.objects.filter(tournament=t, is_deleted=False).count()
        if total == 0:
            continue  # No matches yet — probably hasn't started

        incomplete = Match.objects.filter(
            tournament=t, is_deleted=False,
        ).exclude(
            state__in=['completed', 'cancelled', 'no_show', 'bye'],
        ).count()

        if incomplete == 0:
            try:
                TournamentLifecycleService.transition(
                    t.id,
                    Tournament.COMPLETED,
                    reason=f'Auto: all {total} match(es) complete',
                )
                completed_count += 1
                logger.info(
                    "[wrapup] Tournament %s (%s) → COMPLETED (%d matches)",
                    t.id, t.name, total,
                )
            except Exception as e:
                logger.warning("[wrapup] Failed to complete tournament %s: %s", t.id, e)

    if completed_count:
        logger.info("[wrapup] Completed %d tournament(s)", completed_count)
    return {'completed': completed_count}


@shared_task(
    name='apps.tournaments.tasks.auto_archive_tournaments',
    bind=True,
    max_retries=1,
    ignore_result=True,
)
def auto_archive_tournaments(self):
    """
    Archive tournaments that have been COMPLETED or CANCELLED for more than
    7 days (configurable via TOURNAMENT_ARCHIVE_AFTER_DAYS setting).

    Runs daily at 4 AM via Celery Beat.
    """
    from django.conf import settings
    from apps.tournaments.models.tournament import Tournament
    from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

    archive_after_days = getattr(settings, 'TOURNAMENT_ARCHIVE_AFTER_DAYS', 7)
    cutoff = timezone.now() - timezone.timedelta(days=archive_after_days)

    archivable = Tournament.objects.filter(
        status__in=[Tournament.COMPLETED, Tournament.CANCELLED],
        is_deleted=False,
    ).filter(
        updated_at__lte=cutoff,
    )

    archived_count = 0
    for t in archivable.iterator():
        try:
            TournamentLifecycleService.transition(
                t.id,
                Tournament.ARCHIVED,
                reason=f'Auto: {archive_after_days}d since last update',
                force=True,  # skip 24h guard for batch archival
            )
            archived_count += 1
        except Exception as e:
            logger.warning("[archive] Failed to archive tournament %s: %s", t.id, e)

    if archived_count:
        logger.info("[archive] Archived %d tournament(s)", archived_count)
    return {'archived': archived_count}
