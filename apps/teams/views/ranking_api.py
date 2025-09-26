# apps/teams/views/ranking_api.py
"""
API views for Team Ranking System frontend integration
"""
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
import json

from ..models import Team, TeamRankingBreakdown, TeamRankingHistory
from ..services.ranking_service import ranking_service


class TeamRankingAPIView(View):
    """API view for team ranking data."""
    
    def get(self, request, team_id=None):
        """Get team ranking data or rankings list."""
        if team_id:
            return self.get_team_ranking(request, team_id)
        else:
            return self.get_rankings_list(request)
    
    def get_team_ranking(self, request, team_id):
        """Get detailed ranking data for a specific team."""
        try:
            team = get_object_or_404(Team, id=team_id)
            
            # Get or create breakdown
            breakdown, created = TeamRankingBreakdown.objects.get_or_create(
                team=team,
                defaults={'final_total': 0}
            )
            
            if created:
                # First time - calculate points
                ranking_service.recalculate_team_points(team)
                breakdown.refresh_from_db()
            
            # Get recent history
            history = TeamRankingHistory.objects.filter(
                team=team
            ).order_by('-created_at')[:10]
            
            return JsonResponse({
                'success': True,
                'team': {
                    'id': team.id,
                    'name': team.name,
                    'tag': team.tag,
                    'game': team.game,
                    'created_at': team.created_at.isoformat()
                },
                'ranking': breakdown.to_frontend_dict(),
                'history': [
                    {
                        'date': record.created_at.isoformat(),
                        'source': record.source,
                        'points_change': record.points_change,
                        'points_after': record.points_after,
                        'reason': record.reason,
                        'admin_user': record.admin_user.username if record.admin_user else 'System'
                    }
                    for record in history
                ]
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def get_rankings_list(self, request):
        """Get paginated rankings list."""
        try:
            # Get query parameters
            game = request.GET.get('game')
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)  # Max 100 per page
            
            # Get rankings from service
            rankings = ranking_service.get_team_rankings(
                game=game,
                limit=None  # We'll paginate manually
            )
            
            # Paginate
            paginator = Paginator(rankings, page_size)
            page_obj = paginator.get_page(page)
            
            return JsonResponse({
                'success': True,
                'rankings': [
                    {
                        'rank': item['rank'],
                        'team': {
                            'id': item['team'].id,
                            'name': item['team'].name,
                            'tag': item['team'].tag,
                            'game': item['team'].game
                        },
                        'points': item['points'],
                        'breakdown': item.get('breakdown', {})
                    }
                    for item in page_obj
                ],
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                },
                'filters': {
                    'game': game
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(staff_member_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class TeamRankingManagementAPIView(View):
    """API view for admin ranking management."""
    
    def post(self, request, team_id, action):
        """Handle ranking management actions."""
        try:
            team = get_object_or_404(Team, id=team_id)
            
            if action == 'adjust':
                return self.adjust_points(request, team)
            elif action == 'recalculate':
                return self.recalculate_points(request, team)
            elif action == 'award_tournament':
                return self.award_tournament_points(request, team)
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Unknown action: {action}'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def adjust_points(self, request, team):
        """Adjust team points manually."""
        try:
            data = json.loads(request.body)
            points_adjustment = int(data.get('points_adjustment', 0))
            reason = data.get('reason', 'API adjustment')
            
            if points_adjustment == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Points adjustment cannot be zero'
                }, status=400)
            
            result = ranking_service.adjust_team_points(
                team=team,
                points_adjustment=points_adjustment,
                reason=reason,
                admin_user=request.user
            )
            
            if result['success']:
                team.refresh_from_db()
                breakdown = TeamRankingBreakdown.objects.get(team=team)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Points adjusted by {points_adjustment:+d}',
                    'new_total': team.total_points,
                    'points_change': result['points_change'],
                    'breakdown': breakdown.to_frontend_dict()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def recalculate_points(self, request, team):
        """Recalculate team points."""
        try:
            result = ranking_service.recalculate_team_points(
                team=team,
                admin_user=request.user,
                reason="API recalculation"
            )
            
            if result['success']:
                team.refresh_from_db()
                breakdown = TeamRankingBreakdown.objects.get(team=team)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Points recalculated. Change: {result["points_change"]:+d}',
                    'new_total': team.total_points,
                    'points_change': result['points_change'],
                    'breakdown': breakdown.to_frontend_dict()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def award_tournament_points(self, request, team):
        """Award tournament points to team."""
        try:
            data = json.loads(request.body)
            achievement_type = data.get('achievement_type')  # 'participation', 'winner', etc.
            tournament_name = data.get('tournament_name', 'Unknown Tournament')
            
            if not achievement_type:
                return JsonResponse({
                    'success': False,
                    'error': 'Achievement type is required'
                }, status=400)
            
            # Create mock tournament object (in real app, get from Tournament model)
            class MockTournament:
                def __init__(self, name):
                    self.id = hash(name) % 10000  # Simple hash for ID
                    self.name = name
            
            tournament = MockTournament(tournament_name)
            
            result = ranking_service.award_tournament_points(
                team=team,
                tournament=tournament,
                achievement_type=achievement_type,
                admin_user=request.user
            )
            
            if result['success']:
                team.refresh_from_db()
                breakdown = TeamRankingBreakdown.objects.get(team=team)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Tournament points awarded: +{result["points_awarded"]}',
                    'points_awarded': result['points_awarded'],
                    'new_total': team.total_points,
                    'breakdown': breakdown.to_frontend_dict()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class TeamRankingStatsAPIView(View):
    """API view for ranking statistics and analytics."""
    
    def get(self, request):
        """Get ranking system statistics."""
        try:
            # Get overall stats
            total_teams = Team.objects.count()
            teams_with_points = Team.objects.filter(total_points__gt=0).count()
            
            # Get top teams by game
            games = Team.objects.values_list('game', flat=True).distinct()
            top_teams_by_game = {}
            
            for game in games:
                top_teams = ranking_service.get_team_rankings(game=game, limit=5)
                top_teams_by_game[game] = [
                    {
                        'name': item['team'].name,
                        'tag': item['team'].tag,
                        'points': item['points']
                    }
                    for item in top_teams
                ]
            
            # Get recent activity
            recent_changes = TeamRankingHistory.objects.select_related('team').order_by('-created_at')[:10]
            
            return JsonResponse({
                'success': True,
                'stats': {
                    'total_teams': total_teams,
                    'teams_with_points': teams_with_points,
                    'games': list(games),
                    'top_teams_by_game': top_teams_by_game
                },
                'recent_activity': [
                    {
                        'team_name': change.team.name,
                        'team_tag': change.team.tag,
                        'points_change': change.points_change,
                        'source': change.source,
                        'date': change.created_at.isoformat(),
                        'reason': change.reason
                    }
                    for change in recent_changes
                ]
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)