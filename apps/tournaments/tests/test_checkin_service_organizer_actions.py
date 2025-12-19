"""
Tests for CheckinService organizer actions (organizer_toggle_checkin).

Phase 0 Refactor: Tests for ORM mutations moved from organizer views to service layer.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game, Registration
from apps.tournaments.services.checkin_service import CheckinService

User = get_user_model()


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name='Test Game',
        slug='test-game',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='map_score'
    )


@pytest.fixture
def organizer_user(db):
    """Create an organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def participant_user(db):
    """Create a participant user."""
    return User.objects.create_user(
        username='participant',
        email='participant@example.com',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def tournament(db, game, organizer_user):
    """Create a test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        game=game,
        organizer=organizer_user,
        max_teams=16,
        registration_start=timezone.now() - timedelta(days=2),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=14),
        tournament_end=timezone.now() + timedelta(days=15),
        status='upcoming'
    )


@pytest.fixture
def confirmed_registration(db, tournament, participant_user):
    """Create a confirmed registration (not checked in)."""
    return Registration.objects.create(
        tournament=tournament,
        user=participant_user,
        team_name=f'Team {participant_user.username}',
        status='confirmed',
        checked_in=False
    )


@pytest.fixture
def checked_in_registration(db, tournament, participant_user, organizer_user):
    """Create a checked-in registration."""
    return Registration.objects.create(
        tournament=tournament,
        user=participant_user,
        team_name=f'Team {participant_user.username}',
        status='confirmed',
        checked_in=True,
        checked_in_at=timezone.now() - timedelta(minutes=5),
        checked_in_by=organizer_user
    )


@pytest.mark.django_db
class TestCheckinServiceOrganizerToggle:
    """Test CheckinService.organizer_toggle_checkin()"""
    
    def test_toggle_checkin_off_to_on(self, confirmed_registration, organizer_user):
        """Test organizer toggling check-in from OFF to ON"""
        # Before: not checked in
        assert confirmed_registration.checked_in is False
        assert confirmed_registration.checked_in_at is None
        assert confirmed_registration.checked_in_by is None
        
        # Act: Toggle check-in (OFF → ON)
        result = CheckinService.organizer_toggle_checkin(
            confirmed_registration, 
            organizer_user
        )
        
        # After: checked in
        confirmed_registration.refresh_from_db()
        assert result.checked_in is True
        assert confirmed_registration.checked_in is True
        assert confirmed_registration.checked_in_at is not None
        assert confirmed_registration.checked_in_by == organizer_user
        assert (timezone.now() - confirmed_registration.checked_in_at).total_seconds() < 5
    
    def test_toggle_checkin_on_to_off(self, checked_in_registration, organizer_user):
        """Test organizer toggling check-in from ON to OFF"""
        # Before: checked in
        assert checked_in_registration.checked_in is True
        assert checked_in_registration.checked_in_at is not None
        assert checked_in_registration.checked_in_by is not None
        
        # Act: Toggle check-in (ON → OFF)
        result = CheckinService.organizer_toggle_checkin(
            checked_in_registration,
            organizer_user
        )
        
        # After: not checked in, all fields cleared
        checked_in_registration.refresh_from_db()
        assert result.checked_in is False
        assert checked_in_registration.checked_in is False
        assert checked_in_registration.checked_in_at is None
        assert checked_in_registration.checked_in_by is None
    
    def test_toggle_checkin_is_idempotent_on_double_toggle(
        self, 
        confirmed_registration, 
        organizer_user
    ):
        """Test toggling twice returns to original state"""
        # Start: not checked in
        assert confirmed_registration.checked_in is False
        
        # First toggle: OFF → ON
        CheckinService.organizer_toggle_checkin(confirmed_registration, organizer_user)
        confirmed_registration.refresh_from_db()
        assert confirmed_registration.checked_in is True
        
        # Second toggle: ON → OFF (back to original)
        CheckinService.organizer_toggle_checkin(confirmed_registration, organizer_user)
        confirmed_registration.refresh_from_db()
        assert confirmed_registration.checked_in is False
        assert confirmed_registration.checked_in_at is None
        assert confirmed_registration.checked_in_by is None
