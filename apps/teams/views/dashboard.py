# apps/teams/views/dashboard.py
"""
Team Dashboard & Profile Views
================================
Comprehensive team management dashboard for captains/managers and 
public team profile pages for fans and visitors.
"""
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch, Avg, Case, When, IntegerField
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from decimal import Decimal


def _get_user_profile(user):
    """Helper to get user profile."""
    return getattr(user, 'profile', None) or getattr(user, 'userprofile', None)


@login_required
def team_dashboard_view(request, slug: str):
    """
    Team Dashboard - Captain/Manager View
    Central hub for team management with comprehensive controls.
    """
    Team = apps.get_model("teams", "Team")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    TeamInvite = apps.get_model("teams", "TeamInvite")
    TeamAnalytics = apps.get_model("teams", "TeamAnalytics")
    TeamAchievement = apps.get_model("teams", "TeamAchievement")
    TeamActivity = apps.get_model("teams", "TeamActivity")
    TeamFollower = apps.get_model("teams", "TeamFollower")
    TeamPost = apps.get_model("teams", "TeamPost")
    
    team = get_object_or_404(Team, slug=slug)
    profile = _get_user_profile(request.user)
    
    # Permission check - only captain and managers can access dashboard
    is_captain = (team.captain_id == getattr(profile, "id", None))
    membership = TeamMembership.objects.filter(
        team=team, 
        profile=profile, 
        status="ACTIVE"
    ).first()
    
    is_manager = membership and membership.role in ["MANAGER", "CO_CAPTAIN"]
    
    if not (is_captain or is_manager):
        messages.error(request, "You don't have permission to access this team's dashboard.")
        return redirect("teams:detail", slug=slug)
    
    # Get comprehensive team data
    # 1. Roster with role ordering (Captain first)
    from django.db.models import Case, When, IntegerField
    
    roster = TeamMembership.objects.filter(
        team=team,
        status="ACTIVE"
    ).select_related("profile__user").annotate(
        role_order=Case(
            When(role="CAPTAIN", then=0),
            When(role="MANAGER", then=1),
            When(role="PLAYER", then=2),
            When(role="SUB", then=3),
            default=4,
            output_field=IntegerField()
        )
    ).order_by("role_order", "joined_at")
    
    # 2. Pending invites
    pending_invites = TeamInvite.objects.filter(
        team=team,
        status="PENDING",
        expires_at__gt=timezone.now()
    ).select_related("invited_user", "inviter").order_by("-created_at")
    
    # 3. Team stats - Use TeamAnalytics (new comprehensive model)
    try:
        latest_stats = TeamAnalytics.objects.get(team=team, game=team.game)
    except TeamAnalytics.DoesNotExist:
        # Create default analytics if not exists
        latest_stats = TeamAnalytics.objects.create(
            team=team,
            game=team.game
        )
    
    # 4. Recent achievements
    achievements = TeamAchievement.objects.filter(team=team).order_by("-year", "-id")[:5]
    total_achievements = TeamAchievement.objects.filter(team=team).count()
    
    # 5. Activity feed (last 20 activities)
    activities = TeamActivity.objects.filter(
        team=team
    ).select_related(
        "actor__user", "related_user__user", "related_post"
    ).order_by("-created_at")[:20]
    
    # 6. Social metrics
    followers_count = TeamFollower.objects.filter(team=team).count()
    posts_count = TeamPost.objects.filter(team=team, published_at__isnull=False).count()
    
    # 7. Recent posts
    recent_posts = TeamPost.objects.filter(
        team=team,
        published_at__isnull=False
    ).select_related("author__user").order_by("-published_at")[:5]
    
    # 8. Upcoming matches (if tournaments app exists)
    try:
        Match = apps.get_model("tournaments", "Match")
        upcoming_matches = Match.objects.filter(
            Q(team_a=team) | Q(team_b=team),
            state="SCHEDULED",
            start_at__gte=timezone.now()
        ).order_by("start_at")[:5]
    except:
        upcoming_matches = []
    
    # 9. Game-specific data
    game_config = None
    if team.game:
        from apps.teams.game_config import get_game_config
        try:
            game_config = get_game_config(team.game)
        except KeyError:
            game_config = None
    
    # 10. Calculate roster capacity
    max_roster = 8  # Default
    if game_config:
        max_roster = game_config.max_starters + game_config.max_substitutes
    
    current_roster_size = roster.count()
    pending_invites_count = pending_invites.count()
    available_slots = max(0, max_roster - current_roster_size - pending_invites_count)
    
    # 11. Get notifications/alerts for captain
    alerts = []
    
    # Check for expired invites in last 7 days
    recent_expired = TeamInvite.objects.filter(
        team=team,
        status="PENDING",
        expires_at__lte=timezone.now(),
        expires_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    if recent_expired > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{recent_expired} invite(s) expired recently. Consider resending.'
        })
    
    # Check for low roster
    if game_config and current_roster_size < game_config.min_starters:
        alerts.append({
            'type': 'danger',
            'message': f'Roster below minimum size ({current_roster_size}/{game_config.min_starters}). Recruit more players!'
        })
    
    # Check for upcoming tournament deadlines (placeholder)
    # This would be implemented with actual tournament registration logic
    
    # 12. Calculate win rate from TeamAnalytics
    win_rate = float(latest_stats.win_rate) if latest_stats and latest_stats.win_rate else 0
    
    # 13. Calculate global rank (placeholder - would use actual ranking system)
    global_rank = None
    try:
        TeamRankingBreakdown = apps.get_model("teams", "TeamRankingBreakdown")
        ranking_breakdown = TeamRankingBreakdown.objects.filter(team=team).first()
        if ranking_breakdown:
            global_rank = TeamRankingBreakdown.objects.filter(
                final_total__gt=ranking_breakdown.final_total
            ).count() + 1
    except:
        pass
    
    # 14. Format join requests (if using JoinRequest model)
    join_requests = []
    try:
        JoinRequest = apps.get_model("teams", "JoinRequest")
        join_requests = JoinRequest.objects.filter(
            team=team,
            status="PENDING"
        ).select_related("user__profile", "user").order_by("-created_at")
    except:
        pass
    
    # 15. Format activities for display with icons
    formatted_activities = []
    for activity in activities:
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
        
        formatted_activities.append({
            'id': activity.id,
            'type': activity.activity_type,
            'icon': icon_map.get(activity.activity_type, 'info-circle'),
            'description': activity.description,
            'time_ago': activity.created_at,
            'actor': activity.actor
        })
    
    # 16. Prepare chart data for performance graph
    chart_data = {
        'labels': [],
        'wins': [],
        'losses': [],
    }
    
    # Get last 10 matches results if available
    try:
        Match = apps.get_model("tournaments", "Match")
        recent_results = Match.objects.filter(
            Q(team_a=team) | Q(team_b=team),
            state="VERIFIED"
        ).order_by("-start_at")[:10]
        
        for match in reversed(list(recent_results)):
            chart_data['labels'].append(match.start_at.strftime('%m/%d'))
            if (match.team_a == team and match.winner == match.team_a) or \
               (match.team_b == team and match.winner == match.team_b):
                chart_data['wins'].append(1)
                chart_data['losses'].append(0)
            else:
                chart_data['wins'].append(0)
                chart_data['losses'].append(1)
    except:
        pass

    context = {
        'team': team,
        'is_captain': is_captain,
        'is_manager': is_manager,
        'membership': membership,
        
        # Roster data
        'roster': roster,
        'roster_count': current_roster_size,
        'members_count': current_roster_size,
        'max_roster': max_roster,
        'available_slots': available_slots,
        
        # Invites & Requests
        'pending_invites': pending_invites,
        'pending_invites_count': pending_invites_count,
        'join_requests': join_requests,
        'pending_count': pending_invites_count + len(join_requests),
        
        # Stats & Achievements
        'latest_stats': latest_stats,
        'win_rate': win_rate,
        'global_rank': global_rank or 'Unranked',
        'achievements': achievements,
        'recent_achievements': achievements[:3],
        'total_achievements': total_achievements,
        
        # Social
        'followers_count': followers_count,
        'posts_count': posts_count,
        'recent_posts': recent_posts,
        
        # Activity
        'activities': formatted_activities,
        'recent_activities': formatted_activities[:10],
        
        # Matches
        'upcoming_matches': upcoming_matches,
        'matches_count': len(upcoming_matches),
        
        # Game config
        'game_config': game_config,
        
        # Alerts
        'alerts': alerts,
        
        # Chart data
        'chart_data': chart_data,
        
        # Team members for display
        'team_members': roster[:5],  # First 5 for quick view
    }
    
    return render(request, "teams/dashboard_modern.html", context)


