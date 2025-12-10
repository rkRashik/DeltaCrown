"""
Event replay service for disaster recovery and reprocessing.

This service enables replaying events from EventLog to reprocess failed events
or recover from system failures. Events can be replayed individually or in bulk
based on filters (date range, event name, correlation ID).

Phase 8, Epic 8.1 Implementation:
- ✅ Replay single event by EventLog ID
- ✅ Replay events in bulk (date range, event name, correlation ID)
- ✅ Dry-run mode to preview replay without executing
- ✅ Mark replayed events in metadata (is_replay=True)
- ✅ Support replaying from all statuses (DEAD_LETTER, FAILED, PROCESSED)
- ⏳ Idempotency tracking (deduplicate replays) (future)
- ⏳ Replay scheduling (delayed replay at specific time) (future)

Event Replay Design:
- Reconstruct Event from EventLog.payload and metadata
- Republish via EventBus.publish() with is_replay=True in metadata
- Optionally reset status to PENDING before replay (for DEAD_LETTER/FAILED)
- Handlers should be idempotent to safely handle replayed events

Usage:
    from apps.common.events.replay_service import EventReplayService
    
    service = EventReplayService()
    
    # Replay single event
    service.replay_event(event_log_id=123)
    
    # Replay events in date range
    service.replay_events(
        event_name="MatchCompletedEvent",
        from_date=datetime(2025, 12, 1),
        to_date=datetime(2025, 12, 10)
    )
    
    # Dry-run to preview without executing
    events = service.replay_events_dry_run(
        event_name="MatchCompletedEvent",
        from_date=datetime(2025, 12, 1)
    )
    print(f"Would replay {len(events)} events")

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 8, Epic 8.1
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from django.db.models import Q, QuerySet
from django.utils import timezone

logger = logging.getLogger("common.events.replay")


class EventReplayService:
    """
    Service for replaying events from EventLog.

    This service reconstructs events from EventLog and republishes them via
    EventBus for reprocessing. Useful for disaster recovery, fixing failed
    events, or backfilling data after code changes.

    Methods:
        replay_event: Replay single event by ID
        replay_events: Replay events matching filters
        replay_events_dry_run: Preview events that would be replayed
    """

    def replay_event(
        self,
        event_log_id: int,
        reset_status: bool = True,
        user_id: Optional[int] = None,
    ) -> bool:
        """
        Replay a single event by reconstructing and republishing it.

        Args:
            event_log_id: ID of the EventLog to replay
            reset_status: If True, reset DEAD_LETTER/FAILED events to PENDING before replay
            user_id: Optional user ID who initiated the replay (for audit)

        Returns:
            True if replayed successfully, False if event not found

        Example:
            service.replay_event(event_log_id=123, user_id=456)
        """
        from apps.common.events.models import EventLog
        from apps.common.events.event_bus import Event, get_event_bus

        try:
            event_log = EventLog.objects.get(id=event_log_id)

            # Reset status if requested (for failed/dead-letter events)
            if reset_status and event_log.status in [
                EventLog.STATUS_FAILED,
                EventLog.STATUS_DEAD_LETTER,
            ]:
                event_log.reset_for_replay()
                logger.info(
                    f"Reset event {event_log_id} status to PENDING before replay",
                    extra={
                        "event_log_id": event_log_id,
                        "event_name": event_log.name,
                    },
                )

            # Reconstruct Event from EventLog
            metadata = event_log.metadata.copy() if event_log.metadata else {}
            metadata["is_replay"] = True
            metadata["replayed_at"] = timezone.now().isoformat()
            metadata["replayed_from_event_log_id"] = event_log_id
            if user_id:
                metadata["replayed_by_user_id"] = user_id

            event = Event(
                name=event_log.name,
                payload=event_log.payload,
                occurred_at=event_log.occurred_at,
                user_id=event_log.user_id,
                correlation_id=event_log.correlation_id,
                metadata=metadata,
            )

            # Republish via EventBus
            get_event_bus().publish(event)

            logger.info(
                f"Replayed event {event_log_id}: {event_log.name}",
                extra={
                    "event_log_id": event_log_id,
                    "event_name": event_log.name,
                    "replayed_by_user_id": user_id,
                },
            )

            return True

        except EventLog.DoesNotExist:
            logger.warning(
                f"Cannot replay event {event_log_id}: not found",
                extra={"event_log_id": event_log_id},
            )
            return False
        except Exception as exc:
            logger.error(
                f"Error replaying event {event_log_id}: {exc}",
                extra={"event_log_id": event_log_id},
                exc_info=True,
            )
            return False

    def replay_events(
        self,
        event_name: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        status: Optional[str] = None,
        reset_status: bool = True,
        limit: int = 100,
        user_id: Optional[int] = None,
    ) -> int:
        """
        Replay multiple events matching filters.

        Args:
            event_name: Filter by event type (e.g., "MatchCompletedEvent")
            from_date: Replay events that occurred on or after this date
            to_date: Replay events that occurred on or before this date
            correlation_id: Filter by correlation ID (related events)
            status: Filter by status (DEAD_LETTER, FAILED, PROCESSED, etc.)
            reset_status: If True, reset DEAD_LETTER/FAILED events to PENDING before replay
            limit: Maximum number of events to replay (default 100)
            user_id: Optional user ID who initiated the replay (for audit)

        Returns:
            Number of events successfully replayed

        Example:
            count = service.replay_events(
                event_name="MatchCompletedEvent",
                from_date=datetime(2025, 12, 1),
                to_date=datetime(2025, 12, 10),
                status="DEAD_LETTER",
                limit=50
            )
            print(f"Replayed {count} events")
        """
        from apps.common.events.models import EventLog

        # Build query
        queryset = self._build_replay_query(
            event_name=event_name,
            from_date=from_date,
            to_date=to_date,
            correlation_id=correlation_id,
            status=status,
            limit=limit,
        )

        # Replay each event
        replayed_count = 0
        failed_count = 0

        for event_log in queryset:
            success = self.replay_event(
                event_log_id=event_log.id,
                reset_status=reset_status,
                user_id=user_id,
            )
            if success:
                replayed_count += 1
            else:
                failed_count += 1

        logger.info(
            f"Bulk replay completed: {replayed_count} succeeded, {failed_count} failed",
            extra={
                "replayed_count": replayed_count,
                "failed_count": failed_count,
                "event_name": event_name,
                "from_date": from_date,
                "to_date": to_date,
                "status": status,
                "user_id": user_id,
            },
        )

        return replayed_count

    def replay_events_dry_run(
        self,
        event_name: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> QuerySet:
        """
        Dry-run mode: return events that would be replayed without executing.

        Use this to preview which events would be replayed before committing.

        Args:
            event_name: Filter by event type
            from_date: Filter events on or after this date
            to_date: Filter events on or before this date
            correlation_id: Filter by correlation ID
            status: Filter by status
            limit: Maximum number of events to preview

        Returns:
            QuerySet of EventLog instances that would be replayed

        Example:
            events = service.replay_events_dry_run(
                event_name="MatchCompletedEvent",
                status="DEAD_LETTER"
            )
            print(f"Would replay {events.count()} events:")
            for event in events[:10]:
                print(f"  - {event.id}: {event.name} at {event.occurred_at}")
        """
        queryset = self._build_replay_query(
            event_name=event_name,
            from_date=from_date,
            to_date=to_date,
            correlation_id=correlation_id,
            status=status,
            limit=limit,
        )

        logger.info(
            f"Dry-run: Would replay {queryset.count()} events",
            extra={
                "event_name": event_name,
                "from_date": from_date,
                "to_date": to_date,
                "status": status,
                "limit": limit,
            },
        )

        return queryset

    def _build_replay_query(
        self,
        event_name: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> QuerySet:
        """
        Internal helper to build EventLog query for replay operations.

        Args:
            event_name: Filter by event type
            from_date: Filter events on or after this date
            to_date: Filter events on or before this date
            correlation_id: Filter by correlation ID
            status: Filter by status
            limit: Maximum number of results

        Returns:
            QuerySet of EventLog instances matching filters
        """
        from apps.common.events.models import EventLog

        # Start with all events (no default status filter - can replay any status)
        queryset = EventLog.objects.all()

        # Apply optional filters
        if event_name:
            queryset = queryset.filter(name=event_name)

        if from_date:
            queryset = queryset.filter(occurred_at__gte=from_date)

        if to_date:
            queryset = queryset.filter(occurred_at__lte=to_date)

        if correlation_id:
            queryset = queryset.filter(correlation_id=correlation_id)

        if status:
            queryset = queryset.filter(status=status)

        # Order by occurred_at to replay in chronological order
        queryset = queryset.order_by("occurred_at", "created_at")

        # Apply limit
        queryset = queryset[:limit]

        return queryset
