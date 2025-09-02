# apps/teams/admin/exports.py
from apps.corelib.csvutils import stream_csv


def export_teams_csv(modeladmin, request, queryset):
    """
    Export selected Teams as CSV.

    Columns (must match tests exactly):
        id, name, tag, captain_id, captain_username, created_at
    """
    # Be defensive with relations: try to prefetch/select if available, but don't fail if schema differs.
    try:
        queryset = queryset.select_related("captain__user")
    except Exception:
        pass

    header = ["id", "name", "tag", "captain_id", "captain_username", "created_at"]

    def _rows():
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
            yield [
                getattr(t, "id", ""),
                getattr(t, "name", ""),
                getattr(t, "tag", ""),
                captain_id,
                captain_username,
                created,
            ]

    return stream_csv("teams", header, _rows())


export_teams_csv.short_description = "Export to CSV"
