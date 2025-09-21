from __future__ import annotations

from typing import List

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered

from ...models import Tournament

# idempotent unregister
try:
    admin.site.unregister(Tournament)
except NotRegistered:
    pass

from .inlines import (
    RegistrationInline,
    CompactMatchInline,
    TournamentRegistrationPolicyInline,
    _present_fields, _fields_if_exist,
)
from .mixins import AdminLinkMixin, ExportBracketMixin, ActionsMixin


@admin.register(Tournament)
class TournamentAdmin(AdminLinkMixin, ExportBracketMixin, ActionsMixin, admin.ModelAdmin):
    save_on_top = True
    search_fields = ("name", "slug")
    readonly_fields = (
        "link_bracket",
        "link_settings",
        "link_valorant_config",
        "link_efootball_config",
        "link_export_bracket",
        "link_force_regenerate",
        "bracket_json_preview",
    )

    class Media:
        css = {'all': ('admin/css/ckeditor5_fix.css',)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_superuser:
            return qs
        group_names = set(user.groups.values_list("name", flat=True))
        if "Valorant Organizer" in group_names:
            return qs.filter(game=Tournament.Game.VALORANT)
        if "eFootball Organizer" in group_names:
            return qs.filter(game=Tournament.Game.EFOOTBALL)
        return qs

    def get_list_display(self, request):
        fields = _present_fields(Tournament)
        cols: List[str] = ["id", "name"]
        if "game" in fields:
            cols.append("game")
        cols.append("status_column")
        cols.append("bracket_status_column")
        for name in ("reg_open_at", "reg_close_at", "start_at", "end_at"):
            if name in fields:
                cols.append(name)
        cols.append("fee_column")
        # Add slot information if slot_size field exists
        if "slot_size" in fields:
            cols.append("slots_column")
        return tuple(cols)

    def get_list_filter(self, request):
        try:
            from ..components import HasEntryFeeFilter
        except Exception:
            HasEntryFeeFilter = None
        fields = _present_fields(Tournament)
        lf = [name for name in ("game", "status", "start_at", "end_at") if name in fields]
        if HasEntryFeeFilter:
            lf.append(HasEntryFeeFilter)
        return tuple(lf)

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)} if "slug" in _present_fields(Tournament) else {}

    def get_date_hierarchy(self, request):
        return "start_at" if "start_at" in _present_fields(Tournament) else None

    def get_fieldsets(self, request, obj=None):
        fsets = []

        basics = _fields_if_exist(Tournament, "name", "slug", "game", "short_description")
        if basics:
            fsets.append(("Basics (required)", {"fields": tuple(basics), "description": "Required fields for every tournament."}))

        sched_rows = []
        pair1 = _fields_if_exist(Tournament, "start_at", "end_at")
        pair2 = _fields_if_exist(Tournament, "reg_open_at", "reg_close_at")
        if pair1:
            sched_rows.append(tuple(pair1))
        if pair2:
            sched_rows.append(tuple(pair2))
        # Add slot_size to schedule section
        slot_field = _fields_if_exist(Tournament, "slot_size")
        if slot_field:
            sched_rows.append(tuple(slot_field))
        if sched_rows:
            fsets.append(("Schedule & Capacity", {"fields": tuple(sched_rows), "description": "Tournament timing and registration limits. Set slot_size to limit registrations."}))

        entry = _fields_if_exist(Tournament, "entry_fee_bdt", "entry_fee", "bank_instructions")
        if entry:
            fsets.append(("Entry & Bank (optional)", {"fields": tuple(entry), "description": "Optional entry fee and payout helpers."}))

        links = ["link_export_bracket", "link_force_regenerate", "bracket_json_preview"]
        if obj is not None:
            if hasattr(obj, "bracket"):
                links.append("link_bracket")
            if hasattr(obj, "settings"):
                links.append("link_settings")
            if hasattr(obj, "valorant_config"):
                links.append("link_valorant_config")
            if hasattr(obj, "efootball_config"):
                links.append("link_efootball_config")
        fsets.append(("Advanced / Related (optional)", {"fields": tuple(links), "description": "Quick links to optional tools and related records."}))
        return tuple(fsets)

    def get_inline_instances(self, request, obj=None):
        instances = []

        instances.append(TournamentRegistrationPolicyInline(self.model, self.admin_site))

        try:
            from ..components import TournamentSettingsInline, ValorantConfigInline, EfootballConfigInline
        except Exception:
            TournamentSettingsInline = ValorantConfigInline = EfootballConfigInline = None

        if TournamentSettingsInline:
            instances.append(TournamentSettingsInline(self.model, self.admin_site))
        if ValorantConfigInline:
            instances.append(ValorantConfigInline(self.model, self.admin_site))
        if EfootballConfigInline:
            instances.append(EfootballConfigInline(self.model, self.admin_site))

        try:
            from ...models import Registration as _Registration
            class _RegInline(RegistrationInline):
                model = _Registration
            instances.append(_RegInline(self.model, self.admin_site))
        except Exception:
            pass

        instances.append(CompactMatchInline(self.model, self.admin_site))

        try:
            from apps.economy.admin import CoinPolicyInline
        except Exception:
            CoinPolicyInline = None
        if CoinPolicyInline:
            instances.append(CoinPolicyInline(self.model, self.admin_site))

        return instances

    @admin.display(description="Status")
    def status_column(self, obj: Tournament):
        if hasattr(obj, "status") and getattr(obj, "status"):
            return obj.status
        from django.utils import timezone
        now = timezone.now()
        if getattr(obj, "start_at", None) and getattr(obj, "end_at", None):
            if obj.start_at <= now <= obj.end_at:
                return "RUNNING"
            if obj.end_at < now:
                return "COMPLETED"
        return "—"

    @admin.display(description="Bracket")
    def bracket_status_column(self, obj: Tournament):
        b = getattr(obj, "bracket", None)
        if not b:
            return "—"
        return "Locked" if getattr(b, "is_locked", False) else "Unlocked"

    @admin.display(description="Entry Fee")
    def fee_column(self, obj: Tournament):
        if hasattr(obj, "entry_fee_bdt"):
            return getattr(obj, "entry_fee_bdt")
        if hasattr(obj, "entry_fee"):
            return getattr(obj, "entry_fee")
        return None

    @admin.display(description="Slots")
    def slots_column(self, obj: Tournament):
        try:
            return getattr(obj, "slots_text", None) or "No limit"
        except Exception:
            return "—"

    actions = (
        "action_generate_bracket_safe",
        "action_force_regenerate_bracket",
        "action_lock_bracket",
        "action_unlock_bracket",
        "action_auto_schedule",
        "action_clear_schedule",
        "action_award_participation",
        "action_award_placements",
    )
