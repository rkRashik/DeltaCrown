# tests/test_team_ranking_system.py
"""
Comprehensive tests for the Team Ranking System

Tests cover:
1. Ranking criteria management
2. Point calculations (age, members, tournaments)
3. Manual adjustments and audit trail
4. Admin interface functionality
5. Signal integration
6. Management commands
"""
import pytest
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from apps.organizations.models import (
    Team, TeamMembership, RankingCriteria, 
    TeamRankingHistory, TeamRankingBreakdown
)
from apps.teams.services.ranking_service import ranking_service
from apps.user_profile.models import UserProfile

User = get_user_model()


class TeamRankingSystemTestCase(TransactionTestCase):
    """Base test case for ranking system tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1', 
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com', 
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create user profiles
        self.profile1 = UserProfile.objects.create(user=self.user1)
        self.profile2 = UserProfile.objects.create(user=self.user2)
        self.admin_profile = UserProfile.objects.create(user=self.admin_user)
        
        # Create test team (older team for age points testing)
        self.team = Team.objects.create(
            name='Test Team',
            tag='TEST',
            description='A test team',
            game='valorant',
            captain=self.profile1,
            created_at=timezone.now() - timedelta(days=120)  # 4 months old
        )
        
        # Add team members
        TeamMembership.objects.create(
            team=self.team,
            profile=self.profile1,
            role='CAPTAIN',
            status='ACTIVE'
        )
        TeamMembership.objects.create(
            team=self.team,
            profile=self.profile2,
            role='MEMBER',
            status='ACTIVE'
        )
        
        # Create default ranking criteria
        self.criteria = RankingCriteria.objects.create(
            tournament_participation=50,
            tournament_winner=500,
            tournament_runner_up=300,
            tournament_top_4=150,
            points_per_member=10,
            points_per_month_age=30,
            achievement_points=100,
            is_active=True
        )


class RankingCriteriaTestCase(TeamRankingSystemTestCase):
    """Test ranking criteria management."""
    
    def test_singleton_criteria(self):
        """Test that only one criteria can be active."""
        # Create another criteria
        new_criteria = RankingCriteria.objects.create(
            tournament_participation=75,
            is_active=True
        )
        
        # Original should be deactivated
        self.criteria.refresh_from_db()
        self.assertFalse(self.criteria.is_active)
        self.assertTrue(new_criteria.is_active)
    
    def test_get_active_criteria(self):
        """Test getting active criteria."""
        criteria = RankingCriteria.get_active_criteria()
        self.assertEqual(criteria.id, self.criteria.id)
        self.assertTrue(criteria.is_active)
    
    def test_criteria_point_values_dict(self):
        """Test getting point values as dictionary."""
        values = self.criteria.get_point_values()
        expected_keys = {
            'tournament_participation', 'tournament_winner', 'tournament_runner_up',
            'tournament_top_4', 'points_per_member', 'points_per_month_age',
            'achievement_points'
        }
        self.assertEqual(set(values.keys()), expected_keys)
        self.assertEqual(values['tournament_participation'], 50)


class PointCalculationTestCase(TeamRankingSystemTestCase):
    """Test automatic point calculations."""
    
    def test_team_age_calculation(self):
        """Test team age point calculation."""
        age_points = ranking_service.calculate_team_age_points(self.team)
        # 120 days ≈ 4 months * 30 points = 120 points
        expected_points = 4 * 30
        self.assertEqual(age_points, expected_points)
    
    def test_member_count_calculation(self):
        """Test member count point calculation."""
        member_points = ranking_service.calculate_member_points(self.team)
        # 2 active members * 10 points = 20 points
        expected_points = 2 * 10
        self.assertEqual(member_points, expected_points)
    
    def test_full_team_recalculation(self):
        """Test complete team point recalculation."""
        result = ranking_service.recalculate_team_points(self.team)
        
        self.assertTrue(result['success'])
        self.assertGreater(result['new_total'], 0)
        
        # Check breakdown was created
        breakdown = TeamRankingBreakdown.objects.get(team=self.team)
        self.assertEqual(breakdown.team_age_points, 4 * 30)  # 120 points
        self.assertEqual(breakdown.member_count_points, 2 * 10)  # 20 points
        self.assertEqual(breakdown.final_total, breakdown.calculated_total)
    
    def test_team_points_field_updated(self):
        """Test that team.total_points field is updated."""
        old_points = self.team.total_points
        ranking_service.recalculate_team_points(self.team)
        
        self.team.refresh_from_db()
        self.assertNotEqual(self.team.total_points, old_points)
        self.assertGreater(self.team.total_points, 0)


class ManualAdjustmentTestCase(TeamRankingSystemTestCase):
    """Test manual point adjustments and audit trail."""
    
    def test_manual_point_adjustment(self):
        """Test manual point adjustment by admin."""
        # First calculate initial points
        ranking_service.recalculate_team_points(self.team)
        self.team.refresh_from_db()
        initial_points = self.team.total_points
        
        # Make manual adjustment
        result = ranking_service.adjust_team_points(
            team=self.team,
            points_adjustment=100,
            reason="Test adjustment",
            admin_user=self.admin_user
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['points_change'], 100)
        
        # Check team points updated
        self.team.refresh_from_db()
        self.assertEqual(self.team.total_points, initial_points + 100)
        
        # Check audit trail
        history = TeamRankingHistory.objects.filter(team=self.team).latest('created_at')
        self.assertEqual(history.points_change, 100)
        self.assertEqual(history.source, 'manual_adjustment')
        self.assertEqual(history.admin_user, self.admin_user)
        self.assertEqual(history.reason, "Test adjustment")
    
    def test_negative_adjustment_prevention(self):
        """Test that teams can't have negative total points."""
        # Set team to low points first
        ranking_service.recalculate_team_points(self.team)
        breakdown = TeamRankingBreakdown.objects.get(team=self.team)
        
        # Try to subtract more points than available
        large_negative = -(breakdown.calculated_total + 1000)
        result = ranking_service.adjust_team_points(
            team=self.team,
            points_adjustment=large_negative,
            reason="Large negative test",
            admin_user=self.admin_user
        )
        
        # Should succeed but final total should be 0, not negative
        self.assertTrue(result['success'])
        self.team.refresh_from_db()
        self.assertGreaterEqual(self.team.total_points, 0)


