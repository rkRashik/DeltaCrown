# apps/economy/reward_services.py
"""
Economy Reward Services — Automation Hooks (Phase C)
=====================================================

These functions implement the "scam-free" automation rules shown in the
Fortress → Reward Automation tab. Each function:

  1. Checks a once-per-lifetime idempotency key (DeltaCrownTransaction
     idempotency_key) so the bonus is truly atomic and un-replayable.
  2. Wraps in transaction.atomic() for ledger safety.
  3. Writes a FortressAuditLog entry with action=AUTO_REWARD_*.

Call-sites
----------
  * award_kyc_bonus    → KYC app's on_kyc_approved signal/hook
  * award_first_match_bonus → Match completion signal/hook

Do NOT call these functions from the Fortress SPA directly — they are
triggered automatically by domain events.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction as db_transaction

from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.economy.services import get_master_treasury

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()
logger = logging.getLogger(__name__)

# ── Reward amounts (DC) ────────────────────────────────────────────────────
KYC_BONUS_DC         = 500
FIRST_MATCH_BONUS_DC = 150


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_error_wallet(user: "AbstractUser") -> DeltaCrownWallet:
    """Fetch the user's wallet or raise ValueError if it doesn't exist."""
    try:
        return DeltaCrownWallet.objects.select_for_update().get(
            profile__user=user,
            is_treasury=False,
        )
    except DeltaCrownWallet.DoesNotExist:
        raise ValueError(f"No wallet found for user '{user.username}'.")


def _write_audit(action: str, actor_label: str, target_wallet, amount: int, note: str):
    """Deferred import to avoid circular dependency at module load time."""
    from apps.economy.models.audit import FortressAuditLog
    FortressAuditLog.objects.create(
        action=action,
        actor=None,                    # System-triggered — no human actor
        actor_label=actor_label,
        target_wallet=target_wallet,
        target_label=getattr(
            getattr(getattr(target_wallet, "profile", None), "user", None), "username", "—"
        ),
        amount=amount,
        note=note,
    )


# ---------------------------------------------------------------------------
# Task 3a: award_kyc_bonus
# ---------------------------------------------------------------------------

def award_kyc_bonus(user: "AbstractUser") -> DeltaCrownTransaction | None:
    """
    Award KYC_BONUS_DC (500 DC) once per lifetime upon identity verification.

    Idempotency
    -----------
    The idempotency_key `auto_kyc_bonus_{user_id}` is unique per user.
    If the bonus was already given, IntegrityError is caught and the
    function returns None silently — safe to call multiple times.

    Returns
    -------
    DeltaCrownTransaction on first-time award, or None if already awarded.
    """
    idem_key = f"auto_kyc_bonus_{user.pk}"

    try:
        with db_transaction.atomic():
            user_wallet = _get_or_error_wallet(user)
            treasury    = get_master_treasury()
            treasury_wallet = DeltaCrownWallet.objects.select_for_update().get(pk=treasury.pk)

            # 1. Debit treasury
            DeltaCrownTransaction.objects.create(
                wallet=treasury_wallet,
                amount=-KYC_BONUS_DC,
                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                note=f"[AUTO] KYC bonus treasury debit → {user.username}",
                idempotency_key=f"{idem_key}_treasury",
            )
            treasury_wallet.recalc_and_save()

            # 2. Credit user (idempotency guard)
            txn = DeltaCrownTransaction.objects.create(
                wallet=user_wallet,
                amount=KYC_BONUS_DC,
                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                note=f"[AUTO] KYC Identity Verified bonus (+{KYC_BONUS_DC} DC)",
                idempotency_key=idem_key,
            )
            user_wallet.recalc_and_save()

            # 3. Audit log
            _write_audit(
                action="AUTO_REWARD_KYC",
                actor_label="SYSTEM_KYC",
                target_wallet=user_wallet,
                amount=KYC_BONUS_DC,
                note=f"KYC bonus awarded to {user.username}",
            )

    except IntegrityError:
        # Idempotency key collision → bonus already awarded
        logger.info(
            "[RewardService] KYC bonus already awarded for user=%s — skipping.",
            user.username,
        )
        return None

    logger.info(
        "[RewardService] AUTO_REWARD_KYC: +%s DC awarded to %s",
        KYC_BONUS_DC, user.username,
    )
    return txn


# ---------------------------------------------------------------------------
# Task 3b: award_first_match_bonus
# ---------------------------------------------------------------------------

def award_first_match_bonus(user: "AbstractUser") -> DeltaCrownTransaction | None:
    """
    Award FIRST_MATCH_BONUS_DC (150 DC) once per lifetime upon first
    verified match completion.

    Idempotency
    -----------
    Key: `auto_first_match_{user_id}` — unique constraint prevents re-award.

    Returns
    -------
    DeltaCrownTransaction on first-time award, or None if already awarded.
    """
    idem_key = f"auto_first_match_{user.pk}"

    try:
        with db_transaction.atomic():
            user_wallet = _get_or_error_wallet(user)
            treasury    = get_master_treasury()
            treasury_wallet = DeltaCrownWallet.objects.select_for_update().get(pk=treasury.pk)

            # 1. Debit treasury
            DeltaCrownTransaction.objects.create(
                wallet=treasury_wallet,
                amount=-FIRST_MATCH_BONUS_DC,
                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                note=f"[AUTO] First match bonus treasury debit → {user.username}",
                idempotency_key=f"{idem_key}_treasury",
            )
            treasury_wallet.recalc_and_save()

            # 2. Credit user (idempotency guard)
            txn = DeltaCrownTransaction.objects.create(
                wallet=user_wallet,
                amount=FIRST_MATCH_BONUS_DC,
                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                note=f"[AUTO] Verified Competitor bonus — first match (+{FIRST_MATCH_BONUS_DC} DC)",
                idempotency_key=idem_key,
            )
            user_wallet.recalc_and_save()

            # 3. Audit log
            _write_audit(
                action="AUTO_REWARD_MATCH",
                actor_label="SYSTEM_MATCH",
                target_wallet=user_wallet,
                amount=FIRST_MATCH_BONUS_DC,
                note=f"First match bonus awarded to {user.username}",
            )

    except IntegrityError:
        logger.info(
            "[RewardService] First match bonus already awarded for user=%s — skipping.",
            user.username,
        )
        return None

    logger.info(
        "[RewardService] AUTO_REWARD_MATCH: +%s DC awarded to %s",
        FIRST_MATCH_BONUS_DC, user.username,
    )
    return txn
