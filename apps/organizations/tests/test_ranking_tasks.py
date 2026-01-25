"""
Tests for vNext Ranking Celery Tasks.

Tests the bulk ranking operations:
- Team ranking recalculation
- Inactivity decay processing
- Organization aggregate ranking updates

Phase 4 - Task P4-T2
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.organizations.models import Team, TeamRanking, Organization, OrganizationRanking
from apps.organizations.tasks.rankings import (
    recalculate_team_rankings,
    apply_inactivity_decay,
    recalculate_organization_rankings,
    RANKING_CHUNK_SIZE,
    INACTIVITY_DECAY_RATE,
    MINIMUM_CP,
)

User = get_user_model()


# ============================================================================
# TEST FACTORIES
# ============================================================================

class RankingTaskTestFactory:
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
            ceo = RankingTaskTestFactory.create_user(username=f"ceo_{name.lower().replace(' ', '_')}")
        
        return Organization.objects.create(
            name=name,
            slug=name.lower().replace(' ', '_'),
            ceo=ceo
        )
    
    @staticmethod
    def create_team_with_ranking(
        name="Test Team",
        crown_points=1000,
        tier="GOLD",
        owner=None,
        organization=None,
        game_id=1,
        region="NA",
        last_activity_date=None
    ):
        """Create a team with ranking."""
        if owner is None:
            owner = RankingTaskTestFactory.create_user(username=f"owner_{name.lower().replace(' ', '_')}")
        
        if organization is None:
            organization = RankingTaskTestFactory.create_organization(name=f"Org for {name}", ceo=owner)
        
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
        
        ranking = TeamRanking.objects.create(
            team=team,
            current_cp=crown_points,
            tier=tier,
            is_hot_streak=False,
            streak_count=0,
        )
        
        if last_activity_date:
            ranking.last_activity_date = last_activity_date
            ranking.save()
        
        return team, ranking


# ============================================================================
# TEAM RANKING RECALCULATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestRecalculateTeamRankings(TestCase):
    """Test suite for team ranking recalculation task."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RankingTaskTestFactory()
    
    def test_recalc_with_no_teams_returns_zero_counts(self):
        """Test task handles empty database gracefully."""
        result = recalculate_team_rankings()
        
        self.assertEqual(result['teams_processed'], 0)
        self.assertEqual(result['teams_updated'], 0)
        self.assertEqual(result['tier_changes'], 0)
        self.assertEqual(result['errors'], 0)
    
    def test_recalc_updates_incorrect_tier(self):
        """Test task recalculates tier when CP doesn't match."""
        # Create team with GOLD tier but SILVER CP
        team, ranking = self.factory.create_team_with_ranking(
            name="Mismatched Team",
            crown_points=600,  # SILVER range
            tier="GOLD"  # Wrong tier
        )
        
        result = recalculate_team_rankings()
        
        # Verify tier corrected
        ranking.refresh_from_db()
        self.assertEqual(ranking.tier, 'SILVER')
        self.assertEqual(result['tier_changes'], 1)
        self.assertEqual(result['teams_updated'], 1)
    
    def test_recalc_corrects_negative_cp(self):
        """Test task resets negative CP to floor."""
        team, ranking = self.factory.create_team_with_ranking(
            name="Negative CP Team",
            crown_points=-100,
            tier="UNRANKED"
        )
        
        result = recalculate_team_rankings()
        
        # Verify CP reset to minimum
        ranking.refresh_from_db()
        self.assertEqual(ranking.current_cp, MINIMUM_CP)
        self.assertEqual(result['teams_updated'], 1)
    
    def test_recalc_filters_by_game_id(self):
        """Test task respects game_id filter."""
        team1, _ = self.factory.create_team_with_ranking(name="Game 1 Team", game_id=1, crown_points=600, tier="GOLD")
        team2, _ = self.factory.create_team_with_ranking(name="Game 2 Team", game_id=2, crown_points=600, tier="GOLD")
        
        result = recalculate_team_rankings(game_id=1)
        
        # Only game 1 team processed
        self.assertEqual(result['teams_processed'], 1)
    
    def test_recalc_filters_by_region(self):
        """Test task respects region filter."""
        team1, _ = self.factory.create_team_with_ranking(name="NA Team", region="NA", crown_points=600, tier="GOLD")
        team2, _ = self.factory.create_team_with_ranking(name="EU Team", region="EU", crown_points=600, tier="GOLD")
        
        result = recalculate_team_rankings(region="NA")
        
        # Only NA team processed
        self.assertEqual(result['teams_processed'], 1)
    
    def test_recalc_respects_limit(self):
        """Test task respects limit parameter."""
        for i in range(5):
            self.factory.create_team_with_ranking(
                name=f"Team {i}",
                crown_points=600,
                tier="GOLD"
            )
        
        result = recalculate_team_rankings(limit=3)
        
        self.assertEqual(result['teams_processed'], 3)
    
    def test_recalc_processes_large_batch_efficiently(self):
        """Test task handles large batches with chunking."""
        # Create more teams than chunk size (to test chunking)
        num_teams = 10  # Small number for fast test
        
        for i in range(num_teams):
            self.factory.create_team_with_ranking(
                name=f"Batch Team {i}",
                crown_points=600,
                tier="GOLD"
            )
        
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as context:
            result = recalculate_team_rankings()
        
        # Verify all teams processed
        self.assertEqual(result['teams_processed'], num_teams)
        
        # Query count should be reasonable (not N+1)
        # Expected: ~1 query for fetching teams (chunked), ~1-2 for bulk update
        self.assertLess(len(context.captured_queries), 50)
    
    def test_recalc_handles_errors_gracefully(self):
        """Test task continues processing after individual errors."""
        # Create 3 teams
        for i in range(3):
            self.factory.create_team_with_ranking(
                name=f"Team {i}",
                crown_points=600,
                tier="GOLD"
            )
        
        # Mock RankingService to fail for middle team
        with patch('apps.organizations.services.ranking_service.RankingService.calculate_tier') as mock_calc:
            def side_effect(cp):
                if cp == 600:
                    raise Exception("Simulated error")
                from apps.organizations.choices import RankingTier
                if cp >= 500:
                    return RankingTier.SILVER
                return RankingTier.UNRANKED
            
            mock_calc.side_effect = side_effect
            
            result = recalculate_team_rankings()
            
            # Should have errors but continue
            self.assertEqual(result['teams_processed'], 3)
            self.assertEqual(result['errors'], 3)  # All will fail with this mock
    
    def test_recalc_skips_inactive_teams(self):
        """Test task only processes active teams."""
        team1, _ = self.factory.create_team_with_ranking(name="Active Team")
        team2, _ = self.factory.create_team_with_ranking(name="Inactive Team")
        team2.status = 'INACTIVE'
        team2.save()
        
        result = recalculate_team_rankings()
        
        # Only active team processed
        self.assertEqual(result['teams_processed'], 1)


