# tests/test_team_ranking_integration.py
"""
Integration tests for Team Ranking System with other apps

Tests cover:
1. Tournament integration
2. Team membership integration  
3. Signal handling
4. Cross-app data consistency
5. Performance with large datasets
"""
import pytest
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.test.utils import override_settings

from apps.organizations.models import (
    Team, TeamMembership, RankingCriteria, 
    TeamRankingHistory, TeamRankingBreakdown
)
from apps.teams.services.ranking_service import ranking_service
from apps.user_profile.models import UserProfile

User = get_user_model()


class RankingIntegrationTestCase(TransactionTestCase):
    """Base integration test case."""
    
    def setUp(self):
        """Set up comprehensive test data."""
        # Create users
        self.users = []
        for i in range(10):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            profile = UserProfile.objects.create(user=user)
            self.users.append({'user': user, 'profile': profile})
        
        # Create teams with different ages and member counts
        self.teams = []
        
        # Team 1: Old team, many members
        team1 = Team.objects.create(
            name='Veteran Squad',
            tag='VET',
            game='valorant',
            captain=self.users[0]['profile'],
            created_at=timezone.now() - timedelta(days=300)  # 10 months old
        )
        
        # Add 5 members to team1
        for i in range(5):
            TeamMembership.objects.create(
                team=team1,
                profile=self.users[i]['profile'],
                role='CAPTAIN' if i == 0 else 'MEMBER',
                status='ACTIVE'
            )
        
        self.teams.append(team1)
        
        # Team 2: New team, few members  
        team2 = Team.objects.create(
            name='Fresh Faces',
            tag='FRESH',
            game='valorant',
            captain=self.users[5]['profile'],
            created_at=timezone.now() - timedelta(days=30)  # 1 month old
        )
        
        # Add 2 members to team2
        for i in range(5, 7):
            TeamMembership.objects.create(
                team=team2,
                profile=self.users[i]['profile'],
                role='CAPTAIN' if i == 5 else 'MEMBER',
                status='ACTIVE'
            )
        
        self.teams.append(team2)
        
        # Team 3: Different game
        team3 = Team.objects.create(
            name='EFootball Pros',
            tag='EFP',
            game='efootball',
            captain=self.users[7]['profile'],
            created_at=timezone.now() - timedelta(days=60)  # 2 months old
        )
        
        # Add 3 members to team3
        for i in range(7, 10):
            TeamMembership.objects.create(
                team=team3,
                profile=self.users[i]['profile'],
                role='CAPTAIN' if i == 7 else 'MEMBER',
                status='ACTIVE'
            )
        
        self.teams.append(team3)
        
        # Create ranking criteria
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


class TeamMembershipIntegrationTestCase(RankingIntegrationTestCase):
    """Test integration with team membership changes."""
    
    def test_member_addition_updates_points(self):
        """Test that adding members updates team points automatically."""
        team = self.teams[0]  # Veteran Squad
        
        # Calculate initial points
        ranking_service.recalculate_team_points(team)
        team.refresh_from_db()
        initial_points = team.total_points
        
        # Get initial member count points
        breakdown = TeamRankingBreakdown.objects.get(team=team)
        initial_member_points = breakdown.member_count_points
        
        # Add a new member
        new_user = User.objects.create_user(
            username='newmember',
            email='new@example.com',
            password='testpass123'
        )
        new_profile = UserProfile.objects.create(user=new_user)
        
        # Create membership (this should trigger signal)
        TeamMembership.objects.create(
            team=team,
            profile=new_profile,
            role='MEMBER',
            status='ACTIVE'
        )
        
        # Points should be updated automatically via signals
        team.refresh_from_db()
        new_points = team.total_points
        
        # Should have gained 10 points (1 member * 10 points_per_member)
        expected_increase = self.criteria.points_per_member
        self.assertEqual(new_points, initial_points + expected_increase)
        
        # Check breakdown updated
        breakdown.refresh_from_db()
        new_member_points = breakdown.member_count_points
        self.assertEqual(new_member_points, initial_member_points + expected_increase)
    
    def test_member_removal_updates_points(self):
        """Test that removing members updates team points."""
        team = self.teams[0]  # Veteran Squad (has 5 members)
        
        # Calculate initial points
        ranking_service.recalculate_team_points(team)
        team.refresh_from_db()
        initial_points = team.total_points
        
        # Remove a member (change status to inactive)
        membership = TeamMembership.objects.filter(
            team=team, 
            role='MEMBER'
        ).first()
        membership.status = 'INACTIVE'
        membership.save()
        
        # Points should be updated automatically
        team.refresh_from_db()
        new_points = team.total_points
        
        # Should have lost 10 points
        expected_decrease = self.criteria.points_per_member
        self.assertEqual(new_points, initial_points - expected_decrease)
    
    def test_member_role_change_no_point_impact(self):
        """Test that changing member roles doesn't affect points."""
        team = self.teams[0]
        
        ranking_service.recalculate_team_points(team)
        team.refresh_from_db()
        initial_points = team.total_points
        
        # Change a member's role
        membership = TeamMembership.objects.filter(
            team=team,
            role='MEMBER'
        ).first()
        membership.role = 'CO_CAPTAIN'
        membership.save()
        
        # Points should remain the same (role doesn't affect points)
        team.refresh_from_db()
        self.assertEqual(team.total_points, initial_points)


