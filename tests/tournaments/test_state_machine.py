# tests/tournaments/test_state_machine.py
"""
Tests for Tournament State Machine

Tests all state transitions and business logic in the TournamentStateMachine.
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tournaments.models import Tournament, TournamentSettings
from apps.tournaments.models.state_machine import (
    TournamentStateMachine,
    RegistrationState,
    TournamentPhase,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def tournament():
    """Create a base tournament for testing."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        game='valorant',
        status='PUBLISHED',
        entry_fee=100,
        max_teams=32,
    )


@pytest.fixture
def tournament_settings(tournament):
    """Create tournament settings."""
    return TournamentSettings.objects.create(
        tournament=tournament,
        max_teams=32,
        team_size_min=5,
        team_size_max=5,
    )


class TestRegistrationState:
    """Test registration state computation."""
    
    def test_not_open_before_reg_open(self, tournament, tournament_settings):
        """Registration should be NOT_OPEN before reg_open_at."""
        now = timezone.now()
        tournament_settings.reg_open_at = now + timedelta(hours=1)
        tournament_settings.reg_close_at = now + timedelta(days=1)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.registration_state == RegistrationState.NOT_OPEN
    
    def test_open_during_registration_window(self, tournament, tournament_settings):
        """Registration should be OPEN during the registration window."""
        now = timezone.now()
        tournament_settings.reg_open_at = now - timedelta(hours=1)
        tournament_settings.reg_close_at = now + timedelta(days=1)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.registration_state == RegistrationState.OPEN
    
    def test_closed_after_reg_close(self, tournament, tournament_settings):
        """Registration should be CLOSED after reg_close_at."""
        now = timezone.now()
        tournament_settings.reg_open_at = now - timedelta(days=2)
        tournament_settings.reg_close_at = now - timedelta(hours=1)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.registration_state == RegistrationState.CLOSED
    
    def test_full_when_max_teams_reached(self, tournament, tournament_settings):
        """Registration should be FULL when max_teams reached."""
        now = timezone.now()
        tournament_settings.reg_open_at = now - timedelta(hours=1)
        tournament_settings.reg_close_at = now + timedelta(days=1)
        tournament_settings.max_teams = 2
        tournament_settings.save()
        
        # Create 2 registrations (fill tournament)
        from apps.tournaments.models import Registration
        for i in range(2):
            Registration.objects.create(
                tournament=tournament,
                user=User.objects.create_user(
                    username=f'player{i}',
                    email=f'player{i}@example.com',
                    password='pass'
                ),
                display_name=f'Player {i}',
                in_game_id=f'player{i}#TAG'
            )
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.registration_state == RegistrationState.FULL
    
    def test_started_after_tournament_start(self, tournament, tournament_settings):
        """Registration should be STARTED after tournament starts."""
        now = timezone.now()
        tournament.start_at = now - timedelta(hours=1)
        tournament.save()
        
        tournament_settings.reg_open_at = now - timedelta(days=2)
        tournament_settings.reg_close_at = now - timedelta(hours=2)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.registration_state == RegistrationState.STARTED
    
    def test_completed_status(self, tournament):
        """Registration should be COMPLETED when tournament is completed."""
        tournament.status = 'COMPLETED'
        tournament.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.registration_state == RegistrationState.COMPLETED


class TestTournamentPhase:
    """Test tournament phase computation."""
    
    def test_draft_phase(self, tournament):
        """Draft status should return DRAFT phase."""
        tournament.status = 'DRAFT'
        tournament.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.phase == TournamentPhase.DRAFT
    
    def test_registration_phase(self, tournament, tournament_settings):
        """Active tournament before start should be REGISTRATION phase."""
        now = timezone.now()
        tournament.status = 'PUBLISHED'
        tournament.start_at = now + timedelta(days=1)
        tournament.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.phase == TournamentPhase.REGISTRATION
    
    def test_live_phase(self, tournament):
        """Started tournament should be LIVE phase."""
        now = timezone.now()
        tournament.status = 'RUNNING'
        tournament.start_at = now - timedelta(hours=1)
        tournament.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.phase == TournamentPhase.LIVE
    
    def test_completed_phase(self, tournament):
        """Completed tournament should be COMPLETED phase."""
        tournament.status = 'COMPLETED'
        tournament.save()
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.phase == TournamentPhase.COMPLETED


