# apps/economy/services.py
from __future__ import annotations

from typing import Iterable, List, Optional, Union, Dict, Any

from django.apps import apps
from django.db import transaction
from django.db import DatabaseError, IntegrityError
from time import sleep
import random

from .models import CoinPolicy, DeltaCrownTransaction, DeltaCrownWallet


# Public API of this module
__all__ = [
    "wallet_for",
    "award",
    "award_participation_for_registration",
    "award_placements",
    "backfill_participation_for_verified_payments",
    "manual_adjust",
]

# ---- Wallet helpers ---------------------------------------------------------

def wallet_for(profile) -> DeltaCrownWallet:
    w, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
    return w


def _profiles_from_team(team) -> Iterable:
    """
    Return all profiles on a team, including captain.
    We resolve models lazily to avoid circular imports.
    """
    if not team:
        return []
    Membership = apps.get_model("teams", "TeamMembership")
    qs = Membership.objects.filter(team=team)
    return [m.profile for m in qs.select_related("profile")]


# ---- Ledger primitives ------------------------------------------------------

def _mk_idem_key(kind: str, **parts) -> str:
    """
    Build a deterministic idempotency key like:
      participation:reg:123:w:45
      winner:t:10:w:45
      runner_up:t:10:w:46
      top4:match:77:w:90
    """
    bits = [kind]
    for k in sorted(parts.keys()):
        bits.append(f"{k}:{parts[k]}")
    return ":".join(bits)


@transaction.atomic
def award(
    *,
    profile,
    amount: int,
    reason: str,
    tournament=None,
    registration=None,
    match=None,
    note: str = "",
    created_by=None,
    idempotency_key: Optional[str] = None,
) -> DeltaCrownTransaction:
    """
    Create a credit (amount>0) or debit (amount<0) transaction for profile's wallet.
    Idempotent by (idempotency_key); if provided and exists, returns existing row.
    """
    w = wallet_for(profile)
    idem = idempotency_key
    if not idem:
        # sensible default schemes
        if reason == DeltaCrownTransaction.Reason.PARTICIPATION and registration:
            idem = _mk_idem_key("participation", reg=registration.id, w=w.id)
        elif reason in (
            DeltaCrownTransaction.Reason.WINNER,
            DeltaCrownTransaction.Reason.RUNNER_UP,
            DeltaCrownTransaction.Reason.TOP4,
        ) and tournament:
            # one per (tournament, wallet, reason)
            idem = _mk_idem_key(reason, t=tournament.id, w=w.id)
        elif match:
            idem = _mk_idem_key(reason, match=match.id, w=w.id)

    # Double-check guard
    if idem:
        existing = DeltaCrownTransaction.objects.filter(idempotency_key=idem).first()
        if existing:
            return existing

    tx = DeltaCrownTransaction.objects.create(
        wallet=w,
        amount=int(amount),
        reason=reason,
        tournament=tournament,
        registration=registration,
        match=match,
        note=note,
        created_by=created_by,
        idempotency_key=idem,
    )
    return tx


# ---- Awarding routines ------------------------------------------------------

def award_participation_for_registration(reg) -> List[DeltaCrownTransaction]:
    """
    Award participation coins to the registrant (solo) or all team members (team),
    according to the tournament's CoinPolicy. Idempotent via idempotency_key.
    """
    policy = getattr(reg.tournament, "coin_policy", None)
    if not policy or not policy.enabled or policy.participation <= 0:
        return []

    awards: List[DeltaCrownTransaction] = []

    if getattr(reg, "user_id", None):
        profile = reg.user
        awards.append(
            award(
                profile=profile,
                amount=policy.participation,
                reason=DeltaCrownTransaction.Reason.PARTICIPATION,
                tournament=reg.tournament,
                registration=reg,
                note="Participation",
            )
        )
    elif getattr(reg, "team_id", None):
        for p in _profiles_from_team(reg.team):
            awards.append(
                award(
                    profile=p,
                    amount=policy.participation,
                    reason=DeltaCrownTransaction.Reason.PARTICIPATION,
                    tournament=reg.tournament,
                    registration=reg,
                    note="Participation",
                )
            )
    return awards