class TournamentIntegrationTestCase(RankingIntegrationTestCase):
    """Test tournament integration."""
    
    def setUp(self):
        super().setUp()
        # Create mock tournament data
        self.mock_tournaments = [
            {'id': 1, 'name': 'Valorant Championship', 'game': 'valorant'},
            {'id': 2, 'name': 'EFootball Cup', 'game': 'efootball'},
        ]
    
    def test_tournament_participation_award(self):
        """Test awarding points for tournament participation."""
        team = self.teams[0]  # Veteran Squad
        tournament = type('Tournament', (), self.mock_tournaments[0])()
        
        # Initial calculation
        ranking_service.recalculate_team_points(team)
        team.refresh_from_db()
        initial_points = team.total_points
        
        # Award participation points
        result = ranking_service.award_tournament_points(
            team=team,
            tournament=tournament,
            achievement_type='participation'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['points_awarded'], 50)
        
        # Check points updated
        team.refresh_from_db()
        expected_points = initial_points + 50
        self.assertEqual(team.total_points, expected_points)
        
        # Check breakdown
        breakdown = TeamRankingBreakdown.objects.get(team=team)
        self.assertEqual(breakdown.tournament_participation_points, 50)
        
        # Check history record created
        history = TeamRankingHistory.objects.filter(
            team=team,
            source='tournament_award'
        ).latest('created_at')
        self.assertEqual(history.points_change, 50)
        self.assertIn('participation', history.reason.lower())
    
    def test_tournament_winner_award(self):
        """Test awarding points for tournament victory."""
        team = self.teams[1]  # Fresh Faces
        tournament = type('Tournament', (), self.mock_tournaments[0])()
        
        ranking_service.recalculate_team_points(team)
        team.refresh_from_db()
        initial_points = team.total_points
        
        # Award winner points
        result = ranking_service.award_tournament_points(
            team=team,
            tournament=tournament,
            achievement_type='winner'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['points_awarded'], 500)
        
        # Check total points
        team.refresh_from_db()
        expected_points = initial_points + 500
        self.assertEqual(team.total_points, expected_points)
        
        # Check breakdown
        breakdown = TeamRankingBreakdown.objects.get(team=team)
        self.assertEqual(breakdown.tournament_winner_points, 500)
    
    def test_multiple_tournament_awards(self):
        """Test multiple tournament awards accumulate correctly."""
        team = self.teams[0]
        tournament1 = type('Tournament', (), self.mock_tournaments[0])()
        tournament2 = type('Tournament', (), self.mock_tournaments[1])()
        
        ranking_service.recalculate_team_points(team)
        team.refresh_from_db()
        initial_points = team.total_points
        
        # Award participation in first tournament
        ranking_service.award_tournament_points(
            team=team,
            tournament=tournament1,
            achievement_type='participation'
        )
        
        # Award top 4 in second tournament
        ranking_service.award_tournament_points(
            team=team,
            tournament=tournament2,
            achievement_type='top_4'
        )
        
        # Check total accumulated points
        team.refresh_from_db()
        expected_total = initial_points + 50 + 150  # participation + top_4
        self.assertEqual(team.total_points, expected_total)
        
        # Check breakdown shows both awards
        breakdown = TeamRankingBreakdown.objects.get(team=team)
        self.assertEqual(breakdown.tournament_participation_points, 50)
        self.assertEqual(breakdown.tournament_top_4_points, 150)


