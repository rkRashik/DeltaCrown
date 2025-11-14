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
    # Module 7.4: Revenue Analytics
    "get_daily_revenue",
    "get_weekly_revenue",
    "get_monthly_revenue",
    "calculate_arppu",
    "calculate_arpu",
    "get_revenue_time_series",
    "get_revenue_summary",
    "export_daily_revenue_csv",
    "export_monthly_summary_csv",
    "export_revenue_csv_streaming",
    "get_cohort_revenue",
    "get_cohort_revenue_retention",
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
# See Documents/ExecutionPlan/Modules/MODULE_7.1_COMPLETION_STATUS.md for deprecation timeline.
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


# ================================================================================
# Module 7.4: Revenue Analytics
# ================================================================================

def get_daily_revenue(date: Any) -> Dict[str, Any]:
    """
    Calculate daily revenue metrics for a specific date.
    
    Args:
        date: Target date (datetime.date or datetime)
    
    Returns:
        Dict with:
            - date: The target date
            - total_revenue: Sum of all credit transactions
            - total_refunds: Sum of all refund transactions (absolute value)
            - net_revenue: total_revenue - total_refunds
            - transaction_count: Total number of transactions
            - paying_users_count: Number of unique users with credit transactions
    """
    from django.db.models import Sum, Count, Q
    from django.contrib.auth import get_user_model
    
    # Ensure date is a date object
    if hasattr(date, 'date'):
        date = date.date()
    
    # Query all transactions for the date
    txns = DeltaCrownTransaction.objects.filter(
        created_at__date=date
    )
    
    # Calculate metrics
    # Note: refunds are stored as negative amounts with reason='REFUND'
    aggregates = txns.aggregate(
        total_credits=Sum('amount', filter=Q(amount__gt=0)),
        total_refunds=Sum('amount', filter=Q(reason='REFUND')),
        transaction_count=Count('id')
    )
    
    total_revenue = int(aggregates['total_credits'] or 0)
    total_refunds = abs(int(aggregates['total_refunds'] or 0))
    
    # Count unique paying users (users with credit transactions)
    paying_users = txns.filter(amount__gt=0).values('wallet__profile').distinct().count()
    
    return {
        'date': date,
        'total_revenue': total_revenue,
        'total_refunds': total_refunds,
        'net_revenue': total_revenue - total_refunds,
        'transaction_count': aggregates['transaction_count'],
        'paying_users_count': paying_users
    }


def get_weekly_revenue(week_start: Any) -> Dict[str, Any]:
    """
    Calculate weekly revenue metrics starting from week_start.
    
    Args:
        week_start: Start date of the week (Monday)
    
    Returns:
        Dict with:
            - week_start: Start date of the week
            - week_end: End date of the week (Sunday)
            - total_revenue: Sum of revenue for the week
            - daily_breakdown: List of daily metrics for each day of the week
    """
    from datetime import timedelta
    
    # Ensure date is a date object
    if hasattr(week_start, 'date'):
        week_start = week_start.date()
    
    week_end = week_start + timedelta(days=6)
    
    # Get daily metrics for each day of the week
    daily_breakdown = []
    total_revenue = 0
    
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_metrics = get_daily_revenue(date=day)
        daily_breakdown.append({
            'date': day,
            'revenue': day_metrics['net_revenue'],
            'transactions': day_metrics['transaction_count']
        })
        total_revenue += day_metrics['net_revenue']
    
    return {
        'week_start': week_start,
        'week_end': week_end,
        'total_revenue': total_revenue,
        'daily_breakdown': daily_breakdown
    }


