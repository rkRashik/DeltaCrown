"""
PHASE 9A-3: Game Passports Payload Mapping Tests
Tests for IGN derivation, riot_id parsing, and backend resilience.
"""

import pytest
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.games.models import Game
from apps.user_profile.models import GameProfile

User = get_user_model()


@pytest.mark.django_db
class TestGamePassportPayloadMapping(TestCase):
    """Test payload mapping layer for create/update endpoints"""
    
    def setUp(self):
        """Set up test user and games"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create test games
        self.valorant = Game.objects.create(
            name='VALORANT',
            slug='valorant',
            is_active=True
        )
        
        self.csgo = Game.objects.create(
            name='Counter-Strike 2',
            slug='cs2',
            is_active=True
        )
        
        self.pubg = Game.objects.create(
            name='PUBG Mobile',
            slug='pubg-mobile',
            is_active=True
        )
    
    def test_create_with_explicit_ign_field(self):
        """Test: Explicit ign field in metadata gets extracted"""
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.csgo.id,
                'passport_data': {
                    'ign': 'ProPlayer',
                    'region': 'NA'
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify passport created with correct IGN
        passport = GameProfile.objects.get(user=self.user, game=self.csgo)
        self.assertEqual(passport.ign, 'ProPlayer')
        self.assertEqual(passport.region, 'NA')
    
    def test_create_with_riot_id_parsing(self):
        """Test: riot_id format 'Name#TAG' gets parsed into ign + discriminator"""
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.valorant.id,
                'passport_data': {
                    'riot_id': 'TenZ#NA1',
                    'region': 'NA',
                    'rank': 'Radiant'
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify IGN and discriminator parsed correctly
        passport = GameProfile.objects.get(user=self.user, game=self.valorant)
        self.assertEqual(passport.ign, 'TenZ')
        self.assertEqual(passport.discriminator, 'NA1')
        self.assertEqual(passport.region, 'NA')
        self.assertEqual(passport.rank_name, 'Radiant')
    
    def test_create_with_riot_id_no_tag(self):
        """Test: riot_id without # tag uses full string as IGN"""
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.valorant.id,
                'passport_data': {
                    'riot_id': 'PlayerName',
                    'region': 'EU'
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        data = response.json()
        self.assertTrue(data['success'])
        
        passport = GameProfile.objects.get(user=self.user, game=self.valorant)
        self.assertEqual(passport.ign, 'PlayerName')
        self.assertIsNone(passport.discriminator)
    
    def test_create_with_uid_fallback(self):
        """Test: uid field falls back as IGN when no ign/riot_id"""
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.pubg.id,
                'passport_data': {
                    'uid': '5123456789',
                    'server': 'Asia',
                    'tier': 'Conqueror'
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        data = response.json()
        self.assertTrue(data['success'])
        
        passport = GameProfile.objects.get(user=self.user, game=self.pubg)
        self.assertEqual(passport.ign, '5123456789')
        self.assertEqual(passport.region, 'Asia')  # server → region mapping
        self.assertEqual(passport.rank_name, 'Conqueror')  # tier → rank mapping
    
    def test_create_with_top_level_ign(self):
        """Test: Top-level ign field (legacy format) still works"""
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.csgo.id,
                'ign': 'DirectIGN',
                'region': 'EU',
                'rank': 'Global Elite'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        data = response.json()
        self.assertTrue(data['success'])
        
        passport = GameProfile.objects.get(user=self.user, game=self.csgo)
        self.assertEqual(passport.ign, 'DirectIGN')
    
    def test_create_missing_ign_fails_gracefully(self):
        """Test: Missing IGN returns clear 400 error"""
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.csgo.id,
                'passport_data': {
                    'region': 'NA'
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('IGN', data['error'])
    
    def test_create_duplicate_game_fails(self):
        """Test: Duplicate game passport returns 400"""
        # Create first passport
        GameProfile.objects.create(
            user=self.user,
            game=self.valorant,
            ign='ExistingPlayer'
        )
        
        # Try to create duplicate
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.valorant.id,
                'passport_data': {
                    'ign': 'NewPlayer'
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('already have', data['error'])
    
    def test_update_with_riot_id_parsing(self):
        """Test: Update endpoint also parses riot_id correctly"""
        # Create initial passport
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.valorant,
            ign='OldName',
            region='NA'
        )
        
        # Update with riot_id
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps({
                'passport_id': passport.id,
                'passport_data': {
                    'riot_id': 'NewName#TAG',
                    'region': 'EU',
                    'rank': 'Immortal'
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        data = response.json()
        self.assertTrue(data['success'])
        
        passport.refresh_from_db()
        self.assertEqual(passport.ign, 'NewName')
        self.assertEqual(passport.discriminator, 'TAG')
    
    def test_metadata_preserved_in_passport_data(self):
        """Test: All metadata fields stored in passport_data JSON"""
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.valorant.id,
                'passport_data': {
                    'riot_id': 'Player#NA1',
                    'region': 'NA',
                    'rank': 'Diamond',
                    'peak_rank': 'Immortal',
                    'role': 'Duelist',
                    'custom_field': 'CustomValue'
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        
        passport = GameProfile.objects.get(user=self.user, game=self.valorant)
        
        # Verify structured fields extracted
        self.assertEqual(passport.ign, 'Player')
        self.assertEqual(passport.discriminator, 'NA1')
        self.assertEqual(passport.region, 'NA')
        self.assertEqual(passport.rank_name, 'Diamond')
        
        # Verify all metadata preserved
        self.assertIn('riot_id', passport.metadata)
        self.assertIn('peak_rank', passport.metadata)
        self.assertIn('role', passport.metadata)
        self.assertIn('custom_field', passport.metadata)
        self.assertEqual(passport.metadata['custom_field'], 'CustomValue')


@pytest.mark.django_db
class TestPhase7BRegression(TestCase):
    """Ensure Phase 7B tests still pass after payload mapping changes"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='phase7buser',
            email='phase7b@test.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
    
    def test_create_passport_basic(self):
        """Phase 7B Test: Basic passport creation"""
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps({
                'game_id': self.game.id,
                'ign': 'TestPlayer',
                'region': 'NA'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        passport = GameProfile.objects.get(user=self.user, game=self.game)
        self.assertEqual(passport.ign, 'TestPlayer')
    
    def test_delete_passport_basic(self):
        """Phase 7B Test: Basic passport deletion"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='DeleteMe'
        )
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps({'id': passport.id}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(GameProfile.objects.filter(id=passport.id).exists())


@pytest.mark.django_db
class TestPhase8BLockEnforcement(TestCase):
    """Ensure Phase 8B lock enforcement tests still pass"""
    
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        
        self.client = Client()
        self.user = User.objects.create_user(
            username='phase8buser',
            email='phase8b@test.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        
        # Create locked passport
        self.locked_passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='LockedPlayer',
            locked_until=timezone.now() + timedelta(days=15)
        )
    
    def test_locked_passport_cannot_be_edited(self):
        """Phase 8B Test: Locked passport edit returns 403"""
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps({
                'passport_id': self.locked_passport.id,
                'ign': 'NewName'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('locked', data['error'].lower())
    
    def test_locked_passport_cannot_be_deleted(self):
        """Phase 8B Test: Locked passport delete returns 403"""
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps({'id': self.locked_passport.id}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('locked', data['error'].lower())
