"""
Event persistence models.

This module defines the EventLog model for persisting domain events to the database.
Event persistence enables audit trails, event replay, and debugging.

Implementation Status (Phase 1, Epic 1.2):
- ✅ EventLog model skeleton defined
- ⏳ Integration with EventBus.publish() (next micro-task)
- ⏳ Migrations and admin panel registration (next micro-task)
- ⏳ Indexing strategy for performance (future)
- ⏳ Cleanup/archival policies for old events (future)
- ⏳ Event replay tools (future)

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.2
"""

from django.db import models


class EventLog(models.Model):
    """
    Persistent audit log of domain events.

    This model stores all events published through the EventBus for:
    - Audit trails and compliance
    - Debugging and troubleshooting
    - Event replay and recovery
    - Analytics and observability

    Future enhancements:
    - TODO: Add indexes on name, occurred_at, user_id, correlation_id for query performance
    - TODO: Add status field to track processing state (pending, processed, failed, retrying)
    - TODO: Add retry_count and last_error fields for retry logic
    - TODO: Add partitioning strategy for high-volume events
    - TODO: Add cleanup/archival policies (e.g., archive events older than 90 days)
    - TODO: Create admin panel interface for viewing and replaying events
    - TODO: Add event replay functionality for disaster recovery

    Attributes:
        name: Event type identifier (e.g., "MatchCompletedEvent")
        payload: Business data specific to this event (JSON)
        occurred_at: When the event occurred (UTC)
        user_id: Optional ID of the user who triggered this event
        correlation_id: Optional ID to correlate related events across services
        metadata: Additional context (request_id, source_service, etc.)
        created_at: When this record was created in the database

    Reference: CLEANUP_AND_TESTING_PART_6.md - §3.1 (Event-Driven Workflows)
    """

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

    class Meta:
        app_label = "common"  # Explicit app_label since 'common' is not in INSTALLED_APPS
        ordering = ["-created_at"]
        verbose_name = "Event Log"
        verbose_name_plural = "Event Logs"

        # TODO: Add indexes in a future migration:
        # indexes = [
        #     models.Index(fields=["name", "-occurred_at"]),
        #     models.Index(fields=["correlation_id"]),
        #     models.Index(fields=["user_id", "-occurred_at"]),
        # ]

    def __str__(self) -> str:
        """String representation for admin panel."""
        return f"{self.name} at {self.occurred_at}"
