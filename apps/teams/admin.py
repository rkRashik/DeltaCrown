from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from .models import Team, TeamMembership, TeamInvite
import csv


# ---------- Admin Action: Export Teams to CSV ----------

def export_teams_csv(modeladmin, request, queryset):
    """
    Export selected Teams as CSV.
    Columns are intentionally stable and ops-friendly.
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

    # If captain is a FK to UserProfile which has a OneToOne to User, this helps.
    try:
        queryset = queryset.select_related("captain__user")
    except Exception:
        # Be defensive if the relation differs
        pass

    for t in queryset.order_by("id"):
        captain = getattr(t, "captain", None)
        captain_id = getattr(captain, "id", "")
        captain_user = getattr(captain, "user", None)
        captain_username = getattr(captain_user, "username", "") if captain_user else ""

        writer.writerow([
            t.id,
            getattr(t, "name", ""),
            getattr(t, "tag", ""),
            captain_id,
            captain_username,
            getattr(t, "created_at", "") or "",
        ])

    return response


export_teams_csv.short_description = "Export selected teams to CSV"  # type: ignore[attr-defined]


# ---------- Inlines ----------

class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("joined_at",)


class TeamInviteInline(admin.TabularInline):
    model = TeamInvite
    extra = 0
    autocomplete_fields = ("invited_user", "invited_by")
    readonly_fields = ("token", "created_at")


# ---------- Admins ----------

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tag", "captain", "created_at")
    search_fields = ("name", "tag", "captain__user__username", "captain__display_name")
    list_filter = ()
    date_hierarchy = "created_at"
    inlines = [TeamMembershipInline, TeamInviteInline]
    actions = [export_teams_csv]


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role", "joined_at")
    list_filter = ("role", "team")
    search_fields = ("team__name", "team__tag", "user__display_name", "user__user__username")


@admin.register(TeamInvite)
class TeamInviteAdmin(admin.ModelAdmin):
    list_display = ("team", "invited_user", "invited_by", "status", "expires_at", "token")
    list_filter = ("status", "team")
    search_fields = ("team__name", "invited_user__user__username", "token")
    readonly_fields = ("token",)
