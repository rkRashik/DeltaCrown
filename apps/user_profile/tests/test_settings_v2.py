"""
UP-UI-RESTORE-02: Settings Page Tests

Tests settings page rendering, forms, and game passport management.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, GameProfile
from apps.games.models import Game

User = get_user_model()


class SettingsPageTestCase(TestCase):
    """Test settings page rendering and functionality"""
    
    def setUp(self):
        """Create test user and profile"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='settingstest',
            email='settings@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.display_name = 'Settings Test User'
        self.profile.bio = 'Test bio'
        self.profile.save()
        
        # Create a test game for passport testing
        self.game, _ = Game.objects.get_or_create(
            name='TestGame',
            defaults={
                'slug': 'testgame',
                'display_name': 'Test Game',
                'is_passport_supported': True,
                'is_active': True
            }
        )
    
    def test_settings_page_requires_login(self):
        """Test settings page requires authentication"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login', response['Location'])
    
    def test_settings_page_renders_for_authenticated_user(self):
        """Test settings page renders for logged-in user"""
        self.client.login(username='settingstest', password='testpass123')
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile Settings')
        self.assertContains(response, 'Settings Test User')
    
    def test_settings_page_shows_basic_info_section(self):
        """Test settings page shows basic info form"""
        self.client.login(username='settingstest', password='testpass123')
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'Basic Information')
        self.assertContains(response, 'Display Name')
        self.assertContains(response, 'Bio')
        self.assertContains(response, 'Country')
    
    def test_settings_page_shows_game_passports_section(self):
        """Test settings page shows game passports management"""
        self.client.login(username='settingstest', password='testpass123')
        
        # Create a test passport
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestIGN',
            is_pinned=True
        )
        
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'Game Passports')
        self.assertContains(response, 'TestIGN')
        self.assertContains(response, 'PINNED')
    
    def test_settings_page_shows_social_links_section(self):
        """Test settings page shows social links form"""
        self.client.login(username='settingstest', password='testpass123')
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'Social Links')
        self.assertContains(response, 'YouTube')
        self.assertContains(response, 'Twitch')
        self.assertContains(response, 'Twitter')
        self.assertContains(response, 'Discord')
    
    def test_update_basic_info_post(self):
        """Test updating basic profile information"""
        self.client.login(username='settingstest', password='testpass123')
        url = reverse('user_profile:update_basic_info')
        
        data = {
            'display_name': 'Updated Name',
            'bio': 'Updated bio text',
            'country': 'United States'
        }
        
        response = self.client.post(url, data)
        
        # Should redirect back to settings
        self.assertEqual(response.status_code, 302)
        self.assertIn('profile_settings_v2', response['Location'])
        
        # Verify changes were saved
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, 'Updated Name')
        self.assertEqual(self.profile.bio, 'Updated bio text')
        self.assertEqual(self.profile.country, 'United States')
    
    def test_update_basic_info_requires_display_name(self):
        """Test basic info update requires display name"""
        self.client.login(username='settingstest', password='testpass123')
        url = reverse('user_profile:update_basic_info')
        
        data = {
            'display_name': '',  # Empty display name
            'bio': 'Test bio'
        }
        
        response = self.client.post(url, data, follow=True)
        
        # Should redirect with error message
        messages = list(response.context['messages'])
        self.assertTrue(any('required' in str(m).lower() for m in messages))


class GamePassportManagementTestCase(TestCase):
    """Test game passport management in settings"""
    
    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='passporttest',
            email='passport@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        
        self.game, _ = Game.objects.get_or_create(
            name='TestGame',
            defaults={
                'slug': 'testgame',
                'display_name': 'Test Game',
                'is_passport_supported': True,
                'is_active': True
            }
        )
        
        self.passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer',
            region='NA',
            visibility='public',
            is_pinned=False,
            is_lft=False
        )
    
    def test_settings_shows_passport_quick_actions(self):
        """Test settings page shows passport quick action buttons"""
        self.client.login(username='passporttest', password='testpass123')
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'togglePin')
        self.assertContains(response, 'setVisibility')
        self.assertContains(response, 'toggleLFT')
    
    def test_settings_shows_passport_count(self):
        """Test settings page shows pinned passport count"""
        self.client.login(username='passporttest', password='testpass123')
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertContains(response, '0/6 pinned')  # Default MAX_PINNED_GAMES
    
    def test_settings_shows_empty_state_for_no_passports(self):
        """Test settings page shows empty state when no passports exist"""
        # Delete the passport
        self.passport.delete()
        
        self.client.login(username='passporttest', password='testpass123')
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'No game passports yet')
    
    def test_pinned_passport_shows_gradient_background(self):
        """Test pinned passports have different styling"""
        self.passport.is_pinned = True
        self.passport.save()
        
        self.client.login(username='passporttest', password='testpass123')
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        self.assertContains(response, 'from-indigo-600/20 to-purple-600/20')
        self.assertContains(response, 'PINNED')
