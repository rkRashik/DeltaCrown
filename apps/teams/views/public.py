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
from ..models.ranking_settings import TeamRankingSettings
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
    ("pubg", "PUBG"),
    ("freefire", "Free Fire"),
    ("mlbb", "Mobile Legends: Bang Bang"),
    ("csgo", "Counter-Strike"),
    ("cs2", "Counter-Strike 2"),
    ("fc26", "EA Sports FC 26"),
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
    Common queryset with configurable tournament-based ranking annotations.
    Uses TeamRankingSettings for point calculations.
    """
    from django.db.models import Case, When, IntegerField
    from ..models import TeamRankingSettings
    
    # Get active ranking settings
    ranking_settings = TeamRankingSettings.get_active_settings()
    
    qs = Team.objects.all().distinct()

    # Captain relation is optional in some installs; guard select_related
    try:
        qs = qs.select_related("captain__user")
    except Exception:
        pass

    # Annotated counts for proper ranking
    qs = qs.annotate(
        # Count active memberships
        memberships_count=Coalesce(Count("memberships", distinct=True), Value(0)),
        
        # Count total achievements
        achievements_count=Coalesce(Count("achievements", distinct=True), Value(0)),
        
        # Count tournament wins (WINNER placements)
        tournament_wins=Coalesce(
            Count("achievements", filter=Q(achievements__placement="WINNER"), distinct=True), 
            Value(0)
        ),
        
        # Count runner-up positions
        runner_up_count=Coalesce(
            Count("achievements", filter=Q(achievements__placement="RUNNER_UP"), distinct=True),
            Value(0)
        ),
        
        # Count top 4 finishes
        top4_count=Coalesce(
            Count("achievements", filter=Q(achievements__placement="TOP4"), distinct=True),
            Value(0)
        ),
        
        # Count top 8 finishes
        top8_count=Coalesce(
            Count("achievements", filter=Q(achievements__placement="TOP8"), distinct=True),
            Value(0)
        ),
        
        # Calculate configurable ranking score
        calculated_ranking_score=Coalesce(
            Case(
                When(achievements__placement="WINNER", then=Value(ranking_settings.tournament_victory_points)),
                When(achievements__placement="RUNNER_UP", then=Value(ranking_settings.runner_up_points)),
                When(achievements__placement="TOP4", then=Value(ranking_settings.top4_finish_points)),
                When(achievements__placement="TOP8", then=Value(ranking_settings.top8_finish_points)),
                When(achievements__placement="PARTICIPANT", then=Value(ranking_settings.participation_points)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            Value(0)
        )
    )
    
    # Add ranking settings to context for template access
    qs.ranking_settings = ranking_settings

    # Recent activity timestamp fallback
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
    Sorting keys based on configurable tournament achievements:
    - powerrank (default): calculated ranking score, tournament wins, achievements
    - recent: recent_activity_at desc  
    - members: members_count desc
    - az: name asc
    - game: primary_game asc (alphabetical by game name)
    - points: total_points desc (highest points first)
    
    Optional 'order' parameter can be 'asc' or 'desc' to override default ordering.
    """
    sort = (request.GET.get("sort") or "powerrank").lower()
    order = (request.GET.get("order") or "").lower()
    
    # Determine if we should reverse the default ordering
    reverse_order = order == "desc" if order in ("asc", "desc") else False
    
    if sort == "recent":
        base_order = ["-recent_activity_at", "name"]
        return qs.order_by(*_apply_order_direction(base_order, reverse_order, default_desc=True))
    if sort == "members":
        base_order = ["-memberships_count", "name"]
        return qs.order_by(*_apply_order_direction(base_order, reverse_order, default_desc=True))
    if sort == "az":
        base_order = ["name"]
        return qs.order_by(*_apply_order_direction(base_order, reverse_order, default_desc=False))
    if sort == "game":
        base_order = ["primary_game", "name"]
        return qs.order_by(*_apply_order_direction(base_order, reverse_order, default_desc=False))
    if sort == "points":
        base_order = ["-total_points", "-adjust_points", "name"]
        return qs.order_by(*_apply_order_direction(base_order, reverse_order, default_desc=True))
    
    # Configurable tournament-based ranking (powerrank)
    base_order = [
        "-calculated_ranking_score",  # Primary: calculated score from settings
        "-tournament_wins",           # Tournament victories
        "-runner_up_count",          # Runner-up positions  
        "-top4_count",               # Top 4 finishes
        "-top8_count",               # Top 8 finishes
        "-achievements_count",        # Total achievements
        "-memberships_count",         # Team size bonus
        "-created_at",               # Team age (establishment)
        "name",                      # Alphabetical tiebreaker
    ]
    return qs.order_by(*_apply_order_direction(base_order, reverse_order, default_desc=True))


