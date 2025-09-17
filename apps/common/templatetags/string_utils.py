"""String-related template helpers used across DeltaCrown templates.

Each helper aims to be defensive so that optional data from views or API
payloads does not break template rendering.
"""
from __future__ import annotations

from typing import Iterable, Iterator

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.text import slugify

register = template.Library()


@register.filter(name="coalesce")
def coalesce(value, fallback: str = ""):
    """Return `value` when truthy, otherwise `fallback`."""
    return value or fallback


@register.filter(name="ensure_str")
def ensure_str(value, fallback: str = ""):
    """Cast `value` to `str` while tolerating `None` and odd objects."""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return fallback


@register.filter(name="slugify")
def slugify_filter(value, allow_fallback: bool = True) -> str:
    """Wrapper around :func:django.utils.text.slugify with safe fallback."""
    if not value:
        return "" if allow_fallback else value
    return slugify(value)


@register.filter(name="joinby")
def joinby(values: Iterable, sep: str = ", ") -> str:
    """Join an iterable into a string while skipping `None`/empty entries."""
    if values is None:
        return ""
    if isinstance(values, str):
        return values
    try:
        iterator: Iterator = iter(values)
    except TypeError:
        return ""
    cleaned = [str(v) for v in iterator if v not in (None, "")]
    return sep.join(cleaned)


@register.filter(name="highlight")
def highlight(text, term):
    """Wrap occurrences of `term` in `<mark>` tags (case-insensitive)."""
    if not text or not term:
        return text

    source = str(text)
    needle = str(term)
    lower_source = source.lower()
    lower_needle = needle.lower()
    if lower_needle not in lower_source:
        return text

    pieces: list[str] = []
    start = 0
    step = len(needle)
    escaped_needle = conditional_escape(needle)

    while True:
        idx = lower_source.find(lower_needle, start)
        if idx == -1:
            pieces.append(conditional_escape(source[start:]))
            break
        pieces.append(conditional_escape(source[start:idx]))
        pieces.append(f"<mark>{escaped_needle}</mark>")
        start = idx + step

    return mark_safe("".join(pieces))
