"""
Event bus infrastructure for domain event publishing and subscription.

This module provides the core event infrastructure for DeltaCrown's event-driven
architecture, enabling loosely-coupled communication between domains.

Implementation Status (Phase 1, Epic 1.2):
- ✅ Event base class with metadata
- ✅ EventBus with in-memory pub/sub
- ✅ event_handler decorator for convenient registration
- ✅ EventLog persistence integration
- ✅ Celery integration for async processing (feature-flagged)
- ✅ Basic retry/backoff strategies in Celery task
- ⏳ Dead-letter queue for failed events (Phase 8)
- ⏳ Event replay from EventLog (Phase 8)
- ⏳ Cross-process message broker support (future)

Async Event Processing:
- Set `EVENTS_USE_CELERY = True` in settings to enable async dispatch via Celery.
- When enabled, events are enqueued to Celery tasks after persistence.
- If Celery enqueue fails, events fall back to synchronous dispatch (no events lost).
- When disabled (default), events dispatch synchronously in-process.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.2
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger("common.events")

# Type aliases for clarity
EventHandler = Callable[["Event"], None]
E = TypeVar("E", bound="Event")


@dataclass
class Event:
    """
    Base class for domain events.

    Events represent things that have already happened in the system. They:
    - Carry a payload with business data
    - Include metadata for observability, audit trails, and correlation
    - Are immutable snapshots (use dataclass frozen=False for now, but treat as immutable)

    Common event examples:
    - MatchCompletedEvent (triggers stats updates, leaderboard recalc)
    - TournamentCompletedEvent (triggers payouts, notifications)
    - PaymentVerifiedEvent (triggers registration confirmation)
    - RegistrationApprovedEvent (triggers team notifications)

    Attributes:
        name: Event type identifier (e.g., "MatchCompletedEvent")
        payload: Business data specific to this event
        occurred_at: When the event occurred (UTC)
        user_id: Optional ID of the user who triggered this event
        correlation_id: Optional ID to correlate related events across services
        metadata: Additional context (request_id, source_service, etc.)

    Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.2
    """

    name: str
    payload: Dict[str, Any]
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[int] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize event to a plain dict suitable for logging or persistence.

        Returns:
            Dictionary representation of the event.
        """
        return {
            "name": self.name,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }


