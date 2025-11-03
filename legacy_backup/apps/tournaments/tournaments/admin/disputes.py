# apps/tournaments/admin/disputes.py
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin.sites import AlreadyRegistered, NotRegistered

from ..models import MatchDispute


class MatchDisputeAdmin(admin.ModelAdmin):
    """
    Admin for match disputes. Schema-tolerant and perf-conscious:
    - list_select_related keeps changelist queries low if relations exist.
    - get_queryset defends against missing relations in alternate schemas.
    - display helpers avoid attribute errors across profile/user variations.
    """
    list_display = ("id", "match_link", "reported_by_display", "status", "created_at_display")
    list_filter = ("status",)
    search_fields = (
        "match__tournament__name",
        "match__id",
        "opened_by__display_name",
        "opened_by__user__username",
        "description",
    )
    date_hierarchy = "created_at"

    # Changelist perf: follow common relations if present
    list_select_related = ("match", "match__tournament", "opened_by", "opened_by__user")

    try:
        # If your model exposes these FK fields, autocomplete is a nice UX win
        autocomplete_fields = ("match", "opened_by")
    except Exception:
        # Keep admin import resilient even if field names change
        pass

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Be defensive: select_related where possible to avoid N+1 without breaking
        for rel in ("match", "match__tournament", "opened_by", "opened_by__user"):
            try:
                qs = qs.select_related(rel)
            except Exception:
                pass
        return qs


    # ---------- Safe display helpers ----------

    def match_link(self, obj):
        m = getattr(obj, "match", None)
        if not m:
            return "-"
        # Best-effort link to the Match change page (path may differ in your project)
        try:
            return format_html('<a href="/admin/tournaments/match/{}/change/">{}</a>', m.pk, str(m))
        except Exception:
            return str(m)

    match_link.short_description = "Match"

    def reported_by_display(self, obj):
        # Prefer opened_by; fall back to reported_by if present in older schemas
        p = getattr(obj, "opened_by", None) or getattr(obj, "reported_by", None)
        if not p:
            return "-"
        u = getattr(p, "user", None)
        if u and getattr(u, "username", None):
            return u.username
        return getattr(p, "display_name", None) or str(p) or "-"


    reported_by_display.short_description = "Reporter"

    def created_at_display(self, obj):
        return (
            getattr(obj, "created_at", None)
            or getattr(obj, "created", None)
            or getattr(obj, "created_on", None)
            or "-"
        )

    created_at_display.short_description = "Created"


# ---- Idempotent registration ----
# If something (e.g., admin/base.py) already registered the model, replace it cleanly.
try:
    admin.site.unregister(MatchDispute)
except NotRegistered:
    pass
except Exception:
    # Be defensive; if unregister fails for any unexpected reason, continue to try registering.
    pass

try:
    admin.site.register(MatchDispute, MatchDisputeAdmin)
except AlreadyRegistered:
    # Another import path might have raced to register; ignore to avoid crashing.
    pass
