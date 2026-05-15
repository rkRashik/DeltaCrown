"""Celery tasks for tournament result evidence cleanup.

Beat-driven workflow (RP — Evidence Lifecycle):
  - ``purge_tournament_result_evidence_files_task`` — single tournament
    purge (lifecycle-aware; safe even when called for an active
    tournament, refuses to act).
  - ``sweep_eligible_evidence_task`` — periodic sweeper that scans all
    completed tournaments past the retention window and purges their
    safe submissions. Wired into the celery beat schedule.
"""

from __future__ import annotations

from celery import shared_task

from apps.tournaments.services.evidence_cleanup import (
    purge_tournament_result_evidence_files,
    sweep_eligible_tournaments,
)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def purge_tournament_result_evidence_files_task(self, tournament_id: int):
    try:
        return purge_tournament_result_evidence_files(int(tournament_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(exc=exc)


@shared_task(
    name="apps.tournaments.tasks.sweep_eligible_evidence",
    bind=True,
    max_retries=0,
    expires=3600,
)
def sweep_eligible_evidence_task(self):
    """Daily sweep — purge eligible evidence respecting retention + protection."""
    return sweep_eligible_tournaments()
