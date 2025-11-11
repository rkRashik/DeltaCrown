"""
Module 5.2: Prize Payouts & Reconciliation - Milestone 1 Unit Tests
PrizeTransaction Model Constraints and Validation Tests

Tests:
1. test_prize_amount_positive_constraint - Validates amount >= 0 constraint
2. test_unique_prize_per_participant_placement - Validates unique constraint
3. test_participant_belongs_to_tournament_validation - Validates participant in tournament
4. test_coin_transaction_id_nullable - Validates NULL allowed for pending transactions
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from apps.tournaments.models import Tournament, Registration, PrizeTransaction, Game
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestPrizeTransactionConstraints:
    """Unit tests for PrizeTransaction model constraints and validation."""
    
    @pytest.fixture(scope='function')
    def game(self):
        """Create a test game."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        return Game.objects.create(
            name=f"Test Game {unique_id}",
            slug=f"test-game-{unique_id}",
            default_team_size=5,
            profile_id_field='game_id',
            default_result_type='map_score',
            is_active=True
        )
    
    @pytest.fixture
    def tournament(self, game):
        """Create a test tournament."""
        from django.utils import timezone
        from datetime import timedelta
        import uuid
        
        unique_id = str(uuid.uuid4())[:8]
        organizer = User.objects.create_user(username=f"organizer-{unique_id}", email=f"org-{unique_id}@test.com")
        now = timezone.now()
        return Tournament.objects.create(
            name=f"Test Tournament {unique_id}",
            slug=f"test-tournament-{unique_id}",
            description="Test description",
            game=game,
            organizer=organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            min_participants=2,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=12),
            status=Tournament.REGISTRATION_OPEN
        )
    
    @pytest.fixture
    def participant(self, tournament):
        """Create a test registration (participant)."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(username=f"player1-{unique_id}", email=f"player1-{unique_id}@test.com")
        return Registration.objects.create(
            tournament=tournament,
            user=user,
            status='confirmed'
        )
    
    @pytest.fixture
    def another_tournament(self, game):
        """Create another test tournament for cross-tournament validation."""
        from django.utils import timezone
        from datetime import timedelta
        import uuid
        
        unique_id = str(uuid.uuid4())[:8]
        organizer = User.objects.create_user(username=f"organizer2-{unique_id}", email=f"org2-{unique_id}@test.com")
        now = timezone.now()
        return Tournament.objects.create(
            name=f"Another Tournament {unique_id}",
            slug=f"another-tournament-{unique_id}",
            description="Another test description",
            game=game,
            organizer=organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            min_participants=2,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=12),
            status=Tournament.REGISTRATION_OPEN
        )
    
    def test_prize_amount_positive_constraint(self, tournament, participant):
        """
        Test that PrizeTransaction enforces amount >= 0 constraint.
        
        Expected behavior:
        - Valid amounts (>= 0) should save successfully
        - Negative amounts should raise ValidationError or IntegrityError
        """
        # Test valid amount (0)
        prize_zero = PrizeTransaction(
            tournament=tournament,
            participant=participant,
            placement=PrizeTransaction.Placement.PARTICIPATION,
            amount=Decimal('0.00'),
            status=PrizeTransaction.Status.PENDING
        )
        prize_zero.full_clean()  # Model validation
        prize_zero.save()
        assert prize_zero.id is not None
        
        # Test valid amount (positive)
        prize_positive = PrizeTransaction(
            tournament=tournament,
            participant=participant,
            placement=PrizeTransaction.Placement.FIRST,
            amount=Decimal('100.00'),
            status=PrizeTransaction.Status.PENDING
        )
        prize_positive.full_clean()
        prize_positive.save()
        assert prize_positive.id is not None
        
        # Test invalid amount (negative) - model validation
        prize_negative = PrizeTransaction(
            tournament=tournament,
            participant=participant,
            placement=PrizeTransaction.Placement.SECOND,
            amount=Decimal('-10.00'),
            status=PrizeTransaction.Status.PENDING
        )
        with pytest.raises(ValidationError) as exc_info:
            prize_negative.full_clean()
        assert 'amount' in exc_info.value.message_dict
        
        # Test invalid amount (negative) - database constraint
        with pytest.raises((ValidationError, IntegrityError)):
            with transaction.atomic():
                PrizeTransaction.objects.create(
                    tournament=tournament,
                    participant=participant,
                    placement=PrizeTransaction.Placement.THIRD,
                    amount=Decimal('-5.00'),
                    status=PrizeTransaction.Status.PENDING
                )
    
    def test_unique_prize_per_participant_placement(self, tournament, participant):
        """
        Test that PrizeTransaction enforces unique (tournament, participant, placement) constraint.
        
        Expected behavior:
        - First transaction for (tournament, participant, placement) should save
        - Duplicate (tournament, participant, placement) should raise IntegrityError
        - Different placements for same participant should be allowed
        """
        # First prize transaction for 1st place
        prize1 = PrizeTransaction.objects.create(
            tournament=tournament,
            participant=participant,
            placement=PrizeTransaction.Placement.FIRST,
            amount=Decimal('100.00'),
            status=PrizeTransaction.Status.PENDING
        )
        assert prize1.id is not None
        
        # Attempt duplicate (tournament, participant, placement) - should fail
        # Model's save() calls full_clean(), which raises ValidationError from UniqueConstraint
        with pytest.raises(ValidationError) as exc_info:
            PrizeTransaction.objects.create(
                tournament=tournament,
                participant=participant,
                placement=PrizeTransaction.Placement.FIRST,  # Same placement
                amount=Decimal('50.00'),
                status=PrizeTransaction.Status.PENDING
            )
        # Verify the error message contains the constraint violation message
        error_messages = str(exc_info.value)
        assert 'one prize per placement per tournament' in error_messages.lower() or 'unique' in error_messages.lower()
        
        # Different placement for same participant should succeed
        prize2 = PrizeTransaction.objects.create(
            tournament=tournament,
            participant=participant,
            placement=PrizeTransaction.Placement.PARTICIPATION,  # Different placement
            amount=Decimal('10.00'),
            status=PrizeTransaction.Status.PENDING
        )
        assert prize2.id is not None
    
    def test_participant_belongs_to_tournament_validation(self, tournament, participant, another_tournament):
        """
        Test that PrizeTransaction validates participant belongs to tournament.
        
        Expected behavior:
        - Participant registered in tournament should be valid
        - Participant NOT registered in tournament should raise ValidationError
        """
        # Valid: participant belongs to tournament
        prize_valid = PrizeTransaction(
            tournament=tournament,
            participant=participant,
            placement=PrizeTransaction.Placement.FIRST,
            amount=Decimal('100.00'),
            status=PrizeTransaction.Status.PENDING
        )
        prize_valid.full_clean()  # Should not raise
        prize_valid.save()
        assert prize_valid.id is not None
        
        # Invalid: participant does NOT belong to another_tournament
        prize_invalid = PrizeTransaction(
            tournament=another_tournament,  # Different tournament
            participant=participant,  # Participant registered in 'tournament', not 'another_tournament'
            placement=PrizeTransaction.Placement.FIRST,
            amount=Decimal('100.00'),
            status=PrizeTransaction.Status.PENDING
        )
        with pytest.raises(ValidationError) as exc_info:
            prize_invalid.full_clean()
        assert 'participant' in exc_info.value.message_dict
        assert 'not registered' in str(exc_info.value.message_dict['participant']).lower()
    
    def test_coin_transaction_id_nullable(self, tournament, participant):
        """
        Test that PrizeTransaction allows NULL coin_transaction_id for pending transactions.
        
        Expected behavior:
        - coin_transaction_id can be NULL (pending transactions)
        - coin_transaction_id can be set (completed transactions)
        """
        # Test NULL coin_transaction_id (pending)
        prize_pending = PrizeTransaction.objects.create(
            tournament=tournament,
            participant=participant,
            placement=PrizeTransaction.Placement.FIRST,
            amount=Decimal('100.00'),
            status=PrizeTransaction.Status.PENDING,
            coin_transaction_id=None  # Explicitly NULL
        )
        assert prize_pending.id is not None
        assert prize_pending.coin_transaction_id is None
        
        # Test setting coin_transaction_id (completed)
        prize_pending.coin_transaction_id = 12345
        prize_pending.status = PrizeTransaction.Status.COMPLETED
        prize_pending.save()
        
        prize_pending.refresh_from_db()
        assert prize_pending.coin_transaction_id == 12345
        assert prize_pending.status == PrizeTransaction.Status.COMPLETED
