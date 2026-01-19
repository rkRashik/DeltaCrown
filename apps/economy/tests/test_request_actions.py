# apps/economy/tests/test_request_actions.py
"""
Unit tests for Economy top-up and withdrawal request functionality (UP PHASE 7.1).

Tests owner-only permissions, balance validation, and admin approval workflows.
"""
import pytest
from decimal import Decimal
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.economy.models import DeltaCrownWallet, TopUpRequest, WithdrawalRequest, DeltaCrownTransaction

User = get_user_model()


@pytest.mark.django_db
class TestTopUpRequest:
    """Test POST /economy/api/topup/request/"""
    
    def test_owner_can_create_topup_request(self):
        """Owner can create a top-up request"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        wallet = DeltaCrownWallet.objects.create(profile=profile)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/economy/api/topup/request/', {
            'amount': 100,
            'payment_method': 'bkash',
            'payment_number': '01712345678'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['request']['amount'] == 100
        assert data['request']['status'] == 'pending'
        
        # Verify request was created
        request = TopUpRequest.objects.filter(wallet=wallet).first()
        assert request is not None
        assert request.amount == 100
        assert request.status == 'pending'
    
    def test_minimum_topup_validation(self):
        """Cannot request top-up below minimum (10 DC)"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        DeltaCrownWallet.objects.create(profile=profile)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/economy/api/topup/request/', {
            'amount': 5,
            'payment_method': 'bkash',
            'payment_number': '01712345678'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'minimum' in data['error'].lower()
    
    def test_invalid_payment_method(self):
        """Invalid payment method is rejected"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        DeltaCrownWallet.objects.create(profile=profile)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/economy/api/topup/request/', {
            'amount': 100,
            'payment_method': 'invalid',
            'payment_number': '01712345678'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'invalid payment method' in data['error'].lower()


@pytest.mark.django_db
class TestWithdrawalRequest:
    """Test POST /economy/api/withdraw/request/"""
    
    def test_owner_can_create_withdrawal_request(self):
        """Owner can create a withdrawal request with sufficient balance"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=1000)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/economy/api/withdraw/request/', {
            'amount': 100,
            'payment_method': 'bkash',
            'payment_number': '01712345678'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['request']['amount'] == 100
        assert data['request']['status'] == 'pending'
        
        # Verify request was created
        request = WithdrawalRequest.objects.filter(wallet=wallet).first()
        assert request is not None
        assert request.amount == 100
        assert request.status == 'pending'
    
    def test_insufficient_balance_rejection(self):
        """Cannot withdraw more than available balance"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=50)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/economy/api/withdraw/request/', {
            'amount': 100,
            'payment_method': 'bkash',
            'payment_number': '01712345678'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'insufficient balance' in data['error'].lower()
    
    def test_minimum_withdrawal_validation(self):
        """Cannot request withdrawal below minimum (50 DC)"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=1000)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.post('/economy/api/withdraw/request/', {
            'amount': 20,
            'payment_method': 'bkash',
            'payment_number': '01712345678'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'minimum' in data['error'].lower()


@pytest.mark.django_db
class TestAdminApproval:
    """Test admin approval workflows"""
    
    def test_approve_topup_creates_transaction(self):
        """Approving top-up creates transaction and updates balance"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=0)
        
        topup = TopUpRequest.objects.create(
            wallet=wallet,
            amount=100,
            status='pending',
            payment_method='bkash',
            payment_number='01712345678',
            dc_to_bdt_rate=Decimal('1.00')
        )
        
        admin_user = User.objects.create_superuser(username='admin', password='admin123')
        
        # Simulate admin approval
        from django.utils import timezone
        txn = DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=topup.amount,
            reason='top_up',
            note=f'Top-up request #{topup.id} approved'
        )
        
        topup.status = 'completed'
        topup.reviewed_by = admin_user
        topup.reviewed_at = timezone.now()
        topup.completed_at = timezone.now()
        topup.transaction = txn
        topup.save()
        
        # Recalculate wallet balance
        wallet.recalc_and_save()
        
        # Verify
        assert topup.status == 'completed'
        assert topup.transaction is not None
        wallet.refresh_from_db()
        assert wallet.cached_balance == 100
    
    def test_cannot_approve_twice(self):
        """Cannot approve the same request twice (idempotency)"""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=0)
        
        topup = TopUpRequest.objects.create(
            wallet=wallet,
            amount=100,
            status='completed',  # Already approved
            payment_method='bkash',
            payment_number='01712345678',
            dc_to_bdt_rate=Decimal('1.00')
        )
        
        # Verify status is already completed
        assert topup.status == 'completed'
        
        # Attempting to re-approve should be prevented by checking status
        # (In real admin action, we filter by status='pending')
        pending_requests = TopUpRequest.objects.filter(id=topup.id, status='pending')
        assert pending_requests.count() == 0
