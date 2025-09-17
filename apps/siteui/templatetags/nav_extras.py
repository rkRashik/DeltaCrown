from __future__ import annotations

from django import template

register = template.Library()


def _normalize(pattern: str) -> str:
    if pattern == "/":
        return pattern
    return pattern.rstrip("/") + "/"


@register.simple_tag(takes_context=True)
def nav_active(context, *patterns) -> bool:
    request = context.get("request")
    if not request:
        return False
    path = request.path or "/"

    for raw in patterns:
        if not raw:
            continue
        pattern = str(raw)
        if pattern == "/":
            if path == "/":
                return True
            continue
        normalized = _normalize(pattern)
        if path == pattern or path.startswith(normalized):
            return True
    return False
