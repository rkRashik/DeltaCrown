"""
Context processors for making common data available in all templates.
"""

from apps.common.game_assets import _build_legacy_games_dict, get_game_data
from django.core.cache import cache


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
