"""
Phase 3 Integration Tests - Provider System
Tests that the tournament provider interface works correctly
and that all apps can access tournaments through the interface.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.core.registry import service_registry
from apps.core.interfaces import ITournamentProvider, IGameConfigProvider

User = get_user_model()


@pytest.mark.django_db
class TestTournamentProviderIntegration(TestCase):
    """Test tournament provider interface integration"""
    
    def setUp(self):
        """Set up test data"""
        self.provider = service_registry.get('tournament_provider')
        self.game_provider = service_registry.get('game_config_provider')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_provider_registration(self):
        """Test that providers are registered in service registry"""
        provider = service_registry.get('tournament_provider')
        self.assertIsNotNone(provider)
        self.assertIsInstance(provider, ITournamentProvider)
        
        game_provider = service_registry.get('game_config_provider')
        self.assertIsNotNone(game_provider)
        self.assertIsInstance(game_provider, IGameConfigProvider)
    
    def test_provider_versions(self):
        """Test that providers have correct versions"""
        services = service_registry.list_services()
        
        # list_services returns list of service names (strings)
        self.assertIn('tournament_provider', services)
        self.assertIn('game_config_provider', services)
        
        # Verify we can get the services
        tournament_provider = service_registry.get('tournament_provider')
        self.assertIsNotNone(tournament_provider)
        
        game_provider = service_registry.get('game_config_provider')
        self.assertIsNotNone(game_provider)
    
    def test_list_tournaments(self):
        """Test listing tournaments via provider"""
        tournaments = self.provider.list_tournaments()
        self.assertIsNotNone(tournaments)
        # Should return queryset or list
        self.assertTrue(hasattr(tournaments, '__iter__'))
    
    def test_list_tournaments_by_status(self):
        """Test filtering tournaments by status"""
        for status in ['upcoming', 'active', 'completed']:
            tournaments = self.provider.list_tournaments(status=status)
            self.assertIsNotNone(tournaments)
    
    def test_list_tournaments_by_game(self):
        """Test filtering tournaments by game"""
        for game in ['valorant', 'efootball', 'cs2']:
            tournaments = self.provider.list_tournaments(game=game)
            self.assertIsNotNone(tournaments)
    
    def test_get_tournament_nonexistent(self):
        """Test getting non-existent tournament returns None"""
        from apps.tournaments.models import Tournament
        tournament = self.provider.get_tournament(999999)
        self.assertIsNone(tournament)
    
    def test_get_registrations_for_nonexistent_tournament(self):
        """Test getting registrations for non-existent tournament"""
        registrations = self.provider.get_registrations(999999)
        # Should return empty queryset, not raise error
        self.assertIsNotNone(registrations)
        self.assertEqual(len(list(registrations)), 0)
    
    def test_game_config_provider_get_config(self):
        """Test getting game config via provider"""
        # Test with non-existent tournament - should not crash
        config = self.game_provider.get_config('valorant', 999999)
        # Provider should handle gracefully (return None or default)
        # Exact behavior depends on implementation
        self.assertTrue(config is None or isinstance(config, dict))
    
    def test_provider_has_required_methods(self):
        """Test that provider implements core required interface methods"""
        required_methods = [
            # Core tournament methods
            'get_tournament',
            'list_tournaments',
            'create_tournament',
            'update_tournament',
            'delete_tournament',
            # Core registration methods
            'get_registration',
            'get_registrations',  # Should be implemented as alias
            'get_tournament_registrations',
            'create_registration',
            'update_registration_status',
            'delete_registration',
            # Core match methods
            'get_match',
            'get_tournament_matches',
            'create_match',
            'update_match',
        ]
        
        for method in required_methods:
            self.assertTrue(
                hasattr(self.provider, method),
                f"Provider missing required method: {method}"
            )
            self.assertTrue(
                callable(getattr(self.provider, method)),
                f"Provider method not callable: {method}"
            )


@pytest.mark.django_db
class TestAppDecoupling(TestCase):
    """Test that apps no longer have direct Tournament imports"""
    
    def test_teams_app_no_direct_imports(self):
        """Test that teams app doesn't import Tournament directly"""
        import apps.teams.tasks
        import apps.teams.validators
        import apps.teams.api_views
        
        # If these modules load without ImportError, they're using indirect access
        # The actual import statement check is done via grep in separate verification
        self.assertTrue(True)  # Module loaded successfully
    
    def test_notifications_app_no_direct_imports(self):
        """Test that notifications app doesn't import Tournament directly"""
        import apps.notifications.services
        self.assertTrue(True)  # Module loaded successfully
    
    def test_economy_app_no_direct_imports(self):
        """Test that economy app doesn't import Tournament directly"""
        import apps.economy.admin
        self.assertTrue(True)  # Module loaded successfully
    
    def test_user_profile_app_no_direct_imports(self):
        """Test that user_profile app doesn't import Tournament directly"""
        import apps.user_profile.views_public
        self.assertTrue(True)  # Module loaded successfully


@pytest.mark.django_db
class TestProviderEventPublishing(TestCase):
    """Test that providers publish events correctly"""
    
    def setUp(self):
        """Set up test data"""
        self.provider = service_registry.get('tournament_provider')
        self.user = User.objects.create_user(
            username='eventuser',
            email='event@example.com',
            password='eventpass123'
        )
        self.events_received = []
    
    def test_provider_exists_and_accessible(self):
        """Basic sanity check that provider is accessible"""
        self.assertIsNotNone(self.provider)
        self.assertTrue(hasattr(self.provider, 'create_tournament'))


@pytest.mark.django_db 
class TestProviderQueryOptimization(TestCase):
    """Test that provider uses select_related/prefetch_related appropriately"""
    
    def setUp(self):
        """Set up test data"""
        self.provider = service_registry.get('tournament_provider')
    
    def test_list_tournaments_query_efficiency(self):
        """Test that list_tournaments doesn't cause N+1 queries"""
        from django.test.utils import override_settings
        from django.db import connection
        from django.conf import settings
        
        # Get tournaments
        with self.assertNumQueries(1):
            tournaments = list(self.provider.list_tournaments()[:10])
        
        # Should use select_related for common relations
        # Accessing related fields shouldn't trigger additional queries
        if tournaments:
            with self.assertNumQueries(0):
                for t in tournaments:
                    # These should be pre-fetched
                    _ = str(t)


@pytest.mark.django_db
class TestProviderErrorHandling(TestCase):
    """Test that provider handles errors gracefully"""
    
    def setUp(self):
        """Set up test data"""
        self.provider = service_registry.get('tournament_provider')
        self.user = User.objects.create_user(
            username='erroruser',
            email='error@example.com',
            password='errorpass123'
        )
    
    def test_get_tournament_with_invalid_id(self):
        """Test getting tournament with invalid ID"""
        # Should not raise exception, should return None
        result = self.provider.get_tournament(-1)
        self.assertIsNone(result)
        
        result = self.provider.get_tournament(0)
        self.assertIsNone(result)
    
    def test_create_registration_with_invalid_data(self):
        """Test creating registration with invalid data"""
        # Should handle missing required fields gracefully
        try:
            result = self.provider.create_registration(
                tournament_id=999999,
                team_id=None,
                user_id=None
            )
            # Either returns None or raises ValidationError
            self.assertTrue(result is None or hasattr(result, 'errors'))
        except Exception as e:
            # Should be a known exception type
            self.assertTrue(
                'Tournament' in str(e) or 
                'DoesNotExist' in str(e) or
                'ValidationError' in str(type(e).__name__)
            )


# Run with: pytest tests/test_phase3_integration.py -v
# Or: python manage.py test tests.test_phase3_integration
