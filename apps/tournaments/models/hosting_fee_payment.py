"""
TournamentHostingFeePayment — audit ledger for every tournament creation fee event.

One row is written per tournament creation attempt:
  - status='waived'  → fee was 0 (promo / staff exempt / fee disabled)
  - status='paid'    → fee was deducted from the organiser's wallet
  - status='failed'  → wallet debit failed (insufficient funds or error)
  - status='refunded'→ fee was reversed by an admin

The wallet_transaction_id FK (nullable IntegerField) points to the
DeltaCrownTransaction row created by economy.services.debit().  It stays
null for waived records where no transaction occurs.

Admin actions available:
  mark_verified  — admin confirms payment was checked
  mark_disputed  — flag record for review
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class TournamentHostingFeePayment(models.Model):

    class Status(models.TextChoices):
        WAIVED   = "waived",   "Waived (free / staff exempt)"
        PAID     = "paid",     "Paid"
        FAILED   = "failed",   "Failed"
        REFUNDED = "refunded", "Refunded"
        DISPUTED = "disputed", "Disputed / Under Review"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hosting_fee_payments",
        help_text="Organiser who initiated tournament creation.",
    )
    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosting_fee_payment",
        help_text="Created tournament. Null while creation is in flight.",
    )
    amount_dc = models.PositiveIntegerField(
        default=0,
        help_text="DC charged (0 for waived).",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.WAIVED,
        db_index=True,
    )
    # Points to economy.DeltaCrownTransaction.id — stored as int to avoid
    # cross-app FK which would require a dependency on the economy app migration graph.
    wallet_transaction_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="DeltaCrownTransaction.id for this debit. Null for waived records.",
    )
    idempotency_key = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        help_text="Idempotency key used for the wallet debit transaction.",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Admin / system notes about this payment record.",
    )

    # Verification fields
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_hosting_fee_payments",
        help_text="Admin who manually verified this payment.",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tournaments"
        verbose_name = "Tournament Hosting Fee Payment"
        verbose_name_plural = "Tournament Hosting Fee Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        tournament_name = self.tournament.name if self.tournament_id else "(pending)"
        return f"{self.user} — {self.amount_dc} DC — {self.get_status_display()} — {tournament_name}"

    def mark_verified(self, by_user) -> None:
        self.verified_at = timezone.now()
        self.verified_by = by_user
        self.save(update_fields=["verified_at", "verified_by", "updated_at"])

    def mark_disputed(self, notes: str = "") -> None:
        self.status = self.Status.DISPUTED
        if notes:
            self.notes = notes
        self.save(update_fields=["status", "notes", "updated_at"])
