"""
PHASE 7B: Game Passports Full CRUD - Integration Tests
Tests for settings UI game passport operations.
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, GameProfile
from apps.games.models import Game

User = get_user_model()


class GamePassportsUIAPITestCase(TestCase):
    """Test game passport CRUD operations from Settings UI"""

    def setUp(self):
        """Set up test users and games"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Ensure UserProfile exists (create if not auto-created by signal)
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        
        # Create test games
        self.game_valorant = Game.objects.create(
            name='VALORANT',
            display_name='VALORANT',
            slug='valorant',
            short_code='VAL',
            category='FPS',
            is_active=True
        )
        self.game_cs2 = Game.objects.create(
            name='CS2',
            display_name='Counter-Strike 2',
            slug='cs2',
            short_code='CS2',
            category='FPS',
            is_active=True
        )
        
        self.client.login(username='testuser', password='testpass123')

    def test_list_passports(self):
        """Test listing user's game passports"""
        # Create a passport
        GameProfile.objects.create(
            user=self.user,
            game=self.game_valorant,
            ign='TestPlayer#123',
            region='NA'
        )
        
        response = self.client.get('/profile/api/game-passports/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['passports']), 1)
        self.assertEqual(data['passports'][0]['ign'], 'TestPlayer#123')

    def test_create_passport(self):
        """Test creating a new game passport"""
        payload = {
            'game_id': self.game_valorant.id,
            'ign': 'NewPlayer#456',
            'region': 'EU',
            'rank': 'Diamond'
        }
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify in database
        passport = GameProfile.objects.get(user=self.user, game=self.game_valorant)
        self.assertEqual(passport.ign, 'NewPlayer#456')
        self.assertEqual(passport.region, 'EU')
        self.assertEqual(passport.rank_name, 'Diamond')

    def test_create_passport_duplicate(self):
        """Test that creating duplicate passport for same game fails"""
        GameProfile.objects.create(
            user=self.user,
            game=self.game_valorant,
            ign='Existing#123'
        )
        
        payload = {
            'game_id': self.game_valorant.id,
            'ign': 'Duplicate#456'
        }
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('already have a passport', data['error'])

    def test_update_passport(self):
        """Test updating an existing game passport"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game_valorant,
            ign='OldName#123',
            region='NA'
        )
        
        payload = {
            'id': passport.id,
            'ign': 'NewName#456',
            'region': 'EU',
            'rank': 'Platinum'
        }
        
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify in database
        passport.refresh_from_db()
        self.assertEqual(passport.ign, 'NewName#456')
        self.assertEqual(passport.region, 'EU')
        self.assertEqual(passport.rank_name, 'Platinum')

    def test_delete_passport(self):
        """Test deleting a game passport"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game_valorant,
            ign='DeleteMe#123'
        )
        
        payload = {'id': passport.id}
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify deleted from database
        self.assertFalse(GameProfile.objects.filter(id=passport.id).exists())

    def test_pin_passport(self):
        """Test pinning a game passport"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game_valorant,
            ign='PinMe#123',
            is_pinned=False
        )
        
        payload = {
            'game': 'valorant',
            'pin': True
        }
        
        response = self.client.post(
            '/api/passports/pin/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_pinned'])
        
        # Verify in database
        passport.refresh_from_db()
        self.assertTrue(passport.is_pinned)

    def test_pin_limit(self):
        """Test that pinning more than 6 passports fails"""
        # Create 6 pinned passports
        games = []
        for i in range(6):
            game = Game.objects.create(
                name=f'Game{i}', 
                display_name=f'Game {i}',
                slug=f'game{i}', 
                short_code=f'G{i}',
                category='FPS',
                is_active=True
            )
            games.append(game)
            GameProfile.objects.create(
                user=self.user,
                game=game,
                ign=f'Player{i}',
                is_pinned=True
            )
        
        # Try to create 7th pinned passport
        payload = {
            'game_id': self.game_valorant.id,
            'ign': 'NewPlayer#789',
            'pinned': True
        }
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('only pin up to 6', data['error'])

    def test_passport_permissions(self):
        """Test that users can only modify their own passports"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_profile = UserProfile.objects.get(user=other_user)
        
        # Create passport for other user
        other_passport = GameProfile.objects.create(
            user=other_user,
            game=self.game_valorant,
            ign='OtherPlayer#123'
        )
        
        # Try to delete other user's passport
        payload = {'id': other_passport.id}
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        
        # Verify passport still exists
        self.assertTrue(GameProfile.objects.filter(id=other_passport.id).exists())

    def test_get_available_games(self):
        """Test fetching available games list"""
        from django.urls import reverse
        response = self.client.get(reverse('user_profile:get_available_games'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['games']), 2)
        
        # Verify game structure
        game = data['games'][0]
        self.assertIn('id', game)
        self.assertIn('name', game)
        self.assertIn('slug', game)

    def test_validation_missing_fields(self):
        """Test validation for missing required fields"""
        # Missing game_id
        payload = {'ign': 'Test#123'}
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        
        # Missing ign
        payload = {'game_id': self.game_valorant.id}
        
        response = self.client.post(
            '/profile/api/game-passports/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
