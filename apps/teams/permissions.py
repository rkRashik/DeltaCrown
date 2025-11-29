# apps/teams/permissions.py
"""
Centralized permission checking for team operations.

This module implements the professional role hierarchy:
- OWNER: Root admin, full control
- MANAGER: Administrative powers, cannot delete team
- COACH: View-only access
- PLAYER/SUBSTITUTE: Member access
- Captain Title: Special badge for in-game leader
"""

from typing import Optional
from .models import TeamMembership


class TeamPermissions:
    """
    Centralized permission checker for all team operations.
    
    Usage:
        membership = TeamMembership.objects.get(team=team, profile=profile)
        if TeamPermissions.can_delete_team(membership):
            # Allow deletion
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # OWNER-ONLY PERMISSIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def can_delete_team(membership: Optional[TeamMembership]) -> bool:
        """
        Only OWNER can delete the team.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can delete team
        """
        if not membership:
            return False
        return membership.role == TeamMembership.Role.OWNER
    
    @staticmethod
    def can_transfer_ownership(membership: Optional[TeamMembership]) -> bool:
        """
        Only OWNER can transfer ownership to another member.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can transfer ownership
        """
        if not membership:
            return False
        return membership.role == TeamMembership.Role.OWNER
    
    @staticmethod
    def can_assign_managers(membership: Optional[TeamMembership]) -> bool:
        """
        Only OWNER can assign or remove Manager roles.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can assign managers
        """
        if not membership:
            return False
        return membership.role == TeamMembership.Role.OWNER
    
    # ═══════════════════════════════════════════════════════════════════════
    # OWNER + MANAGER PERMISSIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def can_manage_roster(membership: Optional[TeamMembership]) -> bool:
        """
        OWNER and MANAGER can manage roster (invite/kick members).
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can manage roster
        """
        if not membership:
            return False
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    @staticmethod
    def can_edit_team_profile(membership: Optional[TeamMembership]) -> bool:
        """
        OWNER and MANAGER can edit team profile (name, logo, description, etc).
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can edit team profile
        """
        if not membership:
            return False
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    @staticmethod
    def can_register_tournaments(membership: Optional[TeamMembership]) -> bool:
        """
        OWNER and MANAGER can register team for tournaments.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can register for tournaments
        """
        if not membership:
            return False
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    @staticmethod
    def can_assign_captain_title(membership: Optional[TeamMembership]) -> bool:
        """
        OWNER and MANAGER can assign/remove captain title.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can assign captain title
        """
        if not membership:
            return False
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    @staticmethod
    def can_assign_coach(membership: Optional[TeamMembership]) -> bool:
        """
        OWNER and MANAGER can assign/remove coach role.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can assign coaches
        """
        if not membership:
            return False
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    @staticmethod
    def can_change_player_role(membership: Optional[TeamMembership]) -> bool:
        """
        OWNER and MANAGER can change in-game player roles (dual-role system).
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can change player roles
        """
        if not membership:
            return False
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    # ═══════════════════════════════════════════════════════════════════════
    # VIEW PERMISSIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def can_view_roster(membership: Optional[TeamMembership]) -> bool:
        """
        All team members can view roster.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can view roster
        """
        if not membership:
            return False
        return membership.status == TeamMembership.Status.ACTIVE
    
    @staticmethod
    def can_view_team_settings(membership: Optional[TeamMembership]) -> bool:
        """
        OWNER, MANAGER, and COACH can view team settings.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can view settings
        """
        if not membership:
            return False
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER,
            TeamMembership.Role.COACH
        ]
    
    # ═══════════════════════════════════════════════════════════════════════
    # MEMBER ACTIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def can_leave_team(membership: Optional[TeamMembership]) -> bool:
        """
        All members except OWNER can leave team, unless locked for tournament.
        OWNER must transfer ownership before leaving.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can leave team
        """
        if not membership:
            return False
        
        # Owners cannot leave (must transfer first)
        if membership.role == TeamMembership.Role.OWNER:
            return False
        
        # Check if member is locked for tournament
        if membership.is_locked_for_tournament():
            return False
        
        return True
    
    @staticmethod
    def can_ready_up_match(membership: Optional[TeamMembership]) -> bool:
        """
        OWNER, MANAGER, Captain-titled players, and active players can ready up.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user can ready up for matches
        """
        if not membership:
            return False
        
        # Owners and Managers always can
        if membership.role in [TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER]:
            return True
        
        # Captain-titled players can
        if membership.is_captain:
            return True
        
        # Regular active players can
        if membership.role == TeamMembership.Role.PLAYER and membership.status == TeamMembership.Status.ACTIVE:
            return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # PERMISSION SUMMARY HELPERS
    # ═══════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def get_permission_summary(membership: Optional[TeamMembership]) -> dict:
        """
        Get a complete summary of all permissions for a membership.
        Useful for frontend to determine what UI elements to show.
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            dict: Dictionary of all permissions
        """
        if not membership:
            return {
                'can_delete_team': False,
                'can_transfer_ownership': False,
                'can_assign_managers': False,
                'can_manage_roster': False,
                'can_edit_team_profile': False,
                'can_register_tournaments': False,
                'can_assign_captain_title': False,
                'can_assign_coach': False,
                'can_change_player_role': False,
                'can_view_roster': False,
                'can_view_team_settings': False,
                'can_leave_team': False,
                'can_ready_up_match': False,
                'role': None,
                'is_captain': False
            }
        
        return {
            'can_delete_team': TeamPermissions.can_delete_team(membership),
            'can_transfer_ownership': TeamPermissions.can_transfer_ownership(membership),
            'can_assign_managers': TeamPermissions.can_assign_managers(membership),
            'can_manage_roster': TeamPermissions.can_manage_roster(membership),
            'can_edit_team_profile': TeamPermissions.can_edit_team_profile(membership),
            'can_register_tournaments': TeamPermissions.can_register_tournaments(membership),
            'can_assign_captain_title': TeamPermissions.can_assign_captain_title(membership),
            'can_assign_coach': TeamPermissions.can_assign_coach(membership),
            'can_change_player_role': TeamPermissions.can_change_player_role(membership),
            'can_view_roster': TeamPermissions.can_view_roster(membership),
            'can_view_team_settings': TeamPermissions.can_view_team_settings(membership),
            'can_leave_team': TeamPermissions.can_leave_team(membership),
            'can_ready_up_match': TeamPermissions.can_ready_up_match(membership),
            'role': membership.role,
            'is_captain': membership.is_captain
        }
    
    @staticmethod
    def is_admin(membership: Optional[TeamMembership]) -> bool:
        """
        Check if user is an admin (OWNER or MANAGER).
        
        Args:
            membership: TeamMembership instance
            
        Returns:
            bool: True if user is admin
        """
        if not membership:
            return False
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]


# Decorator for view permission checking
def require_team_permission(permission_func):
    """
    Decorator to check team permissions before executing view.
    
    Usage:
        @require_team_permission(TeamPermissions.can_edit_team_profile)
        def edit_team_view(request, slug):
            # ... view logic
    """
    def decorator(view_func):
        def wrapper(request, slug, *args, **kwargs):
            from django.http import JsonResponse
            from django.shortcuts import get_object_or_404
            from .models import Team
            from .views.utils import _ensure_profile
            
            team = get_object_or_404(Team, slug=slug)
            profile = _ensure_profile(request.user)
            
            if not profile:
                return JsonResponse(
                    {"error": "Authentication required"},
                    status=401
                )
            
            try:
                membership = TeamMembership.objects.get(
                    team=team,
                    profile=profile,
                    status=TeamMembership.Status.ACTIVE
                )
            except TeamMembership.DoesNotExist:
                return JsonResponse(
                    {"error": "You are not a member of this team"},
                    status=403
                )
            
            if not permission_func(membership):
                return JsonResponse(
                    {"error": "You don't have permission to perform this action"},
                    status=403
                )
            
            # Pass membership to view for convenience
            kwargs['membership'] = membership
            return view_func(request, slug, *args, **kwargs)
        
        return wrapper
    return decorator
