"""Celery tasks for tournament result evidence cleanup."""

from __future__ import annotations

from celery import shared_task

from apps.tournaments.services.evidence_cleanup import purge_tournament_result_evidence_files


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def purge_tournament_result_evidence_files_task(self, tournament_id: int):
    try:
        return purge_tournament_result_evidence_files(int(tournament_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(exc=exc)
