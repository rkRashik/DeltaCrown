"""
Django Admin Configuration for Tournament Models

This module provides comprehensive admin interfaces for all tournament-related models
including the 6 new Phase 1 models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Tournament,
    TournamentSchedule,
    TournamentCapacity,
    TournamentFinance,
    TournamentMedia,
    TournamentRules,
    TournamentArchive
)


# ============================================================================
# INLINE ADMIN CLASSES
# ============================================================================

class TournamentScheduleInline(admin.StackedInline):
    """Inline editor for Tournament Schedule"""
    model = TournamentSchedule
    can_delete = False
    verbose_name = "Schedule"
    verbose_name_plural = "Schedule"
    
    fieldsets = (
        ('Registration Period', {
            'fields': (
                ('registration_start', 'registration_end'),
                'early_bird_deadline',
            )
        }),
        ('Check-in & Tournament Dates', {
            'fields': (
                ('checkin_start', 'checkin_end'),
                ('tournament_start', 'tournament_end'),
            )
        }),
        ('Timezone & Settings', {
            'fields': (
                'timezone',
                ('auto_close_registration', 'auto_start_checkin'),
            )
        }),
    )


class TournamentCapacityInline(admin.StackedInline):
    """Inline editor for Tournament Capacity"""
    model = TournamentCapacity
    can_delete = False
    verbose_name = "Capacity & Limits"
    verbose_name_plural = "Capacity & Limits"
    
    fieldsets = (
        ('Team Capacity', {
            'fields': (
                ('min_teams', 'max_teams', 'current_teams'),
                ('min_players_per_team', 'max_players_per_team'),
            )
        }),
        ('Waitlist', {
            'fields': (
                ('enable_waitlist', 'waitlist_capacity', 'current_waitlist'),
            )
        }),
        ('Status', {
            'fields': (
                'capacity_status',
                ('is_full', 'waitlist_full'),
            )
        }),
    )
    
    readonly_fields = ('current_teams', 'current_waitlist', 'is_full', 'waitlist_full')


class TournamentFinanceInline(admin.StackedInline):
    """Inline editor for Tournament Finance"""
    model = TournamentFinance
    can_delete = False
    verbose_name = "Finance & Prizes"
    verbose_name_plural = "Finance & Prizes"
    
    fieldsets = (
        ('Entry Fees', {
            'fields': (
                ('entry_fee', 'currency'),
                ('early_bird_fee', 'late_registration_fee'),
            )
        }),
        ('Prize Pool', {
            'fields': (
                ('prize_pool', 'prize_currency'),
                'prize_distribution',
            )
        }),
        ('Revenue Tracking', {
            'fields': (
                ('total_revenue', 'total_paid_out'),
            )
        }),
    )
    
    readonly_fields = ('total_revenue', 'total_paid_out')


class TournamentMediaInline(admin.StackedInline):
    """Inline editor for Tournament Media"""
    model = TournamentMedia
    can_delete = False
    verbose_name = "Media & Assets"
    verbose_name_plural = "Media & Assets"
    
    fieldsets = (
        ('Images', {
            'fields': (
                ('logo', 'logo_alt_text'),
                ('banner', 'banner_alt_text'),
                ('thumbnail', 'thumbnail_alt_text'),
            )
        }),
        ('Display Settings', {
            'fields': (
                ('show_logo_on_card', 'show_logo_on_detail'),
                ('show_banner_on_card', 'show_banner_on_detail'),
            )
        }),
        ('Streaming', {
            'fields': (
                'stream_url',
                'stream_embed_code',
            )
        }),
    )


class TournamentRulesInline(admin.StackedInline):
    """Inline editor for Tournament Rules"""
    model = TournamentRules
    can_delete = False
    verbose_name = "Rules & Requirements"
    verbose_name_plural = "Rules & Requirements"
    
    fieldsets = (
        ('Rule Sections', {
            'fields': (
                'general_rules',
                'eligibility_requirements',
                'match_rules',
                'scoring_system',
                'penalty_rules',
                'prize_distribution_rules',
                'checkin_instructions',
                'additional_notes',
            ),
            'classes': ('collapse',),
        }),
        ('Requirements', {
            'fields': (
                ('require_discord', 'require_game_id', 'require_team_logo'),
            )
        }),
        ('Restrictions', {
            'fields': (
                ('min_age', 'max_age'),
                'region_restriction',
                'rank_restriction',
            )
        }),
    )


class TournamentArchiveInline(admin.StackedInline):
    """Inline editor for Tournament Archive"""
    model = TournamentArchive
    can_delete = False
    verbose_name = "Archive Settings"
    verbose_name_plural = "Archive Settings"
    
    fieldsets = (
        ('Archive Status', {
            'fields': (
                ('archive_type', 'is_archived'),
                'archived_at',
                'archive_reason',
            )
        }),
        ('Clone Information', {
            'fields': (
                'source_tournament',
                ('clone_number', 'cloned_at'),
            ),
            'classes': ('collapse',),
        }),
        ('Preservation Settings', {
            'fields': (
                ('preserve_participants', 'preserve_matches', 'preserve_media'),
            )
        }),
    )
    
    readonly_fields = ('archived_at', 'cloned_at')


# ============================================================================
# MODEL ADMIN CLASSES
# ============================================================================

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """Main Tournament Admin with all inline editors"""
    
    list_display = (
        'name',
        'game',
        'status',
        'tournament_type',
        'get_capacity_status',
        'get_registration_status',
        'created_at',
    )
    
    list_filter = (
        'status',
        'tournament_type',
        'game',
        'created_at',
    )
    
    search_fields = (
        'name',
        'description',
        'game__name',
    )
    
    readonly_fields = (
        'created_at',
        'updated_at',
        'slug',
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'slug',
                'game',
                'description',
            )
        }),
        ('Tournament Settings', {
            'fields': (
                ('tournament_type', 'status'),
                ('format', 'platform'),
            )
        }),
        ('Organizer', {
            'fields': (
                'organizer',
            )
        }),
        ('Timestamps', {
            'fields': (
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [
        TournamentScheduleInline,
        TournamentCapacityInline,
        TournamentFinanceInline,
        TournamentMediaInline,
        TournamentRulesInline,
        TournamentArchiveInline,
    ]
    
    def get_capacity_status(self, obj):
        """Display capacity status with color coding"""
        if hasattr(obj, 'capacity'):
            status = obj.capacity.capacity_status
            colors = {
                'AVAILABLE': 'green',
                'FILLING': 'orange',
                'FULL': 'red',
                'WAITLIST': 'purple',
            }
            color = colors.get(status, 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                status
            )
        return '-'
    get_capacity_status.short_description = 'Capacity'
    
    def get_registration_status(self, obj):
        """Display registration status"""
        if hasattr(obj, 'schedule'):
            if obj.schedule.is_registration_open():
                return format_html('<span style="color: green;">✓ Open</span>')
            elif obj.schedule.is_registration_upcoming():
                return format_html('<span style="color: orange;">⏳ Upcoming</span>')
            else:
                return format_html('<span style="color: red;">✗ Closed</span>')
        return '-'
    get_registration_status.short_description = 'Registration'


@admin.register(TournamentSchedule)
class TournamentScheduleAdmin(admin.ModelAdmin):
    """Standalone admin for Tournament Schedule"""
    
    list_display = (
        'tournament',
        'registration_start',
        'registration_end',
        'tournament_start',
        'tournament_end',
        'get_status',
    )
    
    list_filter = (
        'auto_close_registration',
        'auto_start_checkin',
        'timezone',
    )
    
    search_fields = (
        'tournament__name',
    )
    
    date_hierarchy = 'tournament_start'
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament',)
        }),
        ('Registration Period', {
            'fields': (
                ('registration_start', 'registration_end'),
                'early_bird_deadline',
            )
        }),
        ('Check-in Period', {
            'fields': (
                ('checkin_start', 'checkin_end'),
            )
        }),
        ('Tournament Period', {
            'fields': (
                ('tournament_start', 'tournament_end'),
            )
        }),
        ('Settings', {
            'fields': (
                'timezone',
                ('auto_close_registration', 'auto_start_checkin'),
            )
        }),
    )
    
    def get_status(self, obj):
        """Display current schedule status"""
        if obj.is_registration_open():
            return format_html('<span style="color: green;">Registration Open</span>')
        elif obj.is_checkin_open():
            return format_html('<span style="color: blue;">Check-in Open</span>')
        elif obj.is_in_progress():
            return format_html('<span style="color: orange;">In Progress</span>')
        elif obj.has_ended():
            return format_html('<span style="color: gray;">Ended</span>')
        else:
            return format_html('<span style="color: purple;">Upcoming</span>')
    get_status.short_description = 'Status'


@admin.register(TournamentCapacity)
class TournamentCapacityAdmin(admin.ModelAdmin):
    """Standalone admin for Tournament Capacity"""
    
    list_display = (
        'tournament',
        'current_teams',
        'max_teams',
        'capacity_status',
        'get_fill_percentage',
        'is_full',
    )
    
    list_filter = (
        'capacity_status',
        'is_full',
        'enable_waitlist',
    )
    
    search_fields = (
        'tournament__name',
    )
    
    readonly_fields = (
        'current_teams',
        'current_waitlist',
        'is_full',
        'waitlist_full',
    )
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament',)
        }),
        ('Team Capacity', {
            'fields': (
                ('min_teams', 'max_teams', 'current_teams'),
                ('min_players_per_team', 'max_players_per_team'),
            )
        }),
        ('Waitlist', {
            'fields': (
                ('enable_waitlist', 'waitlist_capacity', 'current_waitlist'),
            )
        }),
        ('Status', {
            'fields': (
                'capacity_status',
                ('is_full', 'waitlist_full'),
            )
        }),
    )
    
    def get_fill_percentage(self, obj):
        """Display capacity fill percentage"""
        percentage = obj.get_fill_percentage()
        if percentage >= 90:
            color = 'red'
        elif percentage >= 70:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            percentage
        )
    get_fill_percentage.short_description = 'Fill %'


@admin.register(TournamentFinance)
class TournamentFinanceAdmin(admin.ModelAdmin):
    """Standalone admin for Tournament Finance"""
    
    list_display = (
        'tournament',
        'get_entry_fee_display',
        'get_prize_pool_display',
        'get_total_revenue_display',
        'get_profit_display',
    )
    
    list_filter = (
        'currency',
        'prize_currency',
    )
    
    search_fields = (
        'tournament__name',
    )
    
    readonly_fields = (
        'total_revenue',
        'total_paid_out',
    )
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament',)
        }),
        ('Entry Fees', {
            'fields': (
                ('entry_fee', 'currency'),
                ('early_bird_fee', 'late_registration_fee'),
            )
        }),
        ('Prize Pool', {
            'fields': (
                ('prize_pool', 'prize_currency'),
                'prize_distribution',
            )
        }),
        ('Financial Summary', {
            'fields': (
                ('total_revenue', 'total_paid_out'),
            )
        }),
    )
    
    def get_entry_fee_display(self, obj):
        """Display formatted entry fee"""
        fee = obj.get_formatted_entry_fee()
        return format_html('<strong>{}</strong>', fee)
    get_entry_fee_display.short_description = 'Entry Fee'
    
    def get_prize_pool_display(self, obj):
        """Display formatted prize pool"""
        pool = obj.get_formatted_prize_pool()
        return format_html('<strong style="color: green;">{}</strong>', pool)
    get_prize_pool_display.short_description = 'Prize Pool'
    
    def get_total_revenue_display(self, obj):
        """Display formatted total revenue"""
        revenue = obj.get_formatted_total_revenue()
        return format_html('<span style="color: blue;">{}</span>', revenue)
    get_total_revenue_display.short_description = 'Revenue'
    
    def get_profit_display(self, obj):
        """Display profit/loss"""
        profit = obj.calculate_profit()
        color = 'green' if profit >= 0 else 'red'
        symbol = obj.currency
        return format_html(
            '<span style="color: {};">{} {:.2f}</span>',
            color,
            symbol,
            profit
        )
    get_profit_display.short_description = 'Profit/Loss'


@admin.register(TournamentMedia)
class TournamentMediaAdmin(admin.ModelAdmin):
    """Standalone admin for Tournament Media"""
    
    list_display = (
        'tournament',
        'get_logo_preview',
        'get_banner_preview',
        'has_stream',
    )
    
    list_filter = (
        'show_logo_on_card',
        'show_banner_on_card',
    )
    
    search_fields = (
        'tournament__name',
    )
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament',)
        }),
        ('Logo', {
            'fields': (
                ('logo', 'logo_alt_text'),
                ('show_logo_on_card', 'show_logo_on_detail'),
            )
        }),
        ('Banner', {
            'fields': (
                ('banner', 'banner_alt_text'),
                ('show_banner_on_card', 'show_banner_on_detail'),
            )
        }),
        ('Thumbnail', {
            'fields': (
                ('thumbnail', 'thumbnail_alt_text'),
            )
        }),
        ('Streaming', {
            'fields': (
                'stream_url',
                'stream_embed_code',
            )
        }),
    )
    
    def get_logo_preview(self, obj):
        """Display logo preview thumbnail"""
        if obj.logo:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.logo.url
            )
        return '-'
    get_logo_preview.short_description = 'Logo'
    
    def get_banner_preview(self, obj):
        """Display banner preview thumbnail"""
        if obj.banner:
            return format_html(
                '<img src="{}" width="100" height="50" style="object-fit: cover;" />',
                obj.banner.url
            )
        return '-'
    get_banner_preview.short_description = 'Banner'
    
    def has_stream(self, obj):
        """Check if streaming is configured"""
        if obj.stream_url:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: gray;">✗ No</span>')
    has_stream.short_description = 'Streaming'


@admin.register(TournamentRules)
class TournamentRulesAdmin(admin.ModelAdmin):
    """Standalone admin for Tournament Rules"""
    
    list_display = (
        'tournament',
        'get_requirements',
        'get_restrictions',
        'has_rules',
    )
    
    list_filter = (
        'require_discord',
        'require_game_id',
        'require_team_logo',
    )
    
    search_fields = (
        'tournament__name',
        'general_rules',
    )
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament',)
        }),
        ('General Rules', {
            'fields': (
                'general_rules',
                'additional_notes',
            )
        }),
        ('Eligibility', {
            'fields': (
                'eligibility_requirements',
            )
        }),
        ('Match & Scoring', {
            'fields': (
                'match_rules',
                'scoring_system',
            )
        }),
        ('Penalties & Prizes', {
            'fields': (
                'penalty_rules',
                'prize_distribution_rules',
            )
        }),
        ('Check-in', {
            'fields': (
                'checkin_instructions',
            )
        }),
        ('Requirements', {
            'fields': (
                ('require_discord', 'require_game_id', 'require_team_logo'),
            )
        }),
        ('Restrictions', {
            'fields': (
                ('min_age', 'max_age'),
                'region_restriction',
                'rank_restriction',
            )
        }),
    )
    
    def get_requirements(self, obj):
        """Display active requirements"""
        reqs = []
        if obj.require_discord:
            reqs.append('Discord')
        if obj.require_game_id:
            reqs.append('Game ID')
        if obj.require_team_logo:
            reqs.append('Logo')
        
        if reqs:
            return format_html('<span style="color: blue;">{}</span>', ', '.join(reqs))
        return '-'
    get_requirements.short_description = 'Requirements'
    
    def get_restrictions(self, obj):
        """Display active restrictions"""
        restrictions = []
        if obj.min_age or obj.max_age:
            age_text = f"{obj.min_age or '?'}-{obj.max_age or '?'}"
            restrictions.append(f"Age: {age_text}")
        if obj.region_restriction:
            restrictions.append(f"Region: {obj.region_restriction}")
        if obj.rank_restriction:
            restrictions.append(f"Rank: {obj.rank_restriction}")
        
        if restrictions:
            return format_html('<span style="color: orange;">{}</span>', ', '.join(restrictions))
        return '-'
    get_restrictions.short_description = 'Restrictions'
    
    def has_rules(self, obj):
        """Check if rules are defined"""
        if obj.general_rules or obj.match_rules:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: gray;">✗ No</span>')
    has_rules.short_description = 'Rules Defined'


@admin.register(TournamentArchive)
class TournamentArchiveAdmin(admin.ModelAdmin):
    """Standalone admin for Tournament Archive"""
    
    list_display = (
        'tournament',
        'archive_type',
        'is_archived',
        'get_clone_info',
        'archived_at',
    )
    
    list_filter = (
        'archive_type',
        'is_archived',
        'can_restore',
        'preserve_participants',
    )
    
    search_fields = (
        'tournament__name',
        'archive_reason',
        'notes',
    )
    
    readonly_fields = (
        'archived_at',
        'cloned_at',
        'restored_at',
    )
    
    date_hierarchy = 'archived_at'
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament',)
        }),
        ('Archive Status', {
            'fields': (
                ('archive_type', 'is_archived'),
                'archived_at',
                'archived_by',
                'archive_reason',
            )
        }),
        ('Clone Information', {
            'fields': (
                'source_tournament',
                ('clone_number', 'cloned_at'),
                'cloned_by',
            ),
            'classes': ('collapse',),
        }),
        ('Restore Settings', {
            'fields': (
                'can_restore',
                ('restored_at', 'restored_by'),
            )
        }),
        ('Preservation Settings', {
            'fields': (
                ('preserve_participants', 'preserve_matches', 'preserve_media'),
            )
        }),
        ('Additional Information', {
            'fields': (
                'original_data',
                'notes',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def get_clone_info(self, obj):
        """Display clone information"""
        if obj.source_tournament:
            return format_html(
                '<span style="color: purple;">Clone #{} of {}</span>',
                obj.clone_number,
                obj.source_tournament.name
            )
        elif obj.clone_number > 0:
            return format_html(
                '<span style="color: green;">Original (cloned {} times)</span>',
                obj.clone_number
            )
        return '-'
    get_clone_info.short_description = 'Clone Info'
