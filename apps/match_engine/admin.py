from django.contrib import admin

from apps.match_engine.models import GameMatchPipeline, MatchChatMessage

try:
    from unfold.admin import ModelAdmin
except ImportError:
    ModelAdmin = admin.ModelAdmin


@admin.register(GameMatchPipeline)
class GameMatchPipelineAdmin(ModelAdmin):
    list_display = ("game", "archetype", "require_coin_toss", "require_map_veto")
    list_filter = ("archetype",)
    search_fields = ("game__name",)


@admin.register(MatchChatMessage)
class MatchChatMessageAdmin(ModelAdmin):
    list_display = ("match_id", "display_name", "msg_type", "is_official", "created_at")
    list_filter = ("msg_type", "is_official")
    search_fields = ("display_name", "text")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
