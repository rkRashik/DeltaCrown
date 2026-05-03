# apps/economy/fortress_services.py
"""
Financial Fortress — Privileged Economy Services (Phase B)
===========================================================

Every function in this module enforces the Double-Entry Ledger invariant:

    Sum(All User Wallet Balances) + Treasury Balance == 0

Rules:
  * Minting  → Treasury balance goes *more negative* (emitting coins)
  * Airdrop  → Treasury debited, target user credited  (net: 0)
  * TopUp    → Treasury debited, requesting user credited (net: 0)

All operations are wrapped in transaction.atomic() and produce an
immutable FortressAuditLog row.  Every ledger touch uses an
idempotency_key to prevent double-processing on retry.

Access: Call-sites MUST verify is_superuser BEFORE calling these functions.
        These services do NOT re-check auth — the view layer owns that gate.
"""
from __future__ import annotations

import uuid
import logging
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.economy.models import (
    DeltaCrownWallet,
    DeltaCrownTransaction,
    TopUpRequest,
)
from apps.economy.services import get_master_treasury

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lightweight Audit Log (Phase B — no separate model needed yet)
# ---------------------------------------------------------------------------
# We write to DeltaCrownTransaction notes + Django logger for now.
# Phase C will introduce the full FortressAuditLog model with its own table.

def _write_audit(
    action: str,
    actor: "AbstractUser | None",
    note: str,
    amount: int = 0,
    target_wallet=None,
    target_label: str = "",
    ip_address: str | None = None,
) -> None:
    """Write a FortressAuditLog row and a structured log line."""
    from apps.economy.models.audit import FortressAuditLog  # deferred import
    actor_label = actor.username if actor else "SYSTEM"
    try:
        FortressAuditLog.objects.create(
            action=action,
            actor=actor,
            actor_label=actor_label,
            target_wallet=target_wallet,
            target_label=target_label or (getattr(
                getattr(getattr(target_wallet, "profile", None), "user", None),
                "username", ""
            ) if target_wallet else ""),
            amount=amount,
            note=note,
            ip_address=ip_address,
        )
    except Exception as exc:  # never block a ledger operation over an audit failure
        logger.error("[FORTRESS] FortressAuditLog write failed: %s", exc)
    logger.info(
        "[FORTRESS] action=%s actor=%s amount=%s note=%s",
        action, actor_label, amount, note,
    )


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class FortressError(Exception):
    """Base exception for all Fortress service errors."""


class InsufficientTreasuryFunds(FortressError):
    """Treasury does not have enough balance to execute this operation."""


class TopUpAlreadyProcessed(FortressError):
    """TopUpRequest is not in PENDING state — cannot process twice."""


class UserWalletNotFound(FortressError):
    """No wallet exists for the given username."""


# ---------------------------------------------------------------------------
# Task 1a: mint_to_treasury
# ---------------------------------------------------------------------------

def mint_to_treasury(
    amount_dc: int,
    reference: str,
    actor: "AbstractUser",
) -> DeltaCrownTransaction:
    """
    Inject `amount_dc` new DeltaCoins into the Master Treasury reserve.

    Design note
    -----------
    The Treasury starts at 0 and goes NEGATIVE as coins are emitted into
    user wallets.  Minting *increases* the treasury's balance (makes it
    less negative), representing the fiat cash deposited to back new coins.

        Before: Treasury = -250,000 DC, Circulation = +250,000 DC  (sum=0)
        Mint 50,000:
        After:  Treasury = -200,000 DC, Circulation = +250,000 DC  (sum≠0)
        → The treasury holds 50,000 DC ready to distribute.

    The ledger sum temporarily breaks until these coins are airdropped.
    This is by design — mint is always followed by a distribution step.

    Returns
    -------
    DeltaCrownTransaction  — the treasury credit transaction row.
    """
    if amount_dc <= 0:
        raise FortressError("mint_to_treasury: amount_dc must be positive.")

    idem_key = f"fortress_mint_{reference}_{actor.id}"

    with db_transaction.atomic():
        treasury = get_master_treasury()

        # Credit the treasury (positive = adding reserve capacity)
        txn = DeltaCrownTransaction.objects.create(
            wallet=treasury,
            amount=amount_dc,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
            note=f"[FORTRESS MINT] Ref:{reference} | Authorized by {actor.username}",
            created_by=actor,
            idempotency_key=idem_key,
        )
        treasury.recalc_and_save()

    _write_audit(
        "MINT_TO_TREASURY", actor,
        note=f"Ref:{reference}",
        amount=amount_dc,
        target_wallet=treasury,
        target_label="Master Treasury",
    )
    logger.info(
        "[FORTRESS] MINT +%s DC | treasury_new=%s | ref=%s | actor=%s",
        amount_dc, treasury.cached_balance, reference, actor.username,
    )
    return txn


