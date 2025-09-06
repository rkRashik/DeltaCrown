# apps/game_efootball/forms.py
from __future__ import annotations
from decimal import Decimal
from typing import Optional, List

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from .models_registration import EfootballSoloInfo, EfootballDuoInfo

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
UserProfile = apps.get_model("user_profile", "UserProfile")
Team = apps.get_model("teams", "Team")
TeamMembership = apps.get_model("teams", "TeamMembership")

from apps.tournaments.services.registration import (  # type: ignore
    SoloRegistrationInput, TeamRegistrationInput,
    register_efootball_player, register_valorant_team,
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


class EfootballSoloForm(forms.ModelForm):
    """
    Solo 1v1 registration:
      1) Creates Registration + PaymentVerification(pending)
      2) Creates EfootballSoloInfo snapshot
    """
    # Payment
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, required=False)
    payer_account_number = forms.CharField(max_length=32, required=False, help_text="Your bKash/Nagad/Rocket number")
    payment_reference = forms.CharField(max_length=128, required=False, label="Transaction ID / Reference")
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

        # If tournament has a fee, require payment fields
        required = self.entry_fee_bdt > 0
        for f in ("payment_method", "payer_account_number", "payment_reference", "amount_bdt"):
            self.fields[f].required = required

        # Prefill from profile
        u = getattr(self.request, "user", None)
        if getattr(u, "is_authenticated", False) and UserProfile:
            prof = UserProfile.objects.filter(user=u).first()
            if prof:
                self.fields["full_name"].initial = prof.display_name or (u.get_full_name() or u.username)
                self.fields["email"].initial = getattr(u, "email", "") or prof.contact_email or ""
                self.fields["phone"].initial = prof.phone or ""
                self.fields["ign"].initial = prof.efootball_id or ""

        # Agreements must be checked
        for f in ("agree_rules", "agree_no_tools", "agree_no_double"):
            self.fields[f].required = True

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
        # 1) Create Registration + PaymentVerification
        uid = self.request.user.id if self.request and getattr(self.request.user, "is_authenticated", False) else None
        reg = register_efootball_player(
            SoloRegistrationInput(
                tournament_id=int(self.tournament.id),
                user_id=int(uid),
                payment_method=self.cleaned_data.get("payment_method") or None,
                payment_reference=self.cleaned_data.get("payment_reference") or None,
                payer_account_number=self.cleaned_data.get("payer_account_number") or None,
                amount_bdt=float(self.cleaned_data["amount_bdt"]) if self.cleaned_data.get("amount_bdt") else None,
            )
        )
        # 2) Snapshot EfootballSoloInfo
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


