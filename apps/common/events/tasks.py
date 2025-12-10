"""  
Celery tasks for asynchronous event processing.

This module provides Celery task infrastructure for async event dispatch,
enabling event handlers to run outside the request/response cycle with
retry capabilities and error handling.

Phase 1 Implementation (Epic 1.2):
- ✅ dispatch_event_task: Async dispatch to registered event handlers
- ✅ Retry logic with exponential backoff (3 retries, 30s default delay)
- ✅ Event reconstruction from serialized dict
- ✅ Safe error handling with logging

Phase 8 Implementation (Epic 8.1 - Event System Hardening):
- ✅ Status tracking: PENDING → PROCESSING → PROCESSED/FAILED
- ✅ Dead Letter Queue: FAILED → DEAD_LETTER after max retries exceeded
- ✅ Retry metadata: retry_count, last_error, last_error_at
- ✅ Metrics/logging hooks: event_processed, event_failed, event_dead_lettered
- ⏳ Idempotency guards (duplicate event detection) (future)
- ⏳ Circuit breaker patterns for failing handlers (future)Usage:
    # Event bus automatically uses this task when settings.EVENTS_USE_CELERY = True
    from apps.common.events.event_bus import get_event_bus, Event
    
    event = Event(name="MatchCompletedEvent", payload={"match_id": 123})
    get_event_bus().publish(event)  # Enqueues to Celery if enabled

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.2
"""

