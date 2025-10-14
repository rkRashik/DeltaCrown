# apps/teams/views/role_management.py
"""
Role Management Views - Phase 3
New API endpoints for professional role hierarchy system
"""
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction
import json

from ..models import Team, TeamMembership
from ..permissions import TeamPermissions
from apps.user_profile.models import UserProfile


def _ensure_profile(user):
    """Helper to get or create user profile."""
    if not user.is_authenticated:
        return None
    return getattr(user, 'profile', None) or getattr(user, 'userprofile', None)


@login_required
@require_http_methods(["POST"])
def transfer_ownership_view(request, slug: str):
    """
    Transfer team ownership to another member (OWNER only).
    
    POST data:
        - profile_id: ID of user profile to make new owner
        
    Returns:
        - JSON response with success/error
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user is OWNER
    try:
        current_owner_membership = TeamMembership.objects.get(
            team=team, 
            profile=profile, 
            status='ACTIVE'
        )
        
        if not TeamPermissions.can_transfer_ownership(current_owner_membership):
            return JsonResponse({
                "error": "Only the team owner can transfer ownership."
            }, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({
            "error": "You must be a team member."
        }, status=403)
    
    try:
        data = json.loads(request.body)
        new_owner_profile_id = data.get('profile_id')
        
        if not new_owner_profile_id:
            return JsonResponse({"error": "Profile ID is required."}, status=400)
        
        # Get the new owner's membership
        new_owner_membership = get_object_or_404(
            TeamMembership,
            team=team,
            profile_id=new_owner_profile_id,
            status='ACTIVE'
        )
        
        # Cannot transfer to current owner
        if new_owner_membership.profile == profile:
            return JsonResponse({
                "error": "You are already the owner."
            }, status=400)
        
        # Use transaction to ensure atomicity
        with transaction.atomic():
            # Change current OWNER to PLAYER
            current_owner_membership.role = TeamMembership.Role.PLAYER
            current_owner_membership.update_permission_cache()
            current_owner_membership.save()
            
            # Make new member OWNER
            new_owner_membership.role = TeamMembership.Role.OWNER
            new_owner_membership.update_permission_cache()
            new_owner_membership.save()
            
            # Update team captain field (legacy)
            team.captain = new_owner_membership.profile
            team.save(update_fields=['captain'])
        
        return JsonResponse({
            "success": True,
            "message": f"Ownership transferred to {new_owner_membership.profile.display_name}",
            "new_owner": {
                "profile_id": new_owner_membership.profile.id,
                "username": new_owner_membership.profile.user.username,
                "display_name": new_owner_membership.profile.display_name,
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def assign_manager_view(request, slug: str):
    """
    Assign MANAGER role to a team member (OWNER only).
    
    POST data:
        - profile_id: ID of user profile to make manager
        
    Returns:
        - JSON response with success/error
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user is OWNER
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=profile,
            status='ACTIVE'
        )
        
        if not TeamPermissions.can_assign_manager(membership):
            return JsonResponse({
                "error": "Only the team owner can assign managers."
            }, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({
            "error": "You must be a team member."
        }, status=403)
    
    try:
        data = json.loads(request.body)
        target_profile_id = data.get('profile_id')
        
        if not target_profile_id:
            return JsonResponse({"error": "Profile ID is required."}, status=400)
        
        # Get the target member's membership
        target_membership = get_object_or_404(
            TeamMembership,
            team=team,
            profile_id=target_profile_id,
            status='ACTIVE'
        )
        
        # Cannot change OWNER role
        if target_membership.role == TeamMembership.Role.OWNER:
            return JsonResponse({
                "error": "Cannot change owner's role."
            }, status=400)
        
        # Update role to MANAGER
        target_membership.role = TeamMembership.Role.MANAGER
        target_membership.update_permission_cache()
        target_membership.save()
        
        return JsonResponse({
            "success": True,
            "message": f"{target_membership.profile.display_name} is now a manager",
            "member": {
                "profile_id": target_membership.profile.id,
                "username": target_membership.profile.user.username,
                "display_name": target_membership.profile.display_name,
                "role": target_membership.role,
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def remove_manager_view(request, slug: str):
    """
    Remove MANAGER role from a team member (change to PLAYER) - OWNER only.
    
    POST data:
        - profile_id: ID of user profile to demote from manager
        
    Returns:
        - JSON response with success/error
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user is OWNER
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=profile,
            status='ACTIVE'
        )
        
        if not TeamPermissions.can_assign_manager(membership):
            return JsonResponse({
                "error": "Only the team owner can remove managers."
            }, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({
            "error": "You must be a team member."
        }, status=403)
    
    try:
        data = json.loads(request.body)
        target_profile_id = data.get('profile_id')
        
        if not target_profile_id:
            return JsonResponse({"error": "Profile ID is required."}, status=400)
        
        # Get the target member's membership
        target_membership = get_object_or_404(
            TeamMembership,
            team=team,
            profile_id=target_profile_id,
            status='ACTIVE'
        )
        
        # Must be a MANAGER
        if target_membership.role != TeamMembership.Role.MANAGER:
            return JsonResponse({
                "error": "This member is not a manager."
            }, status=400)
        
        # Change to PLAYER
        target_membership.role = TeamMembership.Role.PLAYER
        target_membership.update_permission_cache()
        target_membership.save()
        
        return JsonResponse({
            "success": True,
            "message": f"{target_membership.profile.display_name} is no longer a manager",
            "member": {
                "profile_id": target_membership.profile.id,
                "username": target_membership.profile.user.username,
                "display_name": target_membership.profile.display_name,
                "role": target_membership.role,
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def assign_coach_view(request, slug: str):
    """
    Assign COACH role to a team member (OWNER or MANAGER).
    
    POST data:
        - profile_id: ID of user profile to make coach
        
    Returns:
        - JSON response with success/error
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user has permission
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=profile,
            status='ACTIVE'
        )
        
        if not TeamPermissions.can_assign_coach(membership):
            return JsonResponse({
                "error": "Only owners and managers can assign coaches."
            }, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({
            "error": "You must be a team member."
        }, status=403)
    
    try:
        data = json.loads(request.body)
        target_profile_id = data.get('profile_id')
        
        if not target_profile_id:
            return JsonResponse({"error": "Profile ID is required."}, status=400)
        
        # Get the target member's membership
        target_membership = get_object_or_404(
            TeamMembership,
            team=team,
            profile_id=target_profile_id,
            status='ACTIVE'
        )
        
        # Cannot change OWNER or MANAGER roles
        if target_membership.role in [TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER]:
            return JsonResponse({
                "error": "Cannot change owner or manager role to coach."
            }, status=400)
        
        # Update role to COACH
        target_membership.role = TeamMembership.Role.COACH
        target_membership.update_permission_cache()
        target_membership.save()
        
        return JsonResponse({
            "success": True,
            "message": f"{target_membership.profile.display_name} is now a coach",
            "member": {
                "profile_id": target_membership.profile.id,
                "username": target_membership.profile.user.username,
                "display_name": target_membership.profile.display_name,
                "role": target_membership.role,
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def assign_captain_title_view(request, slug: str):
    """
    Assign in-game captain title (⭐) to a PLAYER or SUBSTITUTE (OWNER or MANAGER).
    Only one captain title per team.
    
    POST data:
        - profile_id: ID of user profile to make captain
        
    Returns:
        - JSON response with success/error
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user has permission
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=profile,
            status='ACTIVE'
        )
        
        if not TeamPermissions.can_assign_captain_title(membership):
            return JsonResponse({
                "error": "Only owners and managers can assign captain title."
            }, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({
            "error": "You must be a team member."
        }, status=403)
    
    try:
        data = json.loads(request.body)
        target_profile_id = data.get('profile_id')
        
        if not target_profile_id:
            return JsonResponse({"error": "Profile ID is required."}, status=400)
        
        # Get the target member's membership
        target_membership = get_object_or_404(
            TeamMembership,
            team=team,
            profile_id=target_profile_id,
            status='ACTIVE'
        )
        
        # Can only assign captain to PLAYER or SUBSTITUTE
        if target_membership.role not in [TeamMembership.Role.PLAYER, TeamMembership.Role.SUBSTITUTE]:
            return JsonResponse({
                "error": "Captain title can only be assigned to players or substitutes."
            }, status=400)
        
        # Use transaction to ensure atomicity
        with transaction.atomic():
            # Remove captain title from all other members
            TeamMembership.objects.filter(
                team=team,
                status='ACTIVE',
                is_captain=True
            ).update(is_captain=False)
            
            # Assign captain title
            target_membership.is_captain = True
            target_membership.save()
        
        return JsonResponse({
            "success": True,
            "message": f"{target_membership.profile.display_name} is now the team captain",
            "member": {
                "profile_id": target_membership.profile.id,
                "username": target_membership.profile.user.username,
                "display_name": target_membership.profile.display_name,
                "role": target_membership.role,
                "is_captain": True,
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def remove_captain_title_view(request, slug: str):
    """
    Remove in-game captain title from a member (OWNER or MANAGER).
    
    POST data:
        - profile_id: ID of user profile to remove captain title from
        
    Returns:
        - JSON response with success/error
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user has permission
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=profile,
            status='ACTIVE'
        )
        
        if not TeamPermissions.can_assign_captain_title(membership):
            return JsonResponse({
                "error": "Only owners and managers can remove captain title."
            }, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({
            "error": "You must be a team member."
        }, status=403)
    
    try:
        data = json.loads(request.body)
        target_profile_id = data.get('profile_id')
        
        if not target_profile_id:
            return JsonResponse({"error": "Profile ID is required."}, status=400)
        
        # Get the target member's membership
        target_membership = get_object_or_404(
            TeamMembership,
            team=team,
            profile_id=target_profile_id,
            status='ACTIVE'
        )
        
        # Remove captain title
        target_membership.is_captain = False
        target_membership.save()
        
        return JsonResponse({
            "success": True,
            "message": f"Captain title removed from {target_membership.profile.display_name}",
            "member": {
                "profile_id": target_membership.profile.id,
                "username": target_membership.profile.user.username,
                "display_name": target_membership.profile.display_name,
                "role": target_membership.role,
                "is_captain": False,
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def change_member_organizational_role_view(request, slug: str):
    """
    Change a member's organizational role (OWNER/MANAGER only).
    Handles all role changes except OWNER transfers.
    
    POST data:
        - profile_id: ID of user profile
        - new_role: One of [PLAYER, SUBSTITUTE, MANAGER, COACH]
        
    Returns:
        - JSON response with success/error
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user has permission
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=profile,
            status='ACTIVE'
        )
        
        if not TeamPermissions.can_manage_roster(membership):
            return JsonResponse({
                "error": "You don't have permission to change member roles."
            }, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({
            "error": "You must be a team member."
        }, status=403)
    
    try:
        data = json.loads(request.body)
        target_profile_id = data.get('profile_id')
        new_role = data.get('new_role')
        
        if not target_profile_id or not new_role:
            return JsonResponse({
                "error": "Both profile_id and new_role are required."
            }, status=400)
        
        # Validate new role
        valid_roles = ['PLAYER', 'SUBSTITUTE', 'MANAGER', 'COACH']
        if new_role not in valid_roles:
            return JsonResponse({
                "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            }, status=400)
        
        # Get the target member's membership
        target_membership = get_object_or_404(
            TeamMembership,
            team=team,
            profile_id=target_profile_id,
            status='ACTIVE'
        )
        
        # Cannot change OWNER role (must use transfer_ownership)
        if target_membership.role == TeamMembership.Role.OWNER:
            return JsonResponse({
                "error": "Cannot change owner's role. Use transfer ownership instead."
            }, status=400)
        
        # Only OWNER can assign MANAGER
        if new_role == 'MANAGER' and not TeamPermissions.can_assign_manager(membership):
            return JsonResponse({
                "error": "Only the team owner can assign managers."
            }, status=403)
        
        # Update role
        target_membership.role = new_role
        target_membership.update_permission_cache()
        target_membership.save()
        
        return JsonResponse({
            "success": True,
            "message": f"{target_membership.profile.display_name}'s role changed to {new_role}",
            "member": {
                "profile_id": target_membership.profile.id,
                "username": target_membership.profile.user.username,
                "display_name": target_membership.profile.display_name,
                "role": target_membership.role,
                "permissions": TeamPermissions.get_permission_summary(target_membership)
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
