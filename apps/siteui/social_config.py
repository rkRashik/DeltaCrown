# Social Media Configuration
# Update these settings to manage social media links and information

SOCIAL_MEDIA_CONFIG = {
    'discord': {
        'name': 'Discord',
        'url': 'https://discord.gg/deltacrown',  # Update with your Discord server invite
        'icon_class': 'fab fa-discord',
        'stat_text': 'Join Community',
        'aria_label': 'Discord Community',
        'enabled': True,
    },
    'facebook': {
        'name': 'Facebook',
        'url': 'https://facebook.com/deltacrown',  # Update with your Facebook page
        'icon_class': 'fab fa-facebook-f',
        'stat_text': 'Follow Us',
        'aria_label': 'Facebook Page',
        'enabled': True,
    },
    'twitch': {
        'name': 'Twitch',
        'url': 'https://twitch.tv/deltacrown',  # Update with your Twitch channel
        'icon_class': 'fab fa-twitch',
        'stat_text': 'Watch Live',
        'aria_label': 'Twitch Streams',
        'enabled': True,
    },
    'youtube': {
        'name': 'YouTube',
        'url': 'https://youtube.com/@deltacrown',  # Update with your YouTube channel
        'icon_class': 'fab fa-youtube',
        'stat_text': 'Subscribe',
        'aria_label': 'YouTube Channel',
        'enabled': True,
    },
    'instagram': {
        'name': 'Instagram',
        'url': 'https://instagram.com/deltacrown',  # Update with your Instagram profile
        'icon_class': 'fab fa-instagram',
        'stat_text': 'Follow Us',
        'aria_label': 'Instagram Profile',
        'enabled': True,
    },
}

# Footer Brand Configuration
BRAND_CONFIG = {
    'name': 'DeltaCrown',
    'tagline': 'Next-Gen Esports',
    'description': 'Where legends are forged and champions rise. Experience the future of competitive gaming.',
    'stats': {
        'players': {
            'number': '50K+',
            'label': 'Players'
        },
        'tournaments': {
            'number': '1.2K+',
            'label': 'Tournaments'
        },
        'prizes': {
            'number': '$2M+',
            'label': 'Prizes'
        }
    }
}

# Newsletter Configuration
NEWSLETTER_CONFIG = {
    'title_neon': 'Stay',
    'title_gradient': 'Connected',
    'subtitle': 'Get exclusive gaming news, tournament alerts, and insider updates',
    'placeholder': 'Enter your email address',
    'button_text': 'Subscribe',
    'privacy_text': 'Your privacy is protected. Unsubscribe anytime.'
}

# Legal Links Configuration
LEGAL_LINKS = [
    {
        'name': 'Privacy Policy',
        'url': '/privacy/',  # Update with actual URL
        'enabled': True,
    },
    {
        'name': 'Terms of Service',
        'url': '/terms/',  # Update with actual URL
        'enabled': True,
    },
    {
        'name': 'Cookie Policy',
        'url': '/cookies/',  # Update with actual URL
        'enabled': True,
    },
]

# Footer Navigation Links
FOOTER_NAVIGATION = {
    'company': {
        'title': 'Company',
        'links': [
            {'name': 'About Us', 'url': '/about/', 'enabled': True},
            {'name': 'Careers', 'url': '/careers/', 'enabled': True},
            {'name': 'Press Kit', 'url': '/press/', 'enabled': True},
            {'name': 'Blog', 'url': '/blog/', 'enabled': True},
            {'name': 'Contact', 'url': '/contact/', 'enabled': True},
        ]
    },
    'gaming': {
        'title': 'Gaming',
        'links': [
            {'name': 'Tournaments', 'url': 'tournaments:hub', 'enabled': True, 'is_url_name': True},
            {'name': 'Teams', 'url': 'teams:list', 'enabled': True, 'is_url_name': True},
            {'name': 'Players', 'url': '/players/', 'enabled': False},  # Disabled until implemented
            {'name': 'Dashboard', 'url': 'dashboard:index', 'enabled': True, 'is_url_name': True},
            {'name': 'Leaderboards', 'url': '/leaderboards/', 'enabled': False},  # Disabled until implemented
        ]
    },
    'support': {
        'title': 'Support',
        'links': [
            {'name': 'Help Center', 'url': '/help/', 'enabled': True},
            {'name': 'Community', 'url': '/community/', 'enabled': True},
            {'name': 'Bug Report', 'url': '/bug-report/', 'enabled': True},
            {'name': 'System Status', 'url': '/status/', 'enabled': True},
            {'name': 'API Docs', 'url': '/api/docs/', 'enabled': True},
        ]
    },
    'resources': {
        'title': 'Resources',
        'links': [
            {'name': 'Game Rules', 'url': '/rules/', 'enabled': True},
            {'name': 'Guides', 'url': '/guides/', 'enabled': True},
            {'name': 'Statistics', 'url': '/stats/', 'enabled': True},
            {'name': 'Downloads', 'url': '/downloads/', 'enabled': True},
            {'name': 'Mobile App', 'url': '/mobile/', 'enabled': True},
        ]
    },
}

def get_enabled_social_media():
    """Return only enabled social media platforms"""
    return {key: config for key, config in SOCIAL_MEDIA_CONFIG.items() if config['enabled']}

def get_enabled_legal_links():
    """Return only enabled legal links"""
    return [link for link in LEGAL_LINKS if link['enabled']]

def get_footer_navigation():
    """Return footer navigation with only enabled links"""
    navigation = {}
    for section_key, section in FOOTER_NAVIGATION.items():
        enabled_links = [link for link in section['links'] if link['enabled']]
        if enabled_links:  # Only include sections that have enabled links
            navigation[section_key] = {
                'title': section['title'],
                'links': enabled_links
            }
    return navigation