import logging
from datetime import datetime
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger("common.events.tasks")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def dispatch_event_task(self, event_data: Dict[str, Any]) -> None:
    """
    Celery task to asynchronously dispatch an event to registered handlers.

    This task reconstructs an Event from serialized data and dispatches it
    to all registered handlers via EventBus._dispatch_to_handlers(). If a
    handler fails, the entire task is retried with exponential backoff.

    Phase 8, Epic 8.1 Enhancements:
    - Marks EventLog.status as PROCESSING before dispatch
    - Marks EventLog.status as PROCESSED on success
    - Marks EventLog.status as FAILED on error (increments retry_count)
    - Marks EventLog.status as DEAD_LETTER if retry_count > EVENTS_MAX_RETRIES
    - Logs metrics hooks for observability

    Retry Strategy:
    - Max retries: 3 (configurable via EVENTS_MAX_RETRIES)
    - Default retry delay: 30 seconds
    - Exponential backoff on subsequent retries

    Error Handling:
    - Individual handler errors are logged by EventBus._dispatch_to_handlers()
    - Task-level errors trigger retry with EventLog.mark_failed()
    - After max retries, event routed to Dead Letter Queue (Epic 8.1)

    Args:
        event_data: Serialized event dictionary from Event.to_dict()
            Required keys: name, payload, occurred_at (ISO string)
            Optional keys: user_id, correlation_id, metadata

    Example event_data:
        {
            "name": "MatchCompletedEvent",
            "payload": {"match_id": 123, "winner_team_id": 456},
            "occurred_at": "2025-12-08T10:30:00.123456",
            "user_id": 789,
            "correlation_id": "abc-123-def",
            "metadata": {"source": "game_server_1"}
        }

    Raises:
        Exception: Propagates exceptions to trigger Celery retry logic

    TODO (Phase 8):
    - Route permanently failed events to dead letter queue
    - Add idempotency checks to prevent duplicate processing
    - Add structured metrics for task execution times
    - Add distributed tracing correlation IDs
    """
    # Reconstruct Event from serialized dict
    # EventBus uses lazy imports, so import here to avoid circular dependencies
    from apps.common.events.event_bus import Event, get_event_bus
    from apps.common.events.models import EventLog
    from django.conf import settings

    # Get max retries from settings (Phase 8, Epic 8.1)
    max_retries = getattr(settings, 'EVENTS_MAX_RETRIES', 3)
    
    # Extract event_log_id from metadata
    event_log_id = event_data.get("metadata", {}).get("event_log_id")
    event_log = None
    
    # Try to fetch EventLog for status tracking
    if event_log_id:
        try:
            event_log = EventLog.objects.get(id=event_log_id)
        except EventLog.DoesNotExist:
            logger.warning(
                f"EventLog {event_log_id} not found for event {event_data.get('name')}",
                extra={"event_log_id": event_log_id, "event_name": event_data.get("name")}
            )

    try:
        # Phase 8, Epic 8.1: Mark event as PROCESSING
        if event_log:
            event_log.mark_processing()
            logger.debug(
                f"Event processing started: {event_data.get('name')}",
                extra={
                    "event_name": event_data.get("name"),
                    "event_log_id": event_log_id,
                    "status": "processing"
                }
            )
        
        # Parse ISO timestamp string back to datetime
        occurred_at_str = event_data.get("occurred_at")
        if isinstance(occurred_at_str, str):
            occurred_at = datetime.fromisoformat(occurred_at_str)
        else:
            # Already a datetime (shouldn't happen, but be defensive)
            occurred_at = occurred_at_str

        # Reconstruct Event instance
        event = Event(
            name=event_data["name"],
            payload=event_data["payload"],
            occurred_at=occurred_at,
            user_id=event_data.get("user_id"),
            correlation_id=event_data.get("correlation_id"),
            metadata=event_data.get("metadata", {}),
        )

        # Dispatch to all registered handlers via EventBus
        # This reuses the same error handling logic as synchronous dispatch
        get_event_bus()._dispatch_to_handlers(event)

        # Phase 8, Epic 8.1: Mark event as PROCESSED
        if event_log:
            event_log.mark_processed()
        
        # Metrics hook: event_processed (Phase 8, Epic 8.1)
        logger.info(
            f"Event processed successfully: {event.name}",
            extra={
                "event_name": event.name,
                "event_log_id": event_log_id,
                "correlation_id": event.correlation_id,
                "retry_count": self.request.retries,
                "status": "processed"
            }
        )

    except Exception as exc:
        # Phase 8, Epic 8.1: Mark event as FAILED and check DLQ threshold
        error_message = f"{exc.__class__.__name__}: {str(exc)}"
        
        if event_log:
            # Check if we've exceeded max retries threshold
            if event_log.retry_count >= max_retries:
                # Move to Dead Letter Queue
                event_log.mark_dead_letter(error_message)
                
                # Metrics hook: event_dead_lettered (Phase 8, Epic 8.1)
                logger.critical(
                    f"Event moved to Dead Letter Queue: {event_data.get('name', 'UNKNOWN')}",
                    extra={
                        "event_name": event_data.get("name"),
                        "event_log_id": event_log_id,
                        "correlation_id": event_data.get("correlation_id"),
                        "retry_count": event_log.retry_count,
                        "max_retries": max_retries,
                        "status": "dead_letter",
                        "error": error_message
                    }
                )
                # Don't retry - permanently failed
                return
            else:
                # Mark as FAILED, will retry
                event_log.mark_failed(error_message)
                
                # Metrics hook: event_failed (Phase 8, Epic 8.1)
                logger.warning(
                    f"Event processing failed, will retry: {event_data.get('name', 'UNKNOWN')}",
                    extra={
                        "event_name": event_data.get("name"),
                        "event_log_id": event_log_id,
                        "correlation_id": event_data.get("correlation_id"),
                        "retry_count": event_log.retry_count,
                        "max_retries": max_retries,
                        "status": "failed",
                        "error": error_message
                    }
                )
        else:
            # No EventLog found - log error
            logger.error(
                f"Error dispatching event {event_data.get('name', 'UNKNOWN')} (no EventLog): {exc}",
                extra={
                    "event_name": event_data.get("name"),
                    "correlation_id": event_data.get("correlation_id"),
                    "retry_count": self.request.retries,
                    "max_retries": self.max_retries
                },
                exc_info=True
            )

        # Retry the task with exponential backoff
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            # Should not reach here if event_log.mark_dead_letter() worked
            # But handle just in case
            logger.critical(
                f"Max retries exhausted for event {event_data.get('name', 'UNKNOWN')}",
                extra={
                    "event_name": event_data.get("name"),
                    "correlation_id": event_data.get("correlation_id"),
                    "event_data": event_data,
                    "status": "max_retries_exceeded"
                }
            )
            # Re-raise to mark task as failed in Celery
            raise
