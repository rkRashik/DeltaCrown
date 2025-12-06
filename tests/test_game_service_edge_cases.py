"""
Unit tests for GameService edge cases.

Tests GameService public API methods including:
- get_game() - lookup by slug
- get_choices() - form field choices
- list_active_games() - active game queryset
"""

import pytest
from django.test import TransactionTestCase

from apps.games.models.game import Game
from apps.games.services.game_service import game_service


@pytest.mark.django_db
class TestGameServiceGetGame(TransactionTestCase):
    """Test GameService.get_game() method."""
    
    def setUp(self):
        """Create test games."""
        self.valorant = Game.objects.create(
            slug='valorant', 
            short_code='VAL',
            name='VALORANT', 
            display_name='VALORANT',
            category='FPS',
            game_type='TEAM_VS_TEAM',
            is_active=True
        )
        self.inactive_game = Game.objects.create(
            slug='inactive', 
            short_code='INAC',
            name='Inactive Game', 
            display_name='Inactive Game',
            category='OTHER',
            game_type='1V1',
            is_active=False
        )
    
    def test_get_game_with_exact_slug(self):
        """Test retrieving game with exact slug match."""
        game = game_service.get_game('valorant')
        self.assertIsNotNone(game)
        self.assertEqual(game.slug, 'valorant')
        self.assertEqual(game.name, 'VALORANT')
        
    def test_get_game_returns_none_for_nonexistent(self):
        """Test that get_game returns None for non-existent slug."""
        game = game_service.get_game('nonexistent_game')
        self.assertIsNone(game)
        
    def test_get_game_filters_inactive_games(self):
        """Test that get_game filters out inactive games."""
        game = game_service.get_game('inactive')
        self.assertIsNone(game)  # is_active=False games are filtered out


@pytest.mark.django_db
class TestGameServiceGetChoices(TransactionTestCase):
    """Test GameService.get_choices() method."""
    
    def setUp(self):
        """Create test games."""
        Game.objects.create(slug='valorant', short_code='VAL', name='VALORANT', display_name='VALORANT', category='FPS', game_type='TEAM_VS_TEAM', is_active=True)
        Game.objects.create(slug='cs2', short_code='CS2', name='Counter-Strike 2', display_name='CS2', category='FPS', game_type='TEAM_VS_TEAM', is_active=True)
        Game.objects.create(slug='fifa', short_code='FIFA', name='EA Sports FC', display_name='EA SPORTS FC', category='SPORTS', game_type='1V1', is_active=True)
        Game.objects.create(slug='inactive', short_code='INAC', name='Inactive', display_name='Inactive', category='OTHER', game_type='1V1', is_active=False)
        
    def test_get_choices_returns_list_of_tuples(self):
        """Test that get_choices returns list of (slug, name) tuples."""
        choices = game_service.get_choices()
        
        self.assertIsInstance(choices, list)
        self.assertGreater(len(choices), 0)
        
        # Each choice should be a tuple
        for choice in choices:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)  # (slug, name)
            self.assertIsInstance(choice[0], str)  # slug
            self.assertIsInstance(choice[1], str)  # name
    
    def test_get_choices_sorted_alphabetically(self):
        """Test that choices are sorted alphabetically by name."""
        choices = game_service.get_choices()
        names = [c[1] for c in choices]
        
        # Check if sorted (CS2 < EA Sports FC < VALORANT)
        self.assertEqual(names, sorted(names), "Choices should be sorted alphabetically")
        
    def test_get_choices_only_includes_active_games(self):
        """Test that get_choices only returns active games."""
        choices = game_service.get_choices()
        slugs = [c[0] for c in choices]
        
        self.assertIn('valorant', slugs)
        self.assertIn('cs2', slugs)
        self.assertIn('fifa', slugs)
        self.assertNotIn('inactive', slugs)  # Inactive game excluded


@pytest.mark.django_db
class TestGameServiceListActiveGames(TransactionTestCase):
    """Test GameService.list_active_games() method."""
    
    def setUp(self):
        """Create test games."""
        self.active1 = Game.objects.create(slug='valorant', short_code='VAL', name='VALORANT', display_name='VALORANT', category='FPS', game_type='TEAM_VS_TEAM', is_active=True)
        self.active2 = Game.objects.create(slug='cs2', short_code='CS2', name='CS2', display_name='CS2', category='FPS', game_type='TEAM_VS_TEAM', is_active=True)
        self.inactive = Game.objects.create(slug='old_game', short_code='OLD', name='Old Game', display_name='Old Game', category='OTHER', game_type='1V1', is_active=False)
        
    def test_list_active_games_filters_inactive(self):
        """Test that list_active_games only returns active games."""
        games = game_service.list_active_games()
        
        slugs = [g.slug for g in games]
        self.assertIn('valorant', slugs)
        self.assertIn('cs2', slugs)
        self.assertNotIn('old_game', slugs)  # Inactive excluded
        
    def test_list_active_games_returns_queryset(self):
        """Test that list_active_games returns a queryset."""
        games = game_service.list_active_games()
        
        # Should be a queryset
        self.assertTrue(hasattr(games, 'filter'))
        self.assertTrue(hasattr(games, 'count'))
        
        # Count should match active games
        self.assertEqual(games.count(), 2)


@pytest.mark.django_db
class TestGameServiceCaching(TransactionTestCase):
    """Test GameService caching behavior."""
    
    def setUp(self):
        """Create test game."""
        self.valorant = Game.objects.create(
            slug='valorant',
            short_code='VAL',
            name='VALORANT',
            display_name='VALORANT',
            category='FPS',
            game_type='TEAM_VS_TEAM',
            is_active=True
        )
        
    def test_get_game_uses_select_related(self):
        """Test that get_game optimizes queries with select_related."""
        # This tests that the method uses select_related for performance
        with self.assertNumQueries(1):  # Should be a single query
            game = game_service.get_game('valorant')
            self.assertIsNotNone(game)
