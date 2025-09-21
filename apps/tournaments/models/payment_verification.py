# apps/tournaments/models/payment_verification.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PaymentVerification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        VERIFIED = "verified", _("Verified")
        REJECTED = "rejected", _("Rejected")

    class Method(models.TextChoices):
        BKASH = "bkash", "bKash"
        NAGAD = "nagad", "Nagad"
        ROCKET = "rocket", "Rocket"
        BANK = "bank", "Bank Transfer"
        OTHER = "other", "Other"

    # Exactly one verification row per registration
    registration = models.OneToOneField(
        "tournaments.Registration",
        on_delete=models.CASCADE,
        related_name="payment_verification",
    )

    method = models.CharField(max_length=16, choices=Method.choices, default=Method.BKASH)

    # What the registrant submits
    payer_account_number = models.CharField(
        max_length=32,
        blank=True,
        help_text="Your bKash/Nagad/Rocket account number (payer)",
    )
    transaction_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Transaction ID from bKash/Nagad/Rocket",
    )
    
    # Reference number for internal tracking (optional for backward compatibility)
    reference_number = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Internal reference number for payment tracking",
    )

    amount_bdt = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    # Optional proof image (screenshot / receipt)
    proof_image = models.ImageField(upload_to="payments/proofs/", null=True, blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(blank=True)
    # Audit trail for last action taken (approve/deny)
    last_action_reason = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---- helpers ----
    def mark_verified(self, user, reason: str = ""):
        self.status = self.Status.VERIFIED
        self.verified_by = user
        self.verified_at = timezone.now()
        self.reject_reason = ""
        if hasattr(self, "last_action_reason"):
            self.last_action_reason = reason or "Manual verify via admin"
        self.save(update_fields=["status", "verified_by", "verified_at", "reject_reason", "last_action_reason", "updated_at"]) if hasattr(self, "last_action_reason") else self.save(update_fields=["status", "verified_by", "verified_at", "reject_reason", "updated_at"])

    def mark_rejected(self, user, reason: str = ""):
        self.status = self.Status.REJECTED
        self.verified_by = user
        self.verified_at = timezone.now()
        self.reject_reason = reason or "Rejected by staff"
        if hasattr(self, "last_action_reason"):
            self.last_action_reason = reason or "Manual reject via admin"
        self.save(update_fields=["status", "verified_by", "verified_at", "reject_reason", "last_action_reason", "updated_at"]) if hasattr(self, "last_action_reason") else self.save(update_fields=["status", "verified_by", "verified_at", "reject_reason", "updated_at"])

    def __str__(self):
        rid = getattr(self.registration, "id", None)
        return f"PaymentVerification(reg={rid}, status={self.status})"
