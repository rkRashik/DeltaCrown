"""
Lifecycle-aware evidence cleanup for completed tournaments.

Policy (per product requirement)
================================
1. Evidence stays visible in TOC until the tournament transitions to
   COMPLETED. While the tournament is active / live / pending / in-progress,
   nothing is deleted.

2. After completion, a **retention window** (``EVIDENCE_RETENTION_DAYS``,
   default 30) elapses before any deletion happens. This protects against
   late dispute escalation.

3. Even after the window, **protected submissions are skipped**:
     - status in {PENDING, DISPUTED, REJECTED}
     - linked to an OPEN dispute (DisputeRecord.status NOT in resolved set)
     - the related match is still in DISPUTED state
     - ``confirmed_at`` is null (never reached a verified state)

4. Only safe submissions (CONFIRMED or FINALIZED with no open dispute) lose
   their ``proof_screenshot`` file. The DB row is preserved for audit.

The function is also a safety net — even if a caller invokes it directly
for an active tournament, the lifecycle check refuses and logs.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.tournaments.models.result_submission import MatchResultSubmission

logger = logging.getLogger("tournaments.evidence_cleanup")


# Default retention window — how long after tournament completion we wait
# before purging "safe" evidence. Override via ``EVIDENCE_RETENTION_DAYS``
# in Django settings. Setting to 0 makes deletion immediate-on-eligible
# (still respects per-submission protected states); negative values are
# treated as 0.
DEFAULT_RETENTION_DAYS = 30


# DisputeRecord statuses that count as "resolved" — these no longer protect
# the underlying submissions from cleanup. Anything else is treated as
# open / unresolved and the submission is preserved.
_RESOLVED_DISPUTE_STATUSES = {
    "resolved",
    "closed",
    "rejected",
    "withdrawn",
    "dismissed",
}


def _retention_days() -> int:
    raw = getattr(settings, "EVIDENCE_RETENTION_DAYS", DEFAULT_RETENTION_DAYS)
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = DEFAULT_RETENTION_DAYS
    return max(0, days)


def _tournament_is_eligible(tournament) -> tuple[bool, str]:
    """Return ``(eligible, reason)``. Eligible only when tournament is
    COMPLETED AND the retention window has elapsed.
    """
    status = str(getattr(tournament, "status", "") or "").lower()
    if status != "completed":
        return False, f"tournament_not_completed (status={status})"
    completed_at = (
        getattr(tournament, "completed_at", None)
        or getattr(tournament, "ended_at", None)
        or getattr(tournament, "updated_at", None)
    )
    if completed_at is None:
        # We can't measure the retention window — refuse rather than
        # purge prematurely.
        return False, "no_completion_timestamp"
    days = _retention_days()
    if days > 0:
        deadline = completed_at + timedelta(days=days)
        if timezone.now() < deadline:
            return False, f"within_retention_window (until={deadline.isoformat()})"
    return True, "eligible"


def _submission_is_protected(submission) -> tuple[bool, str]:
    """Per-submission protection check. ``True`` means skip.

    Protections:
      - status in PENDING / DISPUTED / REJECTED
      - confirmed_at is null (never reached a verified state)
      - is_archived is True (soft-archived by match reset; always preserved
        until explicitly eligible — archivals from reset must not be purged
        while the related match/tournament could still be contested)
      - any related DisputeRecord exists with non-resolved status
      - the related match itself is in DISPUTED state
    """
    status = str(getattr(submission, "status", "") or "").lower()
    if status in {"pending", "disputed", "rejected"}:
        return True, f"submission_status={status}"
    if getattr(submission, "confirmed_at", None) is None:
        return True, "no_confirmed_at"
    # Archived submissions are permanently preserved until the tournament
    # retention window expires AND the match is in a fully resolved state.
    # We protect them here so a reset-then-complete flow cannot accidentally
    # purge screenshots from a contested match attempt.
    if getattr(submission, "is_archived", False):
        return True, "submission_archived"

    # Check related match state.
    match = getattr(submission, "match", None)
    if match is not None:
        match_state = str(getattr(match, "state", "") or "").lower()
        if match_state == "disputed":
            return True, f"match_state=disputed"

    # Open disputes block cleanup.
    try:
        from apps.tournaments.models.dispute import DisputeRecord
        open_count = (
            DisputeRecord.objects
            .filter(submission_id=submission.id)
            .exclude(status__in=_RESOLVED_DISPUTE_STATUSES)
            .count()
        )
        if open_count > 0:
            return True, f"open_disputes={open_count}"
    except Exception as exc:
        # If the dispute lookup fails, err on the side of preservation.
        return True, f"dispute_lookup_failed: {exc.__class__.__name__}"

    return False, ""


def purge_tournament_result_evidence_files(
    tournament_id: int,
    *,
    chunk_size: int = 200,
    force: bool = False,
) -> dict[str, Any]:
    """Delete physical evidence files for a tournament — lifecycle-aware.

    The associated ``MatchResultSubmission`` rows are retained. Only the
    ``proof_screenshot`` ImageField storage object is deleted and the
    reference is nulled. ``proof_screenshot_url`` (external URL) is
    preserved — it points to externally-hosted media which this task does
    not own.

    ``force=True`` bypasses the tournament-eligibility check (useful for
    admin scripts that need to purge a specific completed event manually
    before the retention window). Per-submission protection is ALWAYS
    enforced — disputed / unconfirmed evidence is never deleted.
    """
    from apps.tournaments.models.tournament import Tournament

    stats: dict[str, Any] = {
        "tournament_id": int(tournament_id),
        "scanned": 0,
        "deleted": 0,
        "skipped_protected": 0,
        "failed": 0,
        "eligible": False,
        "skip_reason": "",
    }

    try:
        tournament = Tournament.objects.only(
            "id", "status", "completed_at", "ended_at", "updated_at",
        ).get(pk=tournament_id)
    except Tournament.DoesNotExist:
        stats["skip_reason"] = "tournament_not_found"
        logger.info("Evidence cleanup skipped — %s", stats["skip_reason"],
                    extra={"tournament_id": tournament_id})
        return stats

    if not force:
        eligible, reason = _tournament_is_eligible(tournament)
        stats["eligible"] = eligible
        if not eligible:
            stats["skip_reason"] = reason
            logger.info(
                "Evidence cleanup skipped — %s",
                reason,
                extra={"tournament_id": tournament_id, "force": False},
            )
            return stats
    else:
        stats["eligible"] = True
        stats["skip_reason"] = "force=True"

    queryset = (
        MatchResultSubmission.objects
        .filter(match__tournament_id=tournament_id, proof_screenshot__isnull=False)
        .exclude(proof_screenshot="")
        .select_related("match")
        .only("id", "proof_screenshot", "status", "confirmed_at",
              "is_archived", "match__id", "match__state")
        .order_by("id")
    )

    for submission in queryset.iterator(chunk_size=max(25, int(chunk_size))):
        stats["scanned"] += 1

        protected, protect_reason = _submission_is_protected(submission)
        if protected:
            stats["skipped_protected"] += 1
            logger.debug(
                "Skipping protected submission",
                extra={
                    "submission_id": submission.pk,
                    "reason": protect_reason,
                    "tournament_id": tournament_id,
                },
            )
            continue

        proof_file = getattr(submission, "proof_screenshot", None)
        file_name = str(getattr(proof_file, "name", "") or "").strip()
        if not file_name:
            continue

        try:
            storage = proof_file.storage
            if storage.exists(file_name):
                storage.delete(file_name)
            MatchResultSubmission.objects.filter(pk=submission.pk).update(proof_screenshot=None)
            stats["deleted"] += 1
        except Exception:
            stats["failed"] += 1
            logger.exception(
                "Failed deleting result evidence file",
                extra={
                    "tournament_id": tournament_id,
                    "submission_id": submission.pk,
                    "file_name": file_name,
                },
            )

    logger.info(
        "Evidence cleanup completed for tournament=%s "
        "scanned=%s deleted=%s skipped_protected=%s failed=%s",
        tournament_id,
        stats["scanned"], stats["deleted"], stats["skipped_protected"], stats["failed"],
    )
    return stats


def sweep_eligible_tournaments(*, chunk_size: int = 200) -> dict[str, Any]:
    """Beat-driven sweeper. Finds completed tournaments past the retention
    window with no open disputes and runs the lifecycle-aware purge.

    Designed to be called from a daily Celery beat task. Single-pass over
    completed tournaments — never visits active/live/pending ones.
    """
    from apps.tournaments.models.tournament import Tournament

    days = _retention_days()
    summary = {"tournaments_scanned": 0, "tournaments_purged": 0,
               "total_files_deleted": 0, "retention_days": days}

    cutoff = timezone.now() - timedelta(days=max(0, days))

    qs = Tournament.objects.filter(
        status="completed",
        is_deleted=False,
    ).only("id", "completed_at", "ended_at", "updated_at")

    for tournament in qs.iterator(chunk_size=chunk_size):
        summary["tournaments_scanned"] += 1
        completed_at = (
            getattr(tournament, "completed_at", None)
            or getattr(tournament, "ended_at", None)
            or getattr(tournament, "updated_at", None)
        )
        if completed_at is None or completed_at > cutoff:
            continue
        result = purge_tournament_result_evidence_files(tournament.id, chunk_size=chunk_size)
        if result.get("deleted"):
            summary["tournaments_purged"] += 1
            summary["total_files_deleted"] += int(result.get("deleted") or 0)

    logger.info(
        "Evidence cleanup sweep: scanned=%s purged=%s files=%s retention_days=%s",
        summary["tournaments_scanned"], summary["tournaments_purged"],
        summary["total_files_deleted"], summary["retention_days"],
    )
    return summary
