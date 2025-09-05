# apps/tournaments/admin/brackets.py
from __future__ import annotations

from typing import Optional

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe

from ..models import Bracket


def _admin_change_url(obj) -> Optional[str]:
    try:
        return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
    except NoReverseMatch:
        return None


# Idempotent: avoid AlreadyRegistered if user had a prior admin
try:
    admin.site.unregister(Bracket)
except NotRegistered:
    pass


@admin.register(Bracket)
class BracketAdmin(admin.ModelAdmin):
    """
    Read-only Bracket admin to visualize lock state and navigate related objects.
    Operators don't usually edit Bracket rows directly.
    """
    list_display = ("id", "tournament_link", "is_locked")
    search_fields = ("tournament__name", "tournament__slug")
    list_filter = ("is_locked",)
    readonly_fields = ("tournament_link", "is_locked")

    def has_add_permission(self, request):  # read-only
        return False

    def has_delete_permission(self, request, obj=None):  # read-only
        return False

    def has_change_permission(self, request, obj=None):  # read-only
        return False

    def tournament_link(self, obj: Bracket):
        t = getattr(obj, "tournament", None)
        if not t:
            return "—"
        url = _admin_change_url(t)
        text = f"{getattr(t, 'name', str(t))} (#{t.pk})"
        return mark_safe(f'<a href="{url}">{text}</a>') if url else text
    tournament_link.short_description = "Tournament"
