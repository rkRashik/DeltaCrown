"""
Template filters for team detail page.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def safe_img_url(value, fallback='/static/img/placeholder.png'):
    """
    Safely extract image URL with fallback.
    
    Usage:
        {{ team.logo_url|safe_img_url:"/static/img/default-logo.png" }}
    """
    if not value:
        return fallback
    
    # Handle FileField/ImageField
    if hasattr(value, 'url'):
        try:
            return value.url
        except (ValueError, AttributeError):
            return fallback
    
    # Handle string URL
    if isinstance(value, str) and value.strip():
        return value.strip()
    
    return fallback


@register.filter
def default_if_empty(value, default):
    """
    Return default if value is None, empty string, or whitespace.
    
    Usage:
        {{ team.tagline|default_if_empty:"No tagline set" }}
    """
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    return value
