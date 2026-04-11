"""
Admin configuration for games app.
"""

import logging

from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from apps.common.admin_mixins import SafeUploadMixin
from apps.games.models import (
    Game,
    GameRosterConfig,
    GamePlayerIdentityConfig,
    GameTournamentConfig,
    GameRole,
)
from apps.games.models.map_pool import GameMapPool
from apps.games.models.pipeline_template import GamePipelineTemplate
from apps.games.models.rules import VetoConfiguration

logger = logging.getLogger(__name__)


class GameRosterConfigInline(StackedInline):
    model = GameRosterConfig
    extra = 0
    can_delete = False


class GameTournamentConfigInline(StackedInline):
    model = GameTournamentConfig
    extra = 0
    can_delete = False


class GamePlayerIdentityConfigInline(TabularInline):
    model = GamePlayerIdentityConfig
    extra = 1
    fields = ['field_name', 'display_name', 'is_required', 'validation_regex', 'order']


class GameRoleInline(TabularInline):
    model = GameRole
    extra = 1
    fields = ['role_name', 'role_code', 'icon', 'color', 'is_competitive', 'order']


class GameMapPoolInline(TabularInline):
    model = GameMapPool
    extra = 1
    fields = ['map_name', 'map_code', 'is_active', 'is_competitive', 'order']


@admin.register(Game)
class GameAdmin(SafeUploadMixin, ModelAdmin):
    list_display = ['name', 'slug', 'category', 'game_type', 'is_active', 'is_featured']
    list_filter = ['category', 'game_type', 'is_active', 'is_featured']
    search_fields = ['name', 'slug', 'short_code']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'display_name', 'slug', 'short_code', 'description']
        }),
        ('Classification', {
            'fields': ['category', 'game_type', 'platforms']
        }),
        ('Media & Branding', {
            'fields': ['icon', 'logo', 'banner', 'card_image', 'primary_color', 'secondary_color', 'accent_color']
        }),
        ('Status', {
            'fields': ['is_active', 'is_featured', 'release_date']
        }),
        ('Metadata', {
            'fields': ['developer', 'publisher', 'official_website']
        }),
        ('Game ID Customisation', {
            'fields': ['game_id_label', 'game_id_placeholder'],
            'description': (
                'How the in-game identifier is labelled for this game '
                '(e.g. "Riot ID" for Valorant, "Steam ID" for CS2). '
                'Leave blank to use the default "Game ID".'
            ),
        }),
        ('System', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [
        GameRosterConfigInline,
        GameTournamentConfigInline,
        GamePlayerIdentityConfigInline,
        GameRoleInline,
        GameMapPoolInline,
    ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Bust the cached active-games dict so is_active changes take effect immediately
        from django.core.cache import cache
        cache.delete('context_active_games')


@admin.register(GameRosterConfig)
class GameRosterConfigAdmin(ModelAdmin):
    list_display = ['game', 'max_team_size', 'max_substitutes', 'has_roles']
    list_filter = ['has_roles', 'allow_coaches', 'allow_analysts']
    search_fields = ['game__name']


@admin.register(GamePlayerIdentityConfig)
class GamePlayerIdentityConfigAdmin(ModelAdmin):
    list_display = ['game', 'field_name', 'display_name', 'is_required', 'order']
    list_filter = ['is_required', 'field_type']
    search_fields = ['game__name', 'field_name', 'display_name']
    ordering = ['game', 'order']


@admin.register(GameTournamentConfig)
class GameTournamentConfigAdmin(ModelAdmin):
    list_display = ['game', 'default_match_format', 'default_scoring_type', 'max_score', 'require_check_in', 'allow_draws']
    list_filter = ['default_match_format', 'default_scoring_type', 'require_check_in', 'allow_draws']
    search_fields = ['game__name']
    fieldsets = (
        ('Game', {'fields': ('game',)}),
        ('Match Settings', {'fields': ('available_match_formats', 'default_match_format', 'default_match_duration_minutes')}),
        ('Scoring', {'fields': ('default_scoring_type', 'scoring_rules', 'max_score', 'allow_draws', 'overtime_enabled')}),
        ('Tiebreakers', {'fields': ('default_tiebreakers',)}),
        ('Format Support', {'fields': ('supports_single_elimination', 'supports_double_elimination', 'supports_round_robin', 'supports_swiss', 'supports_group_stage')}),
        ('Check-in', {'fields': ('require_check_in', 'check_in_window_minutes')}),
        ('Credentials (Manual Input Schema)', {
            'fields': ('credential_schema',),
            'description': 'JSON array of credential fields for games without APIs. '
                         'Format: [{"key": "lobby_code", "label": "Lobby Code", "kind": "text", "required": true}]',
        }),
    )


@admin.register(GameRole)
class GameRoleAdmin(ModelAdmin):
    list_display = ['game', 'role_name', 'role_code', 'is_competitive', 'is_active', 'order']
    list_filter = ['game', 'is_competitive', 'is_active']
    search_fields = ['game__name', 'role_name', 'role_code']
    ordering = ['game', 'order', 'role_name']


# GameMatchPipeline admin now registered in apps.match_engine.admin (Phase 6)


@admin.register(GameMapPool)
class GameMapPoolAdmin(ModelAdmin):
    list_display = ['game', 'map_name', 'map_code', 'is_active', 'is_competitive', 'order']
    list_filter = ['game', 'is_active', 'is_competitive']
    list_editable = ['is_active', 'is_competitive', 'order']
    search_fields = ['game__name', 'map_name', 'map_code']
    ordering = ['game', 'order', 'map_name']


@admin.register(GamePipelineTemplate)
class GamePipelineTemplateAdmin(ModelAdmin):
    list_display = ['game', 'name', 'pipeline_mode', 'scoring_type', 'default_match_format', 'is_default', 'is_active']
    list_filter = ['game', 'pipeline_mode', 'scoring_type', 'is_default', 'is_active']
    list_editable = ['is_active', 'is_default']
    search_fields = ['game__name', 'name']
    fieldsets = (
        ('Game', {'fields': ('game', 'name', 'is_default', 'is_active')}),
        ('Pipeline', {'fields': ('pipeline_mode', 'scoring_type', 'default_match_format')}),
        ('Tiebreakers', {'fields': ('tiebreakers',)}),
        ('Manual Input Schema', {
            'fields': ('credential_schema',),
            'description': 'JSON array of credential fields for match setup. '
                         'This is the per-pipeline override; falls back to GameTournamentConfig.',
        }),
    )


@admin.register(VetoConfiguration)
class VetoConfigurationAdmin(ModelAdmin):
    list_display = ['game', 'name', 'domain', 'time_per_action_seconds', 'is_active']
    list_filter = ['domain', 'is_active']
    search_fields = ['game__name', 'name']
