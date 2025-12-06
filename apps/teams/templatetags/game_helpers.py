"""
Game helper template tags for teams app.
Now uses GameService for canonical game data.
"""
from django import template
from apps.games.services import game_service

register = template.Library()


@register.simple_tag
def get_team_game_logo(game_code):
    """Get team game logo URL from GameService."""
    if not game_code:
        return ''
    try:
        # Normalize and get game
        slug = game_service.normalize_slug(game_code)
        game = game_service.get_game(slug)
        if game and game.logo:
            return game.logo.url if hasattr(game.logo, 'url') else str(game.logo)
    except Exception:
        pass
    # Fallback to legacy
    try:
        from apps.common.game_assets import get_game_logo
        return get_game_logo(game_code)
    except:
        return ''


@register.simple_tag
def get_team_game_name(game_code):
    """Get team game display name from GameService (canonical)."""
    if not game_code:
        return ''
    try:
        slug = game_service.normalize_slug(game_code)
        game = game_service.get_game(slug)
        if game:
            return game.display_name
    except Exception:
        pass
    # Fallback to title case
    return game_code.title()


@register.simple_tag 
def get_team_game_color(game_code, color_type='primary'):
    """Get team game color from GameService."""
    if not game_code:
        return '#7c3aed'  # default color
    try:
        slug = game_service.normalize_slug(game_code)
        game = game_service.get_game(slug)
        if game:
            return game.color or '#7c3aed'
    except Exception:
        pass
    return '#7c3aed'


@register.simple_tag
def get_team_game_slug(game_code):
    """Get canonical game slug from GameService."""
    if not game_code:
        return ''
    try:
        return game_service.normalize_slug(game_code)
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
