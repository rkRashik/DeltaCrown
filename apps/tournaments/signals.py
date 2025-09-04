# apps/tournaments/signals.py
from __future__ import annotations

from typing import Optional

from django.apps import apps
from django.db.models.signals import post_save, pre_save
from django.core.exceptions import ValidationError


# ---------- helpers ----------

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


# ---------- receivers ----------

def _ensure_children_on_tournament_save(sender, instance, created, **kwargs):
    """
    Ensure TournamentSettings exists, and create the correct per-game config.
    """
    # Core settings
    try:
        TournamentSettings = apps.get_model("tournaments", "TournamentSettings")
        if not hasattr(instance, "settings") or getattr(instance, "settings", None) is None:
            TournamentSettings.objects.get_or_create(tournament=instance)
    except Exception:
        pass

    # Per-game config
    game_value = (getattr(instance, "game", "") or "").strip().lower()
    try:
        if "valorant" in game_value:
            ValorantConfig = apps.get_model("game_valorant", "ValorantConfig")
            ValorantConfig.objects.get_or_create(tournament=instance)
        elif "efootball" in game_value:
            EfootballConfig = apps.get_model("game_efootball", "EfootballConfig")
            EfootballConfig.objects.get_or_create(tournament=instance)
    except Exception:
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

    try:
        Registration = apps.get_model("tournaments", "Registration")
        pre_save.connect(
            _validate_registration_on_save,
            sender=Registration,
            dispatch_uid="tournaments.validate_registration_on_save",
        )
    except LookupError:
        pass


def _ensure_payment_verification_on_registration_save(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        PaymentVerification = apps.get_model("tournaments", "PaymentVerification")
        PaymentVerification.objects.get_or_create(registration=instance)
    except Exception:
        # If verification model not migrated yet, fail silent
        pass


def register_signals():
    """
    Called from AppConfig.ready() to attach signals.
    """
    Tournament = apps.get_model("tournaments", "Tournament")
    post_save.connect(
        _ensure_children_on_tournament_save,
        sender=Tournament,
        dispatch_uid="tournaments.ensure_children_on_tournament_save",
    )

    # Registration validators (already present from Part 1)
    try:
        Registration = apps.get_model("tournaments", "Registration")
        pre_save.connect(
            _validate_registration_on_save,
            sender=Registration,
            dispatch_uid="tournaments.validate_registration_on_save",
        )
        # NEW: auto-create PaymentVerification on Registration create
        post_save.connect(
            _ensure_payment_verification_on_registration_save,
            sender=Registration,
            dispatch_uid="tournaments.ensure_payment_verification_on_registration_save",
        )
    except LookupError:
        pass

