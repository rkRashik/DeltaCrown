"""
Tests for RegistrationService organizer actions (approve, reject, bulk operations).

Phase 0 Refactor: Tests for ORM mutations moved from organizer views to service layer.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game, Registration
from apps.tournaments.services.registration_service import RegistrationService

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
        description='Test description',
        organizer=organizer_user,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=4,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN
    )


@pytest.fixture
def pending_registration(db, tournament, participant_user):
    """Create a pending registration."""
    return Registration.objects.create(
        tournament=tournament,
        user=participant_user,
        status=Registration.PENDING,
        registration_data={}
    )


@pytest.mark.django_db
class TestRegistrationServiceApprove:
    """Test RegistrationService.approve_registration()"""
    
    def test_approve_pending_registration(self, pending_registration, organizer_user):
        """Test approving a pending registration."""
        # Act
        result = RegistrationService.approve_registration(
            registration=pending_registration,
            approved_by=organizer_user
        )
        
        # Assert
        assert result.status == 'confirmed'
        pending_registration.refresh_from_db()
        assert pending_registration.status == 'confirmed'


@pytest.mark.django_db
class TestRegistrationServiceReject:
    """Test RegistrationService.reject_registration()"""
    
    def test_reject_pending_registration(self, pending_registration, organizer_user):
        """Test rejecting a pending registration."""
        # Act
        result = RegistrationService.reject_registration(
            registration=pending_registration,
            rejected_by=organizer_user
        )
        
        # Assert
        assert result.status == 'rejected'
        pending_registration.refresh_from_db()
        assert pending_registration.status == 'rejected'


@pytest.mark.django_db
class TestRegistrationServiceBulkApprove:
    """Test RegistrationService.bulk_approve_registrations()"""
    
    def test_bulk_approve_multiple_registrations(self, tournament, organizer_user, db):
        """Test bulk approving multiple registrations."""
        # Arrange: Create 3 pending registrations
        user1 = User.objects.create_user(username='user1', email='user1@example.com', password='pass')
        user2 = User.objects.create_user(username='user2', email='user2@example.com', password='pass')
        user3 = User.objects.create_user(username='user3', email='user3@example.com', password='pass')
        
        reg1 = Registration.objects.create(tournament=tournament, user=user1, status=Registration.PENDING)
        reg2 = Registration.objects.create(tournament=tournament, user=user2, status=Registration.PENDING)
        reg3 = Registration.objects.create(tournament=tournament, user=user3, status=Registration.PENDING)
        
        registration_ids = [reg1.id, reg2.id, reg3.id]
        
        # Act
        result = RegistrationService.bulk_approve_registrations(
            registration_ids=registration_ids,
            tournament=tournament,
            approved_by=organizer_user
        )
        
        # Assert
        assert result['success'] is True
        assert result['count'] == 3
        
        reg1.refresh_from_db()
        reg2.refresh_from_db()
        reg3.refresh_from_db()
        assert reg1.status == Registration.CONFIRMED
        assert reg2.status == Registration.CONFIRMED
        assert reg3.status == Registration.CONFIRMED
    
    def test_bulk_approve_empty_list_raises_error(self, tournament, organizer_user):
        """Test bulk approve with empty list raises ValidationError."""
        with pytest.raises(ValidationError, match='No registrations selected'):
            RegistrationService.bulk_approve_registrations(
                registration_ids=[],
                tournament=tournament,
                approved_by=organizer_user
            )


@pytest.mark.django_db
class TestRegistrationServiceBulkReject:
    """Test RegistrationService.bulk_reject_registrations()"""
    
    def test_bulk_reject_multiple_registrations(self, tournament, organizer_user, db):
        """Test bulk rejecting multiple registrations."""
        # Arrange: Create 2 pending registrations
        user1 = User.objects.create_user(username='user1', email='user1@example.com', password='pass')
        user2 = User.objects.create_user(username='user2', email='user2@example.com', password='pass')
        
        reg1 = Registration.objects.create(tournament=tournament, user=user1, status=Registration.PENDING)
        reg2 = Registration.objects.create(tournament=tournament, user=user2, status=Registration.PENDING)
        
        registration_ids = [reg1.id, reg2.id]
        
        # Act
        result = RegistrationService.bulk_reject_registrations(
            registration_ids=registration_ids,
            tournament=tournament,
            rejected_by=organizer_user,
            reason='Invalid game IDs'
        )
        
        # Assert
        assert result['success'] is True
        assert result['count'] == 2
        
        reg1.refresh_from_db()
        reg2.refresh_from_db()
        assert reg1.status == Registration.REJECTED
        assert reg2.status == Registration.REJECTED
        assert reg1.registration_data['rejection_reason'] == 'Invalid game IDs'
        assert reg2.registration_data['rejection_reason'] == 'Invalid game IDs'
    
    def test_bulk_reject_empty_list_raises_error(self, tournament, organizer_user):
        """Test bulk reject with empty list raises ValidationError."""
        with pytest.raises(ValidationError, match='No registrations selected'):
            RegistrationService.bulk_reject_registrations(
                registration_ids=[],
                tournament=tournament,
                rejected_by=organizer_user,
                reason='test'
            )
