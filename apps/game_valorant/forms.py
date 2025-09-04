# apps/game_valorant/forms.py
from __future__ import annotations
from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from .models_registration import ValorantTeamInfo, ValorantPlayer


Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")

from apps.tournaments.services.registration import (  # noqa
    register_valorant_team_detailed,
)


PAYMENT_METHOD_CHOICES = (
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("bank", "Bank Transfer"),
)

REGION_CHOICES = (
    ("APAC", "Asia Pacific"),
    ("EU", "Europe"),
    ("NA", "North America"),
    ("LATAM", "Latin America"),
)


class ValorantPlayerChunk(forms.Form):
    full_name = forms.CharField(max_length=120, required=True)
    riot_id = forms.CharField(max_length=32, required=True, help_text="Without #tagline")
    riot_tagline = forms.CharField(max_length=16, required=True)
    discord = forms.CharField(max_length=64, required=True)
    role = forms.ChoiceField(choices=(("starter", "Starter"), ("sub", "Substitute")), required=True)


class ValorantTeamForm(forms.ModelForm):
    """
    Team registration with roster (up to 7 players). Payment stays pending.
    """
    region = forms.ChoiceField(choices=REGION_CHOICES, required=True)
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, required=True)
    payment_reference = forms.CharField(max_length=128, required=True)
    amount_bdt = forms.DecimalField(required=True, max_digits=10, decimal_places=2)
    payment_proof = forms.ImageField(required=True)

    # up to 7 roster slots (P1 required; others optional)
    players = forms.JSONField(required=True, help_text="Array of up to 7 players")

    class Meta:
        model = ValorantTeamInfo
        fields = [
            "team_name", "team_tag", "team_logo", "region",
            "agree_captain_consent", "agree_rules", "agree_no_cheat", "agree_enforcement",
            "payment_method", "payment_reference", "amount_bdt", "payment_proof",
            "players",
        ]

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop("tournament")
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        for f in ("agree_captain_consent", "agree_rules", "agree_no_cheat", "agree_enforcement"):
            self.fields[f].required = True

    def clean_players(self):
        data = self.cleaned_data["players"]
        if not isinstance(data, list) or not data:
            raise ValidationError("Provide at least 1 player (captain).")
        if len(data) > 7:
            raise ValidationError("Maximum 7 players allowed (5 starters + 2 subs).")

        # Validate chunkwise
        cleaned = []
        for i, entry in enumerate(data):
            chunk = ValorantPlayerChunk(entry)
            if not chunk.is_valid():
                raise ValidationError(f"Player {i+1}: {chunk.errors.as_text()}")
            cleaned.append(chunk.cleaned_data)
        return cleaned

    def save(self):
        user_id = self.request.user.id if self.request and self.request.user.is_authenticated else None
        reg = register_valorant_team_detailed(
            tournament=self.tournament,
            user_id=user_id,
            team_info=self.cleaned_data,
            files=self.files,
        )
        return reg
