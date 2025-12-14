"""
SiteUI Django Admin Configuration

Provides admin interface for managing homepage content and other site-wide content.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from .models import HomePageContent


@admin.register(HomePageContent)
class HomePageContentAdmin(admin.ModelAdmin):
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
