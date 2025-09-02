# apps/teams/admin/inlines.py
from django.contrib import admin
from ..models import TeamMembership, TeamInvite


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