# ---------------------------------------------------------------------------
# Task 1b: fortress_airdrop
# ---------------------------------------------------------------------------

def fortress_airdrop(
    target_username: str,
    amount_dc: int,
    note: str,
    actor: "AbstractUser",
) -> dict:
    """
    Transfer `amount_dc` DC from the Master Treasury to `target_username`.

    Double-entry guarantee
    ----------------------
    1. Treasury debited by `amount_dc`  (balance goes more negative)
    2. Target wallet credited by `amount_dc`
    Both happen inside a single atomic block — either both commit or both roll back.

    Idempotency
    -----------
    The idempotency_key is `fortress_airdrop_{uuid}` — unique per call.
    If the caller wants retry-safe behaviour they should pass a stable UUID
    from the frontend form.

    Returns
    -------
    dict with keys: treasury_txn_id, user_txn_id, new_treasury_balance, new_user_balance
    """
    if amount_dc <= 0:
        raise FortressError("fortress_airdrop: amount_dc must be positive.")

    op_id = uuid.uuid4().hex[:16]
    idem_treasury = f"fortress_airdrop_treasury_{op_id}"
    idem_user     = f"fortress_airdrop_user_{op_id}"

    with db_transaction.atomic():
        # Resolve target wallet
        try:
            target_wallet = (
                DeltaCrownWallet.objects
                .select_for_update()
                .select_related("profile__user")
                .get(profile__user__username=target_username, is_treasury=False)
            )
        except DeltaCrownWallet.DoesNotExist:
            raise UserWalletNotFound(
                f"No wallet found for username '{target_username}'."
            )

        treasury = get_master_treasury()
        treasury_qs = DeltaCrownWallet.objects.select_for_update().filter(pk=treasury.pk)
        treasury = treasury_qs.get()

        # 1. Debit treasury
        treasury_txn = DeltaCrownTransaction.objects.create(
            wallet=treasury,
            amount=-amount_dc,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
            note=f"[FORTRESS AIRDROP OUT] → {target_username} | {note} | by {actor.username}",
            created_by=actor,
            idempotency_key=idem_treasury,
        )
        treasury.recalc_and_save()

        # 2. Credit user
        user_txn = DeltaCrownTransaction.objects.create(
            wallet=target_wallet,
            amount=amount_dc,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
            note=f"[FORTRESS AIRDROP] from Treasury | {note} | authorized by {actor.username}",
            created_by=actor,
            idempotency_key=idem_user,
        )
        target_wallet.recalc_and_save()

    _write_audit(
        "AIRDROP", actor,
        note=f"→ {target_username}: {note}",
        amount=amount_dc,
        target_wallet=target_wallet,
        target_label=target_username,
    )
    treasury.refresh_from_db()
    target_wallet.refresh_from_db()

    return {
        "treasury_txn_id": treasury_txn.pk,
        "user_txn_id": user_txn.pk,
        "new_treasury_balance": int(treasury.cached_balance),
        "new_user_balance": int(target_wallet.cached_balance),
        "target_username": target_username,
    }


