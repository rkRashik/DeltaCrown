# apps/teams/admin/ranking.py
"""
Team Ranking Admin Interface

Provides comprehensive admin interface for managing team ranking points:
1. Global Point Settings (RankingCriteria)
2. Per Team Controls (Team admin enhancements)
3. Audit Trail (TeamRankingHistory)
4. Point Breakdown (TeamRankingBreakdown)
"""
from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.sites import AlreadyRegistered
from django.db.models import QuerySet
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.http import HttpResponse, JsonResponse
import csv
from datetime import datetime
from django.db.models import Sum

from ..models import (
    RankingCriteria, 
    TeamRankingHistory, 
    TeamRankingBreakdown,
    Team
)
from ..services.ranking_service import ranking_service


# -----------------------
# Helper Functions
# -----------------------
def _safe_register(model, admin_class) -> None:
    """Register a model admin if it isn't already registered."""
    try:
        admin.site.register(model, admin_class)
    except AlreadyRegistered:
        pass
    except Exception:
        pass


# -----------------------
# 1. Global Point Settings Admin
# -----------------------
class RankingCriteriaAdmin(admin.ModelAdmin):
    """Admin interface for managing global point values and criteria."""
    
    list_display = [
        'is_active', 'tournament_participation', 'tournament_winner', 
        'tournament_runner_up', 'tournament_top_4', 'points_per_member', 
        'points_per_month_age', 'achievement_points', 'updated_at'
    ]
    
    list_filter = ['is_active', 'updated_at']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Status', {
            'fields': ('is_active',),
            'description': 'Only one criteria set can be active at a time. Activating this will deactivate others.'
        }),
        ('Tournament Points', {
            'fields': (
                'tournament_participation',
                'tournament_winner', 
                'tournament_runner_up',
                'tournament_top_4'
            ),
            'description': 'Points awarded for tournament achievements'
        }),
        ('Team Composition Points', {
            'fields': ('points_per_member', 'points_per_month_age'),
            'description': 'Points based on team size and longevity'
        }),
        ('Other Points', {
            'fields': ('achievement_points',),
            'description': 'Points for miscellaneous achievements'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['activate_criteria', 'recalculate_all_teams']

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-is_active', '-updated_at')

    @admin.action(description="Activate selected criteria (deactivates others)")
    def activate_criteria(self, request, queryset: QuerySet[RankingCriteria]):
        """Activate the selected criteria set."""
        if queryset.count() != 1:
            self.message_user(
                request, 
                "Please select exactly one criteria set to activate.", 
                level=messages.ERROR
            )
            return
            
        criteria = queryset.first()
        
        # Deactivate all others and activate this one
        RankingCriteria.objects.all().update(is_active=False)
        criteria.is_active = True
        criteria.save()
        
        self.message_user(
            request, 
            f"Activated criteria set from {criteria.updated_at.strftime('%Y-%m-%d')}. All team points will be recalculated.",
            level=messages.SUCCESS
        )

    @admin.action(description="Recalculate all team points with current criteria")
    def recalculate_all_teams(self, request, queryset):
        """Trigger recalculation of all team points."""
        result = ranking_service.recalculate_all_teams(admin_user=request.user)
        
        if result['success']:
            self.message_user(
                request,
                f"Recalculated points for {result['teams_processed']} teams. "
                f"{result['teams_updated']} teams had point changes.",
                level=messages.SUCCESS
            )
            if result['errors']:
                self.message_user(
                    request,
                    f"Errors occurred: {'; '.join(result['errors'][:3])}",
                    level=messages.WARNING
                )
        else:
            self.message_user(
                request,
                "Failed to recalculate team points. Check logs for details.",
                level=messages.ERROR
            )


_safe_register(RankingCriteria, RankingCriteriaAdmin)


# -----------------------
# 2. Team Ranking History Admin
# -----------------------
class TeamRankingHistoryAdmin(admin.ModelAdmin):
    """Admin interface for viewing point change audit trail."""
    
    list_display = [
        'team', 'points_change_display', 'source', 'points_before', 
        'points_after', 'admin_user', 'created_at'
    ]
    
    list_filter = [
        'source', 'created_at', 'admin_user'
    ]
    
    search_fields = [
        'team__name', 'team__tag', 'reason', 'admin_user__username'
    ]
    
    readonly_fields = [
        'team', 'points_change', 'points_before', 'points_after',
        'source', 'reason', 'related_object_type', 'related_object_id',
        'admin_user', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False  # History entries are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # History should be immutable
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete history

    def points_change_display(self, obj):
        """Display points change with color coding."""
        if obj.points_change > 0:
            return format_html('<span style="color: green;">+{}</span>', obj.points_change)
        elif obj.points_change < 0:
            return format_html('<span style="color: red;">{}</span>', obj.points_change)
        else:
            return '0'
    points_change_display.short_description = 'Points Change'

    def changelist_view(self, request, extra_context=None):
        """Add export links to the changelist view."""
        extra_context = extra_context or {}
        extra_context['export_urls'] = {
            'export_all_history': reverse('admin:teams_teamrankinghistory_export_all'),
        }
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        """Add custom admin URLs for export functionality."""
        urls = super().get_urls()
        custom_urls = [
            path('export-all-history/', 
                 self.admin_site.admin_view(self.export_all_history_view),
                 name='teams_teamrankinghistory_export_all'),
        ]
        return custom_urls + urls

    def export_all_history_view(self, request):
        """Export all ranking history as CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="all_ranking_history_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # CSV Headers
        writer.writerow([
            'Team Name', 'Team Tag', 'Date/Time', 'Source', 'Points Before',
            'Points Change', 'Points After', 'Reason', 'Admin User'
        ])
        
        # Get all history ordered by most recent
        history = TeamRankingHistory.objects.select_related('team', 'admin_user').order_by('-created_at')
        
        for record in history:
            writer.writerow([
                record.team.name,
                record.team.tag,
                record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                record.get_source_display() if hasattr(record, 'get_source_display') else record.source,
                record.points_before,
                f"{record.points_change:+d}",  # Show + or - sign
                record.points_after,
                record.reason or '',
                record.admin_user.username if record.admin_user else 'System'
            ])
        
        return response


_safe_register(TeamRankingHistory, TeamRankingHistoryAdmin)


# -----------------------
# 3. Team Ranking Breakdown Admin
# -----------------------
class TeamRankingBreakdownAdmin(admin.ModelAdmin):
    """Admin interface for viewing detailed point breakdowns."""
    
    list_display = [
        'team', 'final_total', 'calculated_total', 'manual_adjustment_points',
        'tournament_total_display', 'member_count_points', 'team_age_points',
        'last_calculated'
    ]
    
    list_filter = ['last_calculated']
    
    search_fields = ['team__name', 'team__tag']
    
    readonly_fields = [
        'team', 'calculated_total', 'final_total', 'last_calculated',
        'breakdown_display'
    ]
    
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
        ('Totals', {
            'fields': ('calculated_total', 'final_total', 'last_calculated'),
            'classes': ('wide',)
        }),
        ('Detailed Breakdown', {
            'fields': ('breakdown_display',),
            'classes': ('wide',)
        })
    )
    
    actions = ['recalculate_selected_teams']

    def has_add_permission(self, request):
        return False  # Breakdowns are created automatically
    
    def tournament_total_display(self, obj):
        """Display total tournament points."""
        total = (
            obj.tournament_participation_points +
            obj.tournament_winner_points +
            obj.tournament_runner_up_points +
            obj.tournament_top_4_points
        )
        return total
    tournament_total_display.short_description = 'Tournament Total'

    def breakdown_display(self, obj):
        """Display an enhanced breakdown with before/after values and clear margins."""
        if not obj:
            return "No breakdown available"
            
        # Get current breakdown
        breakdown = obj.get_breakdown_dict()
        
        # Enhanced HTML with better styling
        html_parts = [
            '<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin: 10px 0;">',
            '<h3 style="color: #495057; margin-bottom: 15px; border-bottom: 2px solid #e9ecef; padding-bottom: 8px;">📊 Point Breakdown</h3>',
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">',
            
            # Left column - Tournament Points
            '<div>',
            '<h4 style="color: #6c757d; margin-bottom: 10px;">🏆 Tournament Points</h4>',
            '<div style="background: white; border-radius: 5px; padding: 10px;">',
        ]
        
        tournament_categories = [
            ('tournament_participation_points', 'Participation'),
            ('tournament_winner_points', 'Winner'),
            ('tournament_runner_up_points', 'Runner-up'),
            ('tournament_top_4_points', 'Top 4'),
        ]
        
        tournament_total = 0
        for field, label in tournament_categories:
            points = getattr(obj, field, 0)
            tournament_total += points
            if points > 0:
                html_parts.append(f'<div style="margin: 5px 0; padding: 5px; border-left: 3px solid #28a745;">🎯 {label}: <strong>+{points}</strong></div>')
        
        if tournament_total == 0:
            html_parts.append('<div style="color: #6c757d; font-style: italic;">No tournament points yet</div>')
        else:
            html_parts.append(f'<div style="margin-top: 10px; padding: 8px; background: #e8f5e8; border-radius: 3px; font-weight: bold;">Total Tournament: +{tournament_total}</div>')
        
        html_parts.extend([
            '</div>',
            '</div>',
            
            # Right column - Team Points
            '<div>',
            '<h4 style="color: #6c757d; margin-bottom: 10px;">👥 Team Points</h4>',
            '<div style="background: white; border-radius: 5px; padding: 10px;">',
        ])
        
        # Team composition points
        member_points = obj.member_count_points or 0
        age_points = obj.team_age_points or 0
        achievement_points = obj.achievement_points or 0
        
        if member_points > 0:
            html_parts.append(f'<div style="margin: 5px 0; padding: 5px; border-left: 3px solid #17a2b8;">👨‍👩‍👧‍👦 Members: <strong>+{member_points}</strong></div>')
        if age_points > 0:
            html_parts.append(f'<div style="margin: 5px 0; padding: 5px; border-left: 3px solid #ffc107;">📅 Team Age: <strong>+{age_points}</strong></div>')
        if achievement_points > 0:
            html_parts.append(f'<div style="margin: 5px 0; padding: 5px; border-left: 3px solid #6f42c1;">🎖️ Achievements: <strong>+{achievement_points}</strong></div>')
        
        team_base_total = member_points + age_points + achievement_points
        html_parts.append(f'<div style="margin-top: 10px; padding: 8px; background: #e3f2fd; border-radius: 3px; font-weight: bold;">Team Base Total: +{team_base_total}</div>')
        
        html_parts.extend([
            '</div>',
            '</div>',
            '</div>',  # Close grid
            
            # Manual adjustments section
            '<div style="margin-top: 20px;">',
            '<h4 style="color: #6c757d; margin-bottom: 10px;">⚖️ Manual Adjustments</h4>',
        ])
        
        manual_adj = obj.manual_adjustment_points or 0
        calculated_total = obj.calculated_total or 0
        
        if manual_adj != 0:
            adj_color = '#28a745' if manual_adj > 0 else '#dc3545'
            adj_symbol = '+' if manual_adj > 0 else ''
            html_parts.append(f'''
                <div style="background: white; border-radius: 5px; padding: 15px; border-left: 5px solid {adj_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Before Adjustments:</span>
                        <strong>{calculated_total}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0; color: {adj_color};">
                        <span>Manual Adjustment:</span>
                        <strong>{adj_symbol}{manual_adj}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 2px solid #e9ecef; padding-top: 8px; font-size: 1.1em;">
                        <span><strong>Final Total:</strong></span>
                        <strong style="color: #495057;">{obj.final_total}</strong>
                    </div>
                </div>
            ''')
        else:
            html_parts.append(f'''
                <div style="background: white; border-radius: 5px; padding: 15px;">
                    <div style="text-align: center; color: #6c757d; font-style: italic;">No manual adjustments</div>
                    <div style="text-align: center; margin-top: 10px; font-size: 1.2em; color: #495057;">
                        <strong>Total Points: {obj.final_total}</strong>
                    </div>
                </div>
            ''')
        
        html_parts.extend([
            '</div>',
            f'<div style="text-align: right; margin-top: 15px; color: #6c757d; font-size: 0.9em;">Last Updated: {obj.last_calculated.strftime("%Y-%m-%d %H:%M") if obj.last_calculated else "Never"}</div>',
            '</div>'
        ])
        
        return mark_safe(''.join(html_parts))
    breakdown_display.short_description = 'Point Breakdown'

    def get_urls(self):
        """Add custom admin URLs for export functionality."""
        urls = super().get_urls()
        custom_urls = [
            path('export-team-history/<int:team_id>/', 
                 self.admin_site.admin_view(self.export_team_history_view),
                 name='teams_teamrankingbreakdown_export_history'),
            path('export-all-breakdowns/', 
                 self.admin_site.admin_view(self.export_all_breakdowns_view),
                 name='teams_teamrankingbreakdown_export_all'),
        ]
        return custom_urls + urls

    def export_team_history_view(self, request, team_id):
        """Export detailed point history for a specific team as CSV."""
        try:
            from ..models import Team
            team = Team.objects.get(id=team_id)
            
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="team_{team.tag}_point_history_{datetime.now().strftime("%Y%m%d")}.csv"'
            
            writer = csv.writer(response)
            
            # CSV Headers
            writer.writerow([
                'Team Name', 'Team Tag', 'Date', 'Event Type', 'Event Details',
                'Points Before', 'Points Change', 'Points After', 'Source', 
                'Admin User', 'Tournament/Reason'
            ])
            
            # Get team's complete history
            history = TeamRankingHistory.objects.filter(team=team).order_by('-created_at')
            
            for record in history:
                writer.writerow([
                    team.name,
                    team.tag,
                    record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    record.get_source_display() if hasattr(record, 'get_source_display') else record.source,
                    record.reason or '',
                    record.points_before,
                    f"{record.points_change:+d}",  # Show + or - sign
                    record.points_after,
                    record.source,
                    record.admin_user.username if record.admin_user else '',
                    record.reason or ''
                ])
            
            # Add current breakdown summary
            try:
                breakdown = TeamRankingBreakdown.objects.get(team=team)
                writer.writerow([])  # Empty row
                writer.writerow(['=== CURRENT BREAKDOWN ==='])
                writer.writerow(['Category', 'Points', '', '', '', '', '', '', '', '', ''])
                
                breakdown_data = [
                    ('Tournament Participation', breakdown.tournament_participation_points),
                    ('Tournament Winner', breakdown.tournament_winner_points),
                    ('Tournament Runner-up', breakdown.tournament_runner_up_points),
                    ('Tournament Top 4', breakdown.tournament_top_4_points),
                    ('Team Members', breakdown.member_count_points),
                    ('Team Age', breakdown.team_age_points),
                    ('Achievements', breakdown.achievement_points),
                    ('Manual Adjustments', breakdown.manual_adjustment_points),
                    ('FINAL TOTAL', breakdown.final_total),
                ]
                
                for category, points in breakdown_data:
                    if points != 0 or category == 'FINAL TOTAL':
                        writer.writerow([category, points, '', '', '', '', '', '', '', '', ''])
                        
            except TeamRankingBreakdown.DoesNotExist:
                writer.writerow(['No breakdown available', '', '', '', '', '', '', '', '', '', ''])
            
            return response
            
        except Team.DoesNotExist:
            messages.error(request, f'Team with ID {team_id} not found.')
            return redirect('admin:teams_teamrankingbreakdown_changelist')
        except Exception as e:
            messages.error(request, f'Export failed: {str(e)}')
            return redirect('admin:teams_teamrankingbreakdown_changelist')

    def export_all_breakdowns_view(self, request):
        """Export all team breakdowns as CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="all_team_rankings_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # CSV Headers
        writer.writerow([
            'Team Name', 'Team Tag', 'Game', 'Final Points', 'Calculated Points',
            'Tournament Participation', 'Tournament Winner', 'Tournament Runner-up', 'Tournament Top 4',
            'Member Points', 'Age Points', 'Achievement Points', 'Manual Adjustments',
            'Last Updated'
        ])
        
        # Get all breakdowns
        breakdowns = TeamRankingBreakdown.objects.select_related('team').order_by('-final_total')
        
        for breakdown in breakdowns:
            writer.writerow([
                breakdown.team.name,
                breakdown.team.tag,
                breakdown.team.get_game_display() if hasattr(breakdown.team, 'get_game_display') else breakdown.team.game,
                breakdown.final_total,
                breakdown.calculated_total,
                breakdown.tournament_participation_points,
                breakdown.tournament_winner_points,
                breakdown.tournament_runner_up_points,
                breakdown.tournament_top_4_points,
                breakdown.member_count_points,
                breakdown.team_age_points,
                breakdown.achievement_points,
                breakdown.manual_adjustment_points,
                breakdown.last_calculated.strftime('%Y-%m-%d %H:%M') if breakdown.last_calculated else 'Never'
            ])
        
        return response

    @admin.action(description="Recalculate points for selected teams")
    def recalculate_selected_teams(self, request, queryset):
        """Recalculate points for selected teams."""
        teams_updated = 0
        errors = []
        
        for breakdown in queryset:
            result = ranking_service.recalculate_team_points(
                breakdown.team,
                admin_user=request.user,
                reason="Manual recalculation from admin"
            )
            
            if result['success']:
                if result['points_change'] != 0:
                    teams_updated += 1
            else:
                errors.append(f"{breakdown.team.name}: {result['error']}")
        
        if teams_updated > 0:
            self.message_user(
                request,
                f"Recalculated points for {teams_updated} teams.",
                level=messages.SUCCESS
            )
        
        if errors:
            self.message_user(
                request,
                f"Errors: {'; '.join(errors[:3])}",
                level=messages.WARNING
            )


_safe_register(TeamRankingBreakdown, TeamRankingBreakdownAdmin)


# -----------------------
# 4. Team Admin Enhancements for Ranking
# -----------------------
class TeamPointsAdjustmentForm(forms.Form):
    """Form for making manual point adjustments to teams."""
    
    points_adjustment = forms.IntegerField(
        help_text="Enter positive number to add points, negative to subtract. Example: +100 or -50"
    )
    reason = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text="Explain why you're adjusting the points (required for audit trail)"
    )


def enhance_team_admin():
    """Add ranking functionality to the existing Team admin."""
    try:
        # Get the existing TeamAdmin
        team_admin = admin.site._registry.get(Team)
        if not team_admin:
            return
            
        # Add ranking-related methods
        def ranking_breakdown_display(self, obj):
            """Display enhanced ranking breakdown with export link."""
            try:
                breakdown = getattr(obj, 'ranking_breakdown', None)
                if not breakdown:
                    # Trigger calculation if no breakdown exists
                    result = ranking_service.recalculate_team_points(obj)
                    if result['success']:
                        breakdown = TeamRankingBreakdown.objects.filter(team=obj).first()
                
                if not breakdown:
                    return format_html('<span style="color: red;">No breakdown available</span>')
                
                # Calculate tournament total
                tournament_total = (
                    breakdown.tournament_participation_points + 
                    breakdown.tournament_winner_points + 
                    breakdown.tournament_runner_up_points + 
                    breakdown.tournament_top_4_points
                )
                
                # Enhanced display with export link
                export_url = reverse('admin:teams_teamrankingbreakdown_export_history', args=[obj.id])
                breakdown_url = reverse('admin:teams_teamrankingbreakdown_change', args=[breakdown.team.id])
                
                return format_html(
                    '''
                    <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px; margin: 5px 0;">
                        <div style="font-size: 1.2em; color: #495057; margin-bottom: 8px;">
                            <strong>🏆 Total: {}</strong> points
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.9em;">
                            <div>🎯 Tournament: <strong>{}</strong></div>
                            <div>👥 Members: <strong>{}</strong></div>
                            <div>📅 Team Age: <strong>{}</strong></div>
                            <div>⚖️ Adjustments: <strong style="color: {};">{}</strong></div>
                        </div>
                        <div style="margin-top: 8px; text-align: center;">
                            <a href="{}" target="_blank" style="color: #007bff; text-decoration: none; font-size: 0.85em;">
                                📊 Export History CSV
                            </a>
                            <span style="margin: 0 8px; color: #6c757d;">|</span>
                            <a href="{}" style="color: #28a745; text-decoration: none; font-size: 0.85em;">
                                🔄 View Full Breakdown
                            </a>
                        </div>
                    </div>
                    ''',
                    breakdown.final_total,
                    tournament_total,
                    breakdown.member_count_points,
                    breakdown.team_age_points,
                    '#dc3545' if breakdown.manual_adjustment_points < 0 else '#28a745',
                    '{:+d}'.format(breakdown.manual_adjustment_points),
                    export_url,
                    breakdown_url
                )
            except Exception as e:
                return format_html('<span style="color: red;">Error: {}</span>', str(e))
        ranking_breakdown_display.short_description = 'Ranking Points'
        
        def adjust_ranking_points(self, request, queryset):
            """Admin action to adjust team points."""
            if 'apply' in request.POST:
                # Process the form
                form = TeamPointsAdjustmentForm(request.POST)
                if form.is_valid():
                    adjustment = form.cleaned_data['points_adjustment']
                    reason = form.cleaned_data['reason']
                    
                    updated_teams = []
                    errors = []
                    
                    for team in queryset:
                        result = ranking_service.adjust_team_points(
                            team=team,
                            points_adjustment=adjustment,
                            reason=reason,
                            admin_user=request.user
                        )
                        
                        if result['success']:
                            updated_teams.append(team.name)
                        else:
                            errors.append(f"{team.name}: {result['error']}")
                    
                    if updated_teams:
                        self.message_user(
                            request,
                            f"Adjusted points for {len(updated_teams)} teams: {', '.join(updated_teams[:3])}",
                            level=messages.SUCCESS
                        )
                    
                    if errors:
                        self.message_user(
                            request,
                            f"Errors: {'; '.join(errors[:3])}",
                            level=messages.ERROR
                        )
                    
                    return redirect(request.get_full_path())
            else:
                form = TeamPointsAdjustmentForm()
            
            return render(
                request,
                'admin/teams/adjust_points.html',
                {
                    'form': form,
                    'teams': queryset,
                    'title': 'Adjust Team Points',
                    'opts': self.model._meta,
                }
            )
        adjust_ranking_points.short_description = "Adjust ranking points"
        
        def recalculate_team_points_action(self, request, queryset):
            """Admin action to recalculate team points."""
            updated_teams = []
            errors = []
            
            for team in queryset:
                result = ranking_service.recalculate_team_points(
                    team=team,
                    admin_user=request.user,
                    reason="Manual recalculation from team admin"
                )
                
                if result['success'] and result['points_change'] != 0:
                    updated_teams.append(f"{team.name} ({result['points_change']:+d})")
                elif not result['success']:
                    errors.append(f"{team.name}: {result['error']}")
            
            if updated_teams:
                self.message_user(
                    request,
                    f"Recalculated points: {', '.join(updated_teams[:3])}",
                    level=messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    "No point changes were needed.",
                    level=messages.INFO
                )
            
            if errors:
                self.message_user(
                    request,
                    f"Errors: {'; '.join(errors[:3])}",
                    level=messages.WARNING
                )
        recalculate_team_points_action.short_description = "Recalculate team points"
        
        # Add methods to the admin class (bind them properly)
        import types
        team_admin.ranking_breakdown_display = types.MethodType(ranking_breakdown_display, team_admin)
        team_admin.adjust_ranking_points = types.MethodType(adjust_ranking_points, team_admin)
        team_admin.recalculate_team_points_action = types.MethodType(recalculate_team_points_action, team_admin)
        
        # Add to list_display if not already there
        if hasattr(team_admin, 'list_display'):
            current_display = list(team_admin.list_display)
            if 'ranking_breakdown_display' not in current_display:
                current_display.append('ranking_breakdown_display')
                team_admin.list_display = current_display
        
        # Add to actions if not already there
        if hasattr(team_admin, 'actions'):
            current_actions = list(team_admin.actions or [])
            if 'adjust_ranking_points' not in current_actions:
                current_actions.extend(['adjust_ranking_points', 'recalculate_team_points_action'])
                team_admin.actions = current_actions
        
    except Exception as e:
        # Silently fail if we can't enhance the admin
        pass


# Call the enhancement function
enhance_team_admin()
