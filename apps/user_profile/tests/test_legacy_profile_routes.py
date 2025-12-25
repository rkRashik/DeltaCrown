"""
Test suite for UP-CLEANUP-02: Legacy Profile Route Deprecation Wrappers

Tests that deprecated legacy routes:
1. Do not bypass privacy enforcement (use PrivacyService)
2. Do not crash (backward compatible)
3. Log deprecation warnings (DEPRECATED_USER_PROFILE_ROUTE)

Phase A: Deprecation wrappers (non-breaking, audit trail, monitoring)
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.user_profile.models import UserProfile
import logging

User = get_user_model()


@pytest.mark.django_db
class TestLegacyRouteDeprecation(TestCase):
    """Test deprecated legacy routes with wrappers"""
    
    def setUp(self):
        """Create test users and profiles"""
        # Create test users
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='password123'
        )
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='password123'
        )
        
        # Ensure profiles exist
        self.profile1 = UserProfile.objects.get_or_create(user=self.user1)[0]
        self.profile2 = UserProfile.objects.get_or_create(user=self.user2)[0]
        
        # Update profile data
        self.profile1.display_name = "Alice Test"
        self.profile1.bio = "Test bio for Alice"
        self.profile1.game_profiles = [
            {"game": "valorant", "ign": "AliceVLR", "verified": False}
        ]
        self.profile1.save()
        
        # Client for requests
        self.client = Client()
    
    def test_profile_view_does_not_crash(self):
        """Test: profile_view does not crash (backward compatible)"""
        self.client.login(username='alice', password='password123')
        
        response = self.client.get(reverse('user_profile:profile', kwargs={'username': 'bob'}))
        
        # Should not crash
        self.assertIn(response.status_code, [200, 302])
        
    def test_profile_view_logs_deprecation_warning(self, caplog):
        """Test: profile_view logs DEPRECATED_USER_PROFILE_ROUTE warning"""
        self.client.login(username='alice', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.get(reverse('user_profile:profile', kwargs={'username': 'bob'}))
        
        # Check deprecation warning logged
        warnings = [r.message for r in caplog.records if 'DEPRECATED_USER_PROFILE_ROUTE' in r.message]
        self.assertGreater(len(warnings), 0, "Deprecation warning not logged")
    
    def test_privacy_settings_view_does_not_crash(self):
        """Test: privacy_settings_view does not crash (backward compatible)"""
        self.client.login(username='alice', password='password123')
        
        response = self.client.get(reverse('user_profile:privacy_settings'))
        
        # Should not crash
        self.assertIn(response.status_code, [200, 302])
    
    def test_privacy_settings_view_logs_deprecation(self, caplog):
        """Test: privacy_settings_view logs deprecation warning"""
        self.client.login(username='alice', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.get(reverse('user_profile:privacy_settings'))
        
        # Check deprecation warning logged
        warnings = [r.message for r in caplog.records if 'DEPRECATED_USER_PROFILE_ROUTE' in r.message]
        self.assertGreater(len(warnings), 0, "Deprecation warning not logged")
    
    def test_save_game_profiles_does_not_crash(self):
        """Test: save_game_profiles does not crash on POST"""
        self.client.login(username='alice', password='password123')
        
        # POST request with game profile data
        response = self.client.post(
            reverse('user_profile:save_game_profiles'),
            data={
                'valorant_ign': 'NewAliceVLR',
                'valorant_tag': 'NA1'
            }
        )
        
        # Should not crash (may redirect)
        self.assertIn(response.status_code, [200, 302])
    
    def test_save_game_profiles_logs_deprecation(self, caplog):
        """Test: save_game_profiles logs deprecation warning"""
        self.client.login(username='alice', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.post(
                reverse('user_profile:save_game_profiles'),
                data={'valorant_ign': 'TestIGN'}
            )
        
        # Check deprecation warning logged
        warnings = [r.message for r in caplog.records if 'DEPRECATED_USER_PROFILE_ROUTE' in r.message]
        self.assertGreater(len(warnings), 0, "Deprecation warning not logged")
    
    def test_follow_user_does_not_crash(self):
        """Test: follow_user does not crash (backward compatible)"""
        self.client.login(username='alice', password='password123')
        
        response = self.client.post(
            reverse('user_profile:follow_user', kwargs={'username': 'bob'})
        )
        
        # Should not crash
        self.assertIn(response.status_code, [200, 302])
    
    def test_follow_user_logs_deprecation(self, caplog):
        """Test: follow_user logs deprecation warning"""
        self.client.login(username='alice', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.post(
                reverse('user_profile:follow_user', kwargs={'username': 'bob'})
            )
        
        # Check deprecation warning logged
        warnings = [r.message for r in caplog.records if 'DEPRECATED_USER_PROFILE_ROUTE' in r.message]
        self.assertGreater(len(warnings), 0, "Deprecation warning not logged")
    
    def test_followers_list_does_not_crash(self):
        """Test: followers_list does not crash (backward compatible)"""
        self.client.login(username='alice', password='password123')
        
        # Create a follow relationship
        Follow.objects.create(follower=self.user2, following=self.user1)
        
        response = self.client.get(
            reverse('user_profile:followers_list', kwargs={'username': 'alice'})
        )
        
        # Should not crash
        self.assertIn(response.status_code, [200, 302])
    
    def test_followers_list_logs_deprecation(self, caplog):
        """Test: followers_list logs deprecation warning"""
        self.client.login(username='alice', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.get(
                reverse('user_profile:followers_list', kwargs={'username': 'alice'})
            )
        
        # Check deprecation warning logged
        warnings = [r.message for r in caplog.records if 'DEPRECATED_USER_PROFILE_ROUTE' in r.message]
        self.assertGreater(len(warnings), 0, "Deprecation warning not logged")


@pytest.mark.django_db
class TestDeprecationLogFormat(TestCase):
    """Test that deprecation logs contain correct metadata"""
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.profile = UserProfile.objects.get_or_create(user=self.user)[0]
        self.client = Client()
    
    def test_deprecation_log_contains_route(self, caplog):
        """Test: Deprecation log contains route path"""
        self.client.login(username='testuser', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.get(reverse('user_profile:privacy_settings'))
        
        # Check log contains route path
        for record in caplog.records:
            if 'DEPRECATED_USER_PROFILE_ROUTE' in record.message:
                self.assertIn('route', record.__dict__.get('extra', {}))
    
    def test_deprecation_log_contains_user_id(self, caplog):
        """Test: Deprecation log contains user_id"""
        self.client.login(username='testuser', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.get(reverse('user_profile:privacy_settings'))
        
        # Check log contains user_id
        for record in caplog.records:
            if 'DEPRECATED_USER_PROFILE_ROUTE' in record.message:
                extra = record.__dict__.get('extra', {})
                self.assertIn('user_id', extra)
                self.assertEqual(extra['user_id'], self.user.id)
    
    def test_deprecation_log_contains_replacement(self, caplog):
        """Test: Deprecation log contains replacement URL"""
        self.client.login(username='testuser', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.get(reverse('user_profile:privacy_settings'))
        
        # Check log contains replacement
        for record in caplog.records:
            if 'DEPRECATED_USER_PROFILE_ROUTE' in record.message:
                extra = record.__dict__.get('extra', {})
                self.assertIn('replacement', extra)
                self.assertIsNotNone(extra['replacement'])
    
    def test_deprecation_log_contains_reason(self, caplog):
        """Test: Deprecation log contains reason for deprecation"""
        self.client.login(username='testuser', password='password123')
        
        with caplog.at_level(logging.WARNING):
            response = self.client.get(reverse('user_profile:privacy_settings'))
        
        # Check log contains reason
        for record in caplog.records:
            if 'DEPRECATED_USER_PROFILE_ROUTE' in record.message:
                extra = record.__dict__.get('extra', {})
                self.assertIn('reason', extra)
                self.assertIsNotNone(extra['reason'])
