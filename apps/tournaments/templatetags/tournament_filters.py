"""Custom template filters for tournaments."""
import html
import re

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
    'a', 'span', 'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'i',
    'blockquote', 'hr', 'pre', 'code', 'img', 'sub', 'sup',
]

RULEBOOK_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
    'span': ['class'],
    'div': ['class'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    '*': ['class'],
}


def _normalize_rulebook_text(value):
    """Decode HTML entities repeatedly to handle double-escaped payloads."""
    text = str(value)
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    return text


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
    value = _normalize_rulebook_text(value)
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


@register.filter(name='render_rulebook')
def render_rulebook(value):
    """
    Render rulebook text safely from either escaped HTML or markdown/plain text.
    """
    if not value:
        return ''

    raw = _normalize_rulebook_text(value).strip()
    if not raw:
        return ''

    looks_like_html = bool(re.search(r'</?[a-z][^>]*>', raw, flags=re.IGNORECASE))
    if looks_like_html:
        return sanitize_html(raw)

    safe_text = escape(raw)
    safe_text = re.sub(r'^###\s+(.+)$', r'<h4 class="text-sm font-bold text-white mt-4 mb-2">\1</h4>', safe_text, flags=re.MULTILINE)
    safe_text = re.sub(r'^##\s+(.+)$', r'<h3 class="text-base font-bold text-white mt-5 mb-2">\1</h3>', safe_text, flags=re.MULTILINE)
    safe_text = re.sub(r'^#\s+(.+)$', r'<h2 class="text-lg font-bold text-white mt-6 mb-3">\1</h2>', safe_text, flags=re.MULTILINE)
    safe_text = re.sub(r'\*\*(.+?)\*\*', r'<strong class="text-white">\1</strong>', safe_text)
    safe_text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', safe_text)
    safe_text = re.sub(r'^-\s+(.+)$', r'<li class="ml-5 list-disc">\1</li>', safe_text, flags=re.MULTILINE)
    safe_text = re.sub(r'^\d+\.\s+(.+)$', r'<li class="ml-5 list-decimal">\1</li>', safe_text, flags=re.MULTILINE)
    safe_text = safe_text.replace('\r\n', '\n').replace('\n\n', '</p><p class="mb-3 text-gray-300 leading-relaxed">')
    safe_text = safe_text.replace('\n', '<br>')

    return mark_safe(f'<p class="mb-3 text-gray-300 leading-relaxed">{safe_text}</p>')


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
