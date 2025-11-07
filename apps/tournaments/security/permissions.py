"""
Role-Based Permissions for Tournament System

Provides role scopes and permission classes for REST and WebSocket access control.

Phase 2: Real-Time Features & Security
Module 2.4: Security Hardening

Role Hierarchy:
    - SPECTATOR: Can view tournaments and watch matches (read-only)
    - PLAYER: Can register for tournaments and play matches  
    - ORGANIZER: Can create and manage tournaments
    - ADMIN: Full access to all tournament operations

Usage (REST API):
    from apps.tournaments.security import IsOrganizer
    
    class TournamentViewSet(viewsets.ModelViewSet):
        permission_classes = [IsAuthenticated, IsOrganizer]

Usage (WebSocket):
    from apps.tournaments.security import check_tournament_role, TournamentRole
    
    async def connect(self):
        if not check_tournament_role(self.scope['user'], TournamentRole.PLAYER):
            await self.close(code=4003)
"""

import logging
from enum import Enum
from typing import Optional
from rest_framework import permissions
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class TournamentRole(str, Enum):
    """
    Tournament role scopes.
    
    Roles are hierarchical: ADMIN > ORGANIZER > PLAYER > SPECTATOR
    """
    SPECTATOR = 'spectator'  # Read-only access
    PLAYER = 'player'        # Can participate in tournaments
    ORGANIZER = 'organizer'  # Can create and manage tournaments
    ADMIN = 'admin'          # Full access
    
    @classmethod
    def get_hierarchy(cls) -> dict:
        """
        Get role hierarchy with numeric levels.
        
        Returns:
            Dictionary mapping roles to hierarchy levels (higher = more privileged)
        """
        return {
            cls.SPECTATOR: 1,
            cls.PLAYER: 2,
            cls.ORGANIZER: 3,
            cls.ADMIN: 4,
        }
    
    @classmethod
    def has_permission(cls, user_role: 'TournamentRole', required_role: 'TournamentRole') -> bool:
        """
        Check if user_role meets or exceeds required_role.
        
        Args:
            user_role: Role assigned to user
            required_role: Minimum role required for action
            
        Returns:
            True if user_role >= required_role in hierarchy
            
        Example:
            >>> TournamentRole.has_permission(TournamentRole.ORGANIZER, TournamentRole.PLAYER)
            True
            >>> TournamentRole.has_permission(TournamentRole.SPECTATOR, TournamentRole.ORGANIZER)
            False
        """
        hierarchy = cls.get_hierarchy()
        return hierarchy.get(user_role, 0) >= hierarchy.get(required_role, 0)


def get_user_tournament_role(user) -> TournamentRole:
    """
    Determine user's tournament role based on permissions and attributes.
    
    Args:
        user: Django User instance
        
    Returns:
        TournamentRole enum value
        
    Logic:
        1. Check if user is staff/superuser → ADMIN
        2. Check if user has 'can_organize_tournaments' permission → ORGANIZER
        3. Check if user has active registrations → PLAYER
        4. Default → SPECTATOR
    """
    if not user or not user.is_authenticated:
        return TournamentRole.SPECTATOR
    
    # Staff and superusers have admin access
    if user.is_staff or user.is_superuser:
        return TournamentRole.ADMIN
    
    # Check for organizer permission
    # In future, could check for custom permission or group membership
    if hasattr(user, 'has_perm') and user.has_perm('tournaments.can_organize_tournaments'):
        return TournamentRole.ORGANIZER
    
    # Check if user has any tournament registrations
    # This determines if they're an active player vs spectator
    try:
        from apps.tournaments.models import Registration
        
        has_registrations = Registration.objects.filter(
            user=user,
            status__in=['pending', 'confirmed', 'checked_in']
        ).exists()
        
        if has_registrations:
            return TournamentRole.PLAYER
    except Exception as e:
        logger.warning(f"Error checking user registrations: {e}")
    
    # Default to spectator (read-only access)
    return TournamentRole.SPECTATOR


def check_tournament_role(user, required_role: TournamentRole) -> bool:
    """
    Check if user has required tournament role.
    
    Args:
        user: Django User instance
        required_role: Minimum role required
        
    Returns:
        True if user meets role requirement
        
    Example:
        # In WebSocket consumer
        if not check_tournament_role(self.scope['user'], TournamentRole.ORGANIZER):
            await self.send_json({'error': 'Organizer access required'})
            await self.close(code=4003)
    """
    user_role = get_user_tournament_role(user)
    return TournamentRole.has_permission(user_role, required_role)


# -----------------------------------------------------------------------------
# DRF Permission Classes
# -----------------------------------------------------------------------------

class IsSpectator(permissions.BasePermission):
    """
    Allow access to any authenticated user (minimum: spectator role).
    
    Usage:
        permission_classes = [IsAuthenticated, IsSpectator]
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated (all authenticated users are at least spectators)"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Allow read access to any authenticated user"""
        return request.user and request.user.is_authenticated


