"""
Tournament Result Admin

Admin interface for viewing tournament results and winner determination audit trails.

Related Planning:
- Documents/ExecutionPlan/Modules/MODULE_5.1_EXECUTION_CHECKLIST.md#section-6-admin-integration

Module: apps.tournaments.admin_result
Implements: phase_5:module_5_1
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

import json

from .models import TournamentResult


@admin.register(TournamentResult)
class TournamentResultAdmin(admin.ModelAdmin):
    """
    Admin interface for TournamentResult.
    
    View-only interface for audit purposes.
    Winners are determined automatically via WinnerDeterminationService.
    """
    
    list_display = [
        'tournament_link',
        'winner_link',
        'runner_up_link',
        'determination_method',
        'requires_review_badge',
        'created_at',
        'created_by',
    ]
    
    list_filter = [
        'determination_method',
        'requires_review',
        'created_at',
    ]
    
    search_fields = [
        'tournament__title',
        'winner__user__username',
        'winner__team__name',
        'runner_up__user__username',
        'runner_up__team__name',
    ]
    
    readonly_fields = [
        'tournament',
        'winner',
        'runner_up',
        'third_place',
        'final_bracket',
        'determination_method',
        'rules_applied_formatted',
        'requires_review',
        'created_by',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament', 'final_bracket')
        }),
        ('Placements', {
            'fields': (
                'winner',
                'runner_up',
                'third_place',
            )
        }),
        ('Determination Logic', {
            'fields': (
                'determination_method',
                'rules_applied_formatted',
                'requires_review',
            )
        }),
        ('Audit Trail', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def has_add_permission(self, request):
        """
        Winners determined automatically via service layer.
        No manual creation allowed.
        """
        return False
    
    def has_delete_permission(self, request, obj=None):
        """
        Results are permanent audit records.
        Soft delete only (via SoftDeleteModel).
        """
        return False
    
    def has_change_permission(self, request, obj=None):
        """
        Results are immutable once created.
        View-only interface.
        """
        return False
    
    def tournament_link(self, obj):
        """Link to tournament admin page."""
        if not obj.tournament:
            return '-'
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.tournament.title
        )
    tournament_link.short_description = 'Tournament'
    
    def winner_link(self, obj):
        """Link to winner registration."""
        if not obj.winner:
            return '-'
        url = reverse('admin:tournaments_registration_change', args=[obj.winner.id])
        participant_name = self._get_participant_name(obj.winner)
        return format_html(
            '<a href="{}">{}</a>',
            url,
            participant_name
        )
    winner_link.short_description = 'Winner'
    
    def runner_up_link(self, obj):
        """Link to runner-up registration."""
        if not obj.runner_up:
            return '-'
        url = reverse('admin:tournaments_registration_change', args=[obj.runner_up.id])
        participant_name = self._get_participant_name(obj.runner_up)
        return format_html(
            '<a href="{}">{}</a>',
            url,
            participant_name
        )
    runner_up_link.short_description = 'Runner-Up'
    
    def requires_review_badge(self, obj):
        """Badge for requires_review flag."""
        if obj.requires_review:
            return format_html(
                '<span style="color: #f0ad4e; font-weight: bold;">⚠ REVIEW</span>'
            )
        return format_html(
            '<span style="color: #5cb85c;">✓ Verified</span>'
        )
    requires_review_badge.short_description = 'Review Status'
    
    def rules_applied_formatted(self, obj):
        """Pretty-print rules_applied JSONB field."""
        if not obj.rules_applied:
            return '-'
        
        try:
            formatted_json = json.dumps(obj.rules_applied, indent=2, sort_keys=False)
            return mark_safe(f'<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{formatted_json}</pre>')
        except Exception as e:
            return f'Error formatting: {e}'
    
    rules_applied_formatted.short_description = 'Rules Applied (Audit Trail)'
    
    def _get_participant_name(self, registration):
        """Get participant name (team or user)."""
        if registration.team:
            return registration.team.name
        elif registration.user:
            return registration.user.username
        return f'Registration #{registration.id}'
