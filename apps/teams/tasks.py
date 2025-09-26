# apps/teams/tasks.py
"""
Background tasks for Team Ranking System
"""
from django.core.management import call_command
from django.utils import timezone
from django.db.models import F
from datetime import datetime, timedelta
import logging

from .models import Team, RankingCriteria, TeamRankingBreakdown
from .services.ranking_service import ranking_service

logger = logging.getLogger(__name__)


def update_monthly_team_age_points():
    """
    Monthly task to update team age points.
    This should be run as a cron job or scheduled task.
    """
    try:
        logger.info("Starting monthly team age points update...")
        
        # Get active criteria
        criteria = RankingCriteria.get_active_criteria()
        if not criteria:
            logger.error("No active ranking criteria found")
            return
        
        # Get all teams that need age point updates
        teams = Team.objects.all()
        updated_teams = 0
        
        for team in teams:
            try:
                # Recalculate team points (this includes age calculation)
                result = ranking_service.recalculate_team_points(
                    team=team,
                    reason="Monthly age points update"
                )
                
                if result['success'] and result['points_change'] > 0:
                    updated_teams += 1
                    logger.info(f"Updated {team.name}: +{result['points_change']} points")
                    
            except Exception as e:
                logger.error(f"Error updating team {team.name}: {e}")
                continue
        
        logger.info(f"Monthly age update completed. Updated {updated_teams} teams.")
        
        # Return summary for monitoring
        return {
            'success': True,
            'teams_processed': len(teams),
            'teams_updated': updated_teams,
            'timestamp': timezone.now()
        }
        
    except Exception as e:
        logger.error(f"Monthly age update failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now()
        }


def cleanup_old_ranking_history(days_to_keep=365):
    """
    Clean up old ranking history records.
    Keep only the last N days of history to prevent database bloat.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        from .models.ranking import TeamRankingHistory
        old_records = TeamRankingHistory.objects.filter(created_at__lt=cutoff_date)
        count = old_records.count()
        
        if count > 0:
            old_records.delete()
            logger.info(f"Cleaned up {count} old ranking history records")
        
        return {
            'success': True,
            'records_deleted': count,
            'cutoff_date': cutoff_date
        }
        
    except Exception as e:
        logger.error(f"History cleanup failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def recalculate_all_team_rankings():
    """
    Background task to recalculate all team rankings.
    Useful for maintenance or after criteria changes.
    """
    try:
        logger.info("Starting bulk team ranking recalculation...")
        
        result = ranking_service.recalculate_all_teams(
            reason="Bulk recalculation task"
        )
        
        if result['success']:
            logger.info(f"Bulk recalculation completed: {result['teams_processed']} teams processed, {result['teams_updated']} updated")
        else:
            logger.error(f"Bulk recalculation failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Bulk recalculation task failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def generate_ranking_report():
    """
    Generate a comprehensive ranking system report.
    Useful for monitoring and analytics.
    """
    try:
        from django.db.models import Sum, Count, Avg
        
        # Basic statistics
        total_teams = Team.objects.count()
        teams_with_points = Team.objects.filter(total_points__gt=0).count()
        total_points_awarded = Team.objects.aggregate(Sum('total_points'))['total_points__sum'] or 0
        avg_points_per_team = Team.objects.aggregate(Avg('total_points'))['total_points__avg'] or 0
        
        # Top teams overall
        top_teams = Team.objects.order_by('-total_points')[:10]
        
        # Points distribution by game
        games_stats = {}
        for game in Team.objects.values_list('game', flat=True).distinct():
            game_teams = Team.objects.filter(game=game)
            games_stats[game] = {
                'team_count': game_teams.count(),
                'total_points': game_teams.aggregate(Sum('total_points'))['total_points__sum'] or 0,
                'avg_points': game_teams.aggregate(Avg('total_points'))['total_points__avg'] or 0,
                'top_team': game_teams.order_by('-total_points').first()
            }
        
        # Recent activity
        from .models.ranking import TeamRankingHistory
        recent_changes = TeamRankingHistory.objects.select_related('team').order_by('-created_at')[:20]
        
        report = {
            'generated_at': timezone.now(),
            'overview': {
                'total_teams': total_teams,
                'teams_with_points': teams_with_points,
                'total_points_awarded': total_points_awarded,
                'avg_points_per_team': round(avg_points_per_team, 2)
            },
            'top_teams': [
                {
                    'name': team.name,
                    'tag': team.tag,
                    'points': team.total_points,
                    'game': team.game
                }
                for team in top_teams
            ],
            'games_stats': games_stats,
            'recent_activity': [
                {
                    'team': change.team.name,
                    'points_change': change.points_change,
                    'source': change.source,
                    'date': change.created_at,
                    'reason': change.reason
                }
                for change in recent_changes
            ]
        }
        
        logger.info("Ranking report generated successfully")
        return {
            'success': True,
            'report': report
        }
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Celery task decorators (if using Celery)
try:
    from celery import shared_task
    
    @shared_task(name='teams.update_monthly_age_points')
    def update_monthly_age_points_task():
        """Celery task for monthly age points update."""
        return update_monthly_team_age_points()
    
    @shared_task(name='teams.cleanup_ranking_history') 
    def cleanup_ranking_history_task(days_to_keep=365):
        """Celery task for history cleanup."""
        return cleanup_old_ranking_history(days_to_keep)
    
    @shared_task(name='teams.recalculate_all_rankings')
    def recalculate_all_rankings_task():
        """Celery task for bulk recalculation."""
        return recalculate_all_team_rankings()
    
    @shared_task(name='teams.generate_ranking_report')
    def generate_ranking_report_task():
        """Celery task for report generation."""
        return generate_ranking_report()

except ImportError:
    # Celery not available, tasks can still be run as regular functions
    logger.info("Celery not available, tasks will run as regular functions")


# Cron job commands (for traditional cron setup)
"""
Add these to your crontab for automated execution:

# Monthly team age points update (1st of every month at 2 AM)
0 2 1 * * cd /path/to/project && python manage.py shell -c "from apps.teams.tasks import update_monthly_team_age_points; update_monthly_team_age_points()"

# Weekly history cleanup (Sundays at 3 AM)  
0 3 * * 0 cd /path/to/project && python manage.py shell -c "from apps.teams.tasks import cleanup_old_ranking_history; cleanup_old_ranking_history()"

# Daily ranking report (Every day at 6 AM)
0 6 * * * cd /path/to/project && python manage.py shell -c "from apps.teams.tasks import generate_ranking_report; generate_ranking_report()"
"""