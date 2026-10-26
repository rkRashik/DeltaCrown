"""Identity tags also work in emails without a request context."""
from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def public_url(path="/"):
    from apps.common.seo import absolute_url
    return absolute_url(path)


@register.simple_tag
def brand_config():
    return settings.BRAND


@register.simple_tag
def brand_static_url(path):
    from apps.common.seo import absolute_url
    return absolute_url(static(path))
