"""
Tests for Leaderboard Service.

Tests the unified leaderboard compatibility layer that merges
vNext and legacy team rankings.

Phase 4 - Task P4-T1
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from apps.organizations.models import Team, TeamRanking, Organization
from apps.organizations.services.leaderboard_service import (
    LeaderboardService,
    LeaderboardEntry
)

User = get_user_model()


# ============================================================================
# TEST FACTORIES
# ============================================================================

class LeaderboardTestFactory:
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
            ceo = LeaderboardTestFactory.create_user(username=f"ceo_{name.lower().replace(' ', '_')}")
        
        return Organization.objects.create(
            name=name,
            slug=name.lower().replace(' ', '_'),
            ceo=ceo
        )
    
    @staticmethod
    def create_vnext_team(name="Test Team", crown_points=1000, tier="GOLD", owner=None, organization=None, game_id=1, region="NA"):
        """Create a vNext team with ranking."""
        if owner is None:
            owner = LeaderboardTestFactory.create_user(username=f"owner_{name.lower().replace(' ', '_')}")
        
        if organization is None:
            organization = LeaderboardTestFactory.create_organization(name=f"Org for {name}", ceo=owner)
        
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
            current_cp=crown_points,
            tier=tier,
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
class TestLeaderboardService(TestCase):
    """Test suite for LeaderboardService."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = LeaderboardTestFactory()
    
    # ========================================================================
    # TIER CALCULATION TESTS
    # ========================================================================
    
    def test_calculate_legacy_tier_crown(self):
        """Test tier calculation for CROWN tier."""
        self.assertEqual(LeaderboardService.calculate_legacy_tier(80000), 'CROWN')
        self.assertEqual(LeaderboardService.calculate_legacy_tier(100000), 'CROWN')
    
    def test_calculate_legacy_tier_ascendant(self):
        """Test tier calculation for ASCENDANT tier."""
        self.assertEqual(LeaderboardService.calculate_legacy_tier(40000), 'ASCENDANT')
        self.assertEqual(LeaderboardService.calculate_legacy_tier(60000), 'ASCENDANT')
    
    def test_calculate_legacy_tier_diamond(self):
        """Test tier calculation for DIAMOND tier."""
        self.assertEqual(LeaderboardService.calculate_legacy_tier(15000), 'DIAMOND')
        self.assertEqual(LeaderboardService.calculate_legacy_tier(30000), 'DIAMOND')
    
    def test_calculate_legacy_tier_platinum(self):
        """Test tier calculation for PLATINUM tier."""
        self.assertEqual(LeaderboardService.calculate_legacy_tier(5000), 'PLATINUM')
        self.assertEqual(LeaderboardService.calculate_legacy_tier(10000), 'PLATINUM')
    
    def test_calculate_legacy_tier_gold(self):
        """Test tier calculation for GOLD tier."""
        self.assertEqual(LeaderboardService.calculate_legacy_tier(1500), 'GOLD')
        self.assertEqual(LeaderboardService.calculate_legacy_tier(3000), 'GOLD')
    
    def test_calculate_legacy_tier_silver(self):
        """Test tier calculation for SILVER tier."""
        self.assertEqual(LeaderboardService.calculate_legacy_tier(500), 'SILVER')
        self.assertEqual(LeaderboardService.calculate_legacy_tier(1000), 'SILVER')
    
    def test_calculate_legacy_tier_bronze(self):
        """Test tier calculation for BRONZE tier."""
        self.assertEqual(LeaderboardService.calculate_legacy_tier(50), 'BRONZE')
        self.assertEqual(LeaderboardService.calculate_legacy_tier(400), 'BRONZE')
    
    def test_calculate_legacy_tier_unranked(self):
        """Test tier calculation for UNRANKED tier."""
        self.assertEqual(LeaderboardService.calculate_legacy_tier(0), 'UNRANKED')
        self.assertEqual(LeaderboardService.calculate_legacy_tier(49), 'UNRANKED')
    
    # ========================================================================
    # TEAM URL ROUTING TESTS
    # ========================================================================
    
    def test_get_team_url_vnext(self):
        """Test URL generation for vNext teams."""
        url = LeaderboardService.get_team_url(
            team_id=1,
            team_slug="test_team",
            is_vnext=True
        )
        self.assertEqual(url, "/teams/test_team/")
    
    def test_get_team_url_legacy(self):
        """Test URL generation for legacy teams."""
        url = LeaderboardService.get_team_url(
            team_id=1,
            team_slug="test_team",
            is_vnext=False
        )
        self.assertEqual(url, "/teams/test_team/")
    
    # ========================================================================
    # vNEXT TEAM QUERIES
    # ========================================================================
    
    def test_get_vnext_teams_returns_active_teams(self):
        """Test vNext team query returns only active teams."""
        active_team = self.factory.create_vnext_team(name="Active Team", crown_points=2000)
        inactive_team = self.factory.create_vnext_team(name="Inactive Team", crown_points=1500)
        inactive_team.status = 'INACTIVE'
        inactive_team.save()
        
        teams = LeaderboardService.get_vnext_teams(limit=10)
        
        # Should only include active team
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0]['team_id'], active_team.id)
    
    def test_get_vnext_teams_filters_by_game(self):
        """Test vNext team query filters by game_id."""
        team_game1 = self.factory.create_vnext_team(name="Game 1 Team", game_id=1)
        team_game2 = self.factory.create_vnext_team(name="Game 2 Team", game_id=2)
        
        teams = LeaderboardService.get_vnext_teams(game_id=1, limit=10)
        
        # Should only include game 1 team
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0]['team_id'], team_game1.id)
    
    def test_get_vnext_teams_filters_by_region(self):
        """Test vNext team query filters by region."""
        team_na = self.factory.create_vnext_team(name="NA Team", region="NA")
        team_eu = self.factory.create_vnext_team(name="EU Team", region="EU")
        
        teams = LeaderboardService.get_vnext_teams(region="NA", limit=10)
        
        # Should only include NA team
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0]['team_id'], team_na.id)
    
    def test_get_vnext_teams_orders_by_cp_desc(self):
        """Test vNext team query orders by crown_points descending."""
        team_low = self.factory.create_vnext_team(name="Low CP Team", crown_points=500)
        team_high = self.factory.create_vnext_team(name="High CP Team", crown_points=5000)
        team_mid = self.factory.create_vnext_team(name="Mid CP Team", crown_points=2000)
        
        teams = LeaderboardService.get_vnext_teams(limit=10)
        
        # Should be ordered high -> mid -> low
        self.assertEqual(len(teams), 3)
        self.assertEqual(teams[0]['team_id'], team_high.id)
        self.assertEqual(teams[1]['team_id'], team_mid.id)
        self.assertEqual(teams[2]['team_id'], team_low.id)
    
    def test_get_vnext_teams_respects_limit(self):
        """Test vNext team query respects limit parameter."""
        # Create 5 teams
        for i in range(5):
            self.factory.create_vnext_team(name=f"Team {i}", crown_points=1000 + i * 100)
        
        teams = LeaderboardService.get_vnext_teams(limit=3)
        
        # Should only return 3 teams
        self.assertEqual(len(teams), 3)
    
    def test_get_vnext_teams_returns_correct_data_structure(self):
        """Test vNext team query returns correct DTO structure."""
        team = self.factory.create_vnext_team(name="Test Team", crown_points=2500, tier="GOLD")
        
        teams = LeaderboardService.get_vnext_teams(limit=1)
        
        self.assertEqual(len(teams), 1)
        team_data = teams[0]
        
        # Verify all required fields present
        self.assertEqual(team_data['team_id'], team.id)
        self.assertEqual(team_data['team_name'], "Test Team")
        self.assertEqual(team_data['team_slug'], "test_team")
        self.assertEqual(team_data['crown_points'], 2500)
        self.assertEqual(team_data['tier'], "GOLD")
        self.assertEqual(team_data['game_id'], 1)
        self.assertEqual(team_data['region'], "NA")
        self.assertTrue(team_data['is_vnext'])
    
    # ========================================================================
    # LEGACY TEAM QUERIES (MOCKED)
    # ========================================================================
    
    @patch('apps.organizations.services.leaderboard_service.LegacyTeam')
    def test_get_legacy_teams_returns_empty_when_not_available(self, mock_legacy_team):
        """Test legacy team query returns empty list when model not available."""
        # Simulate ImportError
        with patch('apps.organizations.services.leaderboard_service.LegacyTeam', side_effect=ImportError):
            teams = LeaderboardService.get_legacy_teams(limit=10)
            self.assertEqual(len(teams), 0)
    
    # ========================================================================
    # UNIFIED LEADERBOARD TESTS
    # ========================================================================
    
    def test_get_unified_leaderboard_returns_vnext_teams(self):
        """Test unified leaderboard returns vNext teams."""
        team1 = self.factory.create_vnext_team(name="Team 1", crown_points=3000)
        team2 = self.factory.create_vnext_team(name="Team 2", crown_points=2000)
        
        entries = LeaderboardService.get_unified_leaderboard(limit=10, include_legacy=False)
        
        self.assertEqual(len(entries), 2)
        self.assertIsInstance(entries[0], LeaderboardEntry)
        self.assertEqual(entries[0].team_id, team1.id)
        self.assertEqual(entries[1].team_id, team2.id)
    
    def test_get_unified_leaderboard_sorts_by_cp_desc(self):
        """Test unified leaderboard sorts by crown_points descending."""
        team_low = self.factory.create_vnext_team(name="Low CP", crown_points=1000)
        team_high = self.factory.create_vnext_team(name="High CP", crown_points=5000)
        team_mid = self.factory.create_vnext_team(name="Mid CP", crown_points=3000)
        
        entries = LeaderboardService.get_unified_leaderboard(limit=10, include_legacy=False)
        
        # Should be sorted high -> mid -> low
        self.assertEqual(entries[0].crown_points, 5000)
        self.assertEqual(entries[1].crown_points, 3000)
        self.assertEqual(entries[2].crown_points, 1000)
    
    def test_get_unified_leaderboard_assigns_ranks_correctly(self):
        """Test unified leaderboard assigns 1-based ranks."""
        self.factory.create_vnext_team(name="Team 1", crown_points=3000)
        self.factory.create_vnext_team(name="Team 2", crown_points=2000)
        self.factory.create_vnext_team(name="Team 3", crown_points=1000)
        
        entries = LeaderboardService.get_unified_leaderboard(limit=10, include_legacy=False)
        
        self.assertEqual(entries[0].rank, 1)
        self.assertEqual(entries[1].rank, 2)
        self.assertEqual(entries[2].rank, 3)
    
    def test_get_unified_leaderboard_respects_limit(self):
        """Test unified leaderboard respects limit parameter."""
        for i in range(10):
            self.factory.create_vnext_team(name=f"Team {i}", crown_points=1000 + i * 100)
        
        entries = LeaderboardService.get_unified_leaderboard(limit=5, include_legacy=False)
        
        self.assertEqual(len(entries), 5)
    
    def test_get_unified_leaderboard_filters_by_game(self):
        """Test unified leaderboard filters by game_id."""
        team_game1 = self.factory.create_vnext_team(name="Game 1 Team", game_id=1, crown_points=2000)
        team_game2 = self.factory.create_vnext_team(name="Game 2 Team", game_id=2, crown_points=3000)
        
        entries = LeaderboardService.get_unified_leaderboard(game_id=1, limit=10, include_legacy=False)
        
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].team_id, team_game1.id)
    
    def test_get_unified_leaderboard_filters_by_region(self):
        """Test unified leaderboard filters by region."""
        team_na = self.factory.create_vnext_team(name="NA Team", region="NA", crown_points=2000)
        team_eu = self.factory.create_vnext_team(name="EU Team", region="EU", crown_points=3000)
        
        entries = LeaderboardService.get_unified_leaderboard(region="NA", limit=10, include_legacy=False)
        
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].team_id, team_na.id)
    
    def test_get_unified_leaderboard_includes_team_urls(self):
        """Test unified leaderboard includes correct team URLs."""
        team = self.factory.create_vnext_team(name="Test Team", crown_points=2000)
        
        entries = LeaderboardService.get_unified_leaderboard(limit=1, include_legacy=False)
        
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].team_url, "/teams/test_team/")
    
    def test_get_unified_leaderboard_marks_vnext_teams(self):
        """Test unified leaderboard marks vNext teams correctly."""
        team = self.factory.create_vnext_team(name="Test Team", crown_points=2000)
        
        entries = LeaderboardService.get_unified_leaderboard(limit=1, include_legacy=False)
        
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].is_vnext)
    
    def test_get_vnext_only_leaderboard_convenience_method(self):
        """Test vNext-only convenience method works correctly."""
        team = self.factory.create_vnext_team(name="Test Team", crown_points=2000)
        
        entries = LeaderboardService.get_vnext_only_leaderboard(limit=10)
        
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].is_vnext)
    
    def test_format_for_template_converts_to_dicts(self):
        """Test format_for_template converts DTOs to dicts."""
        team = self.factory.create_vnext_team(name="Test Team", crown_points=2000)
        entries = LeaderboardService.get_unified_leaderboard(limit=1, include_legacy=False)
        
        dicts = LeaderboardService.format_for_template(entries)
        
        self.assertEqual(len(dicts), 1)
        self.assertIsInstance(dicts[0], dict)
        self.assertEqual(dicts[0]['team_name'], "Test Team")
        self.assertEqual(dicts[0]['crown_points'], 2000)
        self.assertTrue(dicts[0]['is_vnext'])
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    def test_get_unified_leaderboard_meets_query_budget(self):
        """Test leaderboard generation stays within query budget (≤5 queries)."""
        # Create multiple teams
        for i in range(5):
            self.factory.create_vnext_team(name=f"Team {i}", crown_points=1000 + i * 100)
        
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as context:
            entries = LeaderboardService.get_unified_leaderboard(limit=10, include_legacy=False)
        
        query_count = len(context.captured_queries)
        self.assertLessEqual(
            query_count,
            5,
            f"Query count {query_count} exceeds budget of 5. Queries: {[q['sql'] for q in context.captured_queries]}"
        )
    
    def test_get_unified_leaderboard_performance(self):
        """Test leaderboard generation performance."""
        import time
        
        # Create 50 teams (realistic load)
        for i in range(50):
            self.factory.create_vnext_team(name=f"Team {i}", crown_points=1000 + i * 100)
        
        start_time = time.time()
        entries = LeaderboardService.get_unified_leaderboard(limit=50, include_legacy=False)
        elapsed_ms = (time.time() - start_time) * 1000
        
        self.assertEqual(len(entries), 50)
        self.assertLess(
            elapsed_ms,
            400,
            f"Leaderboard generation took {elapsed_ms:.2f}ms, exceeds 400ms target"
        )


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.django_db
class TestLeaderboardServiceEdgeCases(TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = LeaderboardTestFactory()
    
    def test_empty_leaderboard_returns_empty_list(self):
        """Test empty leaderboard returns empty list."""
        entries = LeaderboardService.get_unified_leaderboard(limit=10, include_legacy=False)
        
        self.assertEqual(len(entries), 0)
        self.assertIsInstance(entries, list)
    
    def test_leaderboard_with_no_active_teams(self):
        """Test leaderboard with only inactive teams returns empty."""
        team = self.factory.create_vnext_team(name="Inactive Team")
        team.status = 'INACTIVE'
        team.save()
        
        entries = LeaderboardService.get_unified_leaderboard(limit=10, include_legacy=False)
        
        self.assertEqual(len(entries), 0)
    
    def test_leaderboard_with_teams_without_rankings(self):
        """Test leaderboard handles teams without rankings gracefully."""
        # Create team
        team = self.factory.create_vnext_team(name="Test Team")
        
        # Delete ranking (edge case)
        TeamRanking.objects.filter(team=team).delete()
        
        # Should not crash, just skip the team
        entries = LeaderboardService.get_unified_leaderboard(limit=10, include_legacy=False)
        
        self.assertEqual(len(entries), 0)
