# apps/tournaments/models/_bootstrap_monkeypatch.py
from __future__ import annotations
from django.apps import apps
from django.core.exceptions import ValidationError

def _attach_alias_properties():
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
    except LookupError:
        return
    # Alias .settings
    if not hasattr(Tournament, "settings"):
        def _get_settings(inst):
            return getattr(inst, "tournamentsettings", None)
        setattr(Tournament, "settings", property(_get_settings))
    # Alias .valorant_config
    if not hasattr(Tournament, "valorant_config"):
        def _get_vc(inst):
            return getattr(inst, "valorantconfig", None)
        setattr(Tournament, "valorant_config", property(_get_vc))
    # Alias .efootball_config
    if not hasattr(Tournament, "efootball_config"):
        def _get_ec(inst):
            return getattr(inst, "efootballconfig", None)
        setattr(Tournament, "efootball_config", property(_get_ec))

def _wrap_registration_save():
    # Enforce Valorant requires team; ensure PV; backfill team.game
    try:
        Registration = apps.get_model("tournaments", "Registration")
        PaymentVerification = apps.get_model("tournaments", "PaymentVerification")
    except LookupError:
        return
    orig_save = getattr(Registration, "save", None)
    if getattr(Registration, "_dc_save_wrapped", False):
        return
    def save(self, *args, **kwargs):
        tour = getattr(self, "tournament", None)
        if tour and getattr(tour, "game", None) == "valorant" and not getattr(self, "team_id", None):
            raise ValidationError({"team": "Team registration is required for Valorant tournaments."})
        is_new = self.pk is None
        rv = orig_save(self, *args, **kwargs) if orig_save else super(Registration, self).save(*args, **kwargs)
        if is_new:
            try:
                # PaymentVerification autocreate
                if PaymentVerification is not None:
                    PaymentVerification.objects.get_or_create(registration=self)
            except Exception:
                pass
            try:
                # Team.game backfill from Tournament.game
                team = getattr(self, "team", None)
                tour = getattr(self, "tournament", None)
                if team and tour and (getattr(team, "game", "") or "") == "":
                    team.game = getattr(tour, "game", "") or ""
                    try:
                        team.save(update_fields=["game"])
                    except Exception:
                        team.save()
            except Exception:
                pass
        return rv
    if orig_save:
        Registration.save = save
        Registration._dc_save_wrapped = True

def _wrap_tournament_save():
    # Ensure Settings and per-game config on create
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
    except LookupError:
        return
    try:
        ValorantConfig = apps.get_model("game_valorant", "ValorantConfig")
    except LookupError:
        ValorantConfig = None
    try:
        EfootballConfig = apps.get_model("game_efootball", "EfootballConfig")
    except LookupError:
        EfootballConfig = None

    orig_save = getattr(Tournament, "save", None)
    if getattr(Tournament, "_dc_save_wrapped", False):
        return
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        rv = orig_save(self, *args, **kwargs) if orig_save else super(Tournament, self).save(*args, **kwargs)
        if is_new:
            try:
                Settings = apps.get_model("tournaments", "TournamentSettings")
                if Settings is not None:
                    Settings.objects.get_or_create(tournament=self)
            except Exception:
                pass
            game = getattr(self, "game", None)
            if game == "valorant" and ValorantConfig is not None:
                try:
                    ValorantConfig.objects.get_or_create(tournament=self)
                except Exception:
                    pass
            if game == "efootball" and EfootballConfig is not None:
                try:
                    EfootballConfig.objects.get_or_create(tournament=self)
                except Exception:
                    pass
        return rv
    if orig_save:
        Tournament.save = save
        Tournament._dc_save_wrapped = True

# Apply all patches at import
_attach_alias_properties()
_wrap_registration_save()
_wrap_tournament_save()
