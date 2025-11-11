"""
DeltaCoin Shop Services - Module 7.2

Spend authorization and refund flows:
- authorize_spend(): Create reservation hold on wallet
- capture(): Convert hold to debit transaction
- release(): Void authorization (no debit)
- refund(): Compensating credit for captured transaction
- get_available_balance(): Cached balance minus active holds
"""

import time
import random
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import timedelta

from django.db import transaction, models
from django.utils import timezone

from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.economy.services import debit, credit
from apps.economy.exceptions import IdempotencyConflict as EconomyIdempotencyConflict, InsufficientFunds

from .models import ShopItem, ReservationHold
from .exceptions import (
    InvalidStateTransition,
    HoldExpired,
    InvalidTransaction,
    HoldNotFound,
    InvalidAmount,
    ItemNotFound,
    ItemNotActive,
    IdempotencyConflict,
)


# ==============================================================================
# Retry Wrapper
# ==============================================================================

def retry_on_serialization(max_attempts=3):
    """Decorator for bounded retry on serialization/deadlock errors."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    is_retryable = any(keyword in error_msg for keyword in [
                        'deadlock', 'serialization', 'could not serialize', 'lock timeout'
                    ])
                    
                    attempt += 1
                    if not is_retryable or attempt >= max_attempts:
                        raise
                    
                    delay = (0.1 * (2 ** attempt)) + random.uniform(0, 0.1)
                    time.sleep(delay)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ==============================================================================
# Helper Functions
# ==============================================================================

def _derive_idempotency_key(base_key: Optional[str], suffix: str) -> Optional[str]:
    """Derive operation-specific idempotency key."""
    if base_key is None:
        return None
    return f"{base_key}{suffix}"


# ==============================================================================
# Public API
# ==============================================================================

@retry_on_serialization(max_attempts=3)
def authorize_spend(
    wallet: DeltaCrownWallet,
    amount: Decimal,
    *,
    sku: str,
    idempotency_key: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    expires_at: Optional[timezone.datetime] = None
) -> Dict[str, Any]:
    """Create reservation hold on wallet."""
    if amount <= 0:
        raise InvalidAmount(f"Amount must be positive, got {amount}")
    
    derived_key = _derive_idempotency_key(idempotency_key, '_auth')
    
    with transaction.atomic():
        wallet = DeltaCrownWallet.objects.select_for_update().get(id=wallet.id)
        
        # Check idempotent replay
        if derived_key:
            existing_hold = ReservationHold.objects.filter(
                idempotency_key=derived_key,
                wallet=wallet
            ).first()
            if existing_hold:
                return {
                    'hold_id': existing_hold.id,
                    'wallet_id': existing_hold.wallet_id,
                    'amount': existing_hold.amount,
                    'sku': existing_hold.sku,
                    'status': existing_hold.status,
                    'expires_at': existing_hold.expires_at,
                    'created_at': existing_hold.created_at,
                }
        
        # Validate SKU
        try:
            item = ShopItem.objects.get(sku=sku)
        except ShopItem.DoesNotExist:
            raise ItemNotFound(f"SKU '{sku}' does not exist")
        
        if not item.active:
            raise ItemNotActive(f"SKU '{sku}' is not active")
        
        # Calculate available balance
        active_holds = ReservationHold.objects.filter(
            wallet=wallet,
            status='authorized'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        available_balance = wallet.cached_balance - active_holds
        
        # Check sufficient funds
        if not wallet.allow_overdraft and available_balance < amount:
            raise InsufficientFunds(
                f"Insufficient available balance: {available_balance} < {amount}"
            )
        
        # Set default expiry (24 hours)
        if expires_at is None:
            expires_at = timezone.now() + timedelta(hours=24)
        
        # Create hold
        hold = ReservationHold.objects.create(
            wallet=wallet,
            sku=sku,
            amount=int(amount),
            status='authorized',
            expires_at=expires_at,
            idempotency_key=derived_key,
            meta=meta or {}
        )
        
        return {
            'hold_id': hold.id,
            'wallet_id': hold.wallet_id,
            'amount': hold.amount,
            'sku': hold.sku,
            'status': hold.status,
            'expires_at': hold.expires_at,
            'created_at': hold.created_at,
        }


@retry_on_serialization(max_attempts=3)
def capture(
    wallet: DeltaCrownWallet,
    authorization_id: int,
    *,
    idempotency_key: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Capture authorized hold - convert to debit transaction."""
    derived_key = _derive_idempotency_key(idempotency_key, '_capture')
    
    with transaction.atomic():
        wallet = DeltaCrownWallet.objects.select_for_update().get(id=wallet.id)
        
        try:
            hold = ReservationHold.objects.select_for_update().get(
                id=authorization_id,
                wallet=wallet
            )
        except ReservationHold.DoesNotExist:
            raise HoldNotFound(f"Hold {authorization_id} not found")
        
        # Check idempotent replay
        if hold.status == 'captured' and hold.idempotency_key == derived_key:
            return {
                'hold_id': hold.id,
                'wallet_id': hold.wallet_id,
                'amount': hold.amount,
                'status': hold.status,
                'transaction_id': hold.captured_txn_id,
                'captured_at': hold.created_at,
            }
        
        # Validate state
        if hold.status != 'authorized':
            raise InvalidStateTransition(f"Cannot capture hold with status '{hold.status}'")
        
        # Check expiration
        if hold.expires_at and timezone.now() > hold.expires_at:
            hold.status = 'expired'
            hold.save(update_fields=['status'])
            raise HoldExpired(f"Hold {authorization_id} expired")
        
        # Create debit
        debit_key = _derive_idempotency_key(idempotency_key, '_capture_debit')
        try:
            debit_result = debit(
                profile=wallet.profile,  # economy services expect profile, not wallet
                amount=int(hold.amount),  # economy services use int, not Decimal
                reason='SHOP_PURCHASE',
                idempotency_key=debit_key,
                meta={'hold_id': hold.id, 'sku': hold.sku, **(meta or {})}
            )
        except EconomyIdempotencyConflict:
            existing_txn = DeltaCrownTransaction.objects.get(idempotency_key=debit_key)
            debit_result = {
                'transaction_id': existing_txn.id,
                'wallet_id': existing_txn.wallet_id,
                'amount': existing_txn.amount,
            }
        
        # Update hold
        hold.status = 'captured'
        hold.captured_txn_id = debit_result['transaction_id']
        hold.idempotency_key = derived_key
        if meta:
            hold.meta.update(meta)
        hold.save(update_fields=['status', 'captured_txn_id', 'idempotency_key', 'meta'])
        
        return {
            'hold_id': hold.id,
            'wallet_id': hold.wallet_id,
            'amount': hold.amount,
            'status': hold.status,
            'transaction_id': hold.captured_txn_id,
            'captured_at': timezone.now(),
        }