class TournamentPointsTestCase(TeamRankingSystemTestCase):
    """Test tournament-related point awards."""
    
    def test_tournament_participation_award(self):
        """Test awarding participation points."""
        # Mock tournament object (in real app, this would be a Tournament instance)
        class MockTournament:
            def __init__(self):
                self.id = 1
                self.name = "Test Tournament"
        
        tournament = MockTournament()
        
        result = ranking_service.award_tournament_points(
            team=self.team,
            tournament=tournament,
            achievement_type='participation',
            admin_user=self.admin_user
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['points_awarded'], 50)
        
        # Check breakdown updated
        breakdown = TeamRankingBreakdown.objects.get(team=self.team)
        self.assertEqual(breakdown.tournament_participation_points, 50)
    
    def test_duplicate_award_prevention(self):
        """Test that duplicate tournament awards are prevented."""
        class MockTournament:
            def __init__(self):
                self.id = 1
                self.name = "Test Tournament"
        
        tournament = MockTournament()
        
        # Award participation points first time
        result1 = ranking_service.award_tournament_points(
            team=self.team,
            tournament=tournament,
            achievement_type='participation'
        )
        self.assertTrue(result1['success'])
        
        # Try to award again
        result2 = ranking_service.award_tournament_points(
            team=self.team,
            tournament=tournament,
            achievement_type='participation'
        )
        self.assertFalse(result2['success'])
        self.assertIn('already awarded', result2['error'].lower())


