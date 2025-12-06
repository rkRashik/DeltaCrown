# apps/teams/api/permissions.py
"""
Team API Permission Classes (Module 3.3)

Custom DRF permissions for team operations.
Follows ADR-008 (Security Architecture) and Module 3.2 patterns.

Traceability:
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md#adr-008
"""
from rest_framework import permissions

from apps.teams.models._legacy import Team, TeamMembership, TeamInvite
from apps.user_profile.models import UserProfile


class IsTeamCaptain(permissions.BasePermission):
    """
    Permission: User must be the team captain.
    
    Used for:
    - Update team
    - Invite player
    - Transfer captain
    - Remove member
    - Disband team
    """
    message = "Only the team captain can perform this action."
    
    def has_object_permission(self, request, view, obj):
        """Check if user is captain of the team."""
        if isinstance(obj, Team):
            team = obj
        elif hasattr(obj, 'team'):
            team = obj.team
        else:
            return False
        
        # Get or create user profile
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            return team.captain == profile
        except Exception:
            return False


class IsTeamMember(permissions.BasePermission):
    """
    Permission: User must be an active team member.
    
    Used for:
    - Leave team
    - View private team details (if implemented)
    """
    message = "You must be a team member to perform this action."
    
    def has_object_permission(self, request, view, obj):
        """Check if user is active member of the team."""
        if isinstance(obj, Team):
            team = obj
        elif hasattr(obj, 'team'):
            team = obj.team
        else:
            return False
        
        # Get or create user profile and check active membership
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            return TeamMembership.objects.filter(
                team=team,
                profile=profile,
                status=TeamMembership.Status.ACTIVE
            ).exists()
        except Exception:
            return False


class IsInvitedUser(permissions.BasePermission):
    """
    Permission: User must be the invited user for this invite.
    
    Used for:
    - Respond to invite (accept/decline)
    """
    message = "You can only respond to invites sent to you."
    
    def has_object_permission(self, request, view, obj):
        """Check if user is the invited user."""
        if not isinstance(obj, TeamInvite):
            return False
        
        # Get or create user profile and check if they're the invited user
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            return obj.invited_user_id == profile.id
        except Exception:
            return False
