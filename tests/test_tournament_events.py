"""
Tests for Tournament Event Handlers

Tests the new event-driven architecture for tournaments.
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.core.events.bus import event_bus
from apps.core.events.events import TournamentCreatedEvent, RegistrationCreatedEvent
from apps.tournaments.events import (
    create_tournament_settings,
    create_game_config,
    create_payment_verification
)


@pytest.mark.django_db
class TestTournamentEventHandlers:
    """Test tournament event handlers"""
    
    def test_create_tournament_settings_handler(self):
        """Test that TournamentSettings is created when event is published"""
        from apps.tournaments.models import Tournament, TournamentSettings
        
        # Create tournament directly (bypassing service)
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant"
        )
        
        # Manually trigger event handler
        event = TournamentCreatedEvent(data={
            'tournament_id': tournament.id,
            'game': 'valorant'
        })
        create_tournament_settings(event)
        
        # Check that settings were created
        assert TournamentSettings.objects.filter(tournament=tournament).exists()
    
    def test_create_game_config_handler_valorant(self):
        """Test that ValorantConfig is created for valorant tournament"""
        from apps.tournaments.models import Tournament
        
        try:
            from apps.game_valorant.models import ValorantConfig
        except ImportError:
            pytest.skip("game_valorant not installed")
        
        # Create tournament
        tournament = Tournament.objects.create(
            name="Valorant Tournament",
            game="valorant"
        )
        
        # Trigger event handler
        event = TournamentCreatedEvent(data={
            'tournament_id': tournament.id,
            'game': 'valorant'
        })
        create_game_config(event)
        
        # Check that config was created
        assert ValorantConfig.objects.filter(tournament=tournament).exists()
    
    def test_create_payment_verification_handler(self):
        """Test that PaymentVerification is created when registration is created"""
        from apps.tournaments.models import Tournament, Registration, PaymentVerification
        from apps.organizations.models import Team
        from apps.accounts.models import User
        
        # Create test data
        user = User.objects.create_user(username="testuser", email="test@test.com")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant"
        )
        team = Team.objects.create(
            name="Test Team",
            captain=user,
            game="valorant"
        )
        
        # Create registration directly
        registration = Registration.objects.create(
            tournament=tournament,
            team=team,
            user=user
        )
        
        # Trigger event handler
        event = RegistrationCreatedEvent(data={
            'registration_id': registration.id,
            'tournament_id': tournament.id,
            'team_id': team.id,
            'user_id': user.id
        })
        create_payment_verification(event)
        
        # Check that payment verification was created
        assert PaymentVerification.objects.filter(registration=registration).exists()


@pytest.mark.django_db
class TestTournamentService:
    """Test tournament service layer"""
    
    def test_create_tournament_publishes_event(self):
        """Test that creating tournament through service publishes event"""
        from apps.tournaments.services.tournament_service import TournamentService
        from apps.tournaments.models import Tournament, TournamentSettings
        
        service = TournamentService()
        
        # Create tournament through service
        tournament = service.create_tournament(
            name="Test Tournament",
            game="valorant"
        )
        
        # Check tournament was created
        assert Tournament.objects.filter(id=tournament.id).exists()
        
        # Check that event handlers ran (settings should be auto-created)
        assert TournamentSettings.objects.filter(tournament=tournament).exists()
    
    def test_create_registration_publishes_event(self):
        """Test that creating registration through service publishes event"""
        from apps.tournaments.services.tournament_service import RegistrationService
        from apps.tournaments.models import Tournament, Registration, PaymentVerification
        from apps.organizations.models import Team
        from apps.accounts.models import User
        
        # Create test data
        user = User.objects.create_user(username="testuser2", email="test2@test.com")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant"
        )
        team = Team.objects.create(
            name="Test Team",
            captain=user,
            game="valorant"
        )
        
        service = RegistrationService()
        
        # Create registration through service
        registration = service.create_registration(
            tournament=tournament,
            team=team,
            user=user
        )
        
        # Check registration was created
        assert Registration.objects.filter(id=registration.id).exists()
        
        # Check that event handlers ran (payment verification should be auto-created)
        assert PaymentVerification.objects.filter(registration=registration).exists()


@pytest.mark.django_db
class TestEventDisabling:
    """Test that event handlers can be disabled for testing"""
    
    def test_create_tournament_with_disabled_handlers(self):
        """Test creating tournament with handlers disabled"""
        from apps.tournaments.services.tournament_service import TournamentService
        from apps.tournaments.models import Tournament, TournamentSettings
        
        # Disable handler
        event_bus.disable_handler('tournament.created', 'create_tournament_settings')
        
        service = TournamentService()
        tournament = service.create_tournament(
            name="Test Tournament",
            game="valorant"
        )
        
        # Settings should NOT be created because handler is disabled
        assert not TournamentSettings.objects.filter(tournament=tournament).exists()
        
        # Re-enable handler for other tests
        event_bus.enable_handler('tournament.created', 'create_tournament_settings')
