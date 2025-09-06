# apps/tournaments/templatetags/tournament_extras.py
from django import template
from django.apps import apps
from django.urls import reverse, NoReverseMatch

from apps.tournaments.services.scheduling import get_checkin_window
from django.utils.html import format_html
from django.utils.safestring import mark_safe


register = template.Library()

STATUS_MAP = {
    "scheduled": ("Scheduled", "bg-blue-600/15 text-blue-300"),
    "live": ("Live", "bg-red-600/15 text-red-300"),
    "reported": ("Reported", "bg-amber-600/15 text-amber-300"),
    "verified": ("Verified", "bg-green-600/15 text-green-300"),
    "completed": ("Completed", "bg-slate-600/15 text-slate-300"),
}

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


@register.simple_tag
def status_badge(state: str) -> str:
    label, cls = STATUS_MAP.get((state or "").lower(), ("—", "bg-slate-700/40 text-slate-300"))
    return format_html('<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {}">{}</span>', cls, label)

@register.filter
def short_dt(dt):
    # Localize/formatting can be improved; placeholder for Asia/Dhaka
    if not dt:
        return ""
    return dt.strftime("%b %d, %H:%M")

@register.simple_tag
def yesno_icon(v: bool) -> str:
    return mark_safe("✅" if v else "—")