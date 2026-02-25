"""
Tournaments App - Django Admin Configuration

Provides comprehensive admin interface for managing tournaments, games, registrations,
matches, and all tournament-related content. Modeled after the Teams admin for consistency.

Architecture:
- Main models registered here (Tournament, Game, CustomField, TournamentVersion, TournamentTemplate)
- Specialized admins in separate files (admin_registration, admin_match, admin_bracket, etc.)
"""

from django.contrib import admin
from django.db import models
from django import forms
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from apps.common.admin_mixins import SafeUploadMixin
from unfold.decorators import display
from unfold.widgets import UnfoldBooleanSwitchWidget
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
    TournamentStaffRole, TournamentStaff, TournamentAnnouncement,
    RegistrationFormTemplate, TournamentRegistrationForm, FormResponse,
    TournamentFormConfiguration,
    TournamentSponsor, PrizeClaim,
)
from apps.games.services import game_service
from apps.games.models.game import Game as GamesGame
from apps.tournaments.utils import import_rules_from_pdf
from deltacrown.admin_widgets import (
    PrizeDistributionWidget, CoordinatorRolesWidget,
    CommunicationChannelsWidget, MemberCustomFieldsWidget,
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

class CustomFieldInline(TabularInline):
    """Inline editor for CustomField within Tournament admin"""
    model = CustomField
    extra = 0
    fields = ['field_name', 'field_key', 'field_type', 'order', 'is_required', 'help_text']
    prepopulated_fields = {'field_key': ('field_name',)}


class TournamentVersionInline(TabularInline):
    """Inline display for TournamentVersion within Tournament admin (read-only audit trail)"""
    model = TournamentVersion
    extra = 0
    max_num = 20  # Cap to prevent unbounded inline loading
    can_delete = False
    readonly_fields = ['version_number', 'change_summary', 'changed_by', 'changed_at', 'is_active']
    fields = ['version_number', 'change_summary', 'changed_by', 'changed_at', 'is_active']
    ordering = ['-changed_at']
    
    def has_add_permission(self, request, obj=None):
        """Versions are created automatically, not manually"""
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('changed_by')


class TournamentFormConfigurationInline(StackedInline):
    """
    Inline editor for registration form configuration.
    Allows organizers to customise every aspect of the registration experience:
    - Coordinator role options
    - Dynamic communication channels
    - Team info fields
    - Roster / member requirements
    - Legacy boolean toggles (backward-compatible)
    - Payment field toggles
    """
    model = TournamentFormConfiguration
    extra = 0
    can_delete = False
    max_num = 1

    fieldsets = (
        ('Form Type Selection', {
            'fields': ('form_type', 'custom_form'),
            'description': 'Choose between default solo/team forms or create a custom form.',
        }),
        ('Coordinator Role', {
            'fields': (
                'enable_coordinator_role',
                'coordinator_role_choices',
                'coordinator_help_text',
            ),
            'classes': ('collapse',),
            'description': (
                'Configure the "Match Coordinator" role selector shown in the registration form. '
                'Leave role choices empty to use the built-in defaults (Captain/IGL, Manager, Coach, Other).'
            ),
        }),
        ('Communication Channels', {
            'fields': (
                'communication_channels',
                'enable_preferred_communication',
            ),
            'classes': ('collapse',),
            'description': (
                'Define which contact channels appear in the registration form. '
                'Each channel: {"key":"discord","label":"Discord ID","placeholder":"User#0000",'
                '"icon":"discord","required":true,"type":"text"}. '
                'Leave empty to use defaults (Phone + Discord).'
            ),
        }),
        ('Team Info Fields', {
            'fields': (
                'enable_team_logo_upload',
                'enable_team_banner_upload',
                'enable_team_bio',
            ),
            'classes': ('collapse',),
            'description': 'Allow teams to upload logo/banner or add a bio during registration.',
        }),
        ('Roster & Member Requirements', {
            'fields': (
                'allow_roster_editing',
                'show_member_ranks',
                'show_member_game_ids',
                'require_member_real_name',
                'require_member_photo',
                'require_member_email',
                'require_member_age',
                'require_member_national_id',
                'member_custom_fields',
            ),
            'classes': ('collapse',),
            'description': (
                'Configure what information is required for each roster member. '
                'For LAN / official tournaments, enable real name, photo, and national ID.'
            ),
        }),
        ('Solo Registration Fields', {
            'fields': (
                'enable_age_field', 'enable_country_field',
                'enable_platform_field', 'enable_rank_field',
                'enable_phone_field', 'enable_discord_field',
                'enable_preferred_contact_field',
            ),
            'classes': ('collapse',),
            'description': 'Toggle which optional fields appear on solo / per-player registration forms.',
        }),
        ('Team Registration Fields', {
            'fields': (
                'enable_team_logo_field', 'enable_team_region_field',
                'enable_captain_display_name_field', 'enable_captain_whatsapp_field',
                'enable_captain_phone_field', 'enable_captain_discord_field',
                'enable_roster_display_names', 'enable_roster_emails',
            ),
            'classes': ('collapse',),
            'description': 'Toggle which optional fields appear on team registration forms (captain details, roster extras).',
        }),
        ('Payment Fields', {
            'fields': (
                'enable_payment_mobile_number_field',
                'enable_payment_screenshot_field',
                'enable_payment_notes_field',
            ),
            'classes': ('collapse',),
            'description': 'Toggle optional payment-related fields.',
        }),
        ('Rules & Agreements', {
            'fields': (
                'custom_registration_rules',
                'custom_tos_text',
                'custom_fair_play_text',
            ),
            'description': (
                '📋 Shown on the Review & Submit step. Leave any field blank to use DeltaCrown\'s default text. '
                'Tip: write your own tournament-specific rules, terms, or fair-play expectations here.'
            ),
        }),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Replace JSON textareas with user-friendly table widgets, add Rules placeholders."""
        widget_map = {
            'coordinator_role_choices': CoordinatorRolesWidget,
            'communication_channels': CommunicationChannelsWidget,
            'member_custom_fields': MemberCustomFieldsWidget,
        }
        if db_field.name in widget_map:
            kwargs['widget'] = widget_map[db_field.name]()
        # Helpful placeholders for Rules & Agreements text fields
        rules_placeholders = {
            'custom_registration_rules': 'e.g. Players must be 16+ to participate.\nEach team must have a minimum of 5 active players.\nAll participants must join the tournament Discord server.',
            'custom_tos_text': 'e.g. By registering, you agree to follow all tournament rules.\nViolations may result in disqualification and account suspension.',
            'custom_fair_play_text': 'e.g. No use of cheats, exploits, or third-party software.\nRespect all opponents and tournament staff.\nUnsportsmanlike conduct will result in penalties.',
        }
        if db_field.name in rules_placeholders:
            kwargs.setdefault('widget', forms.Textarea(attrs={
                'rows': 5,
                'placeholder': rules_placeholders[db_field.name],
                'style': 'width:100%;',
            }))
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class TournamentPaymentMethodInline(StackedInline):
    """
    Inline editor for configuring payment methods.
    Each method (bKash, Nagad, etc.) only shows the relevant fields
    based on the selected method type — powered by dynamic JS toggle.
    """
    model = TournamentPaymentMethod
    extra = 1
    can_delete = True
    show_change_link = True
    verbose_name = "Payment Method"
    verbose_name_plural = "Payment Methods (add one per provider: bKash, Nagad, etc.)"
    
    fieldsets = (
        ('Basic Configuration', {
            'fields': ('method', 'is_enabled', 'display_order'),
            'description': 'Select a method and it will reveal the relevant configuration fields below.'
        }),
        ('bKash Configuration', {
            'fields': (
                'bkash_account_number', 'bkash_account_type', 'bkash_account_name',
                'bkash_instructions', 'bkash_reference_required'
            ),
            'classes': ('pm-section', 'pm-bkash',),
            'description': 'Configure bKash mobile money payment method'
        }),
        ('Nagad Configuration', {
            'fields': (
                'nagad_account_number', 'nagad_account_type', 'nagad_account_name',
                'nagad_instructions', 'nagad_reference_required'
            ),
            'classes': ('pm-section', 'pm-nagad',),
            'description': 'Configure Nagad mobile money payment method'
        }),
        ('Rocket Configuration', {
            'fields': (
                'rocket_account_number', 'rocket_account_type', 'rocket_account_name',
                'rocket_instructions', 'rocket_reference_required'
            ),
            'classes': ('pm-section', 'pm-rocket',),
            'description': 'Configure Rocket mobile money payment method'
        }),
        ('Bank Transfer Configuration', {
            'fields': (
                'bank_name', 'bank_branch', 'bank_account_number', 'bank_account_name',
                'bank_routing_number', 'bank_swift_code', 'bank_instructions', 
                'bank_reference_required'
            ),
            'classes': ('pm-section', 'pm-bank_transfer',),
            'description': 'Configure traditional bank transfer method'
        }),
        ('DeltaCoin Configuration', {
            'fields': ('deltacoin_instructions',),
            'classes': ('pm-section', 'pm-deltacoin',),
            'description': 'Optional custom instructions for DeltaCoin payments (usually not needed)'
        }),
    )
    
    class Media:
        js = ('admin/js/payment_method_toggle.js',)


# ============================================================================
# MAIN MODEL ADMINS
# ============================================================================
# NOTE: Game admin is registered in apps/games/admin.py (removed duplicate)

@admin.register(Tournament)
class TournamentAdmin(SafeUploadMixin, ModelAdmin):
    """Comprehensive tournament management - similar to Teams admin quality"""
    
    list_per_page = 25
    list_display = [
        'name', 'game_badge', 'official_badge', 'featured_badge', 'organizer_link', 'status_badge', 
        'format', 'registration_count', 'tournament_start', 
        'organizer_console_link'
    ]
    list_filter = [
        'status', 'format', 'participation_type', 'is_official', 'is_featured', 'game',
        'enable_check_in', 'has_entry_fee', 'created_at'
    ]
    search_fields = ['name', 'slug', 'description', 'organizer__username', 'organizer__email']
    readonly_fields = [
        'created_at', 'updated_at', 'published_at', 'tournament_end',
        'registration_count_display', 'match_count', 'organizer_console_button',
        'deleted_at', 'deleted_by'
    ]
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['game', 'organizer']
    formfield_overrides = {
        models.BooleanField: {"widget": UnfoldBooleanSwitchWidget},
    }
    inlines = [TournamentFormConfigurationInline, TournamentPaymentMethodInline, CustomFieldInline, TournamentVersionInline]
    ordering = ['-created_at']
    date_hierarchy = 'tournament_start'
    
    fieldsets = (
        ('Core Tournament', {
            'fields': (
                'name', 'slug', 'game', 'organizer', 'status',
                'is_official', 'is_featured', 'organizer_console_button',
            ),
            'description': (
                'Essential tournament identity. <strong>Organizer</strong> gets full management '
                'via the Organizer Console. Status workflow: Draft → Published → Reg Open → Live → Completed.'
            ),
        }),
        ('Format & Capacity', {
            'fields': (
                'format', 'participation_type', 'platform', 'mode',
                'max_participants', 'min_participants',
                'max_guest_teams', 'allow_display_name_override',
            ),
            'description': (
                'Tournament format (Single/Double Elim, Round Robin, Swiss, Group+Playoffs), '
                'Solo vs Team, and participant limits. Guest teams allow unregistered squads to join.'
            ),
        }),
        ('Schedule & Check-In', {
            'fields': (
                'registration_start', 'registration_end',
                'tournament_start', 'tournament_end',
                'enable_check_in', 'check_in_minutes_before', 'check_in_closes_minutes_before',
            ),
            'description': 'Registration window and tournament dates. Check-in requires participants to confirm attendance before matches.',
        }),
        ('Entry Fees & Prizes', {
            'fields': (
                'has_entry_fee', 'entry_fee_amount', 'entry_fee_currency', 'entry_fee_deltacoin',
                'payment_deadline_hours', 'refund_policy', 'refund_policy_text',
                'enable_fee_waiver', 'fee_waiver_top_n_teams',
                'prize_pool', 'prize_currency', 'prize_deltacoin', 'prize_distribution',
            ),
            'description': (
                'Configure fees and prizes. Payment method details (account numbers, instructions) '
                'are set in the <strong>Payment Methods</strong> inline below. '
                'Prize distribution: JSON e.g. <code>{"1": 500, "2": 250, "3": 125}</code>.'
            ),
        }),
        ('Rules & Terms', {
            'fields': (
                'rules_text', 'rules_pdf',
                'terms_and_conditions', 'terms_pdf', 'require_terms_acceptance',
            ),
            'description': (
                'Provide rules as rich text or PDF upload. '
                'Additional registration-specific rules can be set in the '
                '<strong>Form Configuration</strong> inline below.'
            ),
        }),
        ('Description & Media', {
            'fields': (
                'description', 'banner_image', 'thumbnail_image',
                'promo_video_url', 'stream_youtube_url', 'stream_twitch_url',
            ),
            'description': 'Tournament description and media. Banner: 1920x480, Thumbnail: 400x400.',
        }),
        ('Social & Contact Links', {
            'fields': (
                'social_discord', 'social_twitter', 'social_instagram',
                'social_youtube', 'social_website', 'contact_email',
            ),
            'classes': ('collapse',),
            'description': 'Organizer social links and contact info displayed in the Hub Resources tab.',
        }),
        ('Venue (LAN / Hybrid)', {
            'fields': ('venue_name', 'venue_address', 'venue_city', 'venue_map_url'),
            'classes': ('collapse',),
            'description': 'Only needed for LAN or Hybrid tournaments.',
        }),
        ('Feature Toggles', {
            'fields': (
                'enable_dynamic_seeding', 'enable_live_updates',
                'enable_certificates', 'enable_challenges', 'enable_fan_voting',
            ),
            'classes': ('collapse',),
            'description': 'Optional features: auto-seeding, live score updates, completion certificates, challenges, fan voting.',
        }),
        ('SEO & Metadata', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        ('Statistics', {
            'fields': ('registration_count_display', 'match_count', 'created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',),
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',),
        }),
    )
    
    actions = [
        'publish_tournaments', 'open_registration', 'close_registration', 
        'cancel_tournaments', 'feature_tournaments', 'import_rules_from_pdf_action',
        'transition_to_knockout_stage_action'
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
    
    @display(description="Official", ordering="is_official", boolean=True)
    def official_badge(self, obj):
        """Display official tournament badge."""
        return obj.is_official
    
    @display(description="Featured", ordering="is_featured", boolean=True)
    def featured_badge(self, obj):
        """Display featured tournament badge."""
        return obj.is_featured
    
    def organizer_link(self, obj):
        """Link to organizer's user profile"""
        if obj.organizer:
            url = reverse('admin:accounts_user_change', args=[obj.organizer.pk])
            return format_html('<a href="{}">{}</a>', url, obj.organizer.username)
        return '—'
    organizer_link.short_description = 'Organizer'
    
    @display(
        description="Status",
        ordering="status",
        label={
            "draft": "secondary",
            "pending_approval": "warning",
            "published": "info",
            "registration_open": "success",
            "registration_closed": "warning",
            "live": "danger",
            "completed": "success",
            "cancelled": "secondary",
            "archived": "secondary",
        },
    )
    def status_badge(self, obj):
        """Display status with Unfold colored label badge."""
        return obj.status
    
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
        """Quick link to Tournament Operations Center (TOC)"""
        url = reverse('toc:hub', kwargs={'slug': obj.slug})
        return format_html(
            '<a href="{}" target="_blank" style="color: #F57C00; font-weight: bold;">⚙️ TOC</a>',
            url
        )
    organizer_console_link.short_description = 'Console'
    
    def organizer_console_button(self, obj):
        """Button to open Tournament Operations Center (TOC)"""
        if not obj.pk:
            return '—'
        url = reverse('toc:hub', kwargs={'slug': obj.slug})
        return format_html(
            '<a href="{}" target="_blank" class="button" style="background: #F57C00; '
            'color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">'
            '⚙️ Open TOC</a>',
            url
        )
    organizer_console_button.short_description = 'Operations Center'
    
    def save_model(self, request, obj, form, change):
        """Set organizer to current user if creating new tournament, handle official tournaments"""
        # Handle official tournaments - auto-assign to official account
        if obj.is_official:
            # Try to get official organizer account (ID=1 or username='deltacrown')
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                official_user = User.objects.filter(Q(id=1) | Q(username='deltacrown') | Q(is_superuser=True)).first()
                if official_user:
                    obj.organizer = official_user
            except User.DoesNotExist:
                pass
        elif not change and not obj.organizer_id:
            # Set organizer to current user if creating new non-official tournament
            obj.organizer = request.user
        super().save_model(request, obj, form, change)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restrict choices for organizer and game fields"""
        if db_field.name == 'organizer':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            kwargs['queryset'] = User.objects.filter(is_staff=True)
        elif db_field.name == 'game':
            # Filter to only show active games — single query, no double-hit
            kwargs['queryset'] = GamesGame.objects.filter(is_active=True).order_by('display_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Enhance text and JSON fields with better widgets"""
        if db_field.name == 'prize_distribution':
            kwargs['widget'] = PrizeDistributionWidget()
        elif db_field.name == 'config':
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
    
    @admin.action(description='📄 Import rules_text from PDF')
    def import_rules_from_pdf_action(self, request, queryset):
        """
        Import rules from PDF files into rules_text field.
        
        For each selected tournament:
        - If rules_pdf exists, extract text and convert to HTML
        - Overwrites existing rules_text
        - Skips tournaments without PDF attached
        """
        success_count = 0
        skip_count = 0
        error_count = 0
        errors = []
        
        for tournament in queryset:
            try:
                # Check if tournament has a PDF
                if not tournament.rules_pdf or not tournament.rules_pdf.name:
                    skip_count += 1
                    continue
                
                # Import rules from PDF
                html = import_rules_from_pdf(tournament, overwrite=True)
                
                if html:
                    success_count += 1
                else:
                    skip_count += 1
                    
            except ImportError as e:
                error_count += 1
                errors.append(f"{tournament.name}: {str(e)}")
            except FileNotFoundError:
                error_count += 1
                errors.append(f"{tournament.name}: PDF file not found on disk")
            except Exception as e:
                error_count += 1
                errors.append(f"{tournament.name}: {str(e)}")
        
        # Build result message
        message_parts = []
        
        if success_count > 0:
            message_parts.append(f'✅ Successfully imported {success_count} tournament(s)')
        
        if skip_count > 0:
            message_parts.append(f'⏭️ Skipped {skip_count} tournament(s) (no PDF attached)')
        
        if error_count > 0:
            message_parts.append(f'❌ Failed {error_count} tournament(s)')
        
        # Show main message
        if success_count > 0:
            level = messages.SUCCESS
        elif error_count > 0:
            level = messages.ERROR
        else:
            level = messages.INFO
        
        self.message_user(request, ' | '.join(message_parts), level)
        
        # Show individual errors if any
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                self.message_user(request, f'Error: {error}', messages.ERROR)
            if len(errors) > 5:
                self.message_user(
                    request, 
                    f'... and {len(errors) - 5} more error(s)', 
                    messages.ERROR
                )
    
    @admin.action(description='🚀 Transition GROUP_PLAYOFF tournaments to knockout stage')
    def transition_to_knockout_stage_action(self, request, queryset):
        """
        Transition selected GROUP_PLAYOFF tournaments from group stage to knockout stage.
        
        For each tournament:
        - Validates format is GROUP_PLAYOFF
        - Ensures all group stage matches are completed
        - Recalculates final group standings
        - Generates knockout bracket from advancers
        - Updates tournament stage tracking
        
        Skips tournaments that:
        - Are not GROUP_PLAYOFF format
        - Have incomplete group stage matches
        - Are already in knockout stage
        """
        from apps.tournaments.services.tournament_service import TournamentService
        
        success_count = 0
        skip_count = 0
        error_count = 0
        errors = []
        
        for tournament in queryset:
            try:
                # Skip if not GROUP_PLAYOFF
                if tournament.format != Tournament.GROUP_PLAYOFF:
                    skip_count += 1
                    continue
                
                # Skip if already in knockout stage
                current_stage = tournament.get_current_stage()
                if current_stage == Tournament.STAGE_KNOCKOUT:
                    skip_count += 1
                    continue
                
                # Attempt transition
                bracket = TournamentService.transition_to_knockout_stage(tournament.id)
                success_count += 1
                
            except ValidationError as e:
                error_count += 1
                errors.append(f"{tournament.name}: {str(e)}")
            except Exception as e:
                error_count += 1
                errors.append(f"{tournament.name}: Unexpected error: {str(e)}")
        
        # Build result message
        message_parts = []
        
        if success_count > 0:
            message_parts.append(f'✅ Successfully transitioned {success_count} tournament(s) to knockout stage')
        
        if skip_count > 0:
            message_parts.append(f'⏭️ Skipped {skip_count} tournament(s) (not GROUP_PLAYOFF or already in knockout)')
        
        if error_count > 0:
            message_parts.append(f'❌ Failed {error_count} tournament(s)')
        
        # Show main message
        if success_count > 0:
            level = messages.SUCCESS
        elif error_count > 0:
            level = messages.ERROR
        else:
            level = messages.INFO
        
        self.message_user(request, ' | '.join(message_parts), level)
        
        # Show detailed errors
        if errors:
            for error in errors[:5]:
                self.message_user(request, f'Error: {error}', messages.ERROR)
            if len(errors) > 5:
                self.message_user(
                    request,
                    f'... and {len(errors) - 5} more error(s)',
                    messages.ERROR
                )


@admin.register(CustomField)
class CustomFieldAdmin(ModelAdmin):
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
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tournament')

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
class TournamentVersionAdmin(ModelAdmin):
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
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tournament', 'changed_by', 'rolled_back_by')

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
class TournamentTemplateAdmin(ModelAdmin):
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


# ============================================================================
# ANNOUNCEMENT ADMIN
# ============================================================================

@admin.register(TournamentAnnouncement)
class TournamentAnnouncementAdmin(ModelAdmin):
    """
    Admin interface for tournament announcements.
    Allows organizers to create and manage announcements for participants.
    """
    list_display = ['title', 'tournament_link', 'created_by', 'created_at', 'is_pinned_badge', 'is_important_badge']
    list_filter = ['is_pinned', 'is_important', 'created_at', 'tournament']
    search_fields = ['title', 'message', 'tournament__name', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    list_select_related = ['tournament', 'created_by']
    ordering = ['-is_pinned', '-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tournament', 'title', 'message')
        }),
        ('Display Options', {
            'fields': ('is_pinned', 'is_important'),
            'description': 'Pinned announcements appear at the top. Important announcements are highlighted.'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def tournament_link(self, obj):
        """Link to tournament detail page"""
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.pk])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
    tournament_link.short_description = 'Tournament'
    
    def is_pinned_badge(self, obj):
        """Display badge for pinned status"""
        if obj.is_pinned:
            return format_html('<span style="background:#ffc107;color:#000;padding:2px 8px;border-radius:3px;font-weight:bold;">📌 PINNED</span>')
        return '—'
    is_pinned_badge.short_description = 'Pinned'
    
    def is_important_badge(self, obj):
        """Display badge for important status"""
        if obj.is_important:
            return format_html('<span style="background:#dc3545;color:#fff;padding:2px 8px;border-radius:3px;font-weight:bold;">⚠️ IMPORTANT</span>')
        return '—'
    is_important_badge.short_description = 'Important'
    
    def save_model(self, request, obj, form, change):
        """Automatically set created_by to current user if creating"""
        if not change:  # Creating new announcement
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['make_pinned', 'make_unpinned', 'make_important', 'make_normal']
    
    @admin.action(description="📌 Pin selected announcements")
    def make_pinned(self, request, queryset):
        """Pin selected announcements"""
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f"{updated} announcement(s) pinned.", messages.SUCCESS)
    
    @admin.action(description="📍 Unpin selected announcements")
    def make_unpinned(self, request, queryset):
        """Unpin selected announcements"""
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f"{updated} announcement(s) unpinned.", messages.INFO)
    
    @admin.action(description="⚠️ Mark as important")
    def make_important(self, request, queryset):
        """Mark announcements as important"""
        updated = queryset.update(is_important=True)
        self.message_user(request, f"{updated} announcement(s) marked as important.", messages.SUCCESS)
    
    @admin.action(description="✓ Mark as normal")
    def make_normal(self, request, queryset):
        """Remove important flag from announcements"""
        updated = queryset.update(is_important=False)
        self.message_user(request, f"{updated} announcement(s) marked as normal.", messages.INFO)


