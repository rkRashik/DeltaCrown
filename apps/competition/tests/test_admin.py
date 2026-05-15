"""Minimal tests for competition app admin (Phase 3A-B)."""
import pytest
from django.contrib.admin.sites import AdminSite


# Check schema readiness before importing admin classes
try:
    from apps.competition.apps import COMPETITION_SCHEMA_READY
except ImportError:
    COMPETITION_SCHEMA_READY = False


if COMPETITION_SCHEMA_READY:
    from apps.competition.admin import (
        GameRankingConfigAdmin,
        MatchReportAdmin,
        MatchVerificationAdmin,
        TeamGameRankingSnapshotAdmin,
        TeamGlobalRankingSnapshotAdmin,
        ChallengeAdmin,
        BountyAdmin,
        BountyClaimAdmin,
    )
    from apps.competition.models import (
        GameRankingConfig,
        MatchReport,
        MatchVerification,
        TeamGameRankingSnapshot,
        TeamGlobalRankingSnapshot,
        Challenge,
        Bounty,
        BountyClaim,
    )


@pytest.mark.skipif(not COMPETITION_SCHEMA_READY, reason="Competition schema not ready")
@pytest.mark.django_db
class TestCompetitionAdmin:
    """Test competition app admin registrations."""
    
    def test_game_ranking_config_admin_registered(self):
        """Should have GameRankingConfigAdmin registered."""
        site = AdminSite()
        admin_instance = GameRankingConfigAdmin(GameRankingConfig, site)
        
        assert admin_instance.list_display == ['game_id', 'game_name', 'is_active', 'updated_at']
        assert 'is_active' in admin_instance.list_filter
    
    def test_match_report_admin_registered(self):
        """Should have MatchReportAdmin registered."""
        site = AdminSite()
        admin_instance = MatchReportAdmin(MatchReport, site)
        
        assert 'game_id' in admin_instance.list_display
        assert 'match_type' in admin_instance.list_filter
    
    def test_match_verification_admin_registered(self):
        """Should have MatchVerificationAdmin registered."""
        site = AdminSite()
        admin_instance = MatchVerificationAdmin(MatchVerification, site)
        
        assert 'status' in admin_instance.list_display
        assert 'confidence_level' in admin_instance.list_filter
        # Actions can be strings or functions, check both formats
        action_names = [getattr(action, '__name__', action) for action in admin_instance.actions]
        assert 'mark_as_admin_verified' in action_names
    
    def test_team_game_ranking_snapshot_admin_registered(self):
        """Should have TeamGameRankingSnapshotAdmin registered."""
        site = AdminSite()
        admin_instance = TeamGameRankingSnapshotAdmin(TeamGameRankingSnapshot, site)
        
        assert 'team' in admin_instance.list_display
        assert 'game_id' in admin_instance.list_filter
    
    def test_team_global_ranking_snapshot_admin_registered(self):
        """Should have TeamGlobalRankingSnapshotAdmin registered."""
        site = AdminSite()
        admin_instance = TeamGlobalRankingSnapshotAdmin(TeamGlobalRankingSnapshot, site)
        
        assert 'team' in admin_instance.list_display
        assert 'global_tier' in admin_instance.list_filter

    def test_challenge_admin_protects_lifecycle_and_escrow_fields(self):
        """Showdown admin should expose service actions and protect direct edits."""
        site = AdminSite()
        admin_instance = ChallengeAdmin(Challenge, site)

        action_names = [getattr(action, '__name__', action) for action in admin_instance.actions]
        assert 'settle_confirmed_showdowns' in action_names
        assert 'resolve_disputes_as_challenger_win' in action_names
        assert 'void_refund_showdowns' in action_names
        assert 'respawn_missing_match_rooms' in action_names

        for field in [
            'status',
            'result',
            'score_details',
            'escrow_locked',
            'challenger_lock_txn',
            'challenged_lock_txn',
            'payout_txn',
            'settled_at',
            'closure_reason',
            'closure_note',
        ]:
            assert field in admin_instance.readonly_fields

    def test_bounty_admin_protects_lifecycle_and_escrow_fields(self):
        """Bounty admin should expose service actions and protect direct edits."""
        site = AdminSite()
        admin_instance = BountyAdmin(Bounty, site)

        action_names = [getattr(action, '__name__', action) for action in admin_instance.actions]
        assert 'void_refund_bounties' in action_names
        assert 'expire_stale_bounties_action' in action_names

        for field in [
            'status',
            'reward_amount_dc',
            'escrow_locked',
            'issuer_lock_txn',
            'funded_by',
            'claim_count',
            'closure_reason',
            'closure_note',
        ]:
            assert field in admin_instance.readonly_fields

    def test_bounty_claim_admin_protects_lifecycle_and_escrow_fields(self):
        """Bounty claim admin should verify/reject through service-backed actions."""
        site = AdminSite()
        admin_instance = BountyClaimAdmin(BountyClaim, site)

        action_names = [getattr(action, '__name__', action) for action in admin_instance.actions]
        assert 'approve_pending_claims' in action_names
        assert 'reject_pending_claims' in action_names
        assert 'respawn_missing_claim_match_rooms' in action_names

        for field in [
            'status',
            'verified_by',
            'verified_at',
            'entry_fee_lock_txn',
            'outcome_txn',
            'funded_by',
            'match',
            'closure_reason',
            'closure_note',
        ]:
            assert field in admin_instance.readonly_fields
