from django.contrib import admin

from apps.match_engine.models import GameMatchPipeline

try:
    from unfold.admin import ModelAdmin
except ImportError:
    ModelAdmin = admin.ModelAdmin


@admin.register(GameMatchPipeline)
class GameMatchPipelineAdmin(ModelAdmin):
    list_display = ("game", "archetype", "require_coin_toss", "require_map_veto")
    list_filter = ("archetype",)
    search_fields = ("game__name",)
