# apps/teams/views/public.py
from __future__ import annotations
from uuid import uuid4
from typing import Dict, Optional

from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, Count, F, Value, IntegerField
from django.db.models.functions import Now, Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from urllib.parse import urlencode

from ..models import Team, TeamMembership, TeamInvite
from ..forms import (
    TeamCreationForm, TeamEditForm, TeamInviteForm, 
    TeamMemberManagementForm, TeamSettingsForm
)


# -------------------------
# Constants (games shown in UI)
# -------------------------
GAMES = [
    ("valorant", "Valorant"),
    ("efootball", "eFootball"),
    ("pubg", "PUBG Mobile"),
    ("freefire", "Free Fire"),
    ("codm", "Call of Duty Mobile"),
    ("mlbb", "Mobile Legends"),
    ("csgo", "CS2/CS:GO"),
    ("fc26", "FC 26"),
]


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
    return bool(profile) and (team.captain_id == getattr(profile, "id", None))


def _user_teams_by_game(user) -> Dict[str, Optional[Team]]:
    """
    Map of game_code -> the single team the user belongs to in that game.
    Safe even if 'game' field is missing (returns empty/None entries).
    """
    out = {code: None for code, _ in GAMES}
    if not user or not getattr(user, "is_authenticated", False):
        return out
    prof = _ensure_profile(user)
    # membership model: TeamMembership(profile=<UserProfile>, team=<Team>)
    mems = TeamMembership.objects.select_related("team").filter(profile=prof)
    for m in mems:
        game_code = getattr(m.team, "game", None)
        if game_code in out:
            out[game_code] = m.team
    return out


def _base_team_queryset():
    """
    Common queryset with safe annotations:
    - members_count: Count of memberships
    - recent_activity_at: best-effort activity timestamp (updated_at|created_at|Now)
    - trophies/tournaments_played/wins/losses placeholders (0) — extend later if you add stats joins
    """
    qs = Team.objects.all().distinct()

    # Captain relation is optional in some installs; guard select_related
    try:
        qs = qs.select_related("captain__user")
    except Exception:
        pass

    # Annotated count must not clash with Team.members_count @property
    qs = qs.annotate(memberships_count=Coalesce(Count("memberships", distinct=True), Value(0)))

    # recent_activity_at: prefer updated_at, else created_at, else Now()
    # We can't inspect fields at DB level here, so we try F() in order and fall back.
    recent_expr = None
    for cand in ("updated_at", "edited_at", "created_at"):
        if hasattr(Team, cand):
            recent_expr = F(cand)
            break
    if recent_expr is None:
        recent_expr = Now()
    qs = qs.annotate(recent_activity_at=recent_expr)

    # Placeholder stat annotations (kept zero unless you wire real stats)
    qs = qs.annotate(
        trophies=Value(0, output_field=IntegerField()),
        tournaments_played=Value(0, output_field=IntegerField()),
        wins=Value(0, output_field=IntegerField()),
        losses=Value(0, output_field=IntegerField()),
    )
    return qs


def _apply_filters(request, qs):
    """
    Filters via query params:
    - q: name/tag/slug contains
    - game: exact code (if Team has 'game' field)
    - min_members: int
    - founded_year_from / founded_year_to (if Team has 'founded_year')
    - open=1 (if Team has 'is_open')
    """
    q = (request.GET.get("q") or "").strip()
    game = (request.GET.get("game") or "").strip()
    open_to_join = (request.GET.get("open") or "").strip()

    # search: try name/tag/slug safely
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

    # game filter
    if game and hasattr(Team, "game"):
        qs = qs.filter(game=game)

    # min members
    try:
        min_members = int(request.GET.get("min_members") or 0)
    except (TypeError, ValueError):
        min_members = 0
    if min_members > 0:
        qs = qs.filter(memberships_count__gte=min_members)

    # founded year range (optional field)
    fy_from = request.GET.get("founded_year_from")
    fy_to = request.GET.get("founded_year_to")
    if hasattr(Team, "founded_year"):
        if fy_from and fy_from.isdigit():
            qs = qs.filter(founded_year__gte=int(fy_from))
        if fy_to and fy_to.isdigit():
            qs = qs.filter(founded_year__lte=int(fy_to))

    # open toggle (optional field)
    if open_to_join in ("1", "true", "True", "on") and hasattr(Team, "is_open"):
        qs = qs.filter(is_open=True)

    return qs


