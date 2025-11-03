from __future__ import annotations

from django import template
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

register = template.Library()

@register.simple_tag(takes_context=True)
def include_if_exists(context, template_name: str, **kwargs) -> str:
    """
    Render the given template only if it exists; otherwise render nothing.

    Usage:
        {% load ui_utils %}
        {% include_if_exists "tournaments/_rules_drawer.html" some_var=val %}

    Notes:
    - Merges the parent context with any keyword overrides you pass.
    - Safe drop-in replacement for non-Django patterns like
      `{% include "..." ignore missing %}` from other template engines.
    """
    try:
        tmpl = get_template(template_name)
    except TemplateDoesNotExist:
        return ""
    data = context.flatten()
    data.update(kwargs)
    return tmpl.render(data)
