# apps/user_profile/admin/exports.py
from apps.corelib.csvutils import stream_csv


def export_userprofiles_csv(modeladmin, request, queryset):
    """
    Export selected User Profiles as CSV.

    Columns must match tests exactly:
        id, username, email, display_name, created_at
    """
    # Be defensive with relations; try to follow profile.user if present
    try:
        queryset = queryset.select_related("user")
    except Exception:
        pass

    header = ["id", "username", "email", "display_name", "created_at"]

    def _rows():
        for p in queryset.order_by("id"):
            u = getattr(p, "user", None)
            username = getattr(u, "username", "") if u else ""
            email = getattr(u, "email", "") if u else ""

            display_name = (
                getattr(p, "display_name", None)
                or getattr(p, "name", None)
                or ""
            )
            created = (
                getattr(p, "created_at", None)
                or getattr(p, "created", None)
                or getattr(p, "created_on", None)
                or ""
            )

            yield [
                getattr(p, "id", ""),
                username,
                email,
                display_name,
                created,
            ]

    return stream_csv("user-profiles", header, _rows())


export_userprofiles_csv.short_description = "Export selected user profiles to CSV"  # type: ignore[attr-defined]
