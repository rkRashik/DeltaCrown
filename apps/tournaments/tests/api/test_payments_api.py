# apps/tournaments/tests/api/test_payments_api.py
"""
Tests for Milestone C: Payments API

Covers submit-proof, verify, reject, refund endpoints with:
- State machine validation (PENDING → VERIFIED/REJECTED, VERIFIED → REFUNDED)
- Permissions (owner for submit-proof, staff for moderation)
- Idempotency (replay detection via Idempotency-Key header)
- Error cases (409 conflicts, 400 validation errors, 403 permissions)

Target: 10-12 tests, 0 skips, all passing.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.tournaments.models import PaymentVerification, Registration

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    """Staff user for moderation actions - using superuser for test reliability."""
    user = User.objects.create_superuser(
        username="staff_user",
        email="staff@test.com",
        password="testpass123"
    )
    user.refresh_from_db()
    assert user.is_staff is True
    assert user.is_superuser is True
    return user


@pytest.fixture
def staff_api_client(staff_user):
    """API client authenticated as staff using session-backed login."""
    client = APIClient()
    client.force_login(staff_user)  # Session-backed, not force_authenticate
    return client


@pytest.fixture
def owner_user(db):
    """Regular user who owns a registration."""
    return User.objects.create_user(
        username="owner_user",
        email="owner@test.com",
        password="testpass123"
    )


@pytest.fixture
def other_user(db):
    """Another regular user (not owner)."""
    return User.objects.create_user(
        username="other_user",
        email="other@test.com",
        password="testpass123"
    )


@pytest.fixture
def pv_pending(db, owner_user, game_factory, tournament_factory):
    """PaymentVerification in PENDING state with registration."""
    from apps.tournaments.models import Registration
    
    game = game_factory(slug='valorant', team_size=5, profile_id_field='riot_id')
    tournament = tournament_factory(game=game, participation_type='solo', entry_fee=500)
    
    reg = Registration.objects.create(
        tournament=tournament,
        user=owner_user,
        status='pending'
    )
    
    pv = PaymentVerification.objects.create(
        registration=reg,
        method='bkash',
        payer_account_number='01700000000',
        transaction_id='TX-PENDING-001',
        amount_bdt=500,
        status='pending',
        notes={}
    )
    return pv


@pytest.fixture
def pv_verified(db, owner_user, game_factory, tournament_factory, staff_user):
    """PaymentVerification in VERIFIED state."""
    from apps.tournaments.models import Registration
    from django.utils import timezone
    
    game = game_factory(slug='efootball', team_size=1, profile_id_field='efootball_id')
    tournament = tournament_factory(game=game, participation_type='solo', entry_fee=750)
    
    reg = Registration.objects.create(
        tournament=tournament,
        user=owner_user,
        status='pending'
    )
    
    pv = PaymentVerification.objects.create(
        registration=reg,
        method='nagad',
        payer_account_number='01800000000',
        transaction_id='TX-VERIFIED-001',
        amount_bdt=750,
        status='verified',
        verified_at=timezone.now(),
        verified_by=staff_user,
        notes={}
    )
    return pv


@pytest.fixture
def pv_rejected(db, owner_user, game_factory, tournament_factory, staff_user):
    """PaymentVerification in REJECTED state."""
    from apps.tournaments.models import Registration
    from django.utils import timezone
    
    game = game_factory(slug='fifa', team_size=1, profile_id_field='ea_id')
    tournament = tournament_factory(game=game, participation_type='solo', entry_fee=600)
    
    reg = Registration.objects.create(
        tournament=tournament,
        user=owner_user,
        status='pending'
    )
    
    pv = PaymentVerification.objects.create(
        registration=reg,
        method='rocket',
        payer_account_number='01900000000',
        transaction_id='TX-REJECTED-001',
        amount_bdt=300,
        status='rejected',
        rejected_at=timezone.now(),
        rejected_by=staff_user,
        notes={'reason_code': 'MISMATCH'}
    )
    return pv


# ============================================================================
# Submit Proof Tests (Owner-only)
# ============================================================================

@pytest.mark.django_db
class TestSubmitProof:
    
    def test_submit_proof_happy_path_sets_pending_and_stores_fields(self, owner_user, pv_pending):
        """Owner can submit proof for PENDING payment."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        client.force_authenticate(user=owner_user)
        
        url = f'/api/tournaments/payments/{pv_pending.id}/submit-proof/'
        payload = {
            'transaction_id': 'TX-NEW-123',
            'payer_account_number': '01711111111',
            'amount_bdt': 600,
            'notes': {'receipt_type': 'screenshot'}
        }
        
        response = client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'pending'
        assert response.data['transaction_id'] == 'TX-NEW-123'
        assert response.data['payer_account_number'] == '01711111111'
        assert response.data['amount_bdt'] == 600
        assert response.data['idempotent_replay'] is False
        
        # Verify DB update
        pv_pending.refresh_from_db()
        assert pv_pending.transaction_id == 'TX-NEW-123'
        assert pv_pending.amount_bdt == 600
    
    def test_submit_proof_denied_for_non_owner_403(self, pv_pending, db):
        """Non-owner cannot submit proof for someone else's payment."""
        from rest_framework.test import APIClient
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        other_user = User.objects.create_user(username='other_test', email='other@test.com', password='pass')
        
        client = APIClient()
        client.force_authenticate(user=other_user)
        
        url = f'/api/tournaments/payments/{pv_pending.id}/submit-proof/'
        payload = {
            'transaction_id': 'TX-HACK-999',
            'payer_account_number': '01799999999',
            'amount_bdt': 1000
        }
        
        response = client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_submit_proof_idempotent_replay_returns_same_payload(self, owner_user, pv_pending):
        """Replaying same Idempotency-Key returns original response without re-processing."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        client.force_authenticate(user=owner_user)
        
        url = f'/api/tournaments/payments/{pv_pending.id}/submit-proof/'
        payload = {
            'transaction_id': 'TX-IDEM-001',
            'payer_account_number': '01722222222',
            'amount_bdt': 400
        }
        headers = {'HTTP_IDEMPOTENCY_KEY': 'submit-key-alpha'}
        
        # First request
        response1 = client.post(url, payload, format='json', **headers)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data['idempotent_replay'] is False
        assert response1.data['transaction_id'] == 'TX-IDEM-001'
        
        # Replay with same key (even different payload, but same key)
        payload2 = {
            'transaction_id': 'TX-DIFFERENT',
            'payer_account_number': '01733333333',
            'amount_bdt': 999
        }
        response2 = client.post(url, payload2, format='json', **headers)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['idempotent_replay'] is True
        # Should return original data, not new payload
        assert response2.data['transaction_id'] == 'TX-IDEM-001'
        assert response2.data['amount_bdt'] == 400
    
    def test_submit_proof_allows_resubmit_after_reject_goes_back_to_pending(self, owner_user, pv_rejected):
        """Owner can resubmit proof after rejection, transitioning REJECTED → PENDING."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        client.force_authenticate(user=owner_user)
        
        url = f'/api/tournaments/payments/{pv_rejected.id}/submit-proof/'
        payload = {
            'transaction_id': 'TX-RESUBMIT-999',
            'payer_account_number': '01744444444',
            'amount_bdt': 350,
            'notes': {'retry_reason': 'fixed account number'}
        }
        
        response = client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'pending'
        assert response.data['transaction_id'] == 'TX-RESUBMIT-999'
        
        # Verify DB transition
        pv_rejected.refresh_from_db()
        assert pv_rejected.status == 'pending'
        assert pv_rejected.transaction_id == 'TX-RESUBMIT-999'


