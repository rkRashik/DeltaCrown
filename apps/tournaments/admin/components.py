# apps/tournaments/admin/components.py
"""
Reusable admin components for Tournament admin.
Includes inlines for related models and custom filters.
"""
from __future__ import annotations

from django.apps import apps as django_apps
from django.contrib import admin
from django.utils.html import format_html

# Import concrete model modules
from apps.tournaments.models.tournament import Tournament

try:
    from apps.tournaments.models.tournament_settings import TournamentSettings as _TSModel
except Exception:
    _TSModel = None

# Game configs
from apps.game_efootball.models import EfootballConfig
from apps.game_valorant.models import ValorantConfig


def _present_fields(model) -> set[str]:
    """Get all field names present in a model."""
    return {f.name for f in model._meta.get_fields()}


def _only_existing(model, *names):
    """Filter field names to only those that exist in the model."""
    fields = _present_fields(model)
    return [n for n in names if n in fields]


# ==================== GAME-SPECIFIC CONFIG INLINES ====================

class EfootballConfigInline(admin.StackedInline):
    """Inline for eFootball-specific configuration."""
    model = EfootballConfig
    can_delete = False
    extra = 0
    max_num = 1
    fk_name = "tournament"
    show_change_link = True
    
    verbose_name = "⚽ eFootball Configuration"
    verbose_name_plural = "⚽ eFootball Configuration"
    
    fieldsets = (
        ("Match Setup", {
            "fields": (
                ("format_type", "match_duration_min"),
                ("match_time_limit", "team_strength_cap"),
            ),
            "description": "eFootball match configuration and rules."
        }),
        ("Rules & Settings", {
            "fields": (
                ("allow_extra_time", "allow_penalties"),
                "additional_rules_richtext",
            ),
            "description": "Game rules and additional notes."
        }),
    )

    class Media:
        css = {'all': ('admin/css/ckeditor5_fix.css',)}


class ValorantConfigInline(admin.StackedInline):
    """Inline for Valorant-specific configuration."""
    model = ValorantConfig
    can_delete = False
    extra = 0
    max_num = 1
    fk_name = "tournament"
    show_change_link = True
    
    verbose_name = "🎯 Valorant Configuration"
    verbose_name_plural = "🎯 Valorant Configuration"
    
    fieldsets = (
        ("Match Rules", {
            "fields": (
                ("best_of", "rounds_per_match"),
                ("match_duration_limit", "overtime_rules"),
            ),
            "description": "Valorant match format and timing."
        }),
        ("Map Pool", {
            "fields": ("map_pool",),
            "description": "Available maps for this tournament."
        }),
        ("Production Features", {
            "fields": (
                ("regional_lock", "live_scoreboard"),
                ("sponsor_integration", "community_voting"),
                "livestream_customization",
            ),
            "classes": ("collapse",),
            "description": "Advanced features for professional tournaments."
        }),
        ("Additional Rules", {
            "fields": ("additional_rules_richtext",),
            "description": "Custom rules and notes."
        }),
    )

    class Media:
        css = {'all': ('admin/css/ckeditor5_fix.css',)}


# ==================== TOURNAMENT SETTINGS INLINE ====================

class TournamentSettingsInline(admin.StackedInline):
    """
    Inline for TournamentSettings with lazy model resolution.
    Contains advanced tournament configuration options.
    """
    model = _TSModel
    can_delete = False
    extra = 0
    max_num = 1
    show_change_link = True
    
    verbose_name = "⚙️ Advanced Settings"
    verbose_name_plural = "⚙️ Advanced Settings"

    # Exclude deprecated fields that moved to Schedule inline
    exclude = ("start_at", "end_at", "reg_open_at", "reg_close_at")

    class Media:
        css = {'all': ('admin/css/ckeditor5_fix.css',)}

    def __init__(self, parent_model, admin_site):
        # Resolve the model before Django's base __init__ touches self.model._meta
        if self.model is None:
            self.model = django_apps.get_model("tournaments", "TournamentSettings")
        super().__init__(parent_model, admin_site)

    def get_fieldsets(self, request, obj=None):
        fieldsets = []

        def add_section(title, field_names, description="", classes=None):
            """Helper to add fieldset only if fields exist."""
            present = _only_existing(self.model, *field_names)
            if present:
                opts = {"fields": tuple(present), "description": description}
                if classes:
                    opts["classes"] = classes
                fieldsets.append((title, opts))

        # Format & Structure
        add_section(
            "Format & Structure",
            ("tournament_type",),
            "Tournament structure and format."
        )

        # Scheduling
        add_section(
            "Auto-Scheduling",
            ("round_duration_mins", "round_gap_mins", "automatic_scheduling_enabled"),
            "Configure automatic match scheduling."
        )

        # Prize & Entry Fee
        add_section(
            "Prize Distribution",
            ("prize_pool_bdt", "prize_type", "prize_distribution_text"),
            "Prize pool and distribution configuration."
        )

        # Core Toggles
        add_section(
            "Tournament Toggles",
            ("invite_only", "auto_check_in", "custom_format_enabled", "payment_gateway_enabled"),
            "Core tournament behavior settings."
        )

        # Visibility & Region
        add_section(
            "Visibility & Access",
            ("bracket_visibility", "region_lock", "check_in_open_mins", "check_in_close_mins"),
            "Control who can view and participate."
        )

        # Media & Streaming
        add_section(
            "Media & Streaming",
            ("banner", "rules_pdf", "stream_facebook_url", "stream_youtube_url", "discord_url"),
            "Tournament media files and streaming links.",
            classes=("collapse",)
        )

        # Payment Configuration
        add_section(
            "Payment Types",
            ("bkash_receive_type", "nagad_receive_type", "rocket_receive_type"),
            "Configure payment receiving methods.",
            classes=("collapse",)
        )

        add_section(
            "Payment Accounts",
            ("bkash_receive_number", "nagad_receive_number", "rocket_receive_number", "bank_instructions"),
            "Receiving account numbers and instructions.",
            classes=("collapse",)
        )

        return tuple(fieldsets) if fieldsets else None


