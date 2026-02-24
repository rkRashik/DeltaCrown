"""
Celery Tasks for Dispute System - Phase 6, Epic 6.2

Automated tasks for dispute reminders and escalations.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2 (Opponent Verification & Dispute System)
"""

from datetime import timedelta
from typing import Optional

from django.utils import timezone
from celery import shared_task

from apps.common.events.event_bus import Event, get_event_bus


@shared_task(
    name='tournament_ops.opponent_response_reminder_task',
    bind=True,
    max_retries=3,
)
def opponent_response_reminder_task(self, submission_id: int):
    """
    Send reminder to opponent if no response after N hours.
    
    Workflow:
    1. Check if submission is still pending (not confirmed/disputed)
    2. If pending, send notification to opponent
    3. Publish OpponentResponseReminderEvent
    
    Scheduling:
    - Triggered from ResultSubmissionService.submit_result() with countdown
    - Default: 24 hours after submission (configurable via env var)
    
    Args:
        submission_id: MatchResultSubmission ID
        
    Reference: Phase 6, Epic 6.2 - Opponent Response Reminder
    
    TODO: Configure via CELERY_BEAT_SCHEDULE or manual apply_async with countdown
    TODO: Add env var OPPONENT_RESPONSE_REMINDER_HOURS (default: 24)
    """
    # Import here to avoid circular imports
    from apps.tournament_ops.adapters import ResultSubmissionAdapter
    
    adapter = ResultSubmissionAdapter()
    
    try:
        # Get submission
        submission = adapter.get_submission(submission_id)
        
        # Only remind if still pending
        if submission.status != 'pending':
            # Already confirmed/disputed/rejected, skip reminder
            return {
                'status': 'skipped',
                'reason': f'Submission {submission_id} no longer pending (status: {submission.status})',
            }
        
        # Publish reminder event
        # Listener (Epic 6.3): NotificationService sends email/push to opponent
        get_event_bus().publish(Event(
            name='OpponentResponseReminderEvent',
            payload={
                'submission_id': submission_id,
                'match_id': submission.match_id,
                'opponent_user_id': submission.submitted_by_user_id,  # TODO: Get actual opponent user ID from match
                'submitted_at': submission.submitted_at.isoformat(),
            },
            metadata={
                'reminder_type': 'opponent_response',
                'hours_elapsed': 24,  # TODO: Calculate from submission.submitted_at
            }
        ))
        
        return {
            'status': 'success',
            'submission_id': submission_id,
        }
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    name='tournament_ops.dispute_escalation_task',
    bind=True,
)
def dispute_escalation_task(self):
    """
    Auto-escalate disputes older than SLA.
    
    Workflow:
    1. Query all open/under_review disputes older than SLA (e.g., 48 hours)
    2. For each dispute:
       - Update status to 'escalated'
       - Set escalated_at timestamp
       - Publish DisputeEscalatedEvent
    
    Scheduling:
    - Periodic task (Celery Beat)
    - Suggested: Every 6 hours
    
    Configuration:
    - Env var: DISPUTE_AUTO_ESCALATION_HOURS (default: 48)
    
    Reference: Phase 6, Epic 6.2 - Auto Escalation
    
    TODO: Add to CELERY_BEAT_SCHEDULE:
    ```python
    'dispute-auto-escalation': {
        'task': 'tournament_ops.dispute_escalation_task',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    }
    ```
    """
    # Import here to avoid circular imports
    from apps.tournament_ops.services import DisputeService
    from apps.tournament_ops.adapters import DisputeAdapter, ResultSubmissionAdapter
    
    # Get env var or default to 48 hours
    import os
    escalation_hours = int(os.getenv('DISPUTE_AUTO_ESCALATION_HOURS', '48'))
    escalation_threshold = timezone.now() - timedelta(hours=escalation_hours)
    
    dispute_adapter = DisputeAdapter()
    result_submission_adapter = ResultSubmissionAdapter()
    dispute_service = DisputeService(
        dispute_adapter=dispute_adapter,
        result_submission_adapter=result_submission_adapter,
    )
    
    # Query open/under_review disputes older than threshold
    # Use method-level ORM import
    from apps.tournaments.models import DisputeRecord
    
    old_disputes = DisputeRecord.objects.filter(
        status__in=['open', 'under_review'],
        opened_at__lt=escalation_threshold,
    ).values_list('id', flat=True)
    
    escalated_count = 0
    
    for dispute_id in old_disputes:
        try:
            # Escalate via service (publishes event, logs step)
            dispute_service.escalate_dispute(
                dispute_id=dispute_id,
                escalated_by_user_id=None,  # Auto-escalation (system)
            )
            escalated_count += 1
        except Exception as e:
            # Log error but continue processing other disputes
            print(f"Failed to auto-escalate dispute {dispute_id}: {e}")
            # TODO: Use proper logging (logger.error)
    
    return {
        'status': 'success',
        'escalated_count': escalated_count,
        'escalation_hours': escalation_hours,
    }
