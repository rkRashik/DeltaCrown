"""
Teams App - Django Admin Configuration

Provides comprehensive admin interface for managing teams, members, invitations,
sponsorships, and all team-related content.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.contrib import messages
from django import forms
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from apps.games.services import game_service

from .models import (
    Team, TeamMembership, TeamInvite,
    TeamAchievement, TeamSponsor, TeamMerchItem, TeamPromotion,
    TeamDiscussionPost, TeamDiscussionComment,
    TeamChatMessage, TeamAnalytics, LegacyTeamStats,
    TeamRankingHistory, TeamRankingBreakdown, TeamRankingSettings,
    TeamTournamentRegistration, MatchRecord, MatchParticipation
)
from .models.ranking import TeamGameRanking

# Region choices for teams
REGION_CHOICES = [
    ('', 'Select Region'),
    ('NA', 'North America'),
    ('SA', 'South America'),
    ('EU', 'Europe'),
    ('SEA', 'Southeast Asia'),
    ('EA', 'East Asia'),
    ('OCE', 'Oceania'),
    ('ME', 'Middle East'),
    ('AF', 'Africa'),
    ('SA-BD', 'Bangladesh'),
    ('SA-IN', 'India'),
    ('SA-PK', 'Pakistan'),
]


class TeamAdminForm(forms.ModelForm):
    """Custom form for Team admin with proper Game and Region handling."""
    
    # Explicitly override game field to provide proper widget and validation
    game = forms.CharField(
        max_length=50,
        required=False,
        help_text="Which game this team competes in (blank for legacy teams).",
    )
    
    class Meta:
        model = Team
        fields = '__all__'
        widgets = {
            'region': forms.Select(choices=REGION_CHOICES),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert game CharField to Select widget with dynamic choices
        game_choices = [('', '---------')] + list(game_service.get_choices())
        self.fields['game'].widget = forms.Select(choices=game_choices)
        self.fields['region'].widget = forms.Select(choices=REGION_CHOICES)
    
    def clean_game(self):
        """Validate game choice against database."""
        game_value = self.cleaned_data.get('game')
        if game_value:
            # Check if the game slug exists in the database
            valid_slugs = [slug for slug, name in game_service.get_choices()]
            if game_value not in valid_slugs:
                raise forms.ValidationError(f"'{game_value}' is not a valid game choice.")
        return game_value


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
    
    form = TeamAdminForm
    change_form_template = 'admin/teams/team/change_form.html'
    
    # Ranking controls are implemented inline in change_form.html template
    # No additional JS files needed
    
    list_display = [
        'name', 'tag', 'game_badge', 'owner_link', 
        'member_count', 'created_at', 'verification_status', 'featured_badge'
    ]
    list_filter = [
        'game', 'region', 'is_verified', 'is_featured', 
        'allow_posts', 'created_at'
    ]
    search_fields = ['name', 'tag', 'description']
    readonly_fields = [
        'slug', 'created_at', 'updated_at', 'followers_count', 
        'posts_count', 'logo_preview', 'banner_preview'
    ]
    
    # Temporarily disabled TeamAchievementInline (November 2, 2025)
    # Re-enable when new Tournament Engine is built
    inlines = [TeamMembershipInline, TeamInviteInline]  # TeamAchievementInline removed
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'tag', 'slug', 'game', 'description')
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
    
    def owner_link(self, obj):
        """Link to team owner (captain) via property"""
        captain = obj.captain  # Uses @property to get OWNER
        if captain:
            url = reverse('admin:user_profile_userprofile_change', args=[captain.pk])
            return format_html('<a href="{}">{}</a>', url, captain)
        return '—'
    owner_link.short_description = 'Owner'
    
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
    
    def save_model(self, request, obj, form, change):
        """
        Save team and initialize ranking if newly created.
        
        Phase 5: Checks legacy write enforcement before saving.
        """
        from django.conf import settings
        from apps.organizations.services.exceptions import LegacyWriteBlockedException
        
        # Check if legacy writes are blocked (Phase 5)
        blocked = getattr(settings, 'TEAM_LEGACY_WRITE_BLOCKED', True)
        bypass_enabled = getattr(settings, 'TEAM_LEGACY_WRITE_BYPASS_ENABLED', False)
        
        if blocked and not bypass_enabled:
            # Show user-friendly error message in admin
            messages.error(
                request,
                "Legacy team writes are blocked during Phase 5 migration. "
                "Use the new Organization system (apps.organizations) or enable bypass in settings."
            )
            return  # Prevent save
        
        if blocked and bypass_enabled:
            # Bypass enabled - log warning
            messages.warning(
                request,
                "⚠️ Legacy write bypass is ENABLED - changes will be saved but logged. "
                "This should only be used temporarily."
            )
        
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        
        if is_new and obj.game:
            # Initialize TeamGameRanking for the team's game
            try:
                from apps.teams.models.ranking import TeamGameRanking
                from apps.teams.constants import RankingConstants
                
                TeamGameRanking.objects.get_or_create(
                    team=obj,
                    game=obj.game,
                    defaults={
                        'elo_rating': RankingConstants.DEFAULT_ELO,
                        'global_elo': RankingConstants.DEFAULT_ELO,
                        'division': RankingConstants.DIVISION_BRONZE,
                    }
                )
                self.message_user(request, f'Ranking initialized for {obj.name} in {obj.game}', messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f'Warning: Could not initialize ranking: {e}', messages.WARNING)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Note: captain is now a @property, not a ForeignKey - cannot use select_related
        qs = qs.annotate(member_count=Count('memberships', filter=Q(memberships__status='active')))
        return qs
    
    def get_urls(self):
        """Add custom URLs for ranking management."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:team_id>/adjust-points/',
                self.admin_site.admin_view(self.adjust_points_view),
                name='teams_team_adjust_points',
            ),
            path(
                '<int:team_id>/recalculate-points/',
                self.admin_site.admin_view(self.recalculate_points_view),
                name='teams_team_recalculate_points',
            ),
            path(
                '<int:team_id>/get-points/',
                self.admin_site.admin_view(self.get_points_view),
                name='teams_team_get_points',
            ),
        ]
        return custom_urls + urls
    
    def adjust_points_view(self, request, team_id):
        """Handle point adjustment requests."""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
        
        try:
            team = Team.objects.get(pk=team_id)
            data = json.loads(request.body)
            points_adjustment = int(data.get('points_adjustment', 0))
            reason = data.get('reason', 'Manual admin adjustment')
            
            if points_adjustment == 0:
                return JsonResponse({'success': False, 'error': 'Point adjustment cannot be zero'})
            
            # Use ranking service to adjust points
            from apps.teams.services.ranking_service import ranking_service
            
            result = ranking_service.adjust_team_points(
                team=team,
                points_adjustment=points_adjustment,
                reason=reason,
                admin_user=request.user
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'new_total': result['new_total'],
                    'old_total': result['old_total'],
                    'points_change': result['points_change']
                })
            else:
                return JsonResponse({'success': False, 'error': result.get('error', 'Unknown error')})
                
        except Team.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Team not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    def recalculate_points_view(self, request, team_id):
        """Handle point recalculation requests."""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
        
        try:
            team = Team.objects.get(pk=team_id)
            
            # Use ranking service to recalculate points
            from apps.teams.services.ranking_service import ranking_service
            
            result = ranking_service.recalculate_team_points(
                team=team,
                reason='Manual recalculation via admin'
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'new_total': result['new_total'],
                    'old_total': result['old_total'],
                    'points_change': result['points_change']
                })
            else:
                return JsonResponse({'success': False, 'error': result.get('error', 'Unknown error')})
                
        except Team.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Team not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    def get_points_view(self, request, team_id):
        """Get current team points."""
        try:
            team = Team.objects.get(pk=team_id)
            
            # Get team breakdown for current points
            from apps.teams.models.ranking import TeamRankingBreakdown
            try:
                breakdown = TeamRankingBreakdown.objects.get(team=team)
                points = breakdown.final_total
            except TeamRankingBreakdown.DoesNotExist:
                points = team.total_points
            
            return JsonResponse({
                'success': True,
                'points': points
            })
                
        except Team.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Team not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    # Actions
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
            'fields': ('created_at',),
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


