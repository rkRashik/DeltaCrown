"""
Dashboard API Endpoints
========================
AJAX endpoints for dashboard interactivity.
"""
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta


def _get_user_profile(user):
    """Helper to get user profile."""
    return getattr(user, 'profile', None) or getattr(user, 'userprofile', None)


@login_required
def get_pending_items(request, slug: str):
    """
    Get pending items count (join requests + invites).
    """
    Team = apps.get_model("teams", "Team")
    TeamInvite = apps.get_model("teams", "TeamInvite")
    
    team = get_object_or_404(Team, slug=slug)
    profile = _get_user_profile(request.user)
    
    # Permission check
    is_captain = team.is_captain(profile)
    if not is_captain:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    # Count pending invites
    pending_invites = TeamInvite.objects.filter(
        team=team,
        status="PENDING",
        expires_at__gt=timezone.now()
    ).count()
    
    # Count join requests if available
    join_requests = 0
    try:
        JoinRequest = apps.get_model("teams", "JoinRequest")
        join_requests = JoinRequest.objects.filter(
            team=team,
            status="PENDING"
        ).count()
    except:
        pass
    
    total_pending = pending_invites + join_requests
    
    return JsonResponse({
        "success": True,
        "count": total_pending,
        "pending_invites": pending_invites,
        "join_requests": join_requests
    })


@login_required
def get_recent_activity(request, slug: str):
    """
    Get recent team activities.
    """
    Team = apps.get_model("teams", "Team")
    TeamActivity = apps.get_model("teams", "TeamActivity")
    
    team = get_object_or_404(Team, slug=slug)
    profile = _get_user_profile(request.user)
    
    # Permission check
    is_captain = team.is_captain(profile)
    if not is_captain:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    # Get last 20 activities
    activities = TeamActivity.objects.filter(
        team=team
    ).select_related("actor__user").order_by("-created_at")[:20]
    
    # Format for response
    icon_map = {
        'member_joined': 'user-plus',
        'member_left': 'user-minus',
        'achievement_unlocked': 'trophy',
        'match_won': 'check-circle',
        'match_lost': 'times-circle',
        'tournament_joined': 'flag',
        'post_created': 'file-alt',
        'roster_updated': 'users',
    }
    
    activity_list = []
    for activity in activities:
        # Calculate time ago
        time_diff = timezone.now() - activity.created_at
        if time_diff.days > 0:
            time_ago = f"{time_diff.days}d ago"
        elif time_diff.seconds >= 3600:
            time_ago = f"{time_diff.seconds // 3600}h ago"
        elif time_diff.seconds >= 60:
            time_ago = f"{time_diff.seconds // 60}m ago"
        else:
            time_ago = "Just now"
        
        activity_list.append({
            'id': activity.id,
            'type': activity.activity_type,
            'icon': icon_map.get(activity.activity_type, 'info-circle'),
            'description': activity.description,
            'time_ago': time_ago
        })
    
    return JsonResponse({
        "success": True,
        "activities": activity_list
    })


@login_required
def approve_join_request(request, request_id: int):
    """
    Approve a join request.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        JoinRequest = apps.get_model("teams", "JoinRequest")
        TeamMembership = apps.get_model("teams", "TeamMembership")
        TeamActivity = apps.get_model("teams", "TeamActivity")
        
        join_request = get_object_or_404(JoinRequest, id=request_id)
        team = join_request.team
        profile = _get_user_profile(request.user)
        
        # Permission check
        is_captain = team.is_captain(profile)
        if not is_captain:
            return JsonResponse({"error": "Permission denied"}, status=403)
        
        # Create membership
        TeamMembership.objects.create(
            team=team,
            profile=join_request.user.profile,
            role="PLAYER",
            status="ACTIVE"
        )
        
        # Update join request
        join_request.status = "ACCEPTED"
        join_request.reviewed_by = profile
        join_request.reviewed_at = timezone.now()
        join_request.save()
        
        # Create activity
        TeamActivity.objects.create(
            team=team,
            activity_type="member_joined",
            actor=join_request.user.profile,
            description=f"{join_request.user.username} joined the team",
            is_public=True
        )
        
        return JsonResponse({
            "success": True,
            "message": "Join request approved"
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def reject_join_request(request, request_id: int):
    """
    Reject a join request.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        JoinRequest = apps.get_model("teams", "JoinRequest")
        
        join_request = get_object_or_404(JoinRequest, id=request_id)
        team = join_request.team
        profile = _get_user_profile(request.user)
        
        # Permission check
        is_captain = team.is_captain(profile)
        if not is_captain:
            return JsonResponse({"error": "Permission denied"}, status=403)
        
        # Update join request
        join_request.status = "REJECTED"
        join_request.reviewed_by = profile
        join_request.reviewed_at = timezone.now()
        join_request.save()
        
        return JsonResponse({
            "success": True,
            "message": "Join request rejected"
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def resend_team_invite(request, invite_id: int):
    """
    Resend a team invite (extend expiry).
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    TeamInvite = apps.get_model("teams", "TeamInvite")
    
    invite = get_object_or_404(TeamInvite, id=invite_id)
    team = invite.team
    profile = _get_user_profile(request.user)
    
    # Permission check
    is_captain = team.is_captain(profile)
    if not is_captain:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    # Extend expiry
    invite.expires_at = timezone.now() + timedelta(days=7)
    invite.status = "PENDING"
    invite.save()
    
    return JsonResponse({
        "success": True,
        "message": "Invite resent successfully",
        "new_expiry": invite.expires_at.isoformat()
    })


@login_required
def cancel_team_invite(request, invite_id: int):
    """
    Cancel a team invite.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    TeamInvite = apps.get_model("teams", "TeamInvite")
    
    invite = get_object_or_404(TeamInvite, id=invite_id)
    team = invite.team
    profile = _get_user_profile(request.user)
    
    # Permission check
    is_captain = team.is_captain(profile)
    if not is_captain:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    # Update status
    invite.status = "CANCELLED"
    invite.save()
    
    return JsonResponse({
        "success": True,
        "message": "Invite cancelled"
    })
