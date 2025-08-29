from django import template
from apps.tournaments.services.scheduling import get_checkin_window

register = template.Library()

@register.simple_tag
def match_checkin_window(match):
    """
    Usage in template:
      {% match_checkin_window match as win %}
      {% if win.0 and win.1 %} ... {% endif %}
    """
    return get_checkin_window(match)
