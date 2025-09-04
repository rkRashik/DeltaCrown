# apps/teams/admin/inlines.py
from __future__ import annotations

from django.contrib import admin

from ..models import TeamMembership, TeamInvite


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    autocomplete_fields = ("profile",)
    fields = ("profile", "role", "status", "joined_at")
    readonly_fields = ("joined_at",)


class TeamInviteInline(admin.TabularInline):
    model = TeamInvite
    extra = 0
    autocomplete_fields = ("inviter", "invited_user")
    fields = ("inviter", "invited_user", "invited_email", "role", "status", "token", "expires_at", "created_at")
    readonly_fields = ("token", "created_at")
