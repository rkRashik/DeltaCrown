# apps/notifications/admin/notifications.py
from django.contrib import admin
from apps.corelib.admin_utils import _path_exists

from ..models import Notification
from .exports import export_notifications_csv
from apps.corelib.admin_utils import _safe_select_related


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Notifications admin that is tolerant of small schema variations.
    We keep accessors defensive to avoid admin system-check errors.
    """
    actions = [export_notifications_csv]

    # Keep list_display conservative and use safe accessors
    list_display = ("id", "recipient_display", "is_read_display", "created_at_display")

    # No brittle filters/search fields unless you explicitly add fields in the model
    list_filter = ()
    search_fields = ()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Try to avoid N+1 on a “user-like” relation in a schema-tolerant way.
        for rel in ("user", "recipient", "to_user", "profile__user", "user_profile__user"):
            try:
                if _path_exists(Notification, rel):
                    qs = qs.select_related(rel)
            except Exception:
                # Be defensive: ignore if an unexpected model tweak breaks a path
                pass
        return qs


    # ---- Query optimization (safe) ----
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Try common user-like relations if they exist; ignore missing ones.
        return _safe_select_related(
            qs,
            "user",
            "recipient",
            "to_user",
            "profile__user",
            "user_profile__user",
        )

    # ---- Safe accessors ----
    def recipient_display(self, obj):
        u = (
            getattr(obj, "user", None)
            or getattr(obj, "recipient", None)
            or getattr(obj, "to_user", None)
            or getattr(getattr(obj, "profile", None), "user", None)
            or getattr(getattr(obj, "user_profile", None), "user", None)
        )
        # If user-like, prefer username
        if hasattr(u, "username"):
            return u.username
        # Fallback to readable string or dash
        return str(u) if u else "-"

    recipient_display.short_description = "Recipient"

    def is_read_display(self, obj):
        val = getattr(obj, "is_read", None)
        if val is None:
            val = getattr(obj, "read", None)
        return val if val is not None else "-"

    is_read_display.short_description = "Read?"

    def created_at_display(self, obj):
        val = (
            getattr(obj, "created_at", None)
            or getattr(obj, "created", None)
            or getattr(obj, "created_on", None)
            or getattr(obj, "timestamp", None)
        )
        return val or "-"

    created_at_display.short_description = "Created"
