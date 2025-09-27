"""
Template tags for homepage functionality
"""

from django import template
from apps.common.game_assets import GAMES

register = template.Library()


@register.filter
def get_game_data(game_code):
    """
    Get full game data from GAMES configuration by game code.
    
    Usage: {{ game.code|get_game_data }}
    """
    if not game_code:
        return {}
    
    return GAMES.get(game_code, {})


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary by key.
    
    Usage: {{ dict|get_item:key }}
    """
    if not dictionary or not key:
        return None
    
    return dictionary.get(key)


@register.simple_tag
def game_info(game_code, field=None):
    """
    Get game information by code and optionally a specific field.
    
    Usage: 
    {% game_info 'VALORANT' %} - returns full game data
    {% game_info 'VALORANT' 'display_name' %} - returns specific field
    """
    if not game_code:
        return {} if not field else ''
    
    game_data = GAMES.get(game_code, {})
    
    if field:
        return game_data.get(field, '')
    
    return game_data