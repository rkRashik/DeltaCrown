"""
Smoke tests for settings endpoints - verify they respond correctly.
Tests actual HTTP behavior without UI.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from io import BytesIO
from PIL import Image
import json

User = get_user_model()


class SettingsEndpointsSmokeTest(TestCase):
    """Verify settings endpoints return expected responses."""
    
    def setUp(self):
        """Create test user and authenticate."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_update_basic_info_no_crash(self):
        """POST /me/settings/basic/ should not crash (200 or 302)."""
        url = reverse('user_profile:update_basic_info')
        response = self.client.post(url, {
            'display_name': 'Test User',
            'bio': 'Test bio',
            'country': 'Bangladesh'
        })
        
        # Should redirect or return 200, NOT 500
        self.assertIn(response.status_code, [200, 302], 
                     f"Expected 200 or 302, got {response.status_code}")
        
        # Should NOT have AttributeError in response
        if response.status_code == 500:
            self.fail("Got 500 error - check for AttributeError in logs")
    
    def test_upload_media_returns_json(self):
        """POST /me/settings/media/ should return JSON, not HTML."""
        url = reverse('user_profile:upload_media')
        
        # Create a small test image in memory
        image = Image.new('RGB', (200, 200), color='red')
        image_file = BytesIO()
        image.save(image_file, 'JPEG')
        image_file.seek(0)
        image_file.name = 'test.jpg'
        
        response = self.client.post(url, {
            'media_type': 'avatar',
            'file': image_file
        })
        
        # Should return JSON, not HTML
        self.assertEqual(response.status_code, 200, 
                        f"Expected 200, got {response.status_code}")
        self.assertEqual(response['Content-Type'], 'application/json',
                        f"Expected JSON, got {response['Content-Type']}")
        
        # Parse JSON
        data = json.loads(response.content)
        self.assertIn('success', data, "Response should have 'success' field")
    
    def test_update_social_links_returns_json(self):
        """POST /api/social-links/update/ should return JSON."""
        url = reverse('user_profile:update_social_links_api')
        
        payload = {
            'links': [
                {'platform': 'twitch', 'url': 'https://twitch.tv/testuser'},
                {'platform': 'youtube', 'url': 'https://youtube.com/@testuser'}
            ]
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return JSON, not HTML (not 404)
        self.assertNotEqual(response.status_code, 404,
                           "Endpoint should exist (not 404)")
        self.assertEqual(response.status_code, 200,
                        f"Expected 200, got {response.status_code}")
        self.assertEqual(response['Content-Type'], 'application/json',
                        f"Expected JSON, got {response['Content-Type']}")
        
        # Parse JSON
        data = json.loads(response.content)
        self.assertIn('success', data, "Response should have 'success' field")
    
    def test_update_privacy_returns_json(self):
        """POST /me/settings/privacy/save/ should return JSON, not redirect."""
        url = reverse('user_profile:update_privacy_settings')
        
        payload = {
            'privacy_settings': {
                'show_social_links': True,
                'show_activity_feed': False,
                'show_game_ids': True
            }
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return JSON, not redirect (not 302)
        self.assertNotEqual(response.status_code, 404,
                           "Endpoint should exist (not 404)")
        self.assertEqual(response.status_code, 200,
                        f"Expected 200, got {response.status_code}")
        self.assertEqual(response['Content-Type'], 'application/json',
                        f"Expected JSON, got {response['Content-Type']}")
        
        # Parse JSON
        data = json.loads(response.content)
        self.assertIn('success', data, "Response should have 'success' field")
    
    def test_endpoints_require_auth(self):
        """All endpoints should require authentication."""
        self.client.logout()
        
        endpoints = [
            reverse('user_profile:update_basic_info'),
            reverse('user_profile:upload_media'),
            reverse('user_profile:update_social_links_api'),
            reverse('user_profile:update_privacy_settings'),
        ]
        
        for url in endpoints:
            response = self.client.post(url)
            # Should redirect to login (302) or return 403
            self.assertIn(response.status_code, [302, 403],
                         f"Endpoint {url} should require auth, got {response.status_code}")
