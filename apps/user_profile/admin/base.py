from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from ..models import UserProfile
import csv


# ---------- Admin Action: Export User Profiles to CSV ----------

def export_userprofiles_csv(modeladmin, request, queryset):
    """
    Export selected User Profiles as CSV.
    Columns selected for ops reliability and usefulness.
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"user-profiles-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "username",
        "email",
        "display_name",
        "created_at",
    ])

    # Try to select_related the User to reduce queries if relation exists
    try:
        queryset = queryset.select_related("user")
    except Exception:
        pass

    for p in queryset.order_by("id"):
        user = getattr(p, "user", None)
        username = getattr(user, "username", "")
        email = getattr(user, "email", "")

        writer.writerow([
            p.id,
            username,
            email,
            getattr(p, "display_name", ""),
            getattr(p, "created_at", "") or "",
        ])

    return response


export_userprofiles_csv.short_description = "Export selected user profiles to CSV"  # type: ignore[attr-defined]


# ---------- Admin ----------

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "created_at")
    search_fields = ("user__username", "display_name", "user__email")
    list_filter = ()
    date_hierarchy = "created_at"
    actions = [export_userprofiles_csv]
