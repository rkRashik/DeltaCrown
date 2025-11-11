# apps/economy/services.py
from __future__ import annotations

from typing import Iterable, List, Optional, Union, Dict, Any

from django.apps import apps
from django.db import transaction
from django.db import DatabaseError, IntegrityError
from django.db.models import Count
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
    "get_transaction_history",
    "get_transaction_history_cursor",
    "get_transaction_totals",
    "get_pending_holds_summary",
    "export_transactions_csv",
    "export_transactions_csv_streaming",
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


# ==============================================================================
# DEPRECATED: Tournament Integration Shims (Legacy Functions)
# ==============================================================================
# The following functions (award, award_participation_for_registration,
# award_placements, backfill_participation_for_verified_payments) are retained
# for backward compatibility with Module 5.2 tournament payouts.
#
# Status: Deprecated (tournament models moved to legacy per Nov 2, 2025 signals.py)
# Testing: Covered by idempotency invariant tests only (see test_idempotency_module_7_1.py)
# Coverage: Intentionally excluded from line coverage target (see MODULE_7.1_COMPLETION_STATUS.md)
# Replacement: Use core API (credit/debit/transfer/get_balance/get_transaction_history) for new code
#
# These functions depend on deprecated tournament models and will be removed in Phase 8.
# See Documents/ExecutionPlan/MODULE_7.1_COMPLETION_STATUS.md for deprecation timeline.
# ==============================================================================

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

            # Idempotency: if provided, check existing (use derived keys for debit/credit)
            debit_key = f"{idempotency_key}_debit" if idempotency_key else None
            credit_key = f"{idempotency_key}_credit" if idempotency_key else None
            
            if idempotency_key:
                # Check if debit transaction already exists
                existing_debit = DeltaCrownTransaction.objects.filter(idempotency_key=debit_key).first()
                if existing_debit:
                    # Transfer already processed; return original result
                    existing_credit = DeltaCrownTransaction.objects.filter(idempotency_key=credit_key).first()
                    if not existing_credit:
                        raise IdempotencyConflict("Transfer partially completed (debit exists, credit missing)")
                    
                    return {
                        "from_wallet_id": w_from.id,
                        "to_wallet_id": w_to.id,
                        "from_balance_after": int(w_from.cached_balance),
                        "to_balance_after": int(w_to.cached_balance),
                        "debit_transaction_id": existing_debit.id,
                        "credit_transaction_id": existing_credit.id,
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

            # Create transactions: debit then credit (with distinct keys)
            debit_tx = _create_transaction(w_from, -int(amount), reason, idempotency_key=debit_key)
            credit_tx = _create_transaction(w_to, int(amount), reason, idempotency_key=credit_key)

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


def get_transaction_history(
    wallet_or_profile: Union[DeltaCrownWallet, object],
    *,
    page: int = 1,
    page_size: int = 20,
    transaction_type: Optional[str] = None,
    reason: Optional[str] = None,
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
    order: str = 'desc'
) -> Dict[str, Any]:
    """
    Get paginated transaction history with filtering.
    
    Args:
        wallet_or_profile: DeltaCrownWallet instance or profile object
        page: Page number (1-indexed)
        page_size: Number of transactions per page (default 20, max 100)
        transaction_type: Filter by 'DEBIT' or 'CREDIT' (checks amount sign)
        reason: Filter by transaction reason
        start_date: Filter transactions >= this date
        end_date: Filter transactions <= this date
        order: 'desc' (newest first) or 'asc' (oldest first)
    
    Returns:
        Dict with:
            - transactions: List of transaction dictionaries
            - page: Current page number
            - page_size: Items per page
            - total_count: Total matching transactions
            - has_next: Boolean indicating more pages
            - has_prev: Boolean indicating previous pages
    """
    # Resolve wallet
    if isinstance(wallet_or_profile, DeltaCrownWallet):
        wallet = wallet_or_profile
    else:
        profile = _resolve_profile(wallet_or_profile)
        wallet = DeltaCrownWallet.objects.filter(profile=profile).first()
        if not wallet:
            return {
                'transactions': [],
                'page': page,
                'page_size': page_size,
                'total_count': 0,
                'has_next': False,
                'has_prev': False
            }
    
    # Validate and cap page_size
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    
    # Build queryset
    qs = DeltaCrownTransaction.objects.filter(wallet=wallet)
    
    # Apply filters
    if transaction_type:
        if transaction_type.upper() == 'DEBIT':
            qs = qs.filter(amount__lt=0)
        elif transaction_type.upper() == 'CREDIT':
            qs = qs.filter(amount__gt=0)
    
    if reason:
        qs = qs.filter(reason=reason)
    
    if start_date:
        qs = qs.filter(created_at__gte=start_date)
    
    if end_date:
        qs = qs.filter(created_at__lte=end_date)
    
    # Apply ordering
    order_by = '-created_at' if order.lower() == 'desc' else 'created_at'
    qs = qs.order_by(order_by)
    
    # Get total count
    total_count = qs.count()
    
    # Calculate pagination
    offset = (page - 1) * page_size
    transactions_page = qs[offset:offset + page_size]
    
    # Build response
    transactions = [
        {
            'id': t.id,
            'amount': int(t.amount),
            'balance_after': int(t.cached_balance_after) if hasattr(t, 'cached_balance_after') else None,
            'reason': t.reason,
            'created_at': t.created_at,
            'idempotency_key': t.idempotency_key,
        }
        for t in transactions_page
    ]
    
    return {
        'transactions': transactions,
        'page': page,
        'page_size': page_size,
        'total_count': total_count,
        'has_next': offset + page_size < total_count,
        'has_prev': page > 1
    }


def get_transaction_history_cursor(
    wallet: DeltaCrownWallet,
    *,
    cursor: Optional[int] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get transaction history using cursor-based pagination for stable ordering.
    
    Args:
        wallet: DeltaCrownWallet instance
        cursor: Transaction ID to start from (exclusive)
        limit: Number of transactions to return
    
    Returns:
        Dict with:
            - transactions: List of transaction dictionaries
            - next_cursor: Transaction ID for next page (None if last page)
            - has_more: Boolean indicating more data available
    """
    limit = max(1, min(100, int(limit)))
    
    # Build queryset (ordered by ID desc for stable cursor pagination)
    qs = DeltaCrownTransaction.objects.filter(wallet=wallet).order_by('-id')
    
    if cursor:
        qs = qs.filter(id__lt=cursor)
    
    transactions = list(qs[:limit + 1])  # Fetch one extra to check has_more
    
    has_more = len(transactions) > limit
    if has_more:
        transactions = transactions[:limit]
    
    next_cursor = transactions[-1].id if transactions and has_more else None
    
    return {
        'transactions': [
            {
                'id': t.id,
                'amount': int(t.amount),
                'balance_after': int(t.cached_balance_after) if hasattr(t, 'cached_balance_after') else None,
                'reason': t.reason,
                'created_at': t.created_at,
                'idempotency_key': t.idempotency_key,
            }
            for t in transactions
        ],
        'next_cursor': next_cursor,
        'has_more': has_more
    }


def get_transaction_totals(
    wallet: DeltaCrownWallet,
    *,
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Get transaction totals and summary statistics.
    
    Args:
        wallet: DeltaCrownWallet instance
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Dict with:
            - current_balance: Current wallet balance
            - total_credits: Sum of all credit transactions
            - total_debits: Sum of all debit transactions (absolute value)
            - transaction_count: Total number of transactions
            - credits_count: Number of credit transactions
            - debits_count: Number of debit transactions
    """
    from django.db.models import Sum, Count, Q
    
    qs = DeltaCrownTransaction.objects.filter(wallet=wallet)
    
    if start_date:
        qs = qs.filter(created_at__gte=start_date)
    
    if end_date:
        qs = qs.filter(created_at__lte=end_date)
    
    # Aggregate totals
    aggregates = qs.aggregate(
        total_credits=Sum('amount', filter=Q(amount__gt=0)),
        total_debits=Sum('amount', filter=Q(amount__lt=0)),
        transaction_count=Count('id'),
        credits_count=Count('id', filter=Q(amount__gt=0)),
        debits_count=Count('id', filter=Q(amount__lt=0))
    )
    
    return {
        'current_balance': int(wallet.cached_balance),
        'total_credits': int(aggregates['total_credits'] or 0),
        'total_debits': abs(int(aggregates['total_debits'] or 0)),  # Return as positive
        'transaction_count': aggregates['transaction_count'],
        'credits_count': aggregates['credits_count'],
        'debits_count': aggregates['debits_count']
    }


def get_pending_holds_summary(wallet: DeltaCrownWallet) -> Dict[str, Any]:
    """
    Get summary of pending shop reservation holds.
    
    Args:
        wallet: DeltaCrownWallet instance
    
    Returns:
        Dict with:
            - total_pending: Total amount in pending holds
            - hold_count: Number of active holds
            - available_balance: Current balance minus pending holds
    """
    from django.db.models import Sum
    
    # Import ReservationHold model (lazily to avoid circular imports)
    try:
        ReservationHold = apps.get_model("shop", "ReservationHold")
    except LookupError:
        # Shop app not installed
        return {
            'total_pending': 0,
            'hold_count': 0,
            'available_balance': int(wallet.cached_balance)
        }
    
    # Get active holds
    active_holds = ReservationHold.objects.filter(
        wallet=wallet,
        status='authorized'
    ).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    total_pending = int(active_holds['total'] or 0)
    hold_count = active_holds['count']
    
    return {
        'total_pending': total_pending,
        'hold_count': hold_count,
        'available_balance': int(wallet.cached_balance) - total_pending
    }


def export_transactions_csv(
    wallet: DeltaCrownWallet,
    *,
    transaction_type: Optional[str] = None,
    reason: Optional[str] = None,
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
    max_rows: int = 10000
) -> str:
    """
    Export transaction history to CSV format.
    
    Args:
        wallet: DeltaCrownWallet instance
        transaction_type: Filter by 'DEBIT' or 'CREDIT'
        reason: Filter by transaction reason
        start_date: Filter transactions >= this date
        end_date: Filter transactions <= this date
        max_rows: Maximum number of rows (default 10000)
    
    Returns:
        CSV string with BOM for Excel compatibility
    """
    import csv
    import io
    
    # Build queryset with filters
    qs = DeltaCrownTransaction.objects.filter(wallet=wallet)
    
    if transaction_type:
        if transaction_type.upper() == 'DEBIT':
            qs = qs.filter(amount__lt=0)
        elif transaction_type.upper() == 'CREDIT':
            qs = qs.filter(amount__gt=0)
    
    if reason:
        qs = qs.filter(reason=reason)
    
    if start_date:
        qs = qs.filter(created_at__gte=start_date)
    
    if end_date:
        qs = qs.filter(created_at__lte=end_date)
    
    # Order and limit
    qs = qs.order_by('-created_at')[:max_rows]
    
    # Create CSV
    output = io.StringIO()
    # Add BOM for Excel compatibility
    output.write('\ufeff')
    
    writer = csv.DictWriter(
        output,
        fieldnames=['Date', 'Type', 'Amount', 'Balance After', 'Reason', 'ID'],
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    
    for txn in qs:
        writer.writerow({
            'Date': txn.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Type': 'Credit' if txn.amount > 0 else 'Debit',
            'Amount': int(txn.amount),
            'Balance After': int(txn.cached_balance_after) if hasattr(txn, 'cached_balance_after') else '',
            'Reason': txn.reason,
            'ID': txn.id
        })
    
    return output.getvalue()


def export_transactions_csv_streaming(
    wallet: DeltaCrownWallet,
    *,
    transaction_type: Optional[str] = None,
    reason: Optional[str] = None,
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
    chunk_size: int = 1000
):
    """
    Export transaction history as CSV generator for streaming large datasets.
    
    Args:
        wallet: DeltaCrownWallet instance
        transaction_type: Filter by 'DEBIT' or 'CREDIT'
        reason: Filter by transaction reason
        start_date: Filter transactions >= this date
        end_date: Filter transactions <= this date
        chunk_size: Number of rows per chunk
    
    Yields:
        CSV chunks as strings
    """
    import csv
    import io
    
    # Build queryset with filters
    qs = DeltaCrownTransaction.objects.filter(wallet=wallet)
    
    if transaction_type:
        if transaction_type.upper() == 'DEBIT':
            qs = qs.filter(amount__lt=0)
        elif transaction_type.upper() == 'CREDIT':
            qs = qs.filter(amount__gt=0)
    
    if reason:
        qs = qs.filter(reason=reason)
    
    if start_date:
        qs = qs.filter(created_at__gte=start_date)
    
    if end_date:
        qs = qs.filter(created_at__lte=end_date)
    
    # Order by created_at descending
    qs = qs.order_by('-created_at')
    
    # Yield header with BOM
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.DictWriter(
        output,
        fieldnames=['Date', 'Type', 'Amount', 'Balance After', 'Reason', 'ID'],
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    yield output.getvalue()
    
    # Stream rows in chunks
    offset = 0
    while True:
        chunk = list(qs[offset:offset + chunk_size])
        if not chunk:
            break
        
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=['Date', 'Type', 'Amount', 'Balance After', 'Reason', 'ID'],
            quoting=csv.QUOTE_MINIMAL
        )
        
        for txn in chunk:
            writer.writerow({
                'Date': txn.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Type': 'Credit' if txn.amount > 0 else 'Debit',
                'Amount': int(txn.amount),
                'Balance After': int(txn.cached_balance_after) if hasattr(txn, 'cached_balance_after') else '',
                'Reason': txn.reason,
                'ID': txn.id
            })
        
        yield output.getvalue()
        offset += chunk_size

