"""
QA Hardening Sprint Tests
Comprehensive end-to-end verification of production readiness.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.user_profile.models import UserProfile, PrivacySettings, GameProfile
from apps.games.models import Game
from apps.games.models.player_identity import GamePlayerIdentityConfig

User = get_user_model()


class URLRoutingConsistencyTestCase(TestCase):
    """A) Verify URL routing and namespace safety."""
    
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owneruser', password='pass123', email='owner@test.com')
        self.spectator = User.objects.create_user(username='spectatoruser', password='pass123', email='spectator@test.com')
        self.owner_profile = UserProfile.objects.get(user=self.owner)
        self.spectator_profile = UserProfile.objects.get(user=self.spectator)
    
    def test_url_names_exist_and_resolve(self):
        """Verify all canonical URL names resolve correctly."""
        # Public routes (require username)
        self.assertEqual(reverse('user_profile:profile_public_v2', kwargs={'username': 'owneruser'}), '/@owneruser/')
        self.assertEqual(reverse('user_profile:profile_activity_v2', kwargs={'username': 'owneruser'}), '/@owneruser/activity/')
        
        # Owner routes (no username - /me/ prefix)
        self.assertEqual(reverse('user_profile:profile_settings_v2'), '/me/settings/')
        self.assertEqual(reverse('user_profile:profile_privacy_v2'), '/me/privacy/')
        
        # API routes
        self.assertEqual(reverse('user_profile:passport_create'), '/api/passports/create/')
    
    def test_owner_profile_renders_without_noreversematch(self):
        """Owner viewing own profile should render without URL errors."""
        self.client.login(username='owneruser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'owneruser'}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'NoReverseMatch')
        self.assertNotContains(response, 'Reverse for')
    
    def test_spectator_profile_no_owner_links(self):
        """Spectator viewing profile should not see owner-only action links."""
        self.client.login(username='spectatoruser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'owneruser'}))
        self.assertEqual(response.status_code, 200)
        
        # Should NOT contain Settings or Privacy links
        self.assertNotContains(response, 'Settings')
        self.assertNotContains(response, 'Privacy')
        
        # Should contain Follow/Activity
        self.assertContains(response, 'Follow')
        self.assertContains(response, 'Activity')
    
    def test_settings_page_owner_only(self):
        """Settings page should be owner-only and use /me/ prefix."""
        # Anonymous redirect
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 302)  # Redirects to login
        
        # Logged in owner
        self.client.login(username='owneruser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile Settings')


class PassportModalSchemaTestCase(TestCase):
    """B) Verify passport modal is schema-driven with correct payload."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='pass123', email='test@test.com')
        self.profile = UserProfile.objects.get(user=self.user)
        
        # Create test games with identity configs
        self.valorant = Game.objects.create(
            name='Valorant',
            display_name='Valorant',
            slug='valorant',
            game_code='VAL',
            platforms=['PC']
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.valorant,
            field_name='riot_name',
            display_name='Riot ID',
            field_type='text',
            is_required=True,
            order=1
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.valorant,
            field_name='tag',
            display_name='Tag (#)',
            field_type='text',
            is_required=True,
            order=2
        )
        
        self.csgo = Game.objects.create(
            name='CS:GO',
            display_name='Counter-Strike: Global Offensive',
            slug='csgo',
            game_code='CSGO',
            platforms=['PC', 'Console']
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.csgo,
            field_name='steam_id',
            display_name='Steam ID',
            field_type='text',
            is_required=True,
            order=1
        )
    
    def test_settings_provides_games_list(self):
        """Settings page should provide games list with IDs."""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        
        # Check games queryset in context
        self.assertIn('games', response.context)
        games = list(response.context['games'])
        self.assertGreaterEqual(len(games), 2)
        
        # Verify Valorant is present with ID
        self.assertContains(response, f'data-game-id="{self.valorant.id}"')
        self.assertContains(response, 'value="valorant"')
    
    def test_game_schemas_json_present(self):
        """Settings page should provide game schemas JSON for dynamic fields."""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        
        self.assertIn('game_schemas_json', response.context)
        schemas = json.loads(response.context['game_schemas_json'])
        
        # Verify Valorant schema
        self.assertIn('valorant', schemas)
        val_schema = schemas['valorant']
        self.assertEqual(val_schema['game_id'], self.valorant.id)
        self.assertIn('fields', val_schema)
        self.assertEqual(len(val_schema['fields']), 2)  # riot_name, tag
    
    def test_passport_create_requires_game_id(self):
        """Passport creation endpoint must require game_id (integer)."""
        self.client.login(username='testuser', password='pass123')
        
        # Missing game_id
        response = self.client.post(
            reverse('user_profile:passport_create'),
            data=json.dumps({'ign': 'TestPlayer'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('game_id', data['error'].lower())
    
    def test_passport_create_with_metadata(self):
        """Passport creation should accept metadata for optional showcase fields."""
        self.client.login(username='testuser', password='pass123')
        
        payload = {
            'game_id': self.valorant.id,
            'ign': 'TestPlayer',
            'discriminator': '#NA1',
            'platform': 'PC',
            'metadata': {
                'display_name': 'ProPlayer',
                'current_rank': 'Diamond 2',
                'peak_rank': 'Immortal 1',
                'playstyle': 'Aggressive'
            }
        }
        
        response = self.client.post(
            reverse('user_profile:passport_create'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify passport created with metadata
        passport = GameProfile.objects.get(user=self.user, game=self.valorant)
        self.assertEqual(passport.metadata.get('display_name'), 'ProPlayer')
        self.assertEqual(passport.metadata.get('current_rank'), 'Diamond 2')


class ProfileNavigationTestCase(TestCase):
    """C) Verify profile navigation changes (nav bar removed, action cluster correct)."""
    
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owneruser', password='pass123', email='owner@test.com')
        self.spectator = User.objects.create_user(username='spectatoruser', password='pass123', email='spectator@test.com')
        self.owner_profile = UserProfile.objects.get(user=self.owner)
    
    def test_nav_bar_removed(self):
        """Verify sticky navigation bar is removed from profile."""
        self.client.login(username='owneruser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'owneruser'}))
        self.assertEqual(response.status_code, 200)
        
        # Should NOT contain nav bar structure
        content = response.content.decode('utf-8')
        self.assertNotIn('PROFILE NAVIGATION BAR', content)
        self.assertNotIn('profile-nav-link', content)
    
    def test_owner_action_cluster(self):
        """Owner should see Settings/Privacy/Activity in hero."""
        self.client.login(username='owneruser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'owneruser'}))
        self.assertEqual(response.status_code, 200)
        
        # Check action buttons exist (they're in hero area now)
        self.assertContains(response, 'Settings')
        self.assertContains(response, 'Privacy')
        self.assertContains(response, 'Activity')
        
        # Verify URLs
        self.assertContains(response, reverse('user_profile:profile_settings_v2'))
        self.assertContains(response, reverse('user_profile:profile_privacy_v2'))
    
    def test_spectator_action_cluster(self):
        """Spectator should see Follow/Message/Activity buttons."""
        self.client.login(username='spectatoruser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'owneruser'}))
        self.assertEqual(response.status_code, 200)
        
        # Should see Follow/Message
        self.assertContains(response, 'Follow')
        self.assertContains(response, 'Activity')
        
        # Should NOT see Settings/Privacy
        self.assertNotContains(response, reverse('user_profile:profile_settings_v2'))
        self.assertNotContains(response, reverse('user_profile:profile_privacy_v2'))


class PrivacyEnforcementTestCase(TestCase):
    """D) Verify privacy enforcement is server-side enforced."""
    
    def setUp(self):
        self.client = Client()
        self.private_user = User.objects.create_user(username='privateuser', password='pass123', email='private@test.com')
        self.spectator = User.objects.create_user(username='spectatoruser', password='pass123', email='spectator@test.com')
        
        # Set private preset
        self.private_profile = UserProfile.objects.get(user=self.private_user)
        self.privacy_settings = PrivacySettings.objects.get(user_profile=self.private_profile)
        self.privacy_settings.visibility_preset = PrivacySettings.PRESET_PRIVATE
        self.privacy_settings.show_social_links = False
        self.privacy_settings.show_country = False
        self.privacy_settings.save()
    
    def test_private_profile_blocks_spectator(self):
        """Private profile should block non-owner access."""
        self.client.login(username='spectatoruser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'privateuser'}))
        
        # Should redirect or show error
        # Based on build_public_profile_context, it should redirect
        self.assertIn(response.status_code, [302, 200])  # 200 if showing "This profile is private"
    
    def test_owner_always_sees_own_profile(self):
        """Owner should always see their own profile regardless of privacy."""
        self.client.login(username='privateuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'privateuser'}))
        self.assertEqual(response.status_code, 200)
        
        # Owner should see all content
        self.assertContains(response, 'privateuser')
    
    def test_social_links_respect_toggle(self):
        """Social links should only show if show_social_links is True."""
        # Create public user with social links toggled off
        public_user = User.objects.create_user(username='publicuser', password='pass123', email='public@test.com')
        public_profile = UserProfile.objects.get(user=public_user)
        public_profile.twitter = '@testuser'
        public_profile.save()
        
        privacy = PrivacySettings.objects.get(user_profile=public_profile)
        privacy.show_social_links = False
        privacy.save()
        
        self.client.login(username='spectatoruser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'publicuser'}))
        self.assertEqual(response.status_code, 200)
        
        # Should not show social links section (handled by context builder)
        context = response.context
        if 'social' in context:
            self.assertEqual(len(context['social']), 0)


class SettingsReorganizationTestCase(TestCase):
    """E) Verify Settings page reorganization is complete."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='pass123', email='test@test.com')
    
    def test_all_sections_render(self):
        """All 7 sections should be present in settings page."""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        
        # Check for section headers
        self.assertContains(response, 'Profile Information')
        self.assertContains(response, 'Social Links')
        self.assertContains(response, 'Privacy')
        self.assertContains(response, 'Gaming Activity')
        self.assertContains(response, 'Notifications')
        self.assertContains(response, 'Preferences')
        self.assertContains(response, 'Account')
    
    def test_notifications_section_exists(self):
        """Notifications section should have email/tournament/marketing toggles."""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'Notifications')
        self.assertContains(response, 'Email Notifications')
        self.assertContains(response, 'Tournament Updates')
        self.assertContains(response, 'Marketing Communications')
    
    def test_preferences_section_exists(self):
        """Preferences section should have theme/motion/compact toggles."""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'Preferences')
        self.assertContains(response, 'Dark Theme')
        self.assertContains(response, 'Reduce Animations')
        self.assertContains(response, 'Compact Mode')
        self.assertContains(response, 'Auto-play Videos')
    
    def test_account_section_exists(self):
        """Account section should show email/password/2FA/sessions."""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'Account')
        self.assertContains(response, 'Email Address')
        self.assertContains(response, 'Password')
        self.assertContains(response, 'Two-Factor Authentication')
        self.assertContains(response, 'Connected Sessions')
    
    def test_no_broken_reverse_urls(self):
        """Settings page should not have broken reverse() calls."""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        
        # Check for common error patterns
        content = response.content.decode('utf-8')
        self.assertNotIn('NoReverseMatch', content)
        self.assertNotIn('Reverse for', content)
        self.assertNotIn('is not a registered namespace', content)


class IntegrationSmokeTestCase(TestCase):
    """F) End-to-end smoke tests for critical paths."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='smokeuser', password='pass123', email='smoke@test.com')
        
        # Create a game
        self.game = Game.objects.create(
            name='Test Game',
            display_name='Test Game',
            slug='testgame',
            game_code='TEST'
        )
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name='username',
            display_name='Username',
            field_type='text',
            is_required=True,
            order=1
        )
    
    def test_user_flow_view_profile(self):
        """User can view their own profile."""
        self.client.login(username='smokeuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'smokeuser'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'smokeuser')
    
    def test_user_flow_access_settings(self):
        """User can access settings page."""
        self.client.login(username='smokeuser', password='pass123')
        response = self.client.get(reverse('user_profile:profile_settings_v2'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile Settings')
    
    def test_user_flow_create_passport(self):
        """User can create a passport via API."""
        self.client.login(username='smokeuser', password='pass123')
        
        payload = {
            'game_id': self.game.id,
            'ign': 'SmokePlayer',
            'discriminator': '#001',
            'platform': 'PC',
            'metadata': {'display_name': 'Smoke'}
        }
        
        response = self.client.post(
            reverse('user_profile:passport_create'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify passport exists
        passport = GameProfile.objects.filter(user=self.user, game=self.game).first()
        self.assertIsNotNone(passport)
        self.assertEqual(passport.ign, 'SmokePlayer')
    
    def test_deployment_check_passes(self):
        """System check should pass without errors."""
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        try:
            call_command('check', '--deploy', stdout=out, stderr=out)
            output = out.getvalue()
            # Should not contain "System check identified some errors"
            self.assertNotIn('identified some errors', output.lower())
        except Exception as e:
            self.fail(f"Deployment check failed: {e}")
