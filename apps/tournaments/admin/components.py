# apps/tournaments/admin/components.py
from __future__ import annotations

from django.apps import apps as django_apps
from django.contrib import admin

# Import concrete model modules (avoid package-level re-export issues)
from apps.tournaments.models.tournament import Tournament
try:
    from apps.tournaments.models.tournament_settings import TournamentSettings as _TSModel  # preferred
except Exception:
    _TSModel = None  # will resolve lazily in the inline

# Game configs
from apps.game_efootball.models import EfootballConfig
from apps.game_valorant.models import ValorantConfig


def _present_fields(model) -> set[str]:
    return {f.name for f in model._meta.get_fields()}


def _only_existing(model, *names):
    fields = _present_fields(model)
    return [n for n in names if n in fields]


class EfootballConfigInline(admin.StackedInline):
    model = EfootballConfig
    can_delete = False
    extra = 0
    fk_name = "tournament"
    show_change_link = True


class ValorantConfigInline(admin.StackedInline):
    model = ValorantConfig
    can_delete = False
    extra = 0
    fk_name = "tournament"
    show_change_link = True


class TournamentSettingsInline(admin.StackedInline):
    """
    Inline for TournamentSettings with lazy model resolution.
    Fixes: AttributeError: 'NoneType' object has no attribute '_meta'
    when the package-level import doesn't expose TournamentSettings.
    """
    # Use module import if it worked, resolve lazily otherwise.
    model = _TSModel
    can_delete = False
    extra = 0
    show_change_link = True

    # Field groups
    _FORMAT = ("tournament_type",)
    _SCHEDULE = ("start_at", "end_at", "reg_open_at", "reg_close_at")
    _ENTRY = (
        "min_team_size", "max_team_size", "entry_fee_bdt",
        "prize_pool_bdt", "prize_type", "prize_distribution_text",
    )
    _CORE_TOGGLES = ("invite_only", "auto_check_in", "auto_schedule", "payment_gateway_enabled")
    _VISIBILITY = ("bracket_visibility", "region_lock", "check_in_open_mins", "check_in_close_mins")
    _MEDIA = ("banner", "rules_pdf", "stream_facebook_url", "stream_youtube_url", "discord_url")
    _PAYMENT_TYPES = ("bkash_receive_type", "nagad_receive_type", "rocket_receive_type")
    _PAYMENT = (
        "bkash_receive_number", "nagad_receive_number", "rocket_receive_number",
        "bank_instructions",
    )

    def __init__(self, parent_model, admin_site):
        # Resolve the model BEFORE Django’s base __init__ touches self.model._meta
        if self.model is None:
            self.model = django_apps.get_model("tournaments", "TournamentSettings")
        super().__init__(parent_model, admin_site)

    def get_fieldsets(self, request, obj=None):
        fsets = []

        def add(title, candidates):
            present = _only_existing(self.model, *candidates)
            if present:
                fsets.append((title, {"fields": tuple(present)}))

        add("Format", self._FORMAT)
        add("Schedule", self._SCHEDULE)
        add("Entry & Prize", self._ENTRY)
        add("Core Toggles", self._CORE_TOGGLES)
        add("Visibility & Region", self._VISIBILITY)
        add("Rules & Media", self._MEDIA)
        add("Payment Receiving Types", self._PAYMENT_TYPES)
        add("Receiving Accounts (Manual)", self._PAYMENT)
        return tuple(fsets) if fsets else None


class HasEntryFeeFilter(admin.SimpleListFilter):
    title = "Has entry fee"
    parameter_name = "has_fee"

    def lookups(self, request, model_admin):
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request, queryset):
        val = self.value()
        names = [f.name for f in Tournament._meta.get_fields()]
        if val == "yes":
            try:
                return queryset.filter(settings__entry_fee_bdt__gt=0)
            except Exception:
                pass
            if "entry_fee_bdt" in names:
                return queryset.filter(entry_fee_bdt__gt=0)
            return queryset.none()

        if val == "no":
            try:
                return queryset.filter(settings__entry_fee_bdt__isnull=True) | queryset.filter(settings__entry_fee_bdt=0)
            except Exception:
                pass
            if "entry_fee_bdt" in names:
                return queryset.filter(entry_fee_bdt__isnull=True) | queryset.filter(entry_fee_bdt=0)
            return queryset

        return queryset
