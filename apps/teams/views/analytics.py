"""
Analytics Views (Task 6 - Phase 3)

Views for displaying team and player analytics, dashboards, and leaderboards.
Includes both template-based views and JSON API endpoints for AJAX.
"""
from typing import Any, Dict, Optional
from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from apps.teams.models import Team, TeamAnalytics, PlayerStats, MatchRecord
from apps.teams.services import AnalyticsCalculator, AnalyticsAggregator, CSVExportService


class TeamAnalyticsDashboardView(LoginRequiredMixin, DetailView):
    """
    Main analytics dashboard for a team.
    Shows comprehensive performance metrics, charts, and statistics.
    """
    model = Team
    template_name = 'teams/analytics_dashboard.html'
    context_object_name = 'team'
    pk_url_kwarg = 'team_id'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        team = self.object
        game = self.request.GET.get('game', team.game)
        
        # Get team analytics
        try:
            team_analytics = TeamAnalytics.objects.get(team=team, game=game)
            context['team_analytics'] = team_analytics
            context['has_analytics'] = True
        except TeamAnalytics.DoesNotExist:
            context['has_analytics'] = False
            context['team_analytics'] = None
        
        if context['has_analytics']:
            # Get performance summary
            summary = AnalyticsCalculator.calculate_team_performance_summary(
                team.id, game
            )
            context['performance_summary'] = summary
            
            # Get points progression (last 30 days)
            points_progression = AnalyticsCalculator.calculate_points_progression(
                team.id, game, days=30
            )
            context['points_progression'] = points_progression
            
            # Get player statistics
            player_stats = PlayerStats.objects.filter(
                team=team,
                game=game,
                is_active=True
            ).select_related('player__user').order_by('-contribution_score')[:10]
            context['player_stats'] = player_stats
            
            # Get recent matches
            recent_matches = MatchRecord.objects.filter(
                team=team,
                game=game
            ).order_by('-match_date')[:10]
            context['recent_matches'] = recent_matches
            
            # Get period stats
            context['week_stats'] = AnalyticsAggregator.aggregate_team_stats_by_period(
                team.id, game, 'week'
            )
            context['month_stats'] = AnalyticsAggregator.aggregate_team_stats_by_period(
                team.id, game, 'month'
            )
        
        context['selected_game'] = game
        context['available_games'] = self._get_available_games(team)
        
        return context
    
    def _get_available_games(self, team: Team) -> list:
        """Get list of games this team has analytics for"""
        return TeamAnalytics.objects.filter(
            team=team
        ).values_list('game', flat=True).distinct()


class TeamPerformanceAPIView(LoginRequiredMixin, TemplateView):
    """
    JSON API endpoint for team performance data.
    Used by AJAX calls from the dashboard for dynamic charts.
    """
    
    def get(self, request, *args, **kwargs):
        team_id = kwargs.get('team_id')
        game = request.GET.get('game')
        data_type = request.GET.get('type', 'summary')
        
        if not game:
            return JsonResponse({'error': 'Game parameter required'}, status=400)
        
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return JsonResponse({'error': 'Team not found'}, status=404)
        
        # Check permissions (user must be team member or public team)
        if not self._has_permission(request.user, team):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if data_type == 'summary':
            data = AnalyticsCalculator.calculate_team_performance_summary(team_id, game)
        elif data_type == 'progression':
            days = int(request.GET.get('days', 30))
            data = {
                'progression': AnalyticsCalculator.calculate_points_progression(
                    team_id, game, days
                )
            }
        elif data_type == 'leaderboard':
            limit = int(request.GET.get('limit', 10))
            data = {
                'leaderboard': AnalyticsCalculator.get_team_leaderboard(game, limit)
            }
        elif data_type == 'players':
            limit = int(request.GET.get('limit', 10))
            data = {
                'players': AnalyticsCalculator.get_player_leaderboard(
                    game, limit, team_id
                )
            }
        elif data_type == 'matches':
            limit = int(request.GET.get('limit', 20))
            data = {
                'matches': AnalyticsCalculator.get_match_history(team_id, game, limit)
            }
        elif data_type == 'period':
            period = request.GET.get('period', 'month')
            data = AnalyticsAggregator.aggregate_team_stats_by_period(
                team_id, game, period
            )
        elif data_type == 'roles':
            data = AnalyticsAggregator.aggregate_player_stats_by_role(team_id, game)
        else:
            return JsonResponse({'error': 'Invalid data type'}, status=400)
        
        return JsonResponse(data, safe=False)
    
    def _has_permission(self, user, team: Team) -> bool:
        """Check if user has permission to view team analytics"""
        if not user.is_authenticated:
            return False
        # Team member or captain
        if team.members.filter(id=user.userprofile.id).exists():
            return True
        # Public team
        if hasattr(team, 'is_public') and team.is_public:
            return True
        # Staff/admin
        if user.is_staff or user.is_superuser:
            return True
        return False


