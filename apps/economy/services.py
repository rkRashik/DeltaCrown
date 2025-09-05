# apps/economy/services.py
from __future__ import annotations

from typing import Iterable, List, Optional

from django.apps import apps
from django.db import transaction

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
