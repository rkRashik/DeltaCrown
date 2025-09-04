from __future__ import annotations

from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DeltaCrownTransaction
from .services import award_participation_for_registration


@receiver(post_save, dispatch_uid="economy_award_on_payment_verified")
def award_on_payment_verified(sender, instance, created, **kwargs):
    """
    When PaymentVerification flips to VERIFIED, award participation coin(s).
    We resolve the PaymentVerification model dynamically so import order won't break.
    """
    PaymentVerification = apps.get_model("tournaments", "PaymentVerification")
    if sender is not PaymentVerification:
        return

    # Only award when status is VERIFIED
    if getattr(instance, "status", None) != "verified":
        return

    reg = getattr(instance, "registration", None)
    if not reg:
        return

    # get_or_create uniqueness is enforced on (registration, reason='participation')
    try:
        award_participation_for_registration(reg)
    except Exception:
        # never break the save path
        pass