class ExportTeamStatsView(LoginRequiredMixin, TemplateView):
    """
    View for exporting team statistics to CSV.
    """
    
    def get(self, request, *args, **kwargs):
        team_id = kwargs.get('team_id')
        game = request.GET.get('game')
        export_type = request.GET.get('type', 'summary')
        
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            raise Http404("Team not found")
        
        # Check permissions
        if not self._has_permission(request.user, team):
            return HttpResponse('Permission denied', status=403)
        
        if export_type == 'summary':
            return CSVExportService.export_team_summary_report(
                team_id,
                game,
                filename=f'{team.name}_{game}_summary.csv'
            )
        elif export_type == 'matches':
            limit = int(request.GET.get('limit', 50))
            return CSVExportService.export_match_history_with_participants(
                team_id,
                game,
                limit,
                filename=f'{team.name}_{game}_matches.csv'
            )
        elif export_type == 'analytics':
            queryset = TeamAnalytics.objects.filter(team_id=team_id, game=game)
            return CSVExportService.export_team_analytics(
                queryset,
                filename=f'{team.name}_{game}_analytics.csv'
            )
        else:
            return HttpResponse('Invalid export type', status=400)
    
    def _has_permission(self, user, team: Team) -> bool:
        """Check if user has permission to export team data"""
        if not user.is_authenticated:
            return False
        # Captain or staff
        if team.captain_id == user.userprofile.id or user.is_staff:
            return True
        return False


class PlayerAnalyticsView(LoginRequiredMixin, DetailView):
    """
    Player analytics detail view.
    Shows individual player performance across teams and games.
    """
    template_name = 'teams/player_analytics.html'
    context_object_name = 'target_player'
    
    def get_object(self, queryset=None):
        from apps.user_profile.models import UserProfile
        player_id = self.kwargs.get('player_id')
        return get_object_or_404(UserProfile, id=player_id)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        player = self.object
        game = self.request.GET.get('game')
        
        # Get all player stats
        queryset = PlayerStats.objects.filter(player=player).select_related('team')
        
        if game:
            queryset = queryset.filter(game=game)
        
        context['player_stats'] = queryset.order_by('-contribution_score')
        
        # Get match participation history
        from apps.teams.models import MatchParticipation
        participations = MatchParticipation.objects.filter(
            player=player
        ).select_related('match__team')
        
        if game:
            participations = participations.filter(match__game=game)
        
        context['match_participations'] = participations.order_by('-match__match_date')[:20]
        
        # Calculate overall statistics
        total_matches = participations.count()
        total_mvp = participations.filter(was_mvp=True).count()
        
        context['overall_stats'] = {
            'total_matches': total_matches,
            'total_mvp': total_mvp,
            'mvp_rate': (total_mvp / total_matches * 100) if total_matches > 0 else 0,
            'teams_count': queryset.values('team').distinct().count(),
        }
        
        context['selected_game'] = game
        context['available_games'] = queryset.values_list('game', flat=True).distinct()
        
        return context


class LeaderboardView(TemplateView):
    """
    Global leaderboard view showing top teams and players.
    """
    template_name = 'teams/leaderboard.html'
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        game = self.request.GET.get('game', 'valorant')
        leaderboard_type = self.request.GET.get('type', 'teams')
        limit = int(self.request.GET.get('limit', 50))
        
        if leaderboard_type == 'teams':
            context['leaderboard'] = AnalyticsCalculator.get_team_leaderboard(game, limit)
            context['leaderboard_type'] = 'teams'
        else:
            context['leaderboard'] = AnalyticsCalculator.get_player_leaderboard(game, limit)
            context['leaderboard_type'] = 'players'
        
        context['selected_game'] = game
        context['available_games'] = self._get_available_games()
        
        return context
    
    def _get_available_games(self) -> list:
        """Get list of games with analytics data"""
        return TeamAnalytics.objects.values_list(
            'game', flat=True
        ).distinct().order_by('game')


class ExportLeaderboardView(TemplateView):
    """
    Export leaderboard to CSV.
    """
    
    def get(self, request, *args, **kwargs):
        game = request.GET.get('game', 'valorant')
        leaderboard_type = request.GET.get('type', 'team')
        limit = int(request.GET.get('limit', 50))
        
        return CSVExportService.export_leaderboard(
            game,
            leaderboard_type,
            limit
        )


