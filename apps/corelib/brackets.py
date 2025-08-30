from math import ceil, log2
from typing import List, Dict, Tuple
from django.db import transaction, models
from django.core.exceptions import ValidationError
from apps.tournaments.models import Bracket, Match, Registration
from apps.user_profile.models import UserProfile


# ----- helpers -----
def _best_of_for(tournament) -> int:
    # eFootball uses format_type "BOx"; Valorant uses best_of "BOx"
    if hasattr(tournament, "efootball_config"):
        m = tournament.efootball_config.format_type
        return int(m.replace("BO", "")) if m else 1
    if hasattr(tournament, "valorant_config"):
        m = tournament.valorant_config.best_of
        return int(m.replace("BO", "")) if m else 1
    return 1

def collect_participants(tournament) -> List[Dict]:
    """
    [{ "kind": "solo", "user": <UserProfile>, "label": "..."} |
     { "kind": "team", "team": <Team>, "label": "..."}], from CONFIRMED registrations
    """
    qs = Registration.objects.filter(tournament=tournament, status="CONFIRMED")
    parts = []
    for r in qs:
        if r.user_id:
            parts.append({"kind": "solo", "user": r.user, "label": r.user.display_name})
        elif r.team_id:
            parts.append({"kind": "team", "team": r.team, "label": f"{r.team.tag} — {r.team.name}"})
    return parts

def _next_power_of_two(n: int) -> int:
    return 1 if n <= 1 else 2 ** ceil(log2(n))

def _create_skeleton_matches(tournament, round_count: int, best_of: int):
    matches_by_round = {r: [] for r in range(1, round_count + 1)}
    for r in range(1, round_count + 1):
        slots = 2 ** (round_count - r)
        for pos in range(1, slots + 1):
            m = Match.objects.create(tournament=tournament, round_no=r, position=pos, best_of=best_of)
            matches_by_round[r].append(m)
    return matches_by_round

def _assign_round1(matches_round1: List[Match], participants: List[Dict]):
    # deterministic order; add byes implicitly if list shorter than capacity
    idx = 0
    for m in matches_round1:
        pA = participants[idx] if idx < len(participants) else None
        pB = participants[idx + 1] if idx + 1 < len(participants) else None
        idx += 2
        if pA:
            (m.__setattr__("user_a", pA["user"]) if pA["kind"] == "solo" else m.__setattr__("team_a", pA["team"]))
        if pB:
            (m.__setattr__("user_b", pB["user"]) if pB["kind"] == "solo" else m.__setattr__("team_b", pB["team"]))
        m.full_clean(); m.save()

def _next_slot(round_no: int, position: int) -> Tuple[int, int]:
    # winner goes to (round_no+1, ceil(position/2))
    return round_no + 1, (position + 1) // 2

def _auto_advance_byes(tournament):
    """If a Round-1 match has only one side set, auto-mark winner and propagate."""
    first_round = tournament.matches.filter(round_no=1).order_by("position")
    for m in first_round:
        a_set = bool(m.user_a_id or m.team_a_id)
        b_set = bool(m.user_b_id or m.team_b_id)
        if a_set and not b_set:
            m.set_winner_side("a"); m.save(); _propagate_winner(tournament, m)
        elif b_set and not a_set:
            m.set_winner_side("b"); m.save(); _propagate_winner(tournament, m)

def _propagate_winner(tournament, match: Match):
    # stop at finals
    if match.round_no == tournament.matches.aggregate(models.Max("round_no"))["round_no__max"]:
        return
    nr, np = _next_slot(match.round_no, match.position)
    next_m = tournament.matches.get(round_no=nr, position=np)

    if match.winner_user_id:
        if next_m.user_a_id is None and next_m.team_a_id is None:
            next_m.user_a = match.winner_user
        elif next_m.user_b_id is None and next_m.team_b_id is None:
            next_m.user_b = match.winner_user
        else:
            return
    elif match.winner_team_id:
        if next_m.user_a_id is None and next_m.team_a_id is None:
            next_m.team_a = match.winner_team
        elif next_m.user_b_id is None and next_m.team_b_id is None:
            next_m.team_b = match.winner_team
        else:
            return
    next_m.full_clean(); next_m.save()

# ----- public API -----
@transaction.atomic
def generate_bracket(tournament):
    b = getattr(tournament, "bracket", None)
    if not b:
        b = Bracket.objects.create(tournament=tournament, is_locked=False)
    if b.is_locked:
        raise ValidationError("Bracket is locked; cannot regenerate.")

    # regen from scratch (idempotent while unlocked)
    tournament.matches.all().delete()

    parts = collect_participants(tournament)
    if not parts or len(parts) < 2:
        return b

    capacity = _next_power_of_two(len(parts))
    rounds = int(log2(capacity))
    best_of = _best_of_for(tournament)

    m_by_round = _create_skeleton_matches(tournament, rounds, best_of)
    _assign_round1(m_by_round[1], parts)
    _auto_advance_byes(tournament)
    return b

def report_result(match: Match, score_a: int, score_b: int, reporter: UserProfile):
    if match.is_solo_match:
        if reporter not in [match.user_a, match.user_b]:
            raise ValidationError("Not authorized to report this match.")
    else:
        captains = [match.team_a.captain if match.team_a else None, match.team_b.captain if match.team_b else None]
        if reporter not in [c for c in captains if c]:
            raise ValidationError("Only captains may report team matches.")

    # Check if the result is a draw
    if score_a == score_b:
        raise ValidationError("No draws allowed.")

    # Update match with scores
    match.score_a = score_a
    match.score_b = score_b

    # Determine the winner
    if score_a > score_b:
        match.winner_user = match.user_a if match.is_solo_match else match.team_a
        match.winner_team = None if match.is_solo_match else match.team_a
    else:
        match.winner_user = match.user_b if match.is_solo_match else match.team_b
        match.winner_team = None if match.is_solo_match else match.team_b

    match.state = "REPORTED"
    match.save()

    # Handle dispute flag
    if 'dispute' in match.__dict__ and match.dispute:
        match.state = "DISPUTED"  # Update state to disputed if there's a flag
        match.save()

    return match


def verify_and_apply(match: Match):
    match.state = "VERIFIED"
    match.save(update_fields=["state"])
    _propagate_winner(match.tournament, match)

def admin_set_winner(match: Match, who="a"):
    match.set_winner_side(who)
    match.save()
    _propagate_winner(match.tournament, match)
