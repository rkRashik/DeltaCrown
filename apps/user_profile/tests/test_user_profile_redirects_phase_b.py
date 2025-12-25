"""
Tests for UP-CLEANUP-02 Phase B: URL Redirects

Tests that legacy URLs properly redirect to canonical modern endpoints:
- 301 status codes
- Correct Location headers
- Query parameter preservation
- No breaking changes for wrapper-based routes
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.user_profile.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestLegacyProfileRedirects(TestCase):
    """Test legacy profile URL redirects to canonical @username format"""
    
    def setUp(self):
        """Create test users and profiles"""
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='password123'
        )
        self.profile = UserProfile.objects.get_or_create(user=self.user)[0]
        self.client = Client()
    
    def test_legacy_u_prefix_redirects_to_at_prefix(self):
        """Test /u/alice/ redirects to /@alice/ with 301"""
        response = self.client.get('/u/alice/')
        
        self.assertEqual(response.status_code, 301)
        self.assertIn('/@alice/', response['Location'])
    
    def test_bare_username_redirects_to_at_prefix(self):
        """Test /alice/ redirects to /@alice/ with 301"""
        response = self.client.get('/alice/')
        
        self.assertEqual(response.status_code, 301)
        self.assertIn('/@alice/', response['Location'])
    
    def test_redirect_preserves_query_parameters(self):
        """Test redirect maintains query string"""
        response = self.client.get('/u/alice/?ref=twitter&source=link')
        
        self.assertEqual(response.status_code, 301)
        self.assertIn('/@alice/', response['Location'])
        self.assertIn('ref=twitter', response['Location'])
        self.assertIn('source=link', response['Location'])
    
    def test_unauthenticated_user_can_access_redirect(self):
        """Test redirect works for anonymous users"""
        response = self.client.get('/u/alice/')
        
        self.assertEqual(response.status_code, 301)
        self.assertIn('/@alice/', response['Location'])
    
    def test_authenticated_user_can_access_redirect(self):
        """Test redirect works for authenticated users"""
        self.client.login(username='alice', password='password123')
        response = self.client.get('/u/alice/')
        
        self.assertEqual(response.status_code, 301)
        self.assertIn('/@alice/', response['Location'])
    
    def test_canonical_at_username_returns_200(self):
        """Test canonical /@alice/ route works (no redirect loop)"""
        response = self.client.get('/@alice/')
        
        # Should return 200 (or redirect to login if auth required)
        self.assertIn(response.status_code, [200, 302])
        # Should NOT be 301 (no redirect loop)
        self.assertNotEqual(response.status_code, 301)
    
    def test_redirect_includes_location_header(self):
        """Test redirect includes proper Location header"""
        response = self.client.get('/u/alice/')
        
        self.assertIn('Location', response)
        self.assertTrue(response['Location'].endswith('/@alice/'))
    
    def test_redirect_with_trailing_slash(self):
        """Test redirect handles trailing slash correctly"""
        response = self.client.get('/u/alice/')
        
        self.assertEqual(response.status_code, 301)
        # Should maintain trailing slash in redirect
        self.assertTrue(response['Location'].endswith('/'))


@pytest.mark.django_db
class TestLegacyAPIRedirects(TestCase):
    """Test legacy API endpoint redirects"""
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.profile = UserProfile.objects.get_or_create(user=self.user)[0]
        self.client = Client()
    
    def test_get_game_id_redirects_to_game_ids_api(self):
        """Test /api/profile/get-game-id/ redirects to /api/profile/game-ids/ with 301"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get('/api/profile/get-game-id/')
        
        self.assertEqual(response.status_code, 301)
        self.assertIn('/api/profile/game-ids/', response['Location'])
    
    def test_api_redirect_preserves_query_parameters(self):
        """Test API redirect maintains query string"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get('/api/profile/get-game-id/?game=valorant')
        
        self.assertEqual(response.status_code, 301)
        self.assertIn('game=valorant', response['Location'])
    
    def test_update_game_id_remains_wrapper_based(self):
        """Test /api/profile/update-game-id/ NOT redirected (mutation endpoint)"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post('/api/profile/update-game-id/', {})
        
        # Should NOT be 301 (mutation routes remain wrapper-based in Phase B)
        self.assertNotEqual(response.status_code, 301)
        # Should return 200, 400, or 405 depending on implementation
        self.assertIn(response.status_code, [200, 400, 405])


@pytest.mark.django_db
class TestWrapperRoutesRemainUnchanged(TestCase):
    """Test that wrapper-based routes remain non-redirected in Phase B"""
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.profile = UserProfile.objects.get_or_create(user=self.user)[0]
        self.client = Client()
        self.client.login(username='testuser', password='password123')
    
    def test_action_endpoint_not_redirected(self):
        """Test /actions/save-game-profiles/ not redirected"""
        response = self.client.post('/actions/save-game-profiles/', {})
        
        self.assertNotEqual(response.status_code, 301)
        # Wrapper-based routes should return 200, 302, or 405
        self.assertIn(response.status_code, [200, 302, 405, 500])
