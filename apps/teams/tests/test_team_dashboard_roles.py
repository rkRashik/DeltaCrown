"""
Test role-based team dashboard functionality.

Tests that each role (Owner, Manager, Coach, Player) sees the correct
dashboard sections and actions on the team detail page.
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.teams.models import Team, TeamMembership
from apps.user_profile.models import UserProfile

User = get_user_model()


class TeamDashboardRoleTests(TestCase):
    """Test role-based dashboard visibility and permissions."""
    
    def setUp(self):
        """Create test team and users with different roles."""
        # Create users
        self.owner_user = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123'
        )
        self.manager_user = User.objects.create_user(
            username='manager',
            email='manager@test.com',
            password='testpass123'
        )
        self.coach_user = User.objects.create_user(
            username='coach',
            email='coach@test.com',
            password='testpass123'
        )
        self.player_user = User.objects.create_user(
            username='player',
            email='player@test.com',
            password='testpass123'
        )
        self.nonmember_user = User.objects.create_user(
            username='nonmember',
            email='nonmember@test.com',
            password='testpass123'
        )
        
        # Create profiles
        self.owner_profile = UserProfile.objects.get_or_create(user=self.owner_user)[0]
        self.manager_profile = UserProfile.objects.get_or_create(user=self.manager_user)[0]
        self.coach_profile = UserProfile.objects.get_or_create(user=self.coach_user)[0]
        self.player_profile = UserProfile.objects.get_or_create(user=self.player_user)[0]
        self.nonmember_profile = UserProfile.objects.get_or_create(user=self.nonmember_user)[0]
        
        # Create team
        self.team = Team.objects.create(
            name='Test Esports Team',
            tag='TEST',
            slug='test-esports-team',
            game='valorant',
            captain=self.owner_profile,
            is_public=True,
            is_active=True
        )
        
        # Create memberships with different roles
        self.owner_membership = TeamMembership.objects.create(
            team=self.team,
            profile=self.owner_profile,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE
        )
        
        self.manager_membership = TeamMembership.objects.create(
            team=self.team,
            profile=self.manager_profile,
            role=TeamMembership.Role.MANAGER,
            status=TeamMembership.Status.ACTIVE
        )
        
        self.coach_membership = TeamMembership.objects.create(
            team=self.team,
            profile=self.coach_profile,
            role=TeamMembership.Role.COACH,
            status=TeamMembership.Status.ACTIVE
        )
        
        self.player_membership = TeamMembership.objects.create(
            team=self.team,
            profile=self.player_profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        
        self.client = Client()
        self.team_url = reverse('teams:team_profile', kwargs={'slug': self.team.slug})
    
    def test_owner_sees_captain_controls(self):
        """Owner should see Captain Controls dashboard."""
        self.client.force_login(self.owner_user)
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Captain Controls')
        self.assertContains(response, 'Full Dashboard')
        self.assertContains(response, 'Team Settings')
        self.assertContains(response, 'Manage Roster')
        self.assertContains(response, 'Team Owner Dashboard')
        
        # Should NOT see other role-specific sections
        self.assertNotContains(response, 'Manager Tools')
        self.assertNotContains(response, 'Coach Tools')
    
    def test_manager_sees_manager_tools(self):
        """Manager should see Manager Tools, not Captain Controls."""
        self.client.force_login(self.manager_user)
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manager Tools')
        self.assertContains(response, 'Manage Roster')
        self.assertContains(response, 'Invite Members')
        self.assertContains(response, 'Manager Dashboard')
        
        # Should NOT see Captain Controls or Coach Tools
        self.assertNotContains(response, 'Captain Controls')
        self.assertNotContains(response, 'Full Dashboard')
        self.assertNotContains(response, 'Coach Tools')
    
    def test_coach_sees_coach_tools(self):
        """Coach should see Coach Tools, not management controls."""
        self.client.force_login(self.coach_user)
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Coach Tools')
        self.assertContains(response, 'Strategy Planner')
        self.assertContains(response, 'Schedule Practice')
        self.assertContains(response, 'Performance Analytics')
        self.assertContains(response, 'Training Materials')
        self.assertContains(response, 'Coach Dashboard')
        
        # Should NOT see Captain Controls or Manager Tools
        self.assertNotContains(response, 'Captain Controls')
        self.assertNotContains(response, 'Manager Tools')
        self.assertNotContains(response, 'Manage Roster')
    
    def test_player_sees_player_tools(self):
        """Player should see Player Tools only, no management sections."""
        self.client.force_login(self.player_user)
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Player Tools')
        self.assertContains(response, 'Update Game ID')
        self.assertContains(response, 'View My Stats')
        self.assertContains(response, 'Leave Team')
        self.assertContains(response, 'Member Dashboard')
        
        # Should NOT see any management sections
        self.assertNotContains(response, 'Captain Controls')
        self.assertNotContains(response, 'Manager Tools')
        self.assertNotContains(response, 'Coach Tools')
        self.assertNotContains(response, 'Manage Roster')
        self.assertNotContains(response, 'Full Dashboard')
    
    def test_nonmember_sees_no_dashboard(self):
        """Non-member should not see any member dashboard sections."""
        self.client.force_login(self.nonmember_user)
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should NOT see ANY member dashboard sections
        self.assertNotContains(response, 'Captain Controls')
        self.assertNotContains(response, 'Manager Tools')
        self.assertNotContains(response, 'Coach Tools')
        self.assertNotContains(response, 'Player Tools')
        self.assertNotContains(response, 'My Tools')
        self.assertNotContains(response, 'Leave Team')
        self.assertNotContains(response, 'Dashboard')
    
    def test_anonymous_user_sees_no_dashboard(self):
        """Anonymous user should not see member dashboard."""
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should NOT see ANY member dashboard sections
        self.assertNotContains(response, 'Captain Controls')
        self.assertNotContains(response, 'Manager Tools')
        self.assertNotContains(response, 'Coach Tools')
        self.assertNotContains(response, 'Dashboard')
    
    def test_all_members_see_common_sections(self):
        """All members should see common sections like Communication, Team Info."""
        for user in [self.owner_user, self.manager_user, self.coach_user, self.player_user]:
            self.client.force_login(user)
            response = self.client.get(self.team_url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Communication')
            self.assertContains(response, 'Team Info')
            self.assertContains(response, 'Quick Links')
            self.assertContains(response, 'Team Achievements')
    
    def test_role_display_accuracy(self):
        """Test that role display shows correct role for each user."""
        test_cases = [
            (self.owner_user, 'Owner'),
            (self.manager_user, 'Manager'),
            (self.coach_user, 'Coach'),
            (self.player_user, 'Player'),
        ]
        
        for user, expected_role in test_cases:
            self.client.force_login(user)
            response = self.client.get(self.team_url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, f'Your Role')
            self.assertContains(response, expected_role)
    
    def test_leave_team_button_visibility(self):
        """Test Leave Team button is shown only to non-owners."""
        # Owner should NOT see Leave Team
        self.client.force_login(self.owner_user)
        response = self.client.get(self.team_url)
        self.assertEqual(response.status_code, 200)
        # Check context variable instead of HTML since button might be in modal
        self.assertFalse(response.context.get('can_leave_team', False))
        
        # Manager, Coach, Player SHOULD see Leave Team
        for user in [self.manager_user, self.coach_user, self.player_user]:
            self.client.force_login(user)
            response = self.client.get(self.team_url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context.get('can_leave_team', True))
            self.assertContains(response, 'Leave Team')
    
    def test_context_flags_set_correctly(self):
        """Test that all role context flags are set correctly in the view."""
        # Test owner context
        self.client.force_login(self.owner_user)
        response = self.client.get(self.team_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_owner'])
        self.assertTrue(response.context['is_member'])
        self.assertTrue(response.context['can_manage_roster'])
        self.assertTrue(response.context['can_edit_team_profile'])
        self.assertFalse(response.context['can_leave_team'])
        
        # Test manager context
        self.client.force_login(self.manager_user)
        response = self.client.get(self.team_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_manager'])
        self.assertTrue(response.context['is_member'])
        self.assertTrue(response.context['can_manage_roster'])
        self.assertTrue(response.context['can_edit_team_profile'])
        self.assertTrue(response.context['can_leave_team'])
        
        # Test coach context
        self.client.force_login(self.coach_user)
        response = self.client.get(self.team_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_coach'])
        self.assertTrue(response.context['is_member'])
        self.assertFalse(response.context['can_manage_roster'])
        self.assertFalse(response.context['can_edit_team_profile'])
        self.assertTrue(response.context['can_leave_team'])
        self.assertTrue(response.context['can_view_team_settings'])
        
        # Test player context
        self.client.force_login(self.player_user)
        response = self.client.get(self.team_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_player'])
        self.assertTrue(response.context['is_member'])
        self.assertFalse(response.context['can_manage_roster'])
        self.assertFalse(response.context['can_edit_team_profile'])
        self.assertTrue(response.context['can_leave_team'])
        self.assertFalse(response.context['can_view_team_settings'])
    
    def test_manager_can_access_manage_roster(self):
        """Test that manager can access the manage roster URL."""
        self.client.force_login(self.manager_user)
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manage Roster')
        # Check that the URL is present
        manage_url = reverse('teams:manage', kwargs={'slug': self.team.slug})
        self.assertContains(response, manage_url)
    
    def test_coach_cannot_access_manage_roster(self):
        """Test that coach does NOT see Manage Roster link."""
        self.client.force_login(self.coach_user)
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        # Manage Roster should not be in Coach Tools
        self.assertNotContains(response, 'Manage Roster')
    
    def test_coming_soon_badges_present(self):
        """Test that coming soon features have non-breaking badges."""
        self.client.force_login(self.coach_user)
        response = self.client.get(self.team_url)
        
        self.assertEqual(response.status_code, 200)
        # Check for "Soon" badges
        self.assertContains(response, 'Soon')
        # Check for alert messages instead of broken links
        self.assertContains(response, 'alert(')
        self.assertContains(response, 'coming soon')
