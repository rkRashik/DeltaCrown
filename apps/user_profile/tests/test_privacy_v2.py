"""
UP-UI-RESTORE-02: Privacy Settings Tests

Tests privacy settings page rendering and privacy enforcement.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile

User = get_user_model()


class PrivacySettingsPageTestCase(TestCase):
    """Test privacy settings page rendering and functionality"""
    
    def setUp(self):
        """Create test user and profile"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='privacytest',
            email='privacy@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
    
    def test_privacy_page_requires_login(self):
        """Test privacy page requires authentication"""
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login', response['Location'])
    
    def test_privacy_page_renders_for_authenticated_user(self):
        """Test privacy page renders for logged-in user"""
        self.client.login(username='privacytest', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Privacy Settings')
    
    def test_privacy_page_shows_profile_visibility_options(self):
        """Test privacy page shows visibility radio buttons"""
        self.client.login(username='privacytest', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'Profile Visibility')
        self.assertContains(response, 'Public')
        self.assertContains(response, 'Friends Only')
        self.assertContains(response, 'Private')
    
    def test_privacy_page_shows_field_visibility_toggles(self):
        """Test privacy page shows field visibility toggles"""
        self.client.login(username='privacytest', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'Field Visibility')
        self.assertContains(response, 'Show email address')
        self.assertContains(response, 'Show phone number')
        self.assertContains(response, 'Show real name')
    
    def test_privacy_page_shows_social_privacy_toggles(self):
        """Test privacy page shows social privacy toggles"""
        self.client.login(username='privacytest', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'Social Privacy')
        self.assertContains(response, 'Allow friend requests')
        self.assertContains(response, 'Show online status')
    
    def test_privacy_page_has_toggle_switches(self):
        """Test privacy page uses toggle switch components"""
        self.client.login(username='privacytest', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'toggle-checkbox')
        self.assertContains(response, 'toggle-background')
        self.assertContains(response, 'toggle-dot')
    
    def test_privacy_page_shows_back_to_settings_link(self):
        """Test privacy page has link back to settings"""
        self.client.login(username='privacytest', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        settings_url = reverse('user_profile:profile_settings_v2')
        self.assertContains(response, settings_url)
        self.assertContains(response, 'Back to Settings')
    
    def test_privacy_form_posts_to_safe_endpoint(self):
        """Test privacy form uses safe mutation endpoint"""
        self.client.login(username='privacytest', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        save_url = reverse('user_profile:privacy_settings_save_safe')
        self.assertContains(response, save_url)


class PrivacyEnforcementTestCase(TestCase):
    """Test privacy settings are enforced correctly"""
    
    def setUp(self):
        """Create test users"""
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123'
        )
        
        self.owner_profile, _ = UserProfile.objects.get_or_create(user=self.owner)
        self.owner_profile.display_name = 'Profile Owner'
        self.owner_profile.save()
    
    def test_owner_can_access_own_privacy_settings(self):
        """Test user can access their own privacy settings"""
        self.client.login(username='owner', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_privacy_notice_shown(self):
        """Test privacy notice is displayed"""
        self.client.login(username='owner', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'username and display name are always public')
