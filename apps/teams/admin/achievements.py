from __future__ import annotations
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from ..models import TeamAchievement, TeamStats

def safe_register(model, admin_class):
    try:
        admin.site.register(model, admin_class)
    except AlreadyRegistered:
        pass
    except Exception:
        pass

@admin.register(TeamAchievement)
class TeamAchievementAdmin(admin.ModelAdmin):
    list_display = ("id", "team", "title", "placement", "year", "tournament")
    list_filter = ("placement", "year")
    search_fields = ("title", "team__name", "team__tag")

@admin.register(TeamStats)
class TeamStatsAdmin(admin.ModelAdmin):
    list_display = ("id", "team", "matches_played", "wins", "losses", "win_rate", "streak", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("team__name", "team__tag")