# ==================== FINANCE INLINE ====================

try:
    from apps.tournaments.models.core import TournamentFinance
    
    class TournamentFinanceInline(admin.StackedInline):
        """Inline for tournament financial configuration."""
        model = TournamentFinance
        can_delete = False
        extra = 0
        max_num = 1
        
        verbose_name = "💰 Finance & Prize Pool"
        verbose_name_plural = "💰 Finance & Prize Pool"
        
        fieldsets = (
            ('Entry Fee', {
                'fields': (
                    ('entry_fee', 'currency'),
                    'payment_method',
                ),
                'description': 'Registration fee for participants'
            }),
            ('Prize Pool', {
                'fields': (
                    ('prize_pool', 'prize_currency'),
                    'prize_distribution',
                ),
                'description': 'Total prize pool and distribution percentages'
            }),
            ('Payment Details', {
                'fields': (
                    'payment_instructions',
                    'refund_policy',
                ),
                'classes': ('collapse',),
                'description': 'Payment instructions and refund policy'
            }),
        )
        
        readonly_fields = ()
        
        def has_add_permission(self, request, obj=None):
            """Only allow one finance record per tournament."""
            if obj and hasattr(obj, 'finance'):
                return False
            return super().has_add_permission(request, obj)

except ImportError:
    TournamentFinanceInline = None


# ==================== MEDIA & RULES INLINES ====================

try:
    from apps.tournaments.models import TournamentMedia
    
    class TournamentMediaInline(admin.StackedInline):
        """Inline for tournament media files."""
        model = TournamentMedia
        can_delete = False
        extra = 0
        max_num = 1
        
        verbose_name = "📷 Media & Assets"
        verbose_name_plural = "📷 Media & Assets"
        
        fieldsets = (
            ('Visual Assets', {
                'fields': (
                    'banner',
                    'logo',
                    'thumbnail',
                ),
                'description': 'Tournament visual assets and branding'
            }),
            ('Streaming Links', {
                'fields': (
                    'stream_facebook_url',
                    'stream_youtube_url',
                    'stream_twitch_url',
                    'discord_url',
                ),
                'description': 'Live stream and community links'
            }),
        )

except ImportError:
    TournamentMediaInline = None


try:
    from apps.tournaments.models import TournamentRules
    
    class TournamentRulesInline(admin.StackedInline):
        """Inline for tournament rules."""
        model = TournamentRules
        can_delete = False
        extra = 0
        max_num = 1
        
        verbose_name = "📜 Rules & Documentation"
        verbose_name_plural = "📜 Rules & Documentation"
        
        fieldsets = (
            ('Rules Document', {
                'fields': (
                    'rules_pdf',
                    'rules_text',
                ),
                'description': 'Tournament rules and regulations'
            }),
            ('Additional Information', {
                'fields': (
                    'terms_and_conditions',
                    'code_of_conduct',
                ),
                'classes': ('collapse',),
                'description': 'Terms, conditions, and code of conduct'
            }),
        )
        
        class Media:
            css = {'all': ('admin/css/ckeditor5_fix.css',)}

except ImportError:
    TournamentRulesInline = None


# ==================== CUSTOM FILTERS ====================

class HasEntryFeeFilter(admin.SimpleListFilter):
    """Filter tournaments by whether they have an entry fee."""
    title = "Entry Fee"
    parameter_name = "has_fee"

    def lookups(self, request, model_admin):
        return [
            ("yes", "Has Entry Fee"),
            ("no", "Free Entry"),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        names = [f.name for f in Tournament._meta.get_fields()]
        
        if val == "yes":
            # Check if Tournament model has entry_fee_bdt field
            if "entry_fee_bdt" in names:
                return queryset.filter(entry_fee_bdt__gt=0)
            # Or check TournamentFinance
            return queryset.filter(finance__entry_fee__gt=0)

        if val == "no":
            # Check if Tournament model has entry_fee_bdt field
            if "entry_fee_bdt" in names:
                return queryset.filter(entry_fee_bdt__isnull=True) | queryset.filter(entry_fee_bdt=0)
            # Or check TournamentFinance
            return queryset.filter(finance__isnull=True) | queryset.filter(finance__entry_fee=0)

        return queryset


# Export all components
__all__ = [
    'EfootballConfigInline',
    'ValorantConfigInline',
    'TournamentSettingsInline',
    'TournamentFinanceInline',
    'TournamentMediaInline',
    'TournamentRulesInline',
    'HasEntryFeeFilter',
]