class TeamComparisonView(LoginRequiredMixin, TemplateView):
    """
    Compare two teams side-by-side.
    """
    template_name = 'teams/team_comparison.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        team1_id = self.request.GET.get('team1')
        team2_id = self.request.GET.get('team2')
        game = self.request.GET.get('game')
        
        if not all([team1_id, team2_id, game]):
            context['error'] = 'Please select two teams and a game to compare'
            return context
        
        try:
            team1 = Team.objects.get(id=team1_id)
            team2 = Team.objects.get(id=team2_id)
        except Team.DoesNotExist:
            context['error'] = 'One or both teams not found'
            return context
        
        # Get comparative stats
        comparison = AnalyticsAggregator.get_comparative_stats(
            int(team1_id), game, int(team2_id)
        )
        
        if 'error' in comparison:
            context['error'] = comparison['error']
            return context
        
        context['team1'] = team1
        context['team2'] = team2
        context['comparison'] = comparison
        context['selected_game'] = game
        
        # Get recent head-to-head matches if any
        h2h_matches = MatchRecord.objects.filter(
            Q(team=team1, opponent_team=team2) | Q(team=team2, opponent_team=team1),
            game=game
        ).order_by('-match_date')[:5]
        
        context['head_to_head'] = h2h_matches
        
        return context


class MatchDetailView(LoginRequiredMixin, DetailView):
    """
    Detailed view of a single match with all statistics.
    """
    model = MatchRecord
    template_name = 'teams/match_detail.html'
    context_object_name = 'match'
    pk_url_kwarg = 'match_id'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        match = self.object
        
        # Get all participants with their performance
        from apps.teams.models import MatchParticipation
        participants = MatchParticipation.objects.filter(
            match=match
        ).select_related('player__user').order_by('-performance_score')
        
        context['participants'] = participants
        
        # Calculate team averages
        if participants.exists():
            from django.db.models import Avg
            avg_performance = participants.aggregate(
                Avg('performance_score')
            )['performance_score__avg']
            context['avg_performance'] = avg_performance
        
        # MVP
        mvp = participants.filter(was_mvp=True).first()
        context['mvp'] = mvp
        
        return context


class AnalyticsAPIEndpoint(TemplateView):
    """
    Generic analytics API endpoint for custom queries.
    Used for building custom dashboards and integrations.
    """
    
    def get(self, request, *args, **kwargs):
        """
        Query parameters:
        - action: 'team_stats', 'player_stats', 'match_history', 'leaderboard'
        - team_id: Team ID (for team-specific queries)
        - player_id: Player ID (for player-specific queries)
        - game: Game filter
        - limit: Result limit
        - period: Time period (week/month/year)
        """
        
        action = request.GET.get('action')
        
        if not action:
            return JsonResponse({'error': 'Action parameter required'}, status=400)
        
        try:
            if action == 'team_stats':
                team_id = int(request.GET['team_id'])
                game = request.GET['game']
                data = AnalyticsCalculator.calculate_team_performance_summary(team_id, game)
            
            elif action == 'player_stats':
                game = request.GET['game']
                limit = int(request.GET.get('limit', 10))
                team_id = request.GET.get('team_id')
                team_id = int(team_id) if team_id else None
                data = AnalyticsCalculator.get_player_leaderboard(game, limit, team_id)
            
            elif action == 'match_history':
                team_id = int(request.GET['team_id'])
                game = request.GET.get('game')
                limit = int(request.GET.get('limit', 20))
                data = AnalyticsCalculator.get_match_history(team_id, game, limit)
            
            elif action == 'leaderboard':
                game = request.GET['game']
                board_type = request.GET.get('type', 'team')
                limit = int(request.GET.get('limit', 10))
                
                if board_type == 'team':
                    data = AnalyticsCalculator.get_team_leaderboard(game, limit)
                else:
                    data = AnalyticsCalculator.get_player_leaderboard(game, limit)
            
            elif action == 'period_stats':
                team_id = int(request.GET['team_id'])
                game = request.GET['game']
                period = request.GET.get('period', 'month')
                data = AnalyticsAggregator.aggregate_team_stats_by_period(
                    team_id, game, period
                )
            
            elif action == 'compare':
                team1_id = int(request.GET['team1_id'])
                team2_id = int(request.GET['team2_id'])
                game = request.GET['game']
                data = AnalyticsAggregator.get_comparative_stats(team1_id, game, team2_id)
            
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
            
            return JsonResponse(data, safe=False)
        
        except KeyError as e:
            return JsonResponse({'error': f'Missing parameter: {str(e)}'}, status=400)
        except ValueError as e:
            return JsonResponse({'error': f'Invalid parameter value: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
