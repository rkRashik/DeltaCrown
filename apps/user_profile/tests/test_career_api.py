"""
Tests for Career & Matchmaking Settings API (UP-PHASE2A)

Tests:
- Model validation (CareerProfile, MatchmakingPreferences)
- API endpoints (career GET/POST, matchmaking GET/POST)
- Authentication requirements
- CSRF protection
- Business logic enforcement
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError

from apps.user_profile.models import (
    UserProfile, CareerProfile, MatchmakingPreferences
)

User = get_user_model()


class CareerProfileModelTest(TestCase):
    """Test CareerProfile model validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
    
    def test_career_profile_creation_defaults(self):
        """Test default values on creation"""
        career = CareerProfile.objects.create(user_profile=self.profile)
        
        self.assertEqual(career.career_status, 'NOT_LOOKING')
        self.assertFalse(career.lft_enabled)
        self.assertEqual(career.primary_roles, [])
        self.assertIsNone(career.salary_expectation_min)
        self.assertEqual(career.recruiter_visibility, 'PUBLIC')
        self.assertFalse(career.allow_direct_contracts)
    
    def test_lft_enabled_with_signed_status_raises_error(self):
        """LFT cannot be enabled if status is SIGNED"""
        career = CareerProfile.objects.create(user_profile=self.profile)
        career.career_status = 'SIGNED'
        career.lft_enabled = True
        
        with self.assertRaises(ValidationError) as context:
            career.full_clean()
        
        self.assertIn('LFT cannot be enabled', str(context.exception))
    
    def test_negative_salary_raises_error(self):
        """Salary must be non-negative"""
        career = CareerProfile.objects.create(user_profile=self.profile)
        career.salary_expectation_min = -1000
        
        with self.assertRaises(ValidationError) as context:
            career.full_clean()
        
        self.assertIn('non-negative', str(context.exception))
    
    def test_primary_roles_must_be_list(self):
        """Primary roles must be a list"""
        career = CareerProfile.objects.create(user_profile=self.profile)
        career.primary_roles = "not_a_list"
        
        with self.assertRaises(ValidationError) as context:
            career.full_clean()
        
        self.assertIn('must be a list', str(context.exception))
    
    def test_valid_career_profile_saves(self):
        """Valid career profile should save successfully"""
        career = CareerProfile.objects.create(user_profile=self.profile)
        career.career_status = 'LOOKING'
        career.lft_enabled = True
        career.primary_roles = ['IGL', 'Support']
        career.salary_expectation_min = 2000
        career.recruiter_visibility = 'VERIFIED_SCOUTS'
        
        # Should not raise
        career.full_clean()
        career.save()
        
        # Reload and verify
        career.refresh_from_db()
        self.assertEqual(career.career_status, 'LOOKING')
        self.assertTrue(career.lft_enabled)
        self.assertEqual(career.primary_roles, ['IGL', 'Support'])