class SignalIntegrationTestCase(RankingIntegrationTestCase):
    """Test signal integration and automatic updates."""
    
    def test_criteria_update_triggers_recalculation(self):
        """Test that updating criteria triggers team recalculation."""
        # Calculate initial points for all teams
        for team in self.teams:
            ranking_service.recalculate_team_points(team)
        
        # Store initial points
        initial_points = {}
        for team in self.teams:
            team.refresh_from_db()
            initial_points[team.id] = team.total_points
        
        # Update criteria (increase points per member)
        self.criteria.points_per_member = 20  # Was 10
        self.criteria.save()
        
        # All teams should have updated points
        for team in self.teams:
            team.refresh_from_db()
            
            # Get member count
            member_count = TeamMembership.objects.filter(
                team=team, 
                status='ACTIVE'
            ).count()
            
            # Expected increase: member_count * (20 - 10) = member_count * 10
            expected_increase = member_count * 10
            expected_total = initial_points[team.id] + expected_increase
            
            self.assertEqual(team.total_points, expected_total)
    
    def test_team_creation_initializes_breakdown(self):
        """Test that creating a new team initializes its breakdown."""
        # Create new team
        new_user = User.objects.create_user(
            username='newteamcaptain',
            email='captain@example.com',
            password='testpass123'
        )
        new_profile = UserProfile.objects.create(user=new_user)
        
        new_team = Team.objects.create(
            name='Signal Test Team',
            tag='STT',
            game='valorant',
            captain=new_profile
        )
        
        # Add captain as member
        TeamMembership.objects.create(
            team=new_team,
            profile=new_profile,
            role='CAPTAIN',
            status='ACTIVE'
        )
        
        # Breakdown should be created automatically (via signals or first calculation)
        # Let's trigger a calculation to ensure it works
        ranking_service.recalculate_team_points(new_team)
        
        # Check breakdown exists
        breakdown = TeamRankingBreakdown.objects.get(team=new_team)
        self.assertIsNotNone(breakdown)
        self.assertGreater(breakdown.final_total, 0)


class PerformanceTestCase(RankingIntegrationTestCase):
    """Test performance with larger datasets."""
    
    def test_bulk_recalculation_performance(self):
        """Test bulk recalculation performance."""
        import time
        
        # Create additional teams for performance testing
        extra_teams = []
        for i in range(20):  # Create 20 more teams
            user = User.objects.create_user(
                username=f'perfuser{i}',
                email=f'perf{i}@example.com',
                password='testpass123'
            )
            profile = UserProfile.objects.create(user=user)
            
            team = Team.objects.create(
                name=f'Performance Team {i}',
                tag=f'PT{i}',
                game='valorant' if i % 2 == 0 else 'efootball',
                captain=profile,
                created_at=timezone.now() - timedelta(days=i*10)
            )
            
            # Add random number of members (1-5)
            member_count = (i % 5) + 1
            for j in range(member_count):
                if j == 0:
                    # Captain
                    TeamMembership.objects.create(
                        team=team,
                        profile=profile,
                        role='CAPTAIN',
                        status='ACTIVE'
                    )
                else:
                    # Additional members
                    member_user = User.objects.create_user(
                        username=f'perfmember{i}_{j}',
                        email=f'perfmember{i}_{j}@example.com',
                        password='testpass123'
                    )
                    member_profile = UserProfile.objects.create(user=member_user)
                    TeamMembership.objects.create(
                        team=team,
                        profile=member_profile,
                        role='MEMBER',
                        status='ACTIVE'
                    )
            
            extra_teams.append(team)
        
        all_teams = self.teams + extra_teams
        
        # Time bulk recalculation
        start_time = time.time()
        
        for team in all_teams:
            ranking_service.recalculate_team_points(team)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertion (should complete in reasonable time)
        # 23 teams should calculate in under 5 seconds
        self.assertLess(duration, 5.0)
        
        print(f"Bulk recalculation of {len(all_teams)} teams took {duration:.2f} seconds")
        
        # Verify all teams have valid points
        for team in all_teams:
            team.refresh_from_db()
            self.assertGreaterEqual(team.total_points, 0)
            
            # Verify breakdown exists
            breakdown = TeamRankingBreakdown.objects.get(team=team)
            self.assertIsNotNone(breakdown)
    
    def test_ranking_query_performance(self):
        """Test performance of ranking queries."""
        import time
        
        # Calculate points for all teams first
        for team in self.teams:
            ranking_service.recalculate_team_points(team)
        
        # Time ranking queries
        start_time = time.time()
        
        # Get top 10 rankings
        rankings = ranking_service.get_team_rankings(limit=10)
        
        # Get game-specific rankings
        valorant_rankings = ranking_service.get_team_rankings(game='valorant')
        efootball_rankings = ranking_service.get_team_rankings(game='efootball')
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertion
        self.assertLess(duration, 1.0)  # Should complete under 1 second
        
        print(f"Ranking queries took {duration:.3f} seconds")
        
        # Verify results
        self.assertGreater(len(rankings), 0)
        self.assertGreater(len(valorant_rankings), 0)
        self.assertGreater(len(efootball_rankings), 0)


