# apps/economy/escrow_service.py
"""
Escrow Service — Secure DeltaCoin locking and payout for Challenges and Bounties.

Design principles
-----------------
* All operations are atomic (SELECT FOR UPDATE + transaction.atomic).
* Every transaction is idempotency-keyed — retries are safe.
* Coins leave the user wallet immediately on lock (no intermediate escrow account).
  The escrow_locked flag on the Challenge/Bounty model tracks the locked state.
* The Master Treasury receives the platform fee on every payout.

Typical flows
-------------
Wager Challenge (two-team, symmetric):
  1. Challenger creates  → lock_funds(challenger_wallet, wager_amount_dc,
                                      reference_id="CH-VAL-ABC123_challenger")
  2. Opponent accepts    → lock_funds(challenged_wallet, wager_amount_dc,
                                      reference_id="CH-VAL-ABC123_challenged")
  3a. Match resolved     → payout_winner(winner_wallet,
                                         total_pot = wager_amount_dc * 2,
                                         platform_fee_pct = 5,
                                         reference_id="CH-VAL-ABC123")
  3b. Cancelled/expired  → refund_funds(challenger_wallet, wager_amount_dc,
                                         reference_id="CH-VAL-ABC123_challenger")
                           refund_funds(challenged_wallet, wager_amount_dc,
                                         reference_id="CH-VAL-ABC123_challenged")

Bounty (issuer locks, claimer receives):
  1. Bounty posted  → lock_funds(issuer_wallet, reward_amount_dc,
                                  reference_id="BN-VAL-X1Y2Z3_issuer")
  2. Claim verified → payout_winner(claimer_wallet, reward_amount_dc,
                                     platform_fee_pct=5,
                                     reference_id="BN-VAL-X1Y2Z3")
  3. Cancelled      → refund_funds(issuer_wallet, reward_amount_dc,
                                    reference_id="BN-VAL-X1Y2Z3_issuer")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction, IntegrityError

from .exceptions import InsufficientFunds, InvalidAmount
from .models import DeltaCrownTransaction, DeltaCrownWallet
from .services import get_master_treasury


# ---------------------------------------------------------------------------
# Risk-control constants
# ---------------------------------------------------------------------------

#: Maximum wager in DeltaCoins allowed per side for non-API (manual) games.
#: Manual games rely on screenshot evidence, which is susceptible to forgery.
#: Keeping wagers small limits the blast radius of a successful dispute scam.
NON_API_WAGER_CAP_DC: int = 1_000


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EscrowResult:
    """Immutable result object returned by every escrow operation."""
    success: bool
    operation: str                     # "lock" | "refund" | "payout"
    reference_id: str
    transactions: list = field(default_factory=list)
    error: Optional[str] = None

    def __bool__(self):
        return self.success


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_wallet_locked(wallet_id: int) -> DeltaCrownWallet:
    """Fetch wallet with SELECT FOR UPDATE inside an open atomic block."""
    return DeltaCrownWallet.objects.select_for_update().get(pk=wallet_id)


def _make_transaction(
    *,
    wallet: DeltaCrownWallet,
    amount: int,
    reason: str,
    reference_id: str,
    key_suffix: str,
    note: str,
    actor=None,
) -> DeltaCrownTransaction:
    """
    Create a single ledger row with a deterministic idempotency key.

    On duplicate key (retry scenario), returns the existing transaction silently.
    """
    idem_key = f"escrow_{key_suffix}_{reference_id}"
    balance_after = wallet.cached_balance + amount   # amount is signed

    try:
        txn = DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            reason=reason,
            note=note,
            created_by=actor,
            idempotency_key=idem_key,
            cached_balance_after=balance_after,
        )
    except IntegrityError:
        # Idempotency: duplicate key means this operation already ran — fetch it.
        txn = DeltaCrownTransaction.objects.get(idempotency_key=idem_key)

    return txn


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lock_funds(
    wallet: DeltaCrownWallet,
    amount: int,
    *,
    reference_id: str,
    actor=None,
    note: str = "",
    tournament=None,
) -> EscrowResult:
    """
    Debit `amount` DC from `wallet` and mark it as locked for escrow.

    Args:
        wallet:       The user wallet to debit.
        amount:       Positive integer DC to lock.
        reference_id: Unique challenge/bounty reference (e.g. "CH-VAL-ABC123_challenger").
        actor:        User performing the action (for audit trail).
        note:         Optional human-readable note.
        tournament:   Optional Tournament instance.  When supplied and
                      ``tournament.is_api_verified`` is ``False`` (i.e. the game
                      uses manual screenshot evidence), the wager is capped at
                      ``NON_API_WAGER_CAP_DC`` DC to prevent dispute fraud.

    Returns:
        EscrowResult with success=True and the debit transaction.

    Raises:
        InvalidAmount:     If amount <= 0.
        InsufficientFunds: If wallet balance is insufficient.
        ValidationError:   If the wager exceeds the non-API cap for manual games.
    """
    if amount <= 0:
        raise InvalidAmount(f"lock_funds: amount must be positive, got {amount}")

    # ── Dynamic Risk Control: Non-API (manual) game wager cap ─────────────────
    if tournament is not None and not getattr(tournament, 'is_api_verified', True):
        if amount > NON_API_WAGER_CAP_DC:
            raise ValidationError(
                f"Wager exceeds maximum limit for non-API games to prevent "
                f"dispute fraud. Maximum allowed: {NON_API_WAGER_CAP_DC} DC, "
                f"attempted: {amount} DC."
            )

    with db_transaction.atomic():
        w = _get_wallet_locked(wallet.pk)

        if not w.allow_overdraft and w.cached_balance < amount:
            raise InsufficientFunds(
                f"Insufficient balance to lock {amount} DC for {reference_id}. "
                f"Current balance: {w.cached_balance} DC."
            )

        # Debit the wallet
        w.cached_balance -= amount
        w.save(update_fields=["cached_balance", "updated_at"])

        txn = _make_transaction(
            wallet=w,
            amount=-amount,
            reason=DeltaCrownTransaction.Reason.ESCROW_LOCK,
            reference_id=reference_id,
            key_suffix="lock",
            note=note or f"Escrow lock for {reference_id}",
            actor=actor,
        )

    return EscrowResult(
        success=True,
        operation="lock",
        reference_id=reference_id,
        transactions=[txn],
    )


def refund_funds(
    wallet: DeltaCrownWallet,
    amount: int,
    *,
    reference_id: str,
    actor=None,
    note: str = "",
) -> EscrowResult:
    """
    Reverse a previous escrow lock by crediting `amount` DC back to `wallet`.

    Call this when a Challenge is cancelled, declined, expired, or forfeited
    before the payout stage.

    Args:
        wallet:       The user wallet to credit.
        amount:       Positive integer DC to return.
        reference_id: The same reference used in lock_funds (e.g. "CH-VAL-ABC123_challenger").
        actor:        User performing the action.
        note:         Optional human-readable note.

    Returns:
        EscrowResult with success=True and the credit transaction.
    """
    if amount <= 0:
        raise InvalidAmount(f"refund_funds: amount must be positive, got {amount}")

    with db_transaction.atomic():
        w = _get_wallet_locked(wallet.pk)

        # Credit the wallet
        w.cached_balance += amount
        w.save(update_fields=["cached_balance", "updated_at"])

        txn = _make_transaction(
            wallet=w,
            amount=+amount,
            reason=DeltaCrownTransaction.Reason.ESCROW_REFUND,
            reference_id=reference_id,
            key_suffix="refund",
            note=note or f"Escrow refund for {reference_id}",
            actor=actor,
        )

    return EscrowResult(
        success=True,
        operation="refund",
        reference_id=reference_id,
        transactions=[txn],
    )


def payout_winner(
    winner_wallet: DeltaCrownWallet,
    total_pot: int,
    *,
    platform_fee_pct: Decimal | int | float = 5,
    reference_id: str,
    actor=None,
    note: str = "",
) -> EscrowResult:
    """
    Pay out the total pot to the winner, deducting a platform fee to the Master Treasury.

    This creates TWO transactions atomically:
      1. WAGER_WIN  → winner_wallet  for (total_pot - fee)
      2. PLATFORM_FEE → Master Treasury for fee

    The pot DC was already removed from participants' wallets via lock_funds().
    This call credits the winner and the treasury to complete the circuit.

    Args:
        winner_wallet:      The wallet to receive the winnings.
        total_pot:          Total DC locked from all participants combined.
        platform_fee_pct:   Fee percentage (default 5). e.g. 5 → 5% of total_pot.
        reference_id:       Unique challenge/bounty reference (e.g. "CH-VAL-ABC123").
        actor:              User performing the action.
        note:               Optional base note (appended with "winner" / "fee" suffix).

    Returns:
        EscrowResult with success=True and both transactions.

    Raises:
        InvalidAmount: If total_pot <= 0 or fee_pct out of range.
    """
    if total_pot <= 0:
        raise InvalidAmount(f"payout_winner: total_pot must be positive, got {total_pot}")

    fee_pct = Decimal(str(platform_fee_pct))
    if not (Decimal("0") <= fee_pct <= Decimal("100")):
        raise InvalidAmount(f"payout_winner: platform_fee_pct must be 0–100, got {fee_pct}")

    # Calculate split — integer DC, floor the fee to favour the winner
    fee_dc = int(Decimal(str(total_pot)) * fee_pct / Decimal("100"))
    winner_dc = total_pot - fee_dc

    if winner_dc <= 0:
        raise InvalidAmount(
            f"payout_winner: net winner amount is zero after fee ({fee_pct}% of {total_pot} DC)."
        )

    treasury = get_master_treasury()
    base_note = note or f"Payout for {reference_id}"
    transactions = []

    with db_transaction.atomic():
        # --- 1. Credit winner ---
        w = _get_wallet_locked(winner_wallet.pk)
        w.cached_balance += winner_dc
        w.save(update_fields=["cached_balance", "updated_at"])
        winner_txn = _make_transaction(
            wallet=w,
            amount=+winner_dc,
            reason=DeltaCrownTransaction.Reason.WAGER_WIN,
            reference_id=reference_id,
            key_suffix="winner",
            note=f"{base_note} — winner receives {winner_dc} DC",
            actor=actor,
        )
        transactions.append(winner_txn)

        # --- 2. Credit treasury with platform fee (if any) ---
        if fee_dc > 0:
            t = _get_wallet_locked(treasury.pk)
            t.cached_balance += fee_dc
            t.save(update_fields=["cached_balance", "updated_at"])
            fee_txn = _make_transaction(
                wallet=t,
                amount=+fee_dc,
                reason=DeltaCrownTransaction.Reason.PLATFORM_FEE,
                reference_id=reference_id,
                key_suffix="fee",
                note=f"{base_note} — platform fee {fee_dc} DC ({fee_pct}%)",
                actor=actor,
            )
            transactions.append(fee_txn)

    return EscrowResult(
        success=True,
        operation="payout",
        reference_id=reference_id,
        transactions=transactions,
    )


# ---------------------------------------------------------------------------
# Convenience: full challenge settlement
# ---------------------------------------------------------------------------

def settle_challenge(
    *,
    winner_wallet: DeltaCrownWallet,
    loser_wallet: DeltaCrownWallet,
    wager_amount_dc: int,
    platform_fee_pct: Decimal | int | float = 5,
    reference_id: str,
    actor=None,
) -> EscrowResult:
    """
    One-call helper that settles a completed wager challenge:
      - total_pot = wager_amount_dc * 2 (both sides locked the same amount)
      - Calls payout_winner internally

    Returns:
        EscrowResult from payout_winner.
    """
    total_pot = wager_amount_dc * 2
    return payout_winner(
        winner_wallet=winner_wallet,
        total_pot=total_pot,
        platform_fee_pct=platform_fee_pct,
        reference_id=reference_id,
        actor=actor,
        note=f"Challenge settlement {reference_id}",
    )


def settle_bounty(
    *,
    claimer_wallet: DeltaCrownWallet,
    reward_amount_dc: int,
    platform_fee_pct: Decimal | int | float = 5,
    reference_id: str,
    actor=None,
) -> EscrowResult:
    """
    One-call helper that pays out a verified bounty claim:
      - Calls payout_winner with the bounty's reward_amount_dc as total_pot

    Returns:
        EscrowResult from payout_winner.
    """
    return payout_winner(
        winner_wallet=claimer_wallet,
        total_pot=reward_amount_dc,
        platform_fee_pct=platform_fee_pct,
        reference_id=reference_id,
        actor=actor,
        note=f"Bounty payout {reference_id}",
    )