def get_monthly_revenue(year: int, month: int) -> Dict[str, Any]:
    """
    Calculate monthly revenue metrics.
    
    Args:
        year: Year (e.g., 2025)
        month: Month (1-12)
    
    Returns:
        Dict with:
            - year: Year
            - month: Month
            - total_revenue: Sum of all credits for the month
            - total_refunds: Sum of all refunds
            - net_revenue: total_revenue - total_refunds
            - transaction_count: Total transactions
            - daily_trend: List of daily metrics for visualization
    """
    from django.db.models import Sum, Count, Q
    from datetime import date as date_class
    import calendar
    
    # Get first and last day of month
    first_day = date_class(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = date_class(year, month, last_day_num)
    
    # Query transactions for the month
    txns = DeltaCrownTransaction.objects.filter(
        created_at__date__gte=first_day,
        created_at__date__lte=last_day
    )
    
    # Calculate aggregates
    # Note: refunds are stored as negative amounts with reason='REFUND'
    aggregates = txns.aggregate(
        total_credits=Sum('amount', filter=Q(amount__gt=0)),
        total_refunds=Sum('amount', filter=Q(reason='REFUND')),
        transaction_count=Count('id')
    )
    
    total_revenue = int(aggregates['total_credits'] or 0)
    refunds_total = abs(int(aggregates['total_refunds'] or 0))
    
    # Get daily trend
    daily_trend = []
    for day_num in range(1, last_day_num + 1):
        day = date_class(year, month, day_num)
        day_metrics = get_daily_revenue(date=day)
        daily_trend.append({
            'day': day_num,
            'date': day,
            'revenue': day_metrics['net_revenue'],
            'transactions': day_metrics['transaction_count']
        })
    
    return {
        'year': year,
        'month': month,
        'total_revenue': total_revenue,
        'refunds_total': refunds_total,
        'net_revenue': total_revenue - refunds_total,
        'transaction_count': aggregates['transaction_count'],
        'daily_trend': daily_trend
    }


def calculate_arppu(date: Any) -> Dict[str, Any]:
    """
    Calculate Average Revenue Per Paying User for a specific date.
    
    ARPPU = Total Revenue / Number of Paying Users
    
    Args:
        date: Target date
    
    Returns:
        Dict with:
            - arppu: Average revenue per paying user
            - paying_users: Number of users with credit transactions
            - total_revenue: Total revenue for the date
    """
    from django.db.models import Sum
    
    # Ensure date is a date object
    if hasattr(date, 'date'):
        date = date.date()
    
    # Get transactions for the date with credits only
    credit_txns = DeltaCrownTransaction.objects.filter(
        created_at__date=date,
        amount__gt=0
    )
    
    # Count unique paying users
    paying_users = credit_txns.values('wallet__profile').distinct().count()
    
    # Calculate total revenue
    total_revenue = int(credit_txns.aggregate(total=Sum('amount'))['total'] or 0)
    
    # Calculate ARPPU
    arppu = total_revenue / paying_users if paying_users > 0 else 0
    
    return {
        'arppu': arppu,
        'paying_users': paying_users,
        'total_revenue': total_revenue,
        'date': date
    }


def calculate_arpu(date: Any) -> Dict[str, Any]:
    """
    Calculate Average Revenue Per User for a specific date.
    
    ARPU = Total Revenue / Total Users
    
    Args:
        date: Target date
    
    Returns:
        Dict with:
            - arpu: Average revenue per user (all users, not just paying)
            - total_users: Total number of users in the system
            - total_revenue: Total revenue for the date
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Sum
    
    User = get_user_model()
    
    # Ensure date is a date object
    if hasattr(date, 'date'):
        date = date.date()
    
    # Get total users
    total_users = User.objects.count()
    
    # Get total revenue for the date
    credit_txns = DeltaCrownTransaction.objects.filter(
        created_at__date=date,
        amount__gt=0
    )
    total_revenue = int(credit_txns.aggregate(total=Sum('amount'))['total'] or 0)
    
    # Calculate ARPU
    arpu = total_revenue / total_users if total_users > 0 else 0
    
    return {
        'arpu': arpu,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'date': date
    }


def get_revenue_time_series(
    start_date: Any,
    end_date: Any,
    granularity: str = 'daily'
) -> Dict[str, Any]:
    """
    Get revenue time series data for a date range.
    
    Args:
        start_date: Start date of the range
        end_date: End date of the range
        granularity: 'daily' or 'weekly'
    
    Returns:
        Dict with:
            - data_points: List of time series data points
            - start_date: Range start
            - end_date: Range end
            - granularity: Time granularity
    """
    from datetime import timedelta
    
    # Ensure dates are date objects
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    
    data_points = []
    
    if granularity == 'daily':
        current_date = start_date
        while current_date <= end_date:
            day_metrics = get_daily_revenue(date=current_date)
            data_points.append({
                'date': current_date,
                'revenue': day_metrics['net_revenue'],
                'transactions': day_metrics['transaction_count'],
                'paying_users': day_metrics['paying_users_count']
            })
            current_date += timedelta(days=1)
    
    elif granularity == 'weekly':
        # Start from the Monday of the week containing start_date
        current_date = start_date - timedelta(days=start_date.weekday())
        
        while current_date <= end_date:
            week_metrics = get_weekly_revenue(week_start=current_date)
            data_points.append({
                'week_start': current_date,
                'week_end': current_date + timedelta(days=6),
                'revenue': week_metrics['total_revenue'],
                'daily_breakdown': week_metrics['daily_breakdown']
            })
            current_date += timedelta(days=7)
    
    return {
        'data_points': data_points,
        'start_date': start_date,
        'end_date': end_date,
        'granularity': granularity
    }


def get_revenue_summary(
    start_date: Any,
    end_date: Any,
    include_growth: bool = False
) -> Dict[str, Any]:
    """
    Get comprehensive revenue summary for a date range.
    
    Args:
        start_date: Start date of the period
        end_date: End date of the period
        include_growth: Whether to include growth metrics vs previous period
    
    Returns:
        Dict with:
            - period: Date range
            - total_revenue: Sum of all credits
            - total_refunds: Sum of all refunds
            - net_revenue: Revenue minus refunds
            - transaction_count: Total transactions
            - unique_paying_users: Count of unique paying users
            - arppu: Average revenue per paying user
            - average_transaction_value: Average value per transaction
            - growth: Optional growth metrics vs previous period
    """
    from django.db.models import Sum, Count, Q
    from datetime import timedelta
    
    # Ensure dates are date objects
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    
    # Query transactions for the period
    txns = DeltaCrownTransaction.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    # Calculate aggregates
    # Note: refunds are stored as negative amounts with reason='REFUND'
    aggregates = txns.aggregate(
        total_credits=Sum('amount', filter=Q(amount__gt=0)),
        total_refunds=Sum('amount', filter=Q(reason='REFUND')),
        transaction_count=Count('id'),
        paying_user_txns=Count('id', filter=Q(amount__gt=0))
    )
    
    total_revenue = int(aggregates['total_credits'] or 0)
    total_refunds = abs(int(aggregates['total_refunds'] or 0))
    net_revenue = total_revenue - total_refunds
    transaction_count = aggregates['transaction_count']
    
    # Count unique paying users
    unique_paying_users = txns.filter(amount__gt=0).values('wallet__profile').distinct().count()
    
    # Calculate metrics
    arppu = total_revenue / unique_paying_users if unique_paying_users > 0 else 0
    avg_transaction_value = total_revenue / transaction_count if transaction_count > 0 else 0
    
    result = {
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'total_revenue': total_revenue,
        'total_refunds': total_refunds,
        'net_revenue': net_revenue,
        'transaction_count': transaction_count,
        'unique_paying_users': unique_paying_users,
        'arppu': arppu,
        'average_transaction_value': avg_transaction_value
    }
    
    # Optional: Calculate growth metrics
    if include_growth:
        # Get previous period (same length)
        period_length = (end_date - start_date).days + 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_length - 1)
        
        prev_summary = get_revenue_summary(prev_start, prev_end, include_growth=False)
        
        # Calculate growth percentages
        revenue_growth = 0
        if prev_summary['total_revenue'] > 0:
            revenue_growth = ((total_revenue - prev_summary['total_revenue']) / prev_summary['total_revenue']) * 100
        
        user_growth = 0
        if prev_summary['unique_paying_users'] > 0:
            user_growth = ((unique_paying_users - prev_summary['unique_paying_users']) / prev_summary['unique_paying_users']) * 100
        
        result['growth'] = {
            'revenue_growth_percent': revenue_growth,
            'user_growth_percent': user_growth,
            'previous_period': {
                'start_date': prev_start,
                'end_date': prev_end,
                'total_revenue': prev_summary['total_revenue'],
                'unique_paying_users': prev_summary['unique_paying_users']
            }
        }
    
    return result


def export_daily_revenue_csv(start_date: Any, end_date: Any) -> str:
    """
    Export daily revenue data to CSV format.
    
    Args:
        start_date: Start date of the range
        end_date: End date of the range
    
    Returns:
        CSV string with BOM for Excel compatibility
    """
    import csv
    import io
    from datetime import timedelta
    
    # Ensure dates are date objects
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    
    output = io.StringIO()
    output.write('\ufeff')  # BOM
    
    writer = csv.DictWriter(
        output,
        fieldnames=['Date', 'Revenue', 'Refunds', 'Net Revenue', 'Transactions', 'Paying Users', 'ARPPU'],
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    
    # Generate daily data
    current_date = start_date
    while current_date <= end_date:
        day_metrics = get_daily_revenue(date=current_date)
        arppu_metrics = calculate_arppu(date=current_date)
        
        writer.writerow({
            'Date': current_date.strftime('%Y-%m-%d'),
            'Revenue': day_metrics['total_revenue'],
            'Refunds': day_metrics['total_refunds'],
            'Net Revenue': day_metrics['net_revenue'],
            'Transactions': day_metrics['transaction_count'],
            'Paying Users': day_metrics['paying_users_count'],
            'ARPPU': f"{arppu_metrics['arppu']:.2f}" if arppu_metrics['arppu'] > 0 else '0.00'
        })
        
        current_date += timedelta(days=1)
    
    return output.getvalue()


def export_monthly_summary_csv(year: int, month: int) -> str:
    """
    Export monthly revenue summary to CSV format.
    
    Args:
        year: Year (e.g., 2025)
        month: Month (1-12)
    
    Returns:
        CSV string with BOM for Excel compatibility
    """
    import csv
    import io
    
    monthly_data = get_monthly_revenue(year=year, month=month)
    
    output = io.StringIO()
    output.write('\ufeff')  # BOM
    
    writer = csv.DictWriter(
        output,
        fieldnames=['Day', 'Date', 'Revenue', 'Transactions'],
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    
    for day_data in monthly_data['daily_trend']:
        writer.writerow({
            'Day': day_data['day'],
            'Date': day_data['date'].strftime('%Y-%m-%d'),
            'Revenue': day_data['revenue'],
            'Transactions': day_data['transactions']
        })
    
    return output.getvalue()


def export_revenue_csv_streaming(start_date: Any, end_date: Any, chunk_size: int = 100):
    """
    Export revenue data as CSV generator for streaming large datasets.
    
    Args:
        start_date: Start date of the range
        end_date: End date of the range
        chunk_size: Number of days per chunk
    
    Yields:
        CSV chunks as strings
    """
    import csv
    import io
    from datetime import timedelta
    
    # Ensure dates are date objects
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    
    # Yield header with BOM
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.DictWriter(
        output,
        fieldnames=['Date', 'Revenue', 'Net Revenue', 'Transactions', 'Paying Users'],
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    yield output.getvalue()
    
    # Stream data in chunks
    current_date = start_date
    chunk_count = 0
    
    while current_date <= end_date:
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=['Date', 'Revenue', 'Net Revenue', 'Transactions', 'Paying Users'],
            quoting=csv.QUOTE_MINIMAL
        )
        
        # Process chunk
        for _ in range(chunk_size):
            if current_date > end_date:
                break
            
            day_metrics = get_daily_revenue(date=current_date)
            writer.writerow({
                'Date': current_date.strftime('%Y-%m-%d'),
                'Revenue': day_metrics['total_revenue'],
                'Net Revenue': day_metrics['net_revenue'],
                'Transactions': day_metrics['transaction_count'],
                'Paying Users': day_metrics['paying_users_count']
            })
            
            current_date += timedelta(days=1)
        
        yield output.getvalue()
        chunk_count += 1


def get_cohort_revenue(year: int, month: int) -> Dict[str, Any]:
    """
    Get revenue grouped by user cohort (signup month).
    
    Args:
        year: Year for analysis
        month: Month for analysis
    
    Returns:
        Dict with:
            - cohorts: List of cohort data with signup month and revenue
    """
    from django.db.models import Sum, Count, Q
    from django.contrib.auth import get_user_model
    from datetime import date as date_class
    import calendar
    
    User = get_user_model()
    
    # Get first and last day of target month
    first_day = date_class(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = date_class(year, month, last_day_num)
    
    # Get all transactions in this period
    transactions = DeltaCrownTransaction.objects.filter(
        created_at__date__gte=first_day,
        created_at__date__lte=last_day,
        amount__gt=0
    ).select_related('wallet__profile__user')
    
    # Group by signup cohort
    cohort_map = {}
    for txn in transactions:
        user = txn.wallet.profile.user
        cohort_key = f"{user.date_joined.year}-{user.date_joined.month:02d}"
        
        if cohort_key not in cohort_map:
            cohort_map[cohort_key] = {
                'cohort_month': cohort_key,
                'users': set(),
                'total_revenue': 0
            }
        
        cohort_map[cohort_key]['users'].add(user.id)
        cohort_map[cohort_key]['total_revenue'] += int(txn.amount)
    
    # Convert to list format
    cohorts = []
    for cohort_data in cohort_map.values():
        cohorts.append({
            'cohort_month': cohort_data['cohort_month'],
            'users_count': len(cohort_data['users']),
            'total_revenue': cohort_data['total_revenue']
        })
    
    cohorts.sort(key=lambda x: x['cohort_month'])
    
    return {
        'analysis_period': {
            'year': year,
            'month': month
        },
        'cohorts': cohorts
    }


def get_cohort_revenue_retention(cohort_month: str, months: int = 6) -> Dict[str, Any]:
    """
    Track revenue retention for a user cohort over multiple months.
    
    Args:
        cohort_month: Cohort month in format "YYYY-MM"
        months: Number of months to track
    
    Returns:
        Dict with:
            - cohort_month: The cohort being analyzed
            - retention_data: List of monthly retention metrics
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Sum, Q
    from datetime import date as date_class
    from dateutil.relativedelta import relativedelta
    import calendar
    
    User = get_user_model()
    
    # Parse cohort month
    year, month = map(int, cohort_month.split('-'))
    cohort_start = date_class(year, month, 1)
    
    # Get users from this cohort
    cohort_users = User.objects.filter(
        date_joined__year=year,
        date_joined__month=month
    ).values_list('id', flat=True)
    
    cohort_size = len(cohort_users)
    
    # Track revenue for each subsequent month
    retention_data = []
    
    for i in range(months):
        target_date = cohort_start + relativedelta(months=i)
        target_year = target_date.year
        target_month = target_date.month
        
        # Get first and last day of target month
        first_day = date_class(target_year, target_month, 1)
        last_day_num = calendar.monthrange(target_year, target_month)[1]
        last_day = date_class(target_year, target_month, last_day_num)
        
        # Calculate revenue from cohort users in this month
        cohort_revenue = DeltaCrownTransaction.objects.filter(
            wallet__profile__user_id__in=cohort_users,
            created_at__date__gte=first_day,
            created_at__date__lte=last_day,
            amount__gt=0
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Count active users (users with transactions)
        active_users = DeltaCrownTransaction.objects.filter(
            wallet__profile__user_id__in=cohort_users,
            created_at__date__gte=first_day,
            created_at__date__lte=last_day,
            amount__gt=0
        ).values('wallet__profile__user').distinct().count()
        
        retention_data.append({
            'month': i,
            'date': target_date,
            'revenue': int(cohort_revenue),
            'active_users': active_users,
            'retention_rate': (active_users / cohort_size * 100) if cohort_size > 0 else 0
        })
    
    return {
        'cohort_month': cohort_month,
        'cohort_size': cohort_size,
        'retention_data': retention_data
    }

