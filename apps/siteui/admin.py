"""
SiteUI Django Admin Configuration

Provides admin interface for managing homepage content and other site-wide content.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError

try:
    # Preferred modern admin shell when django-unfold is installed.
    from unfold.admin import ModelAdmin as BaseModelAdmin
except Exception:
    # Fallback keeps admin registration working even if unfold is unavailable.
    from django.contrib.admin import ModelAdmin as BaseModelAdmin

from .models import (
    HomePageContent,
    ArenaGlobalWidget,
    ArenaHighlight,
    ArenaStream,
    ArenaGlobalWidgetVote,
)


@admin.register(HomePageContent)
class HomePageContentAdmin(BaseModelAdmin):
    """
    Admin interface for managing homepage content.
    
    This is a singleton model - only one instance can exist. The admin interface
    prevents creating multiple instances and disallows deletion to maintain site stability.
    """
    
    fieldsets = (
        ('Hero Section', {
            'fields': (
                'hero_badge_text',
                'hero_title',
                'hero_subtitle',
                'hero_description',
                ('primary_cta_text', 'primary_cta_url', 'primary_cta_icon'),
                ('secondary_cta_text', 'secondary_cta_url', 'secondary_cta_icon'),
                'hero_highlights',
            ),
            'description': (
                'Main banner content and call-to-action buttons. '
                'Hero highlights can reference live DB counts (use source: "DB_COUNT") or static values.'
            )
        }),
        
        ('Problem/Opportunity Section', {
            'fields': (
                'problem_section_enabled',
                'problem_title',
                'problem_subtitle',
                'comparison_table',
            ),
            'classes': ('collapse',),
            'description': 'Section explaining why DeltaCrown exists and how it differs from other platforms.'
        }),
        
        ('Ecosystem Pillars', {
            'fields': (
                'pillars_section_enabled',
                'ecosystem_pillars_title',
                'ecosystem_pillars_description',
                'ecosystem_pillars',
            ),
            'classes': ('collapse',),
            'description': 'The 8 interconnected domains of the DeltaCrown ecosystem.'
        }),
        
        ('Games Section', {
            'fields': (
                'games_section_enabled',
                'games_section_title',
                'games_section_description',
                'games_data',
            ),
            'classes': ('collapse',),
            'description': (
                'Supported games section. Currently managed via JSON. '
                'Phase 2 will migrate to Game model relationships.'
            )
        }),
        
        ('Tournaments Section', {
            'fields': (
                'tournaments_section_enabled',
                'tournaments_section_title',
                'tournaments_section_description',
            ),
            'classes': ('collapse',),
            'description': 'Featured tournaments section. Phase 2 will add dynamic tournament queries.'
        }),
        
        ('Teams Section', {
            'fields': (
                'teams_section_enabled',
                'teams_section_title',
                'teams_section_description',
            ),
            'classes': ('collapse',),
            'description': 'Featured teams section. Phase 2 will add dynamic team queries.'
        }),
        
        ('Local Payments', {
            'fields': (
                'payments_section_enabled',
                'payments_section_title',
                'payments_section_description',
                'payment_methods',
                'payments_trust_message',
            ),
            'classes': ('collapse',),
            'description': 'Local payment methods (bKash, Nagad, Rocket, Bank Transfer) section.'
        }),
        
        ('DeltaCoin Economy', {
            'fields': (
                'deltacoin_section_enabled',
                'deltacoin_section_title',
                'deltacoin_section_description',
                'deltacoin_earn_methods',
                'deltacoin_spend_options',
            ),
            'classes': ('collapse',),
            'description': 'DeltaCoin reward system and economy section.'
        }),
        
        ('Community Section', {
            'fields': (
                'community_section_enabled',
                'community_section_title',
                'community_section_description',
            ),
            'classes': ('collapse',),
            'description': 'Community content and engagement section.'
        }),
        
        ('Roadmap', {
            'fields': (
                'roadmap_section_enabled',
                'roadmap_section_title',
                'roadmap_section_description',
                'roadmap_items',
            ),
            'classes': ('collapse',),
            'description': (
                'Platform roadmap with status indicators: COMPLETED, IN_PROGRESS, PLANNED.'
            )
        }),
        
        ('Final CTA', {
            'fields': (
                'final_cta_section_enabled',
                'final_cta_title',
                'final_cta_description',
                ('final_cta_primary_text', 'final_cta_primary_url'),
                ('final_cta_secondary_text', 'final_cta_secondary_url'),
            ),
            'classes': ('collapse',),
            'description': 'Final call-to-action section at bottom of homepage.'
        }),
        
        ('Platform Info', {
            'fields': (
                'platform_tagline',
                'platform_founded_year',
                'platform_founder',
            ),
            'classes': ('collapse',),
            'description': 'Platform metadata used in footer and about sections.'
        }),
        
        ('Meta', {
            'fields': (
                'updated_at',
                'updated_by',
            ),
            'classes': ('collapse',),
            'description': 'Tracking information for content updates.'
        }),
    )
    
    readonly_fields = ('updated_at', 'updated_by')
    
    list_display = ('__str__', 'updated_at', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        """Automatically set updated_by to current user."""
        obj.updated_by = request.user
        try:
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            # Show validation error in admin UI
            from django.contrib import messages
            messages.error(request, str(e))
    
    def has_add_permission(self, request):
        """
        Prevent adding if an instance already exists.
        This enforces the singleton pattern.
        """
        if HomePageContent.objects.exists():
            return False
        return super().has_add_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """
        Prevent deletion of homepage content to maintain site stability.
        Content should be edited, not deleted.
        """
        return False
    
    def changelist_view(self, request, extra_context=None):
        """
        Customize changelist to show prominent edit button for singleton.
        """
        extra_context = extra_context or {}
        extra_context['title'] = 'Homepage Content Management'
        extra_context['subtitle'] = (
            'Edit the content displayed on the DeltaCrown homepage. '
            'Changes take effect immediately after saving.'
        )
        return super().changelist_view(request, extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Customize change view with helpful context.
        """
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False  # Simplify UI
        extra_context['help_text'] = format_html(
            '<div style="background: #fef3cd; border-left: 4px solid #ffc107; '
            'padding: 12px; margin-bottom: 20px;">'
            '<strong>💡 Tips:</strong><br>'
            '• JSON fields: Click "Show all" to expand full editor<br>'
            '• Hero highlights with source="DB_COUNT" will display live stats<br>'
            '• Toggle sections on/off using the "*_section_enabled" checkboxes<br>'
            '• Changes are reflected immediately on the homepage<br>'
            '• Phase 2 will add dynamic tournaments/teams data'
            '</div>'
        )
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(ArenaHighlight)
class ArenaHighlightAdmin(BaseModelAdmin):
    list_display = (
        "display_title",
        "provider",
        "game",
        "thumbnail_preview",
        "duration_label",
        "views_label",
        "is_active",
        "display_order",
        "updated_at",
    )
    list_filter = ("provider", "is_active", "game")
    search_fields = ("custom_title", "fetched_title", "subtitle", "source_url")
    list_editable = ("is_active", "display_order")
    ordering = ("display_order", "-updated_at", "id")
    readonly_fields = (
        "fetched_title",
        "fetched_thumbnail_url",
        "embed_url",
        "provider",
        "thumbnail_preview",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("game",)
    actions = ("activate_selected", "deactivate_selected")
    list_per_page = 25

    fieldsets = (
        ("Main", {
            "fields": (
                "source_url",
                "game",
                "subtitle",
                "is_active",
                "display_order",
                ("duration_label", "views_label"),
            )
        }),
        ("Overrides", {
            "fields": (
                "custom_title",
                "custom_thumbnail",
                "thumbnail_preview",
            ),
            "classes": ("collapse",),
        }),
        ("Auto-Fetched Data", {
            "fields": (
                "fetched_title",
                "fetched_thumbnail_url",
                "embed_url",
                "provider",
            ),
        }),
        ("Meta", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Title")
    def display_title(self, obj):
        return obj.display_title or "-"

    @admin.display(description="Thumbnail")
    def thumbnail_preview(self, obj):
        url = obj.display_thumbnail
        if not url:
            return "-"
        return format_html(
            '<img src="{}" alt="{}" style="height:48px;width:72px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" />',
            url,
            obj.display_title,
        )

    @admin.action(description="Activate selected highlights")
    def activate_selected(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected highlights")
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(ArenaGlobalWidget)
class ArenaGlobalWidgetAdmin(BaseModelAdmin):
    list_display = (
        "prompt_text",
        "tournament_label",
        "is_active",
        "display_order",
        "starts_at",
        "ends_at",
        "vote_count",
        "active_window_status",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("prompt_text", "tournament_label", "option_a_label", "option_b_label")
    list_editable = ("is_active", "display_order")
    ordering = ("display_order", "-updated_at", "id")
    readonly_fields = ("created_at", "updated_at")
    actions = ("activate_selected", "deactivate_selected")
    list_per_page = 25

    fieldsets = (
        ("Widget Labels", {
            "fields": (
                ("badge_label", "meta_label"),
                "tournament_label",
                "prompt_text",
            )
        }),
        ("Poll Options", {
            "fields": (
                ("option_a_label", "option_a_percent"),
                ("option_b_label", "option_b_percent"),
                ("vote_count", "vote_count_label"),
            )
        }),
        ("Publishing", {
            "fields": (
                "is_active",
                "display_order",
                ("starts_at", "ends_at"),
            )
        }),
        ("Meta", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Window")
    def active_window_status(self, obj):
        return "Live" if obj.is_visible_now() else "Scheduled/Inactive"

    @admin.action(description="Activate selected widgets")
    def activate_selected(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected widgets")
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(ArenaStream)
class ArenaStreamAdmin(BaseModelAdmin):
    list_display = (
        "display_title",
        "provider",
        "channel_name",
        "game_display",
        "is_live",
        "featured",
        "is_active",
        "display_order",
        "viewer_count",
        "active_window_status",
    )
    list_filter = ("provider", "is_live", "featured", "is_active")
    search_fields = ("custom_title", "fetched_title", "subtitle", "channel_name", "game_label", "source_url")
    list_editable = ("is_live", "featured", "is_active", "display_order")
    ordering = ("-featured", "display_order", "-updated_at", "id")
    readonly_fields = (
        "fetched_title",
        "fetched_thumbnail_url",
        "embed_url",
        "provider",
        "thumbnail_preview",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("game",)
    actions = ("mark_live", "mark_not_live", "activate_selected", "deactivate_selected")
    list_per_page = 25

    fieldsets = (
        ("Main", {
            "fields": (
                "source_url",
                "game",
                "subtitle",
                "channel_name",
                "game_label",
                ("is_live", "is_active", "featured"),
                "display_order",
            )
        }),
        ("Overrides", {
            "fields": (
                "custom_title",
                "custom_thumbnail",
                "thumbnail_preview",
            ),
            "classes": ("collapse",),
        }),
        ("Auto-Fetched Data", {
            "fields": (
                "fetched_title",
                "fetched_thumbnail_url",
                "embed_url",
                "provider",
            )
        }),
        ("Audience & Schedule", {
            "fields": (
                ("viewer_count", "viewers_label"),
                ("starts_at", "ends_at"),
            )
        }),
        ("Meta", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Title")
    def display_title(self, obj):
        return obj.display_title or "-"

    @admin.display(description="Game")
    def game_display(self, obj):
        return obj.effective_game_label or "-"

    @admin.display(description="Window")
    def active_window_status(self, obj):
        return "Live" if obj.is_currently_live() else "Scheduled/Inactive"

    @admin.display(description="Thumbnail")
    def thumbnail_preview(self, obj):
        url = obj.display_thumbnail
        if not url:
            return "-"
        return format_html(
            '<img src="{}" alt="{}" style="height:48px;width:84px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" />',
            url,
            obj.display_title,
        )

    @admin.action(description="Mark selected as live")
    def mark_live(self, request, queryset):
        queryset.update(is_live=True)

    @admin.action(description="Mark selected as not live")
    def mark_not_live(self, request, queryset):
        queryset.update(is_live=False)

    @admin.action(description="Activate selected streams")
    def activate_selected(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected streams")
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(ArenaGlobalWidgetVote)
class ArenaGlobalWidgetVoteAdmin(BaseModelAdmin):
    list_display = ("widget", "selected_option", "user", "voter_key", "created_at")
    list_filter = ("selected_option", "created_at")
    search_fields = ("widget__prompt_text", "voter_key", "user__username", "user__email")
    readonly_fields = ("widget", "selected_option", "user", "voter_key", "created_at", "updated_at")
    ordering = ("-created_at",)
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
