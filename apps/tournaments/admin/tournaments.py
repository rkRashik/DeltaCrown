from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.template.response import TemplateResponse

from ..models import Tournament, Registration, Bracket, Match
from ..services.analytics import tournament_stats
from .components import (
    EfootballConfigInline, ValorantConfigInline, TournamentSettingsInline, HasEntryFeeFilter
)

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """
    NOTE:
    Your model uses fields like start_at / end_at / slot_size / entry_fee_bdt.
    We expose safe accessors (methods) instead of hard-coding missing names like start_date/end_date.
    """
    list_display = ("name", "status", "starts", "ends", "slots", "fee", "pool", "analytics_link")
    list_filter = ("status", HasEntryFeeFilter)
    search_fields = ("name", "slug")

    def analytics_link(self, obj):
        return format_html('<a href="{}">Analytics</a>', f"./{obj.pk}/analytics/")
    analytics_link.short_description = "Dashboard"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:pk>/analytics/", self.admin_site.admin_view(self.analytics_view), name="tournament_analytics"),
        ]
        return custom + urls

    def analytics_view(self, request, pk):
        obj = self.get_object(request, pk)
        if not self.has_view_permission(request, obj):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        stats = tournament_stats(obj)
        ctx = {
            **self.admin_site.each_context(request),
            "title": f"Analytics — {obj.name}",
            "tournament": obj,
            "stats": stats,
        }
        return TemplateResponse(request, "admin/tournaments/tournament/analytics.html", ctx)

    # We dynamically include settings + exactly one (or both if none) game config inline(s)
    def get_inlines(self, request, obj=None):
        if not obj:
            # On the "Add tournament" page, avoid inlines (parent not saved yet)
            return []
        inlines = [TournamentSettingsInline]

        econf = getattr(obj, "efootball_config", None)
        vconf = getattr(obj, "valorant_config", None)

        if econf and vconf:
            self.message_user(
                request,
                "Warning: both eFootball and Valorant configs exist. Please keep only one.",
                level=messages.WARNING,
            )
            inlines += [EfootballConfigInline, ValorantConfigInline]
            return inlines

        if econf:
            inlines.append(EfootballConfigInline)
            return inlines

        if vconf:
            inlines.append(ValorantConfigInline)
            return inlines

        # If none exists yet, show both so the admin can choose one to create.
        inlines += [EfootballConfigInline, ValorantConfigInline]
        return inlines

    # ---- Safe accessors for list_display ----
    @admin.display(ordering="start_at", description="Start")
    def starts(self, obj):
        # try start_at then start_date
        return getattr(obj, "start_at", None) or getattr(obj, "start_date", None) or "—"

    @admin.display(ordering="end_at", description="End")
    def ends(self, obj):
        # try end_at then end_date
        return getattr(obj, "end_at", None) or getattr(obj, "end_date", None) or "—"

    @admin.display(description="Slots")
    def slots(self, obj):
        # try slot_size, then slots, then max_slots
        return (
            getattr(obj, "slot_size", None)
            or getattr(obj, "slots", None)
            or getattr(obj, "max_slots", None)
            or "—"
        )

    @admin.display(description="Entry Fee")
    def fee(self, obj):
        # common names: entry_fee_bdt, entry_fee, fee
        for name in ("entry_fee_bdt", "entry_fee", "fee"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val not in (None, ""):
                    return val
        return "—"

    @admin.display(description="Prize Pool")
    def pool(self, obj):
        # common names: prize_pool_bdt, prize_pool, pool
        for name in ("prize_pool_bdt", "prize_pool", "pool"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val not in (None, ""):
                    return val
        return "—"


# --- Tournament admin actions: Generate / Lock bracket ---
@admin.action(description="Generate bracket (idempotent)")
def action_generate_bracket(modeladmin, request, queryset):
    from apps.corelib.brackets import generate_bracket  # implemented as stub now; full in Part 6
    done = 0
    for t in queryset:
        try:
            generate_bracket(t)
            done += 1
        except Exception as e:
            modeladmin.message_user(request, f"{t.name}: {e}", level=messages.ERROR)
    modeladmin.message_user(request, f"Generated/updated bracket for {done} tournament(s).")


@admin.action(description="Lock bracket")
def action_lock_bracket(modeladmin, request, queryset):
    for t in queryset:
        b = getattr(t, "bracket", None)
        if not b:
            b = Bracket.objects.create(tournament=t, is_locked=True)
        else:
            b.is_locked = True
            b.save(update_fields=["is_locked"])
    modeladmin.message_user(request, f"Locked {queryset.count()} bracket(s).")
