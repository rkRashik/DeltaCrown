# apps/economy/views/request_views.py
"""
Economy request API endpoints for top-up and withdrawal requests.

Owner-only economy actions with admin approval workflow.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging
import time

from apps.economy.models import (
    DeltaCrownWallet,
    TopUpRequest,
    WithdrawalRequest,
    DeltaCrownTransaction
)
from apps.user_profile.models import UserProfile

logger = logging.getLogger(__name__)


@login_required
@require_POST
def topup_request(request):
    """
    Create a top-up request (pending admin approval).
    
    POST /api/economy/topup/request/
    
    Payload:
        - amount (required): DC amount to top up
        - payment_method (required): bkash/nagad/rocket/bank
        - payment_number (required): Payment account number
        - user_note (optional): User's note/reference
    
    Returns:
        JSON with request data or error
    """
    start_time = time.time()
    
    try:
        # Get user's profile
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User profile not found'
            }, status=404)
        
        # Get or create wallet
        wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
        
        # Validate amount
        try:
            amount = int(request.POST.get('amount', 0))
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid amount'
            }, status=400)
        
        if amount <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Amount must be greater than 0'
            }, status=400)
        
        # Minimum top-up check (e.g., 10 DC)
        if amount < 10:
            return JsonResponse({
                'success': False,
                'error': 'Minimum top-up amount is 10 DC'
            }, status=400)
        
        # Validate payment method
        payment_method = request.POST.get('payment_method', '').lower()
        valid_methods = ['bkash', 'nagad', 'rocket', 'bank']
        if payment_method not in valid_methods:
            return JsonResponse({
                'success': False,
                'error': f'Invalid payment method. Must be one of: {", ".join(valid_methods)}'
            }, status=400)
        
        # Validate payment number
        payment_number = request.POST.get('payment_number', '').strip()
        if not payment_number:
            return JsonResponse({
                'success': False,
                'error': 'Payment number is required'
            }, status=400)
        
        # Optional user note
        user_note = request.POST.get('user_note', '').strip()
        
        # Get exchange rate (hardcoded for now, can be dynamic later)
        dc_to_bdt_rate = Decimal('1.00')  # 1 DC = 1 BDT for simplicity
        
        # Create top-up request
        topup = TopUpRequest.objects.create(
            wallet=wallet,
            amount=amount,
            status='pending',
            payment_method=payment_method,
            payment_number=payment_number,
            dc_to_bdt_rate=dc_to_bdt_rate,
            user_note=user_note,
            requested_at=timezone.now()
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[ECON] topup_request user={request.user.username} amount={amount} status=pending request_id={topup.id} ms={elapsed_ms}")
        
        return JsonResponse({
            'success': True,
            'request': {
                'id': topup.id,
                'amount': amount,
                'bdt_amount': float(topup.bdt_amount),
                'payment_method': payment_method,
                'status': 'pending',
                'requested_at': topup.requested_at.isoformat(),
                'message': 'Top-up request submitted. Awaiting admin approval.'
            }
        })
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[ECON] topup_request user={request.user.username} error={str(e)} ms={elapsed_ms}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to create top-up request'
        }, status=500)


@login_required
@require_POST
def withdraw_request(request):
    """
    Create a withdrawal request (pending admin approval).
    Requires PIN verification for security.
    
    POST /economy/api/withdraw/request/
    
    Payload:
        - amount (required): DC amount to withdraw
        - payment_method (required): bkash/nagad/rocket/bank
        - payment_number (required): Payment account number
        - pin (required): 6-digit wallet PIN
        - user_note (optional): User's note/reference
    
    Returns:
        JSON with request data or error
    """
    start_time = time.time()
    
    try:
        # Get user's profile
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User profile not found'
            }, status=404)
        
        # Get wallet
        try:
            wallet = DeltaCrownWallet.objects.get(profile=profile)
        except DeltaCrownWallet.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Wallet not found'
            }, status=404)
        
        # Validate amount
        try:
            amount = int(request.POST.get('amount', 0))
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid amount'
            }, status=400)
        
        if amount <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Amount must be greater than 0'
            }, status=400)
        
        # Minimum withdrawal check (e.g., 50 DC)
        if amount < 50:
            return JsonResponse({
                'success': False,
                'error': 'Minimum withdrawal amount is 50 DC'
            }, status=400)
        
        # Check sufficient balance
        if amount > wallet.cached_balance:
            return JsonResponse({
                'success': False,
                'error': f'Insufficient balance. You have {wallet.cached_balance} DC.'
            }, status=400)
        
        # Verify PIN (required for withdrawals)
        pin = request.POST.get('pin', '').strip()
        
        if not wallet.pin_enabled:
            return JsonResponse({
                'success': False,
                'error': 'PIN not set up. Please set up your PIN before withdrawing.',
                'pin_required': True
            }, status=400)
        
        if not pin:
            return JsonResponse({
                'success': False,
                'error': 'PIN is required for withdrawals'
            }, status=400)
        
        # Check PIN lockout
        if wallet.pin_locked_until and timezone.now() < wallet.pin_locked_until:
            remaining = int((wallet.pin_locked_until - timezone.now()).total_seconds() / 60)
            return JsonResponse({
                'success': False,
                'error': f'PIN locked. Try again in {remaining} minutes.'
            }, status=403)
        
        # Verify PIN
        if not check_password(pin, wallet.pin_hash):
            wallet.pin_failed_attempts += 1
            
            if wallet.pin_failed_attempts >= 5:
                from datetime import timedelta
                wallet.pin_locked_until = timezone.now() + timedelta(minutes=15)
                wallet.save()
                return JsonResponse({
                    'success': False,
                    'error': 'Too many failed attempts. PIN locked for 15 minutes.'
                }, status=403)
            else:
                wallet.save()
                remaining_attempts = 5 - wallet.pin_failed_attempts
                return JsonResponse({
                    'success': False,
                    'error': f'Incorrect PIN. {remaining_attempts} attempts remaining.'
                }, status=403)
        
        # PIN verified - reset failed attempts
        wallet.pin_failed_attempts = 0
        wallet.save()
        
        # Validate payment method
        payment_method = request.POST.get('payment_method', '').lower()
        valid_methods = ['bkash', 'nagad', 'rocket', 'bank']
        if payment_method not in valid_methods:
            return JsonResponse({
                'success': False,
                'error': f'Invalid payment method. Must be one of: {", ".join(valid_methods)}'
            }, status=400)
        
        # Validate payment number
        payment_number = request.POST.get('payment_number', '').strip()
        if not payment_number:
            return JsonResponse({
                'success': False,
                'error': 'Payment account number is required'
            }, status=400)
        
        # Optional user note
        user_note = request.POST.get('user_note', '').strip()
        
        # Get exchange rate (hardcoded for now)
        dc_to_bdt_rate = Decimal('1.00')  # 1 DC = 1 BDT
        
        # Processing fee (e.g., 2% of amount)
        processing_fee = int(amount * Decimal('0.02'))
        
        # Create withdrawal request
        withdrawal = WithdrawalRequest.objects.create(
            wallet=wallet,
            amount=amount,
            status='pending',
            payment_method=payment_method,
            payment_number=payment_number,
            dc_to_bdt_rate=dc_to_bdt_rate,
            processing_fee=processing_fee,
            user_note=user_note,
            requested_at=timezone.now()
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[ECON] withdraw_request user={request.user.username} amount={amount} status=pending request_id={withdrawal.id} ms={elapsed_ms}")
        
        return JsonResponse({
            'success': True,
            'request': {
                'id': withdrawal.id,
                'amount': amount,
                'processing_fee': processing_fee,
                'net_amount': amount - processing_fee,
                'bdt_amount': float(withdrawal.bdt_amount),
                'payment_method': payment_method,
                'status': 'pending',
                'requested_at': withdrawal.requested_at.isoformat(),
                'message': 'Withdrawal request submitted. Awaiting admin approval.'
            }
        })
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[ECON] withdraw_request user={request.user.username} error={str(e)} ms={elapsed_ms}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to create withdrawal request'
        }, status=500)
