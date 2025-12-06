"""
Smoke tests for leaderboard views.

Tests that ranking/leaderboard views:
- Return HTTP 200
- Use correct templates
- Include expected context variables
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse

from apps.games.models.game import Game


@pytest.mark.django_db
class TestLeaderboardViews(TestCase):
    """Smoke tests for leaderboard view endpoints."""
    
    def setUp(self):
        """Create test game and client."""
        self.client = Client()
        
        self.game = Game.objects.create(
            slug='valorant',
            short_code='VAL',
            name='VALORANT',
            display_name='VALORANT',
            category='FPS',
            game_type='TEAM_VS_TEAM',
            is_active=True
        )
    
    def test_game_leaderboard_returns_200(self):
        """Test that game-specific leaderboard returns HTTP 200."""
        url = reverse('teams:game_rankings', kwargs={'game_slug': self.game.slug})
        response = self.client.get(url)
        
        self.assertEqual(
            response.status_code,
            200,
            f"Game leaderboard should return 200, got {response.status_code}"
        )
    
    def test_game_leaderboard_uses_correct_template(self):
        """Test that game leaderboard uses the correct template."""
        url = reverse('teams:game_rankings', kwargs={'game_slug': self.game.slug})
        response = self.client.get(url)
        
        self.assertTemplateUsed(
            response,
            'teams/rankings/game_leaderboard.html'
        )
    
    def test_game_leaderboard_includes_game_context(self):
        """Test that game leaderboard includes game in context."""
        url = reverse('teams:game_rankings', kwargs={'game_slug': self.game.slug})
        response = self.client.get(url)
        
        self.assertIn('game', response.context, "Context should include 'game'")
        self.assertEqual(
            response.context['game'].slug,
            self.game.slug,
            "Context game should match requested game"
        )
    
    def test_game_leaderboard_includes_rankings_context(self):
        """Test that game leaderboard includes rankings in context."""
        url = reverse('teams:game_rankings', kwargs={'game_slug': self.game.slug})
        response = self.client.get(url)
        
        self.assertIn(
            'rankings',
            response.context,
            "Context should include 'rankings' queryset"
        )
    
    def test_global_leaderboard_returns_200(self):
        """Test that global leaderboard returns HTTP 200."""
        url = reverse('teams:rankings')
        response = self.client.get(url)
        
        self.assertEqual(
            response.status_code,
            200,
            f"Global leaderboard should return 200, got {response.status_code}"
        )
    
    def test_global_leaderboard_uses_correct_template(self):
        """Test that global leaderboard uses the correct template."""
        url = reverse('teams:rankings')
        response = self.client.get(url)
        
        self.assertTemplateUsed(
            response,
            'teams/rankings/global_leaderboard.html'
        )
    
    def test_global_leaderboard_includes_games_context(self):
        """Test that global leaderboard includes available games."""
        url = reverse('teams:rankings')
        response = self.client.get(url)
        
        self.assertIn(
            'games',
            response.context,
            "Context should include 'games' list"
        )
    
    def test_invalid_game_slug_returns_404(self):
        """Test that invalid game slug returns 404."""
        url = reverse('teams:game_rankings', kwargs={'game_slug': 'nonexistent-game'})
        response = self.client.get(url)
        
        self.assertEqual(
            response.status_code,
            404,
            "Invalid game slug should return 404"
        )


@pytest.mark.django_db
class TestLeaderboardPagination(TestCase):
    """Test leaderboard pagination behavior."""
    
    def setUp(self):
        """Create test data."""
        self.client = Client()
        
        self.game = Game.objects.create(
            slug='cs2',
            short_code='CS2',
            name='Counter-Strike 2',
            display_name='CS2',
            category='FPS',
            game_type='TEAM_VS_TEAM',
            is_active=True
        )
    
    def test_leaderboard_accepts_page_parameter(self):
        """Test that leaderboard accepts page query parameter."""
        url = reverse('teams:game_rankings', kwargs={'game_slug': self.game.slug})
        response = self.client.get(url, {'page': '1'})
        
        self.assertEqual(
            response.status_code,
            200,
            "Leaderboard should accept page parameter"
        )
    
    def test_leaderboard_handles_invalid_page_gracefully(self):
        """Test that invalid page number doesn't crash."""
        url = reverse('teams:game_rankings', kwargs={'game_slug': self.game.slug})
        response = self.client.get(url, {'page': '999'})
        
        # Should either show empty page or redirect to last page
        self.assertIn(
            response.status_code,
            [200, 302],
            "Invalid page should be handled gracefully"
        )
