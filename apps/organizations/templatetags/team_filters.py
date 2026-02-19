"""
Template filters for team detail page.
"""
import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='to_json')
def to_json(value):
    """
    Serialize a Python dict/list to a JSON string safe for use in HTML attributes.

    Usage:
        data-permissions='{{ m.permissions|to_json }}'
    """
    if value is None:
        return '{}'
    try:
        return mark_safe(json.dumps(value))
    except (TypeError, ValueError):
        return '{}'


@register.filter(name='effective_perms_json')
def effective_perms_json(membership):
    """
    Render the EFFECTIVE permissions for a TeamMembership as a JSON dict.

    Merges role-based defaults with per-member overrides from the
    permissions JSONField. Returns {perm: true} for each active permission.

    Usage:
        data-permissions='{{ m|effective_perms_json }}'
    """
    try:
        perms = membership.get_permission_list()
        if 'ALL' in perms:
            # OWNER has all permissions
            return mark_safe(json.dumps({p: True for p in membership.ALL_PERMISSIONS}))
        return mark_safe(json.dumps({p: True for p in perms}))
    except Exception:
        return '{}'


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
