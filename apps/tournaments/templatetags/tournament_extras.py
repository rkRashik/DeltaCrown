# apps/tournaments/templatetags/tournament_extras.py
from django import template
from django.apps import apps

from apps.tournaments.services.scheduling import get_checkin_window

register = template.Library()

@register.simple_tag
def match_checkin_window(match):
    # Usage in template:
    #   {% match_checkin_window match as win %}
    #   {% if win.0 and win.1 %} ... {% endif %}
    return get_checkin_window(match)

@register.inclusion_tag("tournaments/_groups.html", takes_context=True)
def render_groups(context, tournament):
    """Render group stage from tournament.bracket.data JSON.
    Expected shape:
      {"groups": [{"name": "Group A", "teams": [team_ids]}]}
    """
    groups = []
    Team = apps.get_model("teams", "Team")
    try:
        bracket = getattr(tournament, "bracket", None)
        data = getattr(bracket, "data", None) or {}
        for g in (data.get("groups") or []):
            name = (g.get("name") or "").strip()
            team_ids = [tid for tid in (g.get("teams") or []) if isinstance(tid, int)]
            team_qs = Team.objects.filter(id__in=team_ids)
            team_map = {t.id: t for t in team_qs}
            ordered = [team_map.get(tid) for tid in team_ids if tid in team_map]
            groups.append({"name": name or "Group", "teams": ordered})
    except Exception:
        groups = []
    ctx = {**context.flatten(), "groups": groups}
    return ctx
