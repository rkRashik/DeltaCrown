"""
Test suite for /profile/api/games/ endpoint (Phase 9A-9)
Ensures the games API returns 200 and has correct structure.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.games.models import Game
import json

User = get_user_model()


class GamesAPITestCase(TestCase):
    """Test GET /profile/api/games/ endpoint"""
    
    def setUp(self):
        """Create test user and client"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_games_api_returns_200(self):
        """GET /profile/api/games/ should return 200 status"""
        response = self.client.get('/profile/api/games/')
        self.assertEqual(response.status_code, 200)
    
    def test_games_api_returns_json(self):
        """Response should be valid JSON"""
        response = self.client.get('/profile/api/games/')
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIsInstance(data, dict)
    
    def test_games_api_success_structure(self):
        """Response should have {success: true, games: [...]} structure"""
        response = self.client.get('/profile/api/games/')
        data = response.json()
        
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('games', data)
        self.assertIsInstance(data['games'], list)
    
    def test_games_api_game_structure(self):
        """Each game should have required fields"""
        # Ensure at least one active game exists
        if not Game.objects.filter(is_active=True).exists():
            Game.objects.create(
                name='Test Game',
                slug='test-game-9a9',
                display_name='Test Game',
                is_active=True
            )
        
        response = self.client.get('/profile/api/games/')
        data = response.json()
        
        if len(data['games']) > 0:
            game = data['games'][0]
            # Required fields
            self.assertIn('id', game)
            self.assertIn('slug', game)
            self.assertIn('display_name', game)
            self.assertIn('passport_schema', game)
            self.assertIsInstance(game['passport_schema'], list)
            self.assertIn('rules', game)
    
    def test_games_api_handles_no_games_gracefully(self):
        """API should work even with no active games"""
        # Deactivate all games
        Game.objects.update(is_active=False)
        
        response = self.client.get('/profile/api/games/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['games']), 0)
