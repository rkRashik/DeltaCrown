"""
PHASE4_STEP5: Critical Tests - Followers/Following Must NOT Return 410 Gone

These tests verify that the endpoints return proper status codes (200/401/403), NOT 410 Gone.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, PrivacySettings, Follow
import json

User = get_user_model()


class FollowersFollowingNot410Tests(TestCase):
    """
    CRITICAL: Verify /api/profile/<username>/followers/ and /following/ do NOT return 410 Gone
    """
    
    def setUp(self):
        # Create test users
        self.user_a = User.objects.create_user(
            username='userA',
            email='usera@test.com',
            password='testpass123'
        )
        self.user_b = User.objects.create_user(
            username='userB',
            email='userb@test.com',
            password='testpass123'
        )
        
        # Create profiles
        self.profile_a, _ = UserProfile.objects.get_or_create(user=self.user_a)
        self.profile_b, _ = UserProfile.objects.get_or_create(user=self.user_b)
        
        # Create privacy settings (public by default)
        self.privacy_a, _ = PrivacySettings.objects.get_or_create(
            user_profile=self.profile_a,
            defaults={
                'followers_list_visibility': 'everyone',
                'following_list_visibility': 'everyone',
                'is_private_account': False
            }
        )
        
        # UserB follows UserA
        Follow.objects.create(follower=self.user_b, following=self.user_a)
        
        self.client = Client()
    
    def test_followers_endpoint_not_410(self):
        """
        CRITICAL: GET /api/profile/<username>/followers/ must NOT return 410 Gone
        """
        self.client.force_login(self.user_a)
        response = self.client.get(
            f'/api/profile/{self.user_a.username}/followers/',
            HTTP_ACCEPT='application/json'
        )
        
        # MUST NOT BE 410
        self.assertNotEqual(response.status_code, 410,
                            f"Followers endpoint returned 410 Gone! Response: {response.content}")
        
        # MUST BE 200 for owner
        self.assertEqual(response.status_code, 200,
                         f"Expected 200, got {response.status_code}. Response: {response.content}")
        
        # MUST return JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # MUST have valid JSON structure
        data = json.loads(response.content)
        self.assertTrue(data.get('success'),
                        f"Expected success=true, got: {data}")
        self.assertIn('followers', data,
                      "Response must contain 'followers' key")
    
    def test_following_endpoint_not_410(self):
        """
        CRITICAL: GET /api/profile/<username>/following/ must NOT return 410 Gone
        """
        self.client.force_login(self.user_a)
        response = self.client.get(
            f'/api/profile/{self.user_a.username}/following/',
            HTTP_ACCEPT='application/json'
        )
        
        # MUST NOT BE 410
        self.assertNotEqual(response.status_code, 410,
                            f"Following endpoint returned 410 Gone! Response: {response.content}")
        
        # MUST BE 200 for owner
        self.assertEqual(response.status_code, 200,
                         f"Expected 200, got {response.status_code}. Response: {response.content}")
        
        # MUST return JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # MUST have valid JSON structure
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))
        self.assertIn('following', data)
    
    def test_followers_privacy_enforced(self):
        """
        Verify privacy settings are enforced (403 for forbidden, NOT 410)
        """
        # Make UserA's followers list private
        self.privacy_a.followers_list_visibility = 'only_me'
        self.privacy_a.save()
        
        # UserB tries to view UserA's followers
        self.client.force_login(self.user_b)
        response = self.client.get(
            f'/api/profile/{self.user_a.username}/followers/',
            HTTP_ACCEPT='application/json'
        )
        
        # MUST NOT BE 410
        self.assertNotEqual(response.status_code, 410,
                            "Privacy-blocked request should return 403, NOT 410")
        
        # MUST BE 403 (Forbidden)
        self.assertEqual(response.status_code, 403,
                         f"Expected 403 for privacy block, got {response.status_code}")
        
        # MUST return JSON error
        data = json.loads(response.content)
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
    
    def test_following_privacy_enforced(self):
        """
        Verify following list privacy (403 for forbidden, NOT 410)
        """
        # Make UserA's following list private
        self.privacy_a.following_list_visibility = 'only_me'
        self.privacy_a.save()
        
        # UserB tries to view UserA's following
        self.client.force_login(self.user_b)
        response = self.client.get(
            f'/api/profile/{self.user_a.username}/following/',
            HTTP_ACCEPT='application/json'
        )
        
        # MUST NOT BE 410
        self.assertNotEqual(response.status_code, 410,
                            "Privacy-blocked request should return 403, NOT 410")
        
        # MUST BE 403
        self.assertEqual(response.status_code, 403)
        
        # MUST return JSON error
        data = json.loads(response.content)
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
    
    def test_followers_requires_auth_json_401(self):
        """
        Anonymous users get 401 JSON (NOT 410, NOT redirect)
        """
        # Make UserA's followers list "followers only"
        self.privacy_a.followers_list_visibility = 'followers'
        self.privacy_a.save()
        
        # Anonymous request
        response = self.client.get(
            f'/api/profile/{self.user_a.username}/followers/',
            HTTP_ACCEPT='application/json'
        )
        
        # MUST NOT BE 410
        self.assertNotEqual(response.status_code, 410,
                            "Anonymous request should return 401, NOT 410")
        
        # MUST BE 401 (Unauthorized)
        self.assertEqual(response.status_code, 401,
                         f"Expected 401 for anonymous, got {response.status_code}")
        
        # MUST return JSON (not redirect)
        self.assertEqual(response['Content-Type'], 'application/json',
                         "Must return JSON, not redirect")
        
        # MUST have error message
        data = json.loads(response.content)
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
    
    def test_following_requires_auth_json_401(self):
        """
        Anonymous users get 401 JSON for following endpoint (NOT 410, NOT redirect)
        """
        # Make UserA's following list "followers only"
        self.privacy_a.following_list_visibility = 'followers'
        self.privacy_a.save()
        
        # Anonymous request
        response = self.client.get(
            f'/api/profile/{self.user_a.username}/following/',
            HTTP_ACCEPT='application/json'
        )
        
        # MUST NOT BE 410
        self.assertNotEqual(response.status_code, 410,
                            "Anonymous request should return 401, NOT 410")
        
        # MUST BE 401
        self.assertEqual(response.status_code, 401)
        
        # MUST return JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # MUST have error message
        data = json.loads(response.content)
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
    
    def test_followers_with_private_account(self):
        """
        Private account enforcement (403 for non-followers, NOT 410)
        """
        # Make UserA's account private
        self.privacy_a.is_private_account = True
        self.privacy_a.followers_list_visibility = 'everyone'  # But account is private
        self.privacy_a.save()
        
        # UserB is already following, so should still see
        self.client.force_login(self.user_b)
        response = self.client.get(
            f'/api/profile/{self.user_a.username}/followers/',
            HTTP_ACCEPT='application/json'
        )
        
        # MUST NOT BE 410
        self.assertNotEqual(response.status_code, 410)
        
        # MUST BE 200 (UserB follows UserA)
        self.assertEqual(response.status_code, 200)
        
        # Now test with UserC who doesn't follow UserA
        user_c = User.objects.create_user(
            username='userC',
            email='userc@test.com',
            password='testpass123'
        )
        self.client.force_login(user_c)
        response = self.client.get(
            f'/api/profile/{self.user_a.username}/followers/',
            HTTP_ACCEPT='application/json'
        )
        
        # MUST NOT BE 410
        self.assertNotEqual(response.status_code, 410,
                            "Private account block should return 403, NOT 410")
        
        # MUST BE 403
        self.assertEqual(response.status_code, 403,
                         "Non-follower viewing private account should get 403")
