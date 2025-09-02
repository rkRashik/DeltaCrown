from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from django import template
from django.conf import settings
from django.utils.html import conditional_escape, format_html

register = template.Library()


def _abs_url(request, url: str | None) -> str | None:
    """
    Ensure URL is absolute for share/OG. If `url` is None, fall back to current request URL.
    """
    if request is None:
        return url
    if not url:
        return request.build_absolute_uri()
    parts = urlsplit(url)
    if parts.scheme and parts.netloc:
        return url
    return request.build_absolute_uri(url)


@register.simple_tag(takes_context=True)
def meta_tags(context, title=None, description=None, image_url=None, canonical_url=None):
    """
    Render canonical link + Open Graph tags.

    Usage in templates: {% meta_tags %} or pass overrides:
      {% meta_tags title=page_title description=page_description image_url=img_url canonical_url=canon_url %}
    """
    request = context.get("request")

    # Resolve values from context with sensible fallbacks
    site_name = getattr(settings, "SITE_NAME", "DeltaCrown")

    # Title
    title = (
        title
        or context.get("page_title")
        or context.get("title")
        or getattr(context.get("object"), "title", None)
        or site_name
    )

    # Description
    description = (
        description
        or context.get("meta_description")
        or context.get("description")
        or getattr(context.get("object"), "description", None)
        or ""
    )

    # Canonical
    canonical_url = _abs_url(request, canonical_url)

    # Image
    image_url = image_url or context.get("meta_image") or getattr(settings, "DEFAULT_OG_IMAGE", None)
    image_url = _abs_url(request, image_url) if image_url else None

    # Escape textual content
    esc_title = conditional_escape(title)
    esc_desc = conditional_escape(description)
    esc_site = conditional_escape(site_name)

    # Build HTML
    pieces = []

    if canonical_url:
        pieces.append(format_html('<link rel="canonical" href="{}"/>', canonical_url))

    # Basic Open Graph
    pieces.append(format_html('<meta property="og:site_name" content="{}"/>', esc_site))
    pieces.append(format_html('<meta property="og:type" content="website"/>'))
    if canonical_url:
        pieces.append(format_html('<meta property="og:url" content="{}"/>', canonical_url))
    pieces.append(format_html('<meta property="og:title" content="{}"/>', esc_title))
    if esc_desc:
        pieces.append(format_html('<meta property="og:description" content="{}"/>', esc_desc))
        pieces.append(format_html('<meta name="description" content="{}"/>', esc_desc))
    if image_url:
        pieces.append(format_html('<meta property="og:image" content="{}"/>', image_url))

    # No Twitter/X tags per BD-first convention.

    return format_html("\n".join(pieces))
