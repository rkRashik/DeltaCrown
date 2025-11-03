# apps/tournaments/admin/brackets.py
from __future__ import annotations
from typing import Optional, Dict, Any

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe
from django.apps import apps

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
        return
    if not isinstance(groups, list):
        raise ValidationError("'groups' must be a list.")
    for i, g in enumerate(groups, start=1):
        if not isinstance(g, dict):
            raise ValidationError(f"Group #{i} must be an object with 'name' and 'teams'.")
        name = g.get("name")
        teams = g.get("teams")
        stats = g.get("stats", None)
        if not isinstance(name, str) or not name.strip():
            raise ValidationError(f"Group #{i} requires a non-empty 'name'.")
        if not isinstance(teams, list):
            raise ValidationError(f"Group '{name}': 'teams' must be a list of team IDs.")
        for tid in teams:
            if not isinstance(tid, int):
                raise ValidationError(f"Group '{name}': each entry in 'teams' must be an integer team ID.")
        if stats is not None:
            if not isinstance(stats, dict):
                raise ValidationError(f"Group '{name}': 'stats' must be an object keyed by team id.")
            # keys can be str or int; values must be objects with numbers
            for k, v in stats.items():
                try:
                    int(k)
                except Exception:
                    raise ValidationError(f"Group '{name}': stats key '{k}' is not a team id.")
                if not isinstance(v, dict):
                    raise ValidationError(f"Group '{name}': stats for team {k} must be an object.")
                for metric in ('w', 'l'):
                    if metric in v and not isinstance(v[metric], int):
                        raise ValidationError(f"Group '{name}': stats[{k}].{metric} must be an integer.")

class BracketAdminForm(forms.ModelForm):
    class Meta:
        model = Bracket
        fields = ['tournament', 'is_locked', 'data']

    def clean_data(self):
        data = self.cleaned_data.get('data')
        if data in (None, ''):
            return data
        _validate_groups_payload(data)
        return data

@admin.register(Bracket)
class BracketAdmin(admin.ModelAdmin):
    form = BracketAdminForm
    list_display = ('id', 'tournament_link', 'is_locked', 'updated_at')
    list_select_related = ('tournament',)
    readonly_fields = ('created_at', 'updated_at', 'groups_preview')
    fieldsets = (
        (None, {'fields': ('tournament', 'is_locked')}),
        ('Bracket JSON', {
            'fields': ('data', 'groups_preview'),
            'description': mark_safe(
                "<p>JSON shape:</p>"
                "<pre>{\"groups\": ["
                "{\"name\": \"Group A\", \"teams\": [1,2,3,4], "
                "\"stats\": {\"1\": {\"w\": 2, \"l\": 0}, \"2\": {\"w\": 1, \"l\": 1}}}"
                "]}</pre>"
            )
        }),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj and getattr(obj, 'is_locked', False):
            return False
        return super().has_change_permission(request, obj)

    def tournament_link(self, obj: Bracket):
        t = getattr(obj, 'tournament', None)
        if not t:
            return '—'
        url = _admin_change_url(t)
        text = f"{getattr(t, 'name', str(t))} (#{t.pk})"
        return mark_safe(f'<a href="{url}">{text}</a>') if url else text
    tournament_link.short_description = 'Tournament'

    def groups_preview(self, obj: Bracket):
        data = getattr(obj, 'data', None) or {}
        groups = data.get('groups') or []
        if not groups:
            return mark_safe('<em>No groups configured.</em>')
        Team = apps.get_model('teams', 'Team')
        html = ['<div class="dc-muted text-sm">Resolved preview:</div>']
        for g in groups:
            name = (g.get('name') or '').strip() or 'Group'
            team_ids = [tid for tid in (g.get('teams') or []) if isinstance(tid, int)]
            q = Team.objects.filter(id__in=team_ids)
            m = {t.id: t for t in q}
            rows = []
            for tid in team_ids:
                t = m.get(tid)
                label = t.name if t else f'#?{tid}'
                rows.append(f'<li>{label}</li>')
            html.append(f'<div class="mt-2"><strong>{name}</strong><ul>' + ''.join(rows) + '</ul></div>')
        return mark_safe(''.join(html))
    groups_preview.short_description = 'Preview (resolved team names)'
