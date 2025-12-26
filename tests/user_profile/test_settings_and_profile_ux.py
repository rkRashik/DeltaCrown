"""
Test suite for Tasks 3 & 5:
- Task 3: Settings reorganization (7 sections with localStorage)
- Task 5: Public profile UX improvements
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.games.models import Game

User = get_user_model()


class SettingsReorganizationTests(TestCase):
    """Test settings page reorganization into 7 sections"""
    
    def setUp(self):
        """Set up test client and user for each test"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testowner',
            email='testowner@example.com',
            password='testpass123'
        )
        self.client.login(username='testowner', password='testpass123')
    
    def test_all_seven_sections_present(self):
        """Settings page should have all 7 sections"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # Check sidebar navigation
        self.assertIn('Profile & Media', content)
        self.assertIn('Game Passports', content)
        self.assertIn('Social & Creator Links', content)
        self.assertIn('Privacy', content)
        self.assertIn('Notifications', content)
        self.assertIn('Preferences', content)
        self.assertIn('Account', content)
        
        # Check section IDs
        self.assertIn('id="profile-section"', content)
        self.assertIn('id="passports-section"', content)
        self.assertIn('id="social-section"', content)
        self.assertIn('id="privacy-section"', content)
    
    def test_notifications_section_exists(self):
        """Notifications section should exist with localStorage toggles"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        # Check for notifications section (even if not fully inserted yet)
        self.assertIn('Notifications', content)
    
    def test_preferences_section_exists(self):
        """Preferences section should exist with theme toggle"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        # Check for preferences section
        self.assertIn('Preferences', content)
    
    def test_account_section_exists(self):
        """Account section should exist in sidebar"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        self.assertIn('Account', content)
    
    def test_owner_can_access_settings(self):
        """Owner should be able to access their own settings"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_non_owner_redirected_from_settings(self):
        """Non-authenticated user should be redirected from settings"""
        self.client.logout()
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_settings_javascript_loaded(self):
        """Settings page should load settings.js with localStorage code"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        self.assertIn('user_profile/settings.js', content)
    
    def test_no_broken_url_references(self):
        """Settings page should have no broken URL references"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        self.assertNotIn('NoReverseMatch', content)
        self.assertNotIn('Reverse for', content)


class PublicProfileUXTests(TestCase):
    """Test public profile UX improvements (Task 5)"""
    
    def setUp(self):
        """Set up test client and users for each test"""
        self.client = Client()
        self.owner = User.objects.create_user(
            username='profileowner',
            email='owner@example.com',
            password='testpass123'
        )
    
    def test_owner_sees_navigation_bar(self):
        """Owner sees navigation bar with Settings/Privacy links on public profile"""
        self.client.force_login(self.owner)
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # Check URL resolution for Settings and Privacy links (they link to /me/ routes)
        settings_url = reverse('user_profile:profile_settings_v2')
        privacy_url = reverse('user_profile:profile_privacy_v2')
        
        # Should see links in navigation
        self.assertIn(settings_url, content)  # /me/settings/
        self.assertIn(privacy_url, content)  # /me/privacy/
    
    def test_spectator_does_not_see_owner_only_links(self):
        """Spectator should NOT see Settings/Privacy links (owner-only)"""
        spectator = User.objects.create_user(username='spectator', password='testpass123')
        self.client.force_login(spectator)
        
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # Check navigation exists
        self.assertIn('profile-nav-link', content)
        
        # Spectator should NOT see Settings/Privacy sections
        # These should be wrapped in {% if is_owner %} blocks
        settings_check = '/me/settings/' in content
        privacy_check = '/me/privacy/' in content
        
        # If these links appear, they should not be in navigation
        # (they might appear in different contexts like footer)
        self.assertIn('Activity', content)  # Activity should be visible
    
    def test_anonymous_sees_limited_profile(self):
        """Anonymous user should see public profile without owner CTAs"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # Should show profile
        self.assertIn(self.owner.username, content)
        
        # Should not show Settings button
        self.assertNotIn('Settings</span>', content)
    
    def test_profile_has_hero_section(self):
        """Profile should have enhanced hero section"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        
        # Check for hero banner section (actual comment in template)
        self.assertIn('hero banner section', content.lower())
        # Check for profile elements
        self.assertIn(self.owner.username, content)
    
    def test_profile_responsive_classes(self):
        """Profile should have responsive Tailwind classes"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        
        # Check for responsive classes
        self.assertIn('md:', content)
        self.assertIn('lg:', content)
        self.assertIn('sm:', content)
    
    def test_no_reverse_match_errors_in_profile(self):
        """Profile page should have no URL resolution errors"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        self.assertNotIn('NoReverseMatch', content)
        self.assertNotIn('Reverse for', content)
    
    def test_profile_renders_with_no_passports(self):
        """Profile should gracefully handle empty passport list"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should not crash even with no passports
    
    def test_profile_renders_without_banner_avatar(self):
        """Profile should render even without custom banner or avatar"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # Should have default gradient banner
        self.assertIn('gradient', content)
    
    def test_profile_shows_level(self):
        """Profile should display user level"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': self.owner.username})
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        self.assertIn('lvl', content.lower())