def _apply_sort(request, qs):
    """
    Sorting keys:
    - powerrank (default): tournaments_played, wins, losses asc, trophies, members_count, recent_activity_at
    - recent: recent_activity_at desc
    - members: members_count desc
    - az: name asc
    """
    sort = (request.GET.get("sort") or "powerrank").lower()
    if sort == "recent":
        return qs.order_by("-recent_activity_at", "name")
    if sort == "members":
        return qs.order_by("-memberships_count", "name")
    if sort == "az":
        return qs.order_by("name")
    # powerrank proxy ordering (tuple order as composite score stand-in)
    return qs.order_by(
        "-tournaments_played",
        "-wins",
        "losses",
        "-trophies",
        "-memberships_count",
        "-recent_activity_at",
        "name",
    )


# -------------------------
# Public index (Teams hub)
# -------------------------
def team_list(request):
    """
    Public teams index with search, filters, sorting, and pagination.
    Also prepares 'my_teams_by_game' for the top row.
    """
    qs = _base_team_queryset()
    qs = _apply_filters(request, qs)
    qs = _apply_sort(request, qs)

    # Build base_qs without page (useful for paginator links)
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
        # collection
        "teams": page_obj.object_list,           # backward compatible
        "object_list": page_obj.object_list,     # for new templates
        "page_obj": page_obj,
        "paginator": paginator,
        "base_qs": base_qs,
        # ui state
        "q": (request.GET.get("q") or "").strip(),
        "query": (request.GET.get("q") or "").strip(),  # alias
        "active_game": (request.GET.get("game") or "").strip(),
        "game": (request.GET.get("game") or "").strip(),  # alias
        "sort": (request.GET.get("sort") or "powerrank").lower(),
        "filters": {
            "min_members": request.GET.get("min_members") or "",
            "founded_year_from": request.GET.get("founded_year_from") or "",
            "founded_year_to": request.GET.get("founded_year_to") or "",
            "open_to_join": (request.GET.get("open") or "") in ("1", "true", "True", "on"),
        },
        # sidebar + my teams row
        "games": GAMES,
        "my_teams_by_game": _user_teams_by_game(request.user),
    }
    return render(request, "teams/list.html", ctx)


# -------------------------
# Team detail (public)
# -------------------------
def team_detail(request, slug: str):
    # Redirect to the new social team page
    from django.shortcuts import redirect
    return redirect('teams:teams_social:team_social_detail', team_slug=slug)
    
    # Original team detail code (kept for reference)
    team_qs = _base_team_queryset()
    team = team_qs.filter(slug=slug).first() or get_object_or_404(team_qs, slug=slug)

    # Roster (active-first ordering if fields exist)
    memberships = (
        team.memberships.select_related("profile__user")
        .all()
        .order_by("role", "joined_at")
    )
    roster = [m.profile for m in memberships if getattr(m, "status", "ACTIVE") == "ACTIVE"]

    # Upcoming and recent results (best effort)
    try:
        Match = apps.get_model("tournaments", "Match")
        now = timezone.now()
        upcoming = (
            Match.objects.filter(Q(team_a=team) | Q(team_b=team), start_at__gt=now)
            .order_by("start_at")[:5]
        )
        results = (
            Match.objects.filter(Q(team_a=team) | Q(team_b=team), state__in=["REPORTED", "VERIFIED"])
            .order_by("-created_at")[:5]
        )
    except Exception:
        upcoming, results = [], []

    # Role flags
    prof = _get_profile(request.user)
    is_captain = _is_captain(prof, team) if prof else False
    is_member = False
    if prof:
        is_member = TeamMembership.objects.filter(team=team, profile=prof).exists()

    # Join-guard: already in a team for this game?
    already_in_team_for_game = False
    game_code = getattr(team, "game", None)
    if prof and game_code:
        already_in_team_for_game = TeamMembership.objects.filter(
            profile=prof, team__game=game_code
        ).exists()

    ctx = {
        "team": team,
        "roster": roster,
        "roster_memberships": memberships,
        "upcoming": upcoming,
        "results": results,
        "is_captain": is_captain,
        "is_member": is_member,
        "already_in_team_for_game": already_in_team_for_game,
        "games": GAMES,  # for chips/UI if needed
    }
    return render(request, "teams/detail.html", ctx)


