from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None


@register.filter
def mul(v, n):
    try:
        return float(v) * float(n)
    except Exception:
        return 0


@register.filter
def div(v, n):
    try:
        n = float(n)
        return (float(v) / n) if n else 0
    except Exception:
        return 0