def _apply_order_direction(base_order, reverse_order, default_desc=True):
    """
    Helper to apply order direction to a list of order fields.
    
    Args:
        base_order: List of field names with optional '-' prefix
        reverse_order: Boolean to reverse the default ordering
        default_desc: Boolean indicating if the default is descending
    
    Returns:
        List of field names with proper '-' prefixes
    """
    if not reverse_order:
        return base_order
    
    # Reverse the ordering by toggling '-' prefix on primary fields
    result = []
    for field in base_order:
        if field.startswith('-'):
            # Remove '-' to make ascending
            result.append(field[1:])
        else:
            # Add '-' to make descending
            result.append('-' + field)
    
    return result


# -------------------------
# Public index (Teams hub)
# -------------------------
def team_list(request):
    """
    Public teams index with search, filters, sorting, and pagination.
    Also prepares 'my_teams_by_game' for the top row.
    Enhanced for mobile-responsive design with comprehensive statistics.
    """
    qs = _base_team_queryset()
    
    # Get total count before filtering for statistics
    total_teams = Team.objects.count()
    
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

    # Enhanced statistics for sidebar
    active_teams = Team.objects.filter(is_active=True).count()
    recruiting_teams = Team.objects.filter(
        is_active=True,
        allow_join_requests=True
    ).count()
    
    # Add power_rank calculation to teams
    teams_with_ranking = []
    for team in page_obj.object_list:
        # Calculate power ranking based on tournaments and activity
        power_rank = _calculate_team_power_rank(team)
        team.power_rank = power_rank
        
        # Add recruiting status for template
        team.recruiting = getattr(team, 'allow_join_requests', False) and getattr(team, 'is_active', True)
        
        teams_with_ranking.append(team)

    # Enhanced games list with proper display names
    games_list = [{"code": code, "name": name} for code, name in GAMES]

    # Get ranking settings for rules display
    ranking_settings = TeamRankingSettings.get_active_settings()
    
    ctx = {
        # collection
        "teams": teams_with_ranking,              # backward compatible
        "object_list": teams_with_ranking,        # for new templates
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
        "games": [code for code, name in GAMES],  # codes for filters
        "games_list": games_list,                  # full games with names
        "my_teams_by_game": _user_teams_by_game(request.user),
        # enhanced statistics
        "total_teams": total_teams,
        "active_teams": active_teams,
        "recruiting_teams": recruiting_teams,
        # ranking system
        "ranking_settings": ranking_settings,
    }
    return render(request, "teams/list.html", ctx)


