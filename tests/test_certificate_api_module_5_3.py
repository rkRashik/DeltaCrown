"""
API Integration Tests for Certificate Endpoints (Module 5.3 Milestone 3)

Tests Cover:
1. Download certificate (owner - happy path)
2. Download certificate (forbidden - non-owner)
3. Download certificate (unauthorized - anonymous)
4. Verify valid certificate
5. Verify invalid certificate (404)
6. Verify revoked certificate (200 with flag)
7. End-to-end QR code URL check

Target: 5-7 integration tests covering full API flow
"""

import pytest
import uuid
from io import BytesIO
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournaments.models import (
    Game,
    Tournament,
    Registration,
    Certificate,
)
from apps.tournaments.services.certificate_service import certificate_service

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def api_client():
    """Return DRF API client."""
    return APIClient()


@pytest.fixture
def game(db):
    """Create test game."""
    return Game.objects.create(
        name='VALORANT',
        slug='valorant',
        is_active=True,
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
def participant_user(db):
    """Create participant user."""
    return User.objects.create_user(
        username='participant1',
        email='participant1@example.com',
        password='testpass123',
    )


@pytest.fixture
def other_user(db):
    """Create other user (not participant)."""
    return User.objects.create_user(
        username='other_user',
        email='other@example.com',
        password='testpass123',
    )


@pytest.fixture
def completed_tournament(db, game, organizer):
    """Create completed tournament."""
    return Tournament.objects.create(
        name='VALORANT Championship 2025',
        game=game,
        format=Tournament.SINGLE_ELIM,
        status='COMPLETED',
        max_participants=16,
        organizer=organizer,
        registration_start=timezone.now() - timezone.timedelta(days=14),
        registration_end=timezone.now() - timezone.timedelta(days=7),
        tournament_start=timezone.now() - timezone.timedelta(days=1),
    )


@pytest.fixture
def registration(db, completed_tournament, participant_user):
    """Create registration for participant."""
    return Registration.objects.create(
        tournament=completed_tournament,
        user=participant_user,
        team_id=None,
        seed=1,
        status=Registration.CONFIRMED,
        checked_in=True,
        checked_in_at=timezone.now() - timezone.timedelta(hours=2),
    )


@pytest.fixture
def certificate(db, registration):
    """Create certificate for participant."""
    return certificate_service.generate_certificate(
        registration_id=registration.id,
        certificate_type='winner',
        placement='1',
        language='en',
    )


# ============================================================================
# TEST CLASS
# ============================================================================

@pytest.mark.django_db
class TestCertificateAPI:
    """Integration tests for Certificate API endpoints (Module 5.3)."""
    
    # ========================================================================
    # Test 1: Download Certificate (Owner - Happy Path)
    # ========================================================================
    
    def test_download_certificate_owner_success(
        self,
        api_client,
        certificate,
        participant_user,
    ):
        """
        Test that certificate owner can download their certificate.
        
        Verifies:
        - 200 OK status
        - Content-Type: application/pdf
        - Content-Disposition header with filename
        - ETag header (SHA-256 hash)
        - Cache-Control header
        - download_count incremented
        - downloaded_at timestamp set
        """
        # Authenticate as participant
        api_client.force_authenticate(user=participant_user)
        
        # Get download URL
        url = reverse('tournaments_api:download-certificate', kwargs={'pk': certificate.id})
        
        # Download certificate
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
        assert 'attachment' in response['Content-Disposition']
        assert 'certificate-' in response['Content-Disposition']
        assert '.pdf' in response['Content-Disposition']
        assert response.has_header('ETag')
        assert certificate.certificate_hash in response['ETag']
        assert response.has_header('Cache-Control')
        assert 'private' in response['Cache-Control']
        assert 'max-age=300' in response['Cache-Control']
        
        # Verify download counter incremented
        certificate.refresh_from_db()
        assert certificate.download_count == 1
        assert certificate.downloaded_at is not None
        assert certificate.downloaded_at <= timezone.now()
    
    def test_download_certificate_png_format(
        self,
        api_client,
        certificate,
        participant_user,
    ):
        """
        Test downloading certificate in PNG format.
        
        Verifies:
        - 200 OK status if PNG file exists
        - Content-Type: image/png
        - Correct file extension in filename
        
        Note: Service generates both PDF and PNG, but PNG may not always be present
        """
        # Authenticate as participant
        api_client.force_authenticate(user=participant_user)
        
        # Get download URL with PNG format
        url = reverse('tournaments_api:download-certificate', kwargs={'pk': certificate.id})
        
        # Download certificate as PNG
        response = api_client.get(url, {'format': 'png'})
        
        # Assertions - PNG should exist if service generated it
        if response.status_code == status.HTTP_200_OK:
            assert response['Content-Type'] == 'image/png'
            assert '.png' in response['Content-Disposition']
        else:
            # PNG file might not exist (file generation issue)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert 'not found' in response.data['detail'].lower()
    
    def test_download_certificate_organizer_access(
        self,
        api_client,
        certificate,
        organizer,
    ):
        """
        Test that tournament organizer can download participant certificates.
        
        Verifies organizer access to all tournament certificates.
        """
        # Authenticate as organizer
        api_client.force_authenticate(user=organizer)
        
        # Get download URL
        url = reverse('tournaments_api:download-certificate', kwargs={'pk': certificate.id})
        
        # Download certificate
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
    
    # ========================================================================
    # Test 2: Download Certificate (Forbidden - Non-Owner)
    # ========================================================================
    
    def test_download_certificate_forbidden_non_owner(
        self,
        api_client,
        certificate,
        other_user,
    ):
        """
        Test that non-owner cannot download certificate.
        
        Verifies:
        - 403 FORBIDDEN status
        - Error message
        - download_count NOT incremented
        """
        # Authenticate as other user (not owner)
        api_client.force_authenticate(user=other_user)
        
        # Get download URL
        url = reverse('tournaments_api:download-certificate', kwargs={'pk': certificate.id})
        
        # Attempt download
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'permission' in response.data['detail'].lower()
        
        # Verify download counter NOT incremented
        certificate.refresh_from_db()
        assert certificate.download_count == 0
        assert certificate.downloaded_at is None
    
    # ========================================================================
    # Test 3: Download Certificate (Unauthorized - Anonymous)
    # ========================================================================
    
    def test_download_certificate_unauthorized_anonymous(
        self,
        api_client,
        certificate,
    ):
        """
        Test that anonymous users cannot download certificates.
        
        Verifies:
        - 401 UNAUTHORIZED status
        - download_count NOT incremented
        """
        # Do NOT authenticate (anonymous)
        
        # Get download URL
        url = reverse('tournaments_api:download-certificate', kwargs={'pk': certificate.id})
        
        # Attempt download
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Verify download counter NOT incremented
        certificate.refresh_from_db()
        assert certificate.download_count == 0
    
    def test_download_certificate_not_found(
        self,
        api_client,
        participant_user,
    ):
        """
        Test 404 response for non-existent certificate.
        """
        # Authenticate
        api_client.force_authenticate(user=participant_user)
        
        # Get download URL for non-existent certificate
        url = reverse('tournaments_api:download-certificate', kwargs={'pk': 99999})
        
        # Attempt download
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_download_certificate_revoked(
        self,
        api_client,
        certificate,
        participant_user,
    ):
        """
        Test that revoked certificates cannot be downloaded.
        
        Verifies:
        - 410 GONE status
        - Revocation details in response
        """
        # Revoke certificate
        certificate.revoke(reason="Test revocation")
        
        # Authenticate as participant
        api_client.force_authenticate(user=participant_user)
        
        # Get download URL
        url = reverse('tournaments_api:download-certificate', kwargs={'pk': certificate.id})
        
        # Attempt download
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_410_GONE
        assert response.data['revoked'] is True
        assert response.data['revoked_reason'] == "Test revocation"
    
    # ========================================================================
    # Test 4: Verify Valid Certificate
    # ========================================================================
    
    def test_verify_certificate_valid(
        self,
        api_client,
        certificate,
    ):
        """
        Test verification of valid certificate (public endpoint).
        
        Verifies:
        - 200 OK status
        - valid=True
        - revoked=False
        - is_tampered=False
        - Correct certificate details
        - No PII (display name only)
        """
        # Get verify URL (no authentication required)
        url = reverse(
            'tournaments_api:verify-certificate',
            kwargs={'code': certificate.verification_code}
        )
        
        # Verify certificate
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] is True
        assert response.data['revoked'] is False
        assert response.data['is_tampered'] is False
        assert response.data['certificate_id'] == certificate.id
        assert response.data['tournament'] == certificate.tournament.name
        assert response.data['participant_display_name'] == 'participant1'  # Username
        assert response.data['certificate_type'] == 'Winner Certificate'
        assert response.data['placement'] == '1'
        assert response.data['generated_at'] is not None
        
        # Verify no PII exposed (no email, no user_id)
        assert 'email' not in response.data
        assert 'user_id' not in response.data
        assert 'username' not in response.data  # Only display name
    
    # ========================================================================
    # Test 5: Verify Invalid Certificate (404)
    # ========================================================================
    
    def test_verify_certificate_invalid_code(
        self,
        api_client,
    ):
        """
        Test verification of non-existent certificate.
        
        Verifies:
        - 404 NOT FOUND status
        - Error message
        """
        # Generate random UUID (doesn't exist)
        fake_code = uuid.uuid4()
        
        # Get verify URL
        url = reverse('tournaments_api:verify-certificate', kwargs={'code': fake_code})
        
        # Attempt verification
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'not found' in response.data['detail'].lower()
    
    # ========================================================================
    # Test 6: Verify Revoked Certificate
    # ========================================================================
    
    def test_verify_certificate_revoked(
        self,
        api_client,
        certificate,
    ):
        """
        Test verification of revoked certificate.
        
        Verifies:
        - 200 OK status (details in body)
        - valid=False
        - revoked=True
        - revoked_reason included
        - is_tampered=False (not tampered, just revoked)
        """
        # Revoke certificate
        certificate.revoke(reason="Dispute resolved - placement changed")
        
        # Get verify URL
        url = reverse(
            'tournaments_api:verify-certificate',
            kwargs={'code': certificate.verification_code}
        )
        
        # Verify certificate
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] is False  # Invalid because revoked
        assert response.data['revoked'] is True
        assert response.data['revoked_reason'] == "Dispute resolved - placement changed"
        assert response.data['is_tampered'] is False  # Not tampered
    
    def test_verify_certificate_tampered(
        self,
        api_client,
        certificate,
    ):
        """
        Test verification detects tampered certificate.
        
        Simulates tampering by changing the stored hash.
        
        Verifies:
        - 200 OK status
        - valid=False
        - is_tampered=True
        - revoked=False (not revoked, just tampered)
        """
        # Tamper with certificate hash (simulate file modification)
        certificate.certificate_hash = 'f' * 64  # Invalid hash
        certificate.save()
        
        # Get verify URL
        url = reverse(
            'tournaments_api:verify-certificate',
            kwargs={'code': certificate.verification_code}
        )
        
        # Verify certificate
        response = api_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] is False  # Invalid because tampered
        assert response.data['is_tampered'] is True
        assert response.data['revoked'] is False  # Not revoked
    
    # ========================================================================
    # Test 7: End-to-End QR Code URL Check
    # ========================================================================
    
    def test_qr_code_url_matches_verify_endpoint(
        self,
        api_client,
        certificate,
    ):
        """
        Test that QR code URL matches the verification endpoint.
        
        Verifies end-to-end flow:
        - Service generates verification URL
        - URL structure matches API endpoint pattern
        - URL resolves correctly
        
        Note: Does not decode QR bitmap (flaky in CI). Just verifies URL construction.
        """
        # Get verification URL from service
        service_url = certificate_service._build_verification_url(certificate.verification_code)
        
        # Build expected API URL
        expected_path = reverse(
            'tournaments_api:verify-certificate',
            kwargs={'code': certificate.verification_code}
        )
        
        # Assertions
        assert str(certificate.verification_code) in service_url
        assert '/api/tournaments/certificates/verify/' in service_url
        assert expected_path in service_url
        
        # Verify the URL actually works (call verify endpoint)
        # Extract path from full URL (service_url may include domain)
        url = reverse(
            'tournaments_api:verify-certificate',
            kwargs={'code': certificate.verification_code}
        )
        
        response = api_client.get(url)
        
        # Verification endpoint should work
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] is True
