"""
Template tags for game assets integration
"""
from django import template
from django.templatetags.static import static
from apps.common.game_assets import GAMES, get_game_data, get_game_card, get_game_logo, get_game_icon

register = template.Library()

@register.simple_tag
def game_card_url(game_slug):
    """Get game card image URL"""
    return get_game_card(game_slug.upper())

@register.simple_tag
def game_logo_url(game_slug):
    """Get game logo URL"""
    return get_game_logo(game_slug.upper())

@register.simple_tag
def game_icon_url(game_slug):
    """Get game icon URL"""
    return get_game_icon(game_slug.upper())

@register.simple_tag
def game_name(game_slug):
    """Get game display name"""
    data = get_game_data(game_slug.upper())
    return data.get('display_name', game_slug.title())

@register.simple_tag
def game_color(game_slug):
    """Get game primary color"""
    data = get_game_data(game_slug.upper())
    return data.get('color_primary', '#00ff88')

@register.filter
def game_data(game_slug):
    """Get full game data as filter"""
    return get_game_data(game_slug.upper())
