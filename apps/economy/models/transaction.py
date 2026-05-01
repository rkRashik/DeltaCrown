# apps/economy/models/transaction.py
from __future__ import annotations

from django.conf import settings
from django.db import models

from ..exceptions import InsufficientFunds, InvalidAmount
from .wallet import DeltaCrownWallet


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
        P2P_TRANSFER = "p2p_transfer", "P2P Transfer"
        # Phase 1 Economy Cleanup: explicit types for financial flows
        TOP_UP = "top_up", "Top-Up"
        WITHDRAWAL = "withdrawal", "Withdrawal"
        # Phase 4 Escrow Engine
        ESCROW_LOCK = "escrow_lock", "Escrow Locked"
        ESCROW_REFUND = "escrow_refund", "Escrow Refunded"
        WAGER_WIN = "wager_win", "Wager Winnings"
        PLATFORM_FEE = "platform_fee", "Platform Fee"
        # Phase 5 P2P & Withdrawals
        WITHDRAWAL_REVENUE = "withdrawal_revenue", "Withdrawal Revenue (Fee)"

    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    amount = models.IntegerField(help_text="Positive for credit, negative for debit")
    cached_balance_after = models.IntegerField(
        null=True,
        blank=True,
        help_text="Wallet balance immediately after this transaction was applied. "
                  "Populated at creation time; never mutate.",
    )
    reason = models.CharField(max_length=32, choices=Reason.choices)

    # Context (optional but helps audit)
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
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["wallet", "id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(amount=0),
                name="economy_transaction_amount_nonzero"
            ),
        ]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

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
            try:
                original = DeltaCrownTransaction.objects.get(pk=self.pk)
                
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
                pass
        
        # Check balance before debit (service layer primary check, model layer backup)
        if is_create and self.amount < 0:
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
                    pass
        
        super().save(*args, **kwargs)
        
        # Maintain cached balance on create only
        if is_create:
            try:
                self.wallet.recalc_and_save()
            except Exception:
                pass
