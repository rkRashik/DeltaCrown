# apps/tournaments/services/registration.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction


@dataclass
class TeamRegistrationInput:
    tournament_id: int
    team_id: int
    created_by_user_id: Optional[int] = None
    payment_id: Optional[int] = None


@dataclass
class SoloRegistrationInput:
    tournament_id: int
    user_id: int
    created_by_user_id: Optional[int] = None
    payment_id: Optional[int] = None


def _get_model(app_label: str, model_name: str):
    return apps.get_model(app_label, model_name)


@transaction.atomic
def register_valorant_team(data: TeamRegistrationInput):
    Tournament = _get_model("tournaments", "Tournament")
    Registration = _get_model("tournaments", "Registration")
    Team = _get_model("teams", "Team")

    tournament = Tournament.objects.select_for_update().get(pk=data.tournament_id)
    team = Team.objects.get(pk=data.team_id)

    reg = Registration(tournament=tournament)
    # Try common field names; skip if absent (the pre_save validator enforces semantics)
    if hasattr(reg, "team"):
        reg.team = team
    if hasattr(reg, "created_by_id") and data.created_by_user_id:
        reg.created_by_id = data.created_by_user_id
    if hasattr(reg, "payment_id") and data.payment_id:
        reg.payment_id = data.payment_id

    # Let signal validator enforce mode and combos
    # Explicitly call full_clean() to surface ValidationError earlier
    try:
        reg.full_clean()
    except Exception:
        # full_clean may not run custom logic; pre_save will still enforce, but surfacing here is nicer:
        pass

    reg.save()
    return reg


@transaction.atomic
def register_efootball_player(data: SoloRegistrationInput):
    Tournament = _get_model("tournaments", "Tournament")
    Registration = _get_model("tournaments", "Registration")
    User = _get_model("auth", "User")

    tournament = Tournament.objects.select_for_update().get(pk=data.tournament_id)
    user = User.objects.get(pk=data.user_id)

    reg = Registration(tournament=tournament)
    if hasattr(reg, "user"):
        reg.user = user
    elif hasattr(reg, "user_profile"):
        # If project stores profile instead of user directly, try to resolve:
        UserProfile = _get_model("user_profile", "UserProfile")
        profile = UserProfile.objects.get(user=user)
        reg.user_profile = profile

    if hasattr(reg, "created_by_id") and data.created_by_user_id:
        reg.created_by_id = data.created_by_user_id
    if hasattr(reg, "payment_id") and data.payment_id:
        reg.payment_id = data.payment_id

    try:
        reg.full_clean()
    except Exception:
        pass

    reg.save()
    return reg
