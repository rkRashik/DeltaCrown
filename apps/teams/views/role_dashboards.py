# apps/teams/views/role_dashboards.py
"""
Role-specific dashboard views for team members.
Provides dedicated views for Owner, Manager, Coach, and Member tools.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.teams.models import Team, TeamMembership, TeamInvite, TeamJoinRequest as JoinRequest
from apps.teams.permissions import TeamPermissions


@login_required
@require_http_methods(["GET"])
def manager_tools_view(request, slug):
    """
    Manager Tools dashboard - roster management, invites, join requests.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = getattr(request.user, "profile", None)

    if not profile:
        messages.error(request, "Please complete your profile first.")
        return redirect("user_profile:profile")

    # Get membership
    membership = TeamMembership.objects.filter(
        team=team, profile=profile, status=TeamMembership.Status.ACTIVE
    ).first()

    if not membership:
        messages.error(request, "You are not a member of this team.")
        return redirect("teams:detail", slug=slug)

    # Check if user has manager permissions
    if not TeamPermissions.can_manage_roster(membership):
        messages.error(request, "You don't have permission to access manager tools.")
        return redirect("teams:detail", slug=slug)

    # Get pending invites and join requests
    pending_invites = team.invites.filter(status=TeamInvite.Status.PENDING).select_related(
        "invited_user__profile", "inviter"
    )
    pending_join_requests = team.join_requests.filter(
        status=JoinRequest.Status.PENDING
    ).select_related("profile")

    context = {
        "team": team,
        "membership": membership,
        "pending_invites": pending_invites,
        "pending_join_requests": pending_join_requests,
        "is_owner": membership.role == TeamMembership.Role.OWNER,
        "is_manager": membership.role == TeamMembership.Role.MANAGER,
    }

    return render(request, "teams/role_dashboards/manager_tools.html", context)


@login_required
@require_http_methods(["GET"])
def coach_tools_view(request, slug):
    """
    Coach Tools dashboard - practice schedule, VOD review, player performance.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = getattr(request.user, "profile", None)

    if not profile:
        messages.error(request, "Please complete your profile first.")
        return redirect("user_profile:profile")

    # Get membership
    membership = TeamMembership.objects.filter(
        team=team, profile=profile, status=TeamMembership.Status.ACTIVE
    ).first()

    if not membership:
        messages.error(request, "You are not a member of this team.")
        return redirect("teams:detail", slug=slug)

    # Check if user has coach role
    if membership.role != TeamMembership.Role.COACH:
        messages.error(request, "You don't have permission to access coach tools.")
        return redirect("teams:detail", slug=slug)

    # Get team roster for performance tracking
    roster = TeamMembership.objects.filter(
        team=team, status=TeamMembership.Status.ACTIVE
    ).select_related("profile")

    context = {
        "team": team,
        "membership": membership,
        "roster": roster,
        "is_coach": True,
    }

    return render(request, "teams/role_dashboards/coach_tools.html", context)


@login_required
@require_http_methods(["GET"])
def team_safety_view(request, slug):
    """
    Team Safety & Danger Zone - settings for leaving team.
    Available to all non-owner members.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = getattr(request.user, "profile", None)

    if not profile:
        messages.error(request, "Please complete your profile first.")
        return redirect("user_profile:profile")

    # Get membership
    membership = TeamMembership.objects.filter(
        team=team, profile=profile, status=TeamMembership.Status.ACTIVE
    ).first()

    if not membership:
        messages.error(request, "You are not a member of this team.")
        return redirect("teams:detail", slug=slug)

    # Check if user can leave team
    can_leave = TeamPermissions.can_leave_team(membership)

    context = {
        "team": team,
        "membership": membership,
        "can_leave_team": can_leave,
        "is_owner": membership.role == TeamMembership.Role.OWNER,
    }

    return render(request, "teams/role_dashboards/team_safety.html", context)
