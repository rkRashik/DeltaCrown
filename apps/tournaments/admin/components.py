# apps/tournaments/admin/components.py
from __future__ import annotations

from django.contrib import admin

from apps.game_efootball.models import EfootballConfig
from apps.game_valorant.models import ValorantConfig
from ..models import Tournament, TournamentSettings


def _present_fields(model) -> set[str]:
    return {f.name for f in model._meta.get_fields()}


def _only_existing(model, *names):
    fields = _present_fields(model)
    return [n for n in names if n in fields]


# ---------------- Inlines ----------------

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
    Flexible inline that only shows fields that actually exist on your TournamentSettings model.
    This avoids admin errors if some fields are not present yet.
    """
    model = TournamentSettings
    can_delete = False
    extra = 0
    show_change_link = True

    # Candidate buckets drawn from your current inline & docs. Only present fields will render.
    _SCHEDULE = ("start_at", "end_at", "reg_open_at", "reg_close_at")
    _ENTRY = ("min_team_size", "max_team_size", "entry_fee_bdt", "entry_fee",
              "prize_pool_bdt", "prize_type", "prize_distribution_text")
    _CORE_TOGGLES = ("invite_only", "auto_check_in", "allow_substitutes",
                     "custom_format_enabled", "automatic_scheduling_enabled",
                     "payment_gateway_enabled")
    _VISIBILITY = ("bracket_visibility", "region_lock", "check_in_open_mins", "check_in_close_mins")
    _MEDIA = ("banner", "rules_pdf",
              "facebook_stream_url", "stream_facebook_url",
              "youtube_stream_url", "stream_youtube_url",
              "discord_link", "discord_url")
    _PAYMENT = ("bkash_receive_number", "nagad_receive_number",
                "rocket_receive_number", "bank_instructions")

    def get_fieldsets(self, request, obj=None):
        fsets = []
        def add(title, candidates):
            present = _only_existing(self.model, *candidates)
            if present:
                fsets.append((title, {"fields": tuple(present)}))

        add("Schedule", self._SCHEDULE)
        add("Entry & Prize", self._ENTRY)
        add("Core Toggles", self._CORE_TOGGLES)
        add("Visibility & Region", self._VISIBILITY)
        add("Rules & Media", self._MEDIA)
        add("Payments (Manual)", self._PAYMENT)
        return tuple(fsets) if fsets else None


# Optional list filter used by TournamentAdmin
class HasEntryFeeFilter(admin.SimpleListFilter):
    title = "Has entry fee"
    parameter_name = "has_fee"

    def lookups(self, request, model_admin):
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request, queryset):
        # Try related settings(entry_fee_bdt) first; fall back to legacy fields on Tournament
        yes, no = "yes", "no"
        val = self.value()
        names = [f.name for f in Tournament._meta.get_fields()]

        if val == yes:
            try:
                return queryset.filter(settings__entry_fee_bdt__gt=0)
            except Exception:
                pass
            if "entry_fee_bdt" in names:
                return queryset.filter(entry_fee_bdt__gt=0)
            if "entry_fee" in names:
                return queryset.filter(entry_fee__gt=0)
            return queryset.none()

        if val == no:
            try:
                return queryset.filter(settings__entry_fee_bdt__isnull=True) | queryset.filter(settings__entry_fee_bdt=0)
            except Exception:
                pass
            if "entry_fee_bdt" in names:
                return queryset.filter(entry_fee_bdt__isnull=True) | queryset.filter(entry_fee_bdt=0)
            if "entry_fee" in names:
                return queryset.filter(entry_fee__isnull=True) | queryset.filter(entry_fee=0)
            return queryset

        return queryset
