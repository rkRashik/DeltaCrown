"""
Dead Letter Queue (DLQ) service for managing permanently failed events.

This service provides tools for querying, acknowledging, and managing events
that have failed processing after exceeding the maximum retry threshold.

Phase 8, Epic 8.1 Implementation:
- ✅ Query dead-letter events with filters (name, date range, retry count)
- ✅ Acknowledge events (mark as reviewed, not for replay)
- ✅ Schedule events for replay (reset status to PENDING)
- ✅ Bulk operations for managing multiple events
- ⏳ Auto-archive old dead-letter events (future)
- ⏳ Alert integration for critical event failures (future)

Dead Letter Queue Design:
- Uses EventLog.status = DEAD_LETTER (no separate model needed)
- Events move to DLQ when retry_count >= EVENTS_MAX_RETRIES
- DLQ events can be: acknowledged (reviewed, no action), scheduled for replay
- Replay is handled by EventReplayService (separate module)

Usage:
    from apps.common.events.dead_letter_service import DeadLetterService
    
    service = DeadLetterService()
    
    # Query dead-letter events
    events = service.list_dead_letter_events(
        event_name="MatchCompletedEvent",
        from_date="2025-12-01",
        to_date="2025-12-10"
    )
    
    # Acknowledge event (mark as reviewed)
    service.acknowledge_event(event_log_id=123)
    
    # Schedule for replay (resets status to PENDING)
    service.schedule_for_replay(event_log_id=123)

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 8, Epic 8.1
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from django.db.models import Q, QuerySet
from django.utils import timezone

logger = logging.getLogger("common.events.dead_letter")


class DeadLetterService:
    """
    Service for managing Dead Letter Queue (DLQ) events.

    This service provides operations for querying, acknowledging, and
    scheduling replay of events that permanently failed processing.

    Methods:
        list_dead_letter_events: Query DLQ with filters
        acknowledge_event: Mark event as reviewed (no replay needed)
        schedule_for_replay: Reset event status to PENDING for retry
        get_dead_letter_stats: Get summary statistics (count by event name, etc.)
    """

    def list_dead_letter_events(
        self,
        event_name: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_retry_count: Optional[int] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> QuerySet:
        """
        Query dead-letter events with optional filters.

        Args:
            event_name: Filter by event type (e.g., "MatchCompletedEvent")
            from_date: Filter events that occurred on or after this date
            to_date: Filter events that occurred on or before this date
            min_retry_count: Filter events with retry_count >= this value
            correlation_id: Filter by correlation ID (related events)
            limit: Maximum number of results to return (default 100)

        Returns:
            QuerySet of EventLog instances with status=DEAD_LETTER

        Example:
            events = service.list_dead_letter_events(
                event_name="MatchCompletedEvent",
                from_date=datetime(2025, 12, 1),
                limit=50
            )
            for event in events:
                print(f"Event {event.id}: {event.name} - {event.last_error}")
        """
        from apps.common.events.models import EventLog

        # Start with dead-letter filter
        queryset = EventLog.objects.filter(status=EventLog.STATUS_DEAD_LETTER)

        # Apply optional filters
        if event_name:
            queryset = queryset.filter(name=event_name)

        if from_date:
            queryset = queryset.filter(occurred_at__gte=from_date)

        if to_date:
            queryset = queryset.filter(occurred_at__lte=to_date)

        if min_retry_count is not None:
            queryset = queryset.filter(retry_count__gte=min_retry_count)

        if correlation_id:
            queryset = queryset.filter(correlation_id=correlation_id)

        # Order by most recent first
        queryset = queryset.order_by("-last_error_at", "-created_at")

        # Apply limit
        queryset = queryset[:limit]

        logger.info(
            f"Listed {queryset.count()} dead-letter events",
            extra={
                "event_name": event_name,
                "from_date": from_date,
                "to_date": to_date,
                "min_retry_count": min_retry_count,
                "correlation_id": correlation_id,
                "limit": limit,
            },
        )

        return queryset

    def acknowledge_event(self, event_log_id: int, notes: Optional[str] = None) -> bool:
        """
        Acknowledge a dead-letter event (mark as reviewed, no replay needed).

        This adds metadata to indicate the event was reviewed and requires no
        further action. The event remains in DEAD_LETTER status for audit purposes.

        Args:
            event_log_id: ID of the EventLog to acknowledge
            notes: Optional notes from reviewer (reason for acknowledging)

        Returns:
            True if acknowledged successfully, False if event not found or not in DLQ

        Example:
            service.acknowledge_event(
                event_log_id=123,
                notes="Duplicate event, original already processed"
            )
        """
        from apps.common.events.models import EventLog

        try:
            event_log = EventLog.objects.get(id=event_log_id)

            # Verify event is in dead-letter status
            if event_log.status != EventLog.STATUS_DEAD_LETTER:
                logger.warning(
                    f"Cannot acknowledge event {event_log_id}: not in DEAD_LETTER status",
                    extra={
                        "event_log_id": event_log_id,
                        "current_status": event_log.status,
                    },
                )
                return False

            # Add acknowledgment metadata
            metadata = event_log.metadata or {}
            metadata["acknowledged_at"] = timezone.now().isoformat()
            metadata["acknowledged"] = True
            if notes:
                metadata["acknowledgment_notes"] = notes

            event_log.metadata = metadata
            event_log.save(update_fields=["metadata"])

            logger.info(
                f"Acknowledged dead-letter event {event_log_id}",
                extra={
                    "event_log_id": event_log_id,
                    "event_name": event_log.name,
                    "notes": notes,
                },
            )

            return True

        except EventLog.DoesNotExist:
            logger.warning(
                f"Cannot acknowledge event {event_log_id}: not found",
                extra={"event_log_id": event_log_id},
            )
            return False

    def schedule_for_replay(self, event_log_id: int) -> bool:
        """
        Schedule a dead-letter event for replay by resetting status to PENDING.

        This resets the event's processing status and retry counter, allowing
        the EventReplayService to republish the event for another attempt.

        Args:
            event_log_id: ID of the EventLog to schedule for replay

        Returns:
            True if scheduled successfully, False if event not found or not in DLQ

        Example:
            service.schedule_for_replay(event_log_id=123)
        """
        from apps.common.events.models import EventLog

        try:
            event_log = EventLog.objects.get(id=event_log_id)

            # Verify event is in dead-letter status
            if event_log.status != EventLog.STATUS_DEAD_LETTER:
                logger.warning(
                    f"Cannot schedule replay for event {event_log_id}: not in DEAD_LETTER status",
                    extra={
                        "event_log_id": event_log_id,
                        "current_status": event_log.status,
                    },
                )
                return False

            # Reset event for replay using EventLog method
            event_log.reset_for_replay()

            # Add replay scheduling metadata
            metadata = event_log.metadata or {}
            metadata["scheduled_for_replay_at"] = timezone.now().isoformat()
            event_log.metadata = metadata
            event_log.save(update_fields=["metadata"])

            logger.info(
                f"Scheduled dead-letter event {event_log_id} for replay",
                extra={
                    "event_log_id": event_log_id,
                    "event_name": event_log.name,
                },
            )

            return True

        except EventLog.DoesNotExist:
            logger.warning(
                f"Cannot schedule replay for event {event_log_id}: not found",
                extra={"event_log_id": event_log_id},
            )
            return False

    def get_dead_letter_stats(self) -> Dict[str, any]:
        """
        Get summary statistics about dead-letter events.

        Returns:
            Dictionary with stats:
            - total_count: Total dead-letter events
            - by_event_name: Count by event type
            - oldest_event: Oldest dead-letter event timestamp
            - newest_event: Newest dead-letter event timestamp

        Example:
            stats = service.get_dead_letter_stats()
            print(f"Total DLQ events: {stats['total_count']}")
            for event_name, count in stats['by_event_name'].items():
                print(f"  {event_name}: {count}")
        """
        from apps.common.events.models import EventLog
        from django.db.models import Count, Min, Max

        queryset = EventLog.objects.filter(status=EventLog.STATUS_DEAD_LETTER)

        stats = {
            "total_count": queryset.count(),
            "by_event_name": {},
            "oldest_event": None,
            "newest_event": None,
        }

        # Count by event name
        by_name = queryset.values("name").annotate(count=Count("id"))
        for item in by_name:
            stats["by_event_name"][item["name"]] = item["count"]

        # Get oldest and newest
        aggregates = queryset.aggregate(
            oldest=Min("last_error_at"), newest=Max("last_error_at")
        )
        stats["oldest_event"] = aggregates["oldest"]
        stats["newest_event"] = aggregates["newest"]

        logger.info(
            f"Dead-letter stats: {stats['total_count']} events",
            extra={"stats": stats},
        )

        return stats
