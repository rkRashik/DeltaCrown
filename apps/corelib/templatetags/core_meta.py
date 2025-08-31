from django import template
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()

def _meta_pair(prop, content):
    if not content:
        return ""
    return format_html('<meta property="{}" content="{}"/>', prop, content)

@register.simple_tag(takes_context=True)
def meta_tags(context, request, title=None, description=None, image=None, type="website"):
    """
    Render canonical link + Open Graph meta tags (Facebook/WhatsApp/Instagram).
    Usage:
        {% load core_meta %}
        {% meta_tags request title="..." description="..." image=object.banner.url %}
    """
    req = request
    esc = conditional_escape

    try:
        canonical = req.build_absolute_uri()
    except Exception:
        canonical = ""

    site_name = "DeltaCrown"
    title = title or site_name
    description = description or "Esports tournaments, teams, and matches."
    og_type = type or "website"

    parts = []
    if canonical:
        parts.append(format_html('<link rel="canonical" href="{}"/>', esc(canonical)))

    parts.append(_meta_pair("og:site_name", site_name))
    parts.append(_meta_pair("og:type", og_type))
    parts.append(_meta_pair("og:title", title))
    parts.append(_meta_pair("og:description", description))
    if image:
        parts.append(_meta_pair("og:image", image))

    html = "\n".join([p for p in parts if p])
    return mark_safe(html)
