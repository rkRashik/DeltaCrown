from django import template
from django.urls import reverse, NoReverseMatch
from apps.siteui.social_config import (
    get_enabled_social_media,
    get_enabled_legal_links,
    get_footer_navigation,
    BRAND_CONFIG,
    NEWSLETTER_CONFIG
)

register = template.Library()

@register.simple_tag
def get_footer_config():
    """Get all footer configuration data"""
    return {
        'brand': BRAND_CONFIG,
        'newsletter': NEWSLETTER_CONFIG,
        'social_media': get_enabled_social_media(),
        'legal_links': get_enabled_legal_links(),
        'navigation': get_footer_navigation()
    }

@register.simple_tag
def get_url_or_link(url_config):
    """Get URL from config, handle both URL names and direct URLs"""
    if url_config.get('is_url_name'):
        try:
            return reverse(url_config['url'])
        except NoReverseMatch:
            return '#'  # Fallback for broken URL names
    return url_config['url']