# ============================================================================
# Verify Tests (Staff-only)
# ============================================================================

@pytest.mark.django_db
class TestVerify:
    
    def test_verify_happy_path_transitions_pending_to_verified_sets_actor_timestamp(self, staff_api_client, staff_user, pv_pending):
        """Staff can verify PENDING payment, setting verified_at and verified_by."""
        
        url = f'/api/tournaments/payments/{pv_pending.id}/verify/'
        payload = {'notes': {'checked_by': 'finance_team'}}
        
        response = staff_api_client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'verified'
        assert response.data['verified_at'] is not None
        assert response.data['idempotent_replay'] is False
        
        # Verify DB update
        pv_pending.refresh_from_db()
        assert pv_pending.status == 'verified'
        assert pv_pending.verified_by_id == staff_user.id
        assert pv_pending.verified_at is not None
    
    def test_verify_invalid_state_from_verified_conflict_409(self, staff_api_client, pv_verified):
        """Cannot verify an already-verified payment (409 conflict)."""
        
        url = f'/api/tournaments/payments/{pv_verified.id}/verify/'
        payload = {}
        
        response = staff_api_client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'Invalid state transition' in response.data['detail']
    
    def test_verify_idempotent_replay_returns_same_result(self, staff_api_client, pv_pending):
        """Replaying verify with same Idempotency-Key returns original response."""
        
        url = f'/api/tournaments/payments/{pv_pending.id}/verify/'
        payload = {'notes': {'approval_code': 'APPROVE-001'}}
        headers = {'HTTP_IDEMPOTENCY_KEY': 'verify-key-beta'}
        
        # First request
        response1 = staff_api_client.post(url, payload, format='json', **headers)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data['status'] == 'verified'
        assert response1.data['idempotent_replay'] is False
        
        # Replay with same key
        response2 = staff_api_client.post(url, payload, format='json', **headers)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['idempotent_replay'] is True
        assert response2.data['status'] == 'verified'


# ============================================================================
# Reject Tests (Staff-only)
# ============================================================================

