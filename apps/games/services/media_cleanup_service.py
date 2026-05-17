"""MediaCleanupService — safely deletes eligible game media orphans from Cloudinary.

Called by the admin action, the management command, and the periodic Celery task.
All safety checks are re-run at deletion time, not just at candidate creation.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from django.utils import timezone

from apps.games.management.commands.audit_cloudinary_orphans import (
    APPROVED_GAME_FOLDERS,
    BLOCKED_SUBSTRINGS,
    _cloudinary_available,
    _cloudinary_media_prefix,
    _destroy,
)
from apps.games.signals_media import _is_still_referenced

logger = logging.getLogger(__name__)


class CleanupResult(TypedDict):
    deleted: int
    skipped: int
    failed: int
    dry_run: bool


def _is_approved_for_deletion(file_name: str) -> bool:
    """Re-verify the file is in an approved game-media folder."""
    if not file_name:
        return False
    name = file_name.strip().replace("\\", "/").lstrip("/")
    prefix = _cloudinary_media_prefix()
    if name.startswith(prefix):
        name = name[len(prefix):]
    name_lower = name.lower()
    return (
        any(name_lower.startswith(f) for f in APPROVED_GAME_FOLDERS)
        and not any(b in name_lower for b in BLOCKED_SUBSTRINGS)
    )


class MediaCleanupService:
    """Process MediaCleanupCandidate rows that have passed their retention window."""

    DEFAULT_BATCH = 50

    def process_eligible(self, *, dry_run: bool = False, limit: int = DEFAULT_BATCH) -> CleanupResult:
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate

        now = timezone.now()
        candidates = (
            MediaCleanupCandidate.objects.filter(
                status=MediaCleanupCandidate.STATUS_PENDING,
                eligible_after__lte=now,
            )
            .order_by("eligible_after")[:limit]
        )

        result: CleanupResult = {"deleted": 0, "skipped": 0, "failed": 0, "dry_run": dry_run}
        for candidate in candidates:
            outcome = self._process_one(candidate, dry_run=dry_run)
            result[outcome] += 1

        logger.info(
            "MediaCleanupService.process_eligible: dry_run=%s deleted=%d skipped=%d failed=%d",
            dry_run,
            result["deleted"],
            result["skipped"],
            result["failed"],
        )
        return result

    def _process_one(self, candidate, *, dry_run: bool) -> str:
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate

        file_name = candidate.file_name

        # Safety gate 1: approved folder
        if not _is_approved_for_deletion(file_name):
            logger.warning(
                "media_cleanup: skipping %s — not in approved folder (id=%s)",
                file_name, candidate.pk,
            )
            candidate.status = MediaCleanupCandidate.STATUS_SKIPPED
            candidate.error_message = "Not in an approved game-media folder."
            candidate.save(update_fields=["status", "error_message"])
            return "skipped"

        # Safety gate 2: still referenced by any DB row?
        if _is_still_referenced(file_name, candidate.source_model, candidate.source_object_id or 0):
            logger.info(
                "media_cleanup: skipping %s — still referenced in DB (id=%s)",
                file_name, candidate.pk,
            )
            candidate.status = MediaCleanupCandidate.STATUS_SKIPPED
            candidate.error_message = "File is still referenced by a DB row."
            candidate.save(update_fields=["status", "error_message"])
            return "skipped"

        if dry_run:
            logger.info("media_cleanup: [dry-run] would delete %s (id=%s)", file_name, candidate.pk)
            return "deleted"

        # Safety gate 3: Cloudinary configured?
        if not _cloudinary_available():
            candidate.status = MediaCleanupCandidate.STATUS_FAILED
            candidate.error_message = "Cloudinary not configured."
            candidate.save(update_fields=["status", "error_message"])
            return "failed"

        ok = _destroy(file_name)
        if ok:
            candidate.status = MediaCleanupCandidate.STATUS_DELETED
            candidate.deleted_at = timezone.now()
            candidate.save(update_fields=["status", "deleted_at"])
            logger.info("media_cleanup: deleted %s from Cloudinary (id=%s)", file_name, candidate.pk)
            return "deleted"
        else:
            candidate.status = MediaCleanupCandidate.STATUS_FAILED
            candidate.error_message = "cloudinary.uploader.destroy returned non-ok result."
            candidate.save(update_fields=["status", "error_message"])
            logger.error("media_cleanup: failed to delete %s (id=%s)", file_name, candidate.pk)
            return "failed"