@admin.register(TeamGameRanking)
class TeamGameRankingAdmin(admin.ModelAdmin):
    """Per-game ranking management for teams."""
    list_display = [
        'team_link', 'game', 'division', 'elo_rating', 'points', 
        'matches_played', 'win_rate_display', 'tournaments_won', 'updated_at'
    ]
    list_filter = ['game', 'division', 'updated_at']
    search_fields = ['team__name', 'team__tag', 'game']
    readonly_fields = [
        'created_at', 'updated_at', 'last_match_date', 'last_decay_date',
        'win_rate_display', 'rank_display'
    ]
    
    fieldsets = (
        ('Team & Game', {
            'fields': ('team', 'game')
        }),
        ('Ranking Metrics', {
            'fields': ('division', 'elo_rating', 'points', 'global_elo')
        }),
        ('Match Statistics', {
            'fields': (
                'matches_played', 'matches_won', 'matches_lost',
                'win_streak', 'loss_streak', 'win_rate_display'
            )
        }),
        ('Tournament Performance', {
            'fields': (
                'tournaments_played', 'tournaments_won', 'tournament_podium_finishes'
            )
        }),
        ('Timestamps', {
            'fields': ('last_match_date', 'last_decay_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def team_link(self, obj):
        url = reverse('admin:teams_team_change', args=[obj.team.pk])
        return format_html('<a href="{}">{}</a>', url, obj.team.name)
    team_link.short_description = 'Team'
    
    def win_rate_display(self, obj):
        return f"{obj.win_rate}%"
    win_rate_display.short_description = 'Win Rate'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('team')


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

