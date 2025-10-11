"""
Statistics API Endpoints
=========================
Comprehensive statistics and analytics API endpoints for team performance tracking.
"""
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


def _get_user_profile(user):
    """Helper to get user profile."""
    return getattr(user, 'profile', None) or getattr(user, 'userprofile', None)


def _check_stats_permission(team, user):
    """Check if user can view team statistics."""
    if not user.is_authenticated:
        return team.show_statistics
    
    profile = _get_user_profile(user)
    TeamMembership = apps.get_model("teams", "TeamMembership")
    
    # Team members can always see stats
    is_member = TeamMembership.objects.filter(
        team=team,
        profile=profile,
        status="ACTIVE"
    ).exists()
    
    if is_member:
        return True
    
    # Otherwise check public setting
    return team.show_statistics


@login_required
def get_team_statistics(request, slug: str):
    """
    Get comprehensive team statistics using TeamAnalytics model.
    Returns detailed stats including win rate, streaks, tournaments, etc.
    """
    Team = apps.get_model("teams", "Team")
    TeamAnalytics = apps.get_model("teams", "TeamAnalytics")
    
    team = get_object_or_404(Team, slug=slug)
    
    # Permission check
    if not _check_stats_permission(team, request.user):
        return JsonResponse({"error": "Statistics are private"}, status=403)
    
    # Get analytics data
    try:
        analytics = TeamAnalytics.objects.get(team=team, game=team.game)
    except TeamAnalytics.DoesNotExist:
        # Create default analytics if not exists
        analytics = TeamAnalytics.objects.create(
            team=team,
            game=team.game
        )
    
    # Calculate additional metrics
    total_matches = analytics.total_matches
    win_percentage = float(analytics.win_rate) if analytics.win_rate else 0
    loss_percentage = 0
    draw_percentage = 0
    
    if total_matches > 0:
        loss_percentage = round((analytics.matches_lost / total_matches) * 100, 2)
        draw_percentage = round((analytics.matches_drawn / total_matches) * 100, 2)
    
    # Get recent points history (last 30 days)
    recent_points = analytics.points_history[-30:] if analytics.points_history else []
    
    # Format game-specific stats
    game_stats = analytics.game_specific_stats or {}
    
    # Calculate streak description
    if analytics.current_streak > 0:
        streak_text = f"{analytics.current_streak}W"
        streak_type = "win"
    elif analytics.current_streak < 0:
        streak_text = f"{abs(analytics.current_streak)}L"
        streak_type = "loss"
    else:
        streak_text = "No streak"
        streak_type = "none"
    
    # Calculate form (last 5 matches)
    form = []
    if analytics.points_history:
        recent_matches = analytics.points_history[-5:]
        for match in recent_matches:
            reason = match.get('reason', '').lower()
            if 'win' in reason:
                form.append('W')
            elif 'loss' in reason or 'lost' in reason:
                form.append('L')
            elif 'draw' in reason:
                form.append('D')
    
    response_data = {
        "success": True,
        "statistics": {
            # Basic Stats
            "total_matches": total_matches,
            "matches_won": analytics.matches_won,
            "matches_lost": analytics.matches_lost,
            "matches_drawn": analytics.matches_drawn,
            
            # Win Rate
            "win_rate": win_percentage,
            "loss_rate": loss_percentage,
            "draw_rate": draw_percentage,
            
            # Points
            "total_points": analytics.total_points,
            "points_history": recent_points,
            
            # Tournaments
            "tournaments_participated": analytics.tournaments_participated,
            "tournaments_won": analytics.tournaments_won,
            "tournament_win_rate": round(
                (analytics.tournaments_won / analytics.tournaments_participated * 100)
                if analytics.tournaments_participated > 0 else 0,
                2
            ),
            
            # Streaks
            "current_streak": analytics.current_streak,
            "streak_text": streak_text,
            "streak_type": streak_type,
            "best_win_streak": analytics.best_win_streak,
            "form": form,
            
            # Activity
            "last_match_date": analytics.last_match_date.isoformat() if analytics.last_match_date else None,
            
            # Game-specific
            "game_specific_stats": game_stats,
        }
    }
    
    return JsonResponse(response_data)


@login_required
def get_match_history(request, slug: str):
    """
    Get detailed match history for a team.
    Returns last 20 matches with scores, opponents, and results.
    """
    Team = apps.get_model("teams", "Team")
    MatchRecord = apps.get_model("teams", "MatchRecord")
    
    team = get_object_or_404(Team, slug=slug)
    
    # Permission check
    if not _check_stats_permission(team, request.user):
        return JsonResponse({"error": "Match history is private"}, status=403)
    
    # Get match records
    matches = MatchRecord.objects.filter(
        team=team
    ).select_related(
        'opponent_team', 'tournament'
    ).order_by('-match_date')[:20]
    
    # Format matches
    match_list = []
    for match in matches:
        match_data = {
            'id': match.id,
            'date': match.match_date.isoformat(),
            'opponent': match.opponent_name,
            'opponent_logo': match.opponent_team.logo.url if (match.opponent_team and match.opponent_team.logo) else None,
            'result': match.result,
            'score': match.score,
            'team_score': match.team_score,
            'opponent_score': match.opponent_score,
            'points_earned': match.points_earned,
            'tournament': match.tournament.name if match.tournament else "Friendly Match",
            'map': match.map_played,
            'duration': match.duration_minutes,
            'replay_url': match.replay_url,
            'notes': match.notes,
        }
        match_list.append(match_data)
    
    # Calculate stats from matches
    total_matches = matches.count()
    wins = matches.filter(result='win').count()
    losses = matches.filter(result='loss').count()
    draws = matches.filter(result='draw').count()
    
    return JsonResponse({
        "success": True,
        "matches": match_list,
        "summary": {
            "total": total_matches,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": round((wins / total_matches * 100) if total_matches > 0 else 0, 2)
        }
    })


