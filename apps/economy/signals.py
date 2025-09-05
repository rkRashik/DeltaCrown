# apps/economy/signals.py
from __future__ import annotations

from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import award_participation_for_registration


@receiver(post_save, dispatch_uid="economy_award_on_payment_verified")
def award_on_payment_verified(sender, instance, created, **kwargs):
    """
    When PaymentVerification flips to VERIFIED, award participation coin(s).
    Resolve model dynamically so import order won't break.
    """
    PV = apps.get_model("tournaments", "PaymentVerification")
    if not PV or sender is not PV:
        return

    # Only award when status is VERIFIED
    if getattr(instance, "status", None) != "verified":
        return

    reg = getattr(instance, "registration", None)
    if not reg:
        return

    try:
        award_participation_for_registration(reg)
    except Exception:
        # never break the save path
        pass
