# apps/tournaments/templatetags/tournament_extras.py
from django import template
from django.apps import apps
from django.urls import reverse, NoReverseMatch

from apps.tournaments.services.scheduling import get_checkin_window

register = template.Library()

@register.simple_tag
def match_checkin_window(match):
    return get_checkin_window(match)

@register.simple_tag
def team_public_url(team):
    """Return public URL for a team when route exists, else empty string."""
    if not team:
        return ''
    try:
        return reverse('teams:detail', kwargs={'pk': team.pk})
    except NoReverseMatch:
        try:
            return reverse('teams:detail', args=[team.pk])
        except NoReverseMatch:
            return ''

@register.inclusion_tag('tournaments/_groups.html', takes_context=True)
def render_groups(context, tournament):
    """Render group stage from tournament.bracket.data JSON with optional stats.
    JSON shape:
      {"groups": [{"name": "Group A", "teams": [ids], "stats": {"1": {"w": 2, "l": 0}}}]}
    """
    groups = []
    Team = apps.get_model('teams', 'Team')
    try:
        bracket = getattr(tournament, 'bracket', None)
        data = getattr(bracket, 'data', None) or {}
        for g in (data.get('groups') or []):
            name = (g.get('name') or '').strip() or 'Group'
            team_ids = [tid for tid in (g.get('teams') or []) if isinstance(tid, int)]
            team_qs = Team.objects.filter(id__in=team_ids)
            team_map = {t.id: t for t in team_qs}
            ordered = [team_map.get(tid) for tid in team_ids if tid in team_map]
            stats = g.get('stats') or {}
            # normalize keys to int
            norm_stats = {}
            for k, v in stats.items():
                try:
                    norm_stats[int(k)] = v
                except Exception:
                    continue
            groups.append({'name': name, 'teams': ordered, 'stats': norm_stats})
    except Exception:
        groups = []
    ctx = {**context.flatten(), 'groups': groups}
    return ctx