def award_placements(tournament) -> List[DeltaCrownTransaction]:
    """
    Award placements (winner, runner_up, optional top4).
    Supports TEAM brackets (team_a/team_b/winner_team) and SOLO brackets (user_a/user_b/winner_user).
    TEAM policy: award to CAPTAINS (avoid double-counting rosters).
    SOLO policy: award directly to users.
    """
    policy = getattr(tournament, "coin_policy", None)
    if not policy or not policy.enabled:
        return []

    Match = apps.get_model("tournaments", "Match")
    Membership = apps.get_model("teams", "TeamMembership")

    def captain_profile(team):
        cap = (
            Membership.objects.filter(team=team, role__iexact="CAPTAIN")
            .select_related("profile")
            .first()
        )
        return cap.profile if cap else None

    # Final = highest round, position 1
    final = (
        Match.objects.filter(tournament=tournament, position=1)
        .order_by("-round_no")
        .first()
    )
    if not final:
        return []

    awards: List[DeltaCrownTransaction] = []

    is_team_final = bool(getattr(final, "winner_team_id", None))
    is_solo_final = bool(getattr(final, "winner_user_id", None))

    # ---------- TEAM BRACKET ----------
    if is_team_final and getattr(final, "team_a_id", None) and getattr(final, "team_b_id", None):
        winner_team = final.winner_team
        runner_team = final.team_a if final.winner_team_id == final.team_b_id else final.team_b

        # Winner
        if policy.winner > 0:
            cp = captain_profile(winner_team)
            if cp:
                awards.append(
                    award(
                        profile=cp,
                        amount=policy.winner,
                        reason=DeltaCrownTransaction.Reason.WINNER,
                        tournament=tournament,
                        match=final,
                        note="Winner",
                    )
                )
        # Runner-up
        if policy.runner_up > 0:
            cp = captain_profile(runner_team)
            if cp:
                awards.append(
                    award(
                        profile=cp,
                        amount=policy.runner_up,
                        reason=DeltaCrownTransaction.Reason.RUNNER_UP,
                        tournament=tournament,
                        match=final,
                        note="Runner-up",
                    )
                )

        # Top4 (losers of semifinals)
        if policy.top4 > 0 and getattr(final, "round_no", None):
            semis = (
                Match.objects.filter(tournament=tournament, round_no=final.round_no - 1, position__in=[1, 2])
                .select_related("team_a", "team_b", "winner_team")
                .all()
            )
            for m in semis:
                if not (m.team_a_id and m.team_b_id and m.winner_team_id):
                    continue
                loser_team = m.team_b if m.winner_team_id == m.team_a_id else m.team_a
                cp = captain_profile(loser_team)
                if cp:
                    awards.append(
                        award(
                            profile=cp,
                            amount=policy.top4,
                            reason=DeltaCrownTransaction.Reason.TOP4,
                            tournament=tournament,
                            match=m,
                            note="Top 4",
                        )
                    )
        return awards

    # ---------- SOLO BRACKET ----------
    if is_solo_final and getattr(final, "user_a_id", None) and getattr(final, "user_b_id", None):
        winner_user = final.winner_user
        runner_user = final.user_a if final.winner_user_id == final.user_b_id else final.user_b

        # Winner
        if policy.winner > 0 and winner_user:
            awards.append(
                award(
                    profile=winner_user,
                    amount=policy.winner,
                    reason=DeltaCrownTransaction.Reason.WINNER,
                    tournament=tournament,
                    match=final,
                    note="Winner",
                )
            )

        # Runner-up
        if policy.runner_up > 0 and runner_user:
            awards.append(
                award(
                    profile=runner_user,
                    amount=policy.runner_up,
                    reason=DeltaCrownTransaction.Reason.RUNNER_UP,
                    tournament=tournament,
                    match=final,
                    note="Runner-up",
                )
            )

        # Top4: losers of semifinals (solo)
        if policy.top4 > 0 and getattr(final, "round_no", None):
            semis = (
                Match.objects.filter(tournament=tournament, round_no=final.round_no - 1, position__in=[1, 2])
                .select_related("user_a", "user_b", "winner_user")
                .all()
            )
            for m in semis:
                if not (m.user_a_id and m.user_b_id and m.winner_user_id):
                    continue
                loser_user = m.user_b if m.winner_user_id == m.user_a_id else m.user_a
                awards.append(
                    award(
                        profile=loser_user,
                        amount=policy.top4,
                        reason=DeltaCrownTransaction.Reason.TOP4,
                        tournament=tournament,
                        match=m,
                        note="Top 4",
                    )
                )
        return awards

    # If neither shape is satisfied, nothing to do
    return []


def backfill_participation_for_verified_payments() -> int:
    """
    Iterate over already-VERIFIED payment verifications and ensure participation is awarded.
    Returns count of registrations processed (creates are idempotent).
    """
    PV = apps.get_model("tournaments", "PaymentVerification")
    Reg = apps.get_model("tournaments", "Registration")

    reg_ids = (
        PV.objects.filter(status="verified")
        .values_list("registration_id", flat=True)
        .distinct()
    )

    processed = 0
    for reg in Reg.objects.filter(id__in=list(reg_ids)).select_related("tournament", "user", "team"):
        award_participation_for_registration(reg)
        processed += 1
    return processed


