"""
Unit tests for EventLog model status tracking and DLQ functionality.

Tests status lifecycle methods, retry metadata updates, and DLQ threshold logic.

Phase 8, Epic 8.1
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone

from apps.common.events.models import EventLog


@pytest.mark.django_db
class TestEventLogStatusTracking:
    """Test EventLog status lifecycle methods (Epic 8.1)."""

    def test_event_log_created_with_pending_status(self):
        """EventLog should default to PENDING status on creation."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={"test": "data"},
            occurred_at=timezone.now(),
        )

        assert event_log.status == EventLog.STATUS_PENDING
        assert event_log.retry_count == 0
        assert event_log.last_error is None
        assert event_log.last_error_at is None

    def test_mark_processing(self):
        """mark_processing() should update status to PROCESSING."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={"test": "data"},
            occurred_at=timezone.now(),
        )

        event_log.mark_processing()
        event_log.refresh_from_db()

        assert event_log.status == EventLog.STATUS_PROCESSING
        assert event_log.retry_count == 0  # Unchanged

    def test_mark_processed(self):
        """mark_processed() should update status to PROCESSED."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={"test": "data"},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_PROCESSING,
        )

        event_log.mark_processed()
        event_log.refresh_from_db()

        assert event_log.status == EventLog.STATUS_PROCESSED
        assert event_log.retry_count == 0  # Unchanged

    def test_mark_failed(self):
        """mark_failed() should update status, increment retry_count, store error."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={"test": "data"},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_PROCESSING,
        )

        error_message = "Connection timeout"
        before_error_time = timezone.now()
        event_log.mark_failed(error_message)
        event_log.refresh_from_db()

        assert event_log.status == EventLog.STATUS_FAILED
        assert event_log.retry_count == 1
        assert event_log.last_error == error_message
        assert event_log.last_error_at is not None
        assert event_log.last_error_at >= before_error_time

    def test_mark_failed_increments_retry_count(self):
        """mark_failed() should increment retry_count on each call."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={"test": "data"},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_PROCESSING,
        )

        # Fail multiple times
        event_log.mark_failed("Error 1")
        event_log.mark_failed("Error 2")
        event_log.mark_failed("Error 3")
        event_log.refresh_from_db()

        assert event_log.retry_count == 3
        assert event_log.last_error == "Error 3"  # Latest error

    def test_mark_dead_letter(self):
        """mark_dead_letter() should move event to DLQ status."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={"test": "data"},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_FAILED,
            retry_count=3,
        )

        error_message = "Max retries exceeded"
        event_log.mark_dead_letter(error_message)
        event_log.refresh_from_db()

        assert event_log.status == EventLog.STATUS_DEAD_LETTER
        assert event_log.retry_count == 4  # Incremented
        assert event_log.last_error == error_message

    def test_reset_for_replay(self):
        """reset_for_replay() should reset event to PENDING with cleared error state."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={"test": "data"},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_DEAD_LETTER,
            retry_count=5,
            last_error="Previous error",
            last_error_at=timezone.now(),
        )

        event_log.reset_for_replay()
        event_log.refresh_from_db()

        assert event_log.status == EventLog.STATUS_PENDING
        assert event_log.retry_count == 0
        assert event_log.last_error is None
        assert event_log.last_error_at is None

    def test_long_error_message_truncated(self):
        """Long error messages should be truncated to avoid DB overflow."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={"test": "data"},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_PROCESSING,
        )

        # Create a 6000-character error message
        long_error = "A" * 6000
        event_log.mark_failed(long_error)
        event_log.refresh_from_db()

        # Should be truncated to 5000 chars
        assert len(event_log.last_error) == 5000
        assert event_log.last_error == "A" * 5000


@pytest.mark.django_db
class TestEventLogQuerying:
    """Test EventLog queries and indexes (Epic 8.1)."""

    def test_query_by_status(self):
        """Should efficiently query events by status."""
        # Create events with different statuses
        EventLog.objects.create(
            name="Event1",
            payload={},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_PENDING,
        )
        EventLog.objects.create(
            name="Event2",
            payload={},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_DEAD_LETTER,
        )
        EventLog.objects.create(
            name="Event3",
            payload={},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_DEAD_LETTER,
        )

        dead_letter_events = EventLog.objects.filter(status=EventLog.STATUS_DEAD_LETTER)
        assert dead_letter_events.count() == 2

    def test_query_by_correlation_id(self):
        """Should efficiently query related events by correlation_id."""
        correlation_id = "test-correlation-123"

        EventLog.objects.create(
            name="Event1",
            payload={},
            occurred_at=timezone.now(),
            correlation_id=correlation_id,
        )
        EventLog.objects.create(
            name="Event2",
            payload={},
            occurred_at=timezone.now(),
            correlation_id=correlation_id,
        )
        EventLog.objects.create(
            name="Event3",
            payload={},
            occurred_at=timezone.now(),
            correlation_id="other",
        )

        related_events = EventLog.objects.filter(correlation_id=correlation_id)
        assert related_events.count() == 2

    def test_str_representation_includes_status(self):
        """__str__() should include status for admin display."""
        event_log = EventLog.objects.create(
            name="TestEvent",
            payload={},
            occurred_at=timezone.now(),
            status=EventLog.STATUS_DEAD_LETTER,
        )

        str_repr = str(event_log)
        assert "TestEvent" in str_repr
        assert "DEAD_LETTER" in str_repr
