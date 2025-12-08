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

Phase 8 (Future):
- ⏳ Dead letter queue for permanently failed events
- ⏳ Event replay from EventLog
- ⏳ Idempotency guards (duplicate event detection)
- ⏳ Circuit breaker patterns for failing handlers
- ⏳ Metrics and observability (Prometheus, Sentry)

Usage:
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

    Retry Strategy:
    - Max retries: 3
    - Default retry delay: 30 seconds
    - Exponential backoff on subsequent retries

    Error Handling:
    - Individual handler errors are logged by EventBus._dispatch_to_handlers()
    - Task-level errors trigger retry
    - After max retries, event is logged and TODO: routed to DLQ (Phase 8)

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

    try:
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

        logger.info(
            f"Successfully dispatched event {event.name} (async)",
            extra={
                "event_name": event.name,
                "correlation_id": event.correlation_id,
                "retry_count": self.request.retries
            }
        )

    except Exception as exc:
        # Log the error with context
        logger.error(
            f"Error dispatching event {event_data.get('name', 'UNKNOWN')}: {exc}",
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
            # Max retries exhausted - log critical error
            logger.critical(
                f"Max retries exhausted for event {event_data.get('name', 'UNKNOWN')}",
                extra={
                    "event_name": event_data.get("name"),
                    "correlation_id": event_data.get("correlation_id"),
                    "event_data": event_data
                }
            )
            # TODO (Phase 8): Route to dead letter queue for manual inspection
            # TODO (Phase 8): Alert on-call engineers (PagerDuty, Slack)
            # For now, re-raise to mark task as failed in Celery
            raise