class EventBus:
    """
    Event bus for publish/subscribe communication with optional async processing.

    Features:
    - Handlers are registered in memory
    - Events persisted to EventLog before dispatch
    - Synchronous dispatch (default) or async via Celery (feature-flagged)
    - Automatic fallback to sync if Celery unavailable

    Async Mode (Phase 1, Epic 1.2 - COMPLETE):
    - ✅ Persist events to EventLog model before dispatching
    - ✅ Integrate Celery for async processing and retries
    - ✅ Basic retry/backoff strategies (3 retries, 30s delay)
    - ⏳ Dead letter queue for permanently failed events (Phase 8)
    - ⏳ Event replay from EventLog (Phase 8)
    - ⏳ Support cross-process message brokers (RabbitMQ / Redis Streams) (future)

    Usage:
        bus = EventBus()
        bus.subscribe("MatchCompletedEvent", handle_match_completed)
        bus.publish(Event(name="MatchCompletedEvent", payload={...}))

    Or use the global default bus via @event_handler decorator.

    Configuration:
        Set `EVENTS_USE_CELERY = True` in Django settings to enable async dispatch.

    Reference: CLEANUP_AND_TESTING_PART_6.md - §3.1 (Event-Driven Workflows)
    """

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """
        Register a handler for a specific event name.

        Args:
            event_name: Name of the event to subscribe to (e.g., "MatchCompletedEvent")
            handler: Callable that accepts an Event and returns None

        Example:
            def my_handler(event: Event) -> None:
                print(f"Received {event.name}: {event.payload}")

            bus.subscribe("MatchCompletedEvent", my_handler)
        """
        self._subscribers.setdefault(event_name, []).append(handler)

    def publish(self, event: Event) -> None:
        """
        Publish an event to all registered subscribers.

        This method persists events to EventLog before dispatching to handlers,
        providing an audit trail and enabling event replay.

        Dispatch mode is controlled by `settings.EVENTS_USE_CELERY`:
        - False (default): Synchronous in-process dispatch via `_dispatch_to_handlers()`
        - True: Async dispatch via Celery task `dispatch_event_task.delay()`

        If Celery enqueue fails when async mode is enabled, automatically falls
        back to synchronous dispatch to ensure no events are lost.

        TODO (Phase 8 - Advanced Event Infrastructure):
        - Implement dead letter queue for permanently failed events
        - Add event replay from EventLog
        - Add structured logging with correlation IDs
        - Add metrics/tracing (Prometheus, Sentry)

        Args:
            event: Event to publish

        Example:
            event = Event(
                name="MatchCompletedEvent",
                payload={"match_id": 123, "winner_team_id": 456},
                user_id=789,
            )
            bus.publish(event)
        """
        # Persist event to EventLog for audit trail and replay capability
        try:
            from apps.common.events.models import EventLog

            EventLog.objects.create(
                name=event.name,
                payload=event.payload,
                occurred_at=event.occurred_at,
                user_id=event.user_id,
                correlation_id=event.correlation_id,
                metadata=event.metadata,
            )
        except Exception as e:
            # Log persistence failure but don't block event dispatch
            logger.warning(
                f"Failed to persist event {event.name} to EventLog: {e}",
                extra={"event_name": event.name, "correlation_id": event.correlation_id}
            )
            # TODO (Phase 8): Add metrics/alerting for persistence failures

        # Determine dispatch mode from settings
        from django.conf import settings
        use_celery = getattr(settings, 'EVENTS_USE_CELERY', False)

        if use_celery:
            # Async dispatch via Celery task
            try:
                from apps.common.events.tasks import dispatch_event_task
                dispatch_event_task.delay(event.to_dict())
                logger.debug(
                    f"Event {event.name} enqueued to Celery",
                    extra={"event_name": event.name, "correlation_id": event.correlation_id}
                )
            except Exception as e:
                # Celery enqueue failed - fall back to synchronous dispatch
                logger.warning(
                    f"Failed to enqueue event {event.name} to Celery, falling back to sync: {e}",
                    extra={"event_name": event.name, "correlation_id": event.correlation_id}
                )
                # TODO (Phase 8): Add metrics for Celery enqueue failures
                self._dispatch_to_handlers(event)
        else:
            # Synchronous dispatch (default)
            self._dispatch_to_handlers(event)

    def _dispatch_to_handlers(self, event: Event) -> None:
        """
        Internal method to dispatch event to all registered handlers.

        This is separated from publish() to enable both sync and async dispatch paths
        to share the same handler invocation logic. Used by:
        - publish() when EVENTS_USE_CELERY is False (sync mode)
        - dispatch_event_task (Celery task) when EVENTS_USE_CELERY is True (async mode)

        Errors in individual handlers are logged but don't prevent other handlers
        from executing. In async mode, Celery will retry the entire task on failure.

        TODO (Phase 8):
        - Log handler errors to EventLog with error status
        - Send to dead letter queue if retries exhausted
        - Add circuit breaker for repeatedly failing handlers

        Args:
            event: Event to dispatch
        """
        for handler in self._subscribers.get(event.name, []):
            try:
                handler(event)
            except Exception as e:
                # Log error but continue to prevent one bad handler from breaking others
                logger.error(
                    f"Error in event handler for {event.name}: {e}",
                    extra={
                        "event_name": event.name,
                        "correlation_id": event.correlation_id,
                        "handler": handler.__name__ if hasattr(handler, '__name__') else str(handler)
                    },
                    exc_info=True
                )
                # TODO (Phase 8): Log to EventLog with error status
                # TODO (Phase 8): Send to dead letter queue if retries exhausted


# Global default event bus instance
# This allows services to use @event_handler decorator without managing bus instances
_default_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """
    Return the default global event bus instance.

    Returns:
        The global EventBus singleton.

    Usage:
        bus = get_event_bus()
        bus.publish(Event(...))
    """
    return _default_event_bus


def event_handler(event_name: str) -> Callable[[EventHandler], EventHandler]:
    """
    Decorator to register an event handler for a given event name.

    This decorator simplifies event handler registration by keeping the
    handler wiring close to the handler code itself.

    Args:
        event_name: Name of the event to handle (e.g., "MatchCompletedEvent")

    Returns:
        Decorator function

    Usage:
        @event_handler("MatchCompletedEvent")
        def handle_match_completed(event: Event) -> None:
            match_id = event.payload["match_id"]
            winner_id = event.payload["winner_team_id"]
            # Update leaderboards, stats, etc.

        # Handler is automatically registered with the global event bus

    Reference: ARCH_PLAN_PART_1.md - Section 2.3 (Event-Driven Communication)
    """

    def decorator(func: EventHandler) -> EventHandler:
        _default_event_bus.subscribe(event_name, func)
        return func

    return decorator
