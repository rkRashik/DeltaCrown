"""
Django Unit Tests for Settings APIs
UP-PHASE15-SESSION6: Comprehensive API endpoint testing

Tests:
- Authentication required
- IDOR prevention
- CSRF protection
- Input validation
- Privacy enforcement
- Success/error responses
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.user_profile.models import UserProfile, SocialLink, GameProfile, ProfileAboutItem
from apps.games.models import Game

User = get_user_model()


class SettingsAPITestCase(TestCase):
    """Base test case with common setup"""
    
    def setUp(self):
        """Create test users and profiles"""
        # User 1 (owner)
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.profile1 = UserProfile.objects.get(user=self.user1)
        
        # User 2 (other user for IDOR tests)
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        self.profile2 = UserProfile.objects.get(user=self.user2)
        
        # Authenticated client
        self.client = Client()
        self.client.login(username='testuser1', password='testpass123')


class TestBasicProfileAPI(SettingsAPITestCase):
    """Test basic profile update API"""
    
    def test_update_basic_info_requires_auth(self):
        """Test that unauthenticated requests are rejected"""
        client = Client()  # No login
        url = reverse('user_profile:update_basic_info')
        
        response = client.post(url, {
            'display_name': 'Hacker'
        })
        
        # Should redirect to login or return 401/403
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_update_basic_info_success(self):
        """Test successful profile update"""
        url = reverse('user_profile:update_basic_info')
        
        response = self.client.post(url, {
            'display_name': 'Updated Name',
            'bio': 'Updated bio text',
            'country': 'BD'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # Check response
        data = response.json()
        self.assertTrue(data.get('success'))
        
        # Check database
        self.profile1.refresh_from_db()
        self.assertEqual(self.profile1.display_name, 'Updated Name')
        self.assertEqual(self.profile1.bio, 'Updated bio text')
        self.assertEqual(self.profile1.country, 'BD')
    
    def test_update_basic_info_validation(self):
        """Test input validation"""
        url = reverse('user_profile:update_basic_info')
        
        # Test too long display name
        response = self.client.post(url, {
            'display_name': 'A' * 200  # Too long
        }, content_type='application/json')
        
        # Should return error
        self.assertIn(response.status_code, [400, 422])


class TestSocialLinksAPI(SettingsAPITestCase):
    """Test social links CRUD APIs"""
    
    def test_create_social_link_requires_auth(self):
        """Test authentication required"""
        client = Client()
        url = reverse('user_profile:social_link_create_api')
        
        response = client.post(url, {
            'platform': 'discord',
            'url': 'https://discord.com/users/123456'
        })
        
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_create_social_link_success(self):
        """Test successful social link creation"""
        url = reverse('user_profile:social_link_create_api')
        
        response = self.client.post(url, {
            'platform': 'discord',
            'url': 'https://discord.com/users/testuser#1234',
            'handle': 'testuser#1234'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('success'))
        
        # Check database
        link = SocialLink.objects.filter(user=self.user1, platform='discord').first()
        self.assertIsNotNone(link)
        self.assertEqual(link.handle, 'testuser#1234')
    
    def test_create_social_link_validation(self):
        """Test platform validation"""
        url = reverse('user_profile:social_link_create_api')
        
        # Invalid platform
        response = self.client.post(url, {
            'platform': 'invalid_platform',
            'url': 'https://example.com'
        }, content_type='application/json')
        
        self.assertIn(response.status_code, [400, 422])
    
    def test_delete_social_link_idor_protection(self):
        """Test that users cannot delete other users' social links"""
        # Create link for user2
        link = SocialLink.objects.create(
            user=self.user2,
            platform='twitter',
            url='https://twitter.com/user2'
        )
        
        url = reverse('user_profile:social_link_delete_api')
        
        # User1 tries to delete User2's link
        response = self.client.post(url, {
            'id': link.id
        }, content_type='application/json')
        
        # Should fail
        self.assertIn(response.status_code, [403, 404])
        
        # Link should still exist
        self.assertTrue(SocialLink.objects.filter(id=link.id).exists())


