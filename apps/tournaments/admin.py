"""
Tournaments App - Django Admin Configuration

Provides comprehensive admin interface for managing tournaments, games, registrations,
matches, and all tournament-related content. Modeled after the Teams admin for consistency.

Architecture:
- Main models registered here (Tournament, Game, CustomField, TournamentVersion, TournamentTemplate)
- Specialized admins in separate files (admin_registration, admin_match, admin_bracket, etc.)
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.contrib import messages
from django.utils import timezone

try:
    from django_ckeditor_5.widgets import CKEditor5Widget
    CKEDITOR_AVAILABLE = True
except ImportError:
    CKEDITOR_AVAILABLE = False

from apps.tournaments.models import (
    Game, Tournament, CustomField, TournamentVersion, TournamentTemplate,
    Registration, Payment, Match, Dispute, Bracket, Certificate,
    TournamentResult, PrizeTransaction, TournamentPaymentMethod,
    TournamentStaffRole, TournamentStaff
)

# Import specialized admin classes from separate modules
from apps.tournaments.admin_registration import RegistrationAdmin, PaymentAdmin
from apps.tournaments.admin_match import MatchAdmin, DisputeAdmin
from apps.tournaments.admin_bracket import BracketAdmin
from apps.tournaments.admin_certificate import CertificateAdmin
from apps.tournaments.admin_result import TournamentResultAdmin
from apps.tournaments.admin_prize import PrizeTransactionAdmin
from apps.tournaments.admin_staff import TournamentStaffInline  # Import staff inline


# ============================================================================
# INLINE ADMINS
# ============================================================================

class CustomFieldInline(admin.TabularInline):
    """Inline editor for CustomField within Tournament admin"""
    model = CustomField
    extra = 0
    fields = ['field_name', 'field_key', 'field_type', 'order', 'is_required', 'help_text']
    prepopulated_fields = {'field_key': ('field_name',)}


class TournamentVersionInline(admin.TabularInline):
    """Inline display for TournamentVersion within Tournament admin (read-only audit trail)"""
    model = TournamentVersion
    extra = 0
    can_delete = False
    readonly_fields = ['version_number', 'change_summary', 'changed_by', 'changed_at', 'is_active']
    fields = ['version_number', 'change_summary', 'changed_by', 'changed_at', 'is_active']
    
    def has_add_permission(self, request, obj=None):
        """Versions are created automatically, not manually"""
        return False


class TournamentPaymentMethodInline(admin.StackedInline):
    """
    Inline editor for configuring payment methods.
    Each method (bKash, Nagad, etc.) has its own collapsible section.
    """
    model = TournamentPaymentMethod
    extra = 0
    can_delete = True
    show_change_link = True
    
    fieldsets = (
        ('Basic Configuration', {
            'fields': ('method', 'is_enabled', 'display_order')
        }),
        ('bKash Configuration', {
            'fields': (
                'bkash_account_number', 'bkash_account_type', 'bkash_account_name',
                'bkash_instructions', 'bkash_reference_required'
            ),
            'classes': ('collapse',),
            'description': 'Configure bKash mobile money payment method'
        }),
        ('Nagad Configuration', {
            'fields': (
                'nagad_account_number', 'nagad_account_type', 'nagad_account_name',
                'nagad_instructions', 'nagad_reference_required'
            ),
            'classes': ('collapse',),
            'description': 'Configure Nagad mobile money payment method'
        }),
        ('Rocket Configuration', {
            'fields': (
                'rocket_account_number', 'rocket_account_type', 'rocket_account_name',
                'rocket_instructions', 'rocket_reference_required'
            ),
            'classes': ('collapse',),
            'description': 'Configure Rocket mobile money payment method'
        }),
        ('Bank Transfer Configuration', {
            'fields': (
                'bank_name', 'bank_branch', 'bank_account_number', 'bank_account_name',
                'bank_routing_number', 'bank_swift_code', 'bank_instructions', 
                'bank_reference_required'
            ),
            'classes': ('collapse',),
            'description': 'Configure traditional bank transfer method'
        }),
        ('DeltaCoin Configuration', {
            'fields': ('deltacoin_instructions',),
            'classes': ('collapse',),
            'description': 'Optional custom instructions for DeltaCoin payments (usually not needed)'
        }),
    )


# ============================================================================
# MAIN MODEL ADMINS
# ============================================================================

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Comprehensive game management"""
    
    list_display = [
        'name', 'slug', 'default_team_size', 'default_result_type', 
        'is_active', 'tournament_count', 'created_at'
    ]
    list_filter = ['is_active', 'default_team_size', 'default_result_type', 'created_at']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['created_at', 'tournament_count']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Game Configuration', {
            'fields': ('default_team_size', 'profile_id_field', 'default_result_type')
        }),
        ('Game Config (JSON)', {
            'fields': ('game_config',),
            'classes': ('collapse',),
            'description': (
                'Advanced configuration in JSON format. Defines allowed tournament formats, '
                'team size constraints, custom field schemas, and match settings.'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'tournament_count')
        }),
    )
    
    actions = ['activate_games', 'deactivate_games']
    
    def tournament_count(self, obj):
        """Display count of tournaments using this game"""
        count = obj.tournaments.count()
        if count > 0:
            url = f'/admin/tournaments/tournament/?game__id__exact={obj.id}'
            return format_html('<a href="{}">{} tournaments</a>', url, count)
        return format_html('<span style="color: gray;">0 tournaments</span>')
    tournament_count.short_description = 'Tournaments'
    
    def activate_games(self, request, queryset):
        """Activate selected games"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} game(s) activated successfully.', messages.SUCCESS)
    activate_games.short_description = "✅ Activate selected games"
    
    def deactivate_games(self, request, queryset):
        """Deactivate selected games"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} game(s) deactivated.', messages.INFO)
    deactivate_games.short_description = "❌ Deactivate selected games"
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Enhance JSON fields with better textarea widget"""
        if db_field.name == 'game_config':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 15, 'cols': 80, 'style': 'font-family: monospace;'}
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """Comprehensive tournament management - similar to Teams admin quality"""
    
    list_display = [
        'name', 'game_badge', 'organizer_link', 'status_badge', 
        'format', 'registration_count', 'tournament_start', 
        'is_official', 'organizer_console_link'
    ]
    list_filter = [
        'status', 'format', 'participation_type', 'is_official', 'game',
        'enable_check_in', 'has_entry_fee', 'created_at'
    ]
    search_fields = ['name', 'slug', 'description', 'organizer__username', 'organizer__email']
    readonly_fields = [
        'created_at', 'updated_at', 'published_at', 'tournament_end',
        'registration_count_display', 'match_count', 'organizer_console_button',
        'deleted_at', 'deleted_by'
    ]
    prepopulated_fields = {'slug': ('name',)}
    inlines = [TournamentPaymentMethodInline, TournamentStaffInline, CustomFieldInline, TournamentVersionInline]
    ordering = ['-created_at']
    date_hierarchy = 'tournament_start'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'game', 'organizer', 'is_official', 'organizer_console_button')
        }),
        ('Description & Rules', {
            'fields': ('description', 'rules_text')
        }),
        ('Tournament Configuration', {
            'fields': (
                'format', 'participation_type', 'max_participants', 'min_participants'
            )
        }),
        ('Schedule', {
            'fields': (
                'registration_start', 'registration_end', 
                'tournament_start', 'tournament_end'
            )
        }),
        ('Prize Pool', {
            'fields': (
                'prize_pool', 'prize_currency', 'prize_deltacoin', 'prize_distribution'
            ),
            'classes': ('collapse',)
        }),
        ('Entry Fee & Payment', {
            'fields': (
                'has_entry_fee', 'entry_fee_amount', 'entry_fee_currency', 
                'entry_fee_deltacoin', 'payment_methods',
                'enable_fee_waiver', 'fee_waiver_top_n_teams'
            ),
            'classes': ('collapse',)
        }),
        ('Media & Streaming', {
            'fields': (
                'banner_image', 'thumbnail_image', 'rules_pdf',
                'promo_video_url', 'stream_youtube_url', 'stream_twitch_url'
            ),
            'classes': ('collapse',)
        }),
        ('Features & Settings', {
            'fields': (
                'enable_check_in', 'check_in_minutes_before', 'check_in_closes_minutes_before',
                'enable_dynamic_seeding', 'enable_live_updates', 
                'enable_certificates', 'enable_challenges', 'enable_fan_voting'
            ),
            'classes': ('collapse',)
        }),
        ('Status & Statistics', {
            'fields': (
                'status', 'published_at', 'registration_count_display', 'match_count'
            )
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Advanced Configuration (JSON)', {
            'fields': ('config',),
            'classes': ('collapse',),
            'description': 'Advanced tournament configuration and feature flags (JSONB)'
        }),
        ('Soft Delete (Read Only)', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'publish_tournaments', 'open_registration', 'close_registration', 
        'cancel_tournaments', 'feature_tournaments'
    ]
    
    def get_queryset(self, request):
        """Include soft-deleted tournaments and annotate with counts"""
        qs = Tournament.all_objects.all()
        qs = qs.select_related('game', 'organizer')
        qs = qs.annotate(reg_count=Count('registrations', distinct=True))
        return qs
    
    def game_badge(self, obj):
        """Display game with color badge"""
        if not obj.game:
            return format_html('<span style="color: gray;">No Game</span>')
        return format_html(
            '<span style="background: #4A90E2; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            obj.game.name
        )
    game_badge.short_description = 'Game'
    
    def organizer_link(self, obj):
        """Link to organizer's user profile"""
        if obj.organizer:
            url = reverse('admin:accounts_user_change', args=[obj.organizer.pk])
            return format_html('<a href="{}">{}</a>', url, obj.organizer.username)
        return '—'
    organizer_link.short_description = 'Organizer'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'draft': '#9E9E9E',
            'pending_approval': '#FF9800',
            'published': '#2196F3',
            'registration_open': '#4CAF50',
            'registration_closed': '#FF9800',
            'live': '#F44336',
            'completed': '#4CAF50',
            'cancelled': '#9E9E9E',
            'archived': '#9E9E9E',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def registration_count(self, obj):
        """Display registration count"""
        count = obj.reg_count if hasattr(obj, 'reg_count') else obj.registrations.count()
        return format_html('<strong>{}</strong> / {}', count, obj.max_participants)
    registration_count.short_description = 'Registrations'
    registration_count.admin_order_field = 'reg_count'
    
    def registration_count_display(self, obj):
        """Detailed registration count with link"""
        count = obj.registrations.count()
        if count > 0:
            url = f'/admin/tournaments/registration/?tournament__id__exact={obj.id}'
            return format_html('<a href="{}">{} registrations</a>', url, count)
        return '0 registrations'
    registration_count_display.short_description = 'Registrations'
    
    def match_count(self, obj):
        """Display match count with link"""
        count = obj.matches.count()
        if count > 0:
            url = f'/admin/tournaments/match/?tournament__id__exact={obj.id}'
            return format_html('<a href="{}">{} matches</a>', url, count)
        return '0 matches'
    match_count.short_description = 'Matches'
    
    def organizer_console_link(self, obj):
        """Quick link to organizer console"""
        url = reverse('tournaments:organizer_tournament_detail', args=[obj.slug])
        return format_html(
            '<a href="{}" target="_blank" style="color: #F57C00; font-weight: bold;">⚙️ Manage</a>',
            url
        )
    organizer_console_link.short_description = 'Console'
    
    def organizer_console_button(self, obj):
        """Button to open organizer console for this tournament"""
        if not obj.pk:
            return '—'
        url = reverse('tournaments:organizer_tournament_detail', args=[obj.slug])
        return format_html(
            '<a href="{}" target="_blank" class="button" style="background: #F57C00; '
            'color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">'
            '⚙️ Open Organizer Console</a>',
            url
        )
    organizer_console_button.short_description = 'Organizer Tools'
    
    def save_model(self, request, obj, form, change):
        """Set organizer to current user if creating new tournament"""
        if not change and not obj.organizer_id:
            obj.organizer = request.user
        super().save_model(request, obj, form, change)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restrict organizer choices to staff users"""
        if db_field.name == 'organizer':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            kwargs['queryset'] = User.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Enhance text and JSON fields with better widgets"""
        if db_field.name == 'config' or db_field.name == 'prize_distribution':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 15, 'cols': 80, 'style': 'font-family: monospace;'}
            )
        elif CKEDITOR_AVAILABLE and db_field.name in ['description', 'rules_text']:
            kwargs['widget'] = CKEditor5Widget(config_name='default')
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    # Admin Actions
    @admin.action(description='✅ Publish selected tournaments')
    def publish_tournaments(self, request, queryset):
        """Bulk publish tournaments"""
        updated = queryset.filter(status=Tournament.DRAFT).update(
            status=Tournament.PUBLISHED,
            published_at=timezone.now()
        )
        self.message_user(request, f'{updated} tournament(s) published successfully.', messages.SUCCESS)
    
    @admin.action(description='🟢 Open registration for selected')
    def open_registration(self, request, queryset):
        """Bulk open registration"""
        updated = queryset.filter(
            status__in=[Tournament.PUBLISHED, Tournament.REGISTRATION_CLOSED]
        ).update(status=Tournament.REGISTRATION_OPEN)
        self.message_user(request, f'Registration opened for {updated} tournament(s).', messages.SUCCESS)
    
    @admin.action(description='🔴 Close registration for selected')
    def close_registration(self, request, queryset):
        """Bulk close registration"""
        updated = queryset.filter(status=Tournament.REGISTRATION_OPEN).update(
            status=Tournament.REGISTRATION_CLOSED
        )
        self.message_user(request, f'Registration closed for {updated} tournament(s).', messages.INFO)
    
    @admin.action(description='❌ Cancel selected tournaments')
    def cancel_tournaments(self, request, queryset):
        """Bulk cancel tournaments"""
        updated = queryset.exclude(
            status__in=[Tournament.COMPLETED, Tournament.CANCELLED]
        ).update(status=Tournament.CANCELLED)
        self.message_user(request, f'{updated} tournament(s) cancelled.', messages.INFO)
    
    @admin.action(description='⭐ Feature selected tournaments')
    def feature_tournaments(self, request, queryset):
        """Mark tournaments as featured/official"""
        updated = queryset.update(is_official=True)
        self.message_user(request, f'{updated} tournament(s) marked as official.', messages.SUCCESS)


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    """Standalone management of custom fields"""
    
    list_display = [
        'field_name', 'tournament_link', 'field_type', 
        'order', 'is_required', 'tournament_status'
    ]
    list_filter = ['field_type', 'is_required', 'tournament__status', 'tournament__game']
    search_fields = ['field_name', 'field_key', 'tournament__name']
    readonly_fields = ['field_key']
    ordering = ['tournament', 'order', 'field_name']
    
    fieldsets = (
        ('Field Definition', {
            'fields': ('tournament', 'field_name', 'field_key', 'field_type')
        }),
        ('Configuration (JSON)', {
            'fields': ('field_config',),
            'classes': ('collapse',)
        }),
        ('Display & Validation', {
            'fields': ('order', 'is_required', 'help_text')
        }),
    )
    
    def tournament_link(self, obj):
        """Link to tournament"""
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.pk])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
    tournament_link.short_description = 'Tournament'
    
    def tournament_status(self, obj):
        """Display tournament status"""
        return obj.tournament.get_status_display()
    tournament_status.short_description = 'Tournament Status'
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Enhance JSON fields"""
        if db_field.name == 'field_config':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 10, 'cols': 80, 'style': 'font-family: monospace;'}
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(TournamentVersion)
class TournamentVersionAdmin(admin.ModelAdmin):
    """Read-only version history for audit trail"""
    
    list_display = [
        'tournament_link', 'version_number', 'change_summary', 
        'changed_by', 'changed_at', 'is_active'
    ]
    list_filter = ['is_active', 'changed_at', 'tournament__status']
    search_fields = ['tournament__name', 'change_summary']
    readonly_fields = [
        'tournament', 'version_number', 'version_data', 'change_summary',
        'changed_by', 'changed_at', 'is_active', 'rolled_back_at', 'rolled_back_by'
    ]
    ordering = ['-changed_at']
    date_hierarchy = 'changed_at'
    
    fieldsets = (
        ('Version Information', {
            'fields': ('tournament', 'version_number', 'change_summary')
        }),
        ('Version Data (Snapshot)', {
            'fields': ('version_data',),
            'classes': ('collapse',)
        }),
        ('Change Tracking', {
            'fields': ('changed_by', 'changed_at', 'is_active')
        }),
        ('Rollback Information', {
            'fields': ('rolled_back_at', 'rolled_back_by'),
            'classes': ('collapse',)
        }),
    )
    
    def tournament_link(self, obj):
        """Link to tournament"""
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.pk])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
    tournament_link.short_description = 'Tournament'
    
    def has_add_permission(self, request):
        """Versions are created automatically"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Versions should not be deleted for audit trail"""
        return False


