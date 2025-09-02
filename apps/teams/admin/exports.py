# apps/teams/admin/exports.py
from django.http import HttpResponse
from django.utils import timezone
import csv


def export_teams_csv(modeladmin, request, queryset):
    """
    Export selected Teams as CSV.

    Columns (must match tests exactly):
        id, name, tag, captain_id, captain_username, created_at
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"teams-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "name",
        "tag",
        "captain_id",
        "captain_username",
        "created_at",
    ])

    # Be defensive with relations: try to prefetch/select if available, but don't fail if schema differs.
    try:
        queryset = queryset.select_related("captain__user")
    except Exception:
        pass

    for t in queryset.order_by("id"):
        # Captain info (UserProfile -> User via OneToOne)
        captain = getattr(t, "captain", None)
        captain_id = getattr(captain, "id", "")
        captain_user = getattr(captain, "user", None)
        captain_username = getattr(captain_user, "username", "") if captain_user else ""

        created = (
            getattr(t, "created_at", None)
            or getattr(t, "created", None)
            or getattr(t, "created_on", None)
            or ""
        )

        writer.writerow([
            getattr(t, "id", ""),
            getattr(t, "name", ""),
            getattr(t, "tag", ""),
            captain_id,
            captain_username,
            created,
        ])

    return response


export_teams_csv.short_description = "Export to CSV"