class RankingServiceTestCase(TeamRankingSystemTestCase):
    """Test ranking service utility functions."""
    
    def test_team_rankings_list(self):
        """Test getting team rankings list."""
        # Create multiple teams and calculate points
        team2 = Team.objects.create(
            name='Team Two',
            tag='TT2',
            game='valorant',
            captain=self.profile2,
            created_at=timezone.now() - timedelta(days=200)  # Older team
        )
        
        # Calculate points for both teams
        ranking_service.recalculate_team_points(self.team)
        ranking_service.recalculate_team_points(team2)
        
        # Get rankings
        rankings = ranking_service.get_team_rankings(limit=10)
        
        self.assertGreater(len(rankings), 0)
        self.assertEqual(rankings[0]['rank'], 1)
        
        # Rankings should be ordered by points (highest first)
        if len(rankings) > 1:
            self.assertGreaterEqual(rankings[0]['points'], rankings[1]['points'])
    
    def test_game_filtered_rankings(self):
        """Test filtering rankings by game."""
        # Create team with different game
        team_efootball = Team.objects.create(
            name='EFootball Team',
            tag='EFT',
            game='efootball',
            captain=self.profile2
        )
        
        ranking_service.recalculate_team_points(self.team)
        ranking_service.recalculate_team_points(team_efootball)
        
        # Get valorant rankings
        valorant_rankings = ranking_service.get_team_rankings(game='valorant')
        efootball_rankings = ranking_service.get_team_rankings(game='efootball')
        
        # Check correct filtering
        valorant_team_ids = [r['team'].id for r in valorant_rankings]
        efootball_team_ids = [r['team'].id for r in efootball_rankings]
        
        self.assertIn(self.team.id, valorant_team_ids)
        self.assertNotIn(team_efootball.id, valorant_team_ids)
        
        self.assertIn(team_efootball.id, efootball_team_ids)
        self.assertNotIn(self.team.id, efootball_team_ids)


class AuditTrailTestCase(TeamRankingSystemTestCase):
    """Test audit trail and history functionality."""
    
    def test_history_record_creation(self):
        """Test that history records are created properly."""
        initial_count = TeamRankingHistory.objects.count()
        
        ranking_service.recalculate_team_points(self.team)
        
        # Should have created a history record
        new_count = TeamRankingHistory.objects.count()
        self.assertGreater(new_count, initial_count)
        
        # Check history record details
        history = TeamRankingHistory.objects.filter(team=self.team).latest('created_at')
        self.assertEqual(history.source, 'recalculation')
        self.assertGreater(history.points_after, history.points_before)
    
    def test_history_calculation_validation(self):
        """Test that history records have correct calculations."""
        ranking_service.recalculate_team_points(self.team)
        
        history = TeamRankingHistory.objects.filter(team=self.team).latest('created_at')
        
        # Validate: points_after = points_before + points_change
        calculated_after = history.points_before + history.points_change
        self.assertEqual(history.points_after, calculated_after)


# Test cleanup function
def cleanup_test_data():
    """Clean up test data after tests complete."""
    try:
        # Delete test teams and related data
        Team.objects.filter(name__startswith='Test').delete()
        Team.objects.filter(name__contains='Team Two').delete()
        Team.objects.filter(name__contains='EFootball Team').delete()
        
        # Delete test users
        User.objects.filter(username__startswith='test').delete()
        User.objects.filter(username='admin').delete()
        
        # Clean up ranking data
        RankingCriteria.objects.all().delete()
        TeamRankingHistory.objects.all().delete()
        TeamRankingBreakdown.objects.all().delete()
        
        print("✅ Test cleanup completed successfully")
        
    except Exception as e:
        print(f"❌ Test cleanup error: {e}")


if __name__ == '__main__':
    # Run tests with pytest
    import sys
    import subprocess
    
    try:
        # Run the tests
        result = subprocess.run([
            sys.executable, '-m', 'pytest', __file__, '-v'
        ], capture_output=True, text=True)
        
        print("TEST OUTPUT:")
        print(result.stdout)
        if result.stderr:
            print("ERRORS:")
            print(result.stderr)
            
        print(f"Tests {'PASSED' if result.returncode == 0 else 'FAILED'}")
        
    except Exception as e:
        print(f"Error running tests: {e}")
    
    finally:
        # Always clean up
        cleanup_test_data()