class TestCanRegister:
    """Test registration permission logic."""
    
    def test_unauthenticated_user_cannot_register(self, tournament, tournament_settings):
        """Anonymous users should not be able to register."""
        now = timezone.now()
        tournament_settings.reg_open_at = now - timedelta(hours=1)
        tournament_settings.reg_close_at = now + timedelta(days=1)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        can_register, message = state_machine.can_register(user=None)
        
        assert can_register is False
        assert "logged in" in message.lower()
    
    def test_user_can_register_when_open(self, tournament, tournament_settings, user):
        """Authenticated user should be able to register when open."""
        now = timezone.now()
        tournament_settings.reg_open_at = now - timedelta(hours=1)
        tournament_settings.reg_close_at = now + timedelta(days=1)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        can_register, message = state_machine.can_register(user=user)
        
        assert can_register is True
        assert "open" in message.lower()
    
    def test_cannot_register_when_closed(self, tournament, tournament_settings, user):
        """User cannot register after registration closes."""
        now = timezone.now()
        tournament_settings.reg_open_at = now - timedelta(days=2)
        tournament_settings.reg_close_at = now - timedelta(hours=1)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        can_register, message = state_machine.can_register(user=user)
        
        assert can_register is False
        assert "closed" in message.lower()
    
    def test_cannot_register_when_full(self, tournament, tournament_settings, user):
        """User cannot register when tournament is full."""
        now = timezone.now()
        tournament_settings.reg_open_at = now - timedelta(hours=1)
        tournament_settings.reg_close_at = now + timedelta(days=1)
        tournament_settings.max_teams = 1
        tournament_settings.save()
        
        # Fill the tournament
        from apps.tournaments.models import Registration
        Registration.objects.create(
            tournament=tournament,
            user=User.objects.create_user(username='other', email='other@example.com', password='pass'),
            display_name='Other Player',
            in_game_id='other#TAG'
        )
        
        state_machine = TournamentStateMachine(tournament)
        can_register, message = state_machine.can_register(user=user)
        
        assert can_register is False
        assert "full" in message.lower()


class TestCapacityManagement:
    """Test tournament capacity and slots logic."""
    
    def test_is_full_when_max_reached(self, tournament, tournament_settings):
        """Tournament should be full when registrations equal max_teams."""
        tournament_settings.max_teams = 2
        tournament_settings.save()
        
        # Create 2 registrations
        from apps.tournaments.models import Registration
        for i in range(2):
            Registration.objects.create(
                tournament=tournament,
                user=User.objects.create_user(
                    username=f'player{i}',
                    email=f'player{i}@example.com',
                    password='pass'
                ),
                display_name=f'Player {i}',
                in_game_id=f'player{i}#TAG'
            )
        
        state_machine = TournamentStateMachine(tournament)
        assert state_machine.is_full is True
    
    def test_slots_info(self, tournament, tournament_settings):
        """Slots info should return correct capacity data."""
        tournament_settings.max_teams = 10
        tournament_settings.save()
        
        # Create 3 registrations
        from apps.tournaments.models import Registration
        for i in range(3):
            Registration.objects.create(
                tournament=tournament,
                user=User.objects.create_user(
                    username=f'player{i}',
                    email=f'player{i}@example.com',
                    password='pass'
                ),
                display_name=f'Player {i}',
                in_game_id=f'player{i}#TAG'
            )
        
        state_machine = TournamentStateMachine(tournament)
        slots = state_machine.slots_info
        
        assert slots['total'] == 10
        assert slots['taken'] == 3
        assert slots['available'] == 7
        assert slots['is_full'] is False
        assert slots['has_limit'] is True


class TestToDictSerialization:
    """Test JSON serialization of state machine."""
    
    def test_to_dict_contains_all_fields(self, tournament, tournament_settings):
        """to_dict should return all necessary fields."""
        now = timezone.now()
        tournament_settings.reg_open_at = now - timedelta(hours=1)
        tournament_settings.reg_close_at = now + timedelta(days=1)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        data = state_machine.to_dict()
        
        # Check required fields
        assert 'phase' in data
        assert 'registration_state' in data
        assert 'can_register' in data
        assert 'is_full' in data
        assert 'slots' in data
        
        # Check types
        assert isinstance(data['phase'], str)
        assert isinstance(data['registration_state'], str)
        assert isinstance(data['can_register'], bool)
        assert isinstance(data['is_full'], bool)
        assert isinstance(data['slots'], dict)
    
    def test_to_dict_values_correct(self, tournament, tournament_settings):
        """to_dict should return correct values."""
        now = timezone.now()
        tournament.status = 'PUBLISHED'
        tournament.save()
        
        tournament_settings.reg_open_at = now - timedelta(hours=1)
        tournament_settings.reg_close_at = now + timedelta(days=1)
        tournament_settings.max_teams = 32
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        data = state_machine.to_dict()
        
        assert data['phase'] == TournamentPhase.REGISTRATION.value
        assert data['registration_state'] == RegistrationState.OPEN.value
        assert data['is_full'] is False
        assert data['slots']['total'] == 32


class TestTimeCalculations:
    """Test time-related calculations."""
    
    def test_time_until_start(self, tournament):
        """Should calculate time until tournament starts."""
        now = timezone.now()
        tournament.start_at = now + timedelta(hours=2, minutes=30)
        tournament.save()
        
        state_machine = TournamentStateMachine(tournament)
        time_delta = state_machine.time_until_start()
        
        assert time_delta is not None
        assert time_delta.total_seconds() > 0
        assert time_delta.total_seconds() < 3 * 60 * 60  # Less than 3 hours
    
    def test_time_until_registration_closes(self, tournament, tournament_settings):
        """Should calculate time until registration closes."""
        now = timezone.now()
        tournament_settings.reg_close_at = now + timedelta(days=1, hours=3)
        tournament_settings.save()
        
        state_machine = TournamentStateMachine(tournament)
        time_delta = state_machine.time_until_registration_closes()
        
        assert time_delta is not None
        assert time_delta.total_seconds() > 0
        assert time_delta.days >= 1
