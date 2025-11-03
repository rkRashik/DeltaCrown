# apps/notifications/admin/notifications.py
from django.contrib import admin

from ..models import Notification

try:
    from apps.corelib.admin_utils import _safe_select_related
except Exception:
    def _safe_select_related(qs, *fields):
        try:
            return qs.select_related(*fields)
        except Exception:
            return qs

try:
    from .exports import export_notifications_csv
except Exception:
    def export_notifications_csv(modeladmin, request, queryset):
        modeladmin.message_user(request, "CSV export unavailable.", level=20)  # INFO


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Read-only notifications admin with CSV export.
    """
    actions = [export_notifications_csv]
    list_display = (
        "id",
        "recipient_display",
        "type",
        "title",
        "is_read_display",
        "created_at_display",
        "tournament_display",
        "match_display",
    )
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("title", "body", "recipient__user__username", "recipient__display_name")
    readonly_fields = ("recipient", "type", "title", "body", "url", "is_read", "created_at", "tournament_id", "match_id")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return _safe_select_related(qs, "recipient__user")

    # ---- safe accessors ----
    def recipient_display(self, obj):
        p = getattr(obj, "recipient", None)
        if not p:
            return "-"
        username = getattr(getattr(p, "user", None), "username", None)
        return username or getattr(p, "display_name", None) or f"Profile#{p.pk}"
    recipient_display.short_description = "Recipient"

    def is_read_display(self, obj):
        return "✔" if getattr(obj, "is_read", False) else "—"
    is_read_display.short_description = "Read?"

    def created_at_display(self, obj):
        return getattr(obj, "created_at", None) or "-"
    created_at_display.short_description = "Created"

    def tournament_display(self, obj):
        tid = getattr(obj, "tournament_id", None)
        return f"Tournament #{tid}" if tid else "—"
    tournament_display.short_description = "Tournament"

    def match_display(self, obj):
        mid = getattr(obj, "match_id", None)
        return f"Match #{mid}" if mid else "—"
    match_display.short_description = "Match"
