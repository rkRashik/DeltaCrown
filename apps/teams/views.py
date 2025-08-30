# apps/teams/views.py
from uuid import uuid4

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import Team, TeamMembership, TeamInvite


# -------------------------
# Helpers (no circular deps)
# -------------------------
def _get_profile(user):
    # Works whether OneToOne is named "profile" or "userprofile"
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)


def _ensure_profile(user):
    p = _get_profile(user)
    if p:
        return p
    UserProfile = apps.get_model("user_profile", "UserProfile")
    p, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"display_name": getattr(user, "username", "Player")}
    )
    return p


def _is_captain(profile, team: Team) -> bool:
    return bool(profile) and (team.captain_id == profile.id)


# -------------------------
# Views
# -------------------------
@login_required
def team_detail(request, team_id: int):
    """
    Overview page: roster + pending invites + captain tools.
    """
    team = get_object_or_404(Team, pk=team_id)
    memberships = (
        team.memberships.select_related("user__user")
        .all()
        .order_by("role", "joined_at")
    )
    invites = team.invites.filter(status="PENDING").select_related("invited_user__user")
    is_captain = _is_captain(_get_profile(request.user), team)
    ctx = {
        "team": team,
        "memberships": memberships,
        "invites": invites,
        "is_captain": is_captain,
    }
    return render(request, "teams/team_detail.html", ctx)


@login_required
@require_http_methods(["GET", "POST"])
def invite_member_view(request, team_id: int):
    """
    Captain invites a user by username/email.
    Creates a TeamInvite directly (idempotent) and ensures token exists.
    """
    team = get_object_or_404(Team, pk=team_id)

    if request.method == "POST":
        actor = _ensure_profile(request.user)
        if not _is_captain(actor, team):
            # Friendly redirect instead of 403 for UX/tests consistency
            messages.error(request, "Only the team captain can invite members.")
            return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))

        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        message = (request.POST.get("message") or "").strip()

        User = get_user_model()
        target_user = None
        if username:
            target_user = User.objects.filter(username=username).first()
        if not target_user and email:
            target_user = User.objects.filter(email=email).first()

        if not target_user:
            messages.error(request, "User not found by username/email.")
            return redirect(reverse("teams:invite_member", kwargs={"team_id": team.id}))

        target_profile = _ensure_profile(target_user)

        invite, _created = TeamInvite.objects.get_or_create(
            team=team,
            invited_user=target_profile,
            defaults={"invited_by": actor, "message": message, "status": "PENDING"},
        )
        # ✅ Ensure token exists so reverse('teams:accept_invite', token=...) works
        if not getattr(invite, "token", ""):
            invite.token = uuid4().hex
            invite.save(update_fields=["token"])

        messages.success(request, f"Invite sent to {target_user.username}.")
        return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))

    # GET: render a simple form (template exists)
    return render(request, "teams/invite_member.html", {"team": team})


@login_required
def my_invites(request):
    """
    List invites for the current user's profile.
    """
    profile = _ensure_profile(request.user)
    invites = (
        TeamInvite.objects
        .filter(invited_user=profile, status="PENDING")
        .select_related("team", "invited_by__user")
    )
    return render(request, "teams/my_invites.html", {"invites": invites})


@login_required
def accept_invite_view(request, token: str):
    """
    Accept an invite by token.
    """
    invite = get_object_or_404(TeamInvite, token=token)
    profile = _ensure_profile(request.user)

    if invite.invited_user_id != profile.id or invite.status != "PENDING":
        messages.error(request, "This invite cannot be accepted.")
        return redirect(reverse("teams:my_invites"))

    # join the team
    TeamMembership.objects.get_or_create(team=invite.team, user=profile, defaults={"role": "player"})
    invite.status = "ACCEPTED"
    invite.save(update_fields=["status"])
    messages.success(request, f"You joined {invite.team.tag}.")
    return redirect(reverse("teams:my_invites"))


@login_required
def decline_invite_view(request, token: str):
    """
    Decline an invite by token.
    """
    invite = get_object_or_404(TeamInvite, token=token)
    profile = _ensure_profile(request.user)

    if invite.invited_user_id != profile.id or invite.status != "PENDING":
        messages.error(request, "This invite cannot be declined.")
        return redirect(reverse("teams:my_invites"))

    invite.status = "DECLINED"
    invite.save(update_fields=["status"])
    messages.info(request, f"Invite from {invite.team.tag} declined.")
    return redirect(reverse("teams:my_invites"))


@login_required
@require_http_methods(["GET", "POST"])
def leave_team_view(request, team_id: int):
    """
    Allow a non-captain to leave. (Accept GET to satisfy tests.)
    For captains, redirect with an error instead of raising 403.
    """
    team = get_object_or_404(Team, pk=team_id)
    profile = _ensure_profile(request.user)

    if _is_captain(profile, team):
        messages.error(request, "Captain must transfer captaincy before leaving the team.")
        return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))

    TeamMembership.objects.filter(team=team, user=profile).delete()
    messages.success(request, "You left the team.")
    return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))


@login_required
@require_http_methods(["POST"])
def transfer_captain_view(request, team_id: int):
    """
    Captain transfers captaincy to another member.
    Expect form field `new_captain` = profile id.
    """
    team = get_object_or_404(Team, pk=team_id)
    actor = _ensure_profile(request.user)
    if not _is_captain(actor, team):
        messages.error(request, "Only the captain can transfer captaincy.")
        return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))

    try:
        new_cap_id = int(request.POST.get("new_captain", "0"))
    except ValueError:
        new_cap_id = 0

    if not new_cap_id:
        messages.error(request, "Select a valid member as new captain.")
        return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))

    UserProfile = apps.get_model("user_profile", "UserProfile")
    new_cap = get_object_or_404(UserProfile, pk=new_cap_id)

    if not TeamMembership.objects.filter(team=team, user=new_cap).exists():
        messages.error(request, "Selected user is not a team member.")
        return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))

    team.captain = new_cap
    team.save(update_fields=["captain"])
    TeamMembership.objects.update_or_create(team=team, user=new_cap, defaults={"role": "captain"})
    TeamMembership.objects.filter(team=team, user=actor).update(role="player")

    messages.success(request, f"Captaincy transferred to {new_cap.user.username}.")
    return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))


@login_required
@require_http_methods(["GET", "POST"])
def create_team_quick(request):
    """
    Minimal team creation: name + tag.
    - GET: redirect back (no dedicated create form in this build).
    - POST: create team, set creator as captain, add membership.
    """
    if request.method == "GET":
        # No UI provided here; bounce back safely
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # POST
    name = (request.POST.get("name") or "").strip()
    tag = (request.POST.get("tag") or "").strip().upper()

    if not name or not tag:
        messages.error(request, "Team name and tag are required.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    cap_profile = _ensure_profile(request.user)
    team = Team.objects.create(name=name, tag=tag, captain=cap_profile)
    TeamMembership.objects.get_or_create(team=team, user=cap_profile, defaults={"role": "captain"})
    messages.success(request, f"Team {tag} created.")
    return redirect(reverse("teams:team_detail", kwargs={"team_id": team.id}))
