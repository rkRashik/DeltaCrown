"""
Result Submission Celery Tasks - Phase 6, Epic 6.1

Background tasks for result submission workflow.

Tasks:
- auto_confirm_submission_task: Auto-confirm after 24h timeout
"""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def auto_confirm_submission_task(self, submission_id: int):
    """
    Auto-confirm result submission after 24-hour timeout.

    Args:
        submission_id: Submission ID to auto-confirm

    Returns:
        Dict with status and submission_id

    Idempotent: Safe to run multiple times (checks submission status first)
    """
    from apps.tournament_ops.services.result_submission_service import ResultSubmissionService
    from apps.tournament_ops.adapters import (
        ResultSubmissionAdapter,
        SchemaValidationAdapter,
        MatchAdapter,
        GameAdapter,
    )
    from apps.tournament_ops.exceptions import (
        ResultSubmissionNotFoundError,
        InvalidSubmissionStateError,
    )

    try:
        # Instantiate service with adapters
        service = ResultSubmissionService(
            result_submission_adapter=ResultSubmissionAdapter(),
            schema_validation_adapter=SchemaValidationAdapter(),
            match_adapter=MatchAdapter(),
            game_adapter=GameAdapter(),
        )

        # Auto-confirm (idempotent)
        submission = service.auto_confirm_result(submission_id)

        logger.info(
            f"Auto-confirm task completed for submission {submission_id}, "
            f"status: {submission.status}"
        )

        return {
            'status': 'success',
            'submission_id': submission_id,
            'final_status': submission.status,
        }

    except ResultSubmissionNotFoundError as e:
        # Submission doesn't exist (maybe deleted)
        logger.warning(f"Submission {submission_id} not found: {e}")
        return {
            'status': 'not_found',
            'submission_id': submission_id,
            'error': str(e),
        }

    except InvalidSubmissionStateError as e:
        # Already confirmed/disputed/finalized (expected, not an error)
        logger.info(f"Submission {submission_id} already processed: {e}")
        return {
            'status': 'already_processed',
            'submission_id': submission_id,
            'message': str(e),
        }

    except Exception as e:
        # Unexpected error, retry
        logger.error(
            f"Auto-confirm task failed for submission {submission_id}: {e}",
            exc_info=True,
        )

        # Retry with exponential backoff
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.critical(
                f"Auto-confirm task exhausted retries for submission {submission_id}"
            )
            return {
                'status': 'failed',
                'submission_id': submission_id,
                'error': str(e),
            }
