# apps/tournaments/signals.py
from __future__ import annotations

from typing import Optional

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver


def _get_field(obj, *candidates) -> Optional[object]:
    """
    Return the first attribute that exists and is not None among candidates.
    Example: _get_field(reg, 'user', 'user_profile')
    """
    for name in candidates:
        if hasattr(obj, name):
            val = getattr(obj, name)
            # also handle *_id style attributes (ForeignKey raw ID)
            if val is not None:
                return val
        # Try *_id explicitly if not yet returned
        id_name = f"{name}_id"
        if hasattr(obj, id_name):
            val = getattr(obj, id_name)
            if val is not None:
                return val
    return None


def _team_fk_present(reg) -> bool:
    return _get_field(reg, "team") is not None


def _user_fk_present(reg) -> bool:
    # Support either `user` or `user_profile` style schemas
    present = _get_field(reg, "user")
    if present is not None:
        return True
    present = _get_field(reg, "user_profile", "profile")
    return present is not None


def _mode_for_tournament(tournament) -> str:
    """
    Determine registration mode for a tournament.
    - 'team' if valorant_config exists
    - 'solo' if efootball_config exists
    - fallback to 'team' if game looks like 'valorant', else 'solo' if 'efootball'
    default to 'solo' if unsure (safer for paid flows to require individual)
    """
    # Prefer explicit related configs if present on your model
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

    # Sensible default
    return "solo"


def _valorant_expected_team_size(tournament) -> int:
    """
    Try to read per-tournament required team size from configs; fallback to 5.
    This is best-effort and will not raise if fields are absent.
    """
    default = 5
    cfg = getattr(tournament, "valorant_config", None)
    if cfg:
        for name in ("team_size", "roster_size", "required_players"):
            if hasattr(cfg, name):
                val = getattr(cfg, name)
                if isinstance(val, int) and val > 0:
                    return val
    return default


def _count_team_players(team) -> Optional[int]:
    """
    Try to count current team players if the Teams app exists.
    Returns None if we cannot determine.
    """
    try:
        TeamMembership = apps.get_model("teams", "TeamMembership")
    except Exception:
        return None

    # Try common role fields; fallback to all members count
    try:
        qs = TeamMembership.objects.filter(team=team)
        # If role field exists and marks players/captains/subs, you can refine here.
        return qs.count()
    except Exception:
        return None


def _validate_registration_instance(reg) -> None:
    """
    Core validator enforcing Valorant (team) vs eFootball (solo) semantics.
    """
    tournament = getattr(reg, "tournament", None)
    if not tournament:
        # If tournament FK is missing, let model-level mandatory FK validation handle it.
        return

    mode = _mode_for_tournament(tournament)

    team_present = _team_fk_present(reg)
    user_present = _user_fk_present(reg)

    # Disallow both or neither
    if team_present and user_present:
        raise ValidationError("Registration cannot have both a team and a user; choose one.")
    if not team_present and not user_present:
        raise ValidationError("Registration must have either a team (team mode) or a user (solo mode).")

    if mode == "team":
        if not team_present:
            raise ValidationError("This tournament requires team registration (Valorant).")
        # Optional: best-effort team size check
        team_obj = getattr(reg, "team", None)
        if team_obj is not None:
            expected = _valorant_expected_team_size(tournament)
            count = _count_team_players(team_obj)
            if isinstance(count, int) and count > 0 and count < expected:
                raise ValidationError(f"Team must have at least {expected} players for Valorant.")
        # Ensure solo fields are clear (if they exist)
        for solo_name in ("user", "user_profile", "profile"):
            if hasattr(reg, solo_name):
                setattr(reg, solo_name, None)

    elif mode == "solo":
        if not user_present:
            raise ValidationError("This tournament requires individual registration (eFootball).")
        # Ensure team field is clear when in solo mode
        if hasattr(reg, "team"):
            setattr(reg, "team", None)


@receiver(pre_save)
def registration_pre_save(sender, instance, **kwargs):
    """
    Global receiver: run only for the Registration model in tournaments app.
    """
    try:
        Registration = apps.get_model("tournaments", "Registration")
    except Exception:
        return

    if sender is Registration:
        _validate_registration_instance(instance)


def connect() -> None:
    """
    Called by AppConfig.ready() to ensure signal module is imported.
    Nothing to do here; using @receiver(pre_save) is sufficient.
    """
    return
