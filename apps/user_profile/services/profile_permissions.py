"""
Profile Privacy Permission Checker (Phase 5B)

Compute viewer-role permissions for profile sections.
Used by profile_public_v2 view to pass can_view_* flags to template.
"""
from typing import Optional
from django.contrib.auth import get_user_model
from apps.user_profile.models_main import PrivacySettings, UserProfile
from apps.user_profile.services.follow_service import FollowService

User = get_user_model()


class ProfilePermissionChecker:
    """
    Compute granular permissions for profile viewing.
    
    Viewer Roles:
    - owner: viewing own profile (full access)
    - follower: following the profile (follower-only access)
    - visitor: logged in but not following (public access)
    - anonymous: not logged in (public access)
    """
    
    def __init__(self, viewer: Optional[User], profile: UserProfile):
        """
        Args:
            viewer: User viewing the profile (None for anonymous)
            profile: UserProfile being viewed
        """
        self.viewer = viewer
        self.profile = profile
        self.profile_user = profile.user
        
        # Get privacy settings (canonical source)
        self.privacy, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        
        # Compute viewer role
        self.is_owner = viewer and viewer.is_authenticated and viewer.id == self.profile_user.id
        self.is_follower = (
            viewer and viewer.is_authenticated and not self.is_owner and
            FollowService.is_following(follower_user=viewer, followee_user=self.profile_user)
        )
        self.is_visitor = viewer and viewer.is_authenticated and not self.is_owner and not self.is_follower
        self.is_anonymous = not viewer or not viewer.is_authenticated
    
    def get_viewer_role(self) -> str:
        """Get viewer role as string"""
        if self.is_owner:
            return 'owner'
        elif self.is_follower:
            return 'follower'
        elif self.is_visitor:
            return 'visitor'
        else:
            return 'anonymous'
    
    def can_view_profile(self) -> bool:
        """Can viewer see profile at all?"""
        # Owner always sees own profile
        if self.is_owner:
            return True
        
        # PHASE 6B: Check private account first (takes precedence over visibility_preset)
        if self.privacy.is_private_account:
            # Use Phase 6A helper to check if viewer is approved follower
            return FollowService.can_view_private_profile(
                viewer=self.viewer,
                owner=self.profile_user
            )
        
        # UP-PHASE12B: Use visibility_preset (profile_visibility was removed in Phase 11)
        # PRIVATE preset = only owner can view
        # PROTECTED preset = limited info to non-followers (but profile still viewable)
        # PUBLIC preset = everyone can view
        visibility = getattr(self.privacy, 'visibility_preset', 'PUBLIC')
        
        if visibility == 'PRIVATE':
            return False
        elif visibility == 'PROTECTED':
            # PROTECTED allows viewing but limits what's shown (handled by other permission methods)
            return True
        else:  # PUBLIC
            return True
    
    def can_view_game_passports(self) -> bool:
        """Can viewer see game passports?"""
        if self.is_owner:
            return True
        if not self.privacy.show_game_ids:
            return False
        return self.can_view_profile()
    
    def can_view_wallet(self) -> bool:
        """Can viewer see wallet balance?"""
        # Wallet always private (owner only)
        return self.is_owner
    
    def can_view_achievements(self) -> bool:
        """Can viewer see achievements/badges?"""
        if self.is_owner:
            return True
        if not self.privacy.show_achievements:
            return False
        return self.can_view_profile()
    
    def can_view_match_history(self) -> bool:
        """Can viewer see match records?"""
        if self.is_owner:
            return True
        if not self.privacy.show_match_history:
            return False
        return self.can_view_profile()
    
    def can_view_teams(self) -> bool:
        """Can viewer see team memberships?"""
        if self.is_owner:
            return True
        if not self.privacy.show_teams:
            return False
        return self.can_view_profile()
    
    def can_view_social_links(self) -> bool:
        """Can viewer see social media links?"""
        if self.is_owner:
            return True
        if not self.privacy.show_social_links:
            return False
        return self.can_view_profile()
    
    def can_send_message(self) -> bool:
        """Can viewer send direct messages?"""
        if self.is_owner:
            return False  # Can't DM yourself
        if not self.privacy.allow_direct_messages:
            return False
        return self.viewer and self.viewer.is_authenticated
    
    def can_send_team_invite(self) -> bool:
        """Can viewer send team invitation?"""
        if self.is_owner:
            return False  # Can't invite yourself
        if not self.privacy.allow_team_invites:
            return False
        return self.viewer and self.viewer.is_authenticated
    
    def get_all_permissions(self) -> dict:
        """
        Get all permission flags as dict for template context.
        
        Returns:
            Dict with can_view_* and can_* flags
        """
        return {
            'viewer_role': self.get_viewer_role(),
            'is_own_profile': self.is_owner,
            'can_view_profile': self.can_view_profile(),
            'can_view_game_passports': self.can_view_game_passports(),
            'can_view_wallet': self.can_view_wallet(),
            'can_view_achievements': self.can_view_achievements(),
            'can_view_match_history': self.can_view_match_history(),
            'can_view_teams': self.can_view_teams(),
            'can_view_social_links': self.can_view_social_links(),
            'can_send_message': self.can_send_message(),
            'can_send_team_invite': self.can_send_team_invite(),
        }
