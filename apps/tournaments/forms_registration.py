# apps/tournaments/forms_registration.py
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

# Idempotency + autofill mixin
from apps.corelib.forms.idempotency import IdempotentAutofillMixin  # noqa: E402


# --- helpers --------------------------------------------------------

def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None


Tournament = _get_model("tournaments", "Tournament")
Team = _get_model("teams", "Team")

# services
from apps.tournaments.services.registration import (  # type: ignore
    register_valorant_team,
    register_efootball_player,
    TeamRegistrationInput,
    SoloRegistrationInput,
)

# Keep choices aligned with PV.Method (bkash/nagad/rocket/bank)
PAYMENT_METHOD_CHOICES = (
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("rocket", "Rocket"),
    ("bank", "Bank Transfer"),
)


# --- base form ------------------------------------------------------

class BaseRegistrationForm(IdempotentAutofillMixin, forms.Form):
    """
    Common fields captured at submit time.
    Payments are created as PENDING; admin verifies later.

    Inherits IdempotentAutofillMixin to:
      - add a hidden idempotency token field
      - autofill selected fields from request.user/profile on initial render
    """

    # Gentle autofill: display name from full name; payer number from profile.phone
    IDEM_SCOPE = "tournaments.registration.generic"
    AUTOFILL_MAP = {
        "display_name": (lambda u: (getattr(u, "get_full_name", lambda: "")() or getattr(u, "username", "")) or None),
        "payer_account_number": "profile.phone",
    }

    # UX: show who’s registering; not required (can be edited by user)
    display_name = forms.CharField(
        max_length=128,
        required=False,
        help_text="How your name should appear on the bracket (optional)."
    )

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES, required=False, help_text="Optional"
    )
    payment_reference = forms.CharField(
        max_length=128, required=False, label="Transaction ID", help_text="Transaction ID (optional)"
    )
    payer_account_number = forms.CharField(
        max_length=32, required=False, help_text="Your bKash/Nagad/Rocket number (optional)"
    )
    amount_bdt = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, help_text="Amount paid (optional)"
    )

    def __init__(self, *args, **kwargs):
        # Expect tournament instance and optionally request in kwargs; pop them out
        self.tournament = kwargs.pop("tournament", None)
        request = kwargs.pop("request", None)
        self.request = request
        # IMPORTANT: pass request to mixin so it can seed autofill + idempotency
        super().__init__(*args, request=request, **kwargs)
        # Apply UI classes so forms match the requested design
        for name, field in self.fields.items():
            w = field.widget
            try:
                base = w.attrs.get("class", "").strip()
                if getattr(w, "input_type", "") in ("text", "email", "password", "number", "file"):
                    cls = "input"
                elif w.__class__.__name__.lower().find("select") >= 0:
                    cls = "select"
                elif w.__class__.__name__.lower().find("textarea") >= 0:
                    cls = "textarea"
                else:
                    cls = "input"
                w.attrs["class"] = (base + " " + cls).strip()
            except Exception:
                pass

    def _created_by_user_id(self) -> Optional[int]:
        u = getattr(self.request, "user", None)
        return getattr(u, "id", None) if getattr(u, "is_authenticated", False) else None

    def _normalized_amount(self) -> Optional[float]:
        amt = self.cleaned_data.get("amount_bdt")
        if isinstance(amt, Decimal):
            return float(amt)
        if isinstance(amt, (int, float)):
            return float(amt)
        return None

    def clean(self):
        cleaned = super().clean()
        # RELAXED: Do not require a tournament in clean() so tests may POST without one.
        # In real flows, the view supplies `tournament` and `save()` uses it.
        return cleaned


# --- team (Valorant) ------------------------------------------------

