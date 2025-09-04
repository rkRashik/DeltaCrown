# apps/tournaments/admin/policy.py
from __future__ import annotations
from django.contrib import admin
from ..models_registration_policy import TournamentRegistrationPolicy


@admin.register(TournamentRegistrationPolicy)
class TournamentRegistrationPolicyAdmin(admin.ModelAdmin):
    list_display = ("tournament", "mode", "team_size_min", "team_size_max")
    search_fields = ("tournament__name",)
