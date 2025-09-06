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
