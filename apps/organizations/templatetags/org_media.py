"""
Safe media file URL handling for organization templates.

Prevents crashes when accessing .url on empty ImageField/FileField.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='safe_file_url')
def safe_file_url(file_field, fallback_url=''):
    """
    Safely get URL from a Django FileField/ImageField.
    
    Returns the file URL if it exists, otherwise returns the fallback URL.
    Never crashes on empty fields.
    
    Usage:
        {{ organization.logo|safe_file_url:"https://example.com/default.png" }}
        {{ user.avatar|safe_file_url }}
    
    Args:
        file_field: Django FileField/ImageField instance
        fallback_url: URL to return if file doesn't exist (default: empty string)
    
    Returns:
        str: File URL or fallback URL
    """
    try:
        # Check if field exists and has a file
        if file_field and hasattr(file_field, 'url') and file_field.name:
            return file_field.url
    except (ValueError, AttributeError):
        # ValueError: "The 'field' attribute has no file associated with it."
        # AttributeError: field is None or doesn't have expected attributes
        pass
    
    return fallback_url or ''


@register.filter(name='safe_file_exists')
def safe_file_exists(file_field):
    """
    Check if a FileField/ImageField has an associated file.
    
    Usage:
        {% if organization.logo|safe_file_exists %}
            <img src="{{ organization.logo.url }}">
        {% endif %}
    
    Args:
        file_field: Django FileField/ImageField instance
    
    Returns:
        bool: True if file exists, False otherwise
    """
    try:
        return bool(file_field and file_field.name)
    except (ValueError, AttributeError):
        return False
