# Social Media & Footer Configuration Guide

This system allows you to easily manage all social media links, footer content, and navigation without touching template files.

## Configuration File Location
```
apps/siteui/social_config.py
```

## Quick Start

### 1. Update Social Media Links
Edit `apps/siteui/social_config.py` and find the `SOCIAL_MEDIA_CONFIG` section:

```python
SOCIAL_MEDIA_CONFIG = {
    'discord': {
        'name': 'Discord',
        'url': 'https://discord.gg/deltacrown',  # ← Update this URL
        'icon_class': 'fab fa-discord',
        'stat_text': 'Join Community',
        'aria_label': 'Discord Community',
        'enabled': True,  # ← Set to False to hide this platform
    },
    'facebook': {
        'name': 'Facebook',
        'url': 'https://facebook.com/deltacrown',  # ← Update this URL
        # ... other settings
    },
    # ... more platforms
}
```

### 2. Enable/Disable Platforms
Set `'enabled': True` or `'enabled': False` for any platform to show/hide it.

### 3. Update Brand Information
Find the `BRAND_CONFIG` section:

```python
BRAND_CONFIG = {
    'name': 'DeltaCrown',
    'tagline': 'Next-Gen Esports',  # ← Update tagline
    'description': 'Your new description here',  # ← Update description
    'stats': {
        'players': {
            'number': '75K+',  # ← Update player count
            'label': 'Players'
        },
        # ... more stats
    }
}
```

### 4. Update Newsletter Settings
Find the `NEWSLETTER_CONFIG` section:

```python
NEWSLETTER_CONFIG = {
    'title_neon': 'Stay',  # ← First part of title
    'title_gradient': 'Connected',  # ← Second part of title
    'subtitle': 'Get exclusive gaming news...',  # ← Update subtitle
    'placeholder': 'Enter your email address',  # ← Input placeholder
    'button_text': 'Subscribe',  # ← Button text
    'privacy_text': 'Your privacy is protected...'  # ← Privacy note
}
```

### 5. Update Footer Navigation Links
Find the `FOOTER_NAVIGATION` section:

```python
FOOTER_NAVIGATION = {
    'company': {
        'title': 'Company',
        'links': [
            {'name': 'About Us', 'url': '/about/', 'enabled': True},
            {'name': 'Careers', 'url': '/careers/', 'enabled': False},  # ← Disabled
            # ... more links
        ]
    },
    # ... more sections
}
```

### 6. Update Legal Links
Find the `LEGAL_LINKS` section:

```python
LEGAL_LINKS = [
    {
        'name': 'Privacy Policy',
        'url': '/privacy/',  # ← Update URL
        'enabled': True,
    },
    # ... more legal links
]
```

## Management Commands

### View Current Configuration
```bash
python manage.py show_footer_config
```

This will display all current settings and their status.

## File Structure

```
apps/siteui/
├── social_config.py              # ← Main configuration file (EDIT THIS)
├── config_manager.py             # Configuration utilities
├── templatetags/
│   └── footer_tags.py           # Template tags for footer
└── management/commands/
    └── show_footer_config.py    # Management command
```

## Important Notes

1. **After making changes**, restart your Django development server
2. **URLs can be absolute** (`https://facebook.com/yourpage`) or **relative** (`/about/`)
3. **Django URL names** are supported - set `'is_url_name': True` in the link config
4. **Enable/disable any section** by setting `'enabled': False`

## Common Tasks

### Add a New Social Platform
1. Add new entry to `SOCIAL_MEDIA_CONFIG`
2. Add corresponding CSS styles in `static/siteui/css/footer.css`
3. Make sure FontAwesome icon class is available

### Remove a Platform
Set `'enabled': False` instead of deleting the configuration.

### Change Social Media URLs
Simply update the `'url'` field for each platform.

### Update Site Statistics
Modify the `stats` section in `BRAND_CONFIG`.

### Add New Footer Sections
Add new sections to `FOOTER_NAVIGATION` following the existing pattern.

## Need Help?

- Configuration file: `apps/siteui/social_config.py`
- Template file: `templates/partials/footer_fixed.html` (don't edit this unless needed)
- CSS file: `static/siteui/css/footer.css`
- Run: `python manage.py show_footer_config` to see current settings