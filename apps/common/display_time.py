"""Presentation-time conversion of aware datetimes to the site timezone (settings.TIME_ZONE).

Storage stays timezone-aware UTC; only text shown to people is converted here. ``strftime`` on a
value read from the database prints UTC, which disagrees with Django's ``|date``/``|time`` filters
(they convert), so free-text messages must go through this module.
"""
from django.utils import timezone


def to_site_time(value):
    """Convert an aware datetime to the active timezone; naive values are returned unchanged."""
    return timezone.localtime(value) if timezone.is_aware(value) else value


def tz_label(value) -> str:
    """Unambiguous offset label for ``value`` in site time, for example ``UTC+06:00``."""
    offset = to_site_time(value).strftime("%z")  # "+0600"; empty for naive values
    return f"UTC{offset[:3]}:{offset[3:]}" if offset else ""


def format_local(value, fmt: str, *, label: bool = True) -> str:
    """``value`` formatted in site time, followed by the offset label when ``label`` is true."""
    text = to_site_time(value).strftime(fmt)
    suffix = tz_label(value) if label else ""
    return f"{text} ({suffix})" if suffix else text
