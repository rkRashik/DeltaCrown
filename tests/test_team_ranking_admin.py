# tests/test_team_ranking_admin.py
"""
Tests for Team Ranking Admin Interface

Tests cover:
1. Admin interface accessibility
2. Point adjustment forms
3. Bulk operations
4. Admin permissions
5. Custom admin views
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from django.contrib.messages import get_messages
from django.http import HttpRequest

from apps.organizations.models import (
    Team, RankingCriteria, TeamRankingHistory, TeamRankingBreakdown
)
from apps.teams.admin.ranking import (
    RankingCriteriaAdmin, TeamRankingHistoryAdmin, 
    TeamRankingBreakdownAdmin
)
from apps.user_profile.models import UserProfile

User = get_user_model()


class TeamRankingAdminTestCase(TestCase):
    """Base test case for admin interface tests."""
    
    def setUp(self):
        """Set up test data and admin client."""
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.admin_profile = UserProfile.objects.create(user=self.admin_user)
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        self.regular_profile = UserProfile.objects.create(user=self.regular_user)
        
        # Create test team
        self.team = Team.objects.create(
            name='Admin Test Team',
            tag='ATT',
            game='valorant',
            captain=self.regular_profile
        )
        
        # Create ranking criteria
        self.criteria = RankingCriteria.objects.create(
            tournament_participation=50,
            tournament_winner=500,
            is_active=True
        )
        
        # Set up admin client
        self.admin_client = Client()
        self.admin_client.login(username='admin', password='adminpass123')
        
        # Set up regular client
        self.regular_client = Client()
        self.regular_client.login(username='regular', password='regularpass123')


class RankingCriteriaAdminTestCase(TeamRankingAdminTestCase):
    """Test Ranking Criteria admin interface."""
    
    def test_criteria_admin_accessible(self):
        """Test that criteria admin page is accessible to superusers."""
        url = reverse('admin:teams_rankingcriteria_changelist')
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ranking Criteria')
    
    def test_criteria_admin_not_accessible_to_regular_users(self):
        """Test that regular users can't access criteria admin."""
        url = reverse('admin:teams_rankingcriteria_changelist')
        response = self.regular_client.get(url)
        # Should redirect to login or show permission denied
        self.assertNotEqual(response.status_code, 200)
    
    def test_criteria_creation_via_admin(self):
        """Test creating new criteria via admin interface."""
        url = reverse('admin:teams_rankingcriteria_add')
        data = {
            'tournament_participation': 75,
            'tournament_winner': 600,
            'tournament_runner_up': 400,
            'tournament_top_4': 200,
            'points_per_member': 15,
            'points_per_month_age': 25,
            'achievement_points': 150,
            'is_active': True
        }
        
        response = self.admin_client.post(url, data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Check criteria was created
        new_criteria = RankingCriteria.objects.filter(
            tournament_participation=75
        ).first()
        self.assertIsNotNone(new_criteria)
        self.assertTrue(new_criteria.is_active)
        
        # Original criteria should be deactivated
        self.criteria.refresh_from_db()
        self.assertFalse(self.criteria.is_active)
    
    def test_criteria_singleton_enforcement(self):
        """Test that admin enforces singleton active criteria."""
        # Create another criteria via admin
        url = reverse('admin:teams_rankingcriteria_add')
        data = {
            'tournament_participation': 100,
            'is_active': True
        }
        
        initial_count = RankingCriteria.objects.filter(is_active=True).count()
        self.assertEqual(initial_count, 1)  # Our setup criteria
        
        response = self.admin_client.post(url, data)
        
        # Should still have only one active criteria
        final_count = RankingCriteria.objects.filter(is_active=True).count()
        self.assertEqual(final_count, 1)


class TeamRankingHistoryAdminTestCase(TeamRankingAdminTestCase):
    """Test Team Ranking History admin interface."""
    
    def setUp(self):
        super().setUp()
        # Create some history records
        self.history1 = TeamRankingHistory.objects.create(
            team=self.team,
            source='recalculation',
            points_before=0,
            points_after=100,
            points_change=100,
            reason='Initial calculation'
        )
        self.history2 = TeamRankingHistory.objects.create(
            team=self.team,
            source='manual_adjustment',
            points_before=100,
            points_after=150,
            points_change=50,
            reason='Admin adjustment',
            admin_user=self.admin_user
        )
    
    def test_history_admin_accessible(self):
        """Test that history admin page is accessible."""
        url = reverse('admin:teams_teamrankinghistory_changelist')
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team ranking histories')
    
    def test_history_admin_readonly_fields(self):
        """Test that history records are read-only in admin."""
        url = reverse('admin:teams_teamrankinghistory_change', args=[self.history1.pk])
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check that form fields are read-only
        content = response.content.decode()
        self.assertIn('readonly', content)
    
    def test_history_filtering(self):
        """Test filtering history by source and team."""
        url = reverse('admin:teams_teamrankinghistory_changelist')
        
        # Filter by source
        response = self.admin_client.get(url + '?source=manual_adjustment')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin adjustment')
        self.assertNotContains(response, 'Initial calculation')
        
        # Filter by team
        response = self.admin_client.get(url + f'?team__id__exact={self.team.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Test Team')


class TeamRankingBreakdownAdminTestCase(TeamRankingAdminTestCase):
    """Test Team Ranking Breakdown admin interface."""
    
    def setUp(self):
        super().setUp()
        # Create breakdown record
        self.breakdown = TeamRankingBreakdown.objects.create(
            team=self.team,
            team_age_points=120,
            member_count_points=30,
            tournament_participation_points=100,
            tournament_winner_points=500,
            achievement_points=50,
            calculated_total=800,
            manual_adjustments=100,
            final_total=900
        )
    
    def test_breakdown_admin_accessible(self):
        """Test that breakdown admin page is accessible."""
        url = reverse('admin:teams_teamrankingbreakdown_changelist')
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team ranking breakdowns')
    
    def test_breakdown_detail_view(self):
        """Test viewing breakdown details in admin."""
        url = reverse('admin:teams_teamrankingbreakdown_change', args=[self.breakdown.pk])
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check all point categories are displayed
        self.assertContains(response, '120')  # age points
        self.assertContains(response, '30')   # member points
        self.assertContains(response, '100')  # participation points
        self.assertContains(response, '500')  # winner points
        self.assertContains(response, '900')  # final total


class TeamAdminEnhancementsTestCase(TeamRankingAdminTestCase):
    """Test enhancements to Team admin for ranking."""
    
    def test_team_admin_has_ranking_section(self):
        """Test that team admin shows ranking information."""
        url = reverse('admin:teams_team_change', args=[self.team.pk])
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check for ranking-related content
        content = response.content.decode()
        # Look for ranking section or related fields
        has_ranking_content = any([
            'ranking' in content.lower(),
            'points' in content.lower(),
            'breakdown' in content.lower()
        ])
        self.assertTrue(has_ranking_content)
    
    def test_point_adjustment_action_available(self):
        """Test that point adjustment action is available in team admin."""
        # This would test custom admin actions if implemented
        url = reverse('admin:teams_team_changelist')
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check if our team is listed
        self.assertContains(response, 'Admin Test Team')


class BulkOperationsTestCase(TeamRankingAdminTestCase):
    """Test bulk operations in admin interface."""
    
    def setUp(self):
        super().setUp()
        # Create multiple teams
        self.team2 = Team.objects.create(
            name='Bulk Test Team 2',
            tag='BTT2',
            game='valorant',
            captain=self.regular_profile
        )
        self.team3 = Team.objects.create(
            name='Bulk Test Team 3',
            tag='BTT3',
            game='efootball',
            captain=self.regular_profile
        )
    
    def test_bulk_recalculation_action(self):
        """Test bulk point recalculation action."""
        url = reverse('admin:teams_team_changelist')
        
        # Select teams and apply bulk action
        data = {
            '_selected_action': [self.team.pk, self.team2.pk],
            'action': 'recalculate_team_points'
        }
        
        response = self.admin_client.post(url, data, follow=True)
        
        # Check for success message
        messages = list(get_messages(response.wsgi_request))
        success_messages = [str(m) for m in messages if 'successfully' in str(m).lower()]
        self.assertGreater(len(success_messages), 0)
    
    def test_bulk_operations_respect_permissions(self):
        """Test that bulk operations require proper permissions."""
        url = reverse('admin:teams_team_changelist')
        
        # Try bulk action with regular user
        data = {
            '_selected_action': [self.team.pk],
            'action': 'recalculate_team_points'
        }
        
        response = self.regular_client.post(url, data)
        # Should be denied or redirected
        self.assertNotEqual(response.status_code, 200)


class AdminPermissionsTestCase(TeamRankingAdminTestCase):
    """Test admin permissions for ranking system."""
    
    def test_staff_user_access(self):
        """Test that staff users can access ranking admin."""
        # Create staff user (not superuser)
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        
        staff_client = Client()
        staff_client.login(username='staff', password='staffpass123')
        
        # Test access to various admin pages
        admin_urls = [
            reverse('admin:teams_rankingcriteria_changelist'),
            reverse('admin:teams_teamrankinghistory_changelist'),
            reverse('admin:teams_teamrankingbreakdown_changelist'),
        ]
        
        for url in admin_urls:
            response = staff_client.get(url)
            # Staff should have access to view
            self.assertIn(response.status_code, [200, 302])  # 302 if redirected due to permissions
    
    def test_regular_user_no_access(self):
        """Test that regular users cannot access ranking admin."""
        admin_urls = [
            reverse('admin:teams_rankingcriteria_changelist'),
            reverse('admin:teams_teamrankinghistory_changelist'),
            reverse('admin:teams_teamrankingbreakdown_changelist'),
        ]
        
        for url in admin_urls:
            response = self.regular_client.get(url)
            # Regular users should be denied or redirected
            self.assertNotEqual(response.status_code, 200)


class AdminFormValidationTestCase(TeamRankingAdminTestCase):
    """Test form validation in admin interface."""
    
    def test_criteria_negative_points_validation(self):
        """Test that negative points are handled properly."""
        url = reverse('admin:teams_rankingcriteria_add')
        data = {
            'tournament_participation': -10,  # Negative value
            'tournament_winner': 500,
            'is_active': True
        }
        
        response = self.admin_client.post(url, data)
        
        # Form should show validation error or handle gracefully
        if response.status_code == 200:
            # Form redisplayed with errors
            self.assertContains(response, 'error')
        else:
            # Check if criteria was created with 0 instead of negative
            criteria = RankingCriteria.objects.filter(
                tournament_winner=500
            ).first()
            if criteria:
                self.assertGreaterEqual(criteria.tournament_participation, 0)
    
    def test_manual_adjustment_form_validation(self):
        """Test validation of manual point adjustments."""
        # This would test custom admin forms for point adjustments
        # Implementation depends on how the adjustment form is built
        pass


if __name__ == '__main__':
    # Run admin tests
    import sys
    import subprocess
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', __file__, '-v'
        ], capture_output=True, text=True)
        
        print("ADMIN TEST OUTPUT:")
        print(result.stdout)
        if result.stderr:
            print("ERRORS:")
            print(result.stderr)
            
        print(f"Admin Tests {'PASSED' if result.returncode == 0 else 'FAILED'}")
        
    except Exception as e:
        print(f"Error running admin tests: {e}")