def team_profile_view(request, slug: str):
    """
    Team Profile Page - Public/Member View
    Showcase team to public, fans, and tournament organizers.
    """
    Team = apps.get_model("teams", "Team")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    TeamAnalytics = apps.get_model("teams", "TeamAnalytics")
    TeamAchievement = apps.get_model("teams", "TeamAchievement")
    TeamFollower = apps.get_model("teams", "TeamFollower")
    TeamPost = apps.get_model("teams", "TeamPost")
    TeamActivity = apps.get_model("teams", "TeamActivity")
    
    team = get_object_or_404(Team, slug=slug)
    
    # Check if team is public or user has access
    profile = _get_user_profile(request.user) if request.user.is_authenticated else None
    
    is_member = False
    is_captain = False
    is_following = False
    
    if profile:
        is_member = TeamMembership.objects.filter(
            team=team, 
            profile=profile, 
            status="ACTIVE"
        ).exists()
        is_captain = (team.captain_id == getattr(profile, "id", None))
        is_following = TeamFollower.objects.filter(
            team=team,
            follower=profile
        ).exists()
    
    # Privacy check
    if not team.is_public and not is_member and not request.user.is_staff:
        messages.error(request, "This team's profile is private.")
        return redirect("teams:list")
    
    # Get team data
    # 1. Roster (Captain first)
    from django.db.models import Case, When, IntegerField
    
    roster = TeamMembership.objects.filter(
        team=team,
        status="ACTIVE"
    ).select_related("profile__user").annotate(
        role_order=Case(
            When(role="CAPTAIN", then=0),
            When(role="MANAGER", then=1),
            When(role="PLAYER", then=2),
            When(role="SUB", then=3),
            default=4,
            output_field=IntegerField()
        )
    ).order_by("role_order", "joined_at")
    
    # 2. Stats (if public or member) - Use TeamAnalytics
    latest_stats = None
    has_matches = False
    if team.show_statistics or is_member or request.user.is_staff:
        try:
            stats = TeamAnalytics.objects.get(team=team, game=team.game)
            # Only show stats if team has actually played matches
            # Also validate that win_rate is reasonable and matches are > 0
            if stats.total_matches > 0 and stats.win_rate >= 0 and stats.win_rate <= 100:
                latest_stats = stats
                has_matches = True
                
                # Recalculate win_rate if needed (in case it's stale)
                if stats.matches_won + stats.matches_lost > 0:
                    calculated_win_rate = (stats.matches_won / (stats.matches_won + stats.matches_lost)) * 100
                    if abs(float(stats.win_rate) - calculated_win_rate) > 0.1:
                        # Update stale win_rate
                        stats.win_rate = Decimal(str(round(calculated_win_rate, 2)))
                        stats.save(update_fields=['win_rate'])
        except TeamAnalytics.DoesNotExist:
            pass  # Don't create default stats, just leave as None
    
    # 3. Achievements
    achievements = TeamAchievement.objects.filter(team=team).order_by("-year", "-id")
    
    # Group achievements by year
    achievements_by_year = {}
    for ach in achievements:
        year = ach.year or "Undated"
        if year not in achievements_by_year:
            achievements_by_year[year] = []
        achievements_by_year[year].append(ach)
    
    # 4. Recent matches
    try:
        Match = apps.get_model("tournaments", "Match")
        recent_matches = Match.objects.filter(
            Q(team_a=team) | Q(team_b=team),
            state="VERIFIED"
        ).select_related("team_a", "team_b", "tournament").order_by("-start_at")[:5]
        
        upcoming_matches = Match.objects.filter(
            Q(team_a=team) | Q(team_b=team),
            state="SCHEDULED",
            start_at__gte=timezone.now()
        ).select_related("team_a", "team_b", "tournament").order_by("start_at")[:5]
    except:
        recent_matches = []
        upcoming_matches = []
    
    # 5. Public posts
    posts = TeamPost.objects.filter(
        team=team,
        published_at__isnull=False,
        visibility__in=["public"]
    ).select_related("author__user").prefetch_related("media").order_by(
        "-is_pinned", "-published_at"
    )[:10]
    
    # If member, show followers-only posts too
    if is_member or is_following:
        posts = TeamPost.objects.filter(
            team=team,
            published_at__isnull=False,
            visibility__in=["public", "followers"]
        ).select_related("author__user").prefetch_related("media").order_by(
            "-is_pinned", "-published_at"
        )[:10]
    
    # 6. Public activities
    activities = TeamActivity.objects.filter(
        team=team,
        is_public=True
    ).select_related("actor__user", "related_user__user").order_by("-created_at")[:10]
    
    # 7. Social counts
    followers_count = TeamFollower.objects.filter(team=team).count()
    
    # 8. Game config
    game_config = None
    if team.game:
        from apps.teams.game_config import get_game_config
        game_config = get_game_config(team.game)
    
    # 9. Social links (only if team allows)
    social_links = []
    if team.twitter:
        social_links.append({"name": "Twitter", "url": team.twitter, "icon": "twitter"})
    if team.instagram:
        social_links.append({"name": "Instagram", "url": team.instagram, "icon": "instagram"})
    if team.discord:
        social_links.append({"name": "Discord", "url": team.discord, "icon": "discord"})
    if team.youtube:
        social_links.append({"name": "YouTube", "url": team.youtube, "icon": "youtube"})
    if team.twitch:
        social_links.append({"name": "Twitch", "url": team.twitch, "icon": "twitch"})
    
    # 10. Can user join?
    can_request_join = False
    already_in_team_for_game = False
    
    if profile and not is_member and team.allow_join_requests:
        # Check if user already has a team in this game
        already_in_team_for_game = TeamMembership.objects.filter(
            profile=profile,
            team__game=team.game,
            status="ACTIVE"
        ).exists()
        
        can_request_join = not already_in_team_for_game
    
    # 11. Get ranking data
    ranking_data = None
    try:
        TeamRankingBreakdown = apps.get_model("teams", "TeamRankingBreakdown")
        ranking_breakdown = TeamRankingBreakdown.objects.filter(team=team).first()
        
        if ranking_breakdown:
            # Calculate ranks based on points
            from django.db.models import Count, Q
            Team = apps.get_model("teams", "Team")
            
            # Global rank (all teams)
            global_rank = TeamRankingBreakdown.objects.filter(
                final_total__gt=ranking_breakdown.final_total
            ).count() + 1
            
            # Regional rank (same region)
            regional_rank = TeamRankingBreakdown.objects.filter(
                final_total__gt=ranking_breakdown.final_total,
                team__region=team.region
            ).count() + 1
            
            # Game rank (same game)
            game_rank = TeamRankingBreakdown.objects.filter(
                final_total__gt=ranking_breakdown.final_total,
                team__game=team.game
            ).count() + 1
            
            ranking_data = {
                'global_rank': global_rank,
                'regional_rank': regional_rank,
                'game_rank': game_rank,
                'total_points': ranking_breakdown.final_total,
                'breakdown': ranking_breakdown
            }
    except:
        ranking_data = None
    
    context = {
        'team': team,
        'is_member': is_member,
        'is_captain': is_captain,
        'is_following': is_following,
        'can_request_join': can_request_join,
        'already_in_team_for_game': already_in_team_for_game,
        
        # Roster
        'roster': roster,
        'roster_count': roster.count(),
        
        # Stats & Achievements
        'latest_stats': latest_stats,
        'has_matches': has_matches,
        'ranking_data': ranking_data,
        'achievements_by_year': achievements_by_year,
        'total_achievements': achievements.count(),
        
        # Matches
        'recent_matches': recent_matches,
        'upcoming_matches': upcoming_matches,
        
        # Social
        'followers_count': followers_count,
        'posts': posts,
        'activities': activities,
        'social_links': social_links,
        
        # Game
        'game_config': game_config,
    }
    
    return render(request, "teams/team_detail_new.html", context)


