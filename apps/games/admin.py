"""
Admin configuration for games app.
"""

from django.contrib import admin
from apps.games.models import (
    Game,
    GameRosterConfig,
    GamePlayerIdentityConfig,
    GameTournamentConfig,
    GameRole
)


class GameRosterConfigInline(admin.StackedInline):
    model = GameRosterConfig
    extra = 0
    can_delete = False


class GameTournamentConfigInline(admin.StackedInline):
    model = GameTournamentConfig
    extra = 0
    can_delete = False


class GamePlayerIdentityConfigInline(admin.TabularInline):
    model = GamePlayerIdentityConfig
    extra = 1
    fields = ['field_name', 'display_name', 'is_required', 'validation_regex', 'order']


class GameRoleInline(admin.TabularInline):
    model = GameRole
    extra = 1
    fields = ['role_name', 'role_code', 'icon', 'color', 'is_competitive', 'order']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
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


@admin.register(GameRosterConfig)
class GameRosterConfigAdmin(admin.ModelAdmin):
    list_display = ['game', 'max_team_size', 'max_substitutes', 'has_roles']
    list_filter = ['has_roles', 'allow_coaches', 'allow_analysts']
    search_fields = ['game__name']


@admin.register(GamePlayerIdentityConfig)
class GamePlayerIdentityConfigAdmin(admin.ModelAdmin):
    list_display = ['game', 'field_name', 'display_name', 'is_required', 'order']
    list_filter = ['is_required', 'field_type']
    search_fields = ['game__name', 'field_name', 'display_name']
    ordering = ['game', 'order']


@admin.register(GameTournamentConfig)
class GameTournamentConfigAdmin(admin.ModelAdmin):
    list_display = ['game', 'default_match_format', 'default_scoring_type', 'require_check_in']
    list_filter = ['default_match_format', 'default_scoring_type', 'require_check_in']
    search_fields = ['game__name']


@admin.register(GameRole)
class GameRoleAdmin(admin.ModelAdmin):
    list_display = ['game', 'role_name', 'role_code', 'is_competitive', 'is_active', 'order']
    list_filter = ['game', 'is_competitive', 'is_active']
    search_fields = ['game__name', 'role_name', 'role_code']
    ordering = ['game', 'order', 'role_name']
