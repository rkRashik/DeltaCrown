# apps/user_profile/templatetags/profile_tags.py
"""
Template tags and filters for user profile privacy and verification.

Usage in templates:
    {% load profile_tags %}
    
    {# Check if a field is visible to the current viewer #}
    {% if profile|can_view_field:request.user:"show_email" %}
        <p>Email: {{ profile.user.email }}</p>
    {% endif %}
    
    {# Display KYC verification badge #}
    {{ profile|kyc_badge }}
    
    {# Check if user can interact (team invite, DM, etc.) #}
    {% if profile|can_interact:request.user:"team_invite" %}
        <button>Invite to Team</button>
    {% endif %}
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html

register = template.Library()


@register.filter
def can_view_field(profile, viewer_and_field):
    """
    Check if viewer can see a specific field on the profile.
    
    Usage: {% if profile|can_view_field:request.user:"show_email" %}
    
    Args:
        profile: UserProfile instance
        viewer_and_field: String in format "viewer:field_name" or tuple (viewer, field_name)
    
    Returns:
        Boolean indicating if field is visible
    """
    if isinstance(viewer_and_field, str):
        # Parse "viewer:field_name" format
        parts = viewer_and_field.split(':')
        if len(parts) != 2:
            return False
        viewer, field_name = parts
    else:
        # Assume tuple (viewer, field_name)
        viewer, field_name = viewer_and_field
    
    # Get privacy settings
    try:
        privacy_settings = profile.privacy_settings
    except Exception:
        # No privacy settings - default to visible
        return True
    
    # Use the allows_viewing method
    return privacy_settings.allows_viewing(viewer, field_name)


@register.simple_tag
def check_field_visibility(profile, viewer, field_name):
    """
    Template tag to check field visibility.
    
    Usage: {% check_field_visibility profile request.user "show_email" as can_see_email %}
           {% if can_see_email %}...{% endif %}
    
    Args:
        profile: UserProfile instance
        viewer: User instance (request.user)
        field_name: Name of the privacy field (e.g., "show_email")
    
    Returns:
        Boolean indicating if field is visible
    """
    try:
        privacy_settings = profile.privacy_settings
        return privacy_settings.allows_viewing(viewer, field_name)
    except Exception:
        # Default to visible if no privacy settings
        return True


@register.filter
def kyc_badge(profile):
    """
    Display a KYC verification badge for the profile.
    
    Usage: {{ profile|kyc_badge }}
    
    Returns:
        HTML badge showing KYC verification status
    """
    if not profile:
        return ''
    
    if profile.kyc_status == 'verified':
        return mark_safe(
            '<span class="kyc-badge verified" title="KYC Verified">'
            '<svg class="w-4 h-4 inline" fill="currentColor" viewBox="0 0 20 20">'
            '<path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>'
            '</svg>'
            '<span class="ml-1">Verified</span>'
            '</span>'
        )
    elif profile.kyc_status == 'pending':
        return mark_safe(
            '<span class="kyc-badge pending" title="KYC Pending Review">'
            '<svg class="w-4 h-4 inline" fill="currentColor" viewBox="0 0 20 20">'
            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>'
            '</svg>'
            '<span class="ml-1">Pending</span>'
            '</span>'
        )
    elif profile.kyc_status == 'rejected':
        return mark_safe(
            '<span class="kyc-badge rejected" title="KYC Rejected">'
            '<svg class="w-4 h-4 inline" fill="currentColor" viewBox="0 0 20 20">'
            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>'
            '</svg>'
            '<span class="ml-1">Rejected</span>'
            '</span>'
        )
    else:
        return ''


@register.filter
def kyc_badge_simple(profile):
    """
    Display a simple text KYC badge (no HTML/SVG).
    
    Usage: {{ profile|kyc_badge_simple }}
    
    Returns:
        Simple text badge
    """
    if not profile:
        return ''
    
    if profile.kyc_status == 'verified':
        return mark_safe('<span class="text-green-600 font-semibold">✓ Verified</span>')
    elif profile.kyc_status == 'pending':
        return mark_safe('<span class="text-yellow-600">⏳ Pending</span>')
    elif profile.kyc_status == 'rejected':
        return mark_safe('<span class="text-red-600">✗ Rejected</span>')
    else:
        return ''


@register.filter
def can_interact(profile, viewer_and_action):
    """
    Check if viewer can perform an interaction with the profile.
    
    Usage: {% if profile|can_interact:request.user:"team_invite" %}
    
    Args:
        profile: UserProfile instance
        viewer_and_action: String in format "viewer:action" where action is:
            - team_invite
            - friend_request
            - direct_message
    
    Returns:
        Boolean indicating if interaction is allowed
    """
    if isinstance(viewer_and_action, str):
        parts = viewer_and_action.split(':')
        if len(parts) != 2:
            return False
        viewer, action = parts
    else:
        viewer, action = viewer_and_action
    
    # Owner and staff can always interact
    if hasattr(viewer, 'profile') and viewer.profile == profile:
        return True
    if hasattr(viewer, 'is_staff') and viewer.is_staff:
        return True
    
    # Check privacy settings
    try:
        privacy_settings = profile.privacy_settings
    except Exception:
        # No privacy settings - default to allowed
        return True
    
    action_map = {
        'team_invite': privacy_settings.allow_team_invites,
        'friend_request': privacy_settings.allow_friend_requests,
        'direct_message': privacy_settings.allow_direct_messages,
    }
    
    return action_map.get(action, False)


@register.simple_tag
def profile_privacy_summary(profile):
    """
    Get a summary of profile privacy settings.
    
    Usage: {% profile_privacy_summary profile as privacy_info %}
           Visible: {{ privacy_info.visible_count }}/{{ privacy_info.total_count }}
    
    Returns:
        Dict with privacy statistics
    """
    try:
        privacy_settings = profile.privacy_settings
        
        fields = [
            'show_real_name', 'show_phone', 'show_email', 'show_age',
            'show_gender', 'show_country', 'show_address', 'show_game_ids',
            'show_match_history', 'show_teams', 'show_achievements',
            'show_inventory_value', 'show_level_xp', 'show_social_links'
        ]
        
        visible_count = sum(getattr(privacy_settings, field, False) for field in fields)
        
        return {
            'visible_count': visible_count,
            'total_count': len(fields),
            'allow_team_invites': privacy_settings.allow_team_invites,
            'allow_friend_requests': privacy_settings.allow_friend_requests,
            'allow_direct_messages': privacy_settings.allow_direct_messages,
        }
    except Exception:
        return {
            'visible_count': 0,
            'total_count': 14,
            'allow_team_invites': True,
            'allow_friend_requests': True,
            'allow_direct_messages': True,
        }


@register.inclusion_tag('user_profile/includes/privacy_indicator.html')
def privacy_indicator(profile, viewer):
    """
    Render a privacy indicator showing what the viewer can see.
    
    Usage: {% privacy_indicator profile request.user %}
    
    Returns:
        Context for rendering privacy indicator template
    """
    try:
        privacy_settings = profile.privacy_settings
        
        # Check various permission categories
        can_see_contact = any([
            privacy_settings.allows_viewing(viewer, 'show_email'),
            privacy_settings.allows_viewing(viewer, 'show_phone'),
            privacy_settings.allows_viewing(viewer, 'show_address'),
        ])
        
        can_see_personal = any([
            privacy_settings.allows_viewing(viewer, 'show_real_name'),
            privacy_settings.allows_viewing(viewer, 'show_age'),
            privacy_settings.allows_viewing(viewer, 'show_gender'),
        ])
        
        can_see_gaming = any([
            privacy_settings.allows_viewing(viewer, 'show_game_ids'),
            privacy_settings.allows_viewing(viewer, 'show_match_history'),
            privacy_settings.allows_viewing(viewer, 'show_teams'),
        ])
        
        return {
            'profile': profile,
            'viewer': viewer,
            'can_see_contact': can_see_contact,
            'can_see_personal': can_see_personal,
            'can_see_gaming': can_see_gaming,
        }
    except Exception:
        return {
            'profile': profile,
            'viewer': viewer,
            'can_see_contact': True,
            'can_see_personal': True,
            'can_see_gaming': True,
        }
