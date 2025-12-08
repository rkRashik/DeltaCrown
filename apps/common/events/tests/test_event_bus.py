"""
Unit tests for Event Bus infrastructure.

Tests event publishing, subscription, and persistence WITHOUT requiring
database access. Uses mocks to simulate EventLog persistence.

Phase: 1 (Core Foundation)
Epic: 1.2 (Event Bus Implementation)
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from apps.common.events.event_bus import Event, EventBus, event_handler, get_event_bus


# =============================================================================
# Event Tests
# =============================================================================


def test_event_creation():
    """Test Event dataclass creation."""
    event = Event(
        name="tournament.created",
        payload={"tournament_id": 1, "name": "Summer Cup"},
        occurred_at=datetime(2025, 1, 15, 10, 0),
    )

    assert event.name == "tournament.created"
    assert event.payload["tournament_id"] == 1
    assert event.occurred_at == datetime(2025, 1, 15, 10, 0)


def test_event_to_dict():
    """Test Event.to_dict() serialization."""
    event = Event(
        name="team.registered",
        payload={"team_id": 10},
        occurred_at=datetime(2025, 1, 15, 10, 0),
    )

    data = event.to_dict()
    assert data["name"] == "team.registered"
    assert data["payload"] == {"team_id": 10}
    assert isinstance(data["occurred_at"], str)


# =============================================================================
# EventBus Singleton Tests
# =============================================================================


def test_event_bus_singleton():
    """Test that get_event_bus() returns the same instance."""
    bus1 = get_event_bus()
    bus2 = get_event_bus()

    assert bus1 is bus2


def test_event_bus_subscribe():
    """Test subscribing handlers to event types."""
    bus = EventBus()
    handler_called = []

    def test_handler(event: Event):
        handler_called.append(event.name)

    bus.subscribe("test.event", test_handler)

    # Publish an event
    event = Event(name="test.event", payload={}, occurred_at=datetime.now())
    bus._dispatch_to_handlers(event)

    assert "test.event" in handler_called


def test_event_bus_multiple_subscribers():
    """Test that multiple handlers are called in order."""
    bus = EventBus()
    call_order = []

    def handler1(event: Event):
        call_order.append("handler1")

    def handler2(event: Event):
        call_order.append("handler2")

    bus.subscribe("test.event", handler1)
    bus.subscribe("test.event", handler2)

    event = Event(name="test.event", payload={}, occurred_at=datetime.now())
    bus._dispatch_to_handlers(event)

    assert call_order == ["handler1", "handler2"]


# =============================================================================
# Event Publishing Tests (with mocked persistence)
# =============================================================================


@patch("apps.common.events.models.EventLog")
def test_event_bus_publish_persists_to_db(mock_event_log_class):
    """Test that EventBus.publish() persists event to Event Log."""
    bus = EventBus()
    mock_event_log_class.objects.create = MagicMock()

    event = Event(
        name="tournament.created",
        payload={"tournament_id": 1},
        occurred_at=datetime.now(),
    )

    bus.publish(event)

    # Verify that EventLog.objects.create was called
    mock_event_log_class.objects.create.assert_called_once()
    call_kwargs = mock_event_log_class.objects.create.call_args[1]
    assert call_kwargs["name"] == "tournament.created"
    assert call_kwargs["payload"] == {"tournament_id": 1}


@patch("apps.common.events.models.EventLog")
def test_event_bus_publish_continues_on_persistence_error(mock_event_log_class):
    """
    Test that EventBus.publish() continues dispatching even if persistence fails.

    This ensures that event handlers are still called even if the EventLog
    table doesn't exist yet (before migrations) or if there's a DB error.
    """
    bus = EventBus()
    handler_called = []

    def test_handler(event: Event):
        handler_called.append(event.name)

    bus.subscribe("test.event", test_handler)

    # Make persistence fail
    mock_event_log_class.objects.create.side_effect = Exception("DB error")

    event = Event(name="test.event", payload={}, occurred_at=datetime.now())
    bus.publish(event)

    # Handler should still be called
    assert "test.event" in handler_called


@patch("apps.common.events.models.EventLog")
def test_event_bus_publish_calls_handlers_after_persistence(mock_event_log_class):
    """
    Test that EventBus.publish() calls handlers after persisting to DB.

    Ensures that event is persisted first, then dispatched to handlers.
    """
    bus = EventBus()
    call_sequence = []

    def mock_create(**kwargs):
        call_sequence.append("persist")
        return MagicMock()

    def test_handler(event: Event):
        call_sequence.append("dispatch")

    mock_event_log_class.objects.create = mock_create
    bus.subscribe("test.event", test_handler)

    event = Event(name="test.event", payload={}, occurred_at=datetime.now())
    bus.publish(event)

    assert call_sequence == ["persist", "dispatch"]


# =============================================================================
# Event Handler Decorator Tests
# =============================================================================


def test_event_handler_decorator():
    """Test @event_handler decorator registers handlers."""
    # Note: decorator uses global bus, can't pass custom bus
    handler_called = []

    @event_handler("decorated.event")
    def decorated_handler(event: Event):
        handler_called.append(event.name)

    bus = get_event_bus()
    event = Event(name="decorated.event", payload={}, occurred_at=datetime.now())
    bus._dispatch_to_handlers(event)

    assert "decorated.event" in handler_called


def test_event_handler_decorator_uses_global_bus():
    """Test @event_handler decorator uses global bus by default."""
    handler_called = []

    @event_handler("global.event")
    def global_handler(event: Event):
        handler_called.append(event.name)

    bus = get_event_bus()
    event = Event(name="global.event", payload={}, occurred_at=datetime.now())
    bus._dispatch_to_handlers(event)

    assert "global.event" in handler_called


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_event_bus_handler_error_does_not_stop_other_handlers():
    """
    Test that if one handler raises an exception, other handlers are still called.

    This ensures resilience in event processing.
    """
    bus = EventBus()
    call_order = []

    def failing_handler(event: Event):
        call_order.append("failing")
        raise ValueError("Handler error")

    def success_handler(event: Event):
        call_order.append("success")

    bus.subscribe("test.event", failing_handler)
    bus.subscribe("test.event", success_handler)

    event = Event(name="test.event", payload={}, occurred_at=datetime.now())
    bus._dispatch_to_handlers(event)

    # Both handlers should be called despite the error
    assert "failing" in call_order
    assert "success" in call_order


# =============================================================================
# Integration Tests (without DB)
# =============================================================================


@patch("apps.common.events.models.EventLog")
def test_event_bus_end_to_end_flow(mock_event_log_class):
    """
    End-to-end test: subscribe handlers, publish event, verify persistence and dispatch.
    """
    bus = EventBus()
    mock_event_log_class.objects.create = MagicMock()

    # Track handler calls
    handler_results = []

    def handler1(event: Event):
        handler_results.append(f"handler1:{event.payload['data']}")

    def handler2(event: Event):
        handler_results.append(f"handler2:{event.payload['data']}")

    bus.subscribe("integration.test", handler1)
    bus.subscribe("integration.test", handler2)

    # Publish event
    event = Event(
        name="integration.test",
        payload={"data": "test_value"},
        occurred_at=datetime.now(),
    )
    bus.publish(event)

    # Verify persistence
    mock_event_log_class.objects.create.assert_called_once()

    # Verify handlers called
    assert "handler1:test_value" in handler_results
    assert "handler2:test_value" in handler_results


# ==============================================================================
# Celery Async Dispatch Tests (Phase 1, Epic 1.2)
# ==============================================================================


def test_publish_sync_mode_when_flag_false():
    """Test that events dispatch synchronously when EVENTS_USE_CELERY is False."""
    bus = EventBus()
    handler_called = []

    def test_handler(event: Event):
        handler_called.append(event.name)

    bus.subscribe("test.event", test_handler)

    event = Event(name="test.event", payload={"test": "data"}, occurred_at=datetime.now())

    # Mock EventLog (lazy import inside publish()) and settings
    with patch("apps.common.events.models.EventLog") as mock_event_log:
        with patch("django.conf.settings") as mock_settings:
            # Feature flag disabled
            mock_settings.EVENTS_USE_CELERY = False

            # Publish event
            bus.publish(event)

            # Handler should be called synchronously
            assert "test.event" in handler_called
            # EventLog should be persisted
            mock_event_log.objects.create.assert_called_once()


def test_publish_sync_mode_when_flag_absent():
    """Test that events default to sync dispatch when EVENTS_USE_CELERY is not set."""
    bus = EventBus()
    handler_called = []

    def test_handler(event: Event):
        handler_called.append(event.name)

    bus.subscribe("test.event", test_handler)

    event = Event(name="test.event", payload={"test": "data"}, occurred_at=datetime.now())

    # Mock EventLog and settings without EVENTS_USE_CELERY attribute
    with patch("apps.common.events.models.EventLog") as mock_event_log:
        with patch("django.conf.settings", spec=[]) as mock_settings:
            # No EVENTS_USE_CELERY attribute - should default to False

            # Publish event
            bus.publish(event)

            # Handler should be called synchronously
            assert "test.event" in handler_called
            # EventLog should be persisted
            mock_event_log.objects.create.assert_called_once()


def test_publish_async_mode_when_flag_true():
    """Test that events enqueue to Celery when EVENTS_USE_CELERY is True."""
    bus = EventBus()
    handler_called = []

    def test_handler(event: Event):
        handler_called.append(event.name)

    bus.subscribe("test.event", test_handler)

    event = Event(name="test.event", payload={"test": "data"}, occurred_at=datetime.now())

    # Mock EventLog, settings, and Celery task
    with patch("apps.common.events.models.EventLog") as mock_event_log:
        with patch("django.conf.settings") as mock_settings:
            with patch("apps.common.events.tasks.dispatch_event_task") as mock_task:
                # Feature flag enabled
                mock_settings.EVENTS_USE_CELERY = True

                # Publish event
                bus.publish(event)

                # Celery task should be enqueued with event dict
                mock_task.delay.assert_called_once()
                call_args = mock_task.delay.call_args[0][0]
                assert call_args["name"] == "test.event"
                assert call_args["payload"] == {"test": "data"}
                assert "occurred_at" in call_args

                # Handler should NOT be called (async dispatch)
                assert len(handler_called) == 0

                # EventLog should still be persisted
                mock_event_log.objects.create.assert_called_once()


def test_publish_async_fallback_on_celery_error():
    """Test that publish falls back to sync dispatch if Celery enqueue fails."""
    bus = EventBus()
    handler_called = []

    def test_handler(event: Event):
        handler_called.append(event.name)

    bus.subscribe("test.event", test_handler)

    event = Event(name="test.event", payload={"test": "data"}, occurred_at=datetime.now())

    # Mock EventLog, settings, and Celery task to raise exception
    with patch("apps.common.events.models.EventLog") as mock_event_log:
        with patch("django.conf.settings") as mock_settings:
            with patch("apps.common.events.tasks.dispatch_event_task") as mock_task:
                # Feature flag enabled
                mock_settings.EVENTS_USE_CELERY = True
                # Celery enqueue fails
                mock_task.delay.side_effect = Exception("Celery broker unavailable")

                # Publish event
                bus.publish(event)

                # Should fall back to synchronous dispatch
                assert "test.event" in handler_called

                # EventLog should still be persisted
                mock_event_log.objects.create.assert_called_once()


def test_dispatch_event_task_calls_handlers():
    """Test that dispatch_event_task reconstructs Event and calls handlers."""
    from apps.common.events.tasks import dispatch_event_task

    # Create event dict as if serialized by Event.to_dict()
    event_data = {
        "name": "test.event",
        "payload": {"match_id": 123},
        "occurred_at": "2025-12-08T10:30:00.123456",
        "user_id": 789,
        "correlation_id": "abc-123",
        "metadata": {"source": "test"}
    }

    # Mock EventBus._dispatch_to_handlers (patch where get_event_bus is imported in tasks.py)
    with patch("apps.common.events.event_bus.get_event_bus") as mock_get_bus:
        mock_bus = MagicMock()
        mock_get_bus.return_value = mock_bus

        # Call task (bypass Celery, call directly)
        dispatch_event_task(event_data)

        # Verify _dispatch_to_handlers was called
        mock_bus._dispatch_to_handlers.assert_called_once()
        
        # Verify Event was reconstructed correctly
        reconstructed_event = mock_bus._dispatch_to_handlers.call_args[0][0]
        assert reconstructed_event.name == "test.event"
        assert reconstructed_event.payload == {"match_id": 123}
        assert reconstructed_event.user_id == 789
        assert reconstructed_event.correlation_id == "abc-123"
        assert reconstructed_event.metadata == {"source": "test"}
        # Verify datetime was reconstructed
        assert isinstance(reconstructed_event.occurred_at, datetime)


def test_dispatch_event_task_retries_on_error():
    """Test that dispatch_event_task handles errors and attempts retry."""
    from apps.common.events.tasks import dispatch_event_task

    event_data = {
        "name": "test.event",
        "payload": {"data": "test"},
        "occurred_at": "2025-12-08T10:30:00.123456",
    }

    # Mock EventBus to raise exception
    with patch("apps.common.events.event_bus.get_event_bus") as mock_get_bus:
        mock_bus = MagicMock()
        mock_bus._dispatch_to_handlers.side_effect = Exception("Handler error")
        mock_get_bus.return_value = mock_bus

        # Mock the retry method to track that it was called
        with patch("apps.common.events.tasks.dispatch_event_task.retry") as mock_retry:
            mock_retry.side_effect = Exception("Retry called")
            
            # Call task and expect it to raise from retry
            try:
                dispatch_event_task(event_data)
                assert False, "Should have raised exception from retry"
            except Exception as e:
                # Should have raised from retry
                assert "Retry called" in str(e) or "Handler error" in str(e)


def test_event_reconstruction_from_dict():
    """Test that Event can be reconstructed from to_dict() output."""
    from apps.common.events.tasks import dispatch_event_task

    # Create original event
    original_event = Event(
        name="MatchCompletedEvent",
        payload={"match_id": 123, "winner": "TeamA"},
        occurred_at=datetime(2025, 12, 8, 10, 30, 0, 123456),
        user_id=789,
        correlation_id="test-correlation-123",
        metadata={"source": "game_server", "version": "1.0"}
    )

    # Serialize to dict
    event_dict = original_event.to_dict()

    # Mock EventBus to capture reconstructed event
    captured_events = []
    with patch("apps.common.events.event_bus.get_event_bus") as mock_get_bus:
        mock_bus = MagicMock()
        mock_bus._dispatch_to_handlers.side_effect = lambda e: captured_events.append(e)
        mock_get_bus.return_value = mock_bus

        # Call task to reconstruct event
        dispatch_event_task(event_dict)

        # Verify event was reconstructed correctly
        assert len(captured_events) == 1
        reconstructed = captured_events[0]
        
        assert reconstructed.name == original_event.name
        assert reconstructed.payload == original_event.payload
        assert reconstructed.user_id == original_event.user_id
        assert reconstructed.correlation_id == original_event.correlation_id
        assert reconstructed.metadata == original_event.metadata
        # Datetime should match (within microseconds)
        assert reconstructed.occurred_at == original_event.occurred_at

