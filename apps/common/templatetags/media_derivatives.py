"""Shared responsive-image helpers for governed media.

{% image_attrs blob "thumb,card,hero" "sizes" %}  -> src (+ srcset/sizes when several variants are listed)
{% image_url blob "card" %}                        -> a single URL (CSS backgrounds, data attributes)

Both fall back to the plain original URL unless derivatives are switched on and the field is eligible, and
never raise for objects that are not governed FieldFiles. Widths are the nominal variant sizes: derivatives are
never upscaled, so a smaller source simply yields a smaller file.
"""
from django import template
from django.utils.html import format_html

from apps.common.media import derivatives

register = template.Library()


def _names(variants):
    return sorted((v.strip() for v in variants.split(",") if v.strip() in derivatives.VARIANTS),
                  key=derivatives.VARIANTS.get)


@register.simple_tag
def image_url(blob, variant):
    if variant not in derivatives.VARIANTS:
        return blob.url
    if derivatives.cdn_allowed(blob):
        return derivatives.cdn_url(blob, variant)
    return derivatives.variant_url(blob, variant)


@register.simple_tag
def image_attrs(blob, variants, sizes=""):
    names = _names(variants)
    if not names:
        return format_html('src="{}"', blob.url)
    pick = (lambda v: derivatives.cdn_url(blob, v)) if derivatives.cdn_allowed(blob) else (lambda v: derivatives.variant_url(blob, v))
    default = pick(names[len(names) // 2])
    urls = [pick(v) for v in names]
    if len(names) == 1 or len(set(urls)) == 1:  # one candidate (or feature off): a plain src is all that's needed
        return format_html('src="{}"', default)
    srcset = ", ".join(f"{u} {derivatives.VARIANTS[v]}w" for u, v in zip(urls, names))
    if sizes:
        return format_html('src="{}" srcset="{}" sizes="{}"', default, srcset, sizes)
    return format_html('src="{}" srcset="{}"', default, srcset)