class MatchmakingPreferencesModelTest(TestCase):
    """Test MatchmakingPreferences model validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
    
    def test_matchmaking_defaults(self):
        """Test default values on creation"""
        prefs = MatchmakingPreferences.objects.create(user_profile=self.profile)
        
        self.assertFalse(prefs.enabled)
        self.assertEqual(prefs.games_enabled, [])
        self.assertIsNone(prefs.min_bounty)
        self.assertIsNone(prefs.max_bounty)
        self.assertFalse(prefs.auto_accept)
        self.assertFalse(prefs.allow_team_bounties)
    
    def test_min_bounty_greater_than_max_raises_error(self):
        """Min bounty cannot exceed max bounty"""
        prefs = MatchmakingPreferences.objects.create(user_profile=self.profile)
        prefs.min_bounty = 1000
        prefs.max_bounty = 500
        
        with self.assertRaises(ValidationError) as context:
            prefs.full_clean()
        
        self.assertIn('cannot exceed max_bounty', str(context.exception))
    
    def test_negative_bounty_raises_error(self):
        """Bounties must be non-negative"""
        prefs = MatchmakingPreferences.objects.create(user_profile=self.profile)
        prefs.min_bounty = -100
        
        with self.assertRaises(ValidationError) as context:
            prefs.full_clean()
        
        self.assertIn('non-negative', str(context.exception))
    
    def test_games_enabled_must_be_list(self):
        """Games enabled must be a list"""
        prefs = MatchmakingPreferences.objects.create(user_profile=self.profile)
        prefs.games_enabled = "not_a_list"
        
        with self.assertRaises(ValidationError) as context:
            prefs.full_clean()
        
        self.assertIn('must be a list', str(context.exception))
    
    def test_valid_matchmaking_preferences_saves(self):
        """Valid preferences should save successfully"""
        prefs = MatchmakingPreferences.objects.create(user_profile=self.profile)
        prefs.enabled = True
        prefs.games_enabled = ['valorant', 'csgo']
        prefs.min_bounty = 500
        prefs.max_bounty = 5000
        prefs.auto_accept = True
        
        # Should not raise
        prefs.full_clean()
        prefs.save()
        
        # Reload and verify
        prefs.refresh_from_db()
        self.assertTrue(prefs.enabled)
        self.assertEqual(prefs.games_enabled, ['valorant', 'csgo'])
        self.assertEqual(prefs.min_bounty, 500)


class CareerAPIEndpointTest(TestCase):
    """Test career settings API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client = Client()
        self.client.login(username='testplayer', password='testpass123')
    
    def test_career_get_creates_defaults(self):
        """GET /me/settings/career/ creates defaults if missing"""
        url = reverse('user_profile:settings_career_get')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['career_status'], 'NOT_LOOKING')
        self.assertFalse(data['data']['lft_enabled'])
        
        # Verify created in DB
        self.assertTrue(CareerProfile.objects.filter(user_profile=self.profile).exists())
    
    def test_career_save_valid_payload(self):
        """POST /me/settings/career/save/ with valid data succeeds"""
        url = reverse('user_profile:settings_career_save')
        payload = {
            'career_status': 'LOOKING',
            'lft_enabled': True,
            'primary_roles': ['IGL', 'Support'],
            'availability': 'PART_TIME',
            'salary_expectation_min': 1500,
            'recruiter_visibility': 'VERIFIED_SCOUTS',
            'allow_direct_contracts': True,
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        
        # Verify saved in DB
        career = CareerProfile.objects.get(user_profile=self.profile)
        self.assertEqual(career.career_status, 'LOOKING')
        self.assertTrue(career.lft_enabled)
        self.assertEqual(career.primary_roles, ['IGL', 'Support'])
    
    def test_career_save_invalid_payload_returns_error(self):
        """POST with invalid data returns success: false"""
        url = reverse('user_profile:settings_career_save')
        payload = {
            'career_status': 'SIGNED',
            'lft_enabled': True,  # Invalid: LFT + SIGNED conflict
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_career_endpoint_requires_authentication(self):
        """Career endpoints require login"""
        self.client.logout()
        
        url_get = reverse('user_profile:settings_career_get')
        url_save = reverse('user_profile:settings_career_save')
        
        response_get = self.client.get(url_get)
        response_save = self.client.post(url_save, data=json.dumps({}), content_type='application/json')
        
        # Should redirect to login
        self.assertEqual(response_get.status_code, 302)
        self.assertEqual(response_save.status_code, 302)


class MatchmakingAPIEndpointTest(TestCase):
    """Test matchmaking settings API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client = Client()
        self.client.login(username='testplayer', password='testpass123')
    
    def test_matchmaking_get_creates_defaults(self):
        """GET /me/settings/matchmaking/ creates defaults if missing"""
        url = reverse('user_profile:settings_matchmaking_get')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertFalse(data['data']['enabled'])
        
        # Verify created in DB
        self.assertTrue(MatchmakingPreferences.objects.filter(user_profile=self.profile).exists())
    
    def test_matchmaking_save_valid_payload(self):
        """POST /me/settings/matchmaking/save/ with valid data succeeds"""
        url = reverse('user_profile:settings_matchmaking_save')
        payload = {
            'enabled': True,
            'games_enabled': ['valorant', 'csgo'],
            'min_bounty': 500,
            'max_bounty': 5000,
            'auto_accept': True,
            'allow_team_bounties': True,
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        
        # Verify saved in DB
        prefs = MatchmakingPreferences.objects.get(user_profile=self.profile)
        self.assertTrue(prefs.enabled)
        self.assertEqual(prefs.games_enabled, ['valorant', 'csgo'])
        self.assertEqual(prefs.min_bounty, 500)
    
    def test_matchmaking_save_invalid_bounty_range(self):
        """POST with min > max returns error"""
        url = reverse('user_profile:settings_matchmaking_save')
        payload = {
            'min_bounty': 1000,
            'max_bounty': 500,  # Invalid: min > max
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_matchmaking_endpoint_requires_authentication(self):
        """Matchmaking endpoints require login"""
        self.client.logout()
        
        url_get = reverse('user_profile:settings_matchmaking_get')
        url_save = reverse('user_profile:settings_matchmaking_save')
        
        response_get = self.client.get(url_get)
        response_save = self.client.post(url_save, data=json.dumps({}), content_type='application/json')
        
        # Should redirect to login
        self.assertEqual(response_get.status_code, 302)
        self.assertEqual(response_save.status_code, 302)


class CSRFProtectionTest(TestCase):
    """Test CSRF protection on POST endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username='testplayer', password='testpass123')
    
    def test_career_save_requires_csrf_token(self):
        """POST to career save without CSRF token should fail"""
        url = reverse('user_profile:settings_career_save')
        payload = {'career_status': 'LOOKING'}
        
        # POST without CSRF token
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return 403 Forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_matchmaking_save_requires_csrf_token(self):
        """POST to matchmaking save without CSRF token should fail"""
        url = reverse('user_profile:settings_matchmaking_save')
        payload = {'enabled': True}
        
        # POST without CSRF token
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return 403 Forbidden
        self.assertEqual(response.status_code, 403)
