from django.db import transaction
from apps.tournaments.models import Bracket, Match

def generate_bracket(tournament):
    """
    Idempotent: re-generate Round 1 only if bracket is not locked.
    Will be fully implemented in Part 6 (power-of-two padding, team/solo participants, etc.).
    """
    b = getattr(tournament, "bracket", None)
    if not b:
        b = Bracket.objects.create(tournament=tournament, is_locked=False)
    if b.is_locked:
        raise ValueError("Bracket is locked; cannot regenerate.")

    # TODO: Implement participant collection and pairing (Part 6).
    # For now: ensure no duplicate round-1 setup beyond a simple placeholder
    with transaction.atomic():
        tournament.matches.filter(round_no=1).delete()
        # Example seed (kept commented until Part 6):
        # Match.objects.create(tournament=tournament, round_no=1, best_of=1, participant_a="A", participant_b="B")
    return b

def admin_set_winner(match, who="a"):
    """
    Set winner and (later) propagate to next round.
    """
    if who not in ("a", "b"):
        raise ValueError("who must be 'a' or 'b'")
    match.winner = match.participant_a if who == "a" else match.participant_b
    match.state = "VERIFIED"
    match.save(update_fields=["winner", "state"])
    # TODO: propagate winner to next match in Part 6

def lock_bracket(tournament):
    b = getattr(tournament, "bracket", None)
    if not b:
        b = Bracket.objects.create(tournament=tournament, is_locked=True)
    else:
        b.is_locked = True
        b.save(update_fields=["is_locked"])
