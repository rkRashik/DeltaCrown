"""
Tests for PaymentService organizer actions (verify, reject).

Phase 0 Refactor: Tests for ORM mutations moved from organizer views to service layer.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game, Registration, Payment
from apps.tournaments.services.payment_service import PaymentService

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
def pending_registration(db, tournament, participant_user):
    """Create a pending registration."""
    return Registration.objects.create(
        tournament=tournament,
        user=participant_user,
        team_name=f'Team {participant_user.username}',
        status='pending'
    )


@pytest.fixture
def pending_payment(db, pending_registration):
    """Create a pending payment."""
    return Payment.objects.create(
        registration=pending_registration,
        amount=100,
        status='pending',
        payment_method='bank_transfer'
    )


@pytest.mark.django_db
class TestPaymentServiceVerify:
    """Test PaymentService.verify_payment()"""
    
    def test_verify_pending_payment(self, pending_payment, organizer_user):
        """Test verifying a pending payment sets correct fields"""
        # Before: status is 'pending', no verified_by/verified_at
        assert pending_payment.status == 'pending'
        assert pending_payment.verified_by is None
        assert pending_payment.verified_at is None
        
        # Act: Verify payment
        result = PaymentService.verify_payment(pending_payment, organizer_user)
        
        # After: status is 'verified', verified_by and verified_at are set
        pending_payment.refresh_from_db()
        assert result.status == 'verified'
        assert pending_payment.status == 'verified'
        assert pending_payment.verified_by == organizer_user
        assert pending_payment.verified_at is not None
        assert (timezone.now() - pending_payment.verified_at).total_seconds() < 5


@pytest.mark.django_db
class TestPaymentServiceReject:
    """Test PaymentService.reject_payment()"""
    
    def test_reject_pending_payment(self, pending_payment, organizer_user):
        """Test rejecting a pending payment sets status and tracks rejector"""
        # Before: status is 'pending', no verified_by/verified_at
        assert pending_payment.status == 'pending'
        assert pending_payment.verified_by is None
        assert pending_payment.verified_at is None
        
        # Act: Reject payment
        result = PaymentService.reject_payment(pending_payment, organizer_user)
        
        # After: status is 'rejected', verified_by/verified_at are set
        # (Payment model uses these fields for BOTH verify and reject)
        pending_payment.refresh_from_db()
        assert result.status == 'rejected'
        assert pending_payment.status == 'rejected'
        assert pending_payment.verified_by == organizer_user
        assert pending_payment.verified_at is not None
        assert (timezone.now() - pending_payment.verified_at).total_seconds() < 5
