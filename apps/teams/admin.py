"""
Teams App - Django Admin Configuration

Provides comprehensive admin interface for managing teams, members, invitations,
sponsorships, and all team-related content.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.contrib import messages

from .models import (
    Team, TeamMembership, TeamInvite,
    TeamAchievement, TeamSponsor, TeamMerchItem, TeamPromotion,
    TeamDiscussionPost, TeamDiscussionComment,
    TeamChatMessage, TeamAnalytics, LegacyTeamStats,
    TeamRankingHistory, TeamRankingBreakdown, TeamRankingSettings,
    TeamTournamentRegistration, MatchRecord, MatchParticipation
)


# ============================================================================
# INLINE ADMINS
# ============================================================================

class TeamMembershipInline(admin.TabularInline):
    """Inline display of team members"""
    model = TeamMembership
    extra = 0
    fields = ['profile', 'role', 'player_role', 'status', 'joined_at']
    readonly_fields = ['joined_at']
    can_delete = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('profile__user')
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """
        Dynamically populate player_role choices based on team's game.
        """
        if db_field.name == "player_role":
            # Get the team from the request (if editing existing team)
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                try:
                    from .models import Team
                    from .dual_role_system import get_player_roles_for_game
                    team = Team.objects.get(pk=obj_id)
                    if team.game:
                        roles = get_player_roles_for_game(team.game)
                        kwargs['choices'] = [('', '---')] + [(r['value'], r['label']) for r in roles]
                except:
                    pass
        return super().formfield_for_choice_field(db_field, request, **kwargs)


class TeamInviteInline(admin.TabularInline):
    """Inline display of team invitations"""
    model = TeamInvite
    extra = 0
    fields = ['invited_user', 'invited_email', 'role', 'status', 'expires_at']
    readonly_fields = ['token', 'created_at']
    can_delete = True


class TeamAchievementInline(admin.StackedInline):
    """Inline display of team achievements"""
    model = TeamAchievement
    extra = 0
    # Removed 'tournament' field (legacy app removed - November 2, 2025)
    # Will be re-added when new Tournament Engine is built
    fields = ['title', 'placement', 'year', 'notes', 'created_at']
    readonly_fields = ['created_at']
    can_delete = True
    
    def get_exclude(self, request, obj=None):
        # Exclude tournament field since tournament app is removed
        return ['tournament']


# ============================================================================
# MAIN MODEL ADMINS
# ============================================================================

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Comprehensive team management"""
    
    list_display = [
        'name', 'tag', 'game_badge', 'captain_link', 
        'member_count', 'created_at', 'verification_status', 'featured_badge'
    ]
    list_filter = [
        'game', 'is_verified', 'is_featured', 
        'allow_posts', 'created_at'
    ]
    search_fields = ['name', 'tag', 'description', 'captain__user__username']
    readonly_fields = [
        'slug', 'created_at', 'updated_at', 'followers_count', 
        'posts_count', 'logo_preview', 'banner_preview'
    ]
    
    # Temporarily disabled TeamAchievementInline (November 2, 2025)
    # Re-enable when new Tournament Engine is built
    inlines = [TeamMembershipInline, TeamInviteInline]  # TeamAchievementInline removed
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'tag', 'slug', 'game', 'description', 'captain')
        }),
        ('Media', {
            'fields': ('logo', 'logo_preview', 'banner_image', 'banner_preview', 'roster_image')
        }),
        ('Location', {
            'fields': ('region',),
            'classes': ('collapse',)
        }),
        ('Social Links', {
            'fields': ('twitter', 'instagram', 'discord', 'youtube', 'twitch', 'linktree'),
            'classes': ('collapse',)
        }),
        ('Status & Verification', {
            'fields': ('is_verified', 'is_featured')
        }),
        ('Statistics', {
            'fields': ('followers_count', 'posts_count', 'total_points', 'adjust_points'),
            'classes': ('collapse',)
        }),
        ('Team Settings', {
            'fields': (
                'is_active', 'is_public', 'allow_posts', 'allow_followers', 
                'posts_require_approval', 'allow_join_requests', 'show_statistics'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'verify_teams', 'unverify_teams', 'feature_teams', 'unfeature_teams',
        'approve_logos', 'export_teams'
    ]
    
    def game_badge(self, obj):
        """Display game with color badge"""
        colors = {
            'efootball': '#00A859',
            'valorant': '#FF4655',
        }
        color = colors.get(obj.game, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_game_display() if obj.game else 'No Game'
        )
    game_badge.short_description = 'Game'
    
    def captain_link(self, obj):
        """Link to captain's user profile"""
        if obj.captain:
            url = reverse('admin:user_profile_userprofile_change', args=[obj.captain.pk])
            return format_html('<a href="{}">{}</a>', url, obj.captain)
        return '—'
    captain_link.short_description = 'Captain'
    
    def member_count(self, obj):
        """Display active member count"""
        count = obj.memberships.filter(status='active').count()
        return format_html('<strong>{}</strong>', count)
    member_count.short_description = 'Members'
    member_count.admin_order_field = 'member_count'
    
    def verification_status(self, obj):
        """Display verification status with icon"""
        if obj.is_verified:
            return format_html('✅ Verified')
        return format_html('⏳ Unverified')
    verification_status.short_description = 'Status'
    
    def featured_badge(self, obj):
        """Display featured badge"""
        if obj.is_featured:
            return format_html('⭐')
        return ''
    featured_badge.short_description = '⭐'
    
    def logo_preview(self, obj):
        """Display logo preview"""
        if obj.logo:
            return format_html('<img src="{}" width="100" height="100" />', obj.logo.url)
        return '—'
    logo_preview.short_description = 'Logo Preview'
    
    def banner_preview(self, obj):
        """Display banner preview"""
        if obj.banner_image:
            return format_html('<img src="{}" width="300" height="100" />', obj.banner_image.url)
        return '—'
    banner_preview.short_description = 'Banner Preview'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('captain__user')
        qs = qs.annotate(member_count=Count('memberships', filter=Q(memberships__status='active')))
        return qs
    
    # Actions
    def verify_teams(self, request, queryset):
        count = queryset.update(is_verified=True, verification_status='approved')
        self.message_user(request, f'{count} team(s) verified successfully.', messages.SUCCESS)
    verify_teams.short_description = "✅ Verify selected teams"
    
    def unverify_teams(self, request, queryset):
        count = queryset.update(is_verified=False, verification_status='pending')
        self.message_user(request, f'{count} team(s) unverified.', messages.INFO)
    unverify_teams.short_description = "❌ Remove verification"
    
    def feature_teams(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f'{count} team(s) featured.', messages.SUCCESS)
    feature_teams.short_description = "⭐ Feature selected teams"
    
    def unfeature_teams(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, f'{count} team(s) unfeatured.', messages.INFO)
    unfeature_teams.short_description = "Remove from featured"
    
    def approve_logos(self, request, queryset):
        # Custom logo approval logic
        self.message_user(
            request, 
            'Logo approval: Verify logos manually and use "Verify teams" action.',
            messages.INFO
        )
    approve_logos.short_description = "🖼️ Review team logos"
    
    def export_teams(self, request, queryset):
        # Export functionality would go here
        self.message_user(request, 'Export functionality: Implement CSV/Excel export.', messages.INFO)
    export_teams.short_description = "📊 Export selected teams"


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    """Team membership management"""
    
    list_display = ['team_link', 'profile_link', 'role_badge', 'status_badge', 'joined_at']
    list_filter = ['role', 'status', 'joined_at']
    search_fields = ['team__name', 'profile__user__username', 'profile__display_name']
    readonly_fields = ['joined_at']
    
    fieldsets = (
        ('Membership Details', {
            'fields': ('team', 'profile', 'role', 'status')
        }),
        ('Timestamps', {
            'fields': ('joined_at',)
        }),
    )
    
    def team_link(self, obj):
        url = reverse('admin:teams_team_change', args=[obj.team.pk])
        return format_html('<a href="{}">{}</a>', url, obj.team.name)
    team_link.short_description = 'Team'
    
    def profile_link(self, obj):
        url = reverse('admin:user_profile_userprofile_change', args=[obj.profile.pk])
        return format_html('<a href="{}">{}</a>', url, obj.profile)
    profile_link.short_description = 'Profile'
    
    def role_badge(self, obj):
        colors = {
            'captain': '#FFD700',
            'player': '#4CAF50',
            'substitute': '#9E9E9E',
        }
        color = colors.get(obj.role, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    def status_badge(self, obj):
        colors = {
            'active': '#4CAF50',
            'inactive': '#9E9E9E',
            'pending': '#FF9800',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('team', 'profile__user')


@admin.register(TeamInvite)
class TeamInviteAdmin(admin.ModelAdmin):
    """Team invitation management"""
    
    list_display = [
        'team_link', 'invited_display', 'role_badge', 
        'status_badge', 'expires_at', 'created_at'
    ]
    list_filter = ['status', 'role', 'expires_at', 'created_at']
    search_fields = [
        'team__name', 'invited_email', 
        'invited_user__user__username', 'inviter__user__username'
    ]
    readonly_fields = ['token', 'created_at', 'invite_link']
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('team', 'invited_user', 'invited_email', 'inviter', 'role')
        }),
        ('Status', {
            'fields': ('status', 'expires_at')
        }),
        ('Technical', {
            'fields': ('token', 'invite_link', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_invites', 'reject_invites', 'resend_invites']
    
    def team_link(self, obj):
        url = reverse('admin:teams_team_change', args=[obj.team.pk])
        return format_html('<a href="{}">{}</a>', url, obj.team.name)
    team_link.short_description = 'Team'
    
    def invited_display(self, obj):
        if obj.invited_user:
            url = reverse('admin:user_profile_userprofile_change', args=[obj.invited_user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.invited_user)
        return obj.invited_email or '—'
    invited_display.short_description = 'Invited'
    
    def role_badge(self, obj):
        colors = {'captain': '#FFD700', 'player': '#4CAF50', 'substitute': '#9E9E9E'}
        color = colors.get(obj.role, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FF9800',
            'accepted': '#4CAF50',
            'declined': '#F44336',
            'expired': '#9E9E9E',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def invite_link(self, obj):
        """Display invite link"""
        if obj.token:
            # URL would be constructed based on your URL patterns
            link = f"/teams/invite/{obj.token}/"
            return format_html('<a href="{}" target="_blank">{}</a>', link, link)
        return '—'
    invite_link.short_description = 'Invite Link'
    
    def approve_invites(self, request, queryset):
        count = queryset.filter(status='pending').update(status='accepted')
        self.message_user(request, f'{count} invite(s) approved.', messages.SUCCESS)
    approve_invites.short_description = "✅ Approve selected invites"
    
    def reject_invites(self, request, queryset):
        count = queryset.filter(status='pending').update(status='declined')
        self.message_user(request, f'{count} invite(s) rejected.', messages.INFO)
    reject_invites.short_description = "❌ Reject selected invites"
    
    def resend_invites(self, request, queryset):
        self.message_user(
            request, 
            'Resend functionality: Implement email resending via notification service.',
            messages.INFO
        )
    resend_invites.short_description = "📧 Resend invitation emails"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('team', 'invited_user', 'inviter')


@admin.register(TeamSponsor)
class TeamSponsorAdmin(admin.ModelAdmin):
    """Team sponsorship management"""
    
    list_display = [
        'team_link', 'sponsor_name', 'tier_badge', 
        'status_badge', 'start_date', 'end_date', 'deal_value'
    ]
    list_filter = ['status', 'sponsor_tier', 'start_date', 'end_date']
    search_fields = ['team__name', 'sponsor_name', 'contact_name', 'contact_email']
    readonly_fields = ['created_at', 'approved_at', 'logo_preview']
    
    fieldsets = (
        ('Sponsor Information', {
            'fields': ('team', 'sponsor_name', 'contact_name', 'contact_email', 'contact_phone')
        }),
        ('Sponsorship Details', {
            'fields': ('sponsor_tier', 'deal_value', 'currency', 'sponsor_logo', 'sponsor_logo_url', 'sponsor_link', 'logo_preview')
        }),
        ('Duration', {
            'fields': ('start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'approved_at', 'approved_by')
        }),
        ('Display', {
            'fields': ('display_order', 'show_on_profile', 'show_on_jerseys'),
            'classes': ('collapse',)
        }),
        ('Benefits & Notes', {
            'fields': ('benefits', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_sponsors', 'reject_sponsors', 'end_sponsorships']
    
    def team_link(self, obj):
        url = reverse('admin:teams_team_change', args=[obj.team.pk])
        return format_html('<a href="{}">{}</a>', url, obj.team.name)
    team_link.short_description = 'Team'
    
    def tier_badge(self, obj):
        colors = {
            'platinum': '#E5E4E2',
            'gold': '#FFD700',
            'silver': '#C0C0C0',
            'bronze': '#CD7F32',
            'partner': '#4A90E2',
        }
        color = colors.get(obj.sponsor_tier, '#666')
        return format_html(
            '<span style="background: {}; color: black; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_sponsor_tier_display()
        )
    tier_badge.short_description = 'Tier'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FF9800',
            'active': '#4CAF50',
            'expired': '#9E9E9E',
            'rejected': '#F44336',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="150" />', obj.logo.url)
        return '—'
    logo_preview.short_description = 'Logo Preview'
    
    def approve_sponsors(self, request, queryset):
        """Approve sponsors and trigger notifications"""
        from apps.teams.services.sponsorship import approve_sponsor
        count = 0
        for sponsor in queryset.filter(status='pending'):
            try:
                approve_sponsor(sponsor)
                count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f'Error approving {sponsor.name}: {str(e)}',
                    messages.ERROR
                )
        self.message_user(request, f'{count} sponsor(s) approved successfully.', messages.SUCCESS)
    approve_sponsors.short_description = "✅ Approve and notify"
    
    def reject_sponsors(self, request, queryset):
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{count} sponsor(s) rejected.', messages.INFO)
    reject_sponsors.short_description = "❌ Reject sponsors"
    
    def end_sponsorships(self, request, queryset):
        from django.utils import timezone
        count = queryset.filter(status='active').update(
            status='expired', 
            end_date=timezone.now().date()
        )
        self.message_user(request, f'{count} sponsorship(s) ended.', messages.INFO)
    end_sponsorships.short_description = "⏹️ End sponsorships"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('team')


@admin.register(TeamDiscussionPost)
class TeamDiscussionPostAdmin(admin.ModelAdmin):
    """Team discussion moderation"""
    
    list_display = ['team_link', 'author_link', 'title', 'post_type_badge', 'created_at', 'comment_count']
    list_filter = ['post_type', 'created_at']
    search_fields = ['team__name', 'author__user__username', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    def team_link(self, obj):
        url = reverse('admin:teams_team_change', args=[obj.team.pk])
        return format_html('<a href="{}">{}</a>', url, obj.team.name)
    team_link.short_description = 'Team'
    
    def author_link(self, obj):
        url = reverse('admin:user_profile_userprofile_change', args=[obj.author.pk])
        return format_html('<a href="{}">{}</a>', url, obj.author)
    author_link.short_description = 'Author'
    
    def post_type_badge(self, obj):
        colors = {
            'announcement': '#F44336',
            'discussion': '#2196F3',
            'question': '#FF9800',
            'poll': '#9C27B0',
        }
        color = colors.get(obj.post_type, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_post_type_display()
        )
    post_type_badge.short_description = 'Type'


# ============================================================================
# SIMPLE ADMINS (Read-Only or Minimal)
# ============================================================================

@admin.register(TeamAchievement)
class TeamAchievementAdmin(admin.ModelAdmin):
    list_display = ['team', 'title', 'placement', 'year', 'created_at']
    list_filter = ['placement', 'year']
    search_fields = ['team__name', 'title']


@admin.register(LegacyTeamStats)
class LegacyTeamStatsAdmin(admin.ModelAdmin):
    """Legacy simple team stats"""
    list_display = ['team', 'matches_played', 'wins', 'losses', 'win_rate']
    search_fields = ['team__name']
    readonly_fields = ['updated_at']


@admin.register(TeamAnalytics)
class TeamAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['team', 'game', 'total_matches', 'matches_won', 'win_rate', 'total_points']
    list_filter = ['game', 'updated_at']
    search_fields = ['team__name', 'game']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TeamTournamentRegistration)
class TeamTournamentRegistrationAdmin(admin.ModelAdmin):
    list_display = ['team', 'tournament_id', 'status', 'registered_at', 'validation_passed']
    list_filter = ['status', 'validation_passed', 'registered_at']
    search_fields = ['team__name']
    readonly_fields = ['registered_at', 'updated_at', 'locked_at', 'roster_snapshot', 'tournament_id']


@admin.register(TeamRankingHistory)
class TeamRankingHistoryAdmin(admin.ModelAdmin):
    list_display = ['team', 'points_change', 'points_before', 'points_after', 'source', 'created_at']
    list_filter = ['source', 'created_at']
    search_fields = ['team__name', 'reason']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(TeamRankingBreakdown)
class TeamRankingBreakdownAdmin(admin.ModelAdmin):
    list_display = ['team', 'final_total', 'calculated_total', 'manual_adjustment_points', 'last_calculated']
    search_fields = ['team__name']
    readonly_fields = ['calculated_total', 'final_total', 'last_calculated']
    
    fieldsets = (
        ('Team', {
            'fields': ('team',)
        }),
        ('Tournament Points', {
            'fields': (
                'tournament_participation_points',
                'tournament_winner_points',
                'tournament_runner_up_points',
                'tournament_top_4_points'
            )
        }),
        ('Team Composition Points', {
            'fields': (
                'member_count_points',
                'team_age_points',
                'achievement_points'
            )
        }),
        ('Manual Adjustments', {
            'fields': ('manual_adjustment_points',)
        }),
        ('Calculated Totals', {
            'fields': ('calculated_total', 'final_total', 'last_calculated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeamRankingSettings)
class TeamRankingSettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_active', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Achievement Points', {
            'fields': (
                'tournament_victory_points',
                'runner_up_points',
                'top4_finish_points',
                'top8_finish_points',
                'participation_points',
                'general_achievement_points'
            )
        }),
        ('Team Composition', {
            'fields': (
                'member_points',
                'monthly_age_points'
            )
        }),
        ('Bonuses', {
            'fields': (
                'verified_team_multiplier',
                'featured_team_bonus'
            )
        }),
        ('System', {
            'fields': (
                'is_active',
                'created_at',
                'updated_at',
                'updated_by'
            )
        }),
    )


# Register remaining models with basic admin
admin.site.register(TeamMerchItem)
admin.site.register(TeamPromotion)
admin.site.register(TeamDiscussionComment)
admin.site.register(TeamChatMessage)
admin.site.register(MatchRecord)
admin.site.register(MatchParticipation)

