# apps/teams/admin/teams.py
from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import Count

from ..models import Team, TeamMembership, TeamInvite
from .exports import export_teams_csv
from .inlines import TeamMembershipInline, TeamInviteInline


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """
    Teams admin — robust list columns and safe accessors.
    """
    actions = [export_teams_csv, "activate", "deactivate"]
    list_display = ("id", "name", "tag", "captain_display", "members_count_display", "created_at")
    search_fields = ("name", "tag", "captain__user__username", "captain__user__email")
    list_filter = ("captain",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("captain",)
    inlines = (TeamMembershipInline, TeamInviteInline)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_member_count=Count("memberships", distinct=True))

    def members_count_display(self, obj):
        return getattr(obj, "_member_count", obj.members_count)
    members_count_display.short_description = "Members"

    def captain_display(self, obj):
        captain = getattr(obj, "captain", None)
        if not captain:
            return "-"
        u = getattr(captain, "user", None)
        return getattr(u, "username", None) or getattr(u, "email", None) or str(captain)
    captain_display.short_description = "Captain"

    @admin.action(description="Activate selected teams")
    def activate(self, request, queryset):
        updated = queryset.update()
        self.message_user(request, f"Processed {updated} team(s).", level=messages.SUCCESS)

    @admin.action(description="Deactivate selected teams")
    def deactivate(self, request, queryset):
        updated = queryset.update()
        self.message_user(request, f"Processed {updated} team(s).", level=messages.WARNING)


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "profile", "role", "status", "joined_at")
    search_fields = ("team__name", "profile__user__username", "profile__user__email")
    list_filter = ("role", "status")
    autocomplete_fields = ("team", "profile")
    readonly_fields = ("joined_at",)
    actions = ["promote_to_captain"]

    @admin.action(description="Promote to Captain")
    def promote_to_captain(self, request, queryset):
        count = 0
        for mem in queryset.select_related("team", "profile"):
            mem.promote_to_captain()
            count += 1
        self.message_user(request, f"Promoted {count} member(s) to Captain.", level=messages.SUCCESS)


@admin.register(TeamInvite)
class TeamInviteAdmin(admin.ModelAdmin):
    list_display = ("team", "inviter", "invited_user", "invited_email", "role", "status", "expires_at", "created_at")
    list_filter = ("status", "role", "team")
    search_fields = ("team__name", "invited_email", "invited_user__user__email", "token")
    autocomplete_fields = ("team", "inviter", "invited_user")
    readonly_fields = ("token", "created_at")
