# apps/tournaments/admin/brackets.py
from __future__ import annotations

from typing import Optional

from django import forms
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.core.exceptions import ValidationError
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe

from ..models import Bracket

def _admin_change_url(obj) -> Optional[str]:
    try:
        return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
    except NoReverseMatch:
        return None

def _validate_groups_payload(data: dict):
    if not isinstance(data, dict):
        raise ValidationError("Bracket data must be a JSON object.")
    groups = data.get("groups", None)
    if groups is None:
        # Allow empty; admin can save {} to clear
        return
    if not isinstance(groups, list):
        raise ValidationError("'groups' must be a list.")
    for i, g in enumerate(groups, start=1):
        if not isinstance(g, dict):
            raise ValidationError(f"Group #{i} must be an object with 'name' and 'teams'.")
        name = g.get("name")
        teams = g.get("teams")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError(f"Group #{i} requires a non-empty 'name'.")
        if not isinstance(teams, list):
            raise ValidationError(f"Group '{name}': 'teams' must be a list of team IDs.")
        for tid in teams:
            if not isinstance(tid, int):
                raise ValidationError(f"Group '{name}': each entry in 'teams' must be an integer team ID.")

class BracketAdminForm(forms.ModelForm):
    class Meta:
        model = Bracket
        fields = ["tournament", "is_locked", "data"]

    def clean_data(self):
        data = self.cleaned_data.get("data")
        if data in (None, ""):
            return data
        _validate_groups_payload(data)
        return data

@admin.register(Bracket)
class BracketAdmin(admin.ModelAdmin):
    form = BracketAdminForm
    list_display = ("id", "tournament_link", "is_locked", "updated_at")
    list_select_related = ("tournament",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("tournament", "is_locked")}),
        ("Bracket JSON", {
            "fields": ("data",),
            "description": mark_safe(
                "<p>Store groups in <code>data</code> as:</p>"
                "<pre>{\"groups\": [{\"name\": \"Group A\", \"teams\": [1,2,3,4]}]}</pre>"
            )
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow editing unless locked
        if obj and getattr(obj, "is_locked", False):
            return False
        return super().has_change_permission(request, obj)

    def tournament_link(self, obj: Bracket):
        t = getattr(obj, "tournament", None)
        if not t:
            return "—"
        url = _admin_change_url(t)
        text = f"{getattr(t, 'name', str(t))} (#{t.pk})"
        return mark_safe(f'<a href="{url}">{text}</a>') if url else text
    tournament_link.short_description = "Tournament"
