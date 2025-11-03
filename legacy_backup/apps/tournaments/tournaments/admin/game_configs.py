"""
Admin interface for Game Configuration models.

Provides management interface for:
- GameConfiguration: Game settings and metadata
- GameFieldConfiguration: Dynamic form fields for each game
- PlayerRoleConfiguration: Role definitions for each game
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.tournaments.models import (
    GameConfiguration,
    GameFieldConfiguration,
    PlayerRoleConfiguration
)


class GameFieldConfigurationInline(admin.TabularInline):
    """Inline admin for game field configurations."""
    model = GameFieldConfiguration
    extra = 0
    fields = [
        'field_name',
        'field_label',
        'field_type',
        'is_required',
        'validation_regex',
        'placeholder',
        'display_order',
        'is_active'
    ]
    ordering = ['display_order', 'field_name']


class PlayerRoleConfigurationInline(admin.TabularInline):
    """Inline admin for player role configurations."""
    model = PlayerRoleConfiguration
    extra = 0
    fields = [
        'role_code',
        'role_name',
        'role_abbreviation',
        'is_unique',
        'is_required',
        'max_per_team',
        'display_order',
        'is_active'
    ]
    ordering = ['display_order', 'role_name']


@admin.register(GameConfiguration)
class GameConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for Game Configuration."""
    
    list_display = [
        'display_name',
        'game_code',
        'roster_badge',
        'tournament_types_badge',
        'field_count',
        'role_count',
        'is_active_badge',
        'updated_at'
    ]
    
    list_filter = [
        'is_active',
        'is_solo',
        'is_team',
        'created_at',
    ]
    
    search_fields = [
        'game_code',
        'display_name',
        'description'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'roster_description',
        'total_roster_size'
    ]
    
    fieldsets = (
        ('Game Identity', {
            'fields': ('game_code', 'display_name', 'icon', 'description')
        }),
        ('Team Composition', {
            'fields': ('team_size', 'sub_count', 'total_roster_size', 'roster_description')
        }),
        ('Tournament Support', {
            'fields': ('is_solo', 'is_team')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [GameFieldConfigurationInline, PlayerRoleConfigurationInline]
    
    def roster_badge(self, obj):
        """Display roster size as a badge."""
        if obj.sub_count > 0:
            text = f"{obj.team_size}+{obj.sub_count}"
        else:
            text = f"{obj.team_size}"
        return format_html(
            '<span style="background: #0d6efd; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            text
        )
    roster_badge.short_description = 'Roster Size'
    
    def tournament_types_badge(self, obj):
        """Display supported tournament types."""
        types = []
        if obj.is_solo:
            types.append('<span style="background: #198754; color: white; padding: 2px 6px; '
                        'border-radius: 3px; font-size: 10px;">SOLO</span>')
        if obj.is_team:
            types.append('<span style="background: #0dcaf0; color: black; padding: 2px 6px; '
                        'border-radius: 3px; font-size: 10px;">TEAM</span>')
        return format_html(' '.join(types))
    tournament_types_badge.short_description = 'Types'
    
    def field_count(self, obj):
        """Count of active fields."""
        count = obj.field_configurations.filter(is_active=True).count()
        return format_html(
            '<span style="color: #6c757d;">{} fields</span>',
            count
        )
    field_count.short_description = 'Fields'
    
    def role_count(self, obj):
        """Count of active roles."""
        count = obj.role_configurations.filter(is_active=True).count()
        if count == 0:
            return format_html('<span style="color: #adb5bd;">No roles</span>')
        return format_html(
            '<span style="color: #6c757d;">{} roles</span>',
            count
        )
    role_count.short_description = 'Roles'
    
    def is_active_badge(self, obj):
        """Display active status as badge."""
        if obj.is_active:
            return format_html(
                '<span style="background: #198754; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">✓ ACTIVE</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">✗ INACTIVE</span>'
        )
    is_active_badge.short_description = 'Status'


@admin.register(GameFieldConfiguration)
class GameFieldConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for Game Field Configuration (standalone view)."""
    
    list_display = [
        'field_label',
        'game',
        'field_name',
        'field_type',
        'is_required_badge',
        'has_validation',
        'display_order',
        'is_active'
    ]
    
    list_filter = [
        'game',
        'field_type',
        'is_required',
        'is_active'
    ]
    
    search_fields = [
        'field_name',
        'field_label',
        'help_text',
        'game__display_name'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Field Identity', {
            'fields': ('game', 'field_name', 'field_label', 'field_type')
        }),
        ('Validation', {
            'fields': (
                'is_required',
                'validation_regex',
                'validation_error_message',
                'min_length',
                'max_length'
            )
        }),
        ('Display', {
            'fields': ('placeholder', 'help_text', 'display_order', 'choices')
        }),
        ('Conditional Display', {
            'fields': ('show_condition',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_required_badge(self, obj):
        """Display required status."""
        if obj.is_required:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">★ Required</span>'
            )
        return format_html('<span style="color: #6c757d;">Optional</span>')
    is_required_badge.short_description = 'Required?'
    
    def has_validation(self, obj):
        """Show if field has validation rules."""
        if obj.validation_regex:
            return format_html(
                '<span style="color: #198754;">✓ Regex</span>'
            )
        if obj.min_length or obj.max_length:
            return format_html(
                '<span style="color: #0dcaf0;">✓ Length</span>'
            )
        return format_html('<span style="color: #adb5bd;">—</span>')
    has_validation.short_description = 'Validation'


@admin.register(PlayerRoleConfiguration)
class PlayerRoleConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for Player Role Configuration (standalone view)."""
    
    list_display = [
        'role_name',
        'game',
        'role_code',
        'role_abbreviation',
        'is_unique_badge',
        'is_required_badge',
        'max_per_team',
        'display_order',
        'is_active'
    ]
    
    list_filter = [
        'game',
        'is_unique',
        'is_required',
        'is_active'
    ]
    
    search_fields = [
        'role_code',
        'role_name',
        'role_abbreviation',
        'description',
        'game__display_name'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Role Identity', {
            'fields': ('game', 'role_code', 'role_name', 'role_abbreviation', 'icon')
        }),
        ('Constraints', {
            'fields': ('is_unique', 'is_required', 'max_per_team')
        }),
        ('Display', {
            'fields': ('description', 'display_order')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_unique_badge(self, obj):
        """Display unique status."""
        if obj.is_unique:
            return format_html(
                '<span style="background: #ffc107; color: black; padding: 2px 6px; '
                'border-radius: 3px; font-size: 10px;">★ UNIQUE</span>'
            )
        return format_html('<span style="color: #adb5bd;">—</span>')
    is_unique_badge.short_description = 'Unique?'
    
    def is_required_badge(self, obj):
        """Display required status."""
        if obj.is_required:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">★ Required</span>'
            )
        return format_html('<span style="color: #6c757d;">Optional</span>')
    is_required_badge.short_description = 'Required?'
