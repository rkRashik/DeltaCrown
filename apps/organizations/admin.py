"""
Django Admin configuration for vNext Organizations and Teams.

COMPATIBILITY: vNext-only. Does NOT affect legacy team system.
QUERY OPTIMIZATION: Uses select_related and raw_id_fields to prevent N+1 queries.
"""

from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationRanking,
    Team,
    TeamMembership,
    TeamRanking,
    TeamActivityLog,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin interface for vNext Organizations."""
    
    list_display = ['name', 'slug', 'ceo_link', 'member_count', 'team_count', 'is_verified', 'created_at']
    search_fields = ['name', 'slug', 'ceo__username', 'ceo__email']
    list_filter = ['is_verified', 'created_at']
    raw_id_fields = ['ceo']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'member_count', 'team_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'ceo', 'description')
        }),
        ('Branding', {
            'fields': ('logo_url', 'banner_url', 'primary_color')
        }),
        ('Status', {
            'fields': ('is_verified', 'created_at', 'updated_at', 'member_count', 'team_count')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('ceo').annotate(
            _member_count=Count('staff_memberships'),
            _team_count=Count('teams', distinct=True)
        )
    
    def ceo_link(self, obj):
        """Display CEO with link to user admin."""
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.ceo.id, obj.ceo.username)
    ceo_link.short_description = 'CEO'
    ceo_link.admin_order_field = 'ceo__username'
    
    def member_count(self, obj):
        """Display active member count."""
        return obj._member_count if hasattr(obj, '_member_count') else obj.staff_memberships.count()
    member_count.short_description = 'Staff'
    
    def team_count(self, obj):
        """Display team count."""
        return obj._team_count if hasattr(obj, '_team_count') else obj.teams.count()
    team_count.short_description = 'Teams'


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    """Admin interface for Organization Memberships."""
    
    list_display = ['user_link', 'organization_link', 'role', 'joined_at']
    search_fields = ['user__username', 'user__email', 'organization__name']
    list_filter = ['role', 'joined_at']
    raw_id_fields = ['user', 'organization']
    ordering = ['-joined_at']
    readonly_fields = ['joined_at']
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('user', 'organization')
    
    def user_link(self, obj):
        """Display user with link to user admin."""
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def organization_link(self, obj):
        """Display organization with link to organization admin."""
        return format_html('<a href="/admin/organizations/organization/{}/change/">{}</a>', obj.organization.id, obj.organization.name)
    organization_link.short_description = 'Organization'
    organization_link.admin_order_field = 'organization__name'


@admin.register(OrganizationRanking)
class OrganizationRankingAdmin(admin.ModelAdmin):
    """Admin interface for Organization Rankings."""
    
    list_display = ['organization_link', 'empire_score', 'global_rank', 'total_trophies', 'last_calculated']
    search_fields = ['organization__name']
    list_filter = ['last_calculated']
    raw_id_fields = ['organization']
    ordering = ['-empire_score']
    readonly_fields = ['last_calculated']
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('organization')
    
    def organization_link(self, obj):
        """Display organization with link."""
        return format_html('<a href="/admin/organizations/organization/{}/change/">{}</a>', obj.organization.id, obj.organization.name)
    organization_link.short_description = 'Organization'
    organization_link.admin_order_field = 'organization__name'


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Admin interface for vNext Teams."""
    
    list_display = ['name', 'slug', 'game_id', 'region', 'owner_link', 'organization_link', 'status', 'created_at']
    search_fields = ['name', 'slug', 'owner__username', 'organization__name']
    list_filter = ['region', 'status', 'created_at']
    raw_id_fields = ['owner', 'organization']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'owner', 'organization', 'game_id', 'region', 'description')
        }),
        ('Branding', {
            'fields': ('logo', 'banner')
        }),
        ('Tournament Operations', {
            'fields': ('preferred_server', 'emergency_contact_discord', 'emergency_contact_phone'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('status', 'is_temporary', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('owner', 'organization')
    
    def owner_link(self, obj):
        """Display owner with link to user admin."""
        if obj.owner:
            return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.owner.id, obj.owner.username)
        return '-'
    owner_link.short_description = 'Owner'
    owner_link.admin_order_field = 'owner__username'
    
    def organization_link(self, obj):
        """Display organization with link (if exists)."""
        if obj.organization:
            return format_html('<a href="/admin/organizations/organization/{}/change/">{}</a>', obj.organization.id, obj.organization.name)
        return '-'
    organization_link.short_description = 'Organization'
    organization_link.admin_order_field = 'organization__name'


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    """Admin interface for Team Memberships."""
    
    list_display = ['user_link', 'team_link', 'role', 'status', 'roster_slot', 'is_tournament_captain', 'joined_at']
    search_fields = ['user__username', 'user__email', 'team__name']
    list_filter = ['role', 'status', 'roster_slot', 'is_tournament_captain', 'joined_at']
    raw_id_fields = ['user', 'team']
    ordering = ['-joined_at']
    readonly_fields = ['joined_at', 'left_at']
    
    fieldsets = (
        ('Membership', {
            'fields': ('team', 'user', 'status')
        }),
        ('Roles', {
            'fields': ('role', 'roster_slot', 'player_role', 'is_tournament_captain')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'left_at', 'left_reason')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('user', 'team')
    
    def user_link(self, obj):
        """Display user with link to user admin."""
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def team_link(self, obj):
        """Display team with link to team admin."""
        return format_html('<a href="/admin/organizations/team/{}/change/">{}</a>', obj.team.id, obj.team.name)
    team_link.short_description = 'Team'
    team_link.admin_order_field = 'team__name'


@admin.register(TeamActivityLog)
class TeamActivityLogAdmin(admin.ModelAdmin):
    """
    Read-only admin interface for Team Activity Logs.
    
    IMPORTANT: This is a log-only model. No add/change/delete allowed.
    """
    
    list_display = ['team_link', 'action_type', 'actor_username', 'timestamp', 'metadata_preview']
    search_fields = ['team__name', 'actor_username']
    list_filter = ['action_type', 'timestamp']
    raw_id_fields = ['team']
    ordering = ['-timestamp']
    readonly_fields = ['team', 'actor_id', 'actor_username', 'action_type', 'description', 'metadata', 'timestamp']
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('team')
    
    def team_link(self, obj):
        """Display team with link to team admin."""
        return format_html('<a href="/admin/organizations/team/{}/change/">{}</a>', obj.team.id, obj.team.name)
    team_link.short_description = 'Team'
    team_link.admin_order_field = 'team__name'
    
    def metadata_preview(self, obj):
        """Display truncated metadata."""
        if obj.metadata:
            preview = str(obj.metadata)[:50]
            return preview + '...' if len(str(obj.metadata)) > 50 else preview
        return '-'
    metadata_preview.short_description = 'Metadata'
    
    # Read-only: No add/change/delete permissions
    def has_add_permission(self, request):
        """Disable adding activity logs manually."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing activity logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting activity logs."""
        return False


# ============================================================================
# CUSTOM FILTERS FOR TEAMRANKING
# ============================================================================

class CPRangeFilter(admin.SimpleListFilter):
    """Custom filter for Crown Points ranges."""
    title = 'CP Range'
    parameter_name = 'cp_range'
    
    def lookups(self, request, model_admin):
        """Define CP range options."""
        return (
            ('0-500', '0-500 (Unranked/Bronze)'),
            ('500-1500', '500-1500 (Silver)'),
            ('1500-5000', '1500-5000 (Gold)'),
            ('5000-15000', '5000-15000 (Platinum)'),
            ('15000-40000', '15000-40000 (Diamond)'),
            ('40000-80000', '40000-80000 (Ascendant)'),
            ('80000+', '80000+ (Crown)'),
        )
    
    def queryset(self, request, queryset):
        """Filter queryset by selected CP range."""
        if self.value() == '0-500':
            return queryset.filter(current_cp__gte=0, current_cp__lt=500)
        elif self.value() == '500-1500':
            return queryset.filter(current_cp__gte=500, current_cp__lt=1500)
        elif self.value() == '1500-5000':
            return queryset.filter(current_cp__gte=1500, current_cp__lt=5000)
        elif self.value() == '5000-15000':
            return queryset.filter(current_cp__gte=5000, current_cp__lt=15000)
        elif self.value() == '15000-40000':
            return queryset.filter(current_cp__gte=15000, current_cp__lt=40000)
        elif self.value() == '40000-80000':
            return queryset.filter(current_cp__gte=40000, current_cp__lt=80000)
        elif self.value() == '80000+':
            return queryset.filter(current_cp__gte=80000)
        return queryset


@admin.register(TeamRanking)
class TeamRankingAdmin(admin.ModelAdmin):
    """
    Admin interface for vNext Team Rankings (DCRS).
    
    Enhanced with filters for tier, hot streaks, games, and regions.
    """
    
    list_display = [
        'team_link',
        'current_cp_display',
        'tier',
        'hot_streak_display',
        'game_id_display',
        'region_display',
        'last_activity_date',
        'global_rank'
    ]
    search_fields = ['team__name', 'team__slug']
    list_filter = [
        'tier',
        'is_hot_streak',
        CPRangeFilter,
        'team__game_id',
        'team__region',
        'team__status',
        'last_activity_date'
    ]
    raw_id_fields = ['team']
    ordering = ['-current_cp']
    readonly_fields = [
        'current_cp',
        'season_cp',
        'all_time_cp',
        'tier',
        'is_hot_streak',
        'streak_count',
        'global_rank',
        'regional_rank',
        'rank_change_24h',
        'rank_change_7d',
        'last_activity_date',
        'last_decay_applied'
    ]
    
    fieldsets = (
        ('Team', {
            'fields': ('team',)
        }),
        ('Crown Points', {
            'fields': ('current_cp', 'season_cp', 'all_time_cp', 'tier')
        }),
        ('Streaks', {
            'fields': ('is_hot_streak', 'streak_count')
        }),
        ('Rankings', {
            'fields': ('global_rank', 'regional_rank', 'rank_change_24h', 'rank_change_7d')
        }),
        ('Activity', {
            'fields': ('last_activity_date', 'last_decay_applied')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('team')
    
    def team_link(self, obj):
        """Display team with link to team admin."""
        return format_html(
            '<a href="/admin/organizations/team/{}/change/">{}</a>',
            obj.team.id,
            obj.team.name
        )
    team_link.short_description = 'Team'
    team_link.admin_order_field = 'team__name'
    
    def current_cp_display(self, obj):
        """Display CP with colored background based on tier."""
        colors = {
            'CROWN': '#FFD700',
            'ASCENDANT': '#E74C3C',
            'DIAMOND': '#3498DB',
            'PLATINUM': '#1ABC9C',
            'GOLD': '#F39C12',
            'SILVER': '#95A5A6',
            'BRONZE': '#CD7F32',
            'UNRANKED': '#7F8C8D'
        }
        color = colors.get(obj.tier, '#7F8C8D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{} CP</span>',
            color,
            obj.current_cp
        )
    current_cp_display.short_description = 'Crown Points'
    current_cp_display.admin_order_field = 'current_cp'
    
    def hot_streak_display(self, obj):
        """Display hot streak with emoji."""
        if obj.is_hot_streak:
            return format_html('🔥 {} wins', obj.streak_count)
        return '-'
    hot_streak_display.short_description = 'Hot Streak'
    hot_streak_display.admin_order_field = 'is_hot_streak'
    
    def game_id_display(self, obj):
        """Display game ID from related team."""
        return obj.team.game_id if obj.team else '-'
    game_id_display.short_description = 'Game'
    game_id_display.admin_order_field = 'team__game_id'
    
    def region_display(self, obj):
        """Display region from related team."""
        return obj.team.region if obj.team else '-'
    region_display.short_description = 'Region'
    region_display.admin_order_field = 'team__region'


