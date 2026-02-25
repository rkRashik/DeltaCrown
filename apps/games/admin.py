"""
Admin configuration for games app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from apps.games.models import (
    Game,
    GameRosterConfig,
    GamePlayerIdentityConfig,
    GameTournamentConfig,
    GameRole
)


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


@admin.register(Game)
class GameAdmin(ModelAdmin):
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
    list_display = ['game', 'default_match_format', 'default_scoring_type', 'require_check_in']
    list_filter = ['default_match_format', 'default_scoring_type', 'require_check_in']
    search_fields = ['game__name']


@admin.register(GameRole)
class GameRoleAdmin(ModelAdmin):
    list_display = ['game', 'role_name', 'role_code', 'is_competitive', 'is_active', 'order']
    list_filter = ['game', 'is_competitive', 'is_active']
    search_fields = ['game__name', 'role_name', 'role_code']
    ordering = ['game', 'order', 'role_name']
