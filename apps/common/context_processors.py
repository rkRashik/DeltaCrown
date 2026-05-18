"""
Context processors for making common data available in all templates.
"""

import os

from apps.common.game_assets import _build_legacy_games_dict, get_game_data
from apps.common.seo import default_seo_for_request
from django.core.cache import cache


# ── P5.2 — Durable static version ────────────────────────────────────────────
# Set STATIC_VERSION env var on each deploy (or in .env) to bust browser caches
# globally. Example: STATIC_VERSION=2026-05-17-a
#
# Template usage:   <script src="{% static 'foo.js' %}?v={{ STATIC_VERSION }}">
# Deployment bump:  change STATIC_VERSION= in Render / .env and redeploy.
# Default value:    "dev" (no-cache-bust in development; browsers re-fetch freely).
#
# This replaces the previous manual ?v=YYYYMMDD approach: one env var,
# one bump, all static assets refreshed across every template at once.
_STATIC_VERSION = os.getenv("STATIC_VERSION", "dev")


def static_version(request):
    """Expose STATIC_VERSION to all templates as ``{{ STATIC_VERSION }}``.

    Wire into TEMPLATES context_processors in settings.py:
        'apps.common.context_processors.static_version'

    Template usage:
        <script src="{% static 'foo.js' %}?v={{ STATIC_VERSION }}"></script>

    To bump on deploy: set STATIC_VERSION=YYYY-MM-DD-x in your Render / .env
    environment variables and redeploy. No template changes required.
    """
    return {"STATIC_VERSION": _STATIC_VERSION}


def game_assets_context(request):
    """
    Add game assets to template context globally.
    Only returns active games (respects is_active flag).
    Results are cached for 60 seconds to avoid per-request DB hits.
    """
    games = cache.get('context_active_games')
    if games is None:
        games = _build_legacy_games_dict()
        cache.set('context_active_games', games, 60)
    return {
        'GAMES': games,
        'get_game_data': get_game_data,
    }


def seo_context(request):
    """Expose one default SEO contract to every template.

    View contexts can override this by passing their own ``seo`` dict built
    with ``apps.common.seo.build_seo``.
    """
    return {"seo": default_seo_for_request(request)}


# ===== PHASE 5A: Platform Preferences Context Processor =====

from apps.user_profile.services.platform_prefs_service import DEFAULT_PREFS


def user_platform_prefs(request):
    """
    Context processor to inject platform preferences into all templates.
    
    Available in templates as:
        {{ user_platform_prefs.timezone }}
        {{ user_platform_prefs.time_format }}
        {{ is_24h }}
        {{ currency_symbol }}
        {{ locale_code }}
    
    SAFE: Falls back to defaults if middleware hasn't set prefs.
    """
    # Get prefs from middleware (or defaults if middleware not run)
    prefs = getattr(request, 'user_platform_prefs', DEFAULT_PREFS.copy())
    
    # Helper flags
    is_24h = prefs.get('time_format', '12h') == '24h'
    currency_code = prefs.get('currency', 'BDT')
    currency_symbol = '৳' if currency_code == 'BDT' else '$'
    locale_code = prefs.get('preferred_language', 'en')
    
    return {
        'user_platform_prefs': prefs,
        'is_24h': is_24h,
        'currency_symbol': currency_symbol,
        'currency_code': currency_code,
        'locale_code': locale_code,
    }