class DataConsistencyTestCase(RankingIntegrationTestCase):
    """Test data consistency across operations."""
    
    def test_breakdown_totals_match_team_points(self):
        """Test that breakdown totals always match team.total_points."""
        # Calculate points for all teams
        for team in self.teams:
            ranking_service.recalculate_team_points(team)
        
        # Check consistency for each team
        for team in self.teams:
            team.refresh_from_db()
            breakdown = TeamRankingBreakdown.objects.get(team=team)
            
            # Team total should match breakdown final total
            self.assertEqual(team.total_points, breakdown.final_total)
            
            # Breakdown final total should equal calculated + manual adjustments
            expected_final = breakdown.calculated_total + breakdown.manual_adjustments
            self.assertEqual(breakdown.final_total, expected_final)
    
    def test_history_audit_trail_complete(self):
        """Test that all point changes are recorded in history."""
        team = self.teams[0]
        
        # Initial calculation
        ranking_service.recalculate_team_points(team)
        initial_history_count = TeamRankingHistory.objects.filter(team=team).count()
        
        # Manual adjustment
        ranking_service.adjust_team_points(
            team=team,
            points_adjustment=50,
            reason="Test adjustment"
        )
        
        # Tournament award
        tournament = type('Tournament', (), {'id': 1, 'name': 'Test Tournament'})()
        ranking_service.award_tournament_points(
            team=team,
            tournament=tournament,
            achievement_type='participation'
        )
        
        # Check history records
        final_history_count = TeamRankingHistory.objects.filter(team=team).count()
        
        # Should have at least 3 new records (initial + adjustment + tournament)
        self.assertGreaterEqual(final_history_count, initial_history_count + 2)
        
        # Verify audit trail completeness
        history_records = TeamRankingHistory.objects.filter(team=team).order_by('created_at')
        
        # Each record should have valid data
        for record in history_records:
            self.assertIsNotNone(record.source)
            self.assertIsNotNone(record.points_before)
            self.assertIsNotNone(record.points_after)
            # points_after should equal points_before + points_change
            self.assertEqual(
                record.points_after, 
                record.points_before + record.points_change
            )


if __name__ == '__main__':
    # Run integration tests
    import sys
    import subprocess
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', __file__, '-v'
        ], capture_output=True, text=True)
        
        print("INTEGRATION TEST OUTPUT:")
        print(result.stdout)
        if result.stderr:
            print("ERRORS:")
            print(result.stderr)
            
        print(f"Integration Tests {'PASSED' if result.returncode == 0 else 'FAILED'}")
        
    except Exception as e:
        print(f"Error running integration tests: {e}")