# ---- Manual adjustments -----------------------------------------------------

def manual_adjust(wallet: DeltaCrownWallet, amount: int, *, note: str = "", created_by=None) -> DeltaCrownTransaction:
    """
    Adjust balance by creating a MANUAL_ADJUST transaction (positive or negative).
    """
    return DeltaCrownTransaction.objects.create(
        wallet=wallet,
        amount=int(amount),
        reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
        note=note or "Manual adjustment",
        created_by=created_by,
    )


# ---- Service API (Step 3) -----------------------------------------------
from .exceptions import InvalidAmount, InsufficientFunds, InvalidWallet, IdempotencyConflict


def _resolve_profile(profile_or_id) -> Any:
    """Accept either a UserProfile instance or an integer id."""
    if profile_or_id is None:
        return None
    if isinstance(profile_or_id, int):
        Profile = apps.get_model("user_profile", "UserProfile")
        return Profile.objects.get(pk=profile_or_id)
    return profile_or_id


def _result_dict(wallet: DeltaCrownWallet, txn: DeltaCrownTransaction, idem: Optional[str]) -> Dict[str, Any]:
    return {
        "wallet_id": wallet.id,
        "balance_after": int(wallet.cached_balance),
        "transaction_id": txn.id,
        "idempotency_key": idem,
    }


def _create_transaction(wallet: DeltaCrownWallet, amount: int, reason: str, *, idempotency_key: Optional[str], **kwargs) -> DeltaCrownTransaction:
    """Create a transaction row and persist. Map DB integrity errors."""
    try:
        tx = DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=int(amount),
            reason=reason,
            idempotency_key=idempotency_key,
            **kwargs,
        )
        return tx
    except IntegrityError as exc:
        # Possible concurrent insert of same idempotency_key -> fetch existing
        if idempotency_key:
            existing = DeltaCrownTransaction.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing
        raise


def _with_retry(fn, retries: int = 3):
    """Simple retry wrapper for serialization/deadlock errors."""
    last = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except DatabaseError as exc:
            last = exc
            msg = str(exc).lower()
            # Retry on common transient DB errors
            if "deadlock" in msg or "could not serialize" in msg or "serialization" in msg:
                backoff = (0.05 * attempt) + random.random() * 0.05
                sleep(backoff)
                continue
            raise
    # exhausted
    raise last


def credit(profile: Union[int, object], amount: int, *, reason: str, idempotency_key: Optional[str] = None, meta: Optional[dict] = None) -> Dict[str, Any]:
    """Credit a wallet atomically. Returns dict with wallet_id, balance_after, transaction_id, idempotency_key."""
    if amount <= 0:
        raise InvalidAmount("Transaction amount must be greater than zero")

    profile = _resolve_profile(profile)

    def _op():
        with transaction.atomic():
            wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
            # lock the wallet row
            wallet = DeltaCrownWallet.objects.select_for_update().get(pk=wallet.pk)

            # Idempotency: return existing if same key used
            if idempotency_key:
                existing = DeltaCrownTransaction.objects.filter(idempotency_key=idempotency_key).first()
                if existing:
                    # Validate same payload
                    if existing.amount != int(amount) or existing.reason != reason:
                        raise IdempotencyConflict("Idempotency key reused with different payload")
                    return _result_dict(wallet, existing, idempotency_key)

            # Apply balance and create txn
            wallet.cached_balance = int(wallet.cached_balance) + int(amount)
            wallet.save(update_fields=["cached_balance", "updated_at"]) if wallet.pk else wallet.save()

            txn = _create_transaction(wallet, amount, reason, idempotency_key=idempotency_key)
            return _result_dict(wallet, txn, idempotency_key)

    return _with_retry(_op)


def debit(profile: Union[int, object], amount: int, *, reason: str, idempotency_key: Optional[str] = None, meta: Optional[dict] = None) -> Dict[str, Any]:
    """Debit a wallet atomically; amount must be >0 (we store negative amounts)."""
    if amount <= 0:
        raise InvalidAmount("Transaction amount must be greater than zero")

    profile = _resolve_profile(profile)

    def _op():
        with transaction.atomic():
            wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
            wallet = DeltaCrownWallet.objects.select_for_update().get(pk=wallet.pk)

            # Idempotency check
            if idempotency_key:
                existing = DeltaCrownTransaction.objects.filter(idempotency_key=idempotency_key).first()
                if existing:
                    if existing.amount != -int(amount) or existing.reason != reason:
                        raise IdempotencyConflict("Idempotency key reused with different payload")
                    return _result_dict(wallet, existing, idempotency_key)

            # Balance check
            projected = int(wallet.cached_balance) - int(amount)
            if projected < 0 and not wallet.allow_overdraft:
                raise InsufficientFunds(f"Insufficient funds: {wallet.cached_balance} available, need {amount}")

            wallet.cached_balance = projected
            wallet.save(update_fields=["cached_balance", "updated_at"]) if wallet.pk else wallet.save()

            txn = _create_transaction(wallet, -int(amount), reason, idempotency_key=idempotency_key)
            return _result_dict(wallet, txn, idempotency_key)

    return _with_retry(_op)


