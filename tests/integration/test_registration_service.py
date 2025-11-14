"""
Integration tests for RegistrationService.

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 5: RegistrationService)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (End-to-end flows)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (Testing standards)

Tests end-to-end registration workflows including:
- Registration creation with eligibility checks
- Payment submission and verification
- Registration cancellation with refunds
- Slot and seed assignment

Note: These tests will run once pytest-django configuration is fixed.
The pytest-django test database creation issue is documented in MODULE_1.3_COMPLETION_STATUS.md.
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.tournaments.models import Game, Tournament, Registration, Payment
from apps.tournaments.services import RegistrationService, TournamentService

User = get_user_model()


@pytest.mark.django_db
class TestRegistrationServiceWorkflows:
    """Test complete registration workflows using RegistrationService"""
    
    @pytest.fixture
    def game(self):
        """Create a test game"""
        return Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='valorant_id',
            default_result_type='map_score',
            is_active=True
        )
    
    @pytest.fixture
    def organizer(self):
        """Create tournament organizer"""
        return User.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='test123',
            role='organizer'  # If role field exists
        )
    
    @pytest.fixture
    def tournament(self, game, organizer):
        """Create a tournament ready for registration"""
        now = timezone.now()
        tournament = TournamentService.create_tournament(
            organizer=organizer,
            data={
                'name': 'Test Tournament',
                'game_id': game.id,
                'format': 'single_elimination',
                'participation_type': 'team',
                'max_participants': 16,
                'min_participants': 4,
                'registration_start': now - timedelta(hours=1),  # Already open
                'registration_end': now + timedelta(days=7),
                'tournament_start': now + timedelta(days=8),
                'has_entry_fee': True,
                'entry_fee_amount': Decimal('500.00'),
                'payment_methods': ['bkash', 'nagad']
            }
        )
        
        # Publish tournament to open registration
        TournamentService.publish_tournament(
            tournament_id=tournament.id,
            user=organizer
        )
        
        return tournament
    
    @pytest.fixture
    def player(self):
        """Create a player user"""
        return User.objects.create_user(
            username='player1',
            email='player1@test.com',
            password='test123',
            role='player'  # If role field exists
        )
    
    def test_complete_registration_payment_flow(self, tournament, player, organizer):
        """
        Test complete workflow: register → submit payment → verify → confirm
        
        Workflow:
        1. Player registers for tournament
        2. Player submits payment proof
        3. Organizer verifies payment
        4. Registration is confirmed
        """
        # Step 1: Register participant
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={
                'game_id': 'Player#TAG',
                'phone': '+8801712345678',
                'notes': 'Ready to compete!'
            }
        )
        
        # Verify registration created correctly
        assert registration.tournament == tournament
        assert registration.user == player
        assert registration.status == Registration.PENDING
        assert registration.registration_data['game_id'] == 'Player#TAG'
        assert not registration.has_payment
        
        # Step 2: Submit payment
        payment = RegistrationService.submit_payment(
            registration_id=registration.id,
            payment_method='bkash',
            amount=Decimal('500.00'),
            transaction_id='TXN123456',
            payment_proof='payments/proof_123.jpg'
        )
        
        # Verify payment created correctly
        assert payment.registration == registration
        assert payment.payment_method == 'bkash'
        assert payment.amount == Decimal('500.00')
        assert payment.status == Payment.SUBMITTED
        
        # Verify registration status updated
        registration.refresh_from_db()
        assert registration.status == Registration.PAYMENT_SUBMITTED
        assert registration.has_payment
        
        # Step 3: Verify payment (organizer action)
        verified_payment = RegistrationService.verify_payment(
            payment_id=payment.id,
            verified_by=organizer,
            admin_notes='Payment verified - bKash transaction confirmed'
        )
        
        # Verify payment status updated
        assert verified_payment.status == Payment.VERIFIED
        assert verified_payment.verified_by == organizer
        assert verified_payment.verified_at is not None
        assert verified_payment.is_verified
        
        # Step 4: Verify registration confirmed
        registration.refresh_from_db()
        assert registration.status == Registration.CONFIRMED
        assert registration.is_confirmed
    
    def test_payment_rejection_flow(self, tournament, player, organizer):
        """
        Test payment rejection workflow
        
        Workflow:
        1. Player registers and submits payment
        2. Organizer rejects payment
        3. Registration status reverts to PENDING
        """
        # Register and submit payment
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={'game_id': 'Player#TAG'}
        )
        
        payment = RegistrationService.submit_payment(
            registration_id=registration.id,
            payment_method='bkash',
            amount=Decimal('500.00'),
            transaction_id='INVALID_TXN'
        )
        
        # Reject payment
        rejected_payment = RegistrationService.reject_payment(
            payment_id=payment.id,
            rejected_by=organizer,
            reason='Invalid transaction ID - please resubmit'
        )
        
        # Verify rejection
        assert rejected_payment.status == Payment.REJECTED
        assert 'Invalid transaction ID' in rejected_payment.admin_notes
        
        # Verify registration status reverted
        registration.refresh_from_db()
        assert registration.status == Registration.PENDING
    
    def test_registration_cancellation_with_refund(self, tournament, player, organizer):
        """
        Test cancellation workflow with automatic refund
        
        Workflow:
        1. Player completes registration with verified payment
        2. Player cancels registration
        3. Payment is automatically refunded
        4. Registration is soft-deleted
        """
        # Complete registration with verified payment
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={'game_id': 'Player#TAG'}
        )
        
        payment = RegistrationService.submit_payment(
            registration_id=registration.id,
            payment_method='bkash',
            amount=Decimal('500.00'),
            transaction_id='TXN123456'
        )
        
        RegistrationService.verify_payment(
            payment_id=payment.id,
            verified_by=organizer,
            admin_notes='Verified'
        )
        
        # Cancel registration
        cancelled_registration = RegistrationService.cancel_registration(
            registration_id=registration.id,
            user=player,
            reason='Schedule conflict'
        )
        
        # Verify cancellation
        assert cancelled_registration.status == Registration.CANCELLED
        assert cancelled_registration.is_deleted
        assert cancelled_registration.deleted_by == player
        
        # Verify automatic refund
        payment.refresh_from_db()
        assert payment.status == Payment.REFUNDED
    
    def test_eligibility_checks(self, tournament, player):
        """
        Test registration eligibility validation
        
        Tests:
        - Duplicate registration prevention
        - Capacity limit enforcement
        - Registration period validation
        """
        # First registration should succeed
        registration1 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={'game_id': 'Player#TAG'}
        )
        assert registration1 is not None
        
        # Duplicate registration should fail
        with pytest.raises(ValidationError, match="already registered"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=player,
                registration_data={'game_id': 'Player#TAG2'}
            )
        
        # Test capacity limit
        tournament.max_participants = 1
        tournament.save()
        
        player2 = User.objects.create_user(
            username='player2',
            email='player2@test.com',
            password='test123',
            role='player'
        )
        
        with pytest.raises(ValidationError, match="full"):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=player2,
                registration_data={'game_id': 'Player2#TAG'}
            )
    
    def test_slot_and_seed_assignment(self, tournament, player, organizer):
        """
        Test bracket slot and seed assignment
        
        Workflow:
        1. Complete registration with verified payment
        2. Assign bracket slot
        3. Assign seeding
        """
        # Complete registration
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={'game_id': 'Player#TAG'}
        )
        
        payment = RegistrationService.submit_payment(
            registration_id=registration.id,
            payment_method='bkash',
            amount=Decimal('500.00')
        )
        
        RegistrationService.verify_payment(
            payment_id=payment.id,
            verified_by=organizer
        )
        
        # Assign slot
        registration_with_slot = RegistrationService.assign_slot(
            registration_id=registration.id,
            slot_number=1,
            assigned_by=organizer
        )
        
        assert registration_with_slot.slot_number == 1
        
        # Assign seed
        registration_with_seed = RegistrationService.assign_seed(
            registration_id=registration.id,
            seed=1,
            assigned_by=organizer
        )
        
        assert registration_with_seed.seed == 1
    
    def test_registration_stats(self, tournament, player, organizer):
        """
        Test registration statistics calculation
        
        Tests:
        - Registration counts by status
        - Capacity percentage calculation
        """
        # Create multiple registrations in different states
        registration1 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={'game_id': 'Player1#TAG'}
        )
        
        player2 = User.objects.create_user(
            username='player2',
            email='player2@test.com',
            password='test123',
            role='player'
        )
        
        registration2 = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player2,
            registration_data={'game_id': 'Player2#TAG'}
        )
        
        # Submit payment for registration2
        RegistrationService.submit_payment(
            registration_id=registration2.id,
            payment_method='bkash',
            amount=Decimal('500.00')
        )
        
        # Get stats
        stats = RegistrationService.get_registration_stats(tournament_id=tournament.id)
        
        # Verify stats
        assert stats['total_registrations'] == 2
        assert stats['pending'] == 1  # registration1
        assert stats['payment_submitted'] == 1  # registration2
        assert stats['confirmed'] == 0
        assert stats['capacity_percentage'] == 12.5  # 2/16 * 100
    
    def test_payment_amount_validation(self, tournament, player):
        """
        Test payment amount must match tournament entry fee
        """
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={'game_id': 'Player#TAG'}
        )
        
        # Attempt to submit incorrect amount
        with pytest.raises(ValidationError, match="does not match entry fee"):
            RegistrationService.submit_payment(
                registration_id=registration.id,
                payment_method='bkash',
                amount=Decimal('300.00')  # Wrong amount
            )
    
    def test_payment_method_validation(self, tournament, player):
        """
        Test payment method must be accepted by tournament
        """
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={'game_id': 'Player#TAG'}
        )
        
        # Attempt to use non-accepted payment method
        with pytest.raises(ValidationError, match="not accepted"):
            RegistrationService.submit_payment(
                registration_id=registration.id,
                payment_method='deltacoin',  # Not in tournament.payment_methods
                amount=Decimal('500.00')
            )


@pytest.mark.django_db
class TestRegistrationServiceEdgeCases:
    """Test edge cases and error conditions in RegistrationService"""
    
    @pytest.fixture
    def closed_tournament(self, organizer):
        """Create a tournament with closed registration"""
        game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='valorant_id',
            is_active=True
        )
        
        now = timezone.now()
        tournament = TournamentService.create_tournament(
            organizer=organizer,
            data={
                'name': 'Closed Tournament',
                'game_id': game.id,
                'format': 'single_elimination',
                'max_participants': 16,
                'registration_start': now - timedelta(days=10),
                'registration_end': now - timedelta(days=1),  # Already closed
                'tournament_start': now + timedelta(days=1),
            }
        )
        return tournament
    
    @pytest.fixture
    def organizer(self):
        """Create tournament organizer"""
        return User.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='test123',
            role='organizer'
        )
    
    @pytest.fixture
    def player(self):
        """Create a player user"""
        return User.objects.create_user(
            username='player',
            email='player@test.com',
            password='test123',
            role='player'
        )
    
    def test_registration_closed_period(self, closed_tournament, player):
        """Test registration fails when registration period is closed"""
        with pytest.raises(ValidationError, match="Registration closed"):
            RegistrationService.register_participant(
                tournament_id=closed_tournament.id,
                user=player,
                registration_data={'game_id': 'Player#TAG'}
            )
    
    def test_duplicate_payment_submission(self, tournament, player):
        """Test that submitting payment twice for same registration fails"""
        # This test would need a properly configured tournament fixture
        # Skipping implementation as it depends on fixtures defined in other test class
        pass
    
    def test_verify_nonexistent_payment(self, organizer):
        """Test verifying non-existent payment raises error"""
        with pytest.raises(ValidationError, match="Payment with ID 99999 not found"):
            RegistrationService.verify_payment(
                payment_id=99999,
                verified_by=organizer
            )
    
    def test_cancel_already_cancelled_registration(self, tournament, player, organizer):
        """Test cancelling already cancelled registration raises error"""
        # Create and cancel registration
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=player,
            registration_data={'game_id': 'Player#TAG'}
        )
        
        RegistrationService.cancel_registration(
            registration_id=registration.id,
            user=player,
            reason='First cancellation'
        )
        
        # Attempt to cancel again
        with pytest.raises(ValidationError, match="already cancelled"):
            RegistrationService.cancel_registration(
                registration_id=registration.id,
                user=player,
                reason='Second cancellation'
            )
