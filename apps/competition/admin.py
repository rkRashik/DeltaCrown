"""Competition app Django admin configuration.

This admin module uses lazy schema detection to prevent crashes when
COMPETITION_APP_ENABLED=1 but migrations not applied.

CRITICAL: Do NOT access database during module import - that breaks migrations!
"""
from django.contrib import admin
from django.shortcuts import render
from django.contrib import messages
from django.utils.html import format_html
from django.db import connection
import logging

logger = logging.getLogger(__name__)


def competition_admin_status(request):
    """Admin status page showing competition schema state (no model queries)."""
    # Check schema without querying models
    try:
        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)
            
            required_tables = {
                'competition_game_ranking_config',
                'competition_match_report',
                'competition_match_verification',
                'competition_team_game_ranking_snapshot',
                'competition_team_global_ranking_snapshot',
            }
            
            existing = required_tables & set(table_names)
            missing = required_tables - set(table_names)
            schema_ready = len(missing) == 0
    except Exception as e:
        schema_ready = False
        existing = set()
        missing = set()
        error = str(e)
    else:
        error = None
    
    context = {
        'title': 'Competition Schema Status',
        'schema_ready': schema_ready,
        'existing_tables': sorted(existing),
        'missing_tables': sorted(missing),
        'error': error,
        'site_header': 'DeltaCrown Admin',
        'site_title': 'Competition Status',
    }
    return render(request, 'admin/competition/status.html', context)


# DO NOT check schema at import time - that causes database access before migrations run
# Instead, we'll check lazily when Django actually tries to load admin classes
try:
    # Import models optimistically - if tables don't exist, admin just won't show them
    from .models import (
        GameRankingConfig,
        MatchReport,
        MatchVerification,
        TeamGameRankingSnapshot,
        TeamGlobalRankingSnapshot,
    )
    from .services import VerificationService, SnapshotService
    
    MODELS_IMPORTED = True
except Exception as e:
    # Models can't be imported (likely because tables don't exist)
    logger.warning(
        f"Competition models not available: {e}. "
        "Run 'python manage.py migrate competition' to enable admin features."
    )
    MODELS_IMPORTED = False


