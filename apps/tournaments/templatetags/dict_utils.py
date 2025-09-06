# apps/tournaments/templatetags/dict_utils.py
from django import template
register = template.Library()

@register.filter
def get_item(d, key):
    try:
        return d.get(key, {}) if isinstance(d, dict) else {}
    except Exception:
        return {}