class EfootballDuoForm(forms.ModelForm):
    """
    Duo (2v2) registration:
      1) Optionally choose an existing Team (captain-only) to auto-fill
      2) Creates Registration + PaymentVerification(pending) using team flow
      3) Creates EfootballDuoInfo snapshot
    """
    # Optional: captain can pick an existing team they lead
    use_team_id = forms.ChoiceField(required=False, label="Use my existing team", choices=())

    # Payment
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, required=False)
    payer_account_number = forms.CharField(max_length=32, required=False, help_text="Your bKash/Nagad/Rocket number")
    payment_reference = forms.CharField(max_length=128, required=False, label="Transaction ID / Reference")
    amount_bdt = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    payment_proof = forms.ImageField(required=False)

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

        # Populate 'use_team_id' choices if captain
        u = getattr(self.request, "user", None)
        if getattr(u, "is_authenticated", False) and Team and TeamMembership and UserProfile:
            prof = UserProfile.objects.filter(user=u).first()
            if prof:
                # captain memberships
                cap_memberships = TeamMembership.objects.filter(profile=prof, role="CAPTAIN", status="ACTIVE").select_related("team")
                self.fields["use_team_id"].choices = [("", "—")] + [(m.team_id, f"{m.team.name} ({m.team.tag})") for m in cap_memberships]

                # Prefill captain info from profile
                self.fields["captain_full_name"].initial = prof.display_name or (u.get_full_name() or u.username)
                self.fields["captain_email"].initial = getattr(u, "email", "") or prof.contact_email or ""
                self.fields["captain_phone"].initial = prof.phone or ""
                self.fields["captain_ign"].initial = prof.efootball_id or ""

        # If tournament has a fee, require payment fields
        required = self.entry_fee_bdt > 0
        for f in ("payment_method", "payer_account_number", "payment_reference", "amount_bdt", "payment_proof"):
            self.fields[f].required = required

        # Agreements required
        for f in ("agree_consent", "agree_rules", "agree_no_tools", "agree_no_multi_team"):
            self.fields[f].required = True

    def clean(self):
        data = super().clean()
        u = getattr(self.request, "user", None)
        if not getattr(u, "is_authenticated", False):
            raise ValidationError("You must be logged in to register.")

        # If captain picked a team, auto-fill from team & membership
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
            # Ensure the user is the captain of that team
            is_captain = TeamMembership.objects.filter(team=team, profile=prof, role="CAPTAIN", status="ACTIVE").exists()
            if not is_captain:
                raise ValidationError("Only the team captain can register this team.")

            # Auto-fill team & mate fields if possible (first ACTIVE non-captain member)
            data["team_name"] = data.get("team_name") or team.name
            data["team_logo"] = data.get("team_logo") or getattr(team, "logo", None)
            # Find any teammate
            mate_m = TeamMembership.objects.filter(team=team, status="ACTIVE").exclude(role="CAPTAIN").select_related("profile").first()
            if mate_m:
                mate_p = mate_m.profile
                data["mate_full_name"] = data.get("mate_full_name") or (mate_p.display_name or mate_p.user.username)
                data["mate_email"] = data.get("mate_email") or (mate_p.contact_email or mate_p.user.email or "")
                data["mate_phone"] = data.get("mate_phone") or (mate_p.phone or "")
                data["mate_ign"] = data.get("mate_ign") or (mate_p.efootball_id or "")

        # Duplicate IGN protections across solo/duo tables (you already had this logic)
        cap_ign = (data.get("captain_ign") or "").strip()
        mate_ign = (data.get("mate_ign") or "").strip()

        if Registration and EfootballSoloInfo:
            if cap_ign and EfootballSoloInfo.objects.filter(registration__tournament=self.tournament, ign__iexact=cap_ign).exists():
                raise ValidationError("Captain IGN is already registered in this tournament (solo).")
            if mate_ign and EfootballSoloInfo.objects.filter(registration__tournament=self.tournament, ign__iexact=mate_ign).exists():
                raise ValidationError("Teammate IGN is already registered in this tournament (solo).")

        if Registration and EfootballDuoInfo:
            q = EfootballDuoInfo.objects.filter(registration__tournament=self.tournament)
            from django.db import models
            if cap_ign and q.filter(models.Q(captain_ign__iexact=cap_ign) | models.Q(mate_ign__iexact=cap_ign)).exists():
                raise ValidationError("Captain IGN already appears on another team in this tournament.")
            if mate_ign and q.filter(models.Q(captain_ign__iexact=mate_ign) | models.Q(mate_ign__iexact=mate_ign)).exists():
                raise ValidationError("Teammate IGN already appears on another team in this tournament.")

        return data

    def save(self):
        # Create or use a Team if provided; then create Registration + PV
        uid = self.request.user.id if self.request and getattr(self.request.user, "is_authenticated", False) else None
        team_obj = None

        # Use existing team if chosen
        team_choice = self.cleaned_data.get("use_team_id")
        if team_choice and Team:
            try:
                team_obj = Team.objects.get(pk=int(team_choice))
            except Exception:
                team_obj = None

        # If no team, create a new simple team (captain = requester)
        if Team and not team_obj:
            prof = UserProfile.objects.filter(user_id=uid).first() if UserProfile else None
            if not prof:
                raise ValidationError("Profile not found for captain.")
            team_obj = Team.objects.create(name=self.cleaned_data["team_name"], tag=self.cleaned_data["team_name"][:10].upper(), captain=prof)
            # teammate membership may be added later in admin or via invites

        # Registration + PV via service (team flow so payer acct is persisted)
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

        # Snapshot duo details
        EfootballDuoInfo.objects.create(
            registration=reg,
            team_name=self.cleaned_data["team_name"],
            team_logo=self.cleaned_data.get("team_logo"),
            captain_full_name=self.cleaned_data["captain_full_name"],
            captain_ign=self.cleaned_data["captain_ign"],
            captain_email=self.cleaned_data["captain_email"],
            captain_phone=self.cleaned_data["captain_phone"],
            mate_full_name=self.cleaned_data["mate_full_name"],
            mate_ign=self.cleaned_data["mate_ign"],
            mate_email=self.cleaned_data["mate_email"],
            mate_phone=self.cleaned_data["mate_phone"],
            agree_consent=self.cleaned_data["agree_consent"],
            agree_rules=self.cleaned_data["agree_rules"],
            agree_no_tools=self.cleaned_data["agree_no_tools"],
            agree_no_multi_team=self.cleaned_data["agree_no_multi_team"],
            payment_method=self.cleaned_data.get("payment_method") or "",
            payment_reference=self.cleaned_data.get("payment_reference") or "",
            amount_bdt=self.cleaned_data.get("amount_bdt") or Decimal("0"),
            payment_proof=self.cleaned_data.get("payment_proof"),
        )
        return reg
