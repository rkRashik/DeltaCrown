"""
Django Admin interfaces for Match and Dispute models (Module 1.4)

⚠️ LEGACY: This Django admin customization is DEPRECATED as of Phase 7, Epic 7.6.
The new Organizer Console (Phase 7, Epics 7.1-7.6) provides a superior UX for:
- Match Operations Command Center (Epic 7.4): Real-time match control, operations dashboard
- Results Inbox & Queue Management (Epic 7.1): Result review and approval workflows
- Dispute Resolution Module (Phase 6, Epic 6.5): Advanced dispute handling

This file is retained ONLY for:
1. Emergency administrative access (super admin use only)
2. Backward compatibility during Phase 7 transition
3. Data inspection/debugging (not end-user workflows)

SCHEDULED FOR REMOVAL: Phase 8+
REPLACEMENT: Organizer Console (Epics 7.1, 7.4) + Dispute Resolution UI (Epic 6.5)

Source Documents:
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Admin UI requirements)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Admin integration patterns)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-001: Service layer)

Admin Features:
- MatchAdmin: List filters, search, state transitions, bulk actions
- DisputeAdmin: Dispute management, resolution, escalation
- All actions use MatchService (ADR-001)
"""

from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.tournaments.models import Match, Dispute
from apps.tournaments.services.match_service import MatchService


# ===========================
# Match Admin
# ===========================