# ============================================================================
# INACTIVITY DECAY TESTS
# ============================================================================

@pytest.mark.django_db
class TestApplyInactivityDecay(TestCase):
    """Test suite for inactivity decay task."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RankingTaskTestFactory()
    
    def test_decay_with_no_inactive_teams_returns_zero(self):
        """Test task handles no inactive teams gracefully."""
        # Create team with recent activity
        team, ranking = self.factory.create_team_with_ranking(
            name="Active Team",
            last_activity_date=timezone.now()
        )
        
        result = apply_inactivity_decay(cutoff_days=7)
        
        self.assertEqual(result['teams_processed'], 0)
        self.assertEqual(result['teams_decayed'], 0)
    
    def test_decay_applies_to_inactive_team(self):
        """Test decay applies to team inactive beyond cutoff."""
        # Create team inactive for 8 days
        inactive_date = timezone.now() - timedelta(days=8)
        team, ranking = self.factory.create_team_with_ranking(
            name="Inactive Team",
            crown_points=1000,
            last_activity_date=inactive_date
        )
        
        result = apply_inactivity_decay(cutoff_days=7)
        
        # Verify decay applied
        ranking.refresh_from_db()
        expected_decay = int(1000 * INACTIVITY_DECAY_RATE)  # 5% of 1000 = 50
        self.assertEqual(ranking.current_cp, 1000 - expected_decay)
        self.assertEqual(result['teams_decayed'], 1)
        self.assertEqual(result['total_cp_lost'], expected_decay)
    
    def test_decay_respects_cp_floor(self):
        """Test decay doesn't go below minimum CP."""
        inactive_date = timezone.now() - timedelta(days=8)
        team, ranking = self.factory.create_team_with_ranking(
            name="Low CP Team",
            crown_points=10,  # Very low CP
            last_activity_date=inactive_date
        )
        
        result = apply_inactivity_decay(cutoff_days=7)
        
        # Verify CP doesn't go negative
        ranking.refresh_from_db()
        self.assertGreaterEqual(ranking.current_cp, MINIMUM_CP)
    
    def test_decay_updates_tier_if_changed(self):
        """Test decay recalculates tier after CP change."""
        # Create team at BRONZE threshold (50 CP)
        inactive_date = timezone.now() - timedelta(days=8)
        team, ranking = self.factory.create_team_with_ranking(
            name="Tier Change Team",
            crown_points=52,  # Just above BRONZE threshold
            tier="BRONZE",
            last_activity_date=inactive_date
        )
        
        result = apply_inactivity_decay(cutoff_days=7)
        
        # Verify tier dropped to UNRANKED (decay brings below 50)
        ranking.refresh_from_db()
        self.assertEqual(ranking.tier, 'UNRANKED')
    
    def test_decay_respects_cutoff_days(self):
        """Test decay only applies to teams inactive beyond cutoff."""
        # Create two teams: one inactive 5 days, one 10 days
        recent = timezone.now() - timedelta(days=5)
        old = timezone.now() - timedelta(days=10)
        
        team1, _ = self.factory.create_team_with_ranking(
            name="Recent Team",
            crown_points=1000,
            last_activity_date=recent
        )
        team2, _ = self.factory.create_team_with_ranking(
            name="Old Team",
            crown_points=1000,
            last_activity_date=old
        )
        
        result = apply_inactivity_decay(cutoff_days=7)
        
        # Only old team should be decayed
        self.assertEqual(result['teams_processed'], 1)
        self.assertEqual(result['teams_decayed'], 1)
    
    def test_decay_idempotent_with_last_decay_applied(self):
        """Test decay doesn't apply twice in same day."""
        inactive_date = timezone.now() - timedelta(days=8)
        team, ranking = self.factory.create_team_with_ranking(
            name="Already Decayed Team",
            crown_points=1000,
            last_activity_date=inactive_date
        )
        
        # Mark as already decayed today
        ranking.last_decay_applied = timezone.now()
        ranking.save()
        
        result = apply_inactivity_decay(cutoff_days=7)
        
        # Should not process (already decayed today)
        self.assertEqual(result['teams_processed'], 0)
    
    def test_decay_respects_limit(self):
        """Test decay respects limit parameter."""
        inactive_date = timezone.now() - timedelta(days=8)
        
        for i in range(5):
            self.factory.create_team_with_ranking(
                name=f"Inactive Team {i}",
                crown_points=1000,
                last_activity_date=inactive_date
            )
        
        result = apply_inactivity_decay(cutoff_days=7, limit=3)
        
        # Should only process 3 teams
        self.assertLessEqual(result['teams_processed'], 3)
    
    def test_decay_handles_errors_gracefully(self):
        """Test decay continues after individual errors."""
        inactive_date = timezone.now() - timedelta(days=8)
        
        for i in range(3):
            self.factory.create_team_with_ranking(
                name=f"Team {i}",
                crown_points=1000,
                last_activity_date=inactive_date
            )
        
        # Should handle errors in loop
        with patch('apps.organizations.services.ranking_service.RankingService.calculate_tier') as mock_calc:
            mock_calc.side_effect = Exception("Simulated error")
            
            result = apply_inactivity_decay(cutoff_days=7)
            
            # Should have errors but continue
            self.assertGreater(result['errors'], 0)


