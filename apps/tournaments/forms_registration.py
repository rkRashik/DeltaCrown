# apps/tournaments/forms_registration.py
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError


def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None


Tournament = _get_model("tournaments", "Tournament")
Team = _get_model("teams", "Team")

# Optional models, used defensively
User = _get_model("auth", "User")

# Use service layer so all business rules live in one place
from apps.tournaments.services.registration import (  # noqa: E402
    register_valorant_team,
    register_efootball_player,
    TeamRegistrationInput,
    SoloRegistrationInput,
)

PAYMENT_METHOD_CHOICES = (
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("rocket", "Rocket"),
    ("bank", "Bank Transfer"),
)


class BaseRegistrationForm(forms.Form):
    """
    Common fields captured at submit time.
    Payments are created as PENDING; admin verifies later.
    """
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES, required=False, help_text="Optional"
    )
    payment_reference = forms.CharField(
        max_length=128, required=False, help_text="Transaction ID / Reference (optional)"
    )
    amount_bdt = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, help_text="Amount paid (optional)"
    )

    def __init__(self, *args, **kwargs):
        # Expect tournament instance and optionally request in kwargs; pop them out
        self.tournament = kwargs.pop("tournament", None)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if not self.tournament or (Tournament and not isinstance(self.tournament, Tournament)):
            raise ValueError("BaseRegistrationForm requires a `tournament` instance.")

    def _normalized_amount(self) -> Optional[Decimal]:
        amt = self.cleaned_data.get("amount_bdt")
        if amt in (None, ""):
            return None
        try:
            return Decimal(amt)
        except Exception:
            return None

    # Useful helpers shared by subclasses
    def _created_by_user_id(self) -> Optional[int]:
        if self.request and hasattr(self.request, "user") and getattr(self.request.user, "is_authenticated", False):
            try:
                return int(self.request.user.id)
            except Exception:
                return None
        return None


class TeamRegistrationForm(BaseRegistrationForm):
    """
    For team-based tournaments (Valorant).
    """
    # Prefer ModelChoiceField if Team model is available; else fallback to integer id
    if Team:
        team = forms.ModelChoiceField(queryset=Team.objects.all(), required=True)
    else:
        team_id = forms.IntegerField(required=True, min_value=1)

    def clean(self):
        cleaned = super().clean()

        # Determine mode from tournament – Valorant = team mode
        # If eFootball config exists (solo), block team registration here.
        t = self.tournament

        # Prefer explicit config relations if present
        is_valorant = bool(getattr(t, "valorant_config", None))
        is_efootball = bool(getattr(t, "efootball_config", None))

        if not (is_valorant or is_efootball):
            # Fallback to textual game field if relations are missing
            g = getattr(t, "game", None)
            if isinstance(g, str):
                gl = g.lower()
                is_valorant = "valorant" in gl
                is_efootball = ("efootball" in gl) or ("e-football" in gl) or ("e football" in gl)

        if is_efootball and not is_valorant:
            raise ValidationError("This tournament requires individual (solo) registration, not team.")

        # Ensure team provided
        if Team and not cleaned.get("team"):
            raise ValidationError("Please select a team to register.")
        if not Team and not cleaned.get("team_id"):
            raise ValidationError("Please provide a valid team id.")

        return cleaned

    def save(self):
        """
        Create a Valorant team registration via service layer.
        Payment (if provided) is created with status='pending'.
        """
        if Team:
            team_obj = self.cleaned_data["team"]
            team_id = int(team_obj.id)
        else:
            team_id = int(self.cleaned_data["team_id"])

        return register_valorant_team(
            TeamRegistrationInput(
                tournament_id=int(self.tournament.id),
                team_id=team_id,
                created_by_user_id=self._created_by_user_id(),
                payment_method=self.cleaned_data.get("payment_method") or None,
                payment_reference=self.cleaned_data.get("payment_reference") or None,
                amount_bdt=self._normalized_amount(),
            )
        )


class SoloRegistrationForm(BaseRegistrationForm):
    """
    For solo-based tournaments (eFootball).
    Uses the current authenticated user by default; can accept `user_id` when no request context.
    """
    user_id = forms.IntegerField(required=False, min_value=1, help_text="Optional; will use request.user if missing")

    def clean(self):
        cleaned = super().clean()

        t = self.tournament

        # Prefer explicit config relations
        is_valorant = bool(getattr(t, "valorant_config", None))
        is_efootball = bool(getattr(t, "efootball_config", None))

        if not (is_valorant or is_efootball):
            g = getattr(t, "game", None)
            if isinstance(g, str):
                gl = g.lower()
                is_valorant = "valorant" in gl
                is_efootball = ("efootball" in gl) or ("e-football" in gl) or ("e football" in gl)

        if is_valorant and not is_efootball:
            raise ValidationError("This tournament requires team registration (Valorant).")

        # Determine user id: prefer request.user; else require user_id field
        uid = None
        if self.request and getattr(self.request, "user", None) and getattr(self.request.user, "is_authenticated", False):
            try:
                uid = int(self.request.user.id)
            except Exception:
                uid = None
        if uid is None:
            uid = self.cleaned_data.get("user_id")
            if not uid:
                raise ValidationError("User not specified. Please sign in or provide user_id.")

        # Validate user existence if possible
        if uid and User:
            try:
                User.objects.only("id").get(pk=uid)
            except Exception:
                raise ValidationError("User account not found.")

        self.cleaned_data["_effective_user_id"] = uid
        return cleaned

    def save(self):
        """
        Create an eFootball solo registration via service layer.
        Payment (if provided) is created with status='pending'.
        """
        uid = int(self.cleaned_data["_effective_user_id"])
        return register_efootball_player(
            SoloRegistrationInput(
                tournament_id=int(self.tournament.id),
                user_id=uid,
                created_by_user_id=self._created_by_user_id(),
                payment_method=self.cleaned_data.get("payment_method") or None,
                payment_reference=self.cleaned_data.get("payment_reference") or None,
                amount_bdt=self._normalized_amount(),
            )
        )


__all__ = ["SoloRegistrationForm", "TeamRegistrationForm"]
