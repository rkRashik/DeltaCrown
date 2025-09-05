# apps/economy/models.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class DeltaCrownWallet(models.Model):
    """
    One wallet per user profile.
    cached_balance is a derived value from the immutable transaction ledger.
    """
    profile = models.OneToOneField(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="dc_wallet",
    )
    cached_balance = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile"]),
        ]
        verbose_name = "DeltaCrown Wallet"

    def __str__(self) -> str:
        return f"Wallet<{getattr(self.profile, 'id', None)}>: {self.cached_balance}"

    def recalc_and_save(self) -> int:
        total = self.transactions.aggregate(s=Sum("amount"))["s"] or 0
        if self.cached_balance != total:
            self.cached_balance = int(total)
            self.save(update_fields=["cached_balance", "updated_at"])
        return self.cached_balance


class DeltaCrownTransaction(models.Model):
    """
    Immutable coin ledger line. Positive amounts = credit, negative = debit.
    NEVER mutate amount after creation; use compensating transactions.
    """
    class Reason(models.TextChoices):
        PARTICIPATION = "participation", "Participation"
        TOP4 = "top4", "Top 4"
        RUNNER_UP = "runner_up", "Runner-up"
        WINNER = "winner", "Winner"
        ENTRY_FEE_DEBIT = "entry_fee_debit", "Entry fee (debit)"
        REFUND = "refund", "Refund"
        MANUAL_ADJUST = "manual_adjust", "Manual adjust"
        CORRECTION = "correction", "Correction"

    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    amount = models.IntegerField(help_text="Positive for credit, negative for debit")
    reason = models.CharField(max_length=32, choices=Reason.choices)

    # Context (optional but helps audit)
    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.PROTECT, null=True, blank=True, related_name="coin_transactions"
    )
    registration = models.ForeignKey(
        "tournaments.Registration", on_delete=models.PROTECT, null=True, blank=True, related_name="coin_transactions"
    )
    match = models.ForeignKey(
        "tournaments.Match", on_delete=models.PROTECT, null=True, blank=True, related_name="coin_transactions"
    )

    note = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="coin_transactions_created"
    )

    # Idempotency guard: unique across the whole table (nullable). Services must set this.
    idempotency_key = models.CharField(max_length=64, blank=True, null=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")
        indexes = [
            models.Index(fields=["reason", "created_at"]),
            models.Index(fields=["tournament", "created_at"]),
            models.Index(fields=["registration"]),
            models.Index(fields=["wallet"]),
        ]
        verbose_name = "DeltaCrown Transaction"

    def __str__(self) -> str:
        return f"Tx[{self.id}] {self.amount} for {self.get_reason_display()} (wallet={self.wallet_id})"

    def save(self, *args, **kwargs):
        is_create = self._state.adding
        super().save(*args, **kwargs)
        # maintain cached balance on create only
        if is_create:
            try:
                self.wallet.recalc_and_save()
            except Exception:
                # never block writes to ledger even if recalc fails – ops can rebuild later
                pass


class CoinPolicy(models.Model):
    """
    Per-tournament coin policy. Enabled by default.
    """
    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="coin_policy",
    )
    enabled = models.BooleanField(default=True)

    participation = models.PositiveIntegerField(default=5)
    top4 = models.PositiveIntegerField(default=25)
    runner_up = models.PositiveIntegerField(default=50)
    winner = models.PositiveIntegerField(default=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"CoinPolicy({getattr(self.tournament, 'name', self.tournament_id)})"