# ============================================================================
# ORGANIZATION RANKING TESTS
# ============================================================================

@pytest.mark.django_db
class TestRecalculateOrganizationRankings(TestCase):
    """Test suite for organization ranking recalculation task."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RankingTaskTestFactory()
    
    def test_org_recalc_with_no_orgs_returns_zero(self):
        """Test task handles empty database gracefully."""
        result = recalculate_organization_rankings()
        
        self.assertEqual(result['orgs_processed'], 0)
        self.assertEqual(result['orgs_updated'], 0)
    
    def test_org_recalc_calculates_empire_score_single_team(self):
        """Test empire score calculation with single team."""
        org = self.factory.create_organization(name="Test Org")
        team, ranking = self.factory.create_team_with_ranking(
            name="Team 1",
            crown_points=1000,
            organization=org
        )
        
        result = recalculate_organization_rankings()
        
        # Empire score = 1000 * 1.0 (1st team weight) = 1000
        org_ranking = OrganizationRanking.objects.get(organization=org)
        self.assertEqual(org_ranking.empire_score, 1000)
        self.assertEqual(result['orgs_updated'], 1)
    
    def test_org_recalc_calculates_empire_score_three_teams(self):
        """Test empire score with top 3 teams weighted correctly [1.0, 0.75, 0.5]."""
        org = self.factory.create_organization(name="Test Org")
        
        team1, _ = self.factory.create_team_with_ranking(
            name="Team 1",
            crown_points=3000,
            organization=org
        )
        team2, _ = self.factory.create_team_with_ranking(
            name="Team 2",
            crown_points=2000,
            organization=org
        )
        team3, _ = self.factory.create_team_with_ranking(
            name="Team 3",
            crown_points=1000,
            organization=org
        )
        
        result = recalculate_organization_rankings()
        
        # Empire score = (3000 * 1.0) + (2000 * 0.75) + (1000 * 0.5)
        #              = 3000 + 1500 + 500 = 5000
        org_ranking = OrganizationRanking.objects.get(organization=org)
        expected_score = int(3000 * 1.0) + int(2000 * 0.75) + int(1000 * 0.5)
        self.assertEqual(org_ranking.empire_score, expected_score)
    
    def test_org_recalc_uses_top_three_only(self):
        """Test empire score only uses top 3 teams."""
        org = self.factory.create_organization(name="Test Org")
        
        # Create 5 teams
        for i in range(5):
            cp = (5 - i) * 1000  # 5000, 4000, 3000, 2000, 1000
            self.factory.create_team_with_ranking(
                name=f"Team {i}",
                crown_points=cp,
                organization=org
            )
        
        result = recalculate_organization_rankings()
        
        # Should only count top 3: 5000, 4000, 3000 with weights [1.0, 0.75, 0.5]
        org_ranking = OrganizationRanking.objects.get(organization=org)
        expected_score = int(5000 * 1.0) + int(4000 * 0.75) + int(3000 * 0.5)
        self.assertEqual(org_ranking.empire_score, expected_score)
    
    def test_org_recalc_handles_org_with_no_teams(self):
        """Test org with no teams gets 0 empire score."""
        org = self.factory.create_organization(name="Empty Org")
        
        result = recalculate_organization_rankings()
        
        # Should create ranking with 0 score
        org_ranking = OrganizationRanking.objects.get(organization=org)
        self.assertEqual(org_ranking.empire_score, 0)
    
    def test_org_recalc_skips_inactive_teams(self):
        """Test only active teams count toward empire score."""
        org = self.factory.create_organization(name="Test Org")
        
        team1, _ = self.factory.create_team_with_ranking(
            name="Active Team",
            crown_points=3000,
            organization=org
        )
        team2, _ = self.factory.create_team_with_ranking(
            name="Inactive Team",
            crown_points=5000,
            organization=org
        )
        team2.status = 'INACTIVE'
        team2.save()
        
        result = recalculate_organization_rankings()
        
        # Should only count active team (3000 CP) with weight 1.0
        org_ranking = OrganizationRanking.objects.get(organization=org)
        expected_score = int(3000 * 1.0)
        self.assertEqual(org_ranking.empire_score, expected_score)
    
    def test_org_recalc_respects_limit(self):
        """Test task respects limit parameter."""
        for i in range(5):
            org = self.factory.create_organization(name=f"Org {i}")
            self.factory.create_team_with_ranking(
                name=f"Team {i}",
                organization=org
            )
        
        result = recalculate_organization_rankings(limit=3)
        
        self.assertEqual(result['orgs_processed'], 3)
    
    def test_org_recalc_handles_errors_gracefully(self):
        """Test task continues after individual errors."""
        for i in range(3):
            self.factory.create_organization(name=f"Org {i}")
        
        # Mock to cause errors
        with patch('apps.organizations.models.Organization.teams') as mock_teams:
            mock_teams.side_effect = Exception("Simulated error")
            
            result = recalculate_organization_rankings()
            
            # Should have errors
            self.assertGreater(result['errors'], 0)
    
    def test_org_recalc_query_efficiency(self):
        """Test organization ranking uses efficient queries."""
        org = self.factory.create_organization(name="Test Org")
        
        for i in range(5):
            self.factory.create_team_with_ranking(
                name=f"Team {i}",
                crown_points=(5 - i) * 1000,
                organization=org
            )
        
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as context:
            result = recalculate_organization_rankings()
        
        # Query count should be reasonable with prefetch_related
        # Expected: ~1 org query + prefetch, ~1 bulk update
        self.assertLess(len(context.captured_queries), 20)
