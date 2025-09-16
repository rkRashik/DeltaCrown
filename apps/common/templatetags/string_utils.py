"""Fallback string utilities for templates."""

from django import template

register = template.Library()


@register.filter
def noop(value):
    """Return the value unchanged."""

    return value
