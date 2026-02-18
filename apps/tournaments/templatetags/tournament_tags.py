"""
Custom template tags for tournament templates.
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary by key.
    
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return {}
    return dictionary.get(key, {})


@register.filter
def in_set(value, collection):
    """
    Check if value exists in a set/list/queryset.

    Usage: {% if tournament.id|in_set:user_registered_tournaments %}
    """
    if collection is None:
        return False
    return value in collection

@register.filter
def platform_icon(platform):
    """
    Get FontAwesome icon class for platform.
    
    Usage: {{ tournament.platform|platform_icon }}
    """
    icons = {
        'pc': 'fa-desktop',
        'mobile': 'fa-mobile-alt',
        'ps5': 'fa-playstation',
        'xbox': 'fa-xbox',
        'switch': 'fa-gamepad',
    }
    return icons.get(platform, 'fa-gamepad')


@register.filter
def mode_icon(mode):
    """
    Get FontAwesome icon class for mode.
    
    Usage: {{ tournament.mode|mode_icon }}
    """
    icons = {
        'online': 'fa-wifi',
        'lan': 'fa-map-marker-alt',
        'hybrid': 'fa-globe',
    }
    return icons.get(mode, 'fa-globe')


@register.filter
def attr(obj, name):
    """
    Dynamically access an attribute by name.

    Usage: {{ standing|attr:col }}
    """
    try:
        return getattr(obj, name, '')
    except Exception:
        return ''
