"""
Game Assets Template Tags
========================

Template tags for easy access to game assets in templates.

Usage in templates:
    {% load game_assets %}
    
    <!-- Get game logo -->
    <img src="{% game_logo 'VALORANT' %}" alt="Valorant">
    
    <!-- Get game card -->
    <div style="background-image: url('{% game_card 'VALORANT' %}')"></div>
    
    <!-- Get game data -->
    {% game_data 'VALORANT' as valorant %}
    <div style="color: {{ valorant.color_primary }}">{{ valorant.display_name }}</div>
"""

from django import template
from django.templatetags.static import static
from apps.common.game_assets import (
    get_game_logo, get_game_card, get_game_icon, 
    get_game_banner, get_game_data, get_game_colors
)

register = template.Library()

@register.simple_tag
def game_logo(game_code):
    """Get game logo URL."""
    return get_game_logo(game_code)

@register.simple_tag
def game_card(game_code):
    """Get game card URL."""
    return get_game_card(game_code)

@register.simple_tag
def game_icon(game_code):
    """Get game icon URL."""
    return get_game_icon(game_code)

@register.simple_tag
def game_banner(game_code):
    """Get game banner URL."""
    return get_game_banner(game_code)

@register.simple_tag
def game_data(game_code):
    """Get complete game data."""
    return get_game_data(game_code)

@register.simple_tag
def game_colors(game_code):
    """Get game colors."""
    return get_game_colors(game_code)

@register.filter
def game_logo_filter(game_code):
    """Filter version of game_logo for use in template variables."""
    return get_game_logo(game_code)

@register.filter
def game_card_filter(game_code):
    """Filter version of game_card for use in template variables."""
    return get_game_card(game_code)

@register.inclusion_tag('common/game_asset_tags.html')
def game_logo_img(game_code, css_class='', alt_text=''):
    """Render a complete img tag for a game logo."""
    game = get_game_data(game_code)
    return {
        'logo_url': get_game_logo(game_code),
        'css_class': css_class,
        'alt_text': alt_text or game['display_name'],
        'game_name': game['display_name']
    }

@register.inclusion_tag('common/game_badge.html')
def game_badge(game_code, show_name=True, css_class=''):
    """Render a complete game badge with logo and name."""
    game = get_game_data(game_code)
    return {
        'game': game,
        'game_code': game_code,
        'logo_url': get_game_logo(game_code),
        'show_name': show_name,
        'css_class': css_class
    }

@register.simple_tag
def game_color_primary(game_code):
    """Get game primary color."""
    game_data = get_game_data(game_code)
    if game_data and 'color_primary' in game_data:
        return game_data['color_primary']
    return '#7c3aed'  # default color

@register.simple_tag
def game_color_secondary(game_code):
    """Get game secondary color."""
    game_data = get_game_data(game_code)
    if game_data and 'color_secondary' in game_data:
        return game_data['color_secondary']
    return '#1a1a1a'  # default color

@register.simple_tag
def game_display_name(game_code):
    """Get game display name from GameService."""
    if not game_code:
        return ''
    try:
        from apps.games.services.game_service import game_service
        game = game_service.get_game(game_code)
        return game.display_name if game else game_code.title()
    except (KeyError, Exception):
        game_data = get_game_data(game_code)
        if game_data and 'display_name' in game_data:
            return game_data['display_name']
        return game_code.title()

@register.simple_tag
def game_category(game_code):
    """Get game category."""
    game_data = get_game_data(game_code)
    if game_data and 'category' in game_data:
        return game_data['category']
    return 'Gaming'  # default category

@register.filter
def game_display_name(game_code):
    """Get game display name from GameService - filter version."""
    if not game_code:
        return ''
    try:
        from apps.games.services.game_service import game_service
        game = game_service.get_game(game_code)
        return game.display_name if game else game_code.title()
    except (KeyError, Exception):
        game_data = get_game_data(game_code)
        if game_data and 'display_name' in game_data:
            return game_data['display_name']
        return game_code.title()

@register.filter
def multiply(value, arg):
    """Multiply filter for mathematical operations in templates."""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0