# ============================================================================
# FORM BUILDER ADMIN (Sprint 1 - Dynamic Registration System)
# ============================================================================

@admin.register(RegistrationFormTemplate)
class RegistrationFormTemplateAdmin(SafeUploadMixin, ModelAdmin):
    """Admin for registration form templates"""
    list_display = [
        'template_badge', 'name', 'participation_type', 'game',
        'usage_badge', 'featured_badge', 'status_badge', 'created_at'
    ]
    list_filter = ['participation_type', 'is_active', 'is_system_template', 'is_featured', 'game']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['usage_count', 'average_completion_rate', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('Classification', {
            'fields': ('participation_type', 'game', 'tags')
        }),
        ('Form Schema', {
            'fields': ('form_schema',),
            'classes': ('collapse',),
            'description': 'JSON schema defining form structure'
        }),
        ('Display Settings', {
            'fields': ('thumbnail', 'is_featured', 'is_active')
        }),
        ('Template Status', {
            'fields': ('is_system_template', 'created_by')
        }),
        ('Analytics', {
            'fields': ('usage_count', 'average_completion_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def template_badge(self, obj):
        """Display template type badge"""
        if obj.is_system_template:
            return format_html('<span style="background:#28a745;color:white;padding:3px 8px;border-radius:3px;font-size:11px;">⭐ SYSTEM</span>')
        return format_html('<span style="background:#6c757d;color:white;padding:3px 8px;border-radius:3px;font-size:11px;">USER</span>')
    template_badge.short_description = 'Type'
    
    def usage_badge(self, obj):
        """Display usage count"""
        color = '#28a745' if obj.usage_count > 10 else '#ffc107' if obj.usage_count > 0 else '#dc3545'
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;border-radius:3px;font-size:11px;">{} uses</span>',
            color, obj.usage_count
        )
    usage_badge.short_description = 'Usage'
    
    def featured_badge(self, obj):
        """Display featured badge"""
        if obj.is_featured:
            return format_html('<span style="color:#ffc107;font-size:16px;" title="Featured">⭐</span>')
        return ''
    featured_badge.short_description = 'Featured'
    
    def status_badge(self, obj):
        """Display status badge"""
        if obj.is_active:
            return format_html('<span style="background:#28a745;color:white;padding:3px 8px;border-radius:3px;font-size:11px;">✓ ACTIVE</span>')
        return format_html('<span style="background:#dc3545;color:white;padding:3px 8px;border-radius:3px;font-size:11px;">✗ INACTIVE</span>')
    status_badge.short_description = 'Status'
    
    @admin.action(description="⭐ Mark as featured")
    def mark_featured(self, request, queryset):
        """Mark templates as featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} template(s) marked as featured.", messages.SUCCESS)
    
    @admin.action(description="Remove featured status")
    def mark_not_featured(self, request, queryset):
        """Remove featured status from templates"""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} template(s) unmarked.", messages.INFO)
    
    @admin.action(description="✓ Activate templates")
    def activate_templates(self, request, queryset):
        """Activate templates"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} template(s) activated.", messages.SUCCESS)
    
    @admin.action(description="✗ Deactivate templates")
    def deactivate_templates(self, request, queryset):
        """Deactivate templates"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} template(s) deactivated.", messages.WARNING)
    
    actions = ['mark_featured', 'mark_not_featured', 'activate_templates', 'deactivate_templates']


@admin.register(TournamentRegistrationForm)
class TournamentRegistrationFormAdmin(ModelAdmin):
    """Admin for tournament registration forms"""
    list_display = [
        'tournament_link', 'template_used', 'analytics_badge',
        'multi_step_badge', 'captcha_badge', 'updated_at'
    ]
    list_filter = ['enable_multi_step', 'enable_captcha', 'enable_autosave']
    search_fields = ['tournament__name', 'tournament__slug']
    readonly_fields = [
        'total_views', 'total_starts', 'total_completions',
        'completion_rate', 'abandonment_rate', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament', 'based_on_template')
        }),
        ('Form Schema', {
            'fields': ('form_schema',),
            'classes': ('collapse',),
        }),
        ('Behavior Settings', {
            'fields': (
                'enable_multi_step', 'enable_autosave', 'enable_progress_bar',
                'allow_edits_after_submit', 'require_email_verification'
            )
        }),
        ('Anti-Spam', {
            'fields': ('enable_captcha', 'rate_limit_per_ip')
        }),
        ('Confirmation', {
            'fields': ('success_message', 'redirect_url', 'send_confirmation_email')
        }),
        ('Advanced', {
            'fields': ('conditional_rules', 'validation_rules'),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': (
                'total_views', 'total_starts', 'total_completions',
                'completion_rate', 'abandonment_rate'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def tournament_link(self, obj):
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
    tournament_link.short_description = 'Tournament'
    
    def template_used(self, obj):
        if obj.based_on_template:
            url = reverse('admin:tournaments_registrationformtemplate_change', args=[obj.based_on_template.id])
            return format_html('<a href="{}">{}</a>', url, obj.based_on_template.name)
        return format_html('<span style="color:#6c757d;">Custom Form</span>')
    template_used.short_description = 'Based On'
    
    def analytics_badge(self, obj):
        if obj.total_completions > 0:
            color = '#28a745' if obj.completion_rate > 70 else '#ffc107' if obj.completion_rate > 40 else '#dc3545'
            return format_html(
                '<span style="background:{};color:white;padding:3px 8px;border-radius:3px;font-size:11px;">{} regs ({}%)</span>',
                color, obj.total_completions, int(obj.completion_rate)
            )
        return format_html('<span style="color:#6c757d;">No data</span>')
    analytics_badge.short_description = 'Analytics'
    
    def multi_step_badge(self, obj):
        if obj.enable_multi_step:
            return format_html('<span style="color:#28a745;">📊</span>')
        return ''
    multi_step_badge.short_description = 'Steps'
    
    def captcha_badge(self, obj):
        if obj.enable_captcha:
            return format_html('<span style="color:#17a2b8;">🛡️</span>')
        return ''
    captcha_badge.short_description = 'Security'


@admin.register(FormResponse)
class FormResponseAdmin(ModelAdmin):
    """Admin for form responses"""
    list_display = [
        'id', 'user_link', 'tournament_link', 'status_badge',
        'payment_badge', 'submitted_at', 'admin_actions'
    ]
    list_filter = ['status', 'has_paid', 'payment_verified', 'tournament']
    search_fields = ['user__username', 'tournament__name']
    list_select_related = ['user', 'tournament', 'team']
    readonly_fields = ['created_at', 'submitted_at', 'approved_at', 'updated_at']
    
    fieldsets = (
        ('Registration', {
            'fields': ('tournament', 'user', 'team', 'status')
        }),
        ('Response Data', {
            'fields': ('response_data',),
            'classes': ('collapse',),
        }),
        ('Payment', {
            'fields': (
                'has_paid', 'payment_verified', 'payment_amount',
                'payment_method', 'payment_transaction_id', 'payment_proof'
            )
        }),
        ('Admin Notes', {
            'fields': ('admin_notes', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'submitted_at', 'approved_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
    user_link.short_description = 'User'
    
    def tournament_link(self, obj):
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
    tournament_link.short_description = 'Tournament'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d', 'submitted': '#17a2b8', 'under_review': '#ffc107',
            'approved': '#28a745', 'rejected': '#dc3545', 'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;border-radius:3px;font-size:11px;">{}</span>',
            color, obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def payment_badge(self, obj):
        if obj.payment_verified:
            return format_html('<span style="background:#28a745;color:white;padding:3px 8px;border-radius:3px;">✓ VERIFIED</span>')
        elif obj.has_paid:
            return format_html('<span style="background:#ffc107;color:white;padding:3px 8px;border-radius:3px;">⏳ PENDING</span>')
        return format_html('<span style="color:#6c757d;">Not Required</span>')
    payment_badge.short_description = 'Payment'
    
    def admin_actions(self, obj):
        """Quick admin action links"""
        actions = []
        if obj.status == 'submitted':
            actions.append(f'<a href="#" style="color:#28a745;" title="Approve">✓</a>')
            actions.append(f'<a href="#" style="color:#dc3545;" title="Reject">✗</a>')
        if obj.has_paid and not obj.payment_verified:
            actions.append(f'<a href="#" style="color:#17a2b8;" title="Verify Payment">💳</a>')
        return format_html(' | '.join(actions)) if actions else '-'
    admin_actions.short_description = 'Actions'
    
    @admin.action(description="✓ Approve registrations")
    def approve_registrations(self, request, queryset):
        """Bulk approve submitted registrations"""
        count = 0
        for response in queryset.filter(status='submitted'):
            response.approve()
            count += 1
        self.message_user(request, f"{count} registration(s) approved.", messages.SUCCESS)
    
    @admin.action(description="✗ Reject registrations")
    def reject_registrations(self, request, queryset):
        """Bulk reject registrations"""
        count = 0
        for response in queryset.filter(status__in=['submitted', 'under_review']):
            response.reject(reason="Bulk rejection by admin")
            count += 1
        self.message_user(request, f"{count} registration(s) rejected.", messages.WARNING)
    
    @admin.action(description="💳 Verify payments")
    def verify_payments(self, request, queryset):
        """Bulk verify payments"""
        updated = queryset.filter(has_paid=True, payment_verified=False).update(payment_verified=True)
        self.message_user(request, f"{updated} payment(s) verified.", messages.SUCCESS)
    
    actions = ['approve_registrations', 'reject_registrations', 'verify_payments']


# ============================================================================
# WEBHOOK ADMIN
# ============================================================================

from apps.tournaments.models.webhooks import FormWebhook, WebhookDelivery


@admin.register(FormWebhook)
class FormWebhookAdmin(ModelAdmin):
    """Admin for form webhooks"""
    
    list_display = ['id', 'tournament_form', 'url', 'event_count', 'is_active', 'delivery_stats', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['url', 'tournament_form__tournament__name']
    list_select_related = ['tournament_form', 'tournament_form__tournament']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tournament_form', 'url', 'is_active')
        }),
        ('Configuration', {
            'fields': ('events', 'secret', 'custom_headers', 'retry_count', 'timeout')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def event_count(self, obj):
        return len(obj.events) if obj.events else 0
    event_count.short_description = 'Events'
    
    def get_queryset(self, request):
        """Annotate delivery stats to avoid N+1 in list_display"""
        from django.db.models import Q
        qs = super().get_queryset(request)
        qs = qs.annotate(
            _delivery_total=Count('deliveries'),
            _delivery_success=Count('deliveries', filter=Q(deliveries__status='success')),
        )
        return qs

    def delivery_stats(self, obj):
        total = getattr(obj, '_delivery_total', 0)
        success = getattr(obj, '_delivery_success', 0)
        if total == 0:
            return '-'
        rate = int((success / total) * 100)
        color = '#28a745' if rate >= 90 else '#ffc107' if rate >= 70 else '#dc3545'
        return format_html(
            '<span style="color:{};">{}/{} ({}%)</span>',
            color, success, total, rate
        )
    delivery_stats.short_description = 'Delivery Success'


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(ModelAdmin):
    """Admin for webhook deliveries"""
    
    list_display = ['id', 'webhook', 'event', 'status_badge', 'status_code', 'attempts', 'created_at']
    list_filter = ['status', 'event', 'created_at']
    search_fields = ['webhook__url', 'event']
    readonly_fields = ['webhook', 'event', 'payload', 'status', 'status_code', 
                      'response_body', 'error_message', 'attempts', 'created_at', 'delivered_at']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'success': '#28a745',
            'failed': '#dc3545',
        }
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:3px; font-size:11px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False  # Deliveries are created automatically


# ============================================================================
# TEMPLATE RATING ADMIN - REMOVED (Deprecated Marketplace Feature)
# ============================================================================
# TemplateRating and RatingHelpful models have been removed as part of
# marketplace cleanup. These were only used for the template marketplace
# which is now an admin-only feature without public ratings.


# ============================================================================
# HUB EXPANSION: Sponsor & Prize Claim Admin
# ============================================================================

@admin.register(TournamentSponsor)
class TournamentSponsorAdmin(SafeUploadMixin, ModelAdmin):
    """Admin for managing tournament sponsors."""

    list_display = ['name', 'tournament', 'tier_badge', 'display_order', 'is_active', 'created_at']
    list_filter = ['tier', 'is_active', 'created_at']
    search_fields = ['name', 'tournament__name']
    list_editable = ['display_order', 'is_active']
    autocomplete_fields = ['tournament']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('tournament', 'name', 'tier', 'display_order', 'is_active'),
        }),
        ('Branding', {
            'fields': ('logo', 'banner_image', 'description'),
        }),
        ('Links', {
            'fields': ('website_url',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def tier_badge(self, obj):
        colors = {
            'title': '#FFD700',
            'gold': '#FFB800',
            'silver': '#C0C0C0',
            'bronze': '#CD7F32',
            'partner': '#00F0FF',
        }
        color = colors.get(obj.tier, '#9CA3AF')
        return format_html(
            '<span style="background:{}; color:#000; padding:3px 10px; '
            'border-radius:4px; font-size:11px; font-weight:700;">{}</span>',
            color, obj.get_tier_display()
        )
    tier_badge.short_description = 'Tier'


@admin.register(PrizeClaim)
class PrizeClaimAdmin(ModelAdmin):
    """Admin for managing prize claims."""

    list_display = ['id', 'claimed_by', 'prize_tournament', 'prize_placement',
                    'prize_amount', 'payout_method', 'status_badge', 'claimed_at']
    list_filter = ['status', 'payout_method', 'claimed_at']
    search_fields = ['claimed_by__username', 'prize_transaction__tournament__name']
    readonly_fields = ['prize_transaction', 'claimed_by', 'claimed_at', 'created_at', 'updated_at']
    autocomplete_fields = []

    fieldsets = (
        (None, {
            'fields': ('prize_transaction', 'claimed_by', 'status'),
        }),
        ('Payout Details', {
            'fields': ('payout_method', 'payout_destination', 'paid_at'),
        }),
        ('Admin', {
            'fields': ('admin_notes',),
        }),
        ('Timestamps', {
            'fields': ('claimed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def prize_tournament(self, obj):
        return obj.prize_transaction.tournament.name if obj.prize_transaction else '-'
    prize_tournament.short_description = 'Tournament'

    def prize_placement(self, obj):
        return obj.prize_transaction.get_placement_display() if obj.prize_transaction else '-'
    prize_placement.short_description = 'Placement'

    def prize_amount(self, obj):
        return f"{obj.prize_transaction.amount}" if obj.prize_transaction else '-'
    prize_amount.short_description = 'Amount'

    def status_badge(self, obj):
        colors = {
            'pending': '#FFB800',
            'processing': '#00F0FF',
            'paid': '#00FF66',
            'rejected': '#FF2A55',
        }
        color = colors.get(obj.status, '#9CA3AF')
        return format_html(
            '<span style="background:{}20; color:{}; padding:3px 10px; '
            'border:1px solid {}40; border-radius:4px; font-size:11px; font-weight:700;">{}</span>',
            color, color, color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

