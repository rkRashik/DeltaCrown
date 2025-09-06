# apps/teams/utils.py
from __future__ import annotations
from typing import Optional
from django.apps import apps

def get_active_team(profile, game: str) -> Optional[object]:
    """Return the user's ACTIVE team for the given game (if any). Prefer captain."""
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    qs = TeamMembership.objects.filter(profile=profile, status='ACTIVE', team__game=game)
    cap_first = qs.filter(role='CAPTAIN').select_related('team').first()
    if cap_first:
        return cap_first.team
    any_active = qs.select_related('team').first()
    return any_active.team if any_active else None


def get_latest_preset(profile, game: str):
    """
    Returns the most recent team preset for the given profile+game.
    """
    if not profile or not game:
        return None
    if game == "efootball":
        Model = apps.get_model("teams", "EfootballTeamPreset")
    elif game == "valorant":
        Model = apps.get_model("teams", "ValorantTeamPreset")
    else:
        return None
    return Model.objects.filter(profile=profile).order_by("-created_at").first()
