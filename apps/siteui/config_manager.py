"""
Social Media Configuration Management

This file provides utilities to manage social media and footer configuration.
You can either edit the social_config.py file directly or use these functions
to programmatically update the configuration.

Usage Examples:

# Update a social media platform URL
from apps.siteui.config_manager import update_social_media
update_social_media('facebook', 'url', 'https://facebook.com/yournewpage')

# Enable/disable a platform
update_social_media('instagram', 'enabled', False)

# Update brand information
from apps.siteui.config_manager import update_brand_config
update_brand_config('description', 'New brand description here')

# Update newsletter settings
from apps.siteui.config_manager import update_newsletter_config
update_newsletter_config('subtitle', 'New subtitle for newsletter')
"""

import json
import os
from django.conf import settings

CONFIG_FILE = os.path.join(settings.BASE_DIR, 'apps', 'siteui', 'social_config.py')

def get_current_config():
    """Get current configuration from the config file"""
    from apps.siteui.social_config import (
        SOCIAL_MEDIA_CONFIG,
        BRAND_CONFIG, 
        NEWSLETTER_CONFIG,
        LEGAL_LINKS,
        FOOTER_NAVIGATION
    )
    return {
        'social_media': SOCIAL_MEDIA_CONFIG,
        'brand': BRAND_CONFIG,
        'newsletter': NEWSLETTER_CONFIG,
        'legal_links': LEGAL_LINKS,
        'navigation': FOOTER_NAVIGATION
    }

def update_social_media(platform, field, value):
    """
    Update a specific field for a social media platform
    
    Args:
        platform (str): Platform key (e.g., 'facebook', 'instagram')
        field (str): Field to update (e.g., 'url', 'enabled', 'stat_text')
        value: New value for the field
    """
    # This is a simplified example - in production you might want to
    # implement a more robust configuration update mechanism
    print(f"To update {platform}.{field} to '{value}':")
    print(f"Edit apps/siteui/social_config.py")
    print(f"Find SOCIAL_MEDIA_CONFIG['{platform}']['{field}'] and change it to '{value}'")

def update_brand_config(field, value):
    """Update brand configuration"""
    print(f"To update brand.{field} to '{value}':")
    print(f"Edit apps/siteui/social_config.py")
    print(f"Find BRAND_CONFIG['{field}'] and change it to '{value}'")

def update_newsletter_config(field, value):
    """Update newsletter configuration"""
    print(f"To update newsletter.{field} to '{value}':")
    print(f"Edit apps/siteui/social_config.py")
    print(f"Find NEWSLETTER_CONFIG['{field}'] and change it to '{value}'")

def print_config_summary():
    """Print a summary of current configuration"""
    config = get_current_config()
    
    print("\n=== SOCIAL MEDIA CONFIGURATION SUMMARY ===")
    print("\nSocial Media Platforms:")
    for platform, settings in config['social_media'].items():
        status = "✓ Enabled" if settings['enabled'] else "✗ Disabled"
        print(f"  {platform.title()}: {status} - {settings['url']}")
    
    print(f"\nBrand: {config['brand']['name']}")
    print(f"Tagline: {config['brand']['tagline']}")
    
    print(f"\nNewsletter Title: {config['newsletter']['title_neon']} {config['newsletter']['title_gradient']}")
    
    print("\nLegal Links:")
    for link in config['legal_links']:
        status = "✓ Enabled" if link['enabled'] else "✗ Disabled"
        print(f"  {link['name']}: {status} - {link['url']}")
    
    print("\nFooter Navigation Sections:")
    for section_key, section in config['navigation'].items():
        enabled_count = sum(1 for link in section['links'] if link['enabled'])
        print(f"  {section['title']}: {enabled_count} enabled links")

if __name__ == "__main__":
    print_config_summary()