@admin.register(Match)
class MatchAdmin(ModelAdmin):
    """
    Admin interface for Match model with state management.
    
    Features:
    - List filters by state, tournament, round
    - Search by participant names
    - Bulk actions for state transitions
    - Inline actions using MatchService
    - Read-only fields for audit trail
    """
    
    list_display = [
        'id',
        'tournament_link',
        'round_match_display',
        'participants_display',
        'score_display',
        'state_badge',
        'scheduled_time',
        'check_in_status',
        'created_at',
    ]
    
    list_filter = [
        'state',
        'tournament',
        'round_number',
        'scheduled_time',
        'is_deleted',
    ]
    
    search_fields = [
        'participant1_name',
        'participant2_name',
        'tournament__name',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'started_at',
        'completed_at',
        'deleted_at',
        'deleted_by',
    ]
    autocomplete_fields = ['tournament', 'bracket']
    list_per_page = 25

    def get_queryset(self, request):
        """Optimize queryset with select_related for FK fields used in list_display."""
        return super().get_queryset(request).select_related(
            'tournament', 'bracket', 'deleted_by'
        )

    fieldsets = (
        (_('Match Identification'), {
            'fields': (
                'id',
                'tournament',
                'bracket',
                'round_number',
                'match_number',
            )
        }),
        (_('Participants'), {
            'fields': (
                'participant1_id',
                'participant1_name',
                'participant2_id',
                'participant2_name',
            )
        }),
        (_('Match State'), {
            'fields': (
                'state',
                'participant1_score',
                'participant2_score',
                'winner_id',
                'loser_id',
            )
        }),
        (_('Scheduling'), {
            'fields': (
                'scheduled_time',
                'check_in_deadline',
                'participant1_checked_in',
                'participant2_checked_in',
            )
        }),
        (_('Match Details'), {
            'fields': (
                'lobby_info',
                'stream_url',
            ),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': (
                'created_at',
                'updated_at',
                'started_at',
                'completed_at',
            ),
            'classes': ('collapse',),
        }),
        (_('Soft Delete'), {
            'fields': (
                'is_deleted',
                'deleted_at',
                'deleted_by',
            ),
            'classes': ('collapse',),
        }),
    )
    
    actions = [
        'bulk_transition_to_live',
        'bulk_cancel_matches',
        'bulk_export_match_list',
    ]
    
    # ===========================
    # Custom Display Methods
    # ===========================
    
    @admin.display(description='Tournament', ordering='tournament__name')
    def tournament_link(self, obj):
        """Display tournament with admin link"""
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
    
    @admin.display(description='Round / Match')
    def round_match_display(self, obj):
        """Display round and match number"""
        return f"R{obj.round_number} / M{obj.match_number}"
    
    @admin.display(description='Participants')
    def participants_display(self, obj):
        """Display both participants"""
        p1 = obj.participant1_name or f"ID:{obj.participant1_id}" if obj.participant1_id else "TBD"
        p2 = obj.participant2_name or f"ID:{obj.participant2_id}" if obj.participant2_id else "TBD"
        return f"{p1} vs {p2}"
    
    @admin.display(description='Score')
    def score_display(self, obj):
        """Display match score with winner highlight"""
        if obj.state in [Match.COMPLETED, Match.PENDING_RESULT]:
            score = f"{obj.participant1_score} - {obj.participant2_score}"
            if obj.winner_id:
                winner_name = obj.participant1_name if obj.winner_id == obj.participant1_id else obj.participant2_name
                return format_html(
                    '<strong>{}</strong><br><small>Winner: {}</small>',
                    score,
                    winner_name
                )
            return score
        return "-"
    
    @display(
        description='State',
        ordering='state',
        label={
            'scheduled': 'secondary',
            'check_in': 'info',
            'ready': 'primary',
            'live': 'success',
            'pending_result': 'warning',
            'completed': 'success',
            'disputed': 'danger',
            'forfeit': 'warning',
            'cancelled': 'secondary',
        },
    )
    def state_badge(self, obj):
        """Display state with Unfold color-coded label badge."""
        return obj.state
    
    @admin.display(description='Check-in', boolean=True)
    def check_in_status(self, obj):
        """Display check-in status"""
        if obj.state in [Match.SCHEDULED, Match.CHECK_IN]:
            return obj.is_both_checked_in
        return None  # Not applicable
    
    # ===========================
    # Bulk Actions
    # ===========================
    
    @admin.action(description='Start selected matches (→ LIVE)')
    def bulk_transition_to_live(self, request: HttpRequest, queryset: QuerySet):
        """Bulk transition matches to LIVE state"""
        success_count = 0
        error_count = 0
        
        for match in queryset:
            try:
                MatchService.transition_to_live(match)
                success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Failed to start match {match.id}: {str(e)}",
                    level=messages.ERROR
                )
        
        if success_count > 0:
            self.message_user(
                request,
                f"Successfully started {success_count} match(es)",
                level=messages.SUCCESS
            )
    
    @admin.action(description='Cancel selected matches')
    def bulk_cancel_matches(self, request: HttpRequest, queryset: QuerySet):
        """Bulk cancel matches"""
        success_count = 0
        
        for match in queryset:
            try:
                MatchService.cancel_match(
                    match=match,
                    reason="Cancelled by admin",
                    cancelled_by_id=request.user.id
                )
                success_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to cancel match {match.id}: {str(e)}",
                    level=messages.ERROR
                )
        
        if success_count > 0:
            self.message_user(
                request,
                f"Successfully cancelled {success_count} match(es)",
                level=messages.SUCCESS
            )
    
    @admin.action(description='Export match list (CSV)')
    def bulk_export_match_list(self, request: HttpRequest, queryset: QuerySet):
        """Export selected matches to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="matches.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Tournament', 'Round', 'Match', 'Participant 1', 'Participant 2',
            'Score', 'State', 'Scheduled Time', 'Completed Time'
        ])
        
        for match in queryset:
            writer.writerow([
                match.id,
                match.tournament.name,
                match.round_number,
                match.match_number,
                match.participant1_name or match.participant1_id,
                match.participant2_name or match.participant2_id,
                f"{match.participant1_score}-{match.participant2_score}",
                match.get_state_display(),
                match.scheduled_time,
                match.completed_at,
            ])
        
        return response


# ===========================
# Dispute Admin
# ===========================

@admin.register(Dispute)
class DisputeAdmin(ModelAdmin):
    """
    Admin interface for Dispute model with resolution management.
    
    Features:
    - List filters by status, reason
    - Search by match details
    - Bulk resolution actions
    - Evidence display
    - MatchService integration
    """
    
    list_display = [
        'id',
        'match_link',
        'reason_display',
        'status_badge',
        'initiator_display',
        'evidence_indicators',
        'created_at',
        'resolved_at',
    ]
    
    list_filter = [
        'status',
        'reason',
        'created_at',
    ]
    
    search_fields = [
        'match__tournament__name',
        'match__participant1_name',
        'match__participant2_name',
        'description',
    ]
    
    readonly_fields = [
        'id',
        'match',
        'initiated_by_id',
        'created_at',
        'resolved_at',
        'evidence_screenshot_preview',
    ]
    list_per_page = 25

    def get_queryset(self, request):
        """Optimize queryset with select_related for FK fields used in list_display."""
        return super().get_queryset(request).select_related(
            'match', 'match__tournament'
        )

    fieldsets = (
        (_('Dispute Information'), {
            'fields': (
                'id',
                'match',
                'initiated_by_id',
                'reason',
                'description',
            )
        }),
        (_('Evidence'), {
            'fields': (
                'evidence_screenshot',
                'evidence_screenshot_preview',
                'evidence_video_url',
            )
        }),
        (_('Resolution'), {
            'fields': (
                'status',
                'resolved_by_id',
                'resolution_notes',
                'final_participant1_score',
                'final_participant2_score',
            )
        }),
        (_('Timestamps'), {
            'fields': (
                'created_at',
                'resolved_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    actions = [
        'bulk_set_under_review',
        'bulk_escalate_to_admin',
        'bulk_export_disputes',
    ]
    
    # ===========================
    # Custom Display Methods
    # ===========================
    
    @admin.display(description='Match', ordering='match__tournament__name')
    def match_link(self, obj):
        """Display match with admin link"""
        url = reverse('admin:tournaments_match_change', args=[obj.match.id])
        match_desc = f"{obj.match.tournament.name} - R{obj.match.round_number}M{obj.match.match_number}"
        return format_html('<a href="{}">{}</a>', url, match_desc)
    
    @admin.display(description='Reason')
    def reason_display(self, obj):
        """Display reason with icon"""
        icons = {
            Dispute.SCORE_MISMATCH: '📊',
            Dispute.NO_SHOW: '👻',
            Dispute.CHEATING: '🚫',
            Dispute.TECHNICAL_ISSUE: '⚙️',
            Dispute.OTHER: '❓',
        }
        icon = icons.get(obj.reason, '❓')
        return f"{icon} {obj.get_reason_display()}"
    
    @display(
        description='Status',
        ordering='status',
        label={
            'open': 'danger',
            'under_review': 'warning',
            'resolved': 'success',
            'escalated': 'info',
        },
    )
    def status_badge(self, obj):
        """Display status with Unfold color-coded label badge."""
        return obj.status
    
    @admin.display(description='Initiated By')
    def initiator_display(self, obj):
        """Display initiator information"""
        return f"User ID: {obj.initiated_by_id}"
    
    @admin.display(description='Evidence')
    def evidence_indicators(self, obj):
        """Display evidence availability indicators"""
        indicators = []
        if obj.evidence_screenshot:
            indicators.append('📷 Screenshot')
        if obj.evidence_video_url:
            indicators.append('🎥 Video')
        return ' | '.join(indicators) if indicators else '-'
    
    @admin.display(description='Screenshot Preview')
    def evidence_screenshot_preview(self, obj):
        """Display screenshot thumbnail"""
        if obj.evidence_screenshot:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 200px;" />',
                obj.evidence_screenshot.url
            )
        return "No screenshot"
    
    # ===========================
    # Bulk Actions
    # ===========================
    
    @admin.action(description='Set status to UNDER_REVIEW')
    def bulk_set_under_review(self, request: HttpRequest, queryset: QuerySet):
        """Bulk update disputes to under review"""
        updated = queryset.filter(status=Dispute.OPEN).update(status=Dispute.UNDER_REVIEW)
        self.message_user(
            request,
            f"Set {updated} dispute(s) to Under Review",
            level=messages.SUCCESS
        )
    
    @admin.action(description='Escalate to Admin')
    def bulk_escalate_to_admin(self, request: HttpRequest, queryset: QuerySet):
        """Bulk escalate disputes"""
        success_count = 0
        
        for dispute in queryset:
            try:
                MatchService.escalate_dispute(
                    dispute=dispute,
                    escalated_by_id=request.user.id,
                    escalation_notes="Bulk escalation by admin"
                )
                success_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to escalate dispute {dispute.id}: {str(e)}",
                    level=messages.ERROR
                )
        
        if success_count > 0:
            self.message_user(
                request,
                f"Successfully escalated {success_count} dispute(s)",
                level=messages.SUCCESS
            )
    
    @admin.action(description='Export disputes (CSV)')
    def bulk_export_disputes(self, request: HttpRequest, queryset: QuerySet):
        """Export selected disputes to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="disputes.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Match', 'Reason', 'Status', 'Initiated By',
            'Description', 'Created', 'Resolved', 'Resolution Notes'
        ])
        
        for dispute in queryset:
            writer.writerow([
                dispute.id,
                f"{dispute.match.tournament.name} - R{dispute.match.round_number}M{dispute.match.match_number}",
                dispute.get_reason_display(),
                dispute.get_status_display(),
                dispute.initiated_by_id,
                dispute.description,
                dispute.created_at,
                dispute.resolved_at,
                dispute.resolution_notes,
            ])
        
        return response