@retry_on_serialization(max_attempts=3)
def release(
    wallet: DeltaCrownWallet,
    authorization_id: int,
    *,
    idempotency_key: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Release (void) authorized hold - no debit."""
    derived_key = _derive_idempotency_key(idempotency_key, '_release')
    
    with transaction.atomic():
        wallet = DeltaCrownWallet.objects.select_for_update().get(id=wallet.id)
        
        try:
            hold = ReservationHold.objects.select_for_update().get(
                id=authorization_id,
                wallet=wallet
            )
        except ReservationHold.DoesNotExist:
            raise HoldNotFound(f"Hold {authorization_id} not found")
        
        # Check idempotent replay
        if hold.status == 'released' and hold.idempotency_key == derived_key:
            return {
                'hold_id': hold.id,
                'wallet_id': hold.wallet_id,
                'amount': hold.amount,
                'status': hold.status,
                'released_at': hold.created_at,
            }
        
        # Validate state
        if hold.status == 'captured':
            raise InvalidStateTransition("Cannot release captured hold")
        
        if hold.status not in ['authorized', 'expired']:
            return {
                'hold_id': hold.id,
                'wallet_id': hold.wallet_id,
                'amount': hold.amount,
                'status': hold.status,
                'released_at': hold.created_at,
            }
        
        # Transition to released
        hold.status = 'released'
        hold.idempotency_key = derived_key
        if meta:
            hold.meta.update(meta)
        hold.save(update_fields=['status', 'idempotency_key', 'meta'])
        
        return {
            'hold_id': hold.id,
            'wallet_id': hold.wallet_id,
            'amount': hold.amount,
            'status': hold.status,
            'released_at': timezone.now(),
        }


@retry_on_serialization(max_attempts=3)
def refund(
    wallet: DeltaCrownWallet,
    capture_txn_id: int,
    amount: Decimal,
    *,
    idempotency_key: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Refund captured transaction - create compensating credit."""
    if amount <= 0:
        raise InvalidAmount(f"Refund amount must be positive, got {amount}")
    
    derived_key = _derive_idempotency_key(idempotency_key, '_refund')
    
    with transaction.atomic():
        wallet = DeltaCrownWallet.objects.select_for_update().get(id=wallet.id)
        
        # Check idempotent replay
        if derived_key:
            try:
                existing_credit = DeltaCrownTransaction.objects.get(
                    idempotency_key=derived_key,
                    wallet=wallet
                )
                return {
                    'refund_id': existing_credit.id,
                    'wallet_id': existing_credit.wallet_id,
                    'amount': existing_credit.amount,
                    'original_transaction_id': capture_txn_id,
                    'refunded_at': existing_credit.created_at,
                }
            except DeltaCrownTransaction.DoesNotExist:
                pass
        
        # Validate original transaction
        try:
            original_txn = DeltaCrownTransaction.objects.get(
                id=capture_txn_id,
                wallet=wallet
            )
        except DeltaCrownTransaction.DoesNotExist:
            raise InvalidTransaction(f"Transaction {capture_txn_id} not found")
        
        if original_txn.reason != 'SHOP_PURCHASE':
            raise InvalidTransaction(f"Transaction is not SHOP_PURCHASE")
        
        # Calculate cumulative refunds
        existing_refunds = DeltaCrownTransaction.objects.filter(
            wallet=wallet,
            reason='SHOP_REFUND',
            meta__original_transaction_id=capture_txn_id
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        refundable_amount = abs(original_txn.amount) - existing_refunds
        
        if amount > refundable_amount:
            raise InvalidAmount(
                f"Refund amount {amount} exceeds refundable {refundable_amount}"
            )
        
        # Create credit
        credit_result = credit(
            profile=wallet.profile,  # economy services expect profile, not wallet
            amount=int(amount),  # economy services use int, not Decimal
            reason='SHOP_REFUND',
            idempotency_key=derived_key,
            meta={'original_transaction_id': capture_txn_id, **(meta or {})}
        )
        
        return {
            'refund_id': credit_result['transaction_id'],
            'wallet_id': credit_result['wallet_id'],
            'amount': credit_result['amount'],
            'original_transaction_id': capture_txn_id,
            'refunded_at': timezone.now(),
        }


def get_available_balance(wallet: DeltaCrownWallet) -> int:
    """Calculate available balance = cached_balance - active holds."""
    active_holds = ReservationHold.objects.filter(
        wallet=wallet,
        status='authorized'
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    return wallet.cached_balance - active_holds
