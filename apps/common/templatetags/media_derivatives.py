"""{% image_attrs blob "thumb,card,hero" "sizes" %} -> src (and srcset/sizes) for governed public artwork.

Falls back to the plain original URL unless derivatives are switched on and the field is allowlisted, so
templates stay valid in every storage mode. Widths are the nominal variant sizes: a derivative is never
upscaled, so a smaller source simply yields a smaller file.
"""
from django import template
from django.utils.html import format_html

from apps.common.media import derivatives

register = template.Library()


@register.simple_tag
def image_attrs(blob, variants, sizes=""):
    if not (derivatives.active() and blob.instance.pk and derivatives.allowed(blob.field)):
        return format_html('src="{}"', blob.url)
    names = [v.strip() for v in variants.split(",") if v.strip() in derivatives.VARIANTS]
    if not names:
        return format_html('src="{}"', blob.url)
    default = derivatives.url(blob, names[len(names) // 2])
    if len(names) == 1:
        return format_html('src="{}"', default)
    srcset = ", ".join(f"{derivatives.url(blob, v)} {derivatives.VARIANTS[v]}w" for v in names)
    if sizes:
        return format_html('src="{}" srcset="{}" sizes="{}"', default, srcset, sizes)
    return format_html('src="{}" srcset="{}"', default, srcset)
