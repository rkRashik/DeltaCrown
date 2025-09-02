from __future__ import annotations

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


def _map_build(path: str, use_build: bool) -> str:
    """
    If use_build is True and the path is under src/, map to build/.
    e.g., src/js/helpers.js -> build/js/helpers.js
    """
    if use_build and path.startswith("src/"):
        return "build/" + path[len("src/") :]
    return path


@register.simple_tag(takes_context=True)
def asset(context, path: str | None = None) -> str:
    """
    Usage: {% asset 'src/js/helpers.js' %}
    Produces: /static/src/js/helpers.js?v=<STATIC_VERSION>

    If settings.USE_BUILD_ASSETS is True, maps to /static/build/... instead.

    Defensive:
      - If called without a path (e.g. inside an HTML comment), return "".
    """
    if not path:
        return ""
    use_build = getattr(settings, "USE_BUILD_ASSETS", False)
    version = getattr(settings, "STATIC_VERSION", "1")
    resolved = _map_build(path, use_build)
    url = static(resolved)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}v={version}"
