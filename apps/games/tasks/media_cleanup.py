"""Periodic Celery task: delete eligible game media cleanup candidates.

Gated by ENABLE_MEDIA_CLEANUP_BEAT=1 env var. The task itself checks this at
runtime so it is safe to register it in the beat schedule unconditionally.
"""

import logging
import os

from celery import shared_task

logger = logging.getLogger(__name__)

ENABLE_MEDIA_CLEANUP_BEAT = os.getenv("ENABLE_MEDIA_CLEANUP_BEAT", "0") == "1"


@shared_task(
    bind=True,
    name="apps.games.tasks.media_cleanup.cleanup_eligible_game_media",
    max_retries=2,
    default_retry_delay=300,
    ignore_result=True,
)
def cleanup_eligible_game_media(self):
    """Delete Cloudinary assets for eligible MediaCleanupCandidate rows.

    Runs only when ENABLE_MEDIA_CLEANUP_BEAT=1.  Each eligible candidate is
    re-validated (approved folder + no active DB references) before deletion.
    """
    if not ENABLE_MEDIA_CLEANUP_BEAT:
        logger.debug("cleanup_eligible_game_media: skipped (ENABLE_MEDIA_CLEANUP_BEAT not set)")
        return

    try:
        from apps.games.services.media_cleanup_service import MediaCleanupService
        service = MediaCleanupService()
        result = service.process_eligible(dry_run=False)
        logger.info(
            "cleanup_eligible_game_media done: deleted=%d skipped=%d failed=%d",
            result["deleted"], result["skipped"], result["failed"],
        )
    except Exception as exc:
        logger.exception("cleanup_eligible_game_media raised: %s", exc)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("cleanup_eligible_game_media: max retries exceeded")
