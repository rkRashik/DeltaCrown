# apps/game_efootball/forms.py
from __future__ import annotations
from decimal import Decimal
from typing import List

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from .models_registration import EfootballSoloInfo, EfootballDuoInfo
from apps.teams.utils import get_active_team

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
UserProfile = apps.get_model("user_profile", "UserProfile")
Team = apps.get_model("teams", "Team")
TeamMembership = apps.get_model("teams", "TeamMembership")

from apps.tournaments.services.registration import (  # type: ignore
    SoloRegistrationInput, TeamRegistrationInput,
    register_efootball_player, register_valorant_team,
)

# Optional presets model (behave gracefully if missing)
EfootballTeamPreset = apps.get_model("teams", "EfootballTeamPreset")

PAYMENT_METHOD_CHOICES = (
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("rocket", "Rocket"),
    ("bank", "Bank Transfer"),
)


def _entry_fee_bdt(tournament) -> float:
    settings = getattr(tournament, "settings", None)
    return float(getattr(settings, "entry_fee_bdt", 0) or 0)


# ------------------------------
# Solo (1v1)
# ------------------------------
class EfootballSoloForm(forms.ModelForm):
    # Payment
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, required=False)
    payer_account_number = forms.CharField(max_length=32, required=False, help_text="Your bKash/Nagad/Rocket number")
    payment_reference = forms.CharField(max_length=128, required=False, label="Transaction ID")
    amount_bdt = forms.DecimalField(required=False, max_digits=10, decimal_places=2)

    class Meta:
        model = EfootballSoloInfo
        fields = [
            "full_name", "ign", "email", "phone",
            "personal_team_name", "team_strength", "team_logo",
            "agree_rules", "agree_no_tools", "agree_no_double",
            "payment_method", "payer_account_number", "payment_reference", "amount_bdt",
        ]

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop("tournament")
        self.request = kwargs.pop("request", None)
        self.entry_fee_bdt = kwargs.pop("entry_fee_bdt", _entry_fee_bdt(self.tournament))
        super().__init__(*args, **kwargs)

        # Require payment if fee > 0
        required = self.entry_fee_bdt > 0
        for f in ("payment_method", "payer_account_number", "payment_reference", "amount_bdt"):
            self.fields[f].required = required

        # Prefill from profile
        u = getattr(self.request, "user", None)
        if getattr(u, "is_authenticated", False) and UserProfile:
            prof = UserProfile.objects.filter(user=u).first()
            if prof:
                self.fields["full_name"].initial = prof.display_name or (u.get_full_name() or u.username)
                self.fields["email"].initial = getattr(u, "email", "") or getattr(prof, "contact_email", "") or ""
                self.fields["phone"].initial = getattr(prof, "phone", "") or ""
                self.fields["ign"].initial = getattr(prof, "efootball_id", "") or ""

        # Agreements must be checked
        for f in ("agree_rules", "agree_no_tools", "agree_no_double"):
            self.fields[f].required = True

        # UI polish
        self.fields["full_name"].widget.attrs.update(placeholder="Your full name")
        self.fields["ign"].widget.attrs.update(placeholder="Your in-game name")
        self.fields["email"].widget.attrs.update(placeholder="Email (optional)")
        self.fields["phone"].widget.attrs.update(placeholder="Phone (optional)")
        self.fields["personal_team_name"].widget.attrs.update(placeholder="Optional")
        self.fields["team_strength"].widget.attrs.update(placeholder="Respect tournament cap")

    def clean_team_strength(self):
        strength = self.cleaned_data["team_strength"]
        limit = None
        cfg = getattr(self.tournament, "efootball_config", None)
        for name in ("max_team_strength", "team_strength_cap"):
            if cfg and hasattr(cfg, name):
                limit = getattr(cfg, name)
                break
        if limit and strength > int(limit):
            raise ValidationError(f"Team strength exceeds tournament limit of {limit}.")
        return strength

    def save(self):
        uid = self.request.user.id if self.request and getattr(self.request.user, "is_authenticated", False) else None
        reg = register_efootball_player(
            SoloRegistrationInput(
                tournament_id=int(self.tournament.id),
                user_id=int(uid) if uid is not None else None,
                payment_method=self.cleaned_data.get("payment_method") or None,
                payment_reference=self.cleaned_data.get("payment_reference") or None,
                payer_account_number=self.cleaned_data.get("payer_account_number") or None,
                amount_bdt=float(self.cleaned_data["amount_bdt"]) if self.cleaned_data.get("amount_bdt") else None,
            )
        )
        # Snapshot
        EfootballSoloInfo.objects.create(
            registration=reg,
            full_name=self.cleaned_data["full_name"],
            ign=self.cleaned_data["ign"],
            email=self.cleaned_data["email"],
            phone=self.cleaned_data["phone"],
            personal_team_name=self.cleaned_data["personal_team_name"],
            team_strength=self.cleaned_data["team_strength"],
            team_logo=self.cleaned_data.get("team_logo"),
            agree_rules=self.cleaned_data["agree_rules"],
            agree_no_tools=self.cleaned_data["agree_no_tools"],
            agree_no_double=self.cleaned_data["agree_no_double"],
            payment_method=self.cleaned_data.get("payment_method") or "",
            payment_reference=self.cleaned_data.get("payment_reference") or "",
            amount_bdt=self.cleaned_data.get("amount_bdt") or Decimal("0"),
        )
        return reg