# Only register admin if models were successfully imported
if MODELS_IMPORTED:
    @admin.register(GameRankingConfig)
    class GameRankingConfigAdmin(admin.ModelAdmin):
        """Admin interface for GameRankingConfig."""
        
        list_display = ['game_id', 'game_name', 'is_active', 'updated_at']
        list_filter = ['is_active']
        search_fields = ['game_id', 'game_name']
        readonly_fields = ['created_at', 'updated_at']
        
        fieldsets = [
            ('Game Information', {
                'fields': ['game_id', 'game_name', 'is_active']
            }),
            ('Scoring Configuration', {
                'fields': ['scoring_weights'],
                'description': 'JSON field: {tournament_win: 500, verified_match_win: 10, ...}'
            }),
            ('Tier Thresholds', {
                'fields': ['tier_thresholds'],
                'description': 'JSON field: {DIAMOND: 2000, PLATINUM: 1200, ...}'
            }),
            ('Decay Policy', {
                'fields': ['decay_policy'],
                'description': 'JSON field: {enabled: true, inactivity_threshold_days: 30, ...}'
            }),
            ('Verification Rules', {
                'fields': ['verification_rules'],
                'description': 'JSON field: {require_opponent_confirmation: true, ...}'
            }),
            ('Metadata', {
                'fields': ['created_at', 'updated_at'],
                'classes': ['collapse']
            }),
        ]
    
    
    @admin.register(MatchReport)
    class MatchReportAdmin(admin.ModelAdmin):
        """Admin interface for MatchReport."""
        
        list_display = ['id', 'game_id', 'team1', 'team2', 'result', 'match_type', 'played_at', 'submitted_at']
        list_filter = ['game_id', 'match_type', 'result', 'played_at']
        search_fields = ['team1__name', 'team2__name', 'submitted_by__username']
        readonly_fields = ['submitted_at']
        date_hierarchy = 'played_at'
        
        fieldsets = [
            ('Match Details', {
                'fields': ['game_id', 'match_type', 'result', 'played_at']
            }),
            ('Teams', {
                'fields': ['team1', 'team2']
            }),
            ('Evidence', {
                'fields': ['evidence_url', 'evidence_notes']
            }),
            ('Submission Info', {
                'fields': ['submitted_by', 'submitted_at'],
                'classes': ['collapse']
            }),
        ]
    
    
    @admin.register(MatchVerification)
    class MatchVerificationAdmin(admin.ModelAdmin):
        """Admin interface for MatchVerification."""
        
        list_display = ['match_report', 'status', 'confidence_level', 'verified_at', 'verified_by']
        list_filter = ['status', 'confidence_level', 'verified_at']
        search_fields = ['match_report__team1__name', 'match_report__team2__name']
        readonly_fields = ['created_at', 'updated_at', 'verified_at']
        date_hierarchy = 'verified_at'
        
        fieldsets = [
            ('Verification Status', {
                'fields': ['match_report', 'status', 'confidence_level']
            }),
            ('Verification Details', {
                'fields': ['verified_at', 'verified_by']
            }),
            ('Dispute Information', {
                'fields': ['dispute_reason', 'admin_notes'],
                'classes': ['collapse']
            }),
            ('Metadata', {
                'fields': ['created_at', 'updated_at'],
                'classes': ['collapse']
            }),
        ]
        
        actions = ['mark_as_admin_verified', 'mark_as_rejected']
        
        @admin.action(description='Mark selected as Admin Verified')
        def mark_as_admin_verified(self, request, queryset):
            """Admin action to verify matches via VerificationService."""
            success_count = 0
            error_count = 0
            
            for verification in queryset:
                try:
                    VerificationService.admin_verify_match(request.user, verification.match_report.id)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(request, f"Failed to verify match {verification.match_report.id}: {str(e)}", level=messages.ERROR)
            
            if success_count:
                self.message_user(request, f"Successfully verified {success_count} match(es)", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed to verify {error_count} match(es)", level=messages.WARNING)
        
        @admin.action(description='Mark selected as Rejected')
        def mark_as_rejected(self, request, queryset):
            """Admin action to reject fraudulent matches via VerificationService."""
            success_count = 0
            error_count = 0
            
            for verification in queryset:
                try:
                    VerificationService.reject_match(request.user, verification.match_report.id, reason="Rejected by admin action")
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(request, f"Failed to reject match {verification.match_report.id}: {str(e)}", level=messages.ERROR)
            
            if success_count:
                self.message_user(request, f"Successfully rejected {success_count} match(es)", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed to reject {error_count} match(es)", level=messages.WARNING)
    
    
    @admin.register(TeamGameRankingSnapshot)
    class TeamGameRankingSnapshotAdmin(admin.ModelAdmin):
        """Admin interface for TeamGameRankingSnapshot."""
        
        list_display = ['team', 'game_id', 'tier', 'score', 'rank', 'verified_match_count', 'confidence_level', 'snapshot_date']
        list_filter = ['game_id', 'tier', 'confidence_level']
        search_fields = ['team__name']
        readonly_fields = ['snapshot_date', 'created_at']
        date_hierarchy = 'snapshot_date'
        actions = ['recompute_selected_snapshots']
        
        fieldsets = [
            ('Team & Game', {
                'fields': ['team', 'game_id']
            }),
            ('Ranking', {
                'fields': ['score', 'tier', 'rank', 'percentile']
            }),
            ('Match Statistics', {
                'fields': ['verified_match_count', 'confidence_level', 'last_match_at']
            }),
            ('Score Breakdown', {
                'fields': ['breakdown'],
                'description': 'JSON field showing score sources',
                'classes': ['collapse']
            }),
            ('Metadata', {
                'fields': ['snapshot_date', 'created_at'],
                'classes': ['collapse']
            }),
        ]
        
        @admin.action(description='Recompute rankings for selected snapshots')
        def recompute_selected_snapshots(self, request, queryset):
            """Recompute rankings for selected game snapshots"""
            success_count = 0
            error_count = 0
            
            for snapshot in queryset:
                try:
                    SnapshotService.update_team_game_snapshot(snapshot.team, snapshot.game_id)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(
                        request, 
                        f"Failed to recompute {snapshot.team.slug}/{snapshot.game_id}: {str(e)}", 
                        level=messages.ERROR
                    )
            
            if success_count:
                self.message_user(
                    request, 
                    f"Successfully recomputed {success_count} snapshot(s)", 
                    level=messages.SUCCESS
                )
            if error_count:
                self.message_user(
                    request, 
                    f"Failed to recompute {error_count} snapshot(s)", 
                    level=messages.WARNING
                )
    
    
    @admin.register(TeamGlobalRankingSnapshot)
    class TeamGlobalRankingSnapshotAdmin(admin.ModelAdmin):
        """Admin interface for TeamGlobalRankingSnapshot."""
        
        list_display = ['team', 'global_tier', 'global_score', 'global_rank', 'games_played', 'snapshot_date']
        list_filter = ['global_tier', 'games_played']
        search_fields = ['team__name']
        readonly_fields = ['snapshot_date', 'created_at']
        date_hierarchy = 'snapshot_date'
        actions = ['recompute_selected_global_snapshots']
        
        fieldsets = [
            ('Team', {
                'fields': ['team']
            }),
            ('Global Ranking', {
                'fields': ['global_score', 'global_tier', 'global_rank', 'games_played']
            }),
            ('Game Contributions', {
                'fields': ['game_contributions'],
                'description': 'JSON field showing per-game scores',
                'classes': ['collapse']
            }),
            ('Metadata', {
                'fields': ['snapshot_date', 'created_at'],
                'classes': ['collapse']
            }),
        ]
        
        @admin.action(description='Recompute global rankings for selected teams')
        def recompute_selected_global_snapshots(self, request, queryset):
            """Recompute global rankings for selected teams"""
            success_count = 0
            error_count = 0
            
            for snapshot in queryset:
                try:
                    SnapshotService.update_team_global_snapshot(snapshot.team)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(
                        request, 
                        f"Failed to recompute global for {snapshot.team.slug}: {str(e)}", 
                        level=messages.ERROR
                    )
            
            if success_count:
                self.message_user(
                    request, 
                    f"Successfully recomputed {success_count} global snapshot(s)", 
                    level=messages.SUCCESS
                )
            if error_count:
                self.message_user(
                    request, 
                    f"Failed to recompute {error_count} global snapshot(s)", 
                    level=messages.WARNING
                )
