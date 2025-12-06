"""
Member Management API Views for Team Settings
Captain-only endpoints for managing team roster
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone

from apps.teams.models import Team, TeamMembership
from apps.teams.permissions import TeamPermissions
from apps.user_profile.models import UserProfile


def _get_profile(user):
    """Get user profile."""
    return getattr(user, 'profile', None) or getattr(user, 'userprofile', None)


def _is_captain(profile, team):
    """Check if profile is team captain."""
    return team.is_captain(profile)


@login_required
@require_http_methods(["GET"])
def get_team_members(request, slug):
    """
    Get all team members with details.
    Captain-only endpoint.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _get_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can view member details"}, status=403)
    
    # Get all memberships
    memberships = team.memberships.select_related('profile__user').all()
    
    members_data = []
    for membership in memberships:
        members_data.append({
            "id": membership.id,
            "user_id": membership.profile.user.id,
            "username": membership.profile.user.username,
            "display_name": membership.profile.display_name,
            "avatar_url": membership.profile.avatar.url if membership.profile.avatar else None,
            "role": membership.role,
            "status": membership.status,
            "is_captain": team.is_captain(membership.profile),
            "is_starter": getattr(membership, 'is_starter', True),
            "in_game_name": getattr(membership, 'in_game_name', ''),
            "jersey_number": getattr(membership, 'jersey_number', None),
            "games_played": getattr(membership, 'games_played', 0),
            "joined_at": membership.joined_at.isoformat(),
        })
    
    return JsonResponse({
        "success": True,
        "members": members_data,
        "total": len(members_data)
    })


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def update_member_role(request, slug, membership_id):
    """
    Update a team member's role and status.
    Requires appropriate permissions based on role being assigned.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _get_profile(request.user)
    
    # Get user's membership to check permissions
    try:
        user_membership = TeamMembership.objects.get(team=team, profile=profile, status=TeamMembership.Status.ACTIVE)
    except TeamMembership.DoesNotExist:
        return JsonResponse({"error": "You are not an active member of this team"}, status=403)
    
    membership = get_object_or_404(TeamMembership, id=membership_id, team=team)
    
    # Prevent users from modifying their own membership
    if membership.profile == profile:
        return JsonResponse({"error": "Cannot modify your own role"}, status=400)
    
    # Get new values from request
    new_role = request.POST.get('role', membership.role)
    is_starter = request.POST.get('is_starter', 'true').lower() == 'true'
    in_game_name = request.POST.get('in_game_name', '')
    jersey_number = request.POST.get('jersey_number')
    
    # Validate role assignment permissions
    if new_role != membership.role:  # Only check if role is actually changing
        if new_role == TeamMembership.Role.OWNER:
            # Only owners can transfer ownership
            if not TeamPermissions.can_transfer_ownership(user_membership):
                return JsonResponse({"error": "Only team owners can transfer ownership"}, status=403)
        elif new_role == TeamMembership.Role.MANAGER:
            # Only owners can assign manager roles
            if not TeamPermissions.can_assign_managers(user_membership):
                return JsonResponse({"error": "Only team owners can assign manager roles"}, status=403)
        elif new_role == TeamMembership.Role.COACH:
            # Owners and managers can assign coach roles
            if not TeamPermissions.can_assign_coach(user_membership):
                return JsonResponse({"error": "Insufficient permissions to assign coach role"}, status=403)
        elif new_role in [TeamMembership.Role.PLAYER, TeamMembership.Role.SUBSTITUTE]:
            # Owners and managers can change player roles
            if not TeamPermissions.can_change_player_role(user_membership):
                return JsonResponse({"error": "Insufficient permissions to change player roles"}, status=403)
    
    # Handle captain title assignment/removal
    assign_captain = request.POST.get('assign_captain')
    if assign_captain is not None:
        assign_captain = assign_captain.lower() == 'true'
        if assign_captain != membership.is_captain:
            if not TeamPermissions.can_assign_captain_title(user_membership):
                return JsonResponse({"error": "Insufficient permissions to assign captain title"}, status=403)
            membership.is_captain = assign_captain
    
    # Update membership
    membership.role = new_role
    if hasattr(membership, 'is_starter'):
        membership.is_starter = is_starter
    if hasattr(membership, 'in_game_name'):
        membership.in_game_name = in_game_name
    if hasattr(membership, 'jersey_number') and jersey_number:
        try:
            membership.jersey_number = int(jersey_number)
        except ValueError:
            pass
    
    membership.save()
    
    return JsonResponse({
        "success": True,
        "message": "Member role updated successfully",
        "member": {
            "id": membership.id,
            "username": membership.profile.user.username,
            "role": membership.role,
            "is_starter": getattr(membership, 'is_starter', True),
        }
    })


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def remove_member(request, slug, membership_id):
    """
    Remove a member from the team.
    Captain-only endpoint with confirmation.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _get_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can remove members"}, status=403)
    
    membership = get_object_or_404(TeamMembership, id=membership_id, team=team)
    
    # Prevent captain from removing themselves
    if team.is_captain(membership.profile):
        return JsonResponse({"error": "Captain cannot remove themselves. Transfer captaincy first."}, status=400)
    
    # Get confirmation token
    confirmation = request.POST.get('confirmation', '')
    username = membership.profile.user.username
    
    if confirmation != username:
        return JsonResponse({"error": f"Please type '{username}' to confirm removal"}, status=400)
    
    # Mark as removed
    membership.status = 'REMOVED'
    membership.left_at = timezone.now()
    membership.save()
    
    # Log activity
    try:
        from apps.teams.models import TeamActivity
        TeamActivity.objects.create(
            team=team,
            activity_type='member_removed',
            description=f"{username} was removed from the team",
            metadata={'removed_by': profile.user.username}
        )
    except:
        pass
    
    return JsonResponse({
        "success": True,
        "message": f"{username} has been removed from the team"
    })


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def transfer_captaincy(request, slug, profile_id):
    """
    Transfer team captaincy to another member.
    Requires password confirmation.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _get_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only the current captain can transfer captaincy"}, status=403)
    
    # Get new captain's membership using profile_id
    try:
        new_membership = team.memberships.get(
            profile_id=profile_id,
            status='ACTIVE'
        )
    except TeamMembership.DoesNotExist:
        return JsonResponse({"error": "Selected member is not an active team member"}, status=400)
    
    # Verify password (optional - could be removed if not needed)
    password = request.POST.get('password', '')
    if password and not request.user.check_password(password):
        return JsonResponse({"error": "Incorrect password"}, status=403)
    
    # Update old captain's membership
    try:
        old_membership = team.memberships.get(profile=team.captain)
        old_membership.role = 'PLAYER'
        if hasattr(old_membership, 'is_captain'):
            old_membership.is_captain = False
        old_membership.save()
    except TeamMembership.DoesNotExist:
        pass
    
    # Update new captain's membership
    new_membership.role = 'CAPTAIN'
    if hasattr(new_membership, 'is_captain'):
        new_membership.is_captain = True
    new_membership.save()
    
    # No need to update team.captain field (removed - it's now a property)
    
    # Log activity
    try:
        from apps.teams.models import TeamActivity
        TeamActivity.objects.create(
            team=team,
            activity_type='captain_transferred',
            description=f"Captaincy transferred to {new_membership.profile.user.username}",
            metadata={
                'old_captain': profile.user.username,
                'new_captain': new_membership.profile.user.username
            }
        )
    except:
        pass
    
    return JsonResponse({
        "success": True,
        "message": f"Captaincy transferred to {new_membership.profile.user.username}",
        "new_captain": {
            "id": new_membership.id,
            "username": new_membership.profile.user.username,
            "display_name": new_membership.profile.display_name,
        }
    })


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def bulk_remove_members(request, slug):
    """
    Remove multiple members at once.
    Captain-only endpoint.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = _get_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can remove members"}, status=403)
    
    import json
    try:
        data = json.loads(request.body)
        membership_ids = data.get('membership_ids', [])
    except:
        membership_ids = request.POST.getlist('membership_ids[]')
    
    if not membership_ids:
        return JsonResponse({"error": "No members selected"}, status=400)
    
    removed_count = 0
    errors = []
    
    for membership_id in membership_ids:
        try:
            membership = team.memberships.get(id=membership_id)
            
            # Skip captain
            if team.is_captain(membership.profile):
                errors.append(f"Cannot remove captain")
                continue
            
            membership.status = 'REMOVED'
            membership.left_at = timezone.now()
            membership.save()
            removed_count += 1
            
        except TeamMembership.DoesNotExist:
            errors.append(f"Member {membership_id} not found")
    
    return JsonResponse({
        "success": True,
        "message": f"Removed {removed_count} member(s)",
        "removed_count": removed_count,
        "errors": errors if errors else None
    })
