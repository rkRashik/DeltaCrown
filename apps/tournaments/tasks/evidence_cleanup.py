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


@shared_task(
    name="apps.tournaments.tasks.run_ocr_and_compare",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=180,   # Gemini Flash can take up to 90s — give 3× headroom
    time_limit=200,
)
def run_ocr_and_compare_task(self, submission_id: int, force: bool = False):
    """P3.1 — Auto-OCR pipeline for a participant-uploaded result screenshot.

    Steps:
      1. Run OCR on the submission. ``force=False`` (default) skips when
         status is already 'completed' — idempotent for the auto-trigger
         path. ``force=True`` is used by the admin rescan action.
      2. After OCR, check whether both sides of the match have completed.
      3. Compute evidence comparison and flag/clear review status.
      4. Broadcast WS update to TOC Evidence tab.

    Requires a running Celery **worker** (``celery -A deltacrown worker``).
    NOT Celery beat — beat is only for scheduled sweepers (evidence cleanup,
    veto timeout). Without a worker the task queues in the broker and executes
    when a worker comes online; manual Scan Evidence always works regardless.
    """
    from apps.tournaments.services.ocr_pipeline import run_ocr_for_submission
    from apps.tournaments.services.evidence_flagging import (
        check_and_flag_evidence_after_ocr,
    )
    try:
        run_ocr_for_submission(submission_id, force=bool(force))
        check_and_flag_evidence_after_ocr(submission_id)
    except Exception as exc:
        raise self.retry(exc=exc)
