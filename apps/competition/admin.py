"""Competition app Django admin configuration.

This admin module uses lazy schema detection to prevent crashes when
COMPETITION_APP_ENABLED=1 but migrations not applied.

CRITICAL: Do NOT access database during module import - that breaks migrations!
"""
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.shortcuts import render
from django.contrib import messages
from django.utils.html import format_html
from django.db import connection
from django.db.models import Count
from django.urls import NoReverseMatch, reverse
import logging

logger = logging.getLogger(__name__)


def _linked_match_result_admin_summary(match):
    if not match:
        return 'No linked match'

    try:
        submissions = list(match.result_submissions.all())
    except Exception:
        submissions = []

    open_disputes = 0
    for submission in submissions:
        try:
            disputes = submission.disputes.all()
        except Exception:
            disputes = []
        for dispute in disputes:
            is_open = getattr(dispute, 'is_open', None)
            if callable(is_open):
                open_disputes += 1 if is_open() else 0
            else:
                status = str(getattr(dispute, 'status', '') or '').lower()
                open_disputes += 1 if status in {'open', 'under_review', 'escalated'} else 0

    lobby_info = getattr(match, 'lobby_info', None)
    workflow = {}
    if isinstance(lobby_info, dict):
        raw_workflow = lobby_info.get('match_lobby_workflow') or lobby_info.get('premium_lobby_workflow')
        workflow = raw_workflow if isinstance(raw_workflow, dict) else {}

    result_status = str(workflow.get('result_status') or '').strip() or 'not submitted'
    proof_count = sum(
        1 for submission in submissions
        if getattr(submission, 'proof_screenshot_url', '') or getattr(submission, 'proof_screenshot', None)
    )

    return format_html(
        '{} | result: {} | submissions: {} | proof: {} | open disputes: {}',
        getattr(match, 'state', '') or 'unknown',
        result_status,
        len(submissions),
        proof_count,
        open_disputes,
    )


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
        Challenge,
        ChallengeResultSubmission,
        Bounty,
        BountyClaim,
    )
    from .services import BountyService, ChallengeService, VerificationService, SnapshotService
    
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
    class GameRankingConfigAdmin(ModelAdmin):
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
    class MatchReportAdmin(ModelAdmin):
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
    class MatchVerificationAdmin(ModelAdmin):
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
    class TeamGameRankingSnapshotAdmin(ModelAdmin):
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
    class TeamGlobalRankingSnapshotAdmin(ModelAdmin):
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

    # ── Challenge Admin ──────────────────────────────────────────────────
    class ChallengeResultSubmissionInline(TabularInline):
        model = ChallengeResultSubmission
        extra = 0
        can_delete = False
        readonly_fields = [
            'id', 'team', 'submitted_by', 'result', 'score_details',
            'evidence_url', 'created_at', 'updated_at',
        ]
        fields = readonly_fields

        def has_add_permission(self, request, obj=None):
            return False

    @admin.register(Challenge)
    class ChallengeAdmin(ModelAdmin):
        """Admin interface for Challenge."""
        
        list_display = [
            'reference_code', 'title', 'challenger_team', 'challenged_team',
            'game', 'status', 'entry_fee_dc', 'result_submissions_count',
            'escrow_state', 'match_room_admin_link', 'linked_match_result_state', 'created_at',
        ]
        list_filter = ['status', 'challenge_type', 'game', 'is_featured', 'escrow_locked']
        search_fields = ['reference_code', 'title', 'challenger_team__name', 'challenged_team__name']
        readonly_fields = [
            'id', 'reference_code', 'status', 'result', 'score_details',
            'evidence_url', 'match_report', 'entry_fee_dc', 'wager_amount_dc',
            'escrow_locked', 'challenger_lock_txn', 'challenged_lock_txn',
            'payout_txn', 'funded_by_challenger', 'funded_by_challenged',
            'resolved_by', 'closure_reason', 'closure_note', 'match',
            'match_room_admin_link', 'linked_match_result_state', 'result_submissions_count',
            'created_at', 'updated_at', 'accepted_at', 'completed_at', 'settled_at',
        ]
        raw_id_fields = [
            'challenger_team', 'challenged_team', 'game', 'match_report',
            'created_by', 'accepted_by', 'resolved_by', 'challenger_lock_txn',
            'challenged_lock_txn', 'payout_txn', 'funded_by_challenger',
            'funded_by_challenged', 'match',
        ]
        date_hierarchy = 'created_at'
        inlines = [ChallengeResultSubmissionInline]
        actions = [
            'settle_confirmed_showdowns',
            'resolve_disputes_as_challenger_win',
            'resolve_disputes_as_challenged_win',
            'resolve_disputes_as_draw',
            'void_refund_showdowns',
            'respawn_missing_match_rooms',
        ]
        
        fieldsets = [
            ('Challenge', {
                'fields': ['id', 'reference_code', 'title', 'description', 'status', 'challenge_type']
            }),
            ('Teams', {
                'fields': ['challenger_team', 'challenged_team']
            }),
            ('Game & Format', {
                'fields': ['game', 'best_of', 'game_config', 'platform', 'server_region']
            }),
            ('Prize', {
                'fields': ['prize_type', 'prize_amount', 'prize_description', 'entry_fee_dc']
            }),
            ('Result', {
                'fields': ['result', 'score_details', 'evidence_url', 'match_report'],
                'classes': ['collapse']
            }),
            ('Escrow & Settlement', {
                'fields': [
                    'escrow_locked', 'challenger_lock_txn', 'challenged_lock_txn',
                    'payout_txn', 'funded_by_challenger', 'funded_by_challenged',
                    'closure_reason', 'closure_note',
                ],
                'classes': ['collapse'],
            }),
            ('Match Room', {
                'fields': ['match', 'match_room_admin_link', 'linked_match_result_state'],
                'classes': ['collapse'],
            }),
            ('Scheduling', {
                'fields': ['scheduled_at', 'expires_at']
            }),
            ('Users & Actions', {
                'fields': ['created_by', 'accepted_by', 'resolved_by'],
                'classes': ['collapse']
            }),
            ('Visibility', {
                'fields': ['is_public', 'is_featured']
            }),
            ('Timestamps', {
                'fields': ['created_at', 'updated_at', 'accepted_at', 'completed_at', 'settled_at'],
                'classes': ['collapse']
            }),
        ]

        def get_queryset(self, request):
            return super().get_queryset(request).annotate(_result_submission_count=Count('result_submissions'))

        @admin.display(description='Submissions')
        def result_submissions_count(self, obj):
            return getattr(obj, '_result_submission_count', None) or obj.result_submissions.count()

        @admin.display(description='Escrow')
        def escrow_state(self, obj):
            if not obj.entry_fee_dc:
                return 'No entry'
            if obj.payout_txn_id:
                return 'Paid out'
            if obj.escrow_locked:
                return 'Locked'
            if obj.challenger_lock_txn_id:
                return 'Partial lock'
            return 'No lock'

        @admin.display(description='Match room')
        def match_room_admin_link(self, obj):
            if not obj.match_id or not getattr(obj.match, 'tournament_id', None):
                return '—'
            tournament = getattr(obj.match, 'tournament', None)
            if not tournament or not getattr(tournament, 'slug', ''):
                return '—'
            try:
                url = reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': obj.match_id})
            except NoReverseMatch:
                return '—'
            return format_html('<a href="{}" target="_blank">Open room</a>', url)

        @admin.display(description='Linked match result')
        def linked_match_result_state(self, obj):
            return _linked_match_result_admin_summary(getattr(obj, 'match', None))

        def _run_showdown_action(self, request, queryset, callback, success_label):
            success_count = 0
            error_count = 0
            for challenge in queryset:
                try:
                    callback(challenge)
                    success_count += 1
                except Exception as exc:
                    error_count += 1
                    self.message_user(
                        request,
                        f"{challenge.reference_code}: {exc}",
                        level=messages.ERROR,
                    )
            if success_count:
                self.message_user(request, f"{success_label}: {success_count}", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed: {error_count}", level=messages.WARNING)

        @admin.action(description='Settle selected confirmed Showdowns')
        def settle_confirmed_showdowns(self, request, queryset):
            self._run_showdown_action(
                request,
                queryset,
                lambda c: ChallengeService.admin_settle_confirmed_showdown(
                    challenge_id=c.pk,
                    resolved_by=request.user,
                    note=f"Settled from Django admin by {request.user.username}.",
                ),
                'Settled Showdowns',
            )

        @admin.action(description='Resolve disputed Showdowns: challenger wins')
        def resolve_disputes_as_challenger_win(self, request, queryset):
            self._resolve_disputes(request, queryset, 'CHALLENGER_WIN', 'Resolved as challenger win')

        @admin.action(description='Resolve disputed Showdowns: opponent wins')
        def resolve_disputes_as_challenged_win(self, request, queryset):
            self._resolve_disputes(request, queryset, 'CHALLENGED_WIN', 'Resolved as opponent win')

        @admin.action(description='Resolve disputed Showdowns: draw/refund')
        def resolve_disputes_as_draw(self, request, queryset):
            self._resolve_disputes(request, queryset, 'DRAW', 'Resolved as draw')

        def _resolve_disputes(self, request, queryset, result, success_label):
            self._run_showdown_action(
                request,
                queryset,
                lambda c: ChallengeService.admin_resolve_disputed_showdown(
                    challenge_id=c.pk,
                    resolved_by=request.user,
                    result=result,
                    note=f"{success_label} from Django admin by {request.user.username}.",
                ),
                success_label,
            )

        @admin.action(description='Void and refund selected Showdowns')
        def void_refund_showdowns(self, request, queryset):
            self._run_showdown_action(
                request,
                queryset,
                lambda c: ChallengeService.admin_void_refund_showdown(
                    challenge_id=c.pk,
                    resolved_by=request.user,
                    note=f"Voided and refunded from Django admin by {request.user.username}.",
                ),
                'Voided/refunded Showdowns',
            )

        @admin.action(description='Respawn missing Showdown match rooms')
        def respawn_missing_match_rooms(self, request, queryset):
            self._run_showdown_action(
                request,
                queryset.filter(match__isnull=True),
                lambda c: ChallengeService.admin_respawn_match_room(
                    challenge_id=c.pk,
                    actor=request.user,
                ),
                'Respawned match rooms',
            )

    # ── Bounty Admin ─────────────────────────────────────────────────────
    class BountyClaimInline(TabularInline):
        model = BountyClaim
        extra = 0
        can_delete = False
        readonly_fields = [
            'id', 'claiming_team', 'status', 'evidence_url', 'evidence_notes',
            'claimed_by', 'claimed_at', 'verified_by', 'verified_at',
            'entry_fee_lock_txn', 'outcome_txn', 'funded_by',
            'claim_match_room_link', 'closure_reason', 'closure_note',
        ]
        fields = readonly_fields

        def has_add_permission(self, request, obj=None):
            return False

        @admin.display(description='Match room')
        def claim_match_room_link(self, obj):
            return BountyClaimAdmin.match_room_admin_link_static(obj)

    @admin.register(Bounty)
    class BountyAdmin(ModelAdmin):
        """Admin interface for Bounty."""
        
        list_display = [
            'reference_code', 'title', 'issuer_team', 'game', 'status',
            'bounty_reward_display', 'claim_count', 'max_claims',
            'escrow_state', 'created_at',
        ]
        list_filter = ['status', 'bounty_type', 'reward_type', 'game', 'is_hitlist', 'escrow_locked', 'is_featured']
        search_fields = ['reference_code', 'title', 'issuer_team__name']
        readonly_fields = [
            'id', 'reference_code', 'status', 'reward_amount_dc',
            'escrow_locked', 'issuer_lock_txn', 'funded_by', 'claim_count',
            'is_hitlist', 'challenger_entry_fee_dc', 'closure_reason',
            'closure_note', 'created_at', 'updated_at', 'escrow_state',
        ]
        raw_id_fields = ['issuer_team', 'game', 'created_by', 'issuer_lock_txn', 'funded_by']
        date_hierarchy = 'created_at'
        inlines = [BountyClaimInline]
        actions = ['void_refund_bounties', 'expire_stale_bounties_action']
        
        fieldsets = [
            ('Bounty', {
                'fields': ['id', 'reference_code', 'title', 'description', 'status', 'bounty_type']
            }),
            ('Issuer & Game', {
                'fields': ['issuer_team', 'game']
            }),
            ('Criteria', {
                'fields': ['criteria'],
                'description': 'JSON defining achievement criteria for this bounty.'
            }),
            ('Reward', {
                'fields': ['reward_type', 'reward_amount', 'reward_amount_dc', 'reward_description']
            }),
            ('Escrow & Settlement', {
                'fields': [
                    'escrow_locked', 'issuer_lock_txn', 'funded_by',
                    'is_hitlist', 'challenger_entry_fee_dc',
                    'closure_reason', 'closure_note', 'escrow_state',
                ],
                'classes': ['collapse'],
            }),
            ('Limits', {
                'fields': ['max_claims', 'claim_count', 'expires_at']
            }),
            ('Visibility', {
                'fields': ['is_public', 'is_featured']
            }),
            ('Meta', {
                'fields': ['created_by', 'created_at', 'updated_at'],
                'classes': ['collapse']
            }),
        ]

        @admin.display(description='Reward')
        def bounty_reward_display(self, obj):
            if obj.reward_amount_dc:
                return f"{obj.reward_amount_dc} DC"
            return obj.reward_description or f"{obj.reward_amount} {obj.reward_type}"

        @admin.display(description='Escrow')
        def escrow_state(self, obj):
            if not obj.is_hitlist and not obj.reward_amount_dc:
                return 'No DC lock'
            if obj.status in ('CLAIMED', 'VERIFIED', 'PAID'):
                return 'Settled/consumed'
            if obj.escrow_locked:
                return 'Issuer reward locked'
            if obj.issuer_lock_txn_id:
                return 'Issuer lock released'
            return 'No lock'

        def _run_bounty_action(self, request, queryset, callback, success_label):
            success_count = 0
            error_count = 0
            for bounty in queryset:
                try:
                    callback(bounty)
                    success_count += 1
                except Exception as exc:
                    error_count += 1
                    self.message_user(
                        request,
                        f"{bounty.reference_code}: {exc}",
                        level=messages.ERROR,
                    )
            if success_count:
                self.message_user(request, f"{success_label}: {success_count}", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed: {error_count}", level=messages.WARNING)

        @admin.action(description='Void/refund selected Bounties')
        def void_refund_bounties(self, request, queryset):
            self._run_bounty_action(
                request,
                queryset,
                lambda b: BountyService.admin_void_refund_bounty(
                    bounty_id=b.pk,
                    resolved_by=request.user,
                    note=f"Voided/refunded from Django admin by {request.user.username}.",
                ),
                'Voided/refunded Bounties',
            )

        @admin.action(description='Expire selected stale Bounties')
        def expire_stale_bounties_action(self, request, queryset):
            self._run_bounty_action(
                request,
                queryset,
                lambda b: BountyService.admin_expire_bounty(
                    bounty_id=b.pk,
                    actor=request.user,
                    note=f"Expired from Django admin by {request.user.username}.",
                ),
                'Expired stale Bounties',
            )

    @admin.register(BountyClaim)
    class BountyClaimAdmin(ModelAdmin):
        """Admin interface for BountyClaim."""
        
        list_display = [
            'bounty', 'claiming_team', 'status', 'claim_escrow_state',
            'match_room_admin_link', 'linked_match_result_state', 'claimed_at', 'verified_at',
        ]
        list_filter = ['status', 'bounty__status', 'bounty__game', 'bounty__is_hitlist']
        search_fields = ['bounty__reference_code', 'claiming_team__name']
        readonly_fields = [
            'id', 'bounty', 'claiming_team', 'status', 'claimed_by',
            'claimed_at', 'verified_at', 'verified_by', 'entry_fee_lock_txn',
            'outcome_txn', 'funded_by', 'match', 'challenge', 'match_report',
            'closure_reason', 'closure_note', 'admin_notes',
            'match_room_admin_link', 'linked_match_result_state',
        ]
        raw_id_fields = [
            'bounty', 'claiming_team', 'claimed_by', 'verified_by',
            'challenge', 'match_report', 'entry_fee_lock_txn',
            'outcome_txn', 'funded_by', 'match',
        ]
        date_hierarchy = 'claimed_at'
        actions = [
            'approve_pending_claims',
            'reject_pending_claims',
            'respawn_missing_claim_match_rooms',
        ]

        fieldsets = [
            ('Claim', {
                'fields': ['id', 'bounty', 'claiming_team', 'status']
            }),
            ('Evidence', {
                'fields': ['evidence_url', 'evidence_notes']
            }),
            ('Review', {
                'fields': ['verified_by', 'verified_at', 'admin_notes', 'closure_reason', 'closure_note']
            }),
            ('Escrow & Settlement', {
                'fields': ['entry_fee_lock_txn', 'outcome_txn', 'funded_by'],
                'classes': ['collapse'],
            }),
            ('Match Room', {
                'fields': ['match', 'match_room_admin_link', 'linked_match_result_state', 'challenge', 'match_report'],
                'classes': ['collapse'],
            }),
            ('Submission', {
                'fields': ['claimed_by', 'claimed_at'],
                'classes': ['collapse'],
            }),
        ]

        @staticmethod
        def match_room_admin_link_static(obj):
            if not obj or not obj.match_id or not getattr(obj.match, 'tournament_id', None):
                return '—'
            tournament = getattr(obj.match, 'tournament', None)
            if not tournament or not getattr(tournament, 'slug', ''):
                return '—'
            try:
                url = reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': obj.match_id})
            except NoReverseMatch:
                return '—'
            return format_html('<a href="{}" target="_blank">Open room</a>', url)

        @admin.display(description='Match room')
        def match_room_admin_link(self, obj):
            return self.match_room_admin_link_static(obj)

        @admin.display(description='Linked match result')
        def linked_match_result_state(self, obj):
            match = getattr(obj, 'match', None) or getattr(getattr(obj, 'challenge', None), 'match', None)
            return _linked_match_result_admin_summary(match)

        @admin.display(description='Escrow')
        def claim_escrow_state(self, obj):
            if obj.outcome_txn_id:
                return 'Settled'
            if obj.entry_fee_lock_txn_id:
                return 'Entry locked'
            return 'No claim lock'

        def _run_claim_action(self, request, queryset, callback, success_label):
            success_count = 0
            error_count = 0
            for claim in queryset:
                try:
                    callback(claim)
                    success_count += 1
                except Exception as exc:
                    error_count += 1
                    self.message_user(
                        request,
                        f"{claim.pk}: {exc}",
                        level=messages.ERROR,
                    )
            if success_count:
                self.message_user(request, f"{success_label}: {success_count}", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed: {error_count}", level=messages.WARNING)

        @admin.action(description='Approve/verify selected pending Bounty claims')
        def approve_pending_claims(self, request, queryset):
            self._run_claim_action(
                request,
                queryset,
                lambda c: BountyService.admin_verify_claim(
                    claim_id=c.pk,
                    verified_by=request.user,
                    notes=f"Approved from Django admin by {request.user.username}.",
                ),
                'Approved Bounty claims',
            )

        @admin.action(description='Reject selected pending Bounty claims')
        def reject_pending_claims(self, request, queryset):
            self._run_claim_action(
                request,
                queryset,
                lambda c: BountyService.admin_reject_claim(
                    claim_id=c.pk,
                    verified_by=request.user,
                    notes=f"Rejected from Django admin by {request.user.username}.",
                ),
                'Rejected Bounty claims',
            )

        @admin.action(description='Respawn missing Bounty claim match rooms')
        def respawn_missing_claim_match_rooms(self, request, queryset):
            self._run_claim_action(
                request,
                queryset.filter(match__isnull=True),
                lambda c: BountyService.admin_respawn_claim_match_room(
                    claim_id=c.pk,
                    actor=request.user,
                ),
                'Respawned Bounty claim match rooms',
            )
