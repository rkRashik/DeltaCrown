# apps/game_valorant/forms.py
from __future__ import annotations
from typing import List, Dict, Any

from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps

from .models_registration import ValorantTeamInfo, ValorantPlayer
from apps.teams.utils import get_active_team

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
UserProfile = apps.get_model("user_profile", "UserProfile")
Team = apps.get_model("teams", "Team")
TeamMembership = apps.get_model("teams", "TeamMembership")

from apps.tournaments.services.registration import (  # type: ignore
    TeamRegistrationInput, register_valorant_team,
)

PAYMENT_METHOD_CHOICES = (
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("rocket", "Rocket"),
    ("bank", "Bank Transfer"),
)

def _entry_fee_bdt(tournament) -> float:
    settings = getattr(tournament, "settings", None)
    return float(getattr(settings, "entry_fee_bdt", 0) or 0)

class PlayerChunk(forms.Form):
    full_name = forms.CharField(max_length=120)
    riot_id = forms.CharField(max_length=32, help_text="Without tagline (e.g., DeltaCrownPro)")
    riot_tagline = forms.CharField(max_length=16, help_text="e.g., #APAC")
    discord = forms.CharField(max_length=64)
    role = forms.ChoiceField(choices=(("starter","Starter"),("sub","Substitute")))


class ValorantTeamForm(forms.Form):
    # Team selection / info
    team = forms.ChoiceField(choices=(), required=False, label="Use my existing team (captain only)")
    team_name = forms.CharField(max_length=120, required=False)
    team_tag = forms.CharField(max_length=10, required=False)
    team_logo = forms.ImageField(required=False)
    region = forms.CharField(max_length=48, required=False)

    # Agreements
    agree_captain_consent = forms.BooleanField(required=True)
    agree_rules = forms.BooleanField(required=True)
    agree_no_cheat = forms.BooleanField(required=True)
    agree_enforcement = forms.BooleanField(required=True)

    # Payment
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, required=False)
    payer_account_number = forms.CharField(max_length=32, required=False)
    payment_reference = forms.CharField(max_length=128, required=False, label="Transaction ID / Reference")
    amount_bdt = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    payment_proof = forms.ImageField(required=False)

    # Nested roster
    players: List[PlayerChunk] = []  # for typing

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop("tournament")
        self.request = kwargs.pop("request", None)
        self.entry_fee_bdt = kwargs.pop("entry_fee_bdt", _entry_fee_bdt(self.tournament))

        # Part A: auto-select active team for ValorantTeamForm
        try:
            u = getattr(self, "request", None) and getattr(self.request, "user", None)
            if u and hasattr(u, "is_authenticated") and u.is_authenticated:
                from django.apps import apps
                UserProfile = apps.get_model("user_profile", "UserProfile")
                prof = UserProfile.objects.filter(user=u).first()
                if prof:
                    from apps.teams.utils import get_active_team
                    _active = get_active_team(prof, "valorant")
                    if _active and "team" in self.fields:
                        self.fields["team"].initial = str(_active.id)
        except Exception:
            pass