@login_required
def follow_team(request, slug: str):
    """Follow a team."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    Team = apps.get_model("teams", "Team")
    TeamFollower = apps.get_model("teams", "TeamFollower")
    
    team = get_object_or_404(Team, slug=slug)
    profile = _get_user_profile(request.user)
    
    if not team.allow_followers:
        return JsonResponse({"error": "This team doesn't accept followers"}, status=403)
    
    follower, created = TeamFollower.objects.get_or_create(
        team=team,
        follower=profile,
        defaults={
            'notify_posts': True,
            'notify_matches': True,
            'notify_achievements': False
        }
    )
    
    if created:
        # Update team followers count
        team.followers_count = TeamFollower.objects.filter(team=team).count()
        team.save(update_fields=['followers_count'])
        
        # Create activity
        TeamActivity = apps.get_model("teams", "TeamActivity")
        TeamActivity.objects.create(
            team=team,
            activity_type="member_joined",  # Reusing for followers
            actor=profile,
            description=f"{profile.display_name or profile.user.username} started following {team.name}",
            is_public=True
        )
        
        return JsonResponse({
            "success": True,
            "message": "Successfully followed team",
            "followers_count": team.followers_count
        })
    else:
        return JsonResponse({"error": "Already following"}, status=400)


@login_required
def unfollow_team(request, slug: str):
    """Unfollow a team."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    Team = apps.get_model("teams", "Team")
    TeamFollower = apps.get_model("teams", "TeamFollower")
    
    team = get_object_or_404(Team, slug=slug)
    profile = _get_user_profile(request.user)
    
    deleted_count, _ = TeamFollower.objects.filter(
        team=team,
        follower=profile
    ).delete()
    
    if deleted_count > 0:
        # Update team followers count
        team.followers_count = TeamFollower.objects.filter(team=team).count()
        team.save(update_fields=['followers_count'])
        
        return JsonResponse({
            "success": True,
            "message": "Successfully unfollowed team",
            "followers_count": team.followers_count
        })
    else:
        return JsonResponse({"error": "Not following this team"}, status=400)


