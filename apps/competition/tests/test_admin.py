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
    )
    from apps.competition.models import (
        GameRankingConfig,
        MatchReport,
        MatchVerification,
        TeamGameRankingSnapshot,
        TeamGlobalRankingSnapshot,
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
