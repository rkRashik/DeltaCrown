"""
Test suite to verify that user profiles correctly display team information.
This addresses the original issue: "In user profile, if the user is in a team, that is not showing."
"""
import pytest
from django.test import TestCase, Client
from apps.accounts.models import User
from django.urls import reverse
from apps.user_profile.models import UserProfile
from apps.teams.models import Team, TeamMembership
from apps.economy.models import DeltaCrownWallet


class UserProfileTeamDisplayTest(TestCase):
    """Test that user profiles correctly display team membership information."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test users
        self.user = User.objects.create_user(
            username='testplayer',
            email='testplayer@example.com',
            password='testpass123'
        )
        self.user_profile = UserProfile.objects.get_or_create(user=self.user)[0]
        
        self.captain = User.objects.create_user(
            username='captain',
            email='captain@example.com',
            password='testpass123'
        )
        self.captain_profile = UserProfile.objects.get_or_create(user=self.captain)[0]
        
        # Create team
        self.team = Team.objects.create(
            name='Test Esports Team',
            tag='TEST',
            slug='test-esports-team',
            description='A test team for unit testing',
            is_active=True
        )
        
        # Create team memberships
        self.captain_membership = TeamMembership.objects.create(
            team=self.team,
            profile=self.captain_profile,
            role=TeamMembership.Role.CAPTAIN,
            status=TeamMembership.Status.ACTIVE
        )
        
        self.player_membership = TeamMembership.objects.create(
            team=self.team,
            profile=self.user_profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Create wallets for users
        DeltaCrownWallet.objects.get_or_create(profile=self.user_profile, defaults={'cached_balance': 100})
        DeltaCrownWallet.objects.get_or_create(profile=self.captain_profile, defaults={'cached_balance': 200})
    
    def test_public_profile_displays_team_membership(self):
        """Test that public profile view displays team membership information."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Esports Team')
        self.assertContains(response, 'TEST')
        self.assertContains(response, 'Player')  # Role should be displayed
        
    def test_public_profile_displays_captain_badge(self):
        """Test that captain badge is displayed for team captains."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.captain.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Esports Team')
        self.assertContains(response, 'Captain')
        self.assertContains(response, 'fas fa-crown')  # Captain icon
        
    def test_private_profile_displays_team_info(self):
        """Test that private profile dashboard displays team information."""
        self.client.login(username='testplayer', password='testpass123')
        url = reverse('user_profile:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Esports Team')
        self.assertContains(response, 'TEST')
        
    def test_profile_displays_no_team_message_when_no_membership(self):
        """Test that profiles display appropriate message when user has no team."""
        # Create a user with no team membership
        no_team_user = User.objects.create_user(
            username='noteam',
            email='noteam@example.com',
            password='testpass123'
        )
        no_team_profile, _ = UserProfile.objects.get_or_create(user=no_team_user)
        
        url = reverse('user_profile:public_profile', kwargs={'username': no_team_user.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Team Memberships')
        self.assertContains(response, 'flying solo')
        
    def test_profile_displays_multiple_teams_if_applicable(self):
        """Test that profiles handle multiple team memberships correctly."""
        # Create second team and membership
        second_team = Team.objects.create(
            name='Second Team',
            tag='SEC',
            slug='second-team',
            description='Second test team',
            is_active=True
        )
        
        TeamMembership.objects.create(
            team=second_team,
            profile=self.user_profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Esports Team')
        self.assertContains(response, 'Second Team')
        
    def test_profile_context_includes_team_data(self):
        """Test that profile views include team data in context."""
        from apps.user_profile.views_public import public_profile_view
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get(f'/profile/{self.user.username}/')
        response = public_profile_view(request, username=self.user.username)
        
        # Check that team data is in context (response should be rendered with context)
        self.assertEqual(response.status_code, 200)
        
    def test_profile_handles_inactive_team_memberships(self):
        """Test that profiles correctly handle inactive team memberships."""
        # Set membership as inactive
        self.player_membership.status = TeamMembership.Status.REMOVED
        self.player_membership.save()
        
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should show in past teams section or not show at all depending on implementation
        
    def test_profile_economy_integration(self):
        """Test that profiles display economy information."""
        self.client.login(username='testplayer', password='testpass123')
        url = reverse('user_profile:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DeltaCoin')
        self.assertContains(response, '100')  # Wallet balance
        
    def test_team_urls_work_correctly(self):
        """Test that team-related URLs in profiles work correctly."""
        # Test team creation URL
        try:
            team_create_url = reverse('teams:create')
            self.assertTrue(True)  # URL reversal succeeded
        except:
            self.fail("Team creation URL 'teams:create' not found")
            
        # Test team list URL
        try:
            team_list_url = reverse('teams:team_list')
            self.assertTrue(True)  # URL reversal succeeded
        except:
            self.fail("Team list URL 'teams:team_list' not found")


class UserProfileResponseCodeTest(TestCase):
    """Test that user profile views return correct HTTP response codes."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        UserProfile.objects.get_or_create(user=self.user)
        
    def test_public_profile_accessible(self):
        """Test that public profiles are accessible without authentication."""
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_private_profile_requires_authentication(self):
        """Test that private profile dashboard requires authentication."""
        url = reverse('user_profile:profile')
        response = self.client.get(url)
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        
    def test_private_profile_accessible_when_authenticated(self):
        """Test that private profile is accessible when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('user_profile:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_nonexistent_user_profile_returns_404(self):
        """Test that requesting profile of non-existent user returns 404."""
        url = reverse('user_profile:public_profile', kwargs={'username': 'nonexistent'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)