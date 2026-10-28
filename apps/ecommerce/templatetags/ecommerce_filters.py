from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def split(value, separator=","):
    """Render stored compatible-game labels without interpreting HTML."""
    return [part.strip() for part in str(value or "").split(separator) if part.strip()]


def _calculate(value, argument, operation):
    try:
        left, right = Decimal(str(value)), Decimal(str(argument))
        if not left.is_finite() or not right.is_finite():
            return ""
        return operation(left, right)
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return ""


@register.filter
def sub(value, argument):
    return _calculate(value, argument, lambda left, right: left - right)


@register.filter
def mul(value, argument):
    return _calculate(value, argument, lambda left, right: left * right)


@register.filter
def div(value, argument):
    return _calculate(value, argument, lambda left, right: left / right)
