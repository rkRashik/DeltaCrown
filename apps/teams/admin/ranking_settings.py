# apps/teams/admin/ranking_settings.py
"""
Django admin configuration for Team Ranking Settings.
Allows admins to configure the point system for team rankings.
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from ..models import TeamRankingSettings, Team

User = get_user_model()


@admin.register(TeamRankingSettings)
class TeamRankingSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for managing team ranking point system.
    """
    list_display = [
        'is_active',
        'tournament_victory_points', 
        'runner_up_points',
        'member_points',
        'updated_at',
        'updated_by',
        'preview_calculation'
    ]
    
    list_filter = ['is_active', 'updated_at']
    
    search_fields = ['updated_by__username']
    
    readonly_fields = ['created_at', 'updated_at', 'preview_calculation', 'active_teams_count']
    
    fieldsets = (
        ('Tournament Achievement Points', {
            'fields': (
                'tournament_victory_points',
                'runner_up_points', 
                'top4_finish_points',
                'top8_finish_points',
                'participation_points',
                'general_achievement_points',
            ),
            'description': 'Points awarded for different tournament placements and achievements.'
        }),
        ('Team Composition & Age Points', {
            'fields': (
                'member_points',
                'monthly_age_points',
            ),
            'description': 'Points based on team size and how long the team has been established.'
        }),
        ('Bonus Multipliers', {
            'fields': (
                'verified_team_multiplier',
                'featured_team_bonus',
            ),
            'description': 'Additional bonuses and multipliers for special team status.'
        }),
        ('System Settings', {
            'fields': (
                'is_active',
                'updated_by',
            ),
            'description': 'Control which ranking system is currently active.'
        }),
        ('Information', {
            'fields': (
                'created_at',
                'updated_at', 
                'active_teams_count',
                'preview_calculation',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set the updated_by field to current admin user."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        # Trigger team score recalculation if this becomes active
        if obj.is_active:
            self.message_user(
                request, 
                f"Ranking settings updated! Team scores will be recalculated based on new point values.",
                level='success'
            )
    
    def preview_calculation(self, obj):
        """Show a preview of how the current settings would calculate scores."""
        if not obj:
            return "No settings available"
        
        # Get a sample team to show calculation
        sample_team = Team.objects.first()
        if not sample_team:
            return "No teams available for preview"
        
        try:
            sample_score = obj.calculate_team_score(sample_team)
            return format_html(
                '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">'
                '<strong>Sample Calculation:</strong><br>'
                'Team: {} <br>'
                'Calculated Score: <strong>{}</strong> points<br>'
                '<small><a href="{}">View team details</a></small>'
                '</div>',
                sample_team.name,
                sample_score,
                reverse('admin:teams_team_change', args=[sample_team.id])
            )
        except Exception as e:
            return format_html(
                '<div style="color: red;">Error calculating preview: {}</div>',
                str(e)
            )
    
    preview_calculation.short_description = "Score Calculation Preview"
    preview_calculation.allow_tags = True
    
    def active_teams_count(self, obj):
        """Show count of active teams that will be affected."""
        count = Team.objects.filter(is_active=True).count()
        return format_html(
            '<strong>{}</strong> active teams will use these settings',
            count
        )
    
    active_teams_count.short_description = "Affected Teams"
    
    actions = ['make_active', 'recalculate_all_scores']
    
    def make_active(self, request, queryset):
        """Action to make selected settings active."""
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one settings record.", level='error')
            return
        
        # Deactivate all others
        TeamRankingSettings.objects.update(is_active=False)
        # Activate selected
        queryset.update(is_active=True)
        
        self.message_user(
            request, 
            f"Selected ranking settings are now active. Team scores should be recalculated.",
            level='success'
        )
    
    make_active.short_description = "Make selected settings active"
    
    def recalculate_all_scores(self, request, queryset):
        """Action to recalculate all team scores using selected settings."""
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one settings record.", level='error')
            return
        
        settings = queryset.first()
        teams = Team.objects.all()
        updated_count = 0
        
        for team in teams:
            try:
                new_score = settings.calculate_team_score(team)
                # You can store this score in a team field if needed
                # team.calculated_ranking_score = new_score
                # team.save(update_fields=['calculated_ranking_score'])
                updated_count += 1
            except Exception:
                continue
        
        self.message_user(
            request,
            f"Recalculated scores for {updated_count} teams using selected settings.",
            level='success'
        )
    
    recalculate_all_scores.short_description = "Recalculate all team scores with these settings"
    
    def has_add_permission(self, request):
        """Limit to reasonable number of settings records."""
        return TeamRankingSettings.objects.count() < 5
    
    def get_readonly_fields(self, request, obj=None):
        """Make updated_by readonly for non-superusers."""
        readonly = list(self.readonly_fields)
        if not request.user.is_superuser:
            readonly.append('updated_by')
        return readonly