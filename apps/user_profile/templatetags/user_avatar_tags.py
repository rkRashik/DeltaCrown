"""
User Avatar Template Tags
=========================

Provides template tags for rendering user avatars.
"""

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

import os

register = template.Library()

DEFAULT_AVATAR = '/static/img/user_avatar/default-avatar.png'


@register.filter
def user_avatar_url(user):
    """
    Get avatar URL for a user.
    
    Usage: {{ user|user_avatar_url }}
    
    Args:
        user: User instance
    
    Returns:
        str: URL to user's avatar image
    """
    try:
        if hasattr(user, 'profile') and user.profile and hasattr(user.profile, 'avatar') and user.profile.avatar:
            # Verify the file actually exists on disk to prevent 404s
            avatar_path = os.path.join(settings.MEDIA_ROOT, str(user.profile.avatar))
            if os.path.isfile(avatar_path):
                return user.profile.avatar.url
    except Exception:
        pass
    
    return DEFAULT_AVATAR


@register.simple_tag
def avatar_img(user, size='medium', css_class=''):
    """
    Render complete avatar image tag.
    
    Usage: {% avatar_img user size="large" css_class="rounded-full" %}
    
    Args:
        user: User instance
        size: 'small' (32px), 'medium' (48px), 'large' (64px), 'xlarge' (96px)
        css_class: Additional CSS classes
    
    Returns:
        HTML img tag
    """
    size_map = {
        'small': '32',
        'medium': '48',
        'large': '64',
        'xlarge': '96',
        'xxlarge': '128'
    }
    
    px_size = size_map.get(size, '48')
    avatar_url = user_avatar_url(user)
    username = getattr(user, 'username', 'User')
    
    html = f'''<img 
        src="{avatar_url}" 
        alt="{username}" 
        width="{px_size}" 
        height="{px_size}"
        class="user-avatar {css_class}"
        onerror="this.src='" + DEFAULT_AVATAR + "'"
    />'''
    
    return mark_safe(html)


@register.simple_tag
def avatar_with_badge(user, size='medium', show_verified=True):
    """
    Render avatar with verification badge if applicable.
    
    Usage: {% avatar_with_badge user size="large" %}
    
    Args:
        user: User instance
        size: Avatar size
        show_verified: Whether to show verification badge
    
    Returns:
        HTML with avatar and badge
    """
    avatar_url = user_avatar_url(user)
    username = getattr(user, 'username', 'User')
    
    size_map = {
        'small': '32',
        'medium': '48',
        'large': '64',
        'xlarge': '96'
    }
    px_size = size_map.get(size, '48')
    
    # Check if user is verified
    is_verified = False
    if hasattr(user, 'profile') and user.profile:
        is_verified = getattr(user.profile, 'kyc_status', '') == 'verified'
    
    badge_html = ''
    if show_verified and is_verified:
        badge_html = '''
            <span class="verification-badge" title="Verified User">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="#06b6d4">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
            </span>
        '''
    
    html = f'''
    <div class="avatar-container" style="position: relative; display: inline-block;">
        <img 
            src="{avatar_url}" 
            alt="{username}" 
            width="{px_size}" 
            height="{px_size}"
            class="user-avatar"
            style="border-radius: 50%; object-fit: cover;"
            onerror="this.src='" + DEFAULT_AVATAR + "'"
        />
        {badge_html}
    </div>
    '''
    
    return mark_safe(html)
