# apps/teams/views/otp_leave.py
"""
OTP-protected leave team flow.
Requires email verification via OTP before allowing members to leave teams.
"""
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction

from apps.teams.models import Team, TeamMembership, TeamOTP
from apps.teams.permissions import TeamPermissions


@login_required
@require_http_methods(["POST"])
def request_leave_otp(request, slug):
    """
    Request OTP code to leave team.
    Sends verification code via email.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = getattr(request.user, "profile", None)

    if not profile:
        return JsonResponse(
            {
                "success": False,
                "error_code": "NO_PROFILE",
                "message": "Please complete your profile first.",
            },
            status=400,
        )

    # Get membership
    membership = TeamMembership.objects.filter(
        team=team, profile=profile, status=TeamMembership.Status.ACTIVE
    ).first()

    if not membership:
        return JsonResponse(
            {
                "success": False,
                "error_code": "NOT_MEMBER",
                "message": "You are not a member of this team.",
            },
            status=403,
        )

    # Check if user can leave team
    if not TeamPermissions.can_leave_team(membership):
        return JsonResponse(
            {
                "success": False,
                "error_code": "CAPTAIN_CANNOT_LEAVE",
                "message": "Team owner must transfer ownership before leaving.",
            },
            status=403,
        )

    # Issue OTP
    try:
        otp = TeamOTP.issue(
            user=request.user, team=team, purpose=TeamOTP.Purpose.LEAVE_TEAM
        )

        return JsonResponse(
            {
                "success": True,
                "message": f"Verification code sent to {request.user.email}",
                "expires_minutes": TeamOTP.EXPIRATION_MINUTES,
            }
        )

    except TeamOTP.RequestThrottled as e:
        return JsonResponse(
            {
                "success": False,
                "error_code": "RATE_LIMITED",
                "message": f"Too many requests. Please wait {e.retry_after} seconds.",
                "retry_after": e.retry_after,
            },
            status=429,
        )


@login_required
@require_http_methods(["POST"])
def confirm_leave_with_otp(request, slug):
    """
    Confirm leave team with OTP code.
    Validates OTP and removes membership if valid.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = getattr(request.user, "profile", None)

    if not profile:
        return JsonResponse(
            {
                "success": False,
                "error_code": "NO_PROFILE",
                "message": "Please complete your profile first.",
            },
            status=400,
        )

    # Get membership
    membership = TeamMembership.objects.filter(
        team=team, profile=profile, status=TeamMembership.Status.ACTIVE
    ).first()

    if not membership:
        return JsonResponse(
            {
                "success": False,
                "error_code": "NOT_MEMBER",
                "message": "You are not a member of this team.",
            },
            status=403,
        )

    # Check if user can leave team
    if not TeamPermissions.can_leave_team(membership):
        return JsonResponse(
            {
                "success": False,
                "error_code": "CAPTAIN_CANNOT_LEAVE",
                "message": "Team owner must transfer ownership before leaving.",
            },
            status=403,
        )

    # Get OTP code from request
    try:
        data = json.loads(request.body)
        code = data.get("code", "").strip()
    except json.JSONDecodeError:
        code = request.POST.get("code", "").strip()

    if not code:
        return JsonResponse(
            {
                "success": False,
                "error_code": "NO_CODE",
                "message": "Please provide verification code.",
            },
            status=400,
        )

    # Find most recent unused OTP
    otp = (
        TeamOTP.objects.filter(
            user=request.user,
            team=team,
            purpose=TeamOTP.Purpose.LEAVE_TEAM,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    if not otp:
        return JsonResponse(
            {
                "success": False,
                "error_code": "NO_OTP",
                "message": "No verification code found. Please request a new one.",
            },
            status=400,
        )

    # Verify code
    result = otp.verify_code(code)

    if not result.success:
        return JsonResponse(
            {
                "success": False,
                "error_code": result.error_code,
                "message": result.message,
                "locked": result.locked,
            },
            status=400,
        )

    # Code verified, proceed with leave
    with transaction.atomic():
        # Store team name before deletion
        team_name = team.name

        # Delete membership
        membership.delete()

        # Update team member count if it exists
        if hasattr(team, "member_count"):
            team.member_count = TeamMembership.objects.filter(
                team=team, status=TeamMembership.Status.ACTIVE
            ).count()
            team.save(update_fields=["member_count"])

    # Return success response
    return JsonResponse(
        {
            "success": True,
            "message": f"You have successfully left {team_name}.",
            "redirect_url": "/teams/",
        }
    )
