"""
Tests for Match Result Integration Service.

Tests the compatibility layer that bridges match completion events
to the vNext ranking system while maintaining legacy compatibility.

Phase 4 - Task P4-T1
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from apps.organizations.models import Team, TeamRanking, Organization
from apps.organizations.services.match_integration import (
    MatchResultIntegrator,
    MatchIntegrationResult
)
from apps.organizations.services.ranking_service import RankingService

User = get_user_model()


# ============================================================================
# TEST FACTORIES
# ============================================================================

class MatchIntegrationTestFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_user(username="testuser", email=None):
        """Create a test user."""
        if email is None:
            email = f"{username}@test.com"
        return User.objects.create_user(username=username, email=email, password="testpass123")
    
    @staticmethod
    def create_organization(name="Test Org", ceo=None):
        """Create a test organization."""
        if ceo is None:
            ceo = MatchIntegrationTestFactory.create_user(username=f"ceo_{name.lower().replace(' ', '_')}")
        
        return Organization.objects.create(
            name=name,
            slug=name.lower().replace(' ', '_'),
            ceo=ceo
        )
    
    @staticmethod
    def create_vnext_team(name="Test Team", owner=None, organization=None, game_id=1, region="NA"):
        """Create a vNext team with ranking."""
        if owner is None:
            owner = MatchIntegrationTestFactory.create_user(username=f"owner_{name.lower().replace(' ', '_')}")
        
        if organization is None:
            organization = MatchIntegrationTestFactory.create_organization(name=f"Org for {name}", ceo=owner)
        
        team = Team.objects.create(
            name=name,
            slug=name.lower().replace(' ', '_'),
            owner=owner,
            organization=organization,
            game_id=game_id,
            region=region,
            status='ACTIVE',
            max_size=5
        )
        
        # Create ranking
        TeamRanking.objects.create(
            team=team,
            current_cp=1000,  # Default to GOLD tier
            tier='GOLD',
            is_hot_streak=False,
            consecutive_wins=0,
            consecutive_losses=0,
            total_matches=0,
            total_wins=0,
            total_losses=0
        )
        
        return team


# ============================================================================
# TEST CASES
# ============================================================================

@pytest.mark.django_db
class TestMatchResultIntegrator(TestCase):
    """Test suite for MatchResultIntegrator."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = MatchIntegrationTestFactory()
        self.winner_team = self.factory.create_vnext_team(name="Winner Team", game_id=1, region="NA")
        self.loser_team = self.factory.create_vnext_team(name="Loser Team", game_id=1, region="NA")
    
    # ========================================================================
    # FEATURE FLAG TESTS
    # ========================================================================
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_is_vnext_enabled_returns_true_when_enabled(self):
        """Test feature flag check returns True when enabled."""
        self.assertTrue(MatchResultIntegrator.is_vnext_enabled())
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=False)
    def test_is_vnext_enabled_returns_false_when_disabled(self):
        """Test feature flag check returns False when disabled."""
        self.assertFalse(MatchResultIntegrator.is_vnext_enabled())
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=True)
    def test_is_vnext_enabled_returns_false_when_force_legacy(self):
        """Test feature flag check returns False when force legacy enabled."""
        self.assertFalse(MatchResultIntegrator.is_vnext_enabled())
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=False)
    def test_process_match_result_skips_when_disabled(self):
        """Test match processing skips vNext when feature flag disabled."""
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=self.winner_team.id,
            loser_team_id=self.loser_team.id,
            match_id=1,
            is_tournament_match=False
        )
        
        self.assertTrue(result.success)
        self.assertFalse(result.vnext_processed)
        self.assertFalse(result.legacy_processed)
    
    # ========================================================================
    # TEAM TYPE DETECTION TESTS
    # ========================================================================
    
    def test_is_vnext_team_returns_true_for_vnext_team(self):
        """Test team type detection returns True for vNext teams."""
        self.assertTrue(MatchResultIntegrator.is_vnext_team(self.winner_team.id))
    
    def test_is_vnext_team_returns_false_for_nonexistent_team(self):
        """Test team type detection returns False for non-existent teams."""
        self.assertFalse(MatchResultIntegrator.is_vnext_team(999999))
    
    def test_get_team_types_returns_both_vnext(self):
        """Test team type detection returns both True for vNext-only match."""
        winner_is_vnext, loser_is_vnext = MatchResultIntegrator.get_team_types(
            self.winner_team.id,
            self.loser_team.id
        )
        self.assertTrue(winner_is_vnext)
        self.assertTrue(loser_is_vnext)
    
    def test_get_team_types_returns_mixed_for_mixed_match(self):
        """Test team type detection returns mixed for vNext vs legacy."""
        # Winner is vNext, loser is non-existent (simulates legacy)
        winner_is_vnext, loser_is_vnext = MatchResultIntegrator.get_team_types(
            self.winner_team.id,
            999999  # Non-existent team
        )
        self.assertTrue(winner_is_vnext)
        self.assertFalse(loser_is_vnext)
    
    # ========================================================================
    # MATCH PROCESSING TESTS
    # ========================================================================
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_process_match_result_updates_vnext_rankings(self):
        """Test match processing updates vNext team rankings correctly."""
        # Get initial CP values
        winner_ranking = TeamRanking.objects.get(team=self.winner_team)
        loser_ranking = TeamRanking.objects.get(team=self.loser_team)
        initial_winner_cp = winner_ranking.current_cp
        initial_loser_cp = loser_ranking.current_cp
        
        # Process match result
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=self.winner_team.id,
            loser_team_id=self.loser_team.id,
            match_id=1,
            is_tournament_match=False
        )
        
        # Verify result
        self.assertTrue(result.success)
        self.assertTrue(result.vnext_processed)
        self.assertIsNone(result.error_message)
        
        # Verify rankings updated
        winner_ranking.refresh_from_db()
        loser_ranking.refresh_from_db()
        
        self.assertGreater(winner_ranking.current_cp, initial_winner_cp, "Winner CP should increase")
        self.assertLess(loser_ranking.current_cp, initial_loser_cp, "Loser CP should decrease")
        self.assertEqual(winner_ranking.total_wins, 1, "Winner total_wins should be 1")
        self.assertEqual(loser_ranking.total_losses, 1, "Loser total_losses should be 1")
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_process_match_result_detects_tier_changes(self):
        """Test match processing detects tier changes."""
        # Set loser to 51 CP (just above BRONZE threshold)
        loser_ranking = TeamRanking.objects.get(team=self.loser_team)
        loser_ranking.current_cp = 51
        loser_ranking.tier = 'BRONZE'
        loser_ranking.save()
        
        # Process match (loser will drop to 26 CP -> UNRANKED)
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=self.winner_team.id,
            loser_team_id=self.loser_team.id,
            match_id=1,
            is_tournament_match=False
        )
        
        # Verify tier change detected
        self.assertTrue(result.loser_tier_changed)
        
        # Verify tier actually changed
        loser_ranking.refresh_from_db()
        self.assertEqual(loser_ranking.tier, 'UNRANKED')
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_process_match_result_detects_hot_streak(self):
        """Test match processing detects hot streak activation."""
        # Set winner to 2 consecutive wins
        winner_ranking = TeamRanking.objects.get(team=self.winner_team)
        winner_ranking.consecutive_wins = 2
        winner_ranking.is_hot_streak = False
        winner_ranking.save()
        
        # Process match (3rd win triggers hot streak)
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=self.winner_team.id,
            loser_team_id=self.loser_team.id,
            match_id=1,
            is_tournament_match=False
        )
        
        # Verify hot streak activated
        winner_ranking.refresh_from_db()
        self.assertTrue(winner_ranking.is_hot_streak)
        self.assertEqual(winner_ranking.consecutive_wins, 3)
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_process_match_result_skips_mixed_matches(self):
        """Test match processing skips vNext vs legacy matches (Phase 4 limitation)."""
        # Process match with non-existent loser (simulates legacy team)
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=self.winner_team.id,
            loser_team_id=999999,  # Non-existent team
            match_id=1,
            is_tournament_match=False
        )
        
        # Verify mixed match skipped
        self.assertTrue(result.success)
        self.assertFalse(result.vnext_processed)
        
        # Verify winner ranking not updated (mixed matches not supported)
        winner_ranking = TeamRanking.objects.get(team=self.winner_team)
        self.assertEqual(winner_ranking.total_wins, 0)
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_process_match_result_skips_neither_vnext(self):
        """Test match processing skips when neither team is vNext."""
        # Process match with two non-existent teams (simulates legacy-only match)
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=999998,
            loser_team_id=999999,
            match_id=1,
            is_tournament_match=False
        )
        
        # Verify skipped correctly
        self.assertTrue(result.success)
        self.assertFalse(result.vnext_processed)
    
    # ========================================================================
    # ERROR HANDLING TESTS
    # ========================================================================
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_process_match_result_handles_missing_team_gracefully(self):
        """Test match processing handles missing teams gracefully."""
        # Process match with non-existent teams
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=999998,
            loser_team_id=999999,
            match_id=1,
            is_tournament_match=False
        )
        
        # Verify handled gracefully (not an error, just skipped)
        self.assertTrue(result.success)
        self.assertFalse(result.vnext_processed)
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    @patch('apps.organizations.services.match_integration.RankingService.apply_match_result')
    def test_process_match_result_handles_ranking_service_errors(self, mock_apply):
        """Test match processing handles RankingService errors gracefully."""
        # Mock RankingService to raise exception
        mock_apply.side_effect = Exception("Database error")
        
        # Process match
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=self.winner_team.id,
            loser_team_id=self.loser_team.id,
            match_id=1,
            is_tournament_match=False
        )
        
        # Verify error captured
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Database error", result.error_message)
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_process_match_result_meets_query_budget(self):
        """Test match processing stays within query budget (≤5 queries)."""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as context:
            result = MatchResultIntegrator.process_match_result(
                winner_team_id=self.winner_team.id,
                loser_team_id=self.loser_team.id,
                match_id=1,
                is_tournament_match=False
            )
        
        query_count = len(context.captured_queries)
        self.assertTrue(result.success)
        self.assertLessEqual(
            query_count,
            5,
            f"Query count {query_count} exceeds budget of 5. Queries: {[q['sql'] for q in context.captured_queries]}"
        )
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_process_match_result_meets_latency_target(self):
        """Test match processing completes within 100ms target."""
        result = MatchResultIntegrator.process_match_result(
            winner_team_id=self.winner_team.id,
            loser_team_id=self.loser_team.id,
            match_id=1,
            is_tournament_match=False
        )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.processing_time_ms)
        self.assertLess(
            result.processing_time_ms,
            100,
            f"Processing time {result.processing_time_ms}ms exceeds 100ms target"
        )


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestMatchIntegrationEndToEnd(TestCase):
    """End-to-end integration tests."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = MatchIntegrationTestFactory()
    
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=True, TEAM_VNEXT_FORCE_LEGACY=False)
    def test_multiple_matches_update_rankings_correctly(self):
        """Test multiple consecutive matches update rankings correctly."""
        team_a = self.factory.create_vnext_team(name="Team A", game_id=1, region="NA")
        team_b = self.factory.create_vnext_team(name="Team B", game_id=1, region="NA")
        
        # Match 1: A beats B
        result1 = MatchResultIntegrator.process_match_result(
            winner_team_id=team_a.id,
            loser_team_id=team_b.id,
            match_id=1,
            is_tournament_match=False
        )
        self.assertTrue(result1.success)
        
        # Match 2: A beats B again
        result2 = MatchResultIntegrator.process_match_result(
            winner_team_id=team_a.id,
            loser_team_id=team_b.id,
            match_id=2,
            is_tournament_match=False
        )
        self.assertTrue(result2.success)
        
        # Match 3: A beats B again (hot streak!)
        result3 = MatchResultIntegrator.process_match_result(
            winner_team_id=team_a.id,
            loser_team_id=team_b.id,
            match_id=3,
            is_tournament_match=False
        )
        self.assertTrue(result3.success)
        
        # Verify Team A has hot streak
        ranking_a = TeamRanking.objects.get(team=team_a)
        self.assertTrue(ranking_a.is_hot_streak)
        self.assertEqual(ranking_a.consecutive_wins, 3)
        self.assertEqual(ranking_a.total_wins, 3)
        
        # Verify Team B lost all
        ranking_b = TeamRanking.objects.get(team=team_b)
        self.assertEqual(ranking_b.total_losses, 3)
        self.assertEqual(ranking_b.consecutive_losses, 3)
