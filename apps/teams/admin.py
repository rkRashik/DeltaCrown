from django.contrib import admin
from .models import Team, TeamMembership, TeamInvite

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

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "tag", "captain", "created_at")
    search_fields = ("name", "tag", "captain__display_name", "captain__user__username")
    inlines = [TeamMembershipInline, TeamInviteInline]

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
