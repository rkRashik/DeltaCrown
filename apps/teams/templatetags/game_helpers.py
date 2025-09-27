"""
Game helper template tags for teams app.
Now uses centralized game assets system.
"""
from django import template
from apps.common.game_assets import GAMES, get_game_data, get_game_logo, get_game_card

register = template.Library()


@register.simple_tag
def get_team_game_logo(game_code):
    """Get team game logo URL from centralized assets."""
    if not game_code:
        return ''
    return get_game_logo(game_code.upper())


@register.simple_tag
def get_team_game_name(game_code):
    """Get team game display name from centralized assets."""
    if not game_code:
        return ''
    
    game_data = get_game_data(game_code.upper())
    if game_data:
        return game_data.get('display_name', game_code.title())
    return game_code.title()


@register.simple_tag 
def get_team_game_color(game_code, color_type='primary'):
    """Get team game color from centralized assets."""
    if not game_code:
        return '#7c3aed'  # default color
        
    game_data = get_game_data(game_code.upper())
    if game_data:
        color_key = f'color_{color_type}'
        return game_data.get(color_key, '#7c3aed')
    return '#7c3aed'


@register.inclusion_tag('components/game_badge.html')
def team_game_badge(game_code):
    """Render a game badge component for teams."""
    return {'game_code': game_code.upper() if game_code else ''}


@register.filter
def game_display_name(game_code):
    """Template filter to get game display name."""
    return get_team_game_name(game_code)