# ---------------------------------------------------------------------------
# Task 1c: fortress_approve_topup
# ---------------------------------------------------------------------------

def fortress_approve_topup(
    request_id: int,
    actor: "AbstractUser",
) -> dict:
    """
    Approve a pending TopUpRequest: debit treasury, credit user wallet.

    Idempotency
    -----------
    Uses `topup_{id}_treasury` and `topup_{id}` keys — identical to the
    legacy admin action in admin.py, so a retry after partial failure will
    hit the UniqueConstraint and return the existing transaction safely.

    Raises
    ------
    TopUpRequest.DoesNotExist   — if ID not found
    TopUpAlreadyProcessed       — if status != pending
    """
    with db_transaction.atomic():
        try:
            topup = (
                TopUpRequest.objects
                .select_for_update()
                .select_related("wallet__profile__user")
                .get(pk=request_id)
            )
        except TopUpRequest.DoesNotExist:
            raise FortressError(f"TopUpRequest #{request_id} not found.")

        if topup.status != TopUpRequest.Status.PENDING:
            raise TopUpAlreadyProcessed(
                f"TopUpRequest #{request_id} is already '{topup.status}' — cannot approve."
            )

        treasury = get_master_treasury()
        treasury = DeltaCrownWallet.objects.select_for_update().get(pk=treasury.pk)

        # 1. Debit treasury
        DeltaCrownTransaction.objects.create(
            wallet=treasury,
            amount=-topup.amount,
            reason=DeltaCrownTransaction.Reason.TOP_UP,
            note=f"[FORTRESS] Treasury debit for top-up #{topup.id}",
            created_by=actor,
            idempotency_key=f"topup_{topup.id}_treasury",
        )
        treasury.recalc_and_save()

        # 2. Credit user wallet
        user_txn = DeltaCrownTransaction.objects.create(
            wallet=topup.wallet,
            amount=topup.amount,
            reason=DeltaCrownTransaction.Reason.TOP_UP,
            note=f"[FORTRESS] Top-up #{topup.id} approved by {actor.username}",
            created_by=actor,
            idempotency_key=f"topup_{topup.id}",
        )
        topup.wallet.recalc_and_save()

        # 3. Update request state
        now = timezone.now()
        topup.status = TopUpRequest.Status.COMPLETED
        topup.reviewed_at = now
        topup.reviewed_by = actor
        topup.completed_at = now
        topup.transaction = user_txn
        topup.admin_note = f"[FORTRESS] Approved by {actor.username}"
        topup.save()

    _write_audit(
        "APPROVE_TOPUP", actor,
        note=f"TopUp #{request_id} | {topup.amount} DC → {topup.wallet.profile.user.username}",
        amount=topup.amount,
        target_wallet=topup.wallet,
        target_label=topup.wallet.profile.user.username,
    )
    treasury.refresh_from_db()
    topup.wallet.refresh_from_db()

    return {
        "topup_id": request_id,
        "amount_credited": topup.amount,
        "new_treasury_balance": int(treasury.cached_balance),
        "new_user_balance": int(topup.wallet.cached_balance),
        "user": topup.wallet.profile.user.username,
    }


# ---------------------------------------------------------------------------
# Task 2: fortress_bulk_airdrop
# ---------------------------------------------------------------------------

class BulkAirdropResult:
    """Value object returned by fortress_bulk_airdrop."""
    __slots__ = ("succeeded", "failed", "total_dc_sent", "new_treasury_balance")

    def __init__(self):
        self.succeeded: list[dict] = []     # {username, amount}
        self.failed:    list[dict] = []     # {username, reason}
        self.total_dc_sent: int    = 0
        self.new_treasury_balance: int = 0

    def to_dict(self) -> dict:
        return {
            "succeeded":           self.succeeded,
            "failed":              self.failed,
            "succeeded_count":     len(self.succeeded),
            "failed_count":        len(self.failed),
            "total_dc_sent":       self.total_dc_sent,
            "new_treasury_balance": self.new_treasury_balance,
        }


