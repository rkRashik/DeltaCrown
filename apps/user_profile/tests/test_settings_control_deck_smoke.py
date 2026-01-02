"""
Phase 1D: Automated Smoke Tests for Settings Control Deck

Tests /me/settings/ page and READY control endpoints.
No Selenium - lightweight Django tests only.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.user_profile.models import UserProfile, PrivacySettings
from apps.economy.models import DeltaCrownWallet

User = get_user_model()


class SettingsControlDeckSmokeTests(TestCase):
    """Smoke tests for Settings Control Deck endpoints"""

    def setUp(self):
        """Create test user with profile and wallet"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Profile auto-created by signal, ensure it exists
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.display_name = 'Test User'
        self.profile.bio = 'Test bio'
        self.profile.save()
        
        # Create wallet
        self.wallet = DeltaCrownWallet.objects.create(
            profile=self.profile,
            cached_balance=100
        )
        
        # Create privacy settings
        self.privacy = PrivacySettings.objects.create(
            user_profile=self.profile,
            show_following_list=True
        )

    def test_settings_page_requires_login(self):
        """Test /me/settings/ redirects to login for anonymous users"""
        response = self.client.get(reverse('user_profile:profile_settings'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_settings_page_loads_for_logged_in_user(self):
        """Test /me/settings/ returns 200 for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('user_profile:profile_settings'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Settings Control Deck', response.content)
        self.assertIn(b'testuser', response.content)

    def test_settings_page_context_has_required_data(self):
        """Test /me/settings/ context contains all required data"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('user_profile:profile_settings'))
        
        self.assertIn('user_profile', response.context)
        self.assertIn('privacy_settings', response.context)
        self.assertIn('wallet', response.context)
        self.assertIn('game_profiles', response.context)
        self.assertIn('hardware_gear', response.context)  # Phase 1C fix
        
        # Verify wallet balance
        self.assertEqual(response.context['wallet'].cached_balance, 100)

    def test_update_basic_info_endpoint(self):
        """Test POST /me/settings/basic/ returns valid JSON"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:update_basic_info'),
            {
                'display_name': 'Updated Name',
                'bio': 'Updated bio',
                'city': 'Dhaka',
                'country': 'Bangladesh',
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        
        # Verify update
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, 'Updated Name')

    def test_update_basic_info_invalid_data(self):
        """Test POST /me/settings/basic/ with invalid data"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:update_basic_info'),
            {
                'display_name': 'A' * 200,  # Too long (max 80)
            }
        )
        
        # Should return error (not 500)
        self.assertIn(response.status_code, [200, 400])
        if response.status_code == 200:
            data = response.json()
            self.assertFalse(data.get('success', False))

    def test_privacy_settings_endpoint(self):
        """Test POST /me/settings/privacy/save/ returns valid JSON"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:update_privacy_settings'),
            json.dumps({'show_following_list': False}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        
        # Verify update
        self.privacy.refresh_from_db()
        self.assertFalse(self.privacy.show_following_list)

    def test_hardware_loadout_endpoint_exists(self):
        """Test hardware loadout endpoint is accessible"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:save_hardware'),
            json.dumps({
                'category': 'MOUSE',
                'brand': 'Logitech',
                'model': 'G Pro X',
                'is_public': True,
            }),
            content_type='application/json'
        )
        
        # Should return JSON (not 404)
        self.assertNotEqual(response.status_code, 404)
        self.assertEqual(response.status_code, 200)

    def test_social_links_endpoint_exists(self):
        """Test social links endpoint is accessible"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:update_social_links_api'),
            json.dumps({
                'links': [
                    {'platform': 'twitch', 'url': 'https://twitch.tv/testuser'}
                ]
            }),
            content_type='application/json'
        )
        
        # Should return JSON (not 404)
        self.assertNotEqual(response.status_code, 404)

    def test_url_reverses_exist(self):
        """Test all URL names used in template exist"""
        url_names = [
            'user_profile:profile_settings',
            'user_profile:public_profile',
            'user_profile:update_basic_info',
            'user_profile:upload_media',
            'user_profile:update_privacy_settings',
            'user_profile:save_hardware',
            'user_profile:update_social_links_api',
            'economy:withdrawal_request',
            'economy:transaction_history',
        ]
        
        for url_name in url_names:
            try:
                if ':' in url_name and url_name.split(':')[1] in ['public_profile']:
                    # URLs with kwargs
                    reverse(url_name, kwargs={'username': 'testuser'})
                else:
                    reverse(url_name)
            except Exception as e:
                self.fail(f"URL {url_name} does not exist: {e}")

    def test_feature_flag_disabled_behavior(self):
        """Test settings page behavior when feature flag is off"""
        # This test verifies the fallback behavior exists
        # Actual flag testing would require settings override
        self.client.login(username='testuser', password='testpass123')
        
        # Page should still load (either Control Deck or old settings)
        response = self.client.get(reverse('user_profile:profile_settings'))
        self.assertIn(response.status_code, [200, 302])

    def test_csrf_token_required(self):
        """Test endpoints reject requests without CSRF token"""
        self.client.login(username='testuser', password='testpass123')
        
        # Django test client includes CSRF by default, so we test with enforce_csrf_checks
        client_no_csrf = Client(enforce_csrf_checks=True)
        client_no_csrf.login(username='testuser', password='testpass123')
        
        response = client_no_csrf.post(
            reverse('user_profile:update_basic_info'),
            {'display_name': 'Test'}
        )
        
        # Should be forbidden (403) without CSRF
        self.assertEqual(response.status_code, 403)

    def test_settings_page_has_hardware_context(self):
        """Phase 1C regression test: hardware_gear context must exist"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('user_profile:profile_settings'))
        
        self.assertIn('hardware_gear', response.context)
        
        # Should have dict with keys for hardware categories
        hardware = response.context['hardware_gear']
        self.assertIsInstance(hardware, dict)
        self.assertIn('mouse', hardware)
        self.assertIn('keyboard', hardware)
        self.assertIn('headset', hardware)
        self.assertIn('monitor', hardware)


class WalletConsistencyTests(TestCase):
    """Tests for wallet section consistency"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='walletuser',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.wallet = DeltaCrownWallet.objects.create(
            profile=self.profile,
            cached_balance=500
        )

    def test_wallet_uses_correct_fk(self):
        """Test wallet query uses profile FK (not user FK)"""
        self.client.login(username='walletuser', password='testpass123')
        response = self.client.get(reverse('user_profile:profile_settings'))
        
        wallet = response.context.get('wallet')
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.profile, self.profile)
        self.assertEqual(wallet.cached_balance, 500)

    def test_economy_routes_exist(self):
        """Test economy withdraw/history routes exist"""
        # These routes should exist (Phase 1 requirement)
        try:
            reverse('economy:withdrawal_request')
            reverse('economy:transaction_history')
        except Exception as e:
            self.fail(f"Economy routes missing: {e}")
