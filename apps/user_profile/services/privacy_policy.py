"""
Profile Visibility Policy Service

Centralized privacy enforcement for UserProfile data access.
Implements role-based field filtering: owner, public, staff.

See: Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_03_PRIVACY_ENFORCEMENT_MODEL.md
"""
from typing import Set, Dict, Any, Optional
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class ProfileVisibilityPolicy:
    """
    Service for enforcing profile data visibility based on viewer role.
    
    Visibility Levels:
    - Owner (viewer == profile.user): All fields visible
    - Public (anonymous or non-owner): Only non-PII fields visible
    - Staff (is_staff=True): All fields + admin metadata visible
    
    PII Fields (Hidden by Default):
    - email, phone, address, postal_code, real_full_name, date_of_birth,
      nationality, emergency_contact_*, kyc_status, kyc_verified_at
    
    Example:
        >>> policy = ProfileVisibilityPolicy()
        >>> visible_fields = policy.get_visible_fields(viewer, profile)
        >>> filtered_data = policy.filter_profile_data(viewer, profile, data)
    """
    
    # Fields always visible to everyone (public profile)
    PUBLIC_FIELDS = {
        'id', 'user_id', 'public_id', 'uuid', 'display_name', 'slug',
        'avatar', 'banner', 'bio', 'pronouns',
        'level', 'xp', 'reputation_score', 'skill_rating',
        'pinned_badges', 'inventory_items',
        'region', 'country',  # Country/region only (not city/address)
        'youtube_link', 'twitch_link', 'discord_id', 'facebook',
        'instagram', 'tiktok', 'twitter', 'stream_status',
        'preferred_games', 'game_profiles',
        'created_at', 'updated_at',
    }
    
    # Fields visible only to profile owner
    OWNER_ONLY_FIELDS = {
        'email', 'phone',
        'city', 'postal_code', 'address',
        'real_full_name', 'date_of_birth', 'nationality', 'gender',
        'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
        'deltacoin_balance', 'lifetime_earnings',
        'kyc_status', 'kyc_verified_at',
    }
    
    # Fields visible to staff (in addition to public + owner fields)
    STAFF_ONLY_FIELDS = {
        'internal_notes',  # If exists
        'moderation_flags',  # If exists
        'last_login_ip',  # If exists
    }
    
    # All fields (complete set)
    ALL_FIELDS = PUBLIC_FIELDS | OWNER_ONLY_FIELDS | STAFF_ONLY_FIELDS
    
    @classmethod
    def can_view_profile(cls, viewer: Optional[User], profile: 'UserProfile') -> bool:
        """
        Check if viewer can see the profile at all.
        
        Args:
            viewer: User viewing the profile (None for anonymous)
            profile: UserProfile being viewed
        
        Returns:
            bool: True if viewer can see profile, False if blocked
        
        Note:
            Currently all profiles are public (returns True).
            Future: Implement profile-level privacy settings.
        """
        # Future: Check profile.privacy_settings.profile_visibility
        # For now, all profiles are public
        return True
    
    @classmethod
    def get_visible_fields(cls, viewer: Optional[User], profile: 'UserProfile') -> Set[str]:
        """
        Get set of field names visible to viewer.
        
        Args:
            viewer: User viewing the profile (None for anonymous)
            profile: UserProfile being viewed
        
        Returns:
            Set[str]: Field names that viewer can see
        
        Example:
            >>> fields = ProfileVisibilityPolicy.get_visible_fields(request.user, profile)
            >>> if 'email' in fields:
            >>>     print(profile.email)
        """
        # Anonymous or not authenticated → public fields only
        if not viewer or not viewer.is_authenticated:
            return cls.PUBLIC_FIELDS.copy()
        
        # Owner viewing own profile → all fields
        if viewer.id == profile.user_id:
            return cls.ALL_FIELDS.copy()
        
        # Staff viewing any profile → public + owner + staff fields
        if viewer.is_staff or viewer.is_superuser:
            return cls.ALL_FIELDS.copy()
        
        # Authenticated non-owner → public fields only
        return cls.PUBLIC_FIELDS.copy()
    
    @classmethod
    def filter_profile_data(
        cls,
        viewer: Optional[User],
        profile: 'UserProfile',
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filter dictionary of profile data based on viewer permissions.
        
        Args:
            viewer: User viewing the profile (None for anonymous)
            profile: UserProfile being viewed
            data: Dictionary of profile fields
        
        Returns:
            Dict[str, Any]: Filtered dictionary with only visible fields
        
        Example:
            >>> profile_data = model_to_dict(profile)
            >>> filtered = ProfileVisibilityPolicy.filter_profile_data(request.user, profile, profile_data)
            >>> return JsonResponse(filtered)
        """
        visible_fields = cls.get_visible_fields(viewer, profile)
        
        filtered = {}
        for key, value in data.items():
            if key in visible_fields:
                filtered[key] = value
            else:
                logger.debug(
                    f"Filtered field '{key}' from profile_id={profile.id} "
                    f"for viewer_id={viewer.id if viewer else 'anonymous'}"
                )
        
        return filtered
    
    @classmethod
    def is_pii_field(cls, field_name: str) -> bool:
        """
        Check if field contains PII (Personally Identifiable Information).
        
        Args:
            field_name: Name of the field
        
        Returns:
            bool: True if field is PII, False otherwise
        
        Example:
            >>> ProfileVisibilityPolicy.is_pii_field('email')
            True
            >>> ProfileVisibilityPolicy.is_pii_field('display_name')
            False
        """
        return field_name in cls.OWNER_ONLY_FIELDS
    
    @classmethod
    def redact_pii_for_logs(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact PII fields from dictionary for safe logging.
        
        Args:
            data: Dictionary containing profile data
        
        Returns:
            Dict[str, Any]: Dictionary with PII fields redacted
        
        Example:
            >>> log_data = ProfileVisibilityPolicy.redact_pii_for_logs(profile_dict)
            >>> logger.info(f"Profile data: {log_data}")
        """
        redacted = data.copy()
        for field in cls.OWNER_ONLY_FIELDS:
            if field in redacted:
                redacted[field] = '***REDACTED***'
        return redacted
    
    @classmethod
    def get_field_visibility_summary(cls, viewer: Optional[User], profile: 'UserProfile') -> Dict[str, str]:
        """
        Get human-readable summary of field visibility for debugging.
        
        Args:
            viewer: User viewing the profile
            profile: UserProfile being viewed
        
        Returns:
            Dict[str, str]: Field name → visibility reason
        
        Example:
            >>> summary = ProfileVisibilityPolicy.get_field_visibility_summary(request.user, profile)
            >>> # {'email': 'HIDDEN (owner-only)', 'display_name': 'VISIBLE (public)'}
        """
        visible_fields = cls.get_visible_fields(viewer, profile)
        
        summary = {}
        for field in cls.ALL_FIELDS:
            if field in visible_fields:
                if field in cls.PUBLIC_FIELDS:
                    summary[field] = 'VISIBLE (public)'
                elif field in cls.OWNER_ONLY_FIELDS:
                    summary[field] = 'VISIBLE (owner)'
                elif field in cls.STAFF_ONLY_FIELDS:
                    summary[field] = 'VISIBLE (staff)'
            else:
                if field in cls.OWNER_ONLY_FIELDS:
                    summary[field] = 'HIDDEN (owner-only)'
                elif field in cls.STAFF_ONLY_FIELDS:
                    summary[field] = 'HIDDEN (staff-only)'
                else:
                    summary[field] = 'HIDDEN (unknown)'
        
        return summary


def get_profile_context_for_template(viewer: Optional[User], profile: 'UserProfile') -> Dict[str, Any]:
    """
    Helper function for template context: Get profile data filtered by visibility policy.
    
    Args:
        viewer: User viewing the profile
        profile: UserProfile to render
    
    Returns:
        Dict: Context dictionary with visible fields only
    
    Usage in views:
        >>> context = get_profile_context_for_template(request.user, profile)
        >>> return render(request, 'profile.html', context)
    """
    from django.forms.models import model_to_dict
    
    # Get all profile fields as dict
    profile_data = model_to_dict(profile)
    
    # Filter by visibility policy
    filtered_data = ProfileVisibilityPolicy.filter_profile_data(viewer, profile, profile_data)
    
    # Add computed properties (not in model_to_dict)
    filtered_data['is_owner'] = viewer and viewer.is_authenticated and viewer.id == profile.user_id
    filtered_data['is_staff_viewing'] = viewer and (viewer.is_staff or viewer.is_superuser)
    
    return {'profile': filtered_data}
