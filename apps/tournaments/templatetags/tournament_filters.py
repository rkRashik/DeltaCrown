"""Custom template filters for tournaments."""
from django import template

register = template.Library()


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
