# apps/economy/models.py
from __future__ import annotations

from django.db import models
from django.utils import timezone


class DeltaCrownWallet(models.Model):
    profile = models.OneToOneField(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="dc_wallet",
    )
    cached_balance = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def recalc_and_save(self):
        total = self.transactions.aggregate(s=models.Sum("amount")).get("s") or 0
        if total != self.cached_balance:
            self.cached_balance = total
            self.save(update_fields=["cached_balance", "updated_at"])
        return total

    @property
    def balance(self) -> int:
        return self.cached_balance

    def __str__(self):
        u = getattr(self.profile, "user", None)
        return f"Wallet({getattr(u, 'username', self.profile_id)})"


class DeltaCrownTransaction(models.Model):
    class Reason(models.TextChoices):
        PARTICIPATION = "participation", "Participation"
        TOP4 = "top4", "Top 4"
        RUNNER_UP = "runner_up", "Runner-up"
        WINNER = "winner", "Winner"
        BONUS = "bonus", "Bonus"
        ADJUSTMENT = "adjustment", "Adjustment"

    wallet = models.ForeignKey(
        DeltaCrownWallet, on_delete=models.CASCADE, related_name="transactions"
    )
    amount = models.IntegerField()  # positive or negative
    reason = models.CharField(max_length=32, choices=Reason.choices)
    note = models.CharField(max_length=255, blank=True)

    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.SET_NULL, null=True, blank=True, related_name="coin_transactions"
    )
    registration = models.ForeignKey(
        "tournaments.Registration", on_delete=models.SET_NULL, null=True, blank=True, related_name="coin_transactions"
    )
    match = models.ForeignKey(
        "tournaments.Match", on_delete=models.SET_NULL, null=True, blank=True, related_name="coin_transactions"
    )
    metadata = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["reason", "created_at"]),
            models.Index(fields=["tournament", "created_at"]),
        ]
        constraints = [
            # Allow multiple participation awards per registration but only one per (registration, wallet)
            models.UniqueConstraint(
                fields=["registration", "wallet", "reason"],
                condition=models.Q(reason="participation"),
                name="uq_participation_once_per_registration_wallet",
            )
        ]
        ordering = ("-created_at", "id")

    def __str__(self):
        return f"{self.amount} for {self.get_reason_display()}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating:
            self.wallet.cached_balance = (self.wallet.cached_balance or 0) + int(self.amount)
            self.wallet.save(update_fields=["cached_balance", "updated_at"])


class CoinPolicy(models.Model):
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
