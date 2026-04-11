"""
Dashboard helper utilities — safe model fetchers, formatters, fallbacks.

Extracted from views.py to reduce God-class size.
"""

from urllib.parse import quote

from django.apps import apps
from django.utils.timesince import timesince as _timesince


def _safe_model(label: str):
    """Return model class or None — never raises."""
    try:
        return apps.get_model(*label.split("."))
    except Exception:
        return None


def _safe_qs(fn):
    """Run a queryset lambda, return [] on any error."""
    try:
        return fn()
    except Exception:
        return []


def _safe_int(fn, default=0):
    try:
        return fn()
    except Exception:
        return default


def _build_game_lookup():
    """Build {game_id: game_name} lookup from games.Game."""
    Game = _safe_model("games.Game")
    if not Game:
        return {}
    try:
        return {g.id: g.name for g in Game.objects.all().only("id", "name")}
    except Exception:
        return {}


def _logo_url(obj, field="logo"):
    try:
        f = getattr(obj, field, None)
        return f.url if f else None
    except Exception:
        return None


def _ts(dt, now):
    """Format datetime as '2h ago' or empty string."""
    if not dt:
        return ''
    try:
        return _timesince(dt, now) + ' ago'
    except Exception:
        return ''


def _img_url(obj, field="logo"):
    """Safely extract image URL from a model field."""
    try:
        f = getattr(obj, field, None)
        return f.url if f else None
    except Exception:
        return None


def _avatar_fallback(name: str, background: str = '222222') -> str:
    """Build a stable UI avatar fallback URL."""
    display = quote((name or 'User')[:40])
    return f'https://ui-avatars.com/api/?name={display}&background={background}&color=fff&size=96'
