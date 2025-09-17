from __future__ import annotations

from typing import Iterable, Any, Optional

from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


def _coalesce_matches(context, explicit_matches: Optional[Iterable[Any]]):
    """
    Prefer explicit matches parameter. Otherwise look for common context keys.
    Returns a list (may be empty).
    """
    if explicit_matches is not None:
        try:
            return list(explicit_matches)
        except TypeError:
            return []
    for key in ("upcoming_matches", "my_matches", "matches"):
        if key in context:
            try:
                return list(context.get(key) or [])
            except TypeError:
                return []
    return []


def _label(team_obj: Any, user_obj: Any, default_text: str) -> str:
    """
    Best-effort label: team.tag, team.name, user.display_name, user.username, fallback.
    Always HTML-escaped.
    """
    if team_obj is not None:
        val = getattr(team_obj, "tag", None) or getattr(team_obj, "name", None)
        if val:
            return escape(str(val))
    if user_obj is not None:
        val = getattr(user_obj, "display_name", None) or getattr(user_obj, "username", None)
        if val:
            return escape(str(val))
    return escape(default_text)


def _fmt_time(dt: Any) -> str:
    try:
        # datetime-like
        return escape(dt.strftime("%b %d, %Y %I:%M %p"))
    except Exception:
        return escape(str(dt)) if dt else "TBD"


@register.simple_tag(takes_context=True)
def upcoming_matches(context, matches=None, limit: Any = 5) -> str:
    """
    Usage:
      {% upcoming_matches %}  # uses upcoming_matches/my_matches/matches from context
      {% upcoming_matches matches=my_matches limit=3 %}

    Returns HTML (card with list). Safe to call in any template (no recursion).
    """
    items = _coalesce_matches(context, matches)

    # Normalize/slice limit
    try:
        lim = int(limit)
    except Exception:
        lim = 5
    if lim > 0:
        items = items[:lim]

    # Resolve "View all" link defensively
    view_all_href = "#"
    try:
        view_all_href = reverse("tournaments:my_matches")
    except NoReverseMatch:
        pass

    # Build HTML
    parts: list[str] = []
    parts.append('<section class="card p-3" aria-labelledby="um-title">')
    parts.append(
        '<div class="d-flex align-items-center justify-content-between mb-2">'
        '<h2 id="um-title" class="mb-0 fw-medium">Upcoming matches</h2>'
        f'<a class="btn btn-outline btn-sm" href="{escape(view_all_href)}">View all</a>'
        "</div>"
    )

    if items:
        parts.append('<ul class="list-unstyled mb-0">')
        for idx, m in enumerate(items):
            # Pull attributes safely
            round_no = getattr(m, "round_no", None)
            scheduled_at = getattr(m, "scheduled_at", None)
            team_a = getattr(m, "team_a", None)
            team_b = getattr(m, "team_b", None)
            user_a = getattr(m, "user_a", None)
            user_b = getattr(m, "user_b", None)
            url = getattr(m, "url", None)
            mid = getattr(m, "id", None)

            # Labels
            a_label = _label(team_a, user_a, "Team A")
            b_label = _label(team_b, user_b, "Team B")

            # Time/round
            meta_bits = []
            if round_no:
                meta_bits.append(f"Round {escape(str(round_no))}")
            meta_bits.append(_fmt_time(scheduled_at))
            meta_bits = [b for b in meta_bits if b]
            meta = " &#183; ".join(meta_bits)

            # Link
            href = "#"
            if url:
                href = url
            elif mid is not None:
                try:
                    href = reverse("tournaments:match_review", args=[mid])
                except NoReverseMatch:
                    href = "#"

            parts.append('<li class="mb-2">')
            parts.append(f'<div class="match-meta">{meta}</div>')
            parts.append(
                '<div class="match-teams">'
                '<div class="match-team">'
                f"<span>{a_label}</span>"
                '<span class="vs-dot">vs</span>'
                f"<span>{b_label}</span>"
                "</div></div>"
            )
            parts.append(
                '<div class="match-actions mt-2">'
                f'<a class="btn btn-outline btn-sm" href="{escape(href)}">Open</a>'
                "</div>"
            )
            parts.append("</li>")
            if idx != len(items) - 1:
                parts.append("<hr/>")
        parts.append("</ul>")
    else:
        parts.append('<div class="text-muted">No upcoming matches.</div>')

    parts.append("</section>")
    return mark_safe("".join(parts))
