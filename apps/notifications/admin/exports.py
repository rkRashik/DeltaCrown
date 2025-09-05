# apps/notifications/admin/exports.py
try:
    from apps.corelib.csvutils import stream_csv
except Exception:
    # Minimal fallback
    from django.http import HttpResponse
    import csv
    def stream_csv(basename, header, rows_iter):
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{basename}.csv"'
        w = csv.writer(resp)
        w.writerow(header)
        for r in rows_iter:
            w.writerow(r)
        return resp


def export_notifications_csv(modeladmin, request, queryset):
    """
    Export selected Notifications as CSV.

    Columns:
        id, user_id, user_username, is_read, created_at, text, url, kind
    """
    header = ["id", "user_id", "user_username", "is_read", "created_at", "text", "url", "kind"]

    def _rows():
        for n in queryset.order_by("id").select_related("recipient__user"):
            user = getattr(n, "recipient", None)
            auth_user = getattr(user, "user", None)
            yield [
                getattr(n, "id", ""),
                getattr(user, "id", ""),
                getattr(auth_user, "username", "") if auth_user else "",
                getattr(n, "is_read", False),
                getattr(n, "created_at", None),
                getattr(n, "title", "") or getattr(n, "body", ""),
                getattr(n, "url", ""),
                getattr(n, "type", ""),
            ]

    return stream_csv("notifications", header, _rows())
export_notifications_csv.short_description = "Export to CSV"
