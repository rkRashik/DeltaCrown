from datetime import timedelta
from django.db import transaction

def _get_ts(tournament):
    """Pull TournamentSettings with sane defaults if absent."""
    s = getattr(tournament, "settings", None)
    return {
        "round_duration_mins": getattr(s, "round_duration_mins", 45),
        "round_gap_mins": getattr(s, "round_gap_mins", 10),
        "check_in_open_mins": getattr(s, "check_in_open_mins", 60),
        "check_in_close_mins": getattr(s, "check_in_close_mins", 15),
    }


@transaction.atomic
def auto_schedule_matches(tournament):
    """
    Assign start_at to all matches by round:
      round 1 -> tournament.start_at
      round N -> previous round + duration + gap
    """
    if not getattr(tournament, "start_at", None):
        raise ValueError("Tournament.start_at must be set before scheduling.")

    knobs = _get_ts(tournament)
    per_round = {}

    # ✅ Use your related_name="matches" (not match_set)
    qs = tournament.matches.all().order_by("round_no", "position", "id")
    if not qs.exists():
        return 0

    base = tournament.start_at
    max_round = qs.order_by("-round_no").first().round_no or 1

    for r in range(1, max_round + 1):
        if r == 1:
            per_round[r] = base
        else:
            prev = per_round[r - 1]
            per_round[r] = prev + timedelta(
                minutes=knobs["round_duration_mins"] + knobs["round_gap_mins"]
            )

    updated = 0
    for m in qs:
        target = per_round.get(m.round_no, base)
        if m.start_at != target:
            m.start_at = target
            m.save(update_fields=["start_at"])
            updated += 1
    return updated


def clear_schedule(tournament):
    """Remove scheduled times from all matches."""
    return tournament.matches.filter(start_at__isnull=False).update(start_at=None)


def get_checkin_window(match):
    """
    Returns (open_dt, close_dt) for a given match using TournamentSettings.
    Requires match.start_at. If absent, returns (None, None).
    """
    if not getattr(match, "start_at", None):
        return (None, None)
    tournament = match.tournament
    knobs = _get_ts(tournament)
    open_dt = match.start_at - timedelta(minutes=knobs["check_in_open_mins"])
    close_dt = match.start_at - timedelta(minutes=knobs["check_in_close_mins"])
    return (open_dt, close_dt)