class IsPlayer(permissions.BasePermission):
    """
    Allow access to users with PLAYER role or higher.
    
    Usage:
        permission_classes = [IsAuthenticated, IsPlayer]
    """
    
    def has_permission(self, request, view):
        """Check if user has at least PLAYER role"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return check_tournament_role(request.user, TournamentRole.PLAYER)
    
    def has_object_permission(self, request, view, obj):
        """Check player access for specific object"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Players can only access their own registrations/matches
        if hasattr(obj, 'user'):
            return obj.user == request.user or check_tournament_role(request.user, TournamentRole.ORGANIZER)
        
        return check_tournament_role(request.user, TournamentRole.PLAYER)


class IsOrganizer(permissions.BasePermission):
    """
    Allow access to tournament organizers and admins.
    
    Usage:
        permission_classes = [IsAuthenticated, IsOrganizer]
    """
    
    def has_permission(self, request, view):
        """Check if user has at least ORGANIZER role"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return check_tournament_role(request.user, TournamentRole.ORGANIZER)
    
    def has_object_permission(self, request, view, obj):
        """Check organizer access for specific tournament"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins have access to all tournaments
        if check_tournament_role(request.user, TournamentRole.ADMIN):
            return True
        
        # Organizers can only manage their own tournaments
        if hasattr(obj, 'organizer'):
            return obj.organizer == request.user
        
        return False


class IsAdmin(permissions.BasePermission):
    """
    Allow access to admins only (staff/superusers).
    
    Usage:
        permission_classes = [IsAuthenticated, IsAdmin]
    """
    
    def has_permission(self, request, view):
        """Check if user has ADMIN role"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return check_tournament_role(request.user, TournamentRole.ADMIN)
    
    def has_object_permission(self, request, view, obj):
        """Admins have access to all objects"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return check_tournament_role(request.user, TournamentRole.ADMIN)


class IsOrganizerOrReadOnly(permissions.BasePermission):
    """
    Allow read access to anyone, write access to organizers.
    
    Usage:
        permission_classes = [IsOrganizerOrReadOnly]
    """
    
    def has_permission(self, request, view):
        """Allow safe methods for everyone, unsafe for organizers"""
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        return check_tournament_role(request.user, TournamentRole.ORGANIZER)
    
    def has_object_permission(self, request, view, obj):
        """Allow read to everyone, write to organizer/admin"""
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins can edit anything
        if check_tournament_role(request.user, TournamentRole.ADMIN):
            return True
        
        # Organizers can only edit their own tournaments
        if hasattr(obj, 'organizer'):
            return obj.organizer == request.user
        
        return False


# -----------------------------------------------------------------------------
# WebSocket Permission Helpers
# -----------------------------------------------------------------------------

def get_required_role_for_action(action_type: str) -> TournamentRole:
    """
    Get minimum role required for a WebSocket action.
    
    Args:
        action_type: Action identifier from WebSocket message
        
    Returns:
        TournamentRole required for action
        
    Example:
        >>> get_required_role_for_action('update_score')
        TournamentRole.ORGANIZER
    """
    # Map actions to required roles
    action_roles = {
        # Spectator actions (read-only)
        'subscribe': TournamentRole.SPECTATOR,
        'ping': TournamentRole.SPECTATOR,
        
        # Player actions
        'ready_up': TournamentRole.PLAYER,
        'report_score': TournamentRole.PLAYER,
        'submit_proof': TournamentRole.PLAYER,
        
        # Organizer actions
        'update_score': TournamentRole.ORGANIZER,
        'verify_payment': TournamentRole.ORGANIZER,
        'reject_payment': TournamentRole.ORGANIZER,
        'advance_bracket': TournamentRole.ORGANIZER,
        'start_match': TournamentRole.ORGANIZER,
        
        # Admin actions
        'regenerate_bracket': TournamentRole.ADMIN,
        'force_refund': TournamentRole.ADMIN,
        'ban_participant': TournamentRole.ADMIN,
    }
    
    return action_roles.get(action_type, TournamentRole.SPECTATOR)


async def check_websocket_action_permission(user, action_type: str) -> bool:
    """
    Check if user has permission to perform WebSocket action.
    
    Args:
        user: Django User instance
        action_type: Action identifier from WebSocket message
        
    Returns:
        True if user has required role for action
        
    Example:
        # In WebSocket consumer receive handler
        action = content.get('type')
        if not await check_websocket_action_permission(self.scope['user'], action):
            await self.send_json({
                'type': 'error',
                'code': 'insufficient_permissions',
                'message': f'Action {action} requires higher privileges'
            })
            return
    """
    required_role = get_required_role_for_action(action_type)
    return check_tournament_role(user, required_role)