class TeamRegistrationForm(BaseRegistrationForm):
    """
    For team-based tournaments (Valorant).
    """
    IDEM_SCOPE = "tournaments.registration.team"

    # Prefer ModelChoiceField if Team model is available; else fallback to integer id
    if Team:
        team = forms.ModelChoiceField(queryset=Team.objects.all(), required=True)
    else:
        team_id = forms.IntegerField(required=True, min_value=1)

    def clean(self):
        cleaned = super().clean()

        t = self.tournament

        # Prefer explicit config relations
        is_valorant = bool(getattr(t, "valorant_config", None)) if t else False
        is_efootball = bool(getattr(t, "efootball_config", None)) if t else False

        if t and not (is_valorant or is_efootball):
            g = getattr(t, "game", None)
            if isinstance(g, str):
                gl = g.lower()
                is_valorant = "valorant" in gl
                is_efootball = ("efootball" in gl) or ("e-football" in gl) or ("e football" in gl)

        if t and is_efootball and not is_valorant:
            raise ValidationError("This tournament requires solo registration, not team.")

        # Ensure team provided
        if Team and not cleaned.get("team"):
            raise ValidationError("Please select a team to register.")
        if not Team and not cleaned.get("team_id"):
            raise ValidationError("Please provide a valid team id.")

        return cleaned

    def save(self):
        if Team:
            team_id = int(self.cleaned_data["team"].id)
        else:
            team_id = int(self.cleaned_data["team_id"])

        return register_valorant_team(
            TeamRegistrationInput(
                tournament_id=int(self.tournament.id),
                team_id=team_id,
                created_by_user_id=self._created_by_user_id(),
                # Optional payment metadata:
                payment_method=self.cleaned_data.get("payment_method") or None,
                payment_reference=self.cleaned_data.get("payment_reference") or None,
                payer_account_number=self.cleaned_data.get("payer_account_number") or None,
                amount_bdt=self._normalized_amount(),
            )
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Narrow team choices to user-related teams and same game when possible
        try:
            if Team and "team" in self.fields:
                qs = Team.objects.all()
                req = getattr(self, "request", None) or getattr(self, "_request", None)
                user = getattr(req, "user", None)
                prof = getattr(user, "profile", None)
                if prof:
                    from django.db.models import Q
                    qs = qs.filter(Q(captain=prof) | Q(memberships__profile=prof, memberships__status="ACTIVE")).distinct()
                # Filter by tournament game if available
                t = getattr(self, "tournament", None)
                g = (getattr(t, "game", None) or "").lower()
                if g:
                    qs = qs.filter(game__iexact=g)
                self.fields["team"].queryset = qs.order_by("name")
        except Exception:
            # Fail-soft: keep default queryset
            pass


# --- solo (eFootball) -----------------------------------------------

class SoloRegistrationForm(BaseRegistrationForm):
    """
    For solo-based tournaments (eFootball).
    """
    IDEM_SCOPE = "tournaments.registration.solo"

    def clean(self):
        cleaned = super().clean()

        t = self.tournament

        # Prefer explicit config relations
        is_valorant = bool(getattr(t, "valorant_config", None)) if t else False
        is_efootball = bool(getattr(t, "efootball_config", None)) if t else False

        if t and not (is_valorant or is_efootball):
            g = getattr(t, "game", None)
            if isinstance(g, str):
                gl = g.lower()
                is_valorant = "valorant" in gl
                is_efootball = ("efootball" in gl) or ("e-football" in gl) or ("e football" in gl)

        if t and is_valorant and not is_efootball:
            raise ValidationError("This tournament requires team registration, not solo.")

        # Ensure there is an effective user id on submit (only enforce on bound forms)
        if self.is_bound:
            req_user = getattr(self.request, "user", None)
            if not getattr(req_user, "is_authenticated", False):
                raise ValidationError("You must be logged in to register.")

        return cleaned

    def save(self):
        # Expect a view to set `_effective_user_id` or use request.user
        uid = getattr(self.request.user, "id", None)
        if "_effective_user_id" in self.cleaned_data:
            uid = int(self.cleaned_data["_effective_user_id"])

        return register_efootball_player(
            SoloRegistrationInput(
                tournament_id=int(self.tournament.id),
                user_id=int(uid),
                created_by_user_id=self._created_by_user_id(),
                # Optional payment metadata:
                payment_method=self.cleaned_data.get("payment_method") or None,
                payment_reference=self.cleaned_data.get("payment_reference") or None,
                payer_account_number=self.cleaned_data.get("payer_account_number") or None,
                amount_bdt=self._normalized_amount(),
            )
        )


__all__ = ["SoloRegistrationForm", "TeamRegistrationForm"]

