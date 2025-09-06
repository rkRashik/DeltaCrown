from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from django.apps import apps
from django.db import models
from django.utils import timezone

def recompute_team_stats(team) -> object:
    """Compute and persist a TeamStats snapshot from verified matches.
    Returns the created TeamStats instance.
    """
    Match = apps.get_model("tournaments", "Match")
    TeamStats = apps.get_model("teams", "TeamStats")
    qs = Match.objects.filter(state="VERIFIED").filter(models.Q(team_a=team) | models.Q(team_b=team))

    played = qs.count()
    wins = qs.filter(winner_team=team).count()
    losses = max(played - wins, 0)

    win_rate = Decimal("0.00")
    if played:
        win_rate = (Decimal(wins) * Decimal(100) / Decimal(played)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # streak: order by start_at or created_at desc and count consecutive wins or losses from latest
    last_matches = list(qs.order_by("-start_at", "-id")[:20])
    streak = 0
    for i, m in enumerate(last_matches):
        won = (getattr(m, "winner_team_id", None) == team.id)
        if i == 0:
            streak = 1 if won else -1
        else:
            if (streak > 0 and won) or (streak < 0 and not won):
                streak = streak + 1 if streak > 0 else streak - 1
            else:
                break

    snapshot = TeamStats.objects.create(
        team=team,
        matches_played=played,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        streak=streak,
    )
    return snapshot
