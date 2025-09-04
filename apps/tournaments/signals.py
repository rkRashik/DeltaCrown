# apps/tournaments/signals.py
from __future__ import annotations

from typing import Optional

from django.apps import apps
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError


# ---------------- helpers (used by registration validator) ----------------

def _get_field(obj, *candidates) -> Optional[object]:
    for name in candidates:
        if hasattr(obj, name):
            val = getattr(obj, name)
            if val is not None:
                return val
        id_name = f"{name}_id"
        if hasattr(obj, id_name):
            val = getattr(obj, id_name)
            if val is not None:
                return val
    return None


def _team_fk_present(reg) -> bool:
    return _get_field(reg, "team") is not None


def _user_fk_present(reg) -> bool:
    present = _get_field(reg, "user")
    if present is not None:
        return True
    present = _get_field(reg, "user_profile", "profile")
    return present is not None


def _mode_for_tournament(tournament) -> str:
    # Prefer explicit related configs if present
    if hasattr(tournament, "valorant_config") and _get_field(tournament, "valorant_config"):
        return "team"
    if hasattr(tournament, "efootball_config") and _get_field(tournament, "efootball_config"):
        return "solo"

    # Fallback to text field
    game = getattr(tournament, "game", None)
    if isinstance(game, str):
        g = game.strip().lower()
        if "valorant" in g:
            return "team"
        if "efootball" in g or "e-football" in g or "e football" in g:
            return "solo"

    return "solo"


# ---------------- signal receivers ----------------

def _ensure_children_on_tournament_save(sender, instance, created, **kwargs):
    """
    Make sure core/settings & game-specific configs exist after saving a Tournament.
    """
    # Ensure TournamentSettings exists
    try:
        TournamentSettings = apps.get_model("tournaments", "TournamentSettings")
        if not hasattr(instance, "settings") or getattr(instance, "settings", None) is None:
            TournamentSettings.objects.get_or_create(tournament=instance)
    except Exception:
        # Settings model may not exist in some branches yet
        pass

    # Ensure per-game config exists
    game_value = (getattr(instance, "game", None) or "").strip().lower()
    try:
        if "valorant" in game_value:
            ValorantConfig = apps.get_model("game_valorant", "ValorantConfig")
            ValorantConfig.objects.get_or_create(tournament=instance)
        elif "efootball" in game_value:
            EfootballConfig = apps.get_model("game_efootball", "EfootballConfig")
            EfootballConfig.objects.get_or_create(tournament=instance)
    except Exception:
        # If the game app is disabled/missing, just skip
        pass


def _validate_registration_on_save(sender, instance, **kwargs):
    """
    Enforce solo vs team semantics for registrations.
    """
    tournament = getattr(instance, "tournament", None)
    if not tournament:
        return

    mode = _mode_for_tournament(tournament)
    team_present = _team_fk_present(instance)
    user_present = _user_fk_present(instance)

    # Disallow both or neither
    if team_present and user_present:
        raise ValidationError("Registration cannot have both a team and a user; choose one.")
    if not team_present and not user_present:
        raise ValidationError("Registration must have either a team (team mode) or a user (solo mode).")

    if mode == "team" and not team_present:
        raise ValidationError("This tournament requires team registration (team is missing).")
    if mode == "solo" and not user_present:
        raise ValidationError("This tournament requires solo registration (user is missing).")


def register_signals():
    """
    Called from AppConfig.ready() to attach signals using dynamic model lookups
    (avoids import order issues).
    """
    Tournament = apps.get_model("tournaments", "Tournament")
    post_save.connect(
        _ensure_children_on_tournament_save,
        sender=Tournament,
        dispatch_uid="tournaments.ensure_children_on_tournament_save",
    )

    # Hook Registration validator if model exists
    try:
        Registration = apps.get_model("tournaments", "Registration")
        pre_save.connect(
            _validate_registration_on_save,
            sender=Registration,
            dispatch_uid="tournaments.validate_registration_on_save",
        )
    except LookupError:
        pass
