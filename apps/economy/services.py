# apps/economy/services.py
from __future__ import annotations

from typing import List

from django.apps import apps
from django.db.models import Max

from .models import DeltaCrownWallet, DeltaCrownTransaction, CoinPolicy


def wallet_for(profile) -> DeltaCrownWallet:
    w, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
    return w


def award(
    *,
    profile,
    amount: int,
    reason: str,
    tournament=None,
    registration=None,
    match=None,
    note: str = "",
    metadata: dict | None = None,
) -> DeltaCrownTransaction:
    w = wallet_for(profile)
    tx = DeltaCrownTransaction.objects.create(
        wallet=w,
        amount=int(amount),
        reason=reason,
        note=note or "",
        tournament=tournament,
        registration=registration,
        match=match,
        metadata=metadata or {},
    )
    return tx


def award_participation_for_registration(registration):
    """
    Award participation coins when a registration is confirmed/paid.

    Idempotent:
      - If ANY participation transaction exists for this registration, do nothing.
        (Prevents duplicate award when both a signal and a manual call happen.)
    Team tournaments:
      - With the constraint updated to include wallet, we can award one per member.
    """
    # Idempotency guard: if already awarded once for this registration, stop.
    if DeltaCrownTransaction.objects.filter(
        registration=registration,
        reason=DeltaCrownTransaction.Reason.PARTICIPATION,
    ).exists():
        return None

    Tournament = apps.get_model("tournaments", "Tournament")
    CoinPolicy = apps.get_model("economy", "CoinPolicy")

    t = registration.tournament
    policy, _ = CoinPolicy.objects.get_or_create(tournament=t, defaults={})
    if not policy.enabled or policy.participation <= 0:
        return None

    game = (getattr(t, "game", "") or "").lower()

    if game == "valorant":
        team = getattr(registration, "team", None)
        if not team:
            return None
        awards = []
        active_members = team.memberships.filter(status="ACTIVE").select_related("profile")
        for mem in active_members:
            awards.append(
                award(
                    profile=mem.profile,
                    amount=policy.participation,
                    reason=DeltaCrownTransaction.Reason.PARTICIPATION,
                    tournament=t,
                    registration=registration,
                    note="Participation",
                    metadata={"team_id": team.id},
                )
            )
        return awards or None

    # default: solo
    profile = getattr(registration, "user", None)
    if not profile:
        return None
    return award(
        profile=profile,
        amount=policy.participation,
        reason=DeltaCrownTransaction.Reason.PARTICIPATION,
        tournament=t,
        registration=registration,
        note="Participation",
        metadata={},
    )


def _profiles_from_team(team) -> List:
    return [m.profile for m in team.memberships.filter(status="ACTIVE").select_related("profile")]


def _final_and_semis(tournament):
    Match = apps.get_model("tournaments", "Match")
    qs = Match.objects.filter(tournament=tournament)
    if not qs.exists():
        return None, []
    max_round = qs.aggregate(m=Max("round_no")).get("m") or 0
    final_qs = list(qs.filter(round_no=max_round).order_by("position"))
    semi_qs = list(qs.filter(round_no=max_round - 1).order_by("position")) if max_round >= 2 else []
    return (final_qs[0] if final_qs else None), semi_qs


def award_placements(tournament):
    policy, _ = CoinPolicy.objects.get_or_create(tournament=tournament, defaults={})
    if not policy.enabled:
        return []

    game = (getattr(tournament, "game", "") or "").lower()
    final, semis = _final_and_semis(tournament)
    if not final:
        return []

    awards = []

    if game == "valorant":
        winner_team = final.winner_team
        finalist_teams = [final.team_a, final.team_b]
        runner_team = [tm for tm in finalist_teams if tm and tm != winner_team][0] if winner_team else None

        if winner_team and policy.winner > 0:
            for p in _profiles_from_team(winner_team):
                awards.append(
                    award(
                        profile=p,
                        amount=policy.winner,
                        reason=DeltaCrownTransaction.Reason.WINNER,
                        tournament=tournament,
                        match=final,
                        note="Winner",
                        metadata={"team_id": winner_team.id},
                    )
                )

        if runner_team and policy.runner_up > 0:
            for p in _profiles_from_team(runner_team):
                awards.append(
                    award(
                        profile=p,
                        amount=policy.runner_up,
                        reason=DeltaCrownTransaction.Reason.RUNNER_UP,
                        tournament=tournament,
                        match=final,
                        note="Runner-up",
                        metadata={"team_id": runner_team.id},
                    )
                )

        if policy.top4 > 0 and semis:
            for m in semis:
                loser_team = None
                if m.winner_team:
                    other = m.team_a if m.winner_team == m.team_b else m.team_b
                    loser_team = other
                for p in _profiles_from_team(loser_team) if loser_team else []:
                    awards.append(
                        award(
                            profile=p,
                            amount=policy.top4,
                            reason=DeltaCrownTransaction.Reason.TOP4,
                            tournament=tournament,
                            match=m,
                            note="Top 4",
                            metadata={"team_id": getattr(loser_team, "id", None)},
                        )
                    )

    else:
        winner_profile = getattr(final, "winner_user", None)
        finalist_users = [final.user_a, final.user_b]
        runner_profile = [u for u in finalist_users if u and u != winner_profile][0] if winner_profile else None

        if winner_profile and policy.winner > 0:
            awards.append(
                award(
                    profile=winner_profile,
                    amount=policy.winner,
                    reason=DeltaCrownTransaction.Reason.WINNER,
                    tournament=tournament,
                    match=final,
                    note="Winner",
                )
            )

        if runner_profile and policy.runner_up > 0:
            awards.append(
                award(
                    profile=runner_profile,
                    amount=policy.runner_up,
                    reason=DeltaCrownTransaction.Reason.RUNNER_UP,
                    tournament=tournament,
                    match=final,
                    note="Runner-up",
                )
            )

        if policy.top4 > 0 and semis:
            for m in semis:
                loser = None
                if m.winner_user:
                    loser = m.user_a if m.winner_user == m.user_b else m.user_b
                if loser:
                    awards.append(
                        award(
                            profile=loser,
                            amount=policy.top4,
                            reason=DeltaCrownTransaction.Reason.TOP4,
                            tournament=tournament,
                            match=m,
                            note="Top 4",
                        )
                    )

    # refresh wallet cache
    for tx in awards:
        tx.wallet.recalc_and_save()
    return awards