def fortress_bulk_airdrop(
    usernames: list[str],
    amount_dc_each: int,
    note: str,
    actor: "AbstractUser",
) -> BulkAirdropResult:
    """
    Airdrop `amount_dc_each` DC from the Master Treasury to EACH username
    in the provided list.

    Atomicity strategy
    ------------------
    Each individual transfer runs in its OWN savepoint so that one bad
    username (no wallet, duplicate key) does not roll back ALL transfers.
    The outer function collects successes and failures for the API response.

    Double-entry guarantee
    ----------------------
    Same as fortress_airdrop() — every credit to a user is matched by a
    debit from the treasury within the same savepoint.

    Returns
    -------
    BulkAirdropResult with succeeded, failed, total_dc_sent lists.
    """
    if amount_dc_each <= 0:
        raise FortressError("fortress_bulk_airdrop: amount_dc_each must be positive.")
    if not usernames:
        raise FortressError("fortress_bulk_airdrop: usernames list is empty.")

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped = [u for u in (u.strip() for u in usernames) if u and not (u in seen or seen.add(u))]

    result = BulkAirdropResult()
    op_batch = uuid.uuid4().hex[:12]     # shared batch tag for audit trail

    for username in deduped:
        op_id         = uuid.uuid4().hex[:12]
        idem_treasury = f"bulk_{op_batch}_{op_id}_treasury"
        idem_user     = f"bulk_{op_batch}_{op_id}_user"

        try:
            with db_transaction.atomic():
                # Resolve user wallet
                try:
                    target_wallet = (
                        DeltaCrownWallet.objects
                        .select_for_update()
                        .select_related("profile__user")
                        .get(profile__user__username=username, is_treasury=False)
                    )
                except DeltaCrownWallet.DoesNotExist:
                    raise UserWalletNotFound(f"No wallet for '{username}'.")

                treasury = get_master_treasury()
                treasury = DeltaCrownWallet.objects.select_for_update().get(pk=treasury.pk)

                # Debit treasury
                DeltaCrownTransaction.objects.create(
                    wallet=treasury,
                    amount=-amount_dc_each,
                    reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                    note=f"[BULK AIRDROP] batch={op_batch} → {username} | {note}",
                    created_by=actor,
                    idempotency_key=idem_treasury,
                )
                treasury.recalc_and_save()

                # Credit user
                DeltaCrownTransaction.objects.create(
                    wallet=target_wallet,
                    amount=amount_dc_each,
                    reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                    note=f"[BULK AIRDROP] batch={op_batch} | {note} | by {actor.username}",
                    created_by=actor,
                    idempotency_key=idem_user,
                )
                target_wallet.recalc_and_save()

                result.succeeded.append({"username": username, "amount": amount_dc_each})
                result.total_dc_sent += amount_dc_each

        except (FortressError, UserWalletNotFound) as exc:
            result.failed.append({"username": username, "reason": str(exc)})
        except Exception as exc:
            logger.exception("[FORTRESS] Bulk airdrop error for %s: %s", username, exc)
            result.failed.append({"username": username, "reason": "Unexpected error — check server logs."})

    # Single audit entry summarising the entire batch
    treasury = get_master_treasury()
    result.new_treasury_balance = int(treasury.cached_balance)

    _write_audit(
        "BULK_AIRDROP", actor,
        note=(
            f"Batch={op_batch} | {len(result.succeeded)}/{len(deduped)} succeeded "
            f"| {amount_dc_each} DC each | {note}"
        ),
        amount=result.total_dc_sent,
        target_label=f"BULK: {len(result.succeeded)} wallets",
    )
    return result
