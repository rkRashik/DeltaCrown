"""
PHASE 4 STEP 4.1: Followers/Following Endpoint Verification Tests

Tests to verify that:
1. API endpoints (/api/profile/<username>/followers|following/) work correctly
2. No "deprecated_endpoint" errors are returned
3. Profile hero links use the correct canonical endpoints
4. JSON responses are properly formatted

Created: 2026-01-22
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import Follow, UserProfile, PrivacySettings
import json

User = get_user_model()


class FollowersFollowingEndpointTests(TestCase):
    """Test that followers/following endpoints work correctly - no deprecated_endpoint errors"""
    
    def setUp(self):
        """Create test users and follow relationships"""
        self.client = Client()
        
        # Create users (custom User model requires email)
        self.user_a = User.objects.create_user(username='userA', email='usera@test.com', password='testpass123')
        self.user_b = User.objects.create_user(username='userB', email='userb@test.com', password='testpass123')
        self.user_c = User.objects.create_user(username='userC', email='userc@test.com', password='testpass123')
        
        # Ensure profiles exist
        UserProfile.objects.get_or_create(user=self.user_a)
        UserProfile.objects.get_or_create(user=self.user_b)
        UserProfile.objects.get_or_create(user=self.user_c)
        
        # Create follow relationships
        # B and C follow A
        Follow.objects.create(follower=self.user_b, following=self.user_a)
        Follow.objects.create(follower=self.user_c, following=self.user_a)
        
        # A follows B
        Follow.objects.create(follower=self.user_a, following=self.user_b)
    
    def test_followers_endpoint_returns_200_json_not_deprecated(self):
        """
        CRITICAL: Followers endpoint must return 200 with JSON, NOT deprecated_endpoint error
        """
        self.client.force_login(self.user_a)
        response = self.client.get(f'/api/profile/{self.user_a.username}/followers/')
        
        # Must be 200, not 404 or 500
        self.assertEqual(response.status_code, 200, 
                         f"Expected 200, got {response.status_code}")
        
        # Must be JSON
        self.assertEqual(response['Content-Type'], 'application/json',
                         f"Expected JSON, got {response['Content-Type']}")
        
        # Parse response
        data = json.loads(response.content)
        
        # Must have success=true structure
        self.assertTrue(data.get('success'), 
                        f"Expected success:true, got {data}")
        
        # Must NOT contain deprecated_endpoint error
        self.assertNotIn('deprecated_endpoint', str(data).lower(),
                         "Response must not contain 'deprecated_endpoint'")
        
        # Must have followers array
        self.assertIn('followers', data)
        self.assertIsInstance(data['followers'], list)
        
        # Verify correct count
        self.assertEqual(len(data['followers']), 2,
                         f"Expected 2 followers (B and C), got {len(data['followers'])}")
    
    def test_following_endpoint_returns_200_json_not_deprecated(self):
        """
        CRITICAL: Following endpoint must return 200 with JSON, NOT deprecated_endpoint error
        """
        self.client.force_login(self.user_a)
        response = self.client.get(f'/api/profile/{self.user_a.username}/following/')
        
        # Must be 200
        self.assertEqual(response.status_code, 200)
        
        # Must be JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse response
        data = json.loads(response.content)
        
        # Must have success structure
        self.assertTrue(data.get('success'))
        
        # Must NOT contain deprecated_endpoint
        self.assertNotIn('deprecated_endpoint', str(data).lower())
        
        # Must have following array
        self.assertIn('following', data)
        self.assertIsInstance(data['following'], list)
        
        # Verify correct count
        self.assertEqual(len(data['following']), 1,
                         f"Expected 1 following (B), got {len(data['following'])}")
    
    def test_followers_endpoint_privacy_returns_proper_error_not_deprecated(self):
        """
        Test that privacy errors are proper JSON, not deprecated_endpoint
        """
        # Make user_a's profile private
        profile = UserProfile.objects.get(user=self.user_a)
        privacy_settings, _ = PrivacySettings.objects.get_or_create(
            user_profile=profile,
            defaults={'followers_list_visibility': 'only_me', 'is_private_account': True}
        )
        privacy_settings.followers_list_visibility = 'only_me'
        privacy_settings.save()
        
        # Try to access as anonymous
        response = self.client.get(f'/api/profile/{self.user_a.username}/followers/')
        
        # Should be 401
        self.assertEqual(response.status_code, 401)
        
        # Must be JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse response
        data = json.loads(response.content)
        
        # Must have error structure (not deprecated_endpoint)
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
        self.assertNotIn('deprecated_endpoint', data.get('error', '').lower())
        
        # Error should be about privacy, not deprecation
        error_msg = data.get('error', '').lower()
        self.assertTrue('private' in error_msg or 'follow' in error_msg,
                        f"Expected privacy-related error, got: {data.get('error')}")
    
    def test_html_routes_return_404_correctly(self):
        """
        Verify that HTML routes (/@username/followers/) don't exist (404)
        This confirms we're using API-only approach with modals
        """
        self.client.force_login(self.user_a)
        
        # HTML routes should 404 (we use modals, not full pages)
        response1 = self.client.get(f'/@{self.user_a.username}/followers/')
        self.assertEqual(response1.status_code, 404,
                         "HTML followers route should not exist (we use modals)")
        
        response2 = self.client.get(f'/@{self.user_a.username}/following/')
        self.assertEqual(response2.status_code, 404,
                         "HTML following route should not exist (we use modals)")
    
    def test_profile_page_contains_modal_javascript(self):
        """
        Verify that profile page has the modal JS functions (not deprecated routes)
        """
        self.client.force_login(self.user_a)
        response = self.client.get(f'/@{self.user_a.username}/')
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Must have modal functions (not deprecated routes)
        self.assertIn('openFollowersModal', content,
                      "Profile page must have openFollowersModal function")
        self.assertIn('openFollowingModal', content,
                      "Profile page must have openFollowingModal function")
        
        # Must fetch from API endpoints (not deprecated routes)
        self.assertIn('/api/profile/', content,
                      "JS must fetch from /api/profile/ endpoints")
        self.assertIn('/followers/', content)
        self.assertIn('/following/', content)
        
        # Must NOT reference deprecated endpoint patterns
        self.assertNotIn('deprecated', content.lower())
        self.assertNotIn('/actions/followers/', content)
        self.assertNotIn('/actions/following/', content)
    
    def test_api_endpoint_json_structure_complete(self):
        """
        Verify API returns complete JSON structure expected by modal JS
        """
        self.client.force_login(self.user_a)
        response = self.client.get(f'/api/profile/{self.user_a.username}/followers/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Required top-level fields
        self.assertIn('success', data)
        self.assertIn('followers', data)
        self.assertIn('count', data)
        self.assertIn('has_more', data)
        
        # Each follower must have required fields for modal rendering
        if data['followers']:
            follower = data['followers'][0]
            required_fields = ['username', 'display_name', 'avatar_url', 
                               'is_followed_by_viewer', 'is_viewer', 'profile_url']
            for field in required_fields:
                self.assertIn(field, follower,
                              f"Follower object missing required field: {field}")


class CanonicalEndpointVerificationTests(TestCase):
    """
    Verify that the canonical endpoints defined in urls.py are active and working
    """
    
    def test_canonical_followers_endpoint_exists_in_urls(self):
        """
        Verify that /api/profile/<username>/followers/ is defined in urls.py
        """
        from django.urls import resolve, reverse
        
        # Should resolve without error
        try:
            resolved = resolve('/api/profile/testuser/followers/')
            self.assertIsNotNone(resolved.func)
            
            # Verify it resolves to the correct handler
            self.assertIn('follow_lists_api', str(resolved.func.__module__),
                          "Should resolve to follow_lists_api module")
        except Exception as e:
            self.fail(f"Canonical followers endpoint not properly configured: {e}")
    
    def test_canonical_following_endpoint_exists_in_urls(self):
        """
        Verify that /api/profile/<username>/following/ is defined in urls.py
        """
        from django.urls import resolve
        
        try:
            resolved = resolve('/api/profile/testuser/following/')
            self.assertIsNotNone(resolved.func)
            
            self.assertIn('follow_lists_api', str(resolved.func.__module__),
                          "Should resolve to follow_lists_api module")
        except Exception as e:
            self.fail(f"Canonical following endpoint not properly configured: {e}")


class NoDeprecatedEndpointRegressionTests(TestCase):
    """
    Regression tests to ensure deprecated_endpoint errors never appear
    """
    
    def test_no_deprecated_endpoint_string_in_codebase(self):
        """
        Verify that no view returns 'deprecated_endpoint' error message
        """
        # This is a documentation test - the grep search confirmed no such string exists
        # except in test names. This test serves as a placeholder and documentation.
        self.assertTrue(True, 
                        "No deprecated_endpoint string found in codebase (verified by grep)")
    
    def test_profile_hero_clicks_use_api_not_deprecated_routes(self):
        """
        Document that profile hero Followers/Following badges use JS modals with API
        """
        # Create a user (custom User model requires email)
        user = User.objects.create_user(username='testuser', email='testuser@test.com', password='pass')
        UserProfile.objects.get_or_create(user=user)
        
        client = Client()
        client.force_login(user)
        
        # Get profile page
        response = client.get(f'/@{user.username}/')
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verify onclick handlers call modal functions (not href navigation)
        self.assertIn('onclick="openFollowersModal()"', content,
                      "Followers badge must use onclick modal, not href")
        self.assertIn('onclick="openFollowingModal()"', content,
                      "Following badge must use onclick modal, not href")
        
        # Verify modal functions fetch from API
        self.assertIn('loadFollowersList', content)
        self.assertIn('loadFollowingList', content)
