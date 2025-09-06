# apps/tournaments/signals.py
from __future__ import annotations

from importlib import import_module
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save

_REGISTERED = False

# ----------------------------
# Helpers
# ----------------------------
def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None

# ----------------------------------------------
# Handlers: Tournament
# ----------------------------------------------
def _ensure_tournament_settings(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        Settings = apps.get_model("tournaments", "TournamentSettings")
        _safe(Settings.objects.get_or_create, tournament=instance)
    except LookupError:
        return

def _ensure_game_config_for_tournament(sender, instance, created, **kwargs):
    if not created:
        return
    game = getattr(instance, "game", None)
    if not game:
        return
    if game == "valorant":
        try:
            VC = apps.get_model("game_valorant", "ValorantConfig")
            _safe(VC.objects.get_or_create, tournament=instance)
        except LookupError:
            pass
    elif game == "efootball":
        try:
            EC = apps.get_model("game_efootball", "EfootballConfig")
            _safe(EC.objects.get_or_create, tournament=instance)
        except LookupError:
            pass

# ----------------------------------------------
# Handlers: Registration
# ----------------------------------------------
def _ensure_payment_verification(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        PV = apps.get_model("tournaments", "PaymentVerification")
        _safe(PV.objects.get_or_create, registration=instance)
    except LookupError:
        return

def _set_team_game_from_registration(sender, instance, created, **kwargs):
    if not created:
        return
    team = getattr(instance, "team", None)
    tour = getattr(instance, "tournament", None)
    current = (getattr(team, "game", "") or "") if team else ""
    if team and tour and current == "":
        team.game = getattr(tour, "game", "") or ""
        _safe(team.save, update_fields=["game"])

# Valorant is team-based — require team on Registration
def _validate_registration_mode(sender, instance, **kwargs):
    tour = getattr(instance, "tournament", None)
    if not tour:
        return
    game = getattr(tour, "game", None)
    if game == "valorant" and not getattr(instance, "team_id", None):
        raise ValidationError({"team": "Team registration is required for Valorant tournaments."})

# ----------------------------------------------
# Handlers: Config exclusivity
# ----------------------------------------------
def _validate_config_matches_game(sender, instance, **kwargs):
    tour = getattr(instance, "tournament", None)
    if not tour:
        return
    game = getattr(tour, "game", None)
    if sender.__name__ == "ValorantConfig" and game != "valorant":
        raise ValidationError({"tournament": "ValorantConfig is only allowed on valorant tournaments."})
    if sender.__name__ == "EfootballConfig" and game != "efootball":
        raise ValidationError({"tournament": "EfootballConfig is only allowed on efootball tournaments."})

# ----------------------------------------------
# Reverse attribute aliases on Tournament
# ----------------------------------------------
def _ensure_reverse_aliases():
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
    except LookupError:
        return
    # Property exists → hasattr(instance, "settings") becomes True
    if not hasattr(Tournament, "settings"):
        def _get_settings(inst):
            return getattr(inst, "tournamentsettings", None)
        setattr(Tournament, "settings", property(_get_settings))
    if not hasattr(Tournament, "valorant_config"):
        def _get_vc(inst):
            return getattr(inst, "valorantconfig", None)
        setattr(Tournament, "valorant_config", property(_get_vc))
    if not hasattr(Tournament, "efootball_config"):
        def _get_ec(inst):
            return getattr(inst, "efootballconfig", None)
        setattr(Tournament, "efootball_config", property(_get_ec))

# ------------------
# Public entry point
# ------------------
def register_signals() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    _REGISTERED = True

    # Reverse alias properties (class-level, immediate)
    _ensure_reverse_aliases()

    # Tournament hooks
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
        post_save.connect(_ensure_tournament_settings, sender=Tournament, dispatch_uid="tournaments.ensure_settings")
        post_save.connect(_ensure_game_config_for_tournament, sender=Tournament, dispatch_uid="tournaments.ensure_game_config")
    except LookupError:
        pass

    # Registration hooks
    try:
        Registration = apps.get_model("tournaments", "Registration")
        post_save.connect(_ensure_payment_verification, sender=Registration, dispatch_uid="tournaments.ensure_payment_verification")
        post_save.connect(_set_team_game_from_registration, sender=Registration, dispatch_uid="tournaments.set_team_game_from_registration")
        pre_save.connect(_validate_registration_mode, sender=Registration, dispatch_uid="tournaments.validate_registration_mode")
    except LookupError:
        pass

    # Config exclusivity
    try:
        ValorantConfig = apps.get_model("game_valorant", "ValorantConfig")
        pre_save.connect(_validate_config_matches_game, sender=ValorantConfig, dispatch_uid="tournaments.val_cfg_exclusive")
    except LookupError:
        pass
    try:
        EfootballConfig = apps.get_model("game_efootball", "EfootballConfig")
        pre_save.connect(_validate_config_matches_game, sender=EfootballConfig, dispatch_uid="tournaments.efb_cfg_exclusive")
    except LookupError:
        pass

    # Optional: coins on verification (best-effort)
    try:
        PaymentVerification = apps.get_model("tournaments", "PaymentVerification")
        def _maybe_award_coins_on_verification(sender, instance, created, **kwargs):
            try:
                status = getattr(instance, "status", None)
                if status not in ("VERIFIED", "APPROVED", "CONFIRMED"):
                    return
                svc = import_module("apps.economy.services.participation")
                if hasattr(svc, "award_participation_for_registration"):
                    reg = getattr(instance, "registration", None)
                    if reg is not None:
                        _safe(svc.award_participation_for_registration, reg)
            except Exception:
                pass
        post_save.connect(_maybe_award_coins_on_verification, sender=PaymentVerification, dispatch_uid="tournaments.maybe_award_coins")
    except LookupError:
        pass

# Ensure properties + connections as soon as module is imported
try:
    register_signals()
except Exception:
    pass