@pytest.mark.django_db
class TestReject:
    
    def test_reject_happy_path_sets_rejected_with_reason(self, staff_api_client, staff_user, pv_pending):
        """Staff can reject PENDING payment with reason code."""
        
        url = f'/api/tournaments/payments/{pv_pending.id}/reject/'
        payload = {
            'reason_code': 'FRAUD',
            'notes': {'investigator': 'security_team'}
        }
        
        response = staff_api_client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'rejected'
        assert response.data['rejected_at'] is not None
        assert response.data['idempotent_replay'] is False
        
        # Verify DB update
        pv_pending.refresh_from_db()
        assert pv_pending.status == 'rejected'
        assert pv_pending.rejected_by_id == staff_user.id
        assert pv_pending.rejected_at is not None
        assert pv_pending.notes['reason_code'] == 'FRAUD'
    
    def test_reject_invalid_state_from_verified_conflict_409(self, staff_api_client, pv_verified):
        """Cannot reject a VERIFIED payment (409 conflict)."""
        
        url = f'/api/tournaments/payments/{pv_verified.id}/reject/'
        payload = {'reason_code': 'TOO_LATE'}
        
        response = staff_api_client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'Invalid state transition' in response.data['detail']
    
    def test_reject_idempotent_replay_returns_same_result(self, staff_api_client, pv_pending):
        """Replaying reject with same Idempotency-Key returns original response."""
        
        url = f'/api/tournaments/payments/{pv_pending.id}/reject/'
        payload = {'reason_code': 'BLURRY_PROOF'}
        headers = {'HTTP_IDEMPOTENCY_KEY': 'reject-key-gamma'}
        
        # First request
        response1 = staff_api_client.post(url, payload, format='json', **headers)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data['status'] == 'rejected'
        assert response1.data['idempotent_replay'] is False
        
        # Replay with same key
        response2 = staff_api_client.post(url, payload, format='json', **headers)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['idempotent_replay'] is True
        assert response2.data['status'] == 'rejected'


# ============================================================================
# Refund Tests (Staff-only)
# ============================================================================

@pytest.mark.django_db
class TestRefund:
    
    def test_refund_happy_path_from_verified_sets_refunded_and_actor_timestamp(self, staff_api_client, staff_user, pv_verified):
        """Staff can refund VERIFIED payment, setting refunded_at and refunded_by."""
        
        url = f'/api/tournaments/payments/{pv_verified.id}/refund/'
        payload = {
            'amount_bdt': 750,
            'reason_code': 'TOURNAMENT_CANCELLED',
            'notes': {'processed_by': 'accounts_team'}
        }
        
        response = staff_api_client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'refunded'
        assert response.data['refunded_at'] is not None
        assert response.data['idempotent_replay'] is False
        
        # Verify DB update
        pv_verified.refresh_from_db()
        assert pv_verified.status == 'refunded'
        assert pv_verified.refunded_by_id == staff_user.id
        assert pv_verified.refunded_at is not None
        assert pv_verified.notes['refund_amount'] == 750
        assert pv_verified.notes['refund_reason_code'] == 'TOURNAMENT_CANCELLED'
    
    def test_refund_invalid_state_from_pending_conflict_409(self, staff_api_client, pv_pending):
        """Cannot refund a PENDING payment (409 conflict - must be VERIFIED first)."""
        
        url = f'/api/tournaments/payments/{pv_pending.id}/refund/'
        payload = {
            'amount_bdt': 500,
            'reason_code': 'USER_REQUEST'
        }
        
        response = staff_api_client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'Invalid state transition' in response.data['detail']
    
    def test_refund_idempotent_replay_returns_same_result(self, staff_api_client, pv_verified):
        """Replaying refund with same Idempotency-Key returns original response."""
        
        url = f'/api/tournaments/payments/{pv_verified.id}/refund/'
        payload = {
            'amount_bdt': 750,
            'reason_code': 'DUPLICATE_PAYMENT'
        }
        headers = {'HTTP_IDEMPOTENCY_KEY': 'refund-key-delta'}
        
        # First request
        response1 = staff_api_client.post(url, payload, format='json', **headers)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data['status'] == 'refunded'
        assert response1.data['idempotent_replay'] is False
        
        # Replay with same key
        response2 = staff_api_client.post(url, payload, format='json', **headers)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['idempotent_replay'] is True
        assert response2.data['status'] == 'refunded'
    
    def test_refund_amount_exceeds_original_400(self, staff_api_client, pv_verified):
        """Refund amount exceeding original payment returns 400."""
        
        url = f'/api/tournaments/payments/{pv_verified.id}/refund/'
        payload = {
            'amount_bdt': 9999,  # pv_verified has 750
            'reason_code': 'ERROR'
        }
        
        response = staff_api_client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'exceeds original amount' in response.data['detail']
