# apps/user_profile/services/economy_sync.py
"""
Economy Sync Service (UP-M3)

Synchronizes wallet balance → profile caches:
- profile.deltacoin_balance = wallet.cached_balance
- profile.lifetime_earnings = sum(positive transactions)
- wallet.lifetime_earnings = sum(positive transactions)

Called by:
- economy signals (post_save DeltaCrownTransaction)
- reconcile_economy management command
- stats update workflows

Concurrency Strategy:
- Uses select_for_update() to lock profile row
- Uses F() expressions for atomic updates where possible
- Idempotent: safe to call multiple times

Related: apps/user_profile/signals/activity_signals.py (creates UserActivity events)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Sum, Q
from django.apps import apps


def sync_wallet_to_profile(wallet_id: int) -> dict:
    """
    Sync wallet cached_balance → profile.deltacoin_balance.
    Also updates wallet.lifetime_earnings and profile.lifetime_earnings from ledger.
    
    Args:
        wallet_id: DeltaCrownWallet primary key
    
    Returns:
        dict with keys: profile_id, balance_synced, earnings_synced, balance_before, balance_after
    
    Concurrency: Uses select_for_update on both wallet and profile
    """
    DeltaCrownWallet = apps.get_model('economy', 'DeltaCrownWallet')
    DeltaCrownTransaction = apps.get_model('economy', 'DeltaCrownTransaction')
    UserProfile = apps.get_model('user_profile', 'UserProfile')
    
    with transaction.atomic():
        # Lock wallet and profile rows
        wallet = DeltaCrownWallet.objects.select_for_update().select_related('profile').get(pk=wallet_id)
        profile = UserProfile.objects.select_for_update().get(pk=wallet.profile_id)
        
        # Store before state
        balance_before = float(profile.deltacoin_balance)
        earnings_before = float(profile.lifetime_earnings)
        
        # Sync current balance (int → decimal conversion)
        new_balance = Decimal(str(wallet.cached_balance))
        balance_changed = (profile.deltacoin_balance != new_balance)
        
        # Calculate lifetime earnings from ledger (sum of positive transactions)
        earnings_sum = DeltaCrownTransaction.objects.filter(
            wallet=wallet,
            amount__gt=0
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        new_earnings = Decimal(str(earnings_sum))
        earnings_changed = (profile.lifetime_earnings != new_earnings)
        
        # Update profile fields
        if balance_changed:
            profile.deltacoin_balance = new_balance
        if earnings_changed:
            profile.lifetime_earnings = new_earnings
        
        # Update wallet.lifetime_earnings (was never set before)
        wallet_earnings_changed = (wallet.lifetime_earnings != earnings_sum)
        if wallet_earnings_changed:
            wallet.lifetime_earnings = earnings_sum
            wallet.save(update_fields=['lifetime_earnings', 'updated_at'])
        
        # Save profile (only if changed)
        if balance_changed or earnings_changed:
            update_fields = []
            if balance_changed:
                update_fields.append('deltacoin_balance')
            if earnings_changed:
                update_fields.append('lifetime_earnings')
            update_fields.append('updated_at')
            profile.save(update_fields=update_fields)
        
        return {
            'profile_id': profile.id,
            'balance_synced': balance_changed,
            'earnings_synced': earnings_changed,
            'balance_before': balance_before,
            'balance_after': float(profile.deltacoin_balance),
            'earnings_before': earnings_before,
            'earnings_after': float(profile.lifetime_earnings),
        }


def sync_profile_by_user_id(user_id: int) -> Optional[dict]:
    """
    Sync profile economy fields for a given user ID.
    Convenience wrapper for sync_wallet_to_profile.
    
    Args:
        user_id: User primary key
    
    Returns:
        Sync result dict, or None if wallet doesn't exist
    """
    DeltaCrownWallet = apps.get_model('economy', 'DeltaCrownWallet')
    UserProfile = apps.get_model('user_profile', 'UserProfile')
    
    try:
        profile = UserProfile.objects.get(user_id=user_id)
        wallet = DeltaCrownWallet.objects.get(profile=profile)
        return sync_wallet_to_profile(wallet.id)
    except (UserProfile.DoesNotExist, DeltaCrownWallet.DoesNotExist):
        return None


def get_balance_drift(wallet_id: int) -> dict:
    """
    Check if profile.deltacoin_balance matches wallet.cached_balance (drift detection).
    Does NOT modify data (read-only).
    
    Args:
        wallet_id: DeltaCrownWallet primary key
    
    Returns:
        dict with keys: has_drift, wallet_balance, profile_balance, diff
    """
    DeltaCrownWallet = apps.get_model('economy', 'DeltaCrownWallet')
    
    wallet = DeltaCrownWallet.objects.select_related('profile').get(pk=wallet_id)
    profile = wallet.profile
    
    wallet_balance = wallet.cached_balance
    profile_balance = float(profile.deltacoin_balance)
    
    diff = wallet_balance - profile_balance
    has_drift = (abs(diff) > 0.01)  # Allow 0.01 epsilon for decimal rounding
    
    return {
        'has_drift': has_drift,
        'wallet_balance': wallet_balance,
        'profile_balance': profile_balance,
        'diff': diff,
    }


def recompute_lifetime_earnings(wallet_id: int) -> int:
    """
    Recompute wallet.lifetime_earnings and profile.lifetime_earnings from ledger.
    
    Args:
        wallet_id: DeltaCrownWallet primary key
    
    Returns:
        int: Total lifetime earnings (sum of positive transactions)
    """
    DeltaCrownWallet = apps.get_model('economy', 'DeltaCrownWallet')
    DeltaCrownTransaction = apps.get_model('economy', 'DeltaCrownTransaction')
    UserProfile = apps.get_model('user_profile', 'UserProfile')
    
    with transaction.atomic():
        wallet = DeltaCrownWallet.objects.select_for_update().select_related('profile').get(pk=wallet_id)
        profile = UserProfile.objects.select_for_update().get(pk=wallet.profile_id)
        
        # Sum all credit transactions
        earnings_sum = DeltaCrownTransaction.objects.filter(
            wallet=wallet,
            amount__gt=0
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Update both wallet and profile
        wallet.lifetime_earnings = earnings_sum
        wallet.save(update_fields=['lifetime_earnings', 'updated_at'])
        
        profile.lifetime_earnings = Decimal(str(earnings_sum))
        profile.save(update_fields=['lifetime_earnings', 'updated_at'])
        
        return earnings_sum