def transfer(from_profile: Union[int, object], to_profile: Union[int, object], amount: int, *, reason: str, idempotency_key: Optional[str] = None, meta: Optional[dict] = None) -> Dict[str, Any]:
    """Transfer amount from one wallet to another atomically. Returns dict with both transaction ids in meta."""
    if amount <= 0:
        raise InvalidAmount("Transaction amount must be greater than zero")

    if from_profile == to_profile:
        raise InvalidWallet("Cannot transfer to the same wallet/profile")

    from_profile = _resolve_profile(from_profile)
    to_profile = _resolve_profile(to_profile)

    def _op():
        with transaction.atomic():
            # Acquire locks in stable order by wallet id (or temp create to get ids)
            w_from, _ = DeltaCrownWallet.objects.get_or_create(profile=from_profile)
            w_to, _ = DeltaCrownWallet.objects.get_or_create(profile=to_profile)

            first, second = (w_from, w_to) if w_from.id <= w_to.id else (w_to, w_from)
            # lock both
            DeltaCrownWallet.objects.select_for_update().filter(pk__in=[first.pk, second.pk]).order_by("pk").count()

            # Re-fetch locked wallets
            w_from = DeltaCrownWallet.objects.select_for_update().get(pk=w_from.pk)
            w_to = DeltaCrownWallet.objects.select_for_update().get(pk=w_to.pk)

            # Idempotency: if provided, check existing
            if idempotency_key:
                existing = DeltaCrownTransaction.objects.filter(idempotency_key=idempotency_key).first()
                if existing:
                    # We expect a pair: credit and debit with same idempotency_key; return original
                    txs = list(DeltaCrownTransaction.objects.filter(idempotency_key=idempotency_key).order_by("id"))
                    if not txs:
                        raise IdempotencyConflict("Idempotency key exists but transactions missing")
                    # return info for first matching tx (debit)
                    return {
                        "wallet_id": w_from.id,
                        "balance_after": int(w_from.cached_balance),
                        "transaction_id": txs[0].id,
                        "idempotency_key": idempotency_key,
                    }

            # Balance check on sender
            projected = int(w_from.cached_balance) - int(amount)
            if projected < 0 and not w_from.allow_overdraft:
                raise InsufficientFunds(f"Insufficient funds: {w_from.cached_balance} available, need {amount}")

            # Apply balances
            w_from.cached_balance = projected
            w_from.save(update_fields=["cached_balance", "updated_at"]) if w_from.pk else w_from.save()

            w_to.cached_balance = int(w_to.cached_balance) + int(amount)
            w_to.save(update_fields=["cached_balance", "updated_at"]) if w_to.pk else w_to.save()

            # Create transactions: debit then credit
            debit_tx = _create_transaction(w_from, -int(amount), reason, idempotency_key=idempotency_key)
            credit_tx = _create_transaction(w_to, int(amount), reason, idempotency_key=idempotency_key)

            return {
                "from_wallet_id": w_from.id,
                "to_wallet_id": w_to.id,
                "from_balance_after": int(w_from.cached_balance),
                "to_balance_after": int(w_to.cached_balance),
                "debit_transaction_id": debit_tx.id,
                "credit_transaction_id": credit_tx.id,
                "idempotency_key": idempotency_key,
            }

    return _with_retry(_op)


def get_balance(profile: Union[int, object]) -> int:
    profile = _resolve_profile(profile)
    w = DeltaCrownWallet.objects.filter(profile=profile).only("cached_balance").first()
    return int(w.cached_balance) if w else 0


def get_transaction_history(profile: Union[int, object], *, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    profile = _resolve_profile(profile)
    w = DeltaCrownWallet.objects.filter(profile=profile).first()
    if not w:
        return []
    qs = DeltaCrownTransaction.objects.filter(wallet=w).order_by("-created_at")[offset : offset + limit]
    return [
        {
            "id": t.id,
            "amount": int(t.amount),
            "reason": t.reason,
            "created_at": t.created_at,
            "idempotency_key": t.idempotency_key,
        }
        for t in qs
    ]

