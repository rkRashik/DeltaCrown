# apps/tournaments/admin/components.py
from django.contrib import admin
from apps.game_efootball.models import EfootballConfig
from apps.game_valorant.models import ValorantConfig
from ..models import Tournament, TournamentSettings

# --- Inlines: show exactly one game config per tournament (plus settings) ---
class EfootballConfigInline(admin.StackedInline):
    model = EfootballConfig
    can_delete = False
    extra = 0
    fk_name = "tournament"


class ValorantConfigInline(admin.StackedInline):
    model = ValorantConfig
    can_delete = False
    extra = 0
    fk_name = "tournament"


class TournamentSettingsInline(admin.StackedInline):
    model = TournamentSettings
    can_delete = False
    extra = 0
    fieldsets = (
        ("Core Toggles", {
            "fields": (
                "invite_only", "auto_check_in", "allow_substitutes",
                "custom_format_enabled", "automatic_scheduling_enabled",
            )
        }),
        ("Visibility & Region", {
            "fields": (
                "bracket_visibility", "region_lock",
                "check_in_open_mins", "check_in_close_mins",
            ),
        }),
        ("Rules & Media", {
            "fields": (
                "rules_pdf", "facebook_stream_url",
                "youtube_stream_url", "discord_link",
            ),
        }),
        ("Payments (Manual)", {
            "fields": (
                "bkash_receive_number",
                "nagad_receive_number",
                "rocket_receive_number",
                "bank_instructions",
            )
        }),
    )


# Optional extra filter for “has entry fee”
class HasEntryFeeFilter(admin.SimpleListFilter):
    title = "Has entry fee"
    parameter_name = "has_fee"

    def lookups(self, request, model_admin):
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return (
                queryset.exclude(entry_fee_bdt__isnull=True).exclude(entry_fee_bdt=0)
                if "entry_fee_bdt" in [f.name for f in Tournament._meta.get_fields()]
                else queryset.exclude(entry_fee__isnull=True).exclude(entry_fee=0)
            )
        if val == "no":
            if "entry_fee_bdt" in [f.name for f in Tournament._meta.get_fields()]:
                return queryset.filter(entry_fee_bdt__isnull=True) | queryset.filter(entry_fee_bdt=0)
            return queryset.filter(entry_fee__isnull=True) | queryset.filter(entry_fee=0)
        return queryset
