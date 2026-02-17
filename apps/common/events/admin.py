"""
Django admin configuration for EventLog model.

Phase 8, Epic 8.1 Enhancements:
- List display with status, retry_count, last_error columns
- List filters: status, event name, date
- Search by event name, correlation_id
- Admin action: replay_events (bulk replay selected events)
- Readonly fields for audit data

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 8, Epic 8.1
"""

from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html
from django.contrib import messages

from apps.common.events.models import EventLog
from apps.common.events.replay_service import EventReplayService


class EventLogAdmin(ModelAdmin):
    """
    Django admin interface for EventLog model with Epic 8.1 enhancements.
    """

    list_display = [
        "id",
        "name",
        "status_badge",
        "occurred_at",
        "retry_count",
        "last_error_at",
        "correlation_id",
    ]

    list_filter = [
        "status",
        "name",
        ("occurred_at", admin.DateFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    ]

    search_fields = [
        "name",
        "correlation_id",
        "metadata",
    ]

    readonly_fields = [
        "id",
        "name",
        "payload",
        "occurred_at",
        "user_id",
        "correlation_id",
        "metadata",
        "created_at",
        "status",
        "retry_count",
        "last_error",
        "last_error_at",
    ]

    ordering = ["-created_at"]

    actions = ["replay_selected_events", "acknowledge_events"]

    def status_badge(self, obj):
        """Display status as colored badge."""
        color_map = {
            EventLog.STATUS_PENDING: "gray",
            EventLog.STATUS_PROCESSING: "blue",
            EventLog.STATUS_PROCESSED: "green",
            EventLog.STATUS_FAILED: "orange",
            EventLog.STATUS_DEAD_LETTER: "red",
        }
        color = color_map.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status,
        )

    status_badge.short_description = "Status"

    def replay_selected_events(self, request, queryset):
        """Admin action to replay selected events."""
        service = EventReplayService()
        replayed_count = 0
        failed_count = 0

        for event_log in queryset:
            success = service.replay_event(
                event_log_id=event_log.id,
                reset_status=True,
                user_id=request.user.id if request.user.is_authenticated else None,
            )
            if success:
                replayed_count += 1
            else:
                failed_count += 1

        self.message_user(
            request,
            f"Replayed {replayed_count} event(s) successfully. {failed_count} failed.",
            level=messages.SUCCESS if failed_count == 0 else messages.WARNING,
        )

    replay_selected_events.short_description = "Replay selected events"

    def acknowledge_events(self, request, queryset):
        """Admin action to acknowledge dead-letter events."""
        from apps.common.events.dead_letter_service import DeadLetterService

        service = DeadLetterService()
        acknowledged_count = 0

        for event_log in queryset.filter(status=EventLog.STATUS_DEAD_LETTER):
            success = service.acknowledge_event(
                event_log_id=event_log.id,
                notes=f"Acknowledged by {request.user.username} via Django admin",
            )
            if success:
                acknowledged_count += 1

        self.message_user(
            request,
            f"Acknowledged {acknowledged_count} dead-letter event(s).",
            level=messages.SUCCESS,
        )

    acknowledge_events.short_description = "Acknowledge dead-letter events"


# Register EventLog with custom admin
admin.site.register(EventLog, EventLogAdmin)
