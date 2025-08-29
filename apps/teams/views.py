# apps/teams/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, PermissionDenied
from django.views.decorators.http import require_http_methods

from apps.user_profile.models import UserProfile
from .models import Team, TeamInvite, TeamMembership
from .services import (
    invite_member, accept_invite, decline_invite,
    leave_team, transfer_captain, can_manage_team
)

@login_required
def team_detail(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    memberships = team.memberships.select_related("user").all().order_by("role", "joined_at")
    invites = team.invites.filter(status="PENDING").select_related("invited_user")
    is_captain = (team.captain_id == request.user.profile.id)
    return render(request, "teams/team_detail.html", {
        "team": team, "memberships": memberships, "invites": invites, "is_captain": is_captain
    })

@login_required
def invite_member_view(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.method == "POST":
        if not can_manage_team(request.user.profile, team):
            raise PermissionDenied("Only captain can invite.")
        username = request.POST.get("username", "").strip()
        message = request.POST.get("message", "").strip()
        target_user = get_object_or_404(User, username=username)
        target_profile = target_user.profile
        try:
            invite = invite_member(request.user.profile, team, target_profile, message)
            messages.success(request, f"Invite sent to @{target_user.username}.")
        except ValidationError as e:
            messages.error(request, e.message)
    return redirect("teams:team_detail", team_id=team.id)

@login_required
def my_invites(request):
    invites = (TeamInvite.objects
               .filter(invited_user=request.user.profile, status="PENDING")
               .select_related("team", "invited_by"))
    return render(request, "teams/my_invites.html", {"invites": invites})

@login_required
def accept_invite_view(request, token):
    invite = get_object_or_404(TeamInvite, token=token)
    try:
        accept_invite(invite, request.user.profile)
        messages.success(request, f"You joined {invite.team.tag}.")
    except ValidationError as e:
        messages.error(request, e.message)
    return redirect("teams:my_invites")

@login_required
def decline_invite_view(request, token):
    invite = get_object_or_404(TeamInvite, token=token)
    try:
        decline_invite(invite, request.user.profile)
        messages.info(request, f"Invite from {invite.team.tag} declined.")
    except ValidationError as e:
        messages.error(request, e.message)
    return redirect("teams:my_invites")

@login_required
def leave_team_view(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    try:
        leave_team(request.user.profile, team)
        messages.success(request, "You left the team.")
    except ValidationError as e:
        messages.error(request, e.message)
    return redirect("teams:team_detail", team_id=team.id)

@login_required
def transfer_captain_view(request, team_id, user_id):
    team = get_object_or_404(Team, pk=team_id)
    new_cap = get_object_or_404(UserProfile, pk=user_id)
    try:
        transfer_captain(request.user.profile, team, new_cap)
        messages.success(request, f"Captaincy transferred to {new_cap.user.username}.")
    except (ValidationError, PermissionDenied) as e:
        messages.error(request, str(e))
    return redirect("teams:team_detail", team_id=team.id)

@login_required
@require_http_methods(["POST"])
def create_team_quick(request):
    name = request.POST.get("name","").strip()
    tag  = request.POST.get("tag","").strip().upper()
    if not name or not tag:
        messages.error(request, "Team name and tag are required.")
        return redirect("home")
    cap_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    team = Team.objects.create(name=name, tag=tag, captain=cap_profile)
    TeamMembership.objects.get_or_create(team=team, user=cap_profile, defaults={"role": "captain"})
    messages.success(request, f"Team {tag} created.")
    return redirect("teams:team_detail", team_id=team.id)