@login_required
def get_win_rate_chart(request, slug: str):
    """
    Get win rate data over time for charts.
    Returns data formatted for Chart.js.
    """
    Team = apps.get_model("teams", "Team")
    MatchRecord = apps.get_model("teams", "MatchRecord")
    
    team = get_object_or_404(Team, slug=slug)
    
    # Permission check
    if not _check_stats_permission(team, request.user):
        return JsonResponse({"error": "Statistics are private"}, status=403)
    
    # Get matches from last 90 days
    ninety_days_ago = timezone.now() - timedelta(days=90)
    matches = MatchRecord.objects.filter(
        team=team,
        match_date__gte=ninety_days_ago
    ).order_by('match_date')
    
    # Group by week and calculate win rate
    chart_data = {
        'labels': [],
        'win_rate': [],
        'wins': [],
        'losses': [],
    }
    
    # Calculate cumulative win rate over time
    cumulative_wins = 0
    cumulative_losses = 0
    cumulative_draws = 0
    
    for match in matches:
        if match.result == 'win':
            cumulative_wins += 1
        elif match.result == 'loss':
            cumulative_losses += 1
        elif match.result == 'draw':
            cumulative_draws += 1
        
        total = cumulative_wins + cumulative_losses + cumulative_draws
        current_win_rate = round((cumulative_wins / total * 100) if total > 0 else 0, 2)
        
        chart_data['labels'].append(match.match_date.strftime('%m/%d'))
        chart_data['win_rate'].append(current_win_rate)
        chart_data['wins'].append(cumulative_wins)
        chart_data['losses'].append(cumulative_losses)
    
    return JsonResponse({
        "success": True,
        "chart_data": chart_data
    })


@login_required
def get_player_statistics(request, slug: str):
    """
    Get player statistics for all team members.
    Returns comprehensive player performance data.
    """
    Team = apps.get_model("teams", "Team")
    PlayerStats = apps.get_model("teams", "PlayerStats")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    
    team = get_object_or_404(Team, slug=slug)
    profile = _get_user_profile(request.user)
    
    # Permission check - only team members can see detailed player stats
    is_member = TeamMembership.objects.filter(
        team=team,
        profile=profile,
        status="ACTIVE"
    ).exists()
    
    if not is_member:
        return JsonResponse({"error": "Only team members can view player statistics"}, status=403)
    
    # Get all active members
    members = TeamMembership.objects.filter(
        team=team,
        status="ACTIVE"
    ).select_related('profile__user')
    
    # Get player stats for each member
    player_stats_list = []
    for member in members:
        try:
            stats = PlayerStats.objects.get(
                player=member.profile,
                team=team,
                game=team.game
            )
        except PlayerStats.DoesNotExist:
            # Create default stats
            stats = PlayerStats.objects.create(
                player=member.profile,
                team=team,
                game=team.game
            )
        
        # Calculate win rate
        win_rate = 0
        if stats.matches_played > 0:
            win_rate = round((stats.matches_won / stats.matches_played) * 100, 2)
        
        player_data = {
            'player_id': member.profile.id,
            'username': member.profile.user.username,
            'display_name': member.profile.display_name or member.profile.user.username,
            'avatar': member.profile.avatar.url if member.profile.avatar else None,
            'role': member.role,
            
            # Stats
            'tournaments_played': stats.tournaments_played,
            'matches_played': stats.matches_played,
            'matches_won': stats.matches_won,
            'win_rate': win_rate,
            'attendance_rate': float(stats.attendance_rate),
            'mvp_count': stats.mvp_count,
            'contribution_score': float(stats.contribution_score),
            'individual_rating': float(stats.individual_rating),
            
            # Activity
            'last_active': stats.last_active.isoformat() if stats.last_active else None,
            'is_active': stats.is_active,
            
            # Game-specific
            'game_specific_stats': stats.game_specific_stats or {},
        }
        
        player_stats_list.append(player_data)
    
    # Sort by contribution score
    player_stats_list.sort(key=lambda x: x['contribution_score'], reverse=True)
    
    return JsonResponse({
        "success": True,
        "player_stats": player_stats_list
    })