# Require payment if fee > 0
        required = self.entry_fee_bdt > 0
        for f in ("payment_method", "payer_account_number", "payment_reference", "amount_bdt", "payment_proof"):
            self.fields[f].required = required

        # captain's teams
        u = getattr(self.request, "user", None)
        choices = [("", "—")]
        if getattr(u, "is_authenticated", False) and Team and TeamMembership and UserProfile:
            prof = UserProfile.objects.filter(user=u).first()
            if prof:
                caps = TeamMembership.objects.filter(profile=prof, role="CAPTAIN", status="ACTIVE").select_related("team")
                choices += [(m.team_id, f"{m.team.name} ({m.team.tag})") for m in caps]
        self.fields["team"].choices = choices

        # Build 7 player forms (max); UI can ignore extras
        self.players = [PlayerChunk(prefix=f"p{i}", data=self.data or None, files=self.files or None) for i in range(7)]

    def clean(self):
        cleaned = super().clean()
        u = getattr(self.request, "user", None)
        if not getattr(u, "is_authenticated", False):
            raise ValidationError("You must be logged in to register.")

        # Captain must select a team or provide name/tag
        team_choice = cleaned.get("team") or ""
        team_obj = None
        if team_choice and Team:
            try:
                team_obj = Team.objects.get(pk=int(team_choice))
            except Exception:
                raise ValidationError("Invalid team selection.")

        if not team_obj and not (cleaned.get("team_name") and cleaned.get("team_tag")):
            raise ValidationError("Provide team name + tag, or select an existing team.")

        # Captain-only check
        if team_obj and TeamMembership and UserProfile:
            prof = UserProfile.objects.filter(user=u).first()
            if not prof or not TeamMembership.objects.filter(team=team_obj, profile=prof, role="CAPTAIN", status="ACTIVE").exists():
                raise ValidationError("Only the team captain can register for Valorant.")

        # Players validation
        valid_chunks: List[Dict[str, Any]] = []
        starters = subs = 0
        for chunk in self.players:
            if not chunk.is_bound:
                continue
            if not any(chunk.data.get(f"{chunk.prefix}-{fld}") for fld in ("full_name","riot_id","discord","role")):
                continue  # empty row
            if not chunk.is_valid():
                raise ValidationError(f"Player block error: {chunk.errors.as_text()}")
            d = chunk.cleaned_data
            valid_chunks.append(d)
            if d["role"] == "starter":
                starters += 1
            else:
                subs += 1

        if starters < 5:
            raise ValidationError("You must list at least 5 starters.")
        if starters + subs > 7:
            raise ValidationError("Roster cannot exceed 7 players (5 starters + up to 2 subs).")
        if subs > 2:
            raise ValidationError("You can specify at most 2 substitutes.")

        cleaned["players"] = valid_chunks
        return cleaned

    def save(self):
        # Team: prefer chosen; otherwise create
        u = getattr(self.request, "user", None)
        prof = UserProfile.objects.filter(user=u).first() if (UserProfile and u and u.is_authenticated) else None

        team_obj = None
        team_choice = self.cleaned_data.get("team") or ""
        if team_choice and Team:
            try:
                team_obj = Team.objects.get(pk=int(team_choice))
            except Exception:
                team_obj = None

        if not team_obj and Team and prof:
            team_obj = Team.objects.create(
                name=self.cleaned_data["team_name"],
                tag=self.cleaned_data["team_tag"],
                captain=prof,
            )

        # Registration + PV
        reg = register_valorant_team(
            TeamRegistrationInput(
                tournament_id=int(self.tournament.id),
                team_id=int(team_obj.id),
                payment_method=self.cleaned_data.get("payment_method") or None,
                payment_reference=self.cleaned_data.get("payment_reference") or None,
                payer_account_number=self.cleaned_data.get("payer_account_number") or None,
                amount_bdt=float(self.cleaned_data["amount_bdt"]) if self.cleaned_data.get("amount_bdt") else None,
            )
        )

        # Snapshot Valorant team info + roster
        info = ValorantTeamInfo.objects.create(
            registration=reg,
            team_name=self.cleaned_data.get("team_name") or getattr(team_obj, "name", ""),
            team_tag=self.cleaned_data.get("team_tag") or getattr(team_obj, "tag", ""),
            team_logo=self.cleaned_data.get("team_logo"),
            region=self.cleaned_data.get("region") or "",
            agree_captain_consent=self.cleaned_data["agree_captain_consent"],
            agree_rules=self.cleaned_data["agree_rules"],
            agree_no_cheat=self.cleaned_data["agree_no_cheat"],
            agree_enforcement=self.cleaned_data["agree_enforcement"],
            payment_method=self.cleaned_data.get("payment_method") or "",
            payment_reference=self.cleaned_data.get("payment_reference") or "",
            amount_bdt=self.cleaned_data.get("amount_bdt") or 0,
            payment_proof=self.cleaned_data.get("payment_proof"),
        )

        for d in self.cleaned_data["players"]:
            ValorantPlayer.objects.create(
                team_info=info,
                full_name=d["full_name"],
                riot_id=d["riot_id"],
                riot_tagline=d["riot_tagline"],
                discord=d["discord"],
                role=d["role"],
            )
        return reg
