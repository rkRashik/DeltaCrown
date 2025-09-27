"""
Context processors for making common data available in all templates.
"""

from apps.common.game_assets import GAMES, get_game_data


def game_assets_context(request):
    """
    Add game assets to template context globally.
    This allows access to game data without loading template tags.
    """
    return {
        'GAMES': GAMES,
        'get_game_data': get_game_data,
    }