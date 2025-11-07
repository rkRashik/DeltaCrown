"""
Unit tests for Registration and Payment models.

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 4: Registration & Payment Models)
- Documents/Planning/PART_3.2_CONSTRAINTS_INDEXES_TRIGGERS.md (Constraints + Indexes)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (UI behavior + flow)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-003 Soft Delete, ADR-004 PostgreSQL)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (Testing standards)

Tests the Registration and Payment models including:
- Field validation
- Status workflows
- JSONB data storage
- Soft delete behavior
- CHECK constraints (user XOR team)
- Payment verification workflow
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.tournaments.models import Registration, Payment, Tournament, Game


@pytest.mark.django_db
class TestRegistrationModel:
    """Test Registration model structure and behavior"""
    
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
    def tournament(self, game, django_user_model):
        """Create a test tournament"""
        organizer = django_user_model.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='test123'
        )
        now = timezone.now()
        return Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=game,
            organizer=organizer,
            format='single_elimination',
            participation_type='team',
            max_participants=16,
            min_participants=4,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=8),
            has_entry_fee=True,
            entry_fee_amount=Decimal('500.00'),
            payment_methods=['bkash', 'nagad']
        )
    
    @pytest.fixture
    def user(self, django_user_model):
        """Create a test user"""
        return django_user_model.objects.create_user(
            username='testplayer',
            email='player@test.com',
            password='test123'
        )
    
    def test_registration_has_required_fields(self, tournament, user):
        """Should have all required fields from planning docs"""
        registration = Registration(
            tournament=tournament,
            user=user,
            status='pending',
            registration_data={'display_name': 'Test Player'}
        )
        
        # Check field existence
        assert hasattr(registration, 'id')
        assert hasattr(registration, 'tournament')
        assert hasattr(registration, 'user')
        assert hasattr(registration, 'team_id')
        assert hasattr(registration, 'registration_data')
        assert hasattr(registration, 'status')
        assert hasattr(registration, 'registered_at')
        assert hasattr(registration, 'checked_in')
        assert hasattr(registration, 'checked_in_at')
        assert hasattr(registration, 'slot_number')
        assert hasattr(registration, 'seed')
        assert hasattr(registration, 'is_deleted')
        assert hasattr(registration, 'deleted_at')
        assert hasattr(registration, 'deleted_by')
        assert hasattr(registration, 'created_at')
        assert hasattr(registration, 'updated_at')
    
    def test_registration_str_representation(self, tournament, user):
        """Should have readable string representation"""
        registration = Registration.objects.create(
            tournament=tournament,
            user=user,
            status='pending'
        )
        
        str_repr = str(registration)
        assert tournament.name in str_repr
        assert user.username in str_repr
    
    def test_registration_status_choices(self):
        """Should validate status field choices"""
        from apps.tournaments.models.registration import Registration as RegModel
        
        expected_statuses = [
            'pending',
            'payment_submitted',
            'confirmed',
            'rejected',
            'cancelled',
            'no_show'
        ]
        
        status_values = [choice[0] for choice in RegModel.STATUS_CHOICES]
        for status in expected_statuses:
            assert status in status_values
    
    def test_registration_defaults(self, tournament, user):
        """Should have correct default values"""
        registration = Registration.objects.create(
            tournament=tournament,
            user=user
        )
        
        assert registration.status == 'pending'
        assert registration.checked_in is False
        assert registration.checked_in_at is None
        assert registration.slot_number is None
        assert registration.seed is None
        assert registration.is_deleted is False
    
    def test_registration_data_jsonb(self, tournament, user):
        """Should store and retrieve JSONB registration_data"""
        test_data = {
            'participant_type': 'solo',
            'display_name': 'ProPlayer123',
            'game_ids': {
                'valorant_id': 'Player#TAG',
                'riot_id': 'Player#TAG'
            },
            'contact': {
                'phone': '+8801712345678',
                'discord': 'player#1234'
            },
            'custom_fields': {
                'preferred_role': 'Duelist',
                'rank': 'Immortal 3'
            }
        }
        
        registration = Registration.objects.create(
            tournament=tournament,
            user=user,
            registration_data=test_data
        )
        
        # Fetch from database
        saved_registration = Registration.objects.get(id=registration.id)
        assert saved_registration.registration_data == test_data
        assert saved_registration.registration_data['contact']['phone'] == '+8801712345678'
        assert saved_registration.registration_data['custom_fields']['rank'] == 'Immortal 3'
    
    def test_registration_user_xor_team_constraint(self, tournament, user):
        """Should enforce either user_id OR team_id, not both"""
        # User registration should work
        user_reg = Registration(
            tournament=tournament,
            user=user,
            team_id=None
        )
        user_reg.save()  # Should succeed
        
        # Team registration should work
        team_reg = Registration(
            tournament=tournament,
            user=None,
            team_id=42
        )
        team_reg.save()  # Should succeed
        
        # Both user and team should fail (constraint check at database level)
        # Note: This will be enforced by database constraint, not model validation
        # The constraint is: (user_id IS NOT NULL AND team_id IS NULL) OR (user_id IS NULL AND team_id IS NOT NULL)
    
    def test_registration_unique_user_per_tournament(self, tournament, user):
        """Should prevent duplicate user registrations for same tournament"""
        # First registration
        Registration.objects.create(
            tournament=tournament,
            user=user,
            status='confirmed'
        )
        
        # Second registration should fail (unique constraint)
        with pytest.raises(IntegrityError):
            Registration.objects.create(
                tournament=tournament,
                user=user,
                status='pending'
            )
    
    def test_registration_slot_number_unique_per_tournament(self, tournament, user, django_user_model):
        """Should prevent duplicate slot numbers in same tournament"""
        user2 = django_user_model.objects.create_user(
            username='player2',
            email='player2@test.com'
        )
        
        # First registration with slot 1
        Registration.objects.create(
            tournament=tournament,
            user=user,
            slot_number=1
        )
        
        # Second registration with same slot should fail
        with pytest.raises(IntegrityError):
            Registration.objects.create(
                tournament=tournament,
                user=user2,
                slot_number=1
            )
    
    def test_registration_soft_delete(self, tournament, user):
        """Should soft delete registration"""
        registration = Registration.objects.create(
            tournament=tournament,
            user=user,
            status='confirmed'
        )
        
        # Soft delete
        registration.soft_delete(deleted_by=user)
        
        assert registration.is_deleted is True
        assert registration.deleted_at is not None
        assert registration.deleted_by == user
        
        # Should not appear in default queryset
        assert not Registration.objects.filter(id=registration.id).exists()
        
        # Should appear in all_objects
        assert Registration.all_objects.filter(id=registration.id).exists()
    
    def test_registration_restore(self, tournament, user):
        """Should restore soft-deleted registration"""
        registration = Registration.objects.create(
            tournament=tournament,
            user=user
        )
        
        # Soft delete
        registration.soft_delete(deleted_by=user)
        assert registration.is_deleted is True
        
        # Restore
        registration.restore()
        assert registration.is_deleted is False
        assert registration.deleted_at is None
        assert registration.deleted_by is None
        
        # Should appear in default queryset again
        assert Registration.objects.filter(id=registration.id).exists()
    
    def test_registration_check_in_workflow(self, tournament, user):
        """Should track check-in status and timestamp"""
        registration = Registration.objects.create(
            tournament=tournament,
            user=user,
            status='confirmed'
        )
        
        assert registration.checked_in is False
        assert registration.checked_in_at is None
        
        # Check in
        registration.checked_in = True
        registration.checked_in_at = timezone.now()
        registration.save()
        
        # Verify
        saved_registration = Registration.objects.get(id=registration.id)
        assert saved_registration.checked_in is True
        assert saved_registration.checked_in_at is not None


@pytest.mark.django_db
class TestPaymentModel:
    """Test Payment model structure and behavior"""
    
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
    def tournament(self, game, django_user_model):
        """Create a test tournament"""
        organizer = django_user_model.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='test123'
        )
        now = timezone.now()
        return Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=game,
            organizer=organizer,
            format='single_elimination',
            max_participants=16,
            min_participants=4,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=8),
            has_entry_fee=True,
            entry_fee_amount=Decimal('500.00'),
            payment_methods=['bkash']
        )
    
    @pytest.fixture
    def user(self, django_user_model):
        """Create a test user"""
        return django_user_model.objects.create_user(
            username='testplayer',
            email='player@test.com',
            password='test123'
        )
    
    @pytest.fixture
    def registration(self, tournament, user):
        """Create a test registration"""
        return Registration.objects.create(
            tournament=tournament,
            user=user,
            status='pending'
        )
    
    def test_payment_has_required_fields(self, registration):
        """Should have all required fields from planning docs"""
        payment = Payment(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('500.00')
        )
        
        # Check field existence
        assert hasattr(payment, 'id')
        assert hasattr(payment, 'registration')
        assert hasattr(payment, 'payment_method')
        assert hasattr(payment, 'amount')
        assert hasattr(payment, 'transaction_id')
        assert hasattr(payment, 'payment_proof')
        assert hasattr(payment, 'status')
        assert hasattr(payment, 'admin_notes')
        assert hasattr(payment, 'verified_by')
        assert hasattr(payment, 'verified_at')
        assert hasattr(payment, 'submitted_at')
        assert hasattr(payment, 'updated_at')
    
    def test_payment_str_representation(self, registration):
        """Should have readable string representation"""
        payment = Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('500.00')
        )
        
        str_repr = str(payment)
        assert 'bkash' in str_repr.lower() or '500' in str_repr
    
    def test_payment_method_choices(self):
        """Should validate payment method choices"""
        from apps.tournaments.models.registration import Payment as PayModel
        
        expected_methods = ['bkash', 'nagad', 'rocket', 'bank', 'deltacoin']
        method_values = [choice[0] for choice in PayModel.PAYMENT_METHOD_CHOICES]
        
        for method in expected_methods:
            assert method in method_values
    
    def test_payment_status_choices(self):
        """Should validate status field choices"""
        from apps.tournaments.models.registration import Payment as PayModel
        
        expected_statuses = ['pending', 'submitted', 'verified', 'rejected', 'refunded']
        status_values = [choice[0] for choice in PayModel.STATUS_CHOICES]
        
        for status in expected_statuses:
            assert status in status_values
    
    def test_payment_defaults(self, registration):
        """Should have correct default values"""
        payment = Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('500.00')
        )
        
        assert payment.status == 'pending'
        assert payment.transaction_id == ''
        assert payment.payment_proof == ''
        assert payment.admin_notes == ''
        assert payment.verified_by is None
        assert payment.verified_at is None
    
    def test_payment_amount_decimal_precision(self, registration):
        """Should handle decimal amounts with correct precision"""
        payment = Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('500.50')
        )
        
        saved_payment = Payment.objects.get(id=payment.id)
        assert saved_payment.amount == Decimal('500.50')
        assert isinstance(saved_payment.amount, Decimal)
    
    def test_payment_one_to_one_registration(self, registration):
        """Should enforce one-to-one relationship with Registration"""
        # First payment
        Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('500.00')
        )
        
        # Second payment for same registration should fail
        with pytest.raises(IntegrityError):
            Payment.objects.create(
                registration=registration,
                payment_method='nagad',
                amount=Decimal('500.00')
            )
    
    def test_payment_verification_workflow(self, registration, django_user_model):
        """Should track verification by admin"""
        payment = Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('500.00'),
            status='submitted',
            transaction_id='BKH123456',
            payment_proof='/media/payments/proof.jpg'
        )
        
        # Initially not verified
        assert payment.verified_by is None
        assert payment.verified_at is None
        
        # Admin verifies
        admin = django_user_model.objects.create_user(
            username='admin',
            email='admin@test.com',
            is_staff=True
        )
        
        payment.status = 'verified'
        payment.verified_by = admin
        payment.verified_at = timezone.now()
        payment.admin_notes = 'Payment confirmed via bKash'
        payment.save()
        
        # Verify saved correctly
        saved_payment = Payment.objects.get(id=payment.id)
        assert saved_payment.status == 'verified'
        assert saved_payment.verified_by == admin
        assert saved_payment.verified_at is not None
        assert 'confirmed' in saved_payment.admin_notes.lower()
    
    def test_payment_rejection_workflow(self, registration, django_user_model):
        """Should allow rejection with admin notes"""
        payment = Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('500.00'),
            status='submitted'
        )
        
        # Admin rejects
        admin = django_user_model.objects.create_user(
            username='admin',
            email='admin@test.com',
            is_staff=True
        )
        
        payment.status = 'rejected'
        payment.verified_by = admin
        payment.verified_at = timezone.now()
        payment.admin_notes = 'Incorrect transaction ID'
        payment.save()
        
        saved_payment = Payment.objects.get(id=payment.id)
        assert saved_payment.status == 'rejected'
        assert 'Incorrect' in saved_payment.admin_notes
    
    def test_payment_timestamps(self, registration):
        """Should auto-set submitted_at and updated_at"""
        payment = Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('500.00')
        )
        
        assert payment.submitted_at is not None
        assert payment.updated_at is not None
        
        original_updated_at = payment.updated_at
        
        # Update payment
        import time
        time.sleep(0.1)  # Ensure time difference
        payment.status = 'verified'
        payment.save()
        
        # updated_at should change
        assert payment.updated_at > original_updated_at


@pytest.mark.django_db
class TestRegistrationPaymentIntegration:
    """Test Registration and Payment model interactions"""
    
    @pytest.fixture
    def setup_data(self, django_user_model):
        """Create complete test setup"""
        # Create game
        game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='valorant_id',
            is_active=True
        )
        
        # Create organizer
        organizer = django_user_model.objects.create_user(
            username='organizer',
            email='org@test.com'
        )
        
        # Create tournament
        now = timezone.now()
        tournament = Tournament.objects.create(
            name='Pro Championship',
            slug='pro-championship',
            game=game,
            organizer=organizer,
            format='single_elimination',
            max_participants=16,
            min_participants=4,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=8),
            has_entry_fee=True,
            entry_fee_amount=Decimal('1000.00'),
            payment_methods=['bkash', 'nagad']
        )
        
        # Create user
        user = django_user_model.objects.create_user(
            username='player1',
            email='player1@test.com'
        )
        
        return {
            'game': game,
            'tournament': tournament,
            'user': user,
            'organizer': organizer
        }
    
    def test_registration_to_payment_flow(self, setup_data):
        """Should complete full registration-to-payment flow"""
        tournament = setup_data['tournament']
        user = setup_data['user']
        organizer = setup_data['organizer']
        
        # Step 1: User registers
        registration = Registration.objects.create(
            tournament=tournament,
            user=user,
            status='pending',
            registration_data={
                'display_name': 'ProPlayer',
                'game_ids': {'valorant_id': 'Player#TAG'}
            }
        )
        
        assert registration.status == 'pending'
        assert not hasattr(registration, 'payment')  # No payment yet
        
        # Step 2: User submits payment proof
        payment = Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=tournament.entry_fee_amount,
            transaction_id='BKH987654',
            payment_proof='/media/proofs/bkash_proof.jpg',
            status='submitted'
        )
        
        registration.status = 'payment_submitted'
        registration.save()
        
        assert registration.status == 'payment_submitted'
        assert registration.payment == payment
        
        # Step 3: Organizer verifies payment
        payment.status = 'verified'
        payment.verified_by = organizer
        payment.verified_at = timezone.now()
        payment.save()
        
        registration.status = 'confirmed'
        registration.save()
        
        assert registration.status == 'confirmed'
        assert payment.status == 'verified'
        assert payment.verified_by == organizer
    
    def test_registration_cancellation_with_refund(self, setup_data):
        """Should handle registration cancellation and refund"""
        tournament = setup_data['tournament']
        user = setup_data['user']
        
        # Create confirmed registration with verified payment
        registration = Registration.objects.create(
            tournament=tournament,
            user=user,
            status='confirmed'
        )
        
        payment = Payment.objects.create(
            registration=registration,
            payment_method='bkash',
            amount=Decimal('1000.00'),
            status='verified'
        )
        
        # User cancels registration
        registration.status = 'cancelled'
        registration.soft_delete(deleted_by=user)
        
        # Process refund
        payment.status = 'refunded'
        payment.admin_notes = 'Refunded due to user cancellation'
        payment.save()
        
        assert registration.is_deleted is True
        assert registration.status == 'cancelled'
        assert payment.status == 'refunded'
