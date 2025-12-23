# apps/economy/signals.py
from __future__ import annotations

from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import award_participation_for_registration


# NOTE: Signal disabled - tournament app moved to legacy (Nov 2, 2025)
# @receiver(post_save, dispatch_uid="economy_award_on_payment_verified")
def award_on_payment_verified_DISABLED(sender, instance, created, **kwargs):
    """
    DISABLED: When PaymentVerification flips to VERIFIED, award participation coin(s).
    Resolve model dynamically so import order won't break.
    """
    pass
    # PV = apps.get_model("tournaments", "PaymentVerification")
    # if not PV or sender is not PV:
    #     return

    # # Only award when status is VERIFIED
    # if getattr(instance, "status", None) != "verified":
    #     return

    # reg = getattr(instance, "registration", None)
    # if not reg:
    #     return

    # try:
    #     award_participation_for_registration(reg)
    # except Exception:
    #     # never break the save path
    #     pass


# ============================================================================
# UP-M3: Economy Sync Signals
# ============================================================================

@receiver(post_save, sender='economy.DeltaCrownTransaction', dispatch_uid='up_m3_sync_profile_on_transaction')
def sync_profile_on_transaction(sender, instance, created, **kwargs):
    """
    UP-M3: Sync wallet balance → profile fields when transaction is created.
    
    Updates:
    - profile.deltacoin_balance = wallet.cached_balance
    - profile.lifetime_earnings = sum(positive transactions)
    - wallet.lifetime_earnings = sum(positive transactions)
    
    Idempotent: Safe to call multiple times (checks if update needed).
    Never raises: Catches all exceptions to avoid blocking transaction save.
    """
    if not created:
        return  # Only sync on new transactions
    
    try:
        from apps.user_profile.services.economy_sync import sync_wallet_to_profile
        
        wallet_id = instance.wallet_id
        if wallet_id:
            sync_wallet_to_profile(wallet_id)
    except Exception:
        # Never block transaction creation
        # Reconciliation command can fix any missed syncs
        pass
