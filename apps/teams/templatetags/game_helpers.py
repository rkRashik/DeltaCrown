"""
Game helper template tags for teams app.
Now uses Game Registry for canonical game data.
"""
from django import template
from apps.common.game_registry import get_game, normalize_slug

register = template.Library()


@register.simple_tag
def get_team_game_logo(game_code):
    """Get team game logo URL from Game Registry."""
    if not game_code:
        return ''
    try:
        game = get_game(game_code)
        return game.logo
    except (KeyError, Exception):
        # Fallback to legacy
        from apps.common.game_assets import get_game_logo
        return get_game_logo(game_code)


@register.simple_tag
def get_team_game_name(game_code):
    """Get team game display name from Game Registry (canonical)."""
    if not game_code:
        return ''
    try:
        game = get_game(game_code)
        return game.display_name
    except (KeyError, Exception):
        # Fallback to title case
        return game_code.title()


@register.simple_tag 
def get_team_game_color(game_code, color_type='primary'):
    """Get team game color from Game Registry."""
    if not game_code:
        return '#7c3aed'  # default color
    try:
        game = get_game(game_code)
        return game.colors.get(color_type, '#7c3aed')
    except (KeyError, Exception):
        return '#7c3aed'


@register.simple_tag
def get_team_game_slug(game_code):
    """Get canonical game slug from Game Registry."""
    if not game_code:
        return ''
    try:
        return normalize_slug(game_code)
    except Exception:
        return game_code.lower()


@register.inclusion_tag('components/game_badge.html')
def team_game_badge(game_code):
    """Render a game badge component for teams."""
    return {'game_code': game_code if game_code else ''}


@register.filter
def game_display_name(game_code):
    """Template filter to get canonical game display name from Game Registry."""
    return get_team_game_name(game_code)

@register.simple_tag
def game_logo(game_code):
    """Get game logo URL - simple tag version for easier use."""
    return get_team_game_logo(game_code)