@login_required
def update_roster_order(request, slug: str):
    """Update roster member ordering (drag-and-drop)."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    import json
    
    Team = apps.get_model("teams", "Team")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    
    team = get_object_or_404(Team, slug=slug)
    profile = _get_user_profile(request.user)
    
    # Permission check
    is_captain = (team.captain_id == getattr(profile, "id", None))
    if not is_captain:
        return JsonResponse({"error": "Only captain can reorder roster"}, status=403)
    
    try:
        data = json.loads(request.body)
        order = data.get("order", [])  # List of profile IDs in new order
        
        # Update display_order for each membership
        for index, profile_id in enumerate(order):
            TeamMembership.objects.filter(
                team=team,
                profile_id=profile_id,
                status="ACTIVE"
            ).update(display_order=index)
        
        return JsonResponse({"success": True, "message": "Roster order updated"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def resend_invite(request, slug: str, invite_id: int):
    """Resend an expired or pending invite."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    Team = apps.get_model("teams", "Team")
    TeamInvite = apps.get_model("teams", "TeamInvite")
    
    team = get_object_or_404(Team, slug=slug)
    profile = _get_user_profile(request.user)
    
    # Permission check
    is_captain = (team.captain_id == getattr(profile, "id", None))
    if not is_captain:
        return JsonResponse({"error": "Only captain can resend invites"}, status=403)
    
    invite = get_object_or_404(TeamInvite, id=invite_id, team=team)
    
    # Extend expiry
    invite.expires_at = timezone.now() + timedelta(days=7)
    invite.status = "PENDING"
    invite.save(update_fields=['expires_at', 'status'])
    
    # TODO: Send notification email
    
    return JsonResponse({
        "success": True,
        "message": "Invite resent successfully",
        "new_expiry": invite.expires_at.isoformat()
    })
