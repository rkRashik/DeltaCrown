"""
Django admin interfaces for Tournament models.

Source Documents:
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md (Section 3: App Breakdown)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (Django admin customization)

Provides admin customization for:
- Tournament: Full CRUD with filters, search, and inline custom fields
- Game: Management of supported games
- CustomField: Inline editing within Tournament admin
- TournamentVersion: Read-only version history display
- Registration: Participant registration management (imported from admin_registration)
- Payment: Payment verification management (imported from admin_registration)
- Match: Match lifecycle management (imported from admin_match - Module 1.4)
- Dispute: Dispute resolution management (imported from admin_match - Module 1.4)

Architecture Decisions:
- ADR-001: Service Layer - Complex operations handled by services, not admin
"""

from django.contrib import admin
from django.utils.html import format_html
from .models.tournament import Game, Tournament, CustomField, TournamentVersion
from .models.template import TournamentTemplate  # Module 2.3

# Import Registration and Payment admin classes
from .admin_registration import RegistrationAdmin, PaymentAdmin

# Import Match and Dispute admin classes (Module 1.4)
from .admin_match import MatchAdmin, DisputeAdmin

# Import Certificate admin class (Module 5.3)
from .admin_certificate import CertificateAdmin


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """
    Admin interface for Game model.
    
    Module 2.2: Enhanced with game_config JSONB editor.
    Provides management of supported games with filtering by active status.
    """
    list_display = ['name', 'slug', 'default_team_size', 'default_result_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'default_team_size', 'default_result_type']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['created_at']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'icon', 'description')
        }),
        ('Game Configuration', {
            'fields': ('default_team_size', 'profile_id_field', 'default_result_type')
        }),
        ('Game Config (JSON)', {
            'fields': ('game_config',),
            'classes': ('collapse',),
            'description': (
                'Advanced configuration in JSON format. Defines allowed tournament formats, '
                'team size constraints, custom field schemas, and match settings. '
                'Edit with caution - invalid JSON will cause errors. '
                'Example: {"schema_version": "1.0", "allowed_formats": ["single_elimination"], '
                '"team_size_range": [1, 5]}'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )


class CustomFieldInline(admin.TabularInline):
    """
    Inline editor for CustomField within Tournament admin.
    
    Allows organizers to add custom fields directly in tournament edit page.
    """
    model = CustomField
    extra = 0
    fields = ['field_name', 'field_key', 'field_type', 'order', 'is_required', 'help_text']
    prepopulated_fields = {'field_key': ('field_name',)}


class TournamentVersionInline(admin.TabularInline):
    """
    Inline display for TournamentVersion within Tournament admin.
    
    Shows version history in read-only format.
    """
    model = TournamentVersion
    extra = 0
    can_delete = False
    readonly_fields = ['version_number', 'change_summary', 'changed_by', 'changed_at', 'is_active']
    fields = ['version_number', 'change_summary', 'changed_by', 'changed_at', 'is_active']
    
    def has_add_permission(self, request, obj=None):
        """Versions are created automatically, not manually added."""
        return False


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """
    Admin interface for Tournament model.
    
    Comprehensive tournament management with filtering, search, and inline editing.
    """
    list_display = [
        'name', 'game', 'status', 'organizer', 'format', 'participation_type',
        'tournament_start', 'max_participants', 'total_registrations', 'is_official'
    ]
    list_filter = [
        'status', 'format', 'participation_type', 'is_official', 'game',
        'enable_check_in', 'enable_dynamic_seeding', 'has_entry_fee'
    ]
    search_fields = ['name', 'slug', 'description', 'organizer__username']
    readonly_fields = [
        'created_at', 'updated_at', 'published_at',
        'total_registrations', 'total_matches', 'completed_matches',
        'deleted_at', 'deleted_by'
    ]
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CustomFieldInline, TournamentVersionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'game', 'organizer', 'is_official')
        }),
        ('Tournament Configuration', {
            'fields': (
                'format', 'participation_type', 'max_participants', 'min_participants',
                'registration_start', 'registration_end', 'tournament_start', 'tournament_end'
            )
        }),
        ('Prize Pool', {
            'fields': (
                'prize_pool', 'prize_currency', 'prize_deltacoin', 'prize_distribution'
            )
        }),
        ('Entry Fee & Payment', {
            'fields': (
                'has_entry_fee', 'entry_fee_amount', 'entry_fee_currency', 'entry_fee_deltacoin',
                'payment_methods', 'enable_fee_waiver', 'fee_waiver_top_n_teams'
            )
        }),
        ('Media & Streaming', {
            'fields': (
                'banner_image', 'thumbnail_image', 'rules_pdf', 'promo_video_url',
                'stream_youtube_url', 'stream_twitch_url'
            ),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': (
                'enable_check_in', 'check_in_minutes_before', 'enable_dynamic_seeding',
                'enable_live_updates', 'enable_certificates', 'enable_challenges', 'enable_fan_voting'
            ),
            'classes': ('collapse',)
        }),
        ('Rules', {
            'fields': ('rules_text',),
            'classes': ('collapse',)
        }),
        ('Status & Stats', {
            'fields': (
                'status', 'published_at', 'total_registrations', 'total_matches', 'completed_matches'
            )
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Soft Delete (Read Only)', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps (Read Only)', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Include soft-deleted tournaments in admin."""
        return Tournament.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        """Set organizer to current user if creating new tournament."""
        if not change and not obj.organizer_id:
            obj.organizer = request.user
        super().save_model(request, obj, form, change)


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    """
    Admin interface for CustomField model (standalone view).
    
    Module 2.2: Enhanced with field_config/field_value JSONB editors.
    Provides direct management of custom fields if needed outside of Tournament inline.
    """
    list_display = ['field_name', 'tournament', 'field_type', 'order', 'is_required', 'tournament_status']
    list_filter = ['field_type', 'is_required', 'tournament__status', 'tournament__game']
    search_fields = ['field_name', 'field_key', 'tournament__name', 'tournament__slug']
    readonly_fields = ['field_key']  # field_key auto-generated in save()
    prepopulated_fields = {}
    ordering = ['tournament', 'order', 'field_name']
    
    fieldsets = (
        ('Field Definition', {
            'fields': ('tournament', 'field_name', 'field_key', 'field_type')
        }),
        ('Configuration (JSON)', {
            'fields': ('field_config',),
            'classes': ('collapse',),
            'description': (
                'Field-specific configuration in JSON format. Examples:\n'
                '- text: {"min_length": 3, "max_length": 100, "pattern": "^[a-zA-Z]+$"}\n'
                '- number: {"min_value": 0, "max_value": 100}\n'
                '- dropdown: {"options": ["Option 1", "Option 2", "Option 3"]}\n'
                '- url: {"pattern": "^https://discord\\\\.gg/[a-zA-Z0-9]+$"}'
            )
        }),
        ('Field Value (JSON)', {
            'fields': ('field_value',),
            'classes': ('collapse',),
            'description': 'Actual value storage in JSON format. Usually populated by tournament participants.'
        }),
        ('Display & Validation', {
            'fields': ('order', 'is_required', 'help_text')
        }),
    )
    
    def tournament_status(self, obj):
        """Display tournament status for quick reference."""
        return obj.tournament.status
    tournament_status.short_description = 'Tournament Status'


@admin.register(TournamentVersion)
class TournamentVersionAdmin(admin.ModelAdmin):
    """
    Admin interface for TournamentVersion model.
    
    Read-only display of version history for audit purposes.
    """
    list_display = ['tournament', 'version_number', 'change_summary', 'changed_by', 'changed_at', 'is_active']
    list_filter = ['is_active', 'changed_at', 'tournament__status']
    search_fields = ['tournament__name', 'change_summary']
    readonly_fields = [
        'tournament', 'version_number', 'version_data', 'change_summary',
        'changed_by', 'changed_at', 'is_active', 'rolled_back_at', 'rolled_back_by'
    ]
    
    fieldsets = (
        ('Version Information', {
            'fields': ('tournament', 'version_number', 'change_summary')
        }),
        ('Version Data (Snapshot)', {
            'fields': ('version_data',)
        }),
        ('Change Tracking', {
            'fields': ('changed_by', 'changed_at', 'is_active')
        }),
        ('Rollback Information', {
            'fields': ('rolled_back_at', 'rolled_back_by'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Versions are created automatically via signals/services."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Versions should not be deleted for audit trail."""
        return False


@admin.register(TournamentTemplate)
class TournamentTemplateAdmin(admin.ModelAdmin):
    """
    Admin interface for TournamentTemplate model.
    
    Module 2.3: Template management for tournament organizers.
    Provides template CRUD, activation/deactivation, and usage tracking.
    """
    list_display = [
        'id',
        'name',
        'game',
        'visibility',
        'is_active',
        'usage_count',
        'last_used_at',
        'created_by',
        'created_at',
    ]
    list_filter = [
        'visibility',
        'is_active',
        'game',
        'created_at',
    ]
    search_fields = ['name', 'slug', 'description', 'created_by__username']
    readonly_fields = [
        'slug',
        'usage_count',
        'last_used_at',
        'created_at',
        'updated_at',
        'deleted_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'game')
        }),
        ('Visibility & Access', {
            'fields': ('visibility', 'organization_id', 'created_by')
        }),
        ('Template Configuration (JSON)', {
            'fields': ('template_config',),
            'description': (
                'Tournament configuration template in JSON format. Example structure:\n'
                '{\n'
                '  "format": "single_elimination",\n'
                '  "participation_type": "team",\n'
                '  "max_participants": 16,\n'
                '  "has_entry_fee": true,\n'
                '  "entry_fee_amount": "500.00",\n'
                '  "prize_pool": "10000.00",\n'
                '  "custom_fields": [...]\n'
                '}'
            )
        }),
        ('Status & Usage', {
            'fields': ('is_active', 'usage_count', 'last_used_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_templates', 'deactivate_templates']
    
    def activate_templates(self, request, queryset):
        """Activate selected templates."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} template(s) activated.")
    activate_templates.short_description = "Activate selected templates"
    
    def deactivate_templates(self, request, queryset):
        """Deactivate selected templates."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} template(s) deactivated.")
    deactivate_templates.short_description = "Deactivate selected templates"
