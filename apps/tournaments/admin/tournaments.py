# apps/tournaments/admin/tournaments.py
from __future__ import annotations

from django.contrib import admin, messages
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.utils.html import format_html

from ..models import Tournament, Registration, Bracket, Match
from ..services import analytics as analytics_svc
from .components import (
    EfootballConfigInline,
    ValorantConfigInline,
    TournamentSettingsInline,
    HasEntryFeeFilter,
)
from .utils import safe_select_related, _safe_message


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """
    Tournament admin with defensive select_related to avoid FieldError
    when models don't have optional relations like 'owner'/'created_by'.
    """
    list_display = (
        "name", "status",
        "starts", "ends",
        "slots", "fee", "pool",
        "analytics_link",
    )
    list_filter = ("status", HasEntryFeeFilter)
    search_fields = ("name", "slug")

    # These are *desired* relations; we will filter to only those that exist.
    list_select_related = ("settings", "valorant_config", "efootball_config", "bracket")

    inlines = [TournamentSettingsInline, EfootballConfigInline, ValorantConfigInline]

    # actions are kept as module-level functions (see bottom) for admin/base.py imports

    # ---- queryset ----
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Some legacy code (or mixins) used to try: owner/created_by. Add them as "desired",
        # then filter to only real relations to prevent FieldError.
        desired = list(self.list_select_related) + ["owner", "created_by"]
        return safe_select_related(qs, self.model, desired)

    # ---- computed columns ----
    @admin.display(description="Starts")
    def starts(self, obj: Tournament):
        for name in ("start_at", "start_date", "starts_at"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val:
                    return val
        return "—"

    @admin.display(description="Ends")
    def ends(self, obj: Tournament):
        for name in ("end_at", "end_date", "ends_at"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val:
                    return val
        return "—"

    @admin.display(description="Slots")
    def slots(self, obj: Tournament):
        for name in ("slot_size", "max_slots", "max_participants"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val not in (None, ""):
                    return val
        # Fallback: count confirmed registrations
        try:
            return Registration.objects.filter(tournament=obj, status="CONFIRMED").count()
        except Exception:
            return "—"

    @admin.display(description="Entry Fee (BDT)")
    def fee(self, obj: Tournament):
        for name in ("entry_fee_bdt", "entry_fee", "fee_bdt", "fee"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val not in (None, ""):
                    return val
        return "—"

    @admin.display(description="Prize Pool (BDT)")
    def pool(self, obj: Tournament):
        for name in ("prize_pool_bdt", "prize_pool", "pool_bdt", "pool"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val not in (None, ""):
                    return val
        return "—"

    # ---- analytics ----
    @admin.display(description="Analytics")
    def analytics_link(self, obj: Tournament):
        try:
            url = reverse("tournament_analytics", args=[obj.pk])
        except Exception:
            # In case the URL name is namespaced under admin site, try fallback:
            try:
                url = reverse("admin:tournament_analytics", args=[obj.pk])
            except Exception:
                return "—"
        return format_html('<a href="{}">Open</a>', url)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "tournaments/<int:pk>/analytics/",
                self.admin_site.admin_view(self.analytics_view),
                name="tournament_analytics",
            )
        ]
        return custom + urls

    def analytics_view(self, request, pk: int):
        obj = Tournament.objects.filter(pk=pk).first()
        if not obj:
            _safe_message(self, request, "Tournament not found.", level=messages.ERROR)
            return TemplateResponse(request, "admin/404.html", {})

        # Gather stats defensively
        try:
            stats = analytics_svc.tournament_stats(obj)
        except Exception:
            stats = {}

        context = dict(
            self.admin_site.each_context(request),
            title=f"Analytics • {getattr(obj, 'name', obj.pk)}",
            tournament=obj,
            stats=stats,
        )
        return TemplateResponse(request, "admin/tournaments/analytics.html", context)


# --- module-level admin actions (kept for imports from admin.base) ---
@admin.action(description="Generate bracket (idempotent)")
def action_generate_bracket(modeladmin, request, queryset):
    from apps.corelib import brackets as bracket_svc  # local import
    done = 0
    for t in queryset:
        try:
            if hasattr(bracket_svc, "generate_bracket"):
                bracket_svc.generate_bracket(t)
            else:
                Bracket.objects.get_or_create(tournament=t)
            done += 1
        except Exception as e:
            _safe_message(modeladmin, request, f"{t}: {e}", level=messages.ERROR)
    _safe_message(modeladmin, request, f"Generated/updated bracket for {done} tournament(s).")


@admin.action(description="Lock bracket")
def action_lock_bracket(modeladmin, request, queryset):
    locked = 0
    for t in queryset:
        b, _ = Bracket.objects.get_or_create(tournament=t)
        b.is_locked = True
        b.save(update_fields=["is_locked"])
        locked += 1
    _safe_message(modeladmin, request, f"Locked {locked} bracket(s).")
