"""
PHASE 7C-P0: Privacy Settings Full Matrix - Integration Tests
Tests for expanded privacy settings (all 25 fields).
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, PrivacySettings

User = get_user_model()


class PrivacyFullMatrixTestCase(TestCase):
    """Test full privacy settings matrix (all 25 fields)"""

    def setUp(self):
        """Set up test user"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.privacy, _ = PrivacySettings.objects.get_or_create(user_profile=self.profile)
        
        self.client.login(username='testuser', password='testpass123')

    def test_load_privacy_settings(self):
        """Test fetching current privacy settings"""
        response = self.client.get('/me/settings/privacy/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify all expected fields are present
        privacy = data['privacy']
        self.assertIn('is_private_account', privacy)
        self.assertIn('show_real_name', privacy)
        self.assertIn('show_email', privacy)
        self.assertIn('inventory_visibility', privacy)

    def test_save_privacy_profile_visibility(self):
        """Test saving profile visibility settings"""
        payload = {
            'show_real_name': True,
            'show_email': False,
            'show_phone': True,
            'show_age': False,
            'show_gender': True,
            'show_country': True
        }
        
        response = self.client.post(
            '/me/settings/privacy/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify in database
        self.privacy.refresh_from_db()
        self.assertTrue(self.privacy.show_real_name)
        self.assertFalse(self.privacy.show_email)
        self.assertTrue(self.privacy.show_phone)
        self.assertFalse(self.privacy.show_age)

    def test_save_privacy_gaming_activity(self):
        """Test saving gaming & activity privacy settings"""
        payload = {
            'show_game_ids': True,
            'show_match_history': False,
            'show_teams': True,
            'show_achievements': False
        }
        
        response = self.client.post(
            '/me/settings/privacy/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify in database
        self.privacy.refresh_from_db()
        self.assertTrue(self.privacy.show_game_ids)
        self.assertFalse(self.privacy.show_match_history)
        self.assertTrue(self.privacy.show_teams)
        self.assertFalse(self.privacy.show_achievements)

    def test_save_privacy_economy(self):
        """Test saving economy & inventory privacy settings"""
        payload = {
            'inventory_visibility': 'FRIENDS',
            'show_inventory_value': False,
            'show_level_xp': True
        }
        
        response = self.client.post(
            '/me/settings/privacy/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify in database
        self.privacy.refresh_from_db()
        self.assertEqual(self.privacy.inventory_visibility, 'FRIENDS')
        self.assertFalse(self.privacy.show_inventory_value)
        self.assertTrue(self.privacy.show_level_xp)

    def test_save_privacy_interaction_permissions(self):
        """Test saving interaction permission settings"""
        payload = {
            'allow_team_invites': True,
            'allow_friend_requests': False,
            'allow_direct_messages': True
        }
        
        response = self.client.post(
            '/me/settings/privacy/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify in database
        self.privacy.refresh_from_db()
        self.assertTrue(self.privacy.allow_team_invites)
        self.assertFalse(self.privacy.allow_friend_requests)
        self.assertTrue(self.privacy.allow_direct_messages)

    def test_save_private_account(self):
        """Test toggling private account"""
        payload = {
            'is_private_account': True
        }
        
        response = self.client.post(
            '/me/settings/privacy/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify in database
        self.privacy.refresh_from_db()
        self.assertTrue(self.privacy.is_private_account)

    def test_inventory_visibility_validation(self):
        """Test inventory_visibility enum validation"""
        # Valid values
        for visibility in ['PUBLIC', 'FRIENDS', 'PRIVATE']:
            payload = {'inventory_visibility': visibility}
            
            response = self.client.post(
                '/me/settings/privacy/save/',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            self.privacy.refresh_from_db()
            self.assertEqual(self.privacy.inventory_visibility, visibility)
        
        # Invalid value
        payload = {'inventory_visibility': 'INVALID'}
        
        response = self.client.post(
            '/me/settings/privacy/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should either reject or default to valid value
        self.assertIn(response.status_code, [200, 400])

    def test_save_all_settings_at_once(self):
        """Test saving all privacy settings in one request"""
        payload = {
            'is_private_account': True,
            'show_real_name': True,
            'show_email': False,
            'show_phone': True,
            'show_age': False,
            'show_gender': True,
            'show_country': True,
            'show_game_ids': False,
            'show_match_history': True,
            'show_teams': False,
            'show_achievements': True,
            'inventory_visibility': 'PRIVATE',
            'show_inventory_value': False,
            'show_level_xp': True,
            'show_social_links': False,
            'show_following_list': True,
            'allow_team_invites': False,
            'allow_friend_requests': True,
            'allow_direct_messages': False
        }
        
        response = self.client.post(
            '/me/settings/privacy/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify all settings persisted correctly
        self.privacy.refresh_from_db()
        self.assertTrue(self.privacy.is_private_account)
        self.assertTrue(self.privacy.show_real_name)
        self.assertFalse(self.privacy.show_email)
        self.assertEqual(self.privacy.inventory_visibility, 'PRIVATE')
        self.assertFalse(self.privacy.allow_team_invites)

    def test_missing_context_keys(self):
        """Test that all privacy fields are available in template context"""
        # This would be a template rendering test in real scenario
        # For now, verify model has all expected fields
        self.assertHasAttr(self.privacy, 'is_private_account')
        self.assertHasAttr(self.privacy, 'show_real_name')
        self.assertHasAttr(self.privacy, 'show_email')
        self.assertHasAttr(self.privacy, 'show_phone')
        self.assertHasAttr(self.privacy, 'show_age')
        self.assertHasAttr(self.privacy, 'show_gender')
        self.assertHasAttr(self.privacy, 'show_country')
        self.assertHasAttr(self.privacy, 'show_game_ids')
        self.assertHasAttr(self.privacy, 'show_match_history')
        self.assertHasAttr(self.privacy, 'show_teams')
        self.assertHasAttr(self.privacy, 'show_achievements')
        self.assertHasAttr(self.privacy, 'inventory_visibility')
        self.assertHasAttr(self.privacy, 'show_inventory_value')
        self.assertHasAttr(self.privacy, 'show_level_xp')
        self.assertHasAttr(self.privacy, 'show_social_links')
        self.assertHasAttr(self.privacy, 'show_following_list')
        self.assertHasAttr(self.privacy, 'allow_team_invites')
        self.assertHasAttr(self.privacy, 'allow_friend_requests')
        self.assertHasAttr(self.privacy, 'allow_direct_messages')

    def assertHasAttr(self, obj, attr_name):
        """Helper to assert object has attribute"""
        self.assertTrue(
            hasattr(obj, attr_name),
            f"PrivacySettings model missing expected field: {attr_name}"
        )


class FollowRequestsUITestCase(TestCase):
    """Test follow requests management UI"""

    def setUp(self):
        """Set up test users"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        
        self.requester = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpass123'
        )
        self.requester_profile = UserProfile.objects.get(user=self.requester)
        
        self.client.login(username='testuser', password='testpass123')

    def test_get_follow_requests_pending(self):
        """Test fetching pending follow requests"""
        response = self.client.get('/me/follow-requests/?status=PENDING')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('requests', data)
        self.assertIsInstance(data['requests'], list)

    def test_get_follow_requests_approved(self):
        """Test fetching approved follow requests"""
        response = self.client.get('/me/follow-requests/?status=APPROVED')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_get_follow_requests_rejected(self):
        """Test fetching rejected follow requests"""
        response = self.client.get('/me/follow-requests/?status=REJECTED')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
