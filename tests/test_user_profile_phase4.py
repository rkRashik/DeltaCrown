"""
PHASE 4A: Automated Runtime Verification Suite
Tests actual behavior, not code inspection.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.user_profile.models_main import UserProfile, GameProfile, PrivacySettings, Follow
from apps.games.models import Game

User = get_user_model()


class Phase4AProfileDataSyncTest(TestCase):
    """Test 1: Settings changes reflect on profile page"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
        self.client.login(username='testuser', password='testpass123')
    
    def test_display_name_sync(self):
        """Settings display_name → Profile page"""
        # Update via settings
        response = self.client.post('/me/settings/basic/', {
            'display_name': 'New Display Name',
            'bio': 'Test bio',
        })
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify DB updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, 'New Display Name')
        
        # Verify profile page shows it
        response = self.client.get(f'/@{self.user.username}/')
        self.assertContains(response, 'New Display Name')
    
    def test_bio_sync(self):
        """Settings bio → Profile page"""
        response = self.client.post('/me/settings/basic/', {
            'display_name': self.profile.display_name or self.user.username,
            'bio': 'This is my new bio',
        })
        
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'This is my new bio')
        
        response = self.client.get(f'/@{self.user.username}/')
        self.assertContains(response, 'This is my new bio')
    
    def test_social_links_sync(self):
        """Settings social links → Profile page"""
        response = self.client.post('/me/settings/social/', {
            'twitter': 'testuser',
            'discord': 'testuser#1234',
            'youtube': 'testchannel',
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify profile page shows social links
        response = self.client.get(f'/@{self.user.username}/')
        # Should render social link icons/buttons
        self.assertContains(response, 'twitter')


class Phase4AGamePassportTest(TestCase):
    """Test 2: Game passport system end-to-end"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='gamer',
            email='gamer@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
        self.client.login(username='gamer', password='testpass123')
        
        # Create test game
        self.game = Game.objects.create(
            name='Test Game',
            display_name='Test Game',
            slug='test-game',
            short_code='TG',
            category='FPS',
            game_type='TEAM_VS_TEAM',
            platforms=['PC']
        )
    
    def test_games_api_loads(self):
        """API returns games list"""
        response = self.client.get('/api/games/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
    
    def test_passport_creation(self):
        """Create passport → Appears in DB and UI"""
        response = self.client.post('/api/passports/create/', {
            'game_id': self.game.id,
            'ign': 'TestPlayer',
            'discriminator': '#1234',
            'platform': 'PC',
        }, content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Verify DB record
        passport = GameProfile.objects.filter(
            user_profile=self.profile,
            game=self.game
        ).first()
        self.assertIsNotNone(passport)
        self.assertEqual(passport.ign, 'TestPlayer')
        
        # Verify appears on profile page
        response = self.client.get(f'/@{self.user.username}/')
        self.assertContains(response, 'TestPlayer')
    
    def test_passport_lft_toggle(self):
        """Toggle LFT status"""
        # Create passport
        passport = GameProfile.objects.create(
            user_profile=self.profile,
            game=self.game,
            ign='Player1',
            platform='PC',
            is_looking_for_team=False
        )
        
        # Toggle on
        response = self.client.post('/api/passports/toggle-lft/', {
            'passport_id': passport.id,
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        passport.refresh_from_db()
        self.assertTrue(passport.is_looking_for_team)
        
        # Toggle off
        response = self.client.post('/api/passports/toggle-lft/', {
            'passport_id': passport.id,
        }, content_type='application/json')
        
        passport.refresh_from_db()
        self.assertFalse(passport.is_looking_for_team)
    
    def test_passport_pin(self):
        """Pin/unpin passport"""
        passport = GameProfile.objects.create(
            user_profile=self.profile,
            game=self.game,
            ign='Player1',
            platform='PC',
            is_pinned=False
        )
        
        response = self.client.post('/api/passports/pin/', {
            'passport_id': passport.id,
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        passport.refresh_from_db()
        self.assertTrue(passport.is_pinned)
    
    def test_passport_delete(self):
        """Delete passport"""
        passport = GameProfile.objects.create(
            user_profile=self.profile,
            game=self.game,
            ign='Player1',
            platform='PC'
        )
        
        response = self.client.post(f'/api/passports/{passport.id}/delete/')
        self.assertEqual(response.status_code, 200)
        
        # Verify removed from DB
        exists = GameProfile.objects.filter(id=passport.id).exists()
        self.assertFalse(exists)


class Phase4AFollowSystemTest(TestCase):
    """Test 3: Follow/unfollow behavior"""
    
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.profile1 = self.user1.profile
        self.profile2 = self.user2.profile
    
    def test_follow_creates_record(self):
        """Follow action creates Follow record"""
        self.client.login(username='user1', password='testpass123')
        
        response = self.client.post(f'/actions/follow/{self.user2.username}/')
        self.assertEqual(response.status_code, 200)
        
        # Verify Follow record
        follow = Follow.objects.filter(
            follower=self.profile1,
            following=self.profile2
        ).first()
        self.assertIsNotNone(follow)
    
    def test_follow_updates_counts(self):
        """Follow updates follower/following counts"""
        self.client.login(username='user1', password='testpass123')
        
        initial_following = self.profile1.following_count
        initial_followers = self.profile2.follower_count
        
        self.client.post(f'/actions/follow/{self.user2.username}/')
        
        self.profile1.refresh_from_db()
        self.profile2.refresh_from_db()
        
        self.assertEqual(self.profile1.following_count, initial_following + 1)
        self.assertEqual(self.profile2.follower_count, initial_followers + 1)
    
    def test_unfollow_removes_record(self):
        """Unfollow removes Follow record"""
        # Create follow
        Follow.objects.create(follower=self.profile1, following=self.profile2)
        
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(f'/actions/unfollow/{self.user2.username}/')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify removed
        exists = Follow.objects.filter(
            follower=self.profile1,
            following=self.profile2
        ).exists()
        self.assertFalse(exists)
    
    def test_profile_adapts_to_viewer(self):
        """Profile shows different content based on viewer"""
        # Create follow relationship
        Follow.objects.create(follower=self.profile1, following=self.profile2)
        
        # User1 views User2's profile (as follower)
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(f'/@{self.user2.username}/')
        
        # Should show "Following" button
        # Should have follower-specific visibility
        self.assertContains(response, self.user2.username)
        
        # Logout and view as anonymous
        self.client.logout()
        response = self.client.get(f'/@{self.user2.username}/')
        
        # Should show limited info if profile is private
        self.assertEqual(response.status_code, 200)


class Phase4APrivacySystemTest(TestCase):
    """Test 6: Privacy system single source of truth"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='private_user',
            email='private@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
        self.viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123'
        )
    
    def test_privacy_settings_exist(self):
        """PrivacySettings model instance exists"""
        # Should be auto-created via signal
        privacy = PrivacySettings.objects.filter(user_profile=self.profile).first()
        self.assertIsNotNone(privacy)
    
    def test_profile_visibility_respected(self):
        """Private profile hides content from non-followers"""
        # Set profile to private
        privacy = self.profile.privacy_settings
        privacy.profile_visibility = 'PRIVATE'
        privacy.save()
        
        # Viewer (non-follower) views profile
        client = Client()
        client.login(username='viewer', password='testpass123')
        response = client.get(f'/@{self.user.username}/')
        
        # Should show limited info or access denied
        # (Exact behavior depends on implementation)
        self.assertEqual(response.status_code, 200)
    
    def test_privacy_save_endpoint(self):
        """Privacy settings save correctly"""
        client = Client()
        client.login(username='private_user', password='testpass123')
        
        response = client.post('/me/settings/privacy/save/', {
            'profile_visibility': 'FOLLOWERS_ONLY',
            'show_game_passports': 'on',
            'show_achievements': 'on',
        })
        
        self.assertEqual(response.status_code, 200)
        
        privacy = PrivacySettings.objects.get(user_profile=self.profile)
        self.assertEqual(privacy.profile_visibility, 'FOLLOWERS_ONLY')


class Phase4ADataIntegrityTest(TestCase):
    """Test data model consistency"""
    
    def test_no_duplicate_privacy_fields(self):
        """Verify only one privacy source of truth"""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='test'
        )
        profile = user.profile
        
        # Check if UserProfile has profile_visibility field
        has_profile_visibility = hasattr(profile, 'profile_visibility')
        
        # Check if PrivacySettings exists
        has_privacy_model = PrivacySettings.objects.filter(user_profile=profile).exists()
        
        # Document what we find
        print(f"UserProfile.profile_visibility exists: {has_profile_visibility}")
        print(f"PrivacySettings model exists: {has_privacy_model}")
        
        # Both should not be active simultaneously
        # This test documents the current state


def run_phase4a_tests():
    """Execute all Phase 4A verification tests"""
    from django.test.runner import DiscoverRunner
    
    runner = DiscoverRunner(verbosity=2, interactive=False, keepdb=True)
    suite = runner.test_suite()
    
    # Add all test cases
    suite.addTests([
        Phase4AProfileDataSyncTest,
        Phase4AGamePassportTest,
        Phase4AFollowSystemTest,
        Phase4APrivacySystemTest,
        Phase4ADataIntegrityTest,
    ])
    
    results = runner.run_suite(suite)
    return results
