"""Custom template filters for tournaments."""
try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

# Allowed HTML tags for rulebook sanitization
RULEBOOK_ALLOWED_TAGS = [
    'p', 'br', 'ul', 'ol', 'li', 'strong', 'em', 'h1', 'h2', 'h3',
    'a', 'span', 'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'blockquote', 'hr', 'pre', 'code', 'img', 'sub', 'sup',
]

RULEBOOK_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
    'span': ['class', 'style'],
    'div': ['class', 'style'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    '*': ['class'],
}


@register.filter(name='sanitize_html')
def sanitize_html(value):
    """
    Sanitize HTML content using bleach, allowing only safe tags.
    
    Usage in templates:
        {{ tournament.rules_text|sanitize_html }}
    
    Allowed tags: p, br, ul, ol, li, strong, em, h1-h3, a, table elements, etc.
    All script/style/iframe tags are stripped. XSS vectors are removed.
    """
    if not value:
        return ''
    if HAS_BLEACH:
        cleaned = bleach.clean(
            value,
            tags=RULEBOOK_ALLOWED_TAGS,
            attributes=RULEBOOK_ALLOWED_ATTRIBUTES,
            strip=True,
        )
        return mark_safe(cleaned)
    # Fallback: escape everything if bleach is not installed
    return escape(value)


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def remaining_slots(max_participants, current_count):
    """Calculate remaining slots."""
    try:
        remaining = int(max_participants) - int(current_count)
        return max(0, remaining)
    except (ValueError, TypeError):
        return 0
