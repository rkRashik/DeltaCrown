# apps/teams/admin/teams.py
from django.contrib import admin

from ..models import Team, TeamMembership, TeamInvite
from .exports import export_teams_csv
from .inlines import TeamMembershipInline, TeamInviteInline


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """
    Teams admin — behavior-preserving split. Keep list columns robust.
    """
    actions = [export_teams_csv]

    list_display = ("id", "name", "tag", "captain_display", "members_count_display", "created_at_display")
    search_fields = ("name", "tag", "captain__display_name", "captain__user__username")
    list_filter = ()  # keep conservative unless you have explicit fields to filter

    # Query perf for changelist: captain -> user in one hop
    list_select_related = ("captain__user",)

    # Attach inlines (moved from legacy base.py)
    inlines = [TeamMembershipInline, TeamInviteInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Try to follow captain -> user; ignore if relation doesn't exist
        try:
            return qs.select_related("captain__user")
        except Exception:
            return qs

    # ---- Safe accessors (avoid admin system-check errors across schema variations) ----
    def captain_display(self, obj):
        captain = getattr(obj, "captain", None)
        if not captain:
            return "-"
        u = getattr(captain, "user", None)
        if hasattr(u, "username"):
            return u.username
        return getattr(captain, "display_name", None) or str(captain) or "-"

    captain_display.short_description = "Captain"

    def members_count_display(self, obj):
        for rel_name in ("members", "memberships", "teammembership_set"):
            rel = getattr(obj, rel_name, None)
            if hasattr(rel, "count"):
                try:
                    return rel.count()
                except Exception:
                    pass
        return 0

    members_count_display.short_description = "Members"

    def created_at_display(self, obj):
        return (
            getattr(obj, "created_at", None)
            or getattr(obj, "created", None)
            or getattr(obj, "created_on", None)
            or "-"
        )

    created_at_display.short_description = "Created"


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role", "joined_at")
    list_filter = ("role", "team")
    search_fields = ("team__name", "team__tag", "user__display_name", "user__user__username")

    # UX + perf: autocompletes on FKs; reduce joins on changelist
    autocomplete_fields = ("team", "user")
    list_select_related = ("team", "user")


@admin.register(TeamInvite)
class TeamInviteAdmin(admin.ModelAdmin):
    list_display = ("team", "invited_user", "invited_by", "status", "expires_at", "token")
    list_filter = ("status", "team")
    search_fields = ("team__name", "invited_user__user__username", "token")
    readonly_fields = ("token",)

    # UX + perf: autocompletes on FKs; reduce joins on changelist
    autocomplete_fields = ("team", "invited_user", "invited_by")
    list_select_related = ("team", "invited_user", "invited_by")
