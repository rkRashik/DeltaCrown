from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
import csv

from ..models import Notification


# ---------- Helpers ----------

def _path_exists(model, path: str) -> bool:
    """
    Verify a select_related path exists on 'model', supporting spans like 'profile__user'.
    """
    parts = path.split("__")
    m = model
    for p in parts:
        try:
            f = m._meta.get_field(p)
        except Exception:
            return False
        # Require a forward relation to continue spanning
        if not getattr(f, "is_relation", False) or getattr(f, "many_to_many", False):
            return False
        m = f.remote_field.model
    return True


def _safe_select_related(qs, candidate_paths):
    """
    Apply select_related only for paths that exist on the queryset's model.
    """
    model = qs.model
    valid = [p for p in candidate_paths if _path_exists(model, p)]
    return qs.select_related(*valid) if valid else qs


# ---------- Admin Action: Export Notifications to CSV ----------

def export_notifications_csv(modeladmin, request, queryset):
    """
    Export selected Notifications as CSV.
    Columns are chosen to be stable across minor model changes.
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"notifications-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "user_id",
        "user_username",
        "is_read",
        "created_at",
        "text",        # title/verb/message/text (best-effort)
        "url",         # optional
        "kind",        # optional category/type if present
    ])

    # Only select related paths that actually exist for this model
    queryset = _safe_select_related(
        queryset,
        [
            "user",
            "recipient",
            "to_user",
            "profile",
            "user_profile",
            "profile__user",
            "user_profile__user",
        ],
    )

    for n in queryset.order_by("id"):
        # Resolve a "user-like" object if any
        u = (
            getattr(n, "user", None)
            or getattr(n, "recipient", None)
            or getattr(n, "to_user", None)
            or getattr(getattr(n, "profile", None), "user", None)
            or getattr(getattr(n, "user_profile", None), "user", None)
        )
        user_id = getattr(u, "id", "")
        user_username = getattr(u, "username", "") if u else ""

        # Best-effort text extraction across possible field names
        text = (
            getattr(n, "title", None)
            or getattr(n, "verb", None)
            or getattr(n, "message", None)
            or getattr(n, "text", None)
            or ""
        )

        url = getattr(n, "url", "") or getattr(n, "link", "") or ""
        kind = getattr(n, "kind", "") or getattr(n, "category", "") or getattr(n, "type", "") or ""

        # created_at variants
        created = (
            getattr(n, "created_at", None)
            or getattr(n, "created", None)
            or getattr(n, "created_on", None)
            or getattr(n, "timestamp", None)
            or ""
        )

        # is_read variants
        is_read_val = getattr(n, "is_read", None)
        if is_read_val is None:
            is_read_val = getattr(n, "read", "")

        writer.writerow([
            getattr(n, "id", ""),
            user_id,
            user_username,
            is_read_val,
            created,
            text,
            url,
            kind,
        ])

    return response


export_notifications_csv.short_description = "Export selected notifications to CSV"  # type: ignore[attr-defined]


# ---------- Admin ----------

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Robust admin that does not assume exact field names on Notification.
    """
    actions = [export_notifications_csv]

    # Use safe accessors for list_display so system checks always pass
    list_display = ("id", "recipient_display", "is_read_display", "created_at_display")

    # Keep filters/search conservative to avoid referring to unknown fields
    list_filter = ()
    search_fields = ()

    # ---- Safe accessors ----
    def recipient_display(self, obj):
        u = (
            getattr(obj, "user", None)
            or getattr(obj, "recipient", None)
            or getattr(obj, "to_user", None)
            or getattr(getattr(obj, "profile", None), "user", None)
            or getattr(getattr(obj, "user_profile", None), "user", None)
        )
        if hasattr(u, "username"):
            return u.username
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
