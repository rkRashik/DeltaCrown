# apps/tournaments/admin/tournaments/inlines.py
from __future__ import annotations

from typing import List

from django.contrib import admin

from ...models import Match
from ...models_registration_policy import TournamentRegistrationPolicy


def _present_fields(model) -> set[str]:
    return {f.name for f in model._meta.get_fields()}


def _fields_if_exist(model, *names) -> List[str]:
    present = _present_fields(model)
    return [n for n in names if n in present]


def _mode_choices_for_game(game_value: str | None):
    if not game_value:
        return list(TournamentRegistrationPolicy.MODE_CHOICES)
    g = (game_value or "").strip().lower()
    if g == "valorant":
        return [(TournamentRegistrationPolicy.MODE_TEAM, "Team")]
    if g == "efootball":
        return [
            (TournamentRegistrationPolicy.MODE_SOLO, "Solo (1v1)"),
            (TournamentRegistrationPolicy.MODE_DUO, "Duo (2v2)"),
        ]
    return list(TournamentRegistrationPolicy.MODE_CHOICES)


class _DynamicFieldsInlineMixin:
    """Read-only inline that shows only fields that exist on the model."""
    _candidate_fields: List[str] = []

    def get_fields(self, request, obj=None):
        model_fields = {f.name for f in self.model._meta.get_fields()}
        fields = [f for f in self._candidate_fields if f in model_fields]
        if "id" in model_fields and "id" not in fields:
            fields.insert(0, "id")
        return fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class RegistrationInline(_DynamicFieldsInlineMixin, admin.TabularInline):
    extra = 0
    can_delete = False
    verbose_name_plural = "Registrations"
    model = None  # set dynamically
    _candidate_fields = ["user", "user_profile", "team", "status"]


class CompactMatchInline(_DynamicFieldsInlineMixin, admin.TabularInline):
    """
    Compact read-only snapshot of matches for this tournament.
    IMPORTANT: Do not slice the queryset here; Django admin filters by FK later.
    """
    extra = 0
    can_delete = False
    verbose_name_plural = "Match Snapshot"
    model = Match
    _candidate_fields = [
        "round_no", "position",
        "user_a", "user_b",
        "team_a", "team_b",
        "winner_user", "winner_team",
        "start_at",
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("round_no", "position")


class TournamentRegistrationPolicyInline(admin.StackedInline):
    model = TournamentRegistrationPolicy
    can_delete = False
    extra = 0
    fk_name = "tournament"

    def get_fields(self, request, obj=None):
        return _fields_if_exist(
            self.model,
            "mode",
            "team_size_min",
            "team_size_max", "allow_substitutes",
        )

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        try:
            base_fields = formset.form.base_fields
            if "registration_mode" in base_fields:
                base_fields["registration_mode"].choices = _mode_choices_for_game(
                    getattr(obj, "game", None)
                )
        except Exception:
            pass
        return formset