# ------------------------------
# Duo (2v2) — presets + UX
# ------------------------------
class EfootballDuoForm(forms.ModelForm):
    # Optional: captain can pick an existing team they lead
    use_team_id = forms.ChoiceField(required=False, label="Use my existing team (captain only)", choices=())

    # Payment
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, required=False)
    payer_account_number = forms.CharField(max_length=32, required=False, help_text="Your bKash/Nagad/Rocket number")
    payment_reference = forms.CharField(max_length=128, required=False, label="Transaction ID")
    amount_bdt = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    payment_proof = forms.ImageField(required=False)

    # Preset
    save_as_preset = forms.BooleanField(required=False, initial=False, label="Save as my eFootball Team")

    class Meta:
        model = EfootballDuoInfo
        fields = [
            "team_name", "team_logo",
            "captain_full_name", "captain_ign", "captain_email", "captain_phone",
            "mate_full_name", "mate_ign", "mate_email", "mate_phone",
            "agree_consent", "agree_rules", "agree_no_tools", "agree_no_multi_team",
            "payment_method", "payer_account_number", "payment_reference", "amount_bdt", "payment_proof",
        ]

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop("tournament")
        self.request = kwargs.pop("request", None)
        self.entry_fee_bdt = kwargs.pop("entry_fee_bdt", _entry_fee_bdt(self.tournament))
        super().__init__(*args, **kwargs)

        # Payment required?
        required = self.entry_fee_bdt > 0
        for f in ("payment_method", "payer_account_number", "payment_reference", "amount_bdt", "payment_proof"):
            self.fields[f].required = required

        # Agreements required
        for f in ("agree_consent", "agree_rules", "agree_no_tools", "agree_no_multi_team"):
            self.fields[f].required = True

        # Make contact fields optional (even if model has blank=False)
        for f in ("captain_email", "captain_phone", "mate_email", "mate_phone"):
            if f in self.fields:
                self.fields[f].required = False

        # UI polish placeholders
        for fld, ph in [
            ("team_name", "If you don't pick an existing team"),
            ("captain_full_name", "e.g., Rahim Uddin"),
            ("captain_ign", "e.g., EF_Rahim"),
            ("captain_email", "Optional"),
            ("captain_phone", "Optional"),
            ("mate_full_name", "e.g., Karim Ali"),
            ("mate_ign", "e.g., EF_Karim"),
            ("mate_email", "Optional"),
            ("mate_phone", "Optional"),
        ]:
            self.fields[fld].widget.attrs.update(placeholder=ph)

        # Build captain's existing teams + active team preselect
        u = getattr(self.request, "user", None)
        prof = None
        _active = None
        choices = [("", "—")]
        if getattr(u, "is_authenticated", False) and Team and TeamMembership and UserProfile:
            prof = UserProfile.objects.filter(user=u).first()
            if prof:
                # Active team
                try:
                    _active = get_active_team(prof, "efootball")
                    if _active:
                        self.fields["use_team_id"].initial = str(_active.id)
                except Exception:
                    _active = None
                # Captain memberships
                cap_qs = (
                    TeamMembership.objects.filter(profile=prof, role="CAPTAIN", status="ACTIVE")
                    .select_related("team")
                )
                choices += [(m.team_id, f"{m.team.name} ({m.team.tag})") for m in cap_qs]
                # Prefill captain from profile (will be overridden by preset below if present)
                self.fields["captain_full_name"].initial = prof.display_name or (u.get_full_name() or u.username)
                self.fields["captain_email"].initial = getattr(u, "email", "") or getattr(prof, "contact_email", "") or ""
                self.fields["captain_phone"].initial = getattr(prof, "phone", "") or ""
                self.fields["captain_ign"].initial = getattr(prof, "efootball_id", "") or ""
        self.fields["use_team_id"].choices = choices

        # Prefill from latest eFootball preset if NO active team — override prior initials
        try:
            if EfootballTeamPreset and prof and not self.fields.get("use_team_id").initial:
                ep = (
                    EfootballTeamPreset.objects.filter(profile=prof)
                    .order_by("-created_at")
                    .first()
                )
                if ep:
                    self.fields["team_name"].initial = ep.team_name or self.fields["team_name"].initial
                    self.fields["captain_full_name"].initial = ep.captain_name or self.fields["captain_full_name"].initial
                    self.fields["captain_ign"].initial = ep.captain_ign or self.fields["captain_ign"].initial
                    self.fields["mate_full_name"].initial = ep.mate_name or self.fields["mate_full_name"].initial
                    self.fields["mate_ign"].initial = ep.mate_ign or self.fields["mate_ign"].initial
        except Exception:
            # Soft-fail to keep form usable
            pass

    def clean(self):
        data = super().clean()
        u = getattr(self.request, "user", None)
        if not getattr(u, "is_authenticated", False):
            raise ValidationError("You must be logged in to register.")

        # If captain picked a team, ensure captainship and gently fill missing mate details
        team_choice = data.get("use_team_id") or ""
        if team_choice and Team and TeamMembership and UserProfile:
            try:
                team_id = int(team_choice)
            except ValueError:
                raise ValidationError("Invalid team selection.")
            team = Team.objects.filter(pk=team_id).first()
            if not team:
                raise ValidationError("Team not found.")

            prof = UserProfile.objects.filter(user=u).first()
            if not prof:
                raise ValidationError("Profile not found.")

            is_captain = TeamMembership.objects.filter(
                team=team, profile=prof, role="CAPTAIN", status="ACTIVE"
            ).exists()
            if not is_captain:
                raise ValidationError("Only the team captain can register this team.")

            # Fill team fields
            data["team_name"] = data.get("team_name") or team.name
            data["team_logo"] = data.get("team_logo") or getattr(team, "logo", None)

            # Try to fill mate from any active non-captain member
            mate_m = (
                TeamMembership.objects.filter(team=team, status="ACTIVE")
                .exclude(role="CAPTAIN")
                .select_related("profile")
                .first()
            )
            if mate_m:
                mate_p = mate_m.profile
                data["mate_full_name"] = data.get("mate_full_name") or (getattr(mate_p, "display_name", None) or mate_p.user.username)
                data["mate_email"] = data.get("mate_email") or (getattr(mate_p, "contact_email", None) or mate_p.user.email or "")
                data["mate_phone"] = data.get("mate_phone") or getattr(mate_p, "phone", "") or ""
                data["mate_ign"] = data.get("mate_ign") or getattr(mate_p, "efootball_id", "") or ""

        # Duplicate IGN protections across solo/duo
        cap_ign = (data.get("captain_ign") or "").strip()
        mate_ign = (data.get("mate_ign") or "").strip()

        if Registration and EfootballSoloInfo:
            if cap_ign and EfootballSoloInfo.objects.filter(
                registration__tournament=self.tournament, ign__iexact=cap_ign
            ).exists():
                raise ValidationError("Captain IGN is already registered in this tournament (solo).")
            if mate_ign and EfootballSoloInfo.objects.filter(
                registration__tournament=self.tournament, ign__iexact=mate_ign
            ).exists():
                raise ValidationError("Teammate IGN is already registered in this tournament (solo).")

        if Registration and EfootballDuoInfo:
            from django.db import models
            q = EfootballDuoInfo.objects.filter(registration__tournament=self.tournament)
            if cap_ign and q.filter(models.Q(captain_ign__iexact=cap_ign) | models.Q(mate_ign__iexact=cap_ign)).exists():
                raise ValidationError("Captain IGN already appears on another team in this tournament.")
            if mate_ign and q.filter(models.Q(captain_ign__iexact=mate_ign) | models.Q(mate_ign__iexact=mate_ign)).exists():
                raise ValidationError("Teammate IGN already appears on another team in this tournament.")

        # Ensure either a picked team or a new team name
        if not (data.get("use_team_id") or data.get("team_name")):
            raise ValidationError("Provide a team name or select an existing team.")
        return data

    def save(self):
        # Create or reuse a Team, then register via team-based service
        uid = self.request.user.id if self.request and getattr(self.request.user, "is_authenticated", False) else None
        team_obj = None

        # Use existing team if chosen
        team_choice = self.cleaned_data.get("use_team_id")
        if team_choice and Team:
            try:
                team_obj = Team.objects.get(pk=int(team_choice))
            except Exception:
                team_obj = None

        # If no team, create a simple team (captain = requester)
        if Team and not team_obj:
            prof = UserProfile.objects.filter(user_id=uid).first() if UserProfile else None
            if not prof:
                raise ValidationError("Profile not found for captain.")
            team_obj = Team.objects.create(
                name=self.cleaned_data["team_name"],
                tag=(self.cleaned_data["team_name"][:10].upper() if self.cleaned_data.get("team_name") else "EFBD"),
                captain=prof,
            )
            # Mark game if available
            try:
                if hasattr(team_obj, "game"):
                    team_obj.game = "efootball"
                    team_obj.save(update_fields=["game"])
            except Exception:
                pass
            # Attach logo if provided
            if hasattr(team_obj, "logo") and self.cleaned_data.get("team_logo"):
                team_obj.logo = self.cleaned_data["team_logo"]
                team_obj.save(update_fields=["logo"])

        # Registration + PV (team flow)
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

        # Snapshot details
        EfootballDuoInfo.objects.create(
            registration=reg,
            team_name=self.cleaned_data["team_name"],
            team_logo=self.cleaned_data.get("team_logo"),
            captain_full_name=self.cleaned_data["captain_full_name"],
            captain_ign=self.cleaned_data["captain_ign"],
            captain_email=self.cleaned_data.get("captain_email") or "",
            captain_phone=self.cleaned_data.get("captain_phone") or "",
            mate_full_name=self.cleaned_data["mate_full_name"],
            mate_ign=self.cleaned_data["mate_ign"],
            mate_email=self.cleaned_data.get("mate_email") or "",
            mate_phone=self.cleaned_data.get("mate_phone") or "",
            agree_consent=self.cleaned_data["agree_consent"],
            agree_rules=self.cleaned_data["agree_rules"],
            agree_no_tools=self.cleaned_data["agree_no_tools"],
            agree_no_multi_team=self.cleaned_data["agree_no_multi_team"],
            payment_method=self.cleaned_data.get("payment_method") or "",
            payment_reference=self.cleaned_data.get("payment_reference") or "",
            amount_bdt=self.cleaned_data.get("amount_bdt") or Decimal("0"),
            payment_proof=self.cleaned_data.get("payment_proof"),
        )

        # Save/update eFootball preset if requested
        try:
            if self.cleaned_data.get("save_as_preset") and EfootballTeamPreset:
                prof = UserProfile.objects.filter(user_id=uid).first() if UserProfile else None
                if prof:
                    ep, _ = EfootballTeamPreset.objects.get_or_create(profile=prof, name="My eFootball Team")
                    ep.team_name = self.cleaned_data.get("team_name") or getattr(team_obj, "name", "") or ""
                    if self.cleaned_data.get("team_logo"):
                        ep.team_logo = self.cleaned_data["team_logo"]
                    ep.captain_name = self.cleaned_data.get("captain_full_name") or ""
                    ep.captain_ign = self.cleaned_data.get("captain_ign") or ""
                    ep.mate_name = self.cleaned_data.get("mate_full_name") or ""
                    ep.mate_ign = self.cleaned_data.get("mate_ign") or ""
                    ep.save()
        except Exception:
            # Never block successful registration if preset save fails
            pass

        return reg
