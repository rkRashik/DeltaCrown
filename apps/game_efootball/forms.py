# apps/game_efootball/forms.py
from __future__ import annotations
from decimal import Decimal
from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from .models_registration import EfootballSoloInfo, EfootballDuoInfo


def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None


Tournament = _get_model("tournaments", "Tournament")
Registration = _get_model("tournaments", "Registration")

# Services
from apps.tournaments.services.registration import (  # noqa
    register_efootball_player,
    register_efootball_solo_detailed,
    register_efootball_duo_detailed,
)


PAYMENT_METHOD_CHOICES = (
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("bank", "Bank Transfer"),
)


class EfootballSoloForm(forms.ModelForm):
    """
    Solo 1v1 registration. Creates Registration + Payment(pending) + EfootballSoloInfo.
    """
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, required=True)
    payment_reference = forms.CharField(max_length=128, required=True)
    amount_bdt = forms.DecimalField(required=True, max_digits=10, decimal_places=2)

    class Meta:
        model = EfootballSoloInfo
        fields = [
            "full_name", "ign", "email", "phone",
            "personal_team_name", "team_strength", "team_logo",
            "agree_rules", "agree_no_tools", "agree_no_double",
            "payment_method", "payment_reference", "amount_bdt",
        ]

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop("tournament")
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # force agreements required
        self.fields["agree_rules"].required = True
        self.fields["agree_no_tools"].required = True
        self.fields["agree_no_double"].required = True

    def clean_ign(self):
        ign = self.cleaned_data["ign"].strip()
        # Unique IGN for this tournament
        if Registration and EfootballSoloInfo:
            exists = EfootballSoloInfo.objects.filter(
                registration__tournament=self.tournament, ign__iexact=ign
            ).exists()
            if exists:
                raise ValidationError("This IGN already registered for this tournament.")
        return ign

    def clean_team_strength(self):
        strength = self.cleaned_data["team_strength"]
        # If the tournament config has a limit, enforce it
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
        user_id = self.request.user.id if self.request and self.request.user.is_authenticated else None
        reg = register_efootball_solo_detailed(
            tournament=self.tournament,
            user_id=user_id,
            solo_info=self.cleaned_data,
        )
        return reg


class EfootballDuoForm(forms.ModelForm):
    """
    2v2 registration. Creates Registration + Payment(pending) + EfootballDuoInfo,
    creates a Team entity and links two user profiles if present, sends emails.
    """
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, required=True)
    payment_reference = forms.CharField(max_length=128, required=True)
    amount_bdt = forms.DecimalField(required=True, max_digits=10, decimal_places=2)
    payment_proof = forms.ImageField(required=True)

    class Meta:
        model = EfootballDuoInfo
        fields = [
            "team_name", "team_logo",
            "captain_full_name", "captain_ign", "captain_email", "captain_phone",
            "mate_full_name", "mate_ign", "mate_email", "mate_phone",
            "agree_consent", "agree_rules", "agree_no_tools", "agree_no_multi_team",
            "payment_method", "payment_reference", "amount_bdt", "payment_proof",
        ]

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop("tournament")
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # agreements required
        for f in ("agree_consent", "agree_rules", "agree_no_tools", "agree_no_multi_team"):
            self.fields[f].required = True

    def clean(self):
        data = super().clean()
        # Anti-duplication: IGN uniqueness in this tournament
        cap_ign = data.get("captain_ign", "").strip()
        mate_ign = data.get("mate_ign", "").strip()

        # Check solo table
        if Registration and EfootballSoloInfo:
            if cap_ign and EfootballSoloInfo.objects.filter(
                registration__tournament=self.tournament, ign__iexact=cap_ign
            ).exists():
                raise ValidationError("Captain IGN is already registered in this tournament (solo).")
            if mate_ign and EfootballSoloInfo.objects.filter(
                registration__tournament=self.tournament, ign__iexact=mate_ign
            ).exists():
                raise ValidationError("Teammate IGN is already registered in this tournament (solo).")

        # Check duo table
        if Registration and EfootballDuoInfo:
            q = EfootballDuoInfo.objects.filter(registration__tournament=self.tournament)
            if cap_ign and q.filter(models.Q(captain_ign__iexact=cap_ign) | models.Q(mate_ign__iexact=cap_ign)).exists():
                raise ValidationError("Captain IGN already appears on another team in this tournament.")
            if mate_ign and q.filter(models.Q(captain_ign__iexact=mate_ign) | models.Q(mate_ign__iexact=mate_ign)).exists():
                raise ValidationError("Teammate IGN already appears on another team in this tournament.")

        return data

    def save(self):
        user_id = self.request.user.id if self.request and self.request.user.is_authenticated else None
        reg = register_efootball_duo_detailed(
            tournament=self.tournament,
            user_id=user_id,
            duo_info=self.cleaned_data,
            files=self.files,
        )
        return reg
