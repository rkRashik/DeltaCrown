"""
Event persistence models.

This module defines the EventLog model for persisting domain events to the database.
Event persistence enables audit trails, event replay, and debugging.

Implementation Status:
- ✅ Phase 1, Epic 1.2: EventLog model skeleton, EventBus integration
- ✅ Phase 8, Epic 8.1: Event System Hardening & Observability
  - ✅ Status field (PENDING, PROCESSING, PROCESSED, FAILED, DEAD_LETTER)
  - ✅ Retry metadata (retry_count, last_error, last_error_at)
  - ✅ Indexes for DLQ queries and event replay
  - ✅ Dead Letter Queue (DLQ) management
  - ✅ Event replay functionality
- ⏳ Cleanup/archival policies for old events (future)
- ⏳ Partitioning strategy for high-volume events (future)

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 8, Epic 8.1
"""

from django.db import models
from django.utils import timezone


class EventLog(models.Model):
    """
    Persistent audit log of domain events with observability and replay support.

    This model stores all events published through the EventBus for:
    - Audit trails and compliance
    - Debugging and troubleshooting
    - Event replay and recovery
    - Analytics and observability
    - Dead Letter Queue (DLQ) for failed events

    Phase 8, Epic 8.1 Enhancements:
    - Status tracking: PENDING → PROCESSING → PROCESSED/FAILED → DEAD_LETTER
    - Retry metadata: retry_count, last_error, last_error_at
    - DLQ threshold: Events moved to DEAD_LETTER after max retries exceeded
    - Event replay: Reconstruct events from EventLog for disaster recovery

    Status Lifecycle:
        PENDING: Event created, awaiting processing
        PROCESSING: Event currently being processed by handler
        PROCESSED: Event successfully processed
        FAILED: Event processing failed, will retry (if retry_count < max_retries)
        DEAD_LETTER: Event permanently failed (retry_count >= max_retries)

    Attributes:
        name: Event type identifier (e.g., "MatchCompletedEvent")
        payload: Business data specific to this event (JSON)
        occurred_at: When the event occurred (UTC)
        user_id: Optional ID of the user who triggered this event
        correlation_id: Optional ID to correlate related events across services
        metadata: Additional context (request_id, source_service, is_replay, etc.)
        created_at: When this record was created in the database
        status: Current processing status (PENDING, PROCESSING, PROCESSED, FAILED, DEAD_LETTER)
        retry_count: Number of processing attempts (0 on creation)
        last_error: Error message from most recent failed processing attempt
        last_error_at: Timestamp of most recent error

    Reference: CLEANUP_AND_TESTING_PART_6.md - §3.1 (Event-Driven Workflows)
    """

    # Status choices for event processing lifecycle
    STATUS_PENDING = "PENDING"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_PROCESSED = "PROCESSED"
    STATUS_FAILED = "FAILED"
    STATUS_DEAD_LETTER = "DEAD_LETTER"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_PROCESSED, "Processed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_DEAD_LETTER, "Dead Letter"),
    ]

    # Core event fields (Phase 1, Epic 1.2)
    name = models.CharField(max_length=255, help_text="Event type identifier")
    payload = models.JSONField(help_text="Event business data")
    occurred_at = models.DateTimeField(help_text="When the event occurred (UTC)")
    user_id = models.IntegerField(
        null=True, blank=True, help_text="User who triggered the event"
    )
    correlation_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Correlation ID for related events",
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional event context"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When this log entry was created"
    )

    # Observability & DLQ fields (Phase 8, Epic 8.1)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text="Event processing status",
    )
    retry_count = models.IntegerField(
        default=0, help_text="Number of processing attempts"
    )
    last_error = models.TextField(
        null=True, blank=True, help_text="Error message from most recent failure"
    )
    last_error_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of most recent error"
    )

    class Meta:
        app_label = "common"  # Explicit app_label since 'common' is not in INSTALLED_APPS
        ordering = ["-created_at"]
        verbose_name = "Event Log"
        verbose_name_plural = "Event Logs"
        indexes = [
            models.Index(fields=["name", "-occurred_at"], name="evt_name_occurred"),
            models.Index(fields=["correlation_id"], name="evt_correlation"),
            models.Index(fields=["user_id", "-occurred_at"], name="evt_user_occurred"),
            models.Index(fields=["status", "-created_at"], name="evt_status_created"),
            models.Index(fields=["-occurred_at"], name="evt_occurred_desc"),
        ]

    def __str__(self) -> str:
        """String representation for admin panel."""
        return f"{self.name} at {self.occurred_at} ({self.status})"

    def mark_processing(self) -> None:
        """
        Mark event as currently being processed.

        Called by Celery task or EventBus when event processing starts.
        """
        self.status = self.STATUS_PROCESSING
        self.save(update_fields=["status"])

    def mark_processed(self) -> None:
        """
        Mark event as successfully processed.

        Called by Celery task when all handlers complete without errors.
        """
        self.status = self.STATUS_PROCESSED
        self.save(update_fields=["status"])

    def mark_failed(self, error_message: str) -> None:
        """
        Mark event as failed and increment retry counter.

        Args:
            error_message: Error description from failed processing attempt
        """
        self.status = self.STATUS_FAILED
        self.retry_count += 1
        self.last_error = error_message[:5000]  # Truncate to avoid DB overflow
        self.last_error_at = timezone.now()
        self.save(update_fields=["status", "retry_count", "last_error", "last_error_at"])

    def mark_dead_letter(self, error_message: str) -> None:
        """
        Mark event as permanently failed (sent to Dead Letter Queue).

        Called when retry_count exceeds EVENTS_MAX_RETRIES threshold.

        Args:
            error_message: Final error description
        """
        self.status = self.STATUS_DEAD_LETTER
        self.retry_count += 1
        self.last_error = error_message[:5000]
        self.last_error_at = timezone.now()
        self.save(update_fields=["status", "retry_count", "last_error", "last_error_at"])

    def reset_for_replay(self) -> None:
        """
        Reset event status to PENDING for manual replay.

        Called by EventReplayService when replaying events from DLQ or history.
        """
        self.status = self.STATUS_PENDING
        self.retry_count = 0
        self.last_error = None
        self.last_error_at = None
        self.save(update_fields=["status", "retry_count", "last_error", "last_error_at"])
