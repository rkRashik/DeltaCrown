# apps/teams/views/player_views.py
"""
Player-specific views for team members.
Includes personal dashboard, settings, and team room access.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q

from apps.teams.models import Team, TeamMembership, TeamChatMessage, TeamDiscussionPost
from apps.teams.permissions import TeamPermissions


@login_required
def player_dashboard_view(request, slug):
    """
    Player's personal dashboard within a team.
    Shows their stats, upcoming matches, team context.
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

    # Get player stats (reuse existing analytics data)
    try:
        from apps.teams.models import PlayerStats, MatchRecord
        
        player_stats = PlayerStats.objects.filter(
            team=team, player=profile
        ).first()
        
        recent_matches = MatchRecord.objects.filter(
            team=team
        ).select_related('opponent_team').order_by('-match_date')[:5]
        
    except ImportError:
        player_stats = None
        recent_matches = []

    # Get upcoming schedule (if tournaments exist)
    upcoming_matches = []
    try:
        from apps.tournaments.models import TournamentRegistration
        active_registrations = TournamentRegistration.objects.filter(
            team=team,
            status='confirmed'
        ).select_related('tournament')[:3]
    except ImportError:
        active_registrations = []

    # Team context
    member_count = TeamMembership.objects.filter(
        team=team, status=TeamMembership.Status.ACTIVE
    ).count()

    context = {
        "team": team,
        "membership": membership,
        "player_stats": player_stats,
        "recent_matches": recent_matches,
        "upcoming_matches": active_registrations,
        "member_count": member_count,
        "is_owner": membership.role == TeamMembership.Role.OWNER,
        "is_manager": membership.role == TeamMembership.Role.MANAGER,
        "is_coach": membership.role == TeamMembership.Role.COACH,
        "is_player": membership.role == TeamMembership.Role.PLAYER,
    }

    return render(request, "teams/player/player_dashboard.html", context)


@login_required
def player_settings_view(request, slug):
    """
    Player settings page: profile fields, game IDs, team safety.
    Integrates with team_safety for Leave Team OTP flow.
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

    # Get player's game IDs if they exist
    game_ids = {}
    if hasattr(profile, 'game_ids'):
        game_ids = profile.game_ids or {}

    context = {
        "team": team,
        "membership": membership,
        "can_leave_team": can_leave,
        "is_owner": membership.role == TeamMembership.Role.OWNER,
        "game_ids": game_ids,
        "profile": profile,
    }

    return render(request, "teams/player/player_settings.html", context)


@login_required
def team_room_view(request, slug):
    """
    Team Room: private space for team members.
    Includes chat, discussions, announcements, and team socials.
    """
    team = get_object_or_404(Team, slug=slug)
    profile = getattr(request.user, "profile", None)

    if not profile:
        messages.error(request, "Please complete your profile first.")
        return redirect("user_profile:profile")

    # Verify membership
    membership = TeamMembership.objects.filter(
        team=team, profile=profile, status=TeamMembership.Status.ACTIVE
    ).first()

    if not membership:
        messages.error(request, "You are not a member of this team. The Team Room is private.")
        return redirect("teams:detail", slug=slug)

    # Get recent chat messages
    recent_messages = TeamChatMessage.objects.filter(
        team=team
    ).select_related('sender').order_by('-created_at')[:20]

    # Get pinned discussions
    try:
        pinned_discussions = TeamDiscussionPost.objects.filter(
            team=team,
            is_pinned=True
        ).select_related('author').order_by('-created_at')[:3]
    except:
        pinned_discussions = []

    # Get recent discussions
    try:
        recent_discussions = TeamDiscussionPost.objects.filter(
            team=team
        ).select_related('author').order_by('-created_at')[:5]
    except:
        recent_discussions = []

    # Get roster
    roster = TeamMembership.objects.filter(
        team=team, status=TeamMembership.Status.ACTIVE
    ).select_related('profile').order_by('-role', 'joined_at')

    context = {
        "team": team,
        "membership": membership,
        "recent_messages": recent_messages,
        "pinned_discussions": pinned_discussions,
        "recent_discussions": recent_discussions,
        "roster": roster,
        "is_owner": membership.role == TeamMembership.Role.OWNER,
        "is_manager": membership.role == TeamMembership.Role.MANAGER,
        "is_coach": membership.role == TeamMembership.Role.COACH,
    }

    return render(request, "teams/player/team_room.html", context)
