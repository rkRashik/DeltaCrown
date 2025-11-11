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
from apps.economy.exceptions import IdempotencyConflict as EconomyIdempotencyConflict
from .exceptions import InsufficientFunds

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
    amount: int,
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
                # Check if parameters match - detect idempotency conflicts
                if existing_hold.sku != sku or existing_hold.amount != amount:
                    raise IdempotencyConflict(
                        f"Idempotency key '{derived_key}' already used for different parameters "
                        f"(existing: {existing_hold.sku}/{existing_hold.amount}, "
                        f"requested: {sku}/{amount})"
                    )
                # Parameters match - return existing hold
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
        if hold.expires_at and timezone.now() >= hold.expires_at:
            hold.status = 'expired'
            hold.save(update_fields=['status'])
            raise HoldExpired(f"Hold {authorization_id} expired")
        
        # Create debit - use ENTRY_FEE_DEBIT reason (closest match to shop purchase)
        debit_key = _derive_idempotency_key(idempotency_key, '_capture_debit')
        note_text = f"Shop purchase: {hold.sku}"
        if meta and meta.get('note'):
            note_text += f" - {meta['note']}"
        
        try:
            debit_result = debit(
                profile=wallet.profile,  # economy services expect profile, not wallet
                amount=int(hold.amount),  # economy services use int, not Decimal
                reason='ENTRY_FEE_DEBIT',
                idempotency_key=debit_key,
                meta={'note': note_text}
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
        
        # Refresh wallet to get updated cached_balance after debit
        wallet.refresh_from_db()
        
        return {
            'hold_id': hold.id,
            'wallet_id': hold.wallet_id,
            'amount': int(hold.amount),
            'status': hold.status,
            'transaction_id': hold.captured_txn_id,
            'captured_at': timezone.now(),
            'balance_after': wallet.cached_balance,
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
            # Return the original released_at timestamp from meta
            released_at_str = hold.meta.get('released_at')
            released_at = timezone.datetime.fromisoformat(released_at_str) if released_at_str else hold.created_at
            return {
                'hold_id': hold.id,
                'wallet_id': hold.wallet_id,
                'amount': int(hold.amount),
                'status': hold.status,
                'released_at': released_at,
            }
        
        # Validate state
        if hold.status == 'captured':
            raise InvalidStateTransition("Cannot release captured hold")
        
        if hold.status not in ['authorized', 'expired']:
            return {
                'hold_id': hold.id,
                'wallet_id': hold.wallet_id,
                'amount': int(hold.amount),
                'status': hold.status,
                'released_at': hold.created_at,
            }
        
        # Transition to released
        released_at = timezone.now()
        hold.status = 'released'
        hold.idempotency_key = derived_key
        # Store released_at in meta for idempotency replay
        hold.meta['released_at'] = released_at.isoformat()
        if meta:
            hold.meta.update(meta)
        hold.save(update_fields=['status', 'idempotency_key', 'meta'])
        
        return {
            'hold_id': hold.id,
            'wallet_id': hold.wallet_id,
            'amount': int(hold.amount),
            'status': hold.status,
            'released_at': released_at,
        }


@retry_on_serialization(max_attempts=3)
def refund(
    wallet: DeltaCrownWallet,
    capture_txn_id: int,
    amount: int,
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
                # Credits have positive amount, so use amount directly
                return {
                    'refund_transaction_id': existing_credit.id,
                    'wallet_id': existing_credit.wallet_id,
                    'amount': existing_credit.amount,  # Already positive
                    'original_transaction_id': capture_txn_id,
                    'refunded_at': existing_credit.created_at,
                    'balance_after': wallet.cached_balance,
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
        
        # Debit transactions have negative amounts, so ENTRY_FEE_DEBIT is our shop purchase
        if original_txn.reason != 'ENTRY_FEE_DEBIT':
            raise InvalidTransaction(f"Transaction is not a shop purchase (entry fee debit)")
        
        # Calculate cumulative refunds
        # Since we can't easily store/query the original txn ID in the transaction note,
        # we'll track refunds via a separate meta field in ReservationHold
        # For now, query all refunds and store refund tracking in hold meta
        from .models import ReservationHold
        try:
            hold = ReservationHold.objects.get(captured_txn_id=capture_txn_id, wallet=wallet)
            refunded_so_far = hold.meta.get('total_refunded', 0)
        except ReservationHold.DoesNotExist:
            # No hold found - this shouldn't happen but allow it
            refunded_so_far = 0
        
        existing_refunds = refunded_so_far
        
        refundable_amount = abs(original_txn.amount) - existing_refunds
        
        if amount > refundable_amount:
            raise InvalidAmount(
                f"Refund amount {amount} exceeds refundable {refundable_amount}"
            )
        
        # Create credit - use REFUND reason with note indicating original transaction
        note_text = f"Refund for txn {capture_txn_id}"
        if meta and meta.get('note'):
            note_text += f" - {meta['note']}"
        
        # Pass note via meta - credit() will forward to _create_transaction as **kwargs
        credit_result = credit(
            profile=wallet.profile,  # economy services expect profile, not wallet
            amount=int(amount),  # economy services use int, not Decimal
            reason='REFUND',
            idempotency_key=derived_key,
            meta={'note': note_text}  # note will be passed to DeltaCrownTransaction.objects.create()
        )
        
        # Update hold meta with cumulative refunds
        if hold:
            hold.meta['total_refunded'] = existing_refunds + amount
            hold.save(update_fields=['meta'])
        
        # credit_result contains: wallet_id, balance_after, transaction_id, idempotency_key
        return {
            'refund_transaction_id': credit_result['transaction_id'],
            'wallet_id': credit_result['wallet_id'],
            'amount': int(amount),  # Use the amount parameter, not from credit_result
            'original_transaction_id': capture_txn_id,
            'refunded_at': timezone.now(),
            'balance_after': credit_result['balance_after'],
        }


def get_available_balance(wallet: DeltaCrownWallet) -> int:
    """Calculate available balance = cached_balance - active holds."""
    active_holds = ReservationHold.objects.filter(
        wallet=wallet,
        status='authorized'
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    return wallet.cached_balance - active_holds
