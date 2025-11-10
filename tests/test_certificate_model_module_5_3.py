"""
Test Certificate Model (Module 5.3: Certificates & Achievement Proofs)

Tests:
- Certificate creation with all fields
- Unique verification_code constraint
- UniqueConstraint enforcement (no duplicate certificates per type per participant unless revoked)

Implements:
- PHASE_5_IMPLEMENTATION_PLAN.md#module-53-certificates--achievement-proofs (model tests)
- PART_3.1_DATABASE_DESIGN_ERD.md (Certificate model structure)
- 01_ARCHITECTURE_DECISIONS.md#adr-012-pytest-for-testing-framework
"""
import pytest
from django.db import IntegrityError
from django.utils import timezone
from apps.tournaments.models import Certificate, Tournament, Registration, Game
from apps.accounts.models import User


@pytest.mark.django_db
class TestCertificateModel:
    """Test suite for Certificate model."""
    
    @pytest.fixture
    def setup_data(self):
        """Create test data: user, game, tournament, registration."""
        user = User.objects.create_user(
            username='testplayer',
            email='player@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Player'
        )
        
        game = Game.objects.create(
            name='VALORANT',
            slug='valorant',
            default_team_size=5,
            is_active=True
        )
        
        tournament = Tournament.objects.create(
            name='VALORANT Championship 2025',
            slug='valorant-championship-2025',
            game=game,
            organizer=user,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timezone.timedelta(days=7),
            tournament_start=timezone.now() + timezone.timedelta(days=14),
            tournament_end=timezone.now() + timezone.timedelta(days=15),
            max_participants=16,
            format='single_elimination',
            status='live'
        )
        
        registration = Registration.objects.create(
            tournament=tournament,
            user=user,
            status='confirmed'
        )
        
        return {
            'user': user,
            'game': game,
            'tournament': tournament,
            'registration': registration,
        }
    
    def test_certificate_creation_with_all_fields(self, setup_data):
        """
        Test creating a certificate with all required fields.
        
        Validates:
        - Certificate can be created successfully
        - All fields are stored correctly
        - verification_code is auto-generated (UUID4)
        - Timestamps are set automatically
        - Related objects (tournament, participant) are accessible
        """
        certificate = Certificate.objects.create(
            tournament=setup_data['tournament'],
            participant=setup_data['registration'],
            certificate_type='winner',
            placement='1st',
            file_pdf='certificates/pdf/2025/11/test_certificate.pdf',
            file_image='certificates/images/2025/11/test_certificate.png',
            certificate_hash='a' * 64,  # SHA-256 produces 64 hex characters
            download_count=0
        )
        
        # Verify certificate created
        assert certificate.id is not None
        assert certificate.tournament == setup_data['tournament']
        assert certificate.participant == setup_data['registration']
        assert certificate.certificate_type == 'winner'
        assert certificate.placement == '1st'
        assert certificate.certificate_hash == 'a' * 64
        
        # Verify verification_code auto-generated (UUID4)
        assert certificate.verification_code is not None
        assert len(str(certificate.verification_code)) == 36  # UUID4 format
        
        # Verify timestamps
        assert certificate.generated_at is not None
        assert certificate.created_at is not None
        assert certificate.updated_at is not None
        
        # Verify not revoked by default
        assert certificate.revoked_at is None
        assert certificate.revoked_reason == ''
        assert certificate.is_revoked is False
        
        # Verify download tracking defaults
        assert certificate.downloaded_at is None
        assert certificate.download_count == 0
        assert certificate.has_been_downloaded is False
        
        # Verify get_participant_display_name() method
        display_name = certificate.get_participant_display_name()
        assert display_name == 'Test Player'  # Uses user.get_full_name()
    
    def test_verification_code_unique_constraint(self, setup_data):
        """
        Test that verification_code is unique across all certificates.
        
        Validates:
        - verification_code is auto-generated and unique
        - Two certificates cannot have the same verification_code
        - Database enforces uniqueness constraint
        """
        # Create first certificate
        cert1 = Certificate.objects.create(
            tournament=setup_data['tournament'],
            participant=setup_data['registration'],
            certificate_type='winner',
            placement='1st',
            certificate_hash='a' * 64
        )
        
        # Create second registration for another user
        user2 = User.objects.create_user(
            username='testplayer2',
            email='player2@test.com',
            password='testpass123'
        )
        registration2 = Registration.objects.create(
            tournament=setup_data['tournament'],
            user=user2,
            status='confirmed'
        )
        
        # Create second certificate
        cert2 = Certificate.objects.create(
            tournament=setup_data['tournament'],
            participant=registration2,
            certificate_type='runner_up',
            placement='2nd',
            certificate_hash='b' * 64
        )
        
        # Verify verification_codes are different (auto-generated UUIDs)
        assert cert1.verification_code != cert2.verification_code
        
        # Verify attempting to manually set duplicate verification_code fails
        with pytest.raises(IntegrityError):
            Certificate.objects.create(
                tournament=setup_data['tournament'],
                participant=registration2,
                certificate_type='third_place',
                placement='3rd',
                certificate_hash='c' * 64,
                verification_code=cert1.verification_code  # Duplicate!
            )
    
    def test_unique_constraint_per_type_per_participant(self, setup_data):
        """
        Test UniqueConstraint: no duplicate certificates per type per participant (unless revoked).
        
        Validates:
        - Cannot create duplicate certificate for same participant + certificate_type
        - After revoking first certificate, can create new one (new verification_code)
        - Constraint only applies to non-revoked certificates (revoked_at IS NULL)
        """
        # Create first winner certificate
        cert1 = Certificate.objects.create(
            tournament=setup_data['tournament'],
            participant=setup_data['registration'],
            certificate_type='winner',
            placement='1st',
            certificate_hash='a' * 64
        )
        
        # Attempt to create duplicate winner certificate for same participant (should fail)
        from django.db import transaction
        
        with transaction.atomic():
            with pytest.raises(IntegrityError) as excinfo:
                Certificate.objects.create(
                    tournament=setup_data['tournament'],
                    participant=setup_data['registration'],
                    certificate_type='winner',  # Same type!
                    placement='1st',
                    certificate_hash='b' * 64
                )
        
        # Verify error is related to unique constraint
        assert 'unique_cert_per_type_per_participant' in str(excinfo.value)
        
        # Now revoke the first certificate
        cert1.revoke(reason='Result disputed and changed')
        assert cert1.is_revoked is True
        
        # After revocation, should be able to create new winner certificate
        cert2 = Certificate.objects.create(
            tournament=setup_data['tournament'],
            participant=setup_data['registration'],
            certificate_type='winner',
            placement='1st',
            certificate_hash='c' * 64
        )
        
        # Verify new certificate created with different verification_code
        assert cert2.id is not None
        assert cert2.verification_code != cert1.verification_code
        assert cert2.is_revoked is False
        
        # Verify can create different certificate type for same participant (no conflict)
        cert3 = Certificate.objects.create(
            tournament=setup_data['tournament'],
            participant=setup_data['registration'],
            certificate_type='participant',  # Different type
            placement='',
            certificate_hash='d' * 64
        )
        
        assert cert3.id is not None
        assert cert3.certificate_type == 'participant'
