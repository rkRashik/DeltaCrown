# apps/teams/views/public.py
from __future__ import annotations
from uuid import uuid4

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django import forms
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from urllib.parse import urlencode

from ..models import Team, TeamMembership, TeamInvite


# -------------------------
# Helpers
# -------------------------
def _get_profile(user):
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
# Public index
# -------------------------
def team_list(request):
    """
    Public teams index with ?q= search and pagination.
    """
    q = (request.GET.get("q") or "").strip()
    game = (request.GET.get("game") or "").strip()
    open_to_join = (request.GET.get("open") or "").strip()

    qs = Team.objects.all().distinct()
    try:
        qs = qs.select_related("captain__user")
    except Exception:
        pass

    filters = Q()
    for field in ("name", "tag", "slug"):
        try:
            Team._meta.get_field(field)
            if q:
                filters |= Q(**{f"{field}__icontains": q})
        except Exception:
            continue
    if q and filters:
        qs = qs.filter(filters)

    # Optional filters
    if game:
        try:
            qs = qs.filter(game=game)
        except Exception:
            pass

    qs = qs.order_by("id")

    # Build base_qs without page
    qdict = request.GET.copy()
    qdict.pop("page", None)
    base_qs = urlencode(qdict, doseq=True)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page") or 1
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        "teams": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "game": game,
        "open": open_to_join,
        "base_qs": base_qs,
    }
    return render(request, "teams/list.html", ctx)


# -------------------------
# Team detail (public)
# -------------------------
def team_detail(request, slug: str):
    team_qs = Team.objects.all()
    try:
        team_qs = team_qs.select_related("captain__user")
    except Exception:
        pass
    team = team_qs.filter(slug=slug).first() or get_object_or_404(team_qs, slug=slug)

    memberships = team.memberships.select_related("profile__user").all().order_by("role", "joined_at")
    roster = [m.profile for m in memberships if getattr(m, "status", "ACTIVE") == "ACTIVE"]

    # Upcoming and recent results (best effort)
    try:
        from apps.tournaments.models import Match
        from django.db import models
        now = timezone.now()
        upcoming = (
            Match.objects.filter(models.Q(team_a=team) | models.Q(team_b=team), start_at__gt=now)
            .order_by("start_at")[:5]
        )
        results = (
            Match.objects.filter(models.Q(team_a=team) | models.Q(team_b=team), state__in=["REPORTED", "VERIFIED"])  # type: ignore
            .order_by("-created_at")[:5]
        )
    except Exception:
        upcoming, results = [], []

    is_captain = _is_captain(_get_profile(request.user), team)

    ctx = {"team": team, "roster": roster, "roster_memberships": memberships, "results": results, "upcoming": upcoming, "is_captain": is_captain}
    return render(request, "teams/detail.html", ctx)


# -------------------------
# Create team (public, auth)
# -------------------------
class TeamCreateForm(forms.ModelForm):
    class Meta:
        model = Team
        exclude = ("name_ci", "tag_ci", "captain")


@login_required
@require_http_methods(["GET", "POST"])
def create_team_view(request):
    profile = _ensure_profile(request.user)

    if request.method == "POST":
        form = TeamCreateForm(request.POST, request.FILES)
        if form.is_valid():
            team = form.save(commit=False)
            team.captain = profile
            team.save()
            messages.success(request, "Team created successfully.")
            return redirect("teams:detail", slug=team.slug or team.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeamCreateForm()

    return render(request, "teams/create.html", {"form": form})


# -------------------------
# Manage team (captain only)
# -------------------------
class TeamEditForm(forms.ModelForm):
    class Meta:
        model = Team
        exclude = ("name_ci", "tag_ci")


@login_required
@require_http_methods(["GET", "POST"])
def manage_team_view(request, slug: str):
    team = get_object_or_404(Team.objects.select_related("captain__user"), slug=slug)
    profile = _ensure_profile(request.user)
    if not _is_captain(profile, team):
        messages.error(request, "Only the captain can manage the team.")
        return redirect("teams:detail", slug=team.slug)

    if request.method == "POST":
        form = TeamEditForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, "Team updated.")
            return redirect("teams:manage", slug=team.slug)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeamEditForm(instance=team)

    pending_invites = team.invites.filter(status="PENDING").select_related("invited_user__user")

    return render(request, "teams/manage.html", {"team": team, "form": form, "pending_invites": pending_invites})


@login_required
@require_http_methods(["GET", "POST"])
def invite_member_view(request, slug: str):
    team = get_object_or_404(Team, slug=slug)

    if request.method == "POST":
        actor = _ensure_profile(request.user)
        if not _is_captain(actor, team):
            messages.error(request, "Only the team captain can invite members.")
            return redirect(reverse("teams:detail", kwargs={"slug": team.slug}))

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
            return redirect(reverse("teams:invite_member", kwargs={"slug": team.slug}))

        target_profile = _ensure_profile(target_user)

        invite, _created = TeamInvite.objects.get_or_create(
            team=team,
            invited_user=target_profile,
            defaults={"invited_by": actor, "message": message, "status": "PENDING"},
        )
        if not getattr(invite, "token", ""):
            invite.token = uuid4().hex
            invite.save(update_fields=["token"])

        messages.success(request, f"Invite sent to {target_user.username}.")
        return redirect(reverse("teams:detail", kwargs={"slug": team.slug}))

    return render(request, "teams/invite_member.html", {"team": team})


@login_required
def my_invites(request):
    profile = _ensure_profile(request.user)
    invites = TeamInvite.objects.filter(invited_user=profile, status="PENDING").select_related("team", "invited_by__user")
    return render(request, "teams/my_invites.html", {"invites": invites})


@login_required
def accept_invite_view(request, token: str):
    invite = get_object_or_404(TeamInvite, token=token)
    profile = _ensure_profile(request.user)

    if invite.invited_user_id != profile.id or invite.status != "PENDING":
        messages.error(request, "This invite cannot be accepted.")
        return redirect(reverse("teams:my_invites"))

    TeamMembership.objects.get_or_create(team=invite.team, profile=profile, defaults={"role": TeamMembership.Role.PLAYER})
    invite.status = "ACCEPTED"
    invite.save(update_fields=["status"])
    messages.success(request, f"You joined {invite.team.tag}.")
    return redirect(reverse("teams:my_invites"))


@login_required
def decline_invite_view(request, token: str):
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
    team = get_object_or_404(Team, pk=team_id)
    profile = _ensure_profile(request.user)

    if _is_captain(profile, team):
        messages.error(request, "Captain must transfer captaincy before leaving the team.")
        return redirect(reverse("teams:detail", kwargs={"team_id": team.id}))

    TeamMembership.objects.filter(team=team, profile=profile).delete()
    messages.success(request, "You left the team.")
    return redirect(reverse("teams:detail", kwargs={"team_id": team.id}))
