# apps/notifications/admin/exports.py
from django.http import HttpResponse
from django.utils import timezone
import csv


def export_notifications_csv(modeladmin, request, queryset):
    """
    Export selected Notifications as CSV.

    Columns intentionally stable (match tests):
        id, user_id, user_username, is_read, created_at, text, url, kind
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"notifications-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        ["id", "user_id", "user_username", "is_read", "created_at", "text", "url", "kind"]
    )

    # The queryset may be empty — header-only export is valid and covered by tests.
    for n in queryset.order_by("id"):
        # Resolve a "user-like" object (tolerant of model field variations)
        u = (
            getattr(n, "user", None)
            or getattr(n, "recipient", None)
            or getattr(n, "to_user", None)
            or getattr(getattr(n, "profile", None), "user", None)
            or getattr(getattr(n, "user_profile", None), "user", None)
        )
        user_id = getattr(u, "id", "")
        user_username = getattr(u, "username", "") if u else ""

        # Read / created fields with fallbacks
        is_read_val = getattr(n, "is_read", None)
        if is_read_val is None:
            is_read_val = getattr(n, "read", "")

        created = (
            getattr(n, "created_at", None)
            or getattr(n, "created", None)
            or getattr(n, "created_on", None)
            or getattr(n, "timestamp", None)
            or ""
        )

        # Text, URL, kind with broad fallbacks to tolerate schema changes
        text = (
            getattr(n, "title", None)
            or getattr(n, "verb", None)
            or getattr(n, "text", None)
            or getattr(n, "body", None)
            or getattr(n, "message", None)
            or ""
        )
        url = (
            getattr(n, "url", None)
            or getattr(n, "link", None)
            or getattr(n, "target_url", None)
            or ""
        )
        kind = (
            getattr(n, "kind", None)
            or getattr(n, "type", None)
            or getattr(n, "category", None)
            or ""
        )

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


export_notifications_csv.short_description = "Export to CSV"