def _calculate_team_power_rank(team):
    """
    Calculate team power ranking based on various factors:
    - Tournament participation
    - Team achievements 
    - Team member count
    - Team activity level
    - Verified status
    """
    base_score = 1000  # Starting score
    
    # Member count bonus (active teams with more members get higher rank)
    member_count = getattr(team, 'members_count', 0)
    member_bonus = min(member_count * 50, 400)  # Max 400 bonus for 8+ members
    
    # Activity bonus based on recent updates
    activity_bonus = 0
    if hasattr(team, 'updated_at') and team.updated_at:
        days_since_update = (timezone.now() - team.updated_at).days
        if days_since_update <= 7:
            activity_bonus = 200
        elif days_since_update <= 30:
            activity_bonus = 100
        elif days_since_update <= 90:
            activity_bonus = 50
    
    # Verified team bonus
    verified_bonus = 300 if getattr(team, 'is_verified', False) else 0
    
    # Tournament participation bonus (placeholder - can be enhanced with real tournament data)
    tournament_bonus = getattr(team, 'tournaments_played', 0) * 25
    wins_bonus = getattr(team, 'wins', 0) * 10
    
    # Social engagement bonus
    social_bonus = 0
    if hasattr(team, 'followers_count'):
        social_bonus = min(team.followers_count * 2, 200)  # Max 200 for social engagement
    
    total_score = (base_score + member_bonus + activity_bonus + 
                  verified_bonus + tournament_bonus + wins_bonus + social_bonus)
    
    return max(total_score, 0)  # Ensure non-negative score


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
        "members": team.memberships.filter(status="ACTIVE").select_related("profile__user"),
        "pending_invites": team.invites.filter(status="PENDING").select_related("invited_user__user"),
    }
    
    return render(request, "teams/settings_clean.html", context)


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


# ========================
# New Professional Team Management Views
# ========================

@login_required
@require_http_methods(["POST"])
def update_team_info_view(request, slug: str):
    """Update team information via AJAX."""
    import json
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can edit team information."}, status=403)
    
    try:
        team.name = request.POST.get('name', team.name).strip()
        team.description = request.POST.get('description', team.description)
        team.region = request.POST.get('region', team.region)
        team.primary_game = request.POST.get('primary_game', team.primary_game)
        
        if 'logo' in request.FILES:
            team.logo = request.FILES['logo']
        if 'banner' in request.FILES:
            team.banner_image = request.FILES['banner']
        
        team.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def update_privacy_view(request, slug: str):
    """Update team privacy settings via AJAX."""
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can edit privacy settings."}, status=403)
    
    try:
        team.is_public = request.POST.get('is_public') == 'on'
        team.allow_join_requests = request.POST.get('allow_join_requests') == 'on'
        team.show_statistics = request.POST.get('show_statistics') == 'on'
        team.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def kick_member_ajax_view(request, slug: str):
    """Kick a team member via AJAX."""
    import json
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can kick members."}, status=403)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        
        User = get_user_model()
        target_user = get_object_or_404(User, username=username)
        target_profile = _get_profile(target_user)
        
        if not target_profile:
            return JsonResponse({"error": "User profile not found."}, status=404)
        
        membership = get_object_or_404(TeamMembership, team=team, profile=target_profile)
        
        if membership.role == 'captain':
            return JsonResponse({"error": "Cannot kick team captain."}, status=400)
        
        membership.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def transfer_captaincy_ajax_view(request, slug: str):
    """Transfer captaincy via AJAX."""
    import json
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    if not _is_captain(profile, team):
        return JsonResponse({"error": "Only captains can transfer captaincy."}, status=403)
    
    try:
        data = json.loads(request.body)
        new_captain_username = data.get('new_captain')
        
        User = get_user_model()
        new_captain_user = get_object_or_404(User, username=new_captain_username)
        new_captain_profile = _get_profile(new_captain_user)
        
        if not new_captain_profile:
            return JsonResponse({"error": "New captain profile not found."}, status=404)
        
        # Check if user is team member
        new_captain_membership = get_object_or_404(TeamMembership, team=team, profile=new_captain_profile)
        
        # Transfer captaincy
        current_captain_membership = TeamMembership.objects.get(team=team, profile=profile)
        current_captain_membership.role = 'member'
        current_captain_membership.save()
        
        new_captain_membership.role = 'captain'
        new_captain_membership.save()
        
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def leave_team_ajax_view(request, slug: str):
    """Leave team via AJAX."""
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    try:
        membership = get_object_or_404(TeamMembership, team=team, profile=profile)
        
        if membership.role == 'captain' and team.members.count() > 1:
            return JsonResponse({"error": "Transfer captaincy before leaving the team."}, status=400)
        elif membership.role == 'captain' and team.members.count() == 1:
            # Last member and captain, delete team
            team.delete()
        else:
            membership.delete()
        
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