# -------------------------
# Create team (public, auth)
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def create_team_view(request):
    """Create a new team with the requesting user as captain."""
    profile = _ensure_profile(request.user)

    if request.method == "POST":
        form = TeamCreationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            team = form.save()
            messages.success(request, f"Team '{team.name}' created successfully!")
            return redirect("teams:detail", slug=team.slug)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill game from query string if provided
        initial = {}
        game = request.GET.get("game", "").strip()
        if game:
            initial["game"] = game
        form = TeamCreationForm(user=request.user, initial=initial)

    return render(request, "teams/create.html", {"form": form})


# -------------------------
# Manage team (captain only)
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def manage_team_view(request, slug: str):
    """Comprehensive team management view for team captains."""
    team = get_object_or_404(Team.objects.select_related("captain__user"), slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        messages.error(request, "Only the team captain can manage this team.")
        return redirect("teams:detail", slug=team.slug)

    # Handle form submissions
    if request.method == "POST":
        form_type = request.POST.get("form_type")
        
        if form_type == "edit_team":
            form = TeamEditForm(request.POST, request.FILES, instance=team, user=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Team information updated successfully!")
                return redirect("teams:manage", slug=team.slug)
            else:
                messages.error(request, "Please correct the errors in the team information form.")
                
        elif form_type == "invite_member":
            invite_form = TeamInviteForm(request.POST, team=team, sender=request.user)
            if invite_form.is_valid():
                invite_form.save()
                messages.success(request, f"Invitation sent successfully!")
                return redirect("teams:manage", slug=team.slug)
            else:
                messages.error(request, "Please correct the errors in the invitation form.")
                
        elif form_type == "manage_members":
            member_form = TeamMemberManagementForm(request.POST, team=team, user=request.user)
            if member_form.is_valid():
                member_form.save()
                messages.success(request, "Member management action completed successfully!")
                return redirect("teams:manage", slug=team.slug)
            else:
                messages.error(request, "Please correct the errors in the member management form.")
                
        elif form_type == "team_settings":
            settings_form = TeamSettingsForm(request.POST, instance=team, user=request.user)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Team settings updated successfully!")
                return redirect("teams:manage", slug=team.slug)
            else:
                messages.error(request, "Please correct the errors in the settings form.")
    
    # Initialize forms for GET request
    edit_form = TeamEditForm(instance=team, user=request.user)
    invite_form = TeamInviteForm(team=team, sender=request.user)
    member_form = TeamMemberManagementForm(team=team, user=request.user)
    settings_form = TeamSettingsForm(instance=team, user=request.user)
    
    # Get team data
    pending_invites = team.invites.filter(status="PENDING").select_related("invited_user__user")
    members = team.memberships.filter(status="ACTIVE").select_related("user__user")
    
    context = {
        "team": team,
        "edit_form": edit_form,
        "invite_form": invite_form,
        "member_form": member_form,
        "settings_form": settings_form,
        "pending_invites": pending_invites,
        "members": members,
    }

    return render(request, "teams/manage.html", context)


# -------------------------
# Invitations
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def invite_member_view(request, slug: str):
    """Send invitation to new team member."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        messages.error(request, "Only the team captain can invite members.")
        return redirect("teams:detail", slug=team.slug)

    if request.method == "POST":
        form = TeamInviteForm(request.POST, team=team, sender=request.user)
        if form.is_valid():
            invite = form.save()
            messages.success(request, f"Invitation sent to {invite.invited_user.user.username}!")
            return redirect("teams:detail", slug=team.slug)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeamInviteForm(team=team, sender=request.user)

    return render(request, "teams/invite_member.html", {"team": team, "form": form})


@login_required
def my_invites(request):
    profile = _ensure_profile(request.user)
    invites = TeamInvite.objects.filter(
        invited_user=profile, status="PENDING"
    ).select_related("team", "invited_by__user")
    return render(request, "teams/my_invites.html", {"invites": invites})


@login_required
def accept_invite_view(request, token: str):
    invite = get_object_or_404(TeamInvite, token=token)
    profile = _ensure_profile(request.user)

    if invite.invited_user_id != profile.id or invite.status != "PENDING":
        messages.error(request, "This invite cannot be accepted.")
        return redirect(reverse("teams:my_invites"))

    # One-team-per-game guard: block if user already in another team of this game
    game_code = getattr(invite.team, "game", None)
    if game_code and TeamMembership.objects.filter(profile=profile, team__game=game_code).exists():
        messages.error(request, f"You already belong to a {game_code.title()} team.")
        return redirect(reverse("teams:my_invites"))

    TeamMembership.objects.get_or_create(
        team=invite.team,
        profile=profile,
        defaults={"role": getattr(TeamMembership.Role, "PLAYER", "PLAYER")},
    )
    invite.status = "ACCEPTED"
    invite.save(update_fields=["status"])
    messages.success(request, f"You joined {getattr(invite.team, 'tag', invite.team.name)}.")
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
    messages.info(request, f"Invite from {getattr(invite.team, 'tag', invite.team.name)} declined.")
    return redirect(reverse("teams:my_invites"))


# -------------------------
# Leave team (non-captain)
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def leave_team_view(request, slug: str):
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)

    if _is_captain(profile, team):
        messages.error(request, "Captain must transfer captaincy before leaving the team.")
        return redirect(reverse("teams:detail", kwargs={"slug": team.slug}))

    TeamMembership.objects.filter(team=team, profile=profile).delete()
    messages.success(request, "You left the team.")
    return redirect(reverse("teams:detail", kwargs={"slug": team.slug}))


# -------------------------
# Join team (public, auth, guard one-team-per-game)
# -------------------------
@login_required
@require_http_methods(["POST", "GET"])
def join_team_view(request, slug: str):
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)

    # Guard: already member
    if TeamMembership.objects.filter(team=team, profile=profile).exists():
        messages.info(request, "You are already a member of this team.")
        return redirect("teams:detail", slug=team.slug)

    # Guard: one-team-per-game
    game_code = getattr(team, "game", None)
    if game_code and TeamMembership.objects.filter(profile=profile, team__game=game_code).exists():
        messages.error(request, f"You already belong to a {game_code.title()} team.")
        return redirect("teams:detail", slug=team.slug)

    # Optional: only allow if team is open (if such a field exists)
    if hasattr(team, "is_open") and not getattr(team, "is_open"):
        messages.error(request, "This team is not open to join directly. Ask for an invite.")
        return redirect("teams:detail", slug=team.slug)

    TeamMembership.objects.get_or_create(
        team=team,
        profile=profile,
        defaults={"role": getattr(TeamMembership.Role, "PLAYER", "PLAYER")},
    )
    messages.success(request, f"You joined {getattr(team, 'tag', team.name)}.")
    return redirect("teams:detail", slug=team.slug)


# -------------------------
# Team member management
# -------------------------
@login_required
@require_http_methods(["POST"])
def kick_member_view(request, slug: str, profile_id: int):
    """Remove a member from the team (captain only)."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        messages.error(request, "Only the team captain can remove members.")
        return redirect("teams:detail", slug=team.slug)

    try:
        membership = get_object_or_404(TeamMembership, team=team, profile_id=profile_id)
        member_name = membership.user.user.username
        membership.delete()
        messages.success(request, f"Member {member_name} has been removed from the team.")
    except TeamMembership.DoesNotExist:
        messages.error(request, "Member not found in this team.")
    
    return redirect("teams:detail", slug=team.slug)


@login_required
@require_http_methods(["POST"])
def leave_team_view(request, slug: str):
    """Allow a member to leave the team."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Captain cannot leave (must transfer captaincy first)
    if _is_captain(profile, team):
        messages.error(request, "As captain, you must transfer captaincy before leaving the team.")
        return redirect("teams:manage", slug=team.slug)
    
    try:
        membership = get_object_or_404(TeamMembership, team=team, user=profile)
        membership.delete()
        messages.success(request, f"You have left team {team.name}.")
        return redirect("teams:list")
    except TeamMembership.DoesNotExist:
        messages.error(request, "You are not a member of this team.")
        return redirect("teams:detail", slug=team.slug)


@login_required
@require_http_methods(["POST"])
def transfer_captaincy_view(request, slug: str, profile_id: int):
    """Transfer team captaincy to another member."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        messages.error(request, "Only the current captain can transfer captaincy.")
        return redirect("teams:detail", slug=team.slug)
    
    try:
        new_captain_membership = get_object_or_404(
            TeamMembership, 
            team=team, 
            profile_id=profile_id,
            status="ACTIVE"
        )
        
        # Update team captain
        team.captain = new_captain_membership.user
        team.save()
        
        messages.success(
            request, 
            f"Team captaincy transferred to {new_captain_membership.user.user.username}."
        )
    except TeamMembership.DoesNotExist:
        messages.error(request, "Selected user is not an active member of this team.")
    
    return redirect("teams:detail", slug=team.slug)


@login_required
@require_http_methods(["GET", "POST"])
def team_settings_view(request, slug: str):
    """Team settings page for advanced configuration."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        messages.error(request, "Only the team captain can access team settings.")
        return redirect("teams:detail", slug=team.slug)
    
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_setting":
            # Handle individual setting updates
            for field in ['is_open', 'is_recruiting']:
                if field in request.POST:
                    setattr(team, field, request.POST.get(field) == 'true')
            team.save()
            messages.success(request, "Team settings updated successfully!")
        return redirect("teams:settings", slug=team.slug)
    
    context = {
        "team": team,
        "members": team.memberships.filter(status="ACTIVE").select_related("user__user"),
        "pending_invites": team.invites.filter(status="PENDING").select_related("invited_user__user"),
    }
    
    return render(request, "teams/settings.html", context)


@login_required
@require_http_methods(["POST"])
def delete_team_view(request, slug: str):
    """Delete a team permanently (captain only)."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        messages.error(request, "Only the team captain can delete the team.")
        return redirect("teams:detail", slug=team.slug)
    
    confirm_name = request.POST.get("confirm_name", "").strip()
    if confirm_name != team.name:
        messages.error(request, "Team name confirmation does not match.")
        return redirect("teams:settings", slug=team.slug)
    
    team_name = team.name
    team.delete()
    messages.success(request, f"Team '{team_name}' has been permanently deleted.")
    return redirect("teams:list")


@login_required
@require_http_methods(["POST"])
def cancel_invite_view(request, slug: str):
    """Cancel a pending team invitation."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        messages.error(request, "Only the team captain can cancel invitations.")
        return redirect("teams:detail", slug=team.slug)
    
    invite_id = request.POST.get("invite_id")
    try:
        invite = get_object_or_404(TeamInvite, id=invite_id, team=team, status="PENDING")
        invited_user_name = invite.invited_user.display_name
        invite.delete()
        messages.success(request, f"Invitation to {invited_user_name} has been cancelled.")
    except TeamInvite.DoesNotExist:
        messages.error(request, "Invitation not found or already processed.")
    
    return redirect("teams:manage", slug=team.slug)
