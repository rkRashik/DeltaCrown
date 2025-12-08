"""
Event bus infrastructure for domain event publishing and subscription.

This module provides the core event infrastructure for DeltaCrown's event-driven
architecture, enabling loosely-coupled communication between domains.

Implementation Status (Phase 1, Epic 1.2):
- ✅ Event base class with metadata
- ✅ EventBus with in-memory pub/sub
- ✅ event_handler decorator for convenient registration
- ⏳ EventLog persistence integration (next micro-task)
- ⏳ Celery integration for async processing (next micro-task)
- ⏳ Retry/backoff strategies (next micro-task)
- ⏳ Cross-process message broker support (future)

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

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
    In-process event bus for publish/subscribe communication.

    This is the first iteration of the event system with minimal functionality:
    - Handlers are registered in memory
    - `publish()` dispatches synchronously in-process
    - No persistence or async processing yet

    Future iterations (Phase 1, Epic 1.2):
    - TODO: Persist events to EventLog model before dispatching
    - TODO: Integrate Celery for async processing and retries
    - TODO: Add retry/backoff strategies for failed handlers
    - TODO: Support cross-process message brokers (RabbitMQ / Redis Streams)
    - TODO: Add dead letter queue for permanently failed events
    - TODO: Implement event replay from EventLog

    Usage:
        bus = EventBus()
        bus.subscribe("MatchCompletedEvent", handle_match_completed)
        bus.publish(Event(name="MatchCompletedEvent", payload={...}))

    Or use the global default bus via @event_handler decorator.

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

        This method now persists events to EventLog before dispatching to handlers,
        providing an audit trail and enabling event replay.

        NOTE: Still synchronous in-process dispatch. Celery integration comes later.

        TODO (Epic 1.2 - future micro-tasks):
        - Dispatch to Celery tasks for async processing
        - Add error handling and retry logic for handlers
        - Add observability (logging, metrics, tracing)
        - Implement dead letter queue for failed events

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
            from common.events.models import EventLog

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
            # TODO: Add proper logging with structured logger
            print(f"WARNING: Failed to persist event {event.name} to EventLog: {e}")
            # TODO: Add metrics/alerting for persistence failures

        # Dispatch to all subscribers (synchronous for now)
        for handler in self._subscribers.get(event.name, []):
            try:
                handler(event)
            except Exception as e:
                # TODO: Add proper error handling, logging, and retry logic
                # For now, just log and continue to prevent one bad handler from breaking others
                print(f"Error in event handler for {event.name}: {e}")
                # TODO: Log to EventLog with error status
                # TODO: Send to dead letter queue if retries exhausted


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