@login_required
def get_ranking_history(request, slug: str):
    """
    Get ranking history for visualization.
    Returns ranking progression over time.
    """
    Team = apps.get_model("teams", "Team")
    TeamRankingHistory = apps.get_model("teams", "TeamRankingHistory")
    
    team = get_object_or_404(Team, slug=slug)
    
    # Get last 30 days of ranking history
    thirty_days_ago = timezone.now() - timedelta(days=30)
    history = TeamRankingHistory.objects.filter(
        team=team,
        created_at__gte=thirty_days_ago
    ).order_by('created_at')
    
    # Format for chart - aggregate by day
    from collections import defaultdict
    daily_data = defaultdict(lambda: {'points': 0, 'changes': 0})
    
    for record in history:
        date_key = record.created_at.strftime('%m/%d')
        daily_data[date_key]['points'] = record.points_after
        daily_data[date_key]['changes'] += record.points_change
    
    # If no history, use current team points
    if not daily_data:
        today = timezone.now().strftime('%m/%d')
        daily_data[today] = {
            'points': team.total_points or 0,
            'changes': 0
        }
    
    # Format for chart
    chart_data = {
        'labels': list(daily_data.keys()),
        'points': [data['points'] for data in daily_data.values()],
        'global_rank': [],  # Not available in current model
        'regional_rank': [],
        'game_rank': [],
    }
    
    # Get current ranking breakdown
    TeamRankingBreakdown = apps.get_model("teams", "TeamRankingBreakdown")
    try:
        breakdown = TeamRankingBreakdown.objects.get(team=team)
        breakdown_data = {
            'tournament_points': (breakdown.tournament_winner_points + 
                                 breakdown.tournament_runner_up_points + 
                                 breakdown.tournament_top_4_points +
                                 breakdown.tournament_participation_points),
            'win_loss_points': 0,  # Not tracked separately in current model
            'activity_bonus': (breakdown.member_bonus + 
                              breakdown.age_bonus +
                              breakdown.achievement_bonus),
            'adjustment_points': breakdown.admin_adjustments,
            'final_total': breakdown.total_points,
        }
    except TeamRankingBreakdown.DoesNotExist:
        breakdown_data = {
            'tournament_points': 0,
            'win_loss_points': 0,
            'activity_bonus': 0,
            'adjustment_points': 0,
            'final_total': team.total_points or 0,
        }
    
    return JsonResponse({
        "success": True,
        "chart_data": chart_data,
        "current_breakdown": breakdown_data
    })


@login_required
def get_performance_metrics(request, slug: str):
    """
    Get advanced performance metrics and analytics.
    """
    Team = apps.get_model("teams", "Team")
    TeamAnalytics = apps.get_model("teams", "TeamAnalytics")
    MatchRecord = apps.get_model("teams", "MatchRecord")
    
    team = get_object_or_404(Team, slug=slug)
    
    # Permission check
    if not _check_stats_permission(team, request.user):
        return JsonResponse({"error": "Statistics are private"}, status=403)
    
    # Get analytics
    try:
        analytics = TeamAnalytics.objects.get(team=team, game=team.game)
    except TeamAnalytics.DoesNotExist:
        analytics = TeamAnalytics.objects.create(team=team, game=team.game)
    
    # Calculate various metrics
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_matches = MatchRecord.objects.filter(
        team=team,
        match_date__gte=thirty_days_ago
    )
    
    # Win rate by opponent type
    tournament_matches = recent_matches.filter(tournament__isnull=False)
    friendly_matches = recent_matches.filter(tournament__isnull=True)
    
    tournament_win_rate = 0
    if tournament_matches.exists():
        tournament_wins = tournament_matches.filter(result='win').count()
        tournament_win_rate = round((tournament_wins / tournament_matches.count() * 100), 2)
    
    friendly_win_rate = 0
    if friendly_matches.exists():
        friendly_wins = friendly_matches.filter(result='win').count()
        friendly_win_rate = round((friendly_wins / friendly_matches.count() * 100), 2)
    
    # Average points per match
    total_points = recent_matches.aggregate(Sum('points_earned'))['points_earned__sum'] or 0
    avg_points_per_match = round((total_points / recent_matches.count()) if recent_matches.count() > 0 else 0, 2)
    
    # Most faced opponents
    from django.db.models import Count
    top_opponents = recent_matches.values('opponent_name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Performance by day of week
    from collections import defaultdict
    wins_by_day = defaultdict(int)
    matches_by_day = defaultdict(int)
    
    for match in recent_matches:
        day = match.match_date.strftime('%A')
        matches_by_day[day] += 1
        if match.result == 'win':
            wins_by_day[day] += 1
    
    performance_by_day = []
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        if day in matches_by_day:
            win_rate = round((wins_by_day[day] / matches_by_day[day] * 100), 2)
            performance_by_day.append({
                'day': day,
                'matches': matches_by_day[day],
                'win_rate': win_rate
            })
    
    return JsonResponse({
        "success": True,
        "metrics": {
            "tournament_win_rate": tournament_win_rate,
            "friendly_win_rate": friendly_win_rate,
            "avg_points_per_match": avg_points_per_match,
            "top_opponents": list(top_opponents),
            "performance_by_day": performance_by_day,
            "total_recent_matches": recent_matches.count(),
        }
    })
