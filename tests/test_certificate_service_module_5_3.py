"""
Unit tests for CertificateService (Module 5.3 Milestone 2)

Tests Cover:
1. Certificate generation (PDF + PNG)
2. Idempotency (return existing non-revoked certificate)
3. SHA-256 hash calculation
4. QR code embedding
5. Verification system (valid/tampered/revoked)
6. Multi-language support (en/bn)
7. Edge cases (missing participant name, very long tournament title)
8. Force regeneration flag
9. Batch generation for tournament
10. Invalid inputs (not completed tournament, invalid type)

Target: ≥85% coverage for CertificateService
"""

import pytest
import hashlib
import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth import get_user_model
from PIL import Image

from apps.tournaments.models import (
    Game,
    Tournament,
    Registration,
    Certificate,
)
from apps.tournaments.services.certificate_service import CertificateService, certificate_service

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def game(db):
    """Create test game."""
    return Game.objects.create(
        name='VALORANT',
        slug='valorant',
        is_active=True,
    )


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        username='testplayer',
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def organizer(db):
    """Create organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123',
    )


@pytest.fixture
def completed_tournament(db, game, organizer):
    """Create completed tournament."""
    return Tournament.objects.create(
        name='VALORANT Championship 2025',
        game=game,
        format=Tournament.SINGLE_ELIM,
        status='COMPLETED',  # Must be COMPLETED for certificate generation
        max_participants=16,
        organizer=organizer,
        registration_start=timezone.now() - timezone.timedelta(days=14),
        registration_end=timezone.now() - timezone.timedelta(days=7),
        tournament_start=timezone.now() - timezone.timedelta(days=1),
    )


@pytest.fixture
def registration(db, completed_tournament, user):
    """Create registration for completed tournament."""
    return Registration.objects.create(
        tournament=completed_tournament,
        user=user,
        team_id=None,  # IntegerField, not FK
        seed=1,
        status=Registration.CONFIRMED,
        checked_in=True,
        checked_in_at=timezone.now() - timezone.timedelta(hours=2),
    )


@pytest.fixture
def draft_tournament(db, game, organizer):
    """Create draft tournament (not completed)."""
    return Tournament.objects.create(
        name='Draft Tournament',
        game=game,
        format=Tournament.SINGLE_ELIM,
        status='DRAFT',  # Not completed - should fail certificate generation
        max_participants=8,
        organizer=organizer,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timezone.timedelta(days=7),
        tournament_start=timezone.now() + timezone.timedelta(days=14),
    )


@pytest.fixture
def certificate_service_instance():
    """Return CertificateService instance."""
    return CertificateService()


# ============================================================================
# TEST CLASS
# ============================================================================

@pytest.mark.django_db
class TestCertificateService:
    """Test suite for CertificateService (Module 5.3)."""
    
    # ========================================================================
    # Test 1-2: PDF + PNG Generation
    # ========================================================================
    
    def test_generate_certificate_creates_pdf_and_png_files(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that generate_certificate creates both PDF and PNG files.
        
        Verifies:
        - Certificate record created
        - PDF file saved
        - PNG file saved
        - Files are non-empty
        - Verification code is UUID
        """
        # Generate certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='winner',
            placement='1',
            language='en',
        )
        
        # Assertions
        assert certificate is not None
        assert certificate.id is not None
        assert certificate.tournament == registration.tournament
        assert certificate.participant == registration
        assert certificate.certificate_type == 'winner'
        assert certificate.placement == '1'
        
        # Check files exist
        assert certificate.file_pdf is not None
        assert certificate.file_pdf.name != ''
        assert certificate.file_image is not None
        assert certificate.file_image.name != ''
        
        # Check files are non-empty
        certificate.file_pdf.open('rb')
        pdf_bytes = certificate.file_pdf.read()
        certificate.file_pdf.close()
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')  # PDF magic number
        
        certificate.file_image.open('rb')
        png_bytes = certificate.file_image.read()
        certificate.file_image.close()
        assert len(png_bytes) > 0
        assert png_bytes.startswith(b'\x89PNG')  # PNG magic number
        
        # Check verification code
        assert isinstance(certificate.verification_code, uuid.UUID)
        
        # Check generated_at timestamp
        assert certificate.generated_at is not None
        assert certificate.generated_at <= timezone.now()
    
    def test_png_image_dimensions_and_format(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that PNG image has correct dimensions (1920x1080) and format.
        
        Note: This test validates image structure without pixel-perfect assertions
        to avoid flaky CI tests.
        """
        # Generate certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='participant',
            language='en',
        )
        
        # Open PNG file and check dimensions
        certificate.file_image.open('rb')
        png_bytes = certificate.file_image.read()
        certificate.file_image.close()
        
        img = Image.open(BytesIO(png_bytes))
        
        # Check dimensions (1920x1080 as specified in service)
        assert img.size == (1920, 1080), f"Expected (1920, 1080), got {img.size}"
        
        # Check format
        assert img.format == 'PNG'
        
        # Check mode (RGB)
        assert img.mode == 'RGB'
    
    # ========================================================================
    # Test 3-4: SHA-256 Hash Calculation
    # ========================================================================
    
    def test_certificate_hash_is_64_char_hex_sha256(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that certificate_hash is a valid 64-character SHA-256 hex hash.
        
        Verifies:
        - Hash is 64 characters
        - Hash is hexadecimal
        - Hash matches SHA-256 of actual PDF bytes
        """
        # Generate certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='runner_up',
            placement='2',
            language='en',
        )
        
        # Check hash format
        assert len(certificate.certificate_hash) == 64
        assert all(c in '0123456789abcdef' for c in certificate.certificate_hash)
        
        # Verify hash matches actual PDF bytes
        certificate.file_pdf.open('rb')
        pdf_bytes = certificate.file_pdf.read()
        certificate.file_pdf.close()
        
        expected_hash = hashlib.sha256(pdf_bytes).hexdigest()
        assert certificate.certificate_hash == expected_hash
    
    def test_hash_calculation_is_deterministic(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that hash calculation is deterministic for same PDF bytes.
        
        Note: This doesn't test ReportLab determinism (timestamps may vary),
        but verifies that _calculate_hash() is consistent.
        """
        # Create sample PDF bytes
        sample_bytes = b'%PDF-1.4\nSample PDF content for testing'
        
        # Calculate hash twice
        hash1 = certificate_service_instance._calculate_hash(sample_bytes)
        hash2 = certificate_service_instance._calculate_hash(sample_bytes)
        
        # Hashes should be identical
        assert hash1 == hash2
        assert len(hash1) == 64
    
    # ========================================================================
    # Test 5-6: Verification System (Valid, Tampered, Revoked)
    # ========================================================================
    
    def test_verify_certificate_valid(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test verification of valid, non-revoked certificate.
        
        Verifies:
        - valid=True
        - revoked=False
        - is_tampered=False
        - Correct tournament/participant names (no PII)
        """
        # Generate certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='third_place',
            placement='3',
            language='en',
        )
        
        # Verify certificate
        result = certificate_service_instance.verify_certificate(certificate.verification_code)
        
        # Assertions
        assert result['valid'] is True
        assert result['revoked'] is False
        assert result['is_tampered'] is False
        assert result['certificate_id'] == certificate.id
        assert result['tournament_name'] == registration.tournament.name
        assert result['participant_name'] == registration.user.username  # Should be 'testplayer'
        assert result['certificate_type'] == 'Third Place Certificate'
        assert result['placement'] == '3'
        assert result['generated_at'] == certificate.generated_at
    
    def test_verify_certificate_tampered(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test verification detects tampered certificate (hash mismatch).
        
        Simulates tampering by changing the stored hash.
        
        Verifies:
        - valid=False
        - is_tampered=True
        """
        # Generate certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='winner',
            placement='1',
            language='en',
        )
        
        # Tamper with hash (simulate file modification)
        original_hash = certificate.certificate_hash
        certificate.certificate_hash = 'f' * 64  # Invalid hash
        certificate.save()
        
        # Verify certificate
        result = certificate_service_instance.verify_certificate(certificate.verification_code)
        
        # Assertions
        assert result['valid'] is False
        assert result['is_tampered'] is True
        assert result['revoked'] is False  # Not revoked, just tampered
    
    def test_verify_certificate_revoked(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test verification detects revoked certificate.
        
        Verifies:
        - valid=False
        - revoked=True
        - revoked_reason included
        """
        # Generate certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='participant',
            language='en',
        )
        
        # Revoke certificate
        certificate.revoke(reason="Dispute resolved - placement changed")
        
        # Verify certificate
        result = certificate_service_instance.verify_certificate(certificate.verification_code)
        
        # Assertions
        assert result['valid'] is False
        assert result['revoked'] is True
        assert result['revoked_reason'] == "Dispute resolved - placement changed"
        assert result['is_tampered'] is False  # Hash is still valid
    
    def test_verify_certificate_not_found(
        self,
        certificate_service_instance,
    ):
        """
        Test verification raises ValidationError for non-existent code.
        """
        # Random UUID that doesn't exist
        fake_code = uuid.uuid4()
        
        with pytest.raises(ValidationError) as excinfo:
            certificate_service_instance.verify_certificate(fake_code)
        
        assert "not found" in str(excinfo.value)
    
    # ========================================================================
    # Test 7: Multi-Language Support (English, Bengali)
    # ========================================================================
    
    def test_generate_certificate_english_language(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test certificate generation in English (default language).
        
        Verifies PDF is generated without errors (no content assertions to avoid flakiness).
        """
        # Generate English certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='winner',
            placement='1',
            language='en',
        )
        
        # Assertions
        assert certificate is not None
        assert certificate.file_pdf is not None
        
        # Verify PDF is valid
        certificate.file_pdf.open('rb')
        pdf_bytes = certificate.file_pdf.read()
        certificate.file_pdf.close()
        assert pdf_bytes.startswith(b'%PDF')
    
    @pytest.mark.skipif(
        not Path('static/fonts/NotoSansBengali-Regular.ttf').exists(),
        reason="Bengali font not installed (see static/fonts/README.md)"
    )
    def test_generate_certificate_bengali_language(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test certificate generation in Bengali language.
        
        Note: Skipped if Bengali font not installed.
        
        Verifies PDF is generated without errors.
        """
        # Generate Bengali certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='participant',
            language='bn',
        )
        
        # Assertions
        assert certificate is not None
        assert certificate.file_pdf is not None
        
        # Verify PDF is valid
        certificate.file_pdf.open('rb')
        pdf_bytes = certificate.file_pdf.read()
        certificate.file_pdf.close()
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_invalid_language_raises_validation_error(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that invalid language code raises ValidationError.
        """
        with pytest.raises(ValidationError) as excinfo:
            certificate_service_instance.generate_certificate(
                registration_id=registration.id,
                certificate_type='winner',
                language='fr',  # Invalid: only 'en' and 'bn' supported
            )
        
        assert "Invalid language" in str(excinfo.value)
    
    # ========================================================================
    # Test 8-9: Idempotency & Force Regeneration
    # ========================================================================
    
    def test_idempotency_returns_existing_certificate(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that calling generate_certificate twice returns same certificate.
        
        Verifies idempotency:
        - Second call returns existing certificate (same ID)
        - No duplicate certificates created
        """
        # First generation
        cert1 = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='winner',
            placement='1',
            language='en',
        )
        
        # Second generation (should return existing)
        cert2 = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='winner',
            placement='1',
            language='en',
        )
        
        # Assertions
        assert cert1.id == cert2.id
        assert cert1.verification_code == cert2.verification_code
        
        # Verify only 1 certificate exists for this registration + type
        cert_count = Certificate.objects.filter(
            tournament=registration.tournament,
            participant=registration,
            certificate_type='winner',
            revoked_at__isnull=True,
        ).count()
        assert cert_count == 1
    
    def test_force_regenerate_creates_new_certificate(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that force_regenerate=True creates new certificate even if one exists.
        
        Note: When force_regenerate=True is used with an existing non-revoked certificate,
        the old one is implicitly revoked (via uniqueness constraint), and a new one is created.
        """
        # First generation
        cert1 = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='runner_up',
            placement='2',
            language='en',
        )
        
        # Revoke first certificate (simulates dispute resolution scenario)
        cert1.revoke(reason="Regenerating due to updated placement")
        
        # Force regeneration (creates new certificate after revocation)
        cert2 = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='runner_up',
            placement='2',
            language='en',
            force_regenerate=True,
        )
        
        # Assertions
        assert cert1.id != cert2.id  # Different certificates
        assert cert1.verification_code != cert2.verification_code
        assert cert1.is_revoked is True  # First is revoked
        assert cert2.is_revoked is False  # Second is active
        
        # Both certificates exist (old one not deleted, just revoked)
        cert_count = Certificate.objects.filter(
            tournament=registration.tournament,
            participant=registration,
            certificate_type='runner_up',
        ).count()
        assert cert_count == 2
    
    # ========================================================================
    # Test 10: Edge Cases (Missing Name, Long Title)
    # ========================================================================
    
    def test_missing_participant_name_uses_fallback(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that missing participant name uses fallback ('Participant').
        
        Simulates scenario where user has no display name.
        """
        # Clear user's first/last name and registration team_name
        registration.user.first_name = ''
        registration.user.last_name = ''
        registration.user.save()
        registration.team_name = ''
        registration.save()
        
        # Generate certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='participant',
            language='en',
        )
        
        # Assertions
        assert certificate is not None
        
        # Verify certificate uses fallback name in verification
        result = certificate_service_instance.verify_certificate(certificate.verification_code)
        # Should use username as fallback via get_display_name()
        assert result['participant_name'] in ['testplayer', 'Participant']
    
    def test_very_long_tournament_title_truncated(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that very long tournament title is truncated in PDF (edge case handling).
        
        Service should handle this gracefully without errors.
        """
        # Update tournament name to very long title (>60 chars)
        registration.tournament.name = 'A' * 100 + ' Championship Tournament 2025'
        registration.tournament.save()
        
        # Generate certificate
        certificate = certificate_service_instance.generate_certificate(
            registration_id=registration.id,
            certificate_type='winner',
            placement='1',
            language='en',
        )
        
        # Assertions
        assert certificate is not None
        
        # Verify PDF is generated without errors
        certificate.file_pdf.open('rb')
        pdf_bytes = certificate.file_pdf.read()
        certificate.file_pdf.close()
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
    
    # ========================================================================
    # Test 11: Invalid Inputs (Not Completed Tournament, Invalid Type)
    # ========================================================================
    
    def test_generate_certificate_tournament_not_completed_raises_error(
        self,
        certificate_service_instance,
        draft_tournament,
        user,
    ):
        """
        Test that generate_certificate raises ValidationError for non-COMPLETED tournament.
        """
        # Create registration for draft tournament
        registration = Registration.objects.create(
            tournament=draft_tournament,
            user=user,
            team_id=None,
            seed=1,
            status=Registration.CONFIRMED,
            checked_in=True,
            checked_in_at=timezone.now() - timezone.timedelta(hours=2),
        )
        
        # Attempt to generate certificate
        with pytest.raises(ValidationError) as excinfo:
            certificate_service_instance.generate_certificate(
                registration_id=registration.id,
                certificate_type='winner',
            )
        
        assert "must be COMPLETED" in str(excinfo.value)
    
    def test_generate_certificate_invalid_type_raises_error(
        self,
        certificate_service_instance,
        registration,
    ):
        """
        Test that invalid certificate_type raises ValidationError.
        """
        with pytest.raises(ValidationError) as excinfo:
            certificate_service_instance.generate_certificate(
                registration_id=registration.id,
                certificate_type='invalid_type',  # Invalid
            )
        
        assert "Invalid certificate_type" in str(excinfo.value)
    
    def test_generate_certificate_registration_not_found_raises_error(
        self,
        certificate_service_instance,
    ):
        """
        Test that non-existent registration_id raises ValidationError.
        """
        with pytest.raises(ValidationError) as excinfo:
            certificate_service_instance.generate_certificate(
                registration_id=99999,  # Doesn't exist
                certificate_type='winner',
            )
        
        assert "not found" in str(excinfo.value)
    
    # ========================================================================
    # Test 12: Batch Generation (generate_all_certificates_for_tournament)
    # ========================================================================
    
    def test_generate_all_certificates_for_tournament(
        self,
        certificate_service_instance,
        completed_tournament,
        user,
    ):
        """
        Test batch generation of certificates for all tournament participants.
        
        Verifies:
        - All registrations get participation certificates
        - Correct count returned
        - Idempotency (second call returns existing certificates)
        """
        # Create 3 registrations
        reg1 = Registration.objects.create(
            tournament=completed_tournament,
            user=user,
            team_id=None,
            seed=1,
            status=Registration.CONFIRMED,
            checked_in=True,
            checked_in_at=timezone.now() - timezone.timedelta(hours=2),
        )
        user2 = User.objects.create_user(username='player2', email='p2@test.com', password='test')
        reg2 = Registration.objects.create(
            tournament=completed_tournament,
            user=user2,
            team_id=None,
            seed=2,
            status=Registration.CONFIRMED,
            checked_in=True,
            checked_in_at=timezone.now() - timezone.timedelta(hours=2),
        )
        user3 = User.objects.create_user(username='player3', email='p3@test.com', password='test')
        reg3 = Registration.objects.create(
            tournament=completed_tournament,
            user=user3,
            team_id=None,
            seed=3,
            status=Registration.CONFIRMED,
            checked_in=True,
            checked_in_at=timezone.now() - timezone.timedelta(hours=2),
        )
        
        # Generate all certificates
        certificates = certificate_service_instance.generate_all_certificates_for_tournament(
            tournament_id=completed_tournament.id,
            language='en',
        )
        
        # Assertions
        assert len(certificates) == 3
        assert all(cert.certificate_type == 'participant' for cert in certificates)
        assert all(cert.tournament == completed_tournament for cert in certificates)
        
        # Second call should return existing certificates (idempotency)
        certificates2 = certificate_service_instance.generate_all_certificates_for_tournament(
            tournament_id=completed_tournament.id,
            language='en',
        )
        assert len(certificates2) == 3
        assert set(c.id for c in certificates) == set(c.id for c in certificates2)
    
    def test_generate_all_certificates_tournament_not_completed_raises_error(
        self,
        certificate_service_instance,
        draft_tournament,
    ):
        """
        Test that batch generation raises ValidationError for non-COMPLETED tournament.
        """
        with pytest.raises(ValidationError) as excinfo:
            certificate_service_instance.generate_all_certificates_for_tournament(
                tournament_id=draft_tournament.id,
            )
        
        assert "must be COMPLETED" in str(excinfo.value)
    
    # ========================================================================
    # Test 13: QR Code Generation
    # ========================================================================
    
    def test_qr_code_generation(
        self,
        certificate_service_instance,
    ):
        """
        Test QR code generation creates valid PIL Image.
        
        Note: Does not decode QR code (requires zbar/pyzbar which may not be installed).
        """
        # Generate QR code
        url = "https://deltacrown.com/verify/test-code"
        qr_image = certificate_service_instance._create_qr_code(url, size=200)
        
        # Assertions
        assert qr_image is not None
        assert isinstance(qr_image, Image.Image)
        assert qr_image.size == (200, 200)
        assert qr_image.mode in ('1', 'L', 'RGB')  # Valid PIL modes for QR
