"""Evidence file cleanup utilities for completed tournaments."""

from __future__ import annotations

import logging
from typing import Any

from apps.tournaments.models.result_submission import MatchResultSubmission

logger = logging.getLogger("tournaments.evidence_cleanup")


def purge_tournament_result_evidence_files(tournament_id: int, *, chunk_size: int = 200) -> dict[str, Any]:
    """
    Delete physical evidence files for a completed tournament while preserving DB rows.

    The associated MatchResultSubmission records are retained. Only the ImageField
    storage object is deleted and the ImageField reference is nulled.
    """
    stats: dict[str, Any] = {
        "tournament_id": int(tournament_id),
        "scanned": 0,
        "deleted": 0,
        "failed": 0,
    }

    queryset = (
        MatchResultSubmission.objects
        .filter(match__tournament_id=tournament_id, proof_screenshot__isnull=False)
        .exclude(proof_screenshot="")
        .only("id", "proof_screenshot")
        .order_by("id")
    )

    for submission in queryset.iterator(chunk_size=max(25, int(chunk_size))):
        stats["scanned"] += 1

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
        "Tournament evidence cleanup completed",
        extra={
            "tournament_id": tournament_id,
            "scanned": stats["scanned"],
            "deleted": stats["deleted"],
            "failed": stats["failed"],
        },
    )
    return stats
