"""
Reusable signal utilities for tracking field changes across pre_save / post_save.

Usage:
    from apps.common.signals import make_status_tracker

    track_payment_status = make_status_tracker('status', '_original_status')

    pre_save.connect(track_payment_status, sender=PaymentVerification)
"""

from __future__ import annotations

from django.db.models.signals import pre_save


def make_status_tracker(field_name: str, attr_name: str):
    """
    Return a pre_save handler that snapshots *field_name* onto *attr_name*.

    The snapshot is read from the database so the post_save handler can
    compare ``instance.<attr_name>`` with the current value to detect
    transitions.
    """

    def _track(sender, instance, **kwargs):
        if instance.pk:
            try:
                old = sender.objects.get(pk=instance.pk)
                setattr(instance, attr_name, getattr(old, field_name))
            except sender.DoesNotExist:
                setattr(instance, attr_name, None)
        else:
            setattr(instance, attr_name, None)

    _track.__qualname__ = f"track_{field_name}_change"
    _track.__doc__ = (
        f"Pre-save snapshot of '{field_name}' → instance.{attr_name}"
    )
    return _track