@admin.register(TournamentTemplate)
class TournamentTemplateAdmin(admin.ModelAdmin):
    """Template management for quick tournament creation"""
    
    list_display = [
        'name', 'game', 'visibility', 'is_active', 
        'usage_count', 'last_used_at', 'created_by'
    ]
    list_filter = ['visibility', 'is_active', 'game', 'created_at']
    search_fields = ['name', 'slug', 'description', 'created_by__username']
    readonly_fields = ['slug', 'usage_count', 'last_used_at', 'created_at', 'updated_at']
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
            'description': 'Tournament configuration template in JSON format'
        }),
        ('Status & Usage', {
            'fields': ('is_active', 'usage_count', 'last_used_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_templates', 'deactivate_templates']
    
    @admin.action(description="✅ Activate selected templates")
    def activate_templates(self, request, queryset):
        """Activate selected templates"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} template(s) activated.", messages.SUCCESS)
    
    @admin.action(description="❌ Deactivate selected templates")
    def deactivate_templates(self, request, queryset):
        """Deactivate selected templates"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} template(s) deactivated.", messages.INFO)
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Enhance JSON fields"""
        if db_field.name == 'template_config':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 20, 'cols': 80, 'style': 'font-family: monospace;'}
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)


# Note: Registration, Payment, Match, Dispute, Bracket, Certificate, TournamentResult, 
# and PrizeTransaction admins are registered in their respective admin_*.py files
