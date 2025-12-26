"""
UP-UI-REDESIGN-01: Profile Dashboard v3 Tests
Test new modules: Teams, Tournaments, Economy, Shop, Dashboard Nav
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileDashboardTests(TestCase):
    """Test Profile Dashboard v3 rendering and role-based visibility"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otherplayer',
            email='other@example.com',
            password='testpass123'
        )
        self.profile_url = reverse('user_profile:profile_public_v2', kwargs={'username': 'testplayer'})
    
    def test_dashboard_nav_renders(self):
        """Test that dashboard navigation renders with all sections"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Check for navigation links
        self.assertContains(response, 'href="#overview"')
        self.assertContains(response, 'href="#passports"')
        self.assertContains(response, 'href="#teams"')
        self.assertContains(response, 'href="#tournaments"')
        self.assertContains(response, 'href="#stats"')
        self.assertContains(response, 'href="#activity"')
        self.assertContains(response, 'href="#about"')
    
    def test_overview_section_exists(self):
        """Test that Overview section renders"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="overview"')
        self.assertContains(response, 'Career Stats')
    
    def test_teams_section_exists(self):
        """Test that Teams section renders with empty state"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="teams"')
        self.assertContains(response, 'Teams')
        self.assertContains(response, 'No Teams Yet')
    
    def test_tournaments_section_exists(self):
        """Test that Tournaments section renders with empty state"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="tournaments"')
        self.assertContains(response, 'Tournaments')
        self.assertContains(response, 'No Tournaments Yet')
    
    def test_economy_section_owner_only(self):
        """Test that Economy section only visible to owner"""
        # Owner view
        self.client.login(username='testplayer', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="economy"')
        self.assertContains(response, 'Economy')
        self.assertContains(response, 'href="#economy"')
        
        # Spectator view
        self.client.logout()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="economy"')
        self.assertNotContains(response, 'href="#economy"')
    
    def test_shop_section_owner_only(self):
        """Test that Shop section only visible to owner"""
        # Owner view
        self.client.login(username='testplayer', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="shop"')
        self.assertContains(response, 'Shop & Orders')
        self.assertContains(response, 'href="#shop"')
        
        # Spectator view
        self.client.logout()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="shop"')
        self.assertNotContains(response, 'href="#shop"')
    
    def test_activity_section_exists(self):
        """Test that Activity section renders"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="activity"')
        self.assertContains(response, 'Recent Activity')
    
    def test_about_section_exists(self):
        """Test that About section renders"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="about"')
        self.assertContains(response, 'About')
    
    def test_owner_actions_visible_to_owner(self):
        """Test that owner-specific actions visible to owner"""
        self.client.login(username='testplayer', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'Edit Profile')
        self.assertNotContains(response, 'Follow')
    
    def test_spectator_actions_visible_to_others(self):
        """Test that spectator actions visible to non-owners"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'Follow')
        self.assertNotContains(response, 'Edit Profile')
    
    def test_game_passports_section_exists(self):
        """Test that Game Passports section renders"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="passports"')
        self.assertContains(response, 'Game Passports')
    
    def test_stats_section_exists(self):
        """Test that Stats section renders"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="stats"')
        self.assertContains(response, 'Career Stats')
    
    def test_dashboard_uses_correct_css_classes(self):
        """Test that dashboard uses UP-UI-REDESIGN-01 CSS classes"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'dashboard-card')
        self.assertContains(response, 'module-header')
        self.assertContains(response, 'module-title')
        self.assertContains(response, 'nav-chip')
        self.assertContains(response, 'empty-state')
    
    def test_dashboard_includes_javascript(self):
        """Test that dashboard includes profile_dashboard.js"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'profile_dashboard.js')
    
    def test_battle_cards_still_work(self):
        """Test that Battle Cards from UP-UI-POLISH-04 still render"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'battle-card')
    
    def test_pinned_passports_display(self):
        """Test that pinned passports have pin indicator"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        # Check for pin emoji/indicator (if passports exist)
        # This will only show if user has passports, so we just check structure exists
        self.assertIn('pinned_passports', response.context)
    
    def test_more_games_collapsible_exists(self):
        """Test that More Games collapsible section exists"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="toggleMoreGames"')
        self.assertContains(response, 'id="moreGamesContent"')
        self.assertContains(response, 'collapsible-content')
    
    def test_accessibility_aria_labels(self):
        """Test that dashboard includes proper ARIA labels"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'aria-label')
        self.assertContains(response, 'aria-expanded')
        self.assertContains(response, 'aria-controls')
        self.assertContains(response, 'role="navigation"')
    
    def test_responsive_breakpoints(self):
        """Test that template includes responsive classes"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Check for Tailwind responsive classes
        self.assertContains(response, 'sm:')
        self.assertContains(response, 'md:')
        self.assertContains(response, 'lg:')
    
    def test_no_deprecated_endpoints(self):
        """Test that template doesn't use deprecated URL names"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Should NOT contain old/deprecated URL patterns
        self.assertNotContains(response, 'profile_edit_old')
        self.assertNotContains(response, 'account_settings_legacy')


class EmptyStateTests(TestCase):
    """Test empty state rendering for modules without data"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='testpass123'
        )
        self.profile_url = reverse('user_profile:profile_public_v2', kwargs={'username': 'newuser'})
    
    def test_empty_game_passports_cta(self):
        """Test that empty game passports shows CTA"""
        self.client.login(username='newuser', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'No Game Passports Yet')
        self.assertContains(response, 'Add Your First Game Passport')
    
    def test_empty_teams_message(self):
        """Test that empty teams shows appropriate message"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'No Teams Yet')
        self.assertContains(response, 'Join a team to compete')
    
    def test_empty_tournaments_message(self):
        """Test that empty tournaments shows appropriate message"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'No Tournaments Yet')
        self.assertContains(response, 'Register for tournaments')
    
    def test_empty_activity_message(self):
        """Test that empty activity shows appropriate message"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'No recent activity')
        self.assertContains(response, 'Activity will appear here')
    
    def test_empty_social_links_message(self):
        """Test that empty social links shows appropriate message"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'No social links yet')


class RoleBasedVisibilityTests(TestCase):
    """Test role-based visibility (Owner/Spectator/Admin)"""
    
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        self.spectator = User.objects.create_user(
            username='spectator',
            email='spectator@example.com',
            password='testpass123'
        )
        self.profile_url = reverse('user_profile:profile_public_v2', kwargs={'username': 'owner'})
    
    def test_owner_sees_all_modules(self):
        """Test that owner sees all modules including Economy and Shop"""
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'id="overview"')
        self.assertContains(response, 'id="passports"')
        self.assertContains(response, 'id="teams"')
        self.assertContains(response, 'id="tournaments"')
        self.assertContains(response, 'id="stats"')
        self.assertContains(response, 'id="economy"')
        self.assertContains(response, 'id="shop"')
        self.assertContains(response, 'id="activity"')
        self.assertContains(response, 'id="about"')
    
    def test_spectator_does_not_see_economy_shop(self):
        """Test that spectator doesn't see Economy and Shop modules"""
        self.client.login(username='spectator', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Should see public modules
        self.assertContains(response, 'id="overview"')
        self.assertContains(response, 'id="passports"')
        self.assertContains(response, 'id="teams"')
        self.assertContains(response, 'id="tournaments"')
        self.assertContains(response, 'id="stats"')
        self.assertContains(response, 'id="activity"')
        self.assertContains(response, 'id="about"')
        
        # Should NOT see owner-only modules
        self.assertNotContains(response, 'id="economy"')
        self.assertNotContains(response, 'id="shop"')
    
    def test_anonymous_user_sees_public_modules(self):
        """Test that anonymous user sees public modules only"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Should see public modules
        self.assertContains(response, 'id="passports"')
        self.assertContains(response, 'id="teams"')
        self.assertContains(response, 'id="tournaments"')
        self.assertContains(response, 'id="stats"')
        
        # Should NOT see owner-only modules
        self.assertNotContains(response, 'id="economy"')
        self.assertNotContains(response, 'id="shop"')


# Run tests with: pytest tests/test_profile_dashboard_v3.py -v