class TestGamePassportsAPI(SettingsAPITestCase):
    """Test game passports CRUD APIs"""
    
    def setUp(self):
        super().setUp()
        
        # Create test game
        self.game = Game.objects.create(
            slug='valorant',
            name='VALORANT',
            display_name='VALORANT',
            is_active=True,
            is_passport_supported=True
        )
    
    def test_create_passport_requires_auth(self):
        """Test authentication required"""
        client = Client()
        url = reverse('user_profile:create_game_passport_api')
        
        response = client.post(url, {
            'game_id': self.game.id,
            'in_game_name': 'TestUser#1234'
        })
        
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_create_passport_success(self):
        """Test successful passport creation"""
        url = reverse('user_profile:create_game_passport_api')
        
        response = self.client.post(url, {
            'game_id': self.game.id,
            'ign': 'TestUser',
            'discriminator': '1234',
            'region': 'NA'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('success'))
        
        # Check database
        passport = GameProfile.objects.filter(user=self.user1, game=self.game).first()
        self.assertIsNotNone(passport)
    
    def test_delete_passport_idor_protection(self):
        """Test IDOR protection on delete"""
        # Create passport for user2
        passport = GameProfile.objects.create(
            user=self.user2,
            game=self.game,
            in_game_name='User2#5678'
        )
        
        url = reverse('user_profile:delete_game_passport_api')
        
        # User1 tries to delete User2's passport
        response = self.client.post(url, {
            'id': passport.id
        }, content_type='application/json')
        
        # Should fail
        self.assertIn(response.status_code, [403, 404])
        
        # Passport should still exist
        self.assertTrue(GameProfile.objects.filter(id=passport.id).exists())


class TestAboutItemsAPI(SettingsAPITestCase):
    """Test ProfileAboutItem CRUD APIs"""
    
    def test_create_about_item_requires_auth(self):
        """Test authentication required"""
        client = Client()
        url = reverse('user_profile:create_about_item')
        
        response = client.post(url, {
            'item_type': 'custom',
            'display_text': 'Test item'
        })
        
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_create_about_item_success(self):
        """Test successful about item creation"""
        url = reverse('user_profile:create_about_item')
        
        response = self.client.post(url, {
            'item_type': 'custom',
            'display_text': 'Test about item',
            'icon_emoji': '🎮',
            'visibility': 'public'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('success'))
        
        # Check database
        item = ProfileAboutItem.objects.filter(
            user_profile=self.profile1,
            display_text='Test about item'
        ).first()
        self.assertIsNotNone(item)
    
    def test_update_about_item_idor_protection(self):
        """Test IDOR protection on update"""
        # Create item for user2
        item = ProfileAboutItem.objects.create(
            user_profile=self.profile2,
            item_type='custom',
            display_text='User2 item'
        )
        
        url = reverse('user_profile:update_about_item', kwargs={'item_id': item.id})
        
        # User1 tries to update User2's item
        response = self.client.post(url, {
            'display_text': 'Hacked!'
        }, content_type='application/json')
        
        # Should fail
        self.assertIn(response.status_code, [403, 404])
        
        # Item should be unchanged
        item.refresh_from_db()
        self.assertEqual(item.display_text, 'User2 item')


class TestPrivacyEnforcement(SettingsAPITestCase):
    """Test privacy gates and permissions"""
    
    def test_get_profile_data_requires_auth(self):
        """Test that profile data requires authentication"""
        client = Client()
        url = reverse('user_profile:get_profile_data')
        
        response = client.get(url)
        
        # Should redirect or return 401
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_get_profile_data_returns_own_data(self):
        """Test that users can only get their own data"""
        url = reverse('user_profile:get_profile_data')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['username'], 'testuser1')
        # Should not include user2's data


class TestCSRFProtection(SettingsAPITestCase):
    """Test CSRF token validation"""
    
    def test_post_without_csrf_fails(self):
        """Test that POST without CSRF token is rejected"""
        client = Client(enforce_csrf_checks=True)
        client.login(username='testuser1', password='testpass123')
        
        url = reverse('user_profile:update_basic_info')
        
        # Post without CSRF token
        response = client.post(url, {
            'display_name': 'Hacker'
        }, content_type='application/json')
        
        # Should fail with 403
        self.assertEqual(response.status_code, 403)


class TestInputValidation(SettingsAPITestCase):
    """Test input validation and sanitization"""
    
    def test_xss_prevention_in_display_name(self):
        """Test that XSS attempts are sanitized"""
        url = reverse('user_profile:update_basic_info')
        
        response = self.client.post(url, {
            'display_name': '<script>alert("XSS")</script>',
            'bio': '<img src=x onerror=alert(1)>'
        }, content_type='application/json')
        
        # Should succeed but sanitize
        self.profile1.refresh_from_db()
        
        # Display name should not contain script tags
        self.assertNotIn('<script>', self.profile1.display_name)
        self.assertNotIn('<img', self.profile1.bio)
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        url = reverse('user_profile:update_basic_info')
        
        # Attempt SQL injection
        response = self.client.post(url, {
            'display_name': "'; DROP TABLE users; --"
        }, content_type='application/json')
        
        # Should not crash
        self.assertIn(response.status_code, [200, 400])
        
        # User should still exist
        self.assertTrue(User.objects.filter(id=self.user1.id).exists())


# Test runner helper
def run_all_tests():
    """Run all settings API tests"""
    import sys
    from django.core.management import call_command
    
    # Run tests
    result = call_command('test', 'tests.test_settings_api', verbosity=2)
    
    sys.exit(0 if result == 0 else 1)


if __name__ == '__main__':
    run_all_tests()
