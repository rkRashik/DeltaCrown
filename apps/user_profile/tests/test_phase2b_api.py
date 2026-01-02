"""
Phase 2B Test Suite: Notifications + Inventory Visibility + Dynamic Games
Tests the backend implementation of Phase 2B settings features.
"""

import json
from datetime import time
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.user_profile.models.settings import NotificationPreferences
from apps.user_profile.models_main import UserProfile, PrivacySettings
from apps.games.models import Game


User = get_user_model()


class NotificationPreferencesModelTest(TestCase):
    """Test NotificationPreferences model validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
    
    def test_notification_prefs_created_with_defaults(self):
        """Test that notification preferences are created with default values"""
        prefs = NotificationPreferences.objects.get_or_create(user_profile=self.profile)[0]
        self.assertTrue(prefs.email_enabled)
        self.assertTrue(prefs.push_enabled)  # Push defaults to ON for better UX
        self.assertFalse(prefs.sms_enabled)
        self.assertTrue(prefs.notif_tournaments)
        self.assertTrue(prefs.notif_teams)
        self.assertTrue(prefs.notif_bounties)
        self.assertTrue(prefs.notif_messages)
        self.assertTrue(prefs.notif_system)
        self.assertFalse(prefs.quiet_hours_enabled)
    
    def test_quiet_hours_validation_requires_times(self):
        """Test that enabling quiet hours requires start and end times"""
        prefs = NotificationPreferences.objects.get_or_create(user_profile=self.profile)[0]
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = None
        prefs.quiet_hours_end = None
        
        with self.assertRaises(Exception):  # ValidationError from clean()
            prefs.clean()
    
    def test_quiet_hours_validation_passes_with_times(self):
        """Test that quiet hours validation passes with valid times"""
        prefs = NotificationPreferences.objects.get_or_create(user_profile=self.profile)[0]
        prefs.quiet_hours_enabled = True
        prefs.quiet_hours_start = time(22, 0)
        prefs.quiet_hours_end = time(8, 0)
        
        # Should not raise
        prefs.clean()
        prefs.save()
        
        # Verify saved
        prefs.refresh_from_db()
        self.assertEqual(prefs.quiet_hours_start, time(22, 0))
        self.assertEqual(prefs.quiet_hours_end, time(8, 0))


class NotificationsAPITest(TestCase):
    """Test notification settings API endpoints"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client.login(username='testuser', password='testpass123')
        
        self.get_url = reverse('user_profile:settings_notifications_get')
        self.save_url = reverse('user_profile:settings_notifications_save')
    
    def test_get_returns_defaults_for_new_user(self):
        """Test GET endpoint returns default notification preferences"""
        response = self.client.get(self.get_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['email_enabled'])
        self.assertTrue(data['data']['push_enabled'])  # Default is True
        self.assertFalse(data['data']['sms_enabled'])
        self.assertTrue(data['data']['notif_tournaments'])
        self.assertFalse(data['data']['quiet_hours_enabled'])
    
    def test_post_saves_notification_preferences(self):
        """Test POST endpoint saves notification preferences"""
        payload = {
            'email_enabled': False,
            'push_enabled': True,
            'sms_enabled': False,
            'notif_tournaments': False,
            'notif_teams': True,
            'notif_bounties': True,
            'notif_messages': False,
            'notif_system': True,
            'quiet_hours_enabled': False,
        }
        
        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify saved in DB
        prefs = NotificationPreferences.objects.get(user_profile=self.profile)
        self.assertFalse(prefs.email_enabled)
        self.assertTrue(prefs.push_enabled)
        self.assertFalse(prefs.notif_tournaments)
        self.assertTrue(prefs.notif_teams)
    
    def test_post_quiet_hours_requires_times(self):
        """Test POST validation fails when quiet hours enabled without times"""
        payload = {
            'email_enabled': True,
            'push_enabled': False,
            'sms_enabled': False,
            'notif_tournaments': True,
            'notif_teams': True,
            'notif_bounties': True,
            'notif_messages': True,
            'notif_system': True,
            'quiet_hours_enabled': True,
            'quiet_hours_start': None,
            'quiet_hours_end': None,
        }
        
        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('quiet hours', data['error'].lower())
    
    def test_post_quiet_hours_accepts_valid_times(self):
        """Test POST accepts quiet hours with valid times"""
        payload = {
            'email_enabled': True,
            'push_enabled': False,
            'sms_enabled': False,
            'notif_tournaments': True,
            'notif_teams': True,
            'notif_bounties': True,
            'notif_messages': True,
            'notif_system': True,
            'quiet_hours_enabled': True,
            'quiet_hours_start': '22:00',
            'quiet_hours_end': '08:00',
        }
        
        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify saved
        prefs = NotificationPreferences.objects.get(user_profile=self.profile)
        self.assertTrue(prefs.quiet_hours_enabled)
        self.assertEqual(prefs.quiet_hours_start, time(22, 0))
        self.assertEqual(prefs.quiet_hours_end, time(8, 0))
    
    def test_get_requires_authentication(self):
        """Test GET endpoint requires authentication"""
        self.client.logout()
        response = self.client.get(self.get_url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_post_requires_authentication(self):
        """Test POST endpoint requires authentication"""
        self.client.logout()
        response = self.client.post(
            self.save_url,
            data=json.dumps({'email_enabled': True}),
            content_type='application/json'
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)


class InventoryVisibilityTest(TestCase):
    """Test inventory visibility privacy setting"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client.login(username='testuser', password='testpass123')
        
        self.url = reverse('user_profile:update_privacy_settings')
    
    def test_default_inventory_visibility_is_public(self):
        """Test that inventory_visibility defaults to PUBLIC"""
        privacy = PrivacySettings.objects.get_or_create(user_profile=self.profile)[0]
        self.assertEqual(privacy.inventory_visibility, 'PUBLIC')
    
    def test_post_updates_inventory_visibility(self):
        """Test POST updates inventory_visibility field"""
        payload = {
            'show_following_list': True,
            'inventory_visibility': 'FRIENDS',
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify saved
        privacy = PrivacySettings.objects.get(user_profile=self.profile)
        self.assertEqual(privacy.inventory_visibility, 'FRIENDS')
    
    def test_post_rejects_invalid_inventory_visibility(self):
        """Test POST rejects invalid inventory_visibility values"""
        payload = {
            'show_following_list': True,
            'inventory_visibility': 'INVALID_VALUE',
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_all_three_visibility_choices_work(self):
        """Test all three inventory_visibility choices save correctly"""
        privacy = PrivacySettings.objects.get_or_create(user_profile=self.profile)[0]
        
        for choice in ['PUBLIC', 'FRIENDS', 'PRIVATE']:
            payload = {
                'show_following_list': True,
                'inventory_visibility': choice,
            }
            
            response = self.client.post(
                self.url,
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            privacy.refresh_from_db()
            self.assertEqual(privacy.inventory_visibility, choice)


class DynamicGamesValidationTest(TestCase):
    """Test dynamic games list validation in matchmaking settings"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client.login(username='testuser', password='testpass123')
        
        # Create test games with unique short_codes
        self.valorant = Game.objects.create(
            name='VALORANT',
            slug='valorant',
            short_code='VAL',
            display_name='VALORANT',
            is_active=True
        )
        self.csgo = Game.objects.create(
            name='CS:GO',
            slug='csgo',
            short_code='CS',
            display_name='CS:GO',
            is_active=True
        )
        self.inactive_game = Game.objects.create(
            name='Old Game',
            slug='oldgame',
            short_code='OLD',
            display_name='Old Game',
            is_active=False
        )
        
        self.url = reverse('user_profile:settings_matchmaking_save')
    
    def test_valid_game_slugs_save_correctly(self):
        """Test that valid game slugs save to matchmaking settings"""
        payload = {
            'enabled': True,
            'games_enabled': ['valorant', 'csgo'],
            'min_bounty': 100,
            'max_bounty': 500,
            'auto_accept': False,
            'auto_reject_below_min': False,
            'allow_team_bounties': True,
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify saved
        self.profile.refresh_from_db()
        matchmaking = self.profile.matchmaking_prefs
        self.assertIn('valorant', matchmaking.games_enabled)
        self.assertIn('csgo', matchmaking.games_enabled)
    
    def test_invalid_game_slug_rejected(self):
        """Test that invalid game slugs are rejected"""
        payload = {
            'enabled': True,
            'games_enabled': ['valorant', 'nonexistent_game'],
            'min_bounty': 100,
            'max_bounty': 500,
            'auto_accept': False,
            'auto_reject_below_min': False,
            'allow_team_bounties': True,
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('game', data['error'].lower())
    
    def test_inactive_game_rejected(self):
        """Test that inactive games are rejected from matchmaking"""
        payload = {
            'enabled': True,
            'games_enabled': ['valorant', 'oldgame'],  # oldgame is inactive
            'min_bounty': 100,
            'max_bounty': 500,
            'auto_accept': False,
            'auto_reject_below_min': False,
            'allow_team_bounties': True,
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('active', data['error'].lower())
    
    def test_empty_games_list_allowed(self):
        """Test that empty games_enabled list is allowed"""
        payload = {
            'enabled': False,
            'games_enabled': [],
            'min_bounty': None,
            'max_bounty': None,
            'auto_accept': False,
            'auto_reject_below_min': False,
            'allow_team_bounties': False,
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
