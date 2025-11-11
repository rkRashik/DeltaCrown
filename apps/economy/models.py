# apps/economy/models.py
# Implements: Documents/ExecutionPlan/MODULE_7.1_KICKOFF.md - Step 2 (Ledger Invariants)
from __future__ import annotations

from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum

from .exceptions import InsufficientFunds, InvalidAmount


class DeltaCrownWallet(models.Model):
    """
    One wallet per user profile.
    cached_balance is a derived value from the immutable transaction ledger.
    
    allow_overdraft: If True, balance can go negative. Default False (reject debits beyond balance).
    """
    profile = models.OneToOneField(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="dc_wallet",
    )
    cached_balance = models.IntegerField(default=0)
    allow_overdraft = models.BooleanField(
        default=False,
        help_text="If True, allows negative balance (overdraft). Default: False (reject insufficient funds)."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile"]),
        ]
        verbose_name = "DeltaCrown Wallet"

    def __str__(self) -> str:
        return f"Wallet<{getattr(self.profile, 'id', None)}>: {self.cached_balance}"

    @transaction.atomic
    def recalc_and_save(self) -> int:
        """
        Atomically recalculate cached_balance from ledger sum with row lock.
        
        Uses SELECT FOR UPDATE to prevent concurrent modifications.
        Returns the corrected balance.
        
        PII Discipline: Only logs wallet ID, no user data.
        """
        # Row lock: prevent concurrent updates during recalc
        locked_wallet = DeltaCrownWallet.objects.select_for_update().get(pk=self.pk)
        
        # Recompute from ledger
        total = locked_wallet.transactions.aggregate(s=Sum("amount"))["s"] or 0
        
        if locked_wallet.cached_balance != total:
            locked_wallet.cached_balance = int(total)
            locked_wallet.save(update_fields=["cached_balance", "updated_at"])
            # Refresh self to match locked_wallet state
            self.cached_balance = locked_wallet.cached_balance
        
        return self.cached_balance


class DeltaCrownTransaction(models.Model):
    """
    Immutable coin ledger line. Positive amounts = credit, negative = debit.
    NEVER mutate amount after creation; use compensating transactions.
    
    Invariants enforced:
    - Immutability: Cannot modify amount/reason after save (raises exception)
    - Amount validation: Cannot be zero (DB CHECK constraint)
    - Idempotency: Unique constraint on idempotency_key WHERE NOT NULL
    - Balance check: Service layer checks wallet balance before debit (if not overdraft)
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
        P2P_TRANSFER = "p2p_transfer", "P2P Transfer"  # For Step 3

    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    amount = models.IntegerField(help_text="Positive for credit, negative for debit")
    reason = models.CharField(max_length=32, choices=Reason.choices)

    # Context (optional but helps audit)
    # NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    # Stores legacy tournament/registration/match IDs for historical reference
    tournament_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")
    registration_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy registration ID (reference only)")
    match_id = models.IntegerField(null=True, blank=True, help_text="Legacy match ID (reference only)")

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
            models.Index(fields=["wallet"]),
            models.Index(fields=["wallet", "created_at"]),  # Fast history queries
            models.Index(fields=["wallet", "id"]),  # Pagination optimization
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(amount=0),
                name="economy_transaction_amount_nonzero"
            ),
        ]
        verbose_name = "DeltaCrown Transaction"

    def __str__(self) -> str:
        return f"Tx[{self.id}] {self.amount} for {self.get_reason_display()} (wallet={self.wallet_id})"

    def save(self, *args, **kwargs):
        """
        Save transaction with immutability enforcement.
        
        Raises:
            InvalidAmount: If amount is zero
            ValueError: If attempting to modify existing transaction
        """
        is_create = self._state.adding
        
        # Validation: amount cannot be zero
        if self.amount == 0:
            raise InvalidAmount("Transaction amount cannot be zero")
        
        # Immutability: prevent modification of existing transactions
        if not is_create:
            # Load original from DB
            try:
                original = DeltaCrownTransaction.objects.get(pk=self.pk)
                
                # Check if critical fields changed
                if original.amount != self.amount:
                    raise ValueError(
                        f"Cannot modify transaction amount after creation. "
                        f"Original: {original.amount}, Attempted: {self.amount}. "
                        f"Use compensating transaction instead."
                    )
                if original.reason != self.reason:
                    raise ValueError(
                        f"Cannot modify transaction reason after creation. "
                        f"Original: {original.reason}, Attempted: {self.reason}."
                    )
            except DeltaCrownTransaction.DoesNotExist:
                # Transaction was deleted? Unusual but allow re-creation
                pass
        
        # Check balance before debit (service layer primary check, model layer backup)
        if is_create and self.amount < 0:
            # Only check if wallet exists and has allow_overdraft set
            if self.wallet_id:
                try:
                    wallet = self.wallet if hasattr(self, 'wallet') else DeltaCrownWallet.objects.get(pk=self.wallet_id)
                    if not wallet.allow_overdraft:
                        projected_balance = wallet.cached_balance + self.amount
                        if projected_balance < 0:
                            raise InsufficientFunds(
                                f"Insufficient balance: {wallet.cached_balance} available, "
                                f"{abs(self.amount)} required (would result in {projected_balance})"
                            )
                except DeltaCrownWallet.DoesNotExist:
                    # Wallet doesn't exist yet (unusual, but allow transaction to proceed)
                    pass
        
        super().save(*args, **kwargs)
        
        # Maintain cached balance on create only
        if is_create:
            try:
                self.wallet.recalc_and_save()
            except Exception:
                # Never block writes to ledger even if recalc fails – ops can rebuild later
                pass


class CoinPolicy(models.Model):
    """
    Per-tournament coin policy. Enabled by default.
    NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    """
    tournament_id = models.IntegerField(unique=True, null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")
    enabled = models.BooleanField(default=True)

    participation = models.PositiveIntegerField(default=5)
    top4 = models.PositiveIntegerField(default=25)
    runner_up = models.PositiveIntegerField(default=50)
    winner = models.PositiveIntegerField(default=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"CoinPolicy(tournament_id={self.tournament_id})"
