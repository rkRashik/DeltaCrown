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
    import hashlib
    import json
    from decimal import Decimal
    
    def generate_dedup_key(task_name: str, **kwargs) -> str:
        """
        Generate a unique deduplication key for idempotent task execution.
        
        Args:
            task_name: Name of the task
            **kwargs: Task parameters to include in the key
            
        Returns:
            SHA256 hash of the task signature
        """
        # Sort kwargs for consistent hashing
        sorted_kwargs = json.dumps(kwargs, sort_keys=True)
        signature = f"{task_name}:{sorted_kwargs}"
        return hashlib.sha256(signature.encode()).hexdigest()
    
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
    
    @shared_task(bind=True, name='teams.recompute_team_rankings', max_retries=3, default_retry_delay=300)
    def recompute_team_rankings(self, tournament_id=None):
        """
        Recompute team rankings based on tournament results.
        
        Args:
            tournament_id: Optional tournament ID to recompute rankings for.
                          If None, recomputes all rankings.
        
        This task is idempotent and can be run multiple times safely.
        """
        from django.apps import apps
        from django.db import transaction
        
        # Get models via apps registry
        Tournament = apps.get_model('tournaments', 'Tournament')
        Registration = apps.get_model('tournaments', 'Registration')
        
        try:
            logger.info(f"Starting ranking recalculation for tournament_id={tournament_id}")
            
            # Generate deduplication key
            dedup_key = generate_dedup_key('recompute_rankings', tournament_id=tournament_id)
            
            with transaction.atomic():
                if tournament_id:
                    # Recompute for specific tournament
                    tournament = Tournament.objects.select_for_update().get(id=tournament_id)
                    
                    # Only recompute if tournament is finalized
                    if tournament.status != 'completed':
                        logger.warning(f"Tournament {tournament_id} is not completed. Skipping ranking update.")
                        return {'status': 'skipped', 'reason': 'tournament_not_completed'}
                    
                    # Get all teams that participated
                    registrations = Registration.objects.filter(
                        tournament=tournament,
                        status='approved'
                    ).select_related('team')
                    
                    teams_to_update = [reg.team for reg in registrations]
                else:
                    # Recompute all team rankings
                    teams_to_update = Team.objects.all()
                
                updated_count = 0
                for team in teams_to_update:
                    # Calculate total wins, losses, and points from tournament participations
                    registrations = Registration.objects.filter(
                        team=team,
                        tournament__status='completed'
                    )
                    
                    total_points = sum(reg.points_earned or 0 for reg in registrations)
                    total_wins = sum(reg.wins or 0 for reg in registrations)
                    total_losses = sum(reg.losses or 0 for reg in registrations)
                    
                    # Update team ranking metrics
                    if team.total_points != total_points or team.wins != total_wins or team.losses != total_losses:
                        team.total_points = total_points
                        team.wins = total_wins
                        team.losses = total_losses
                        team.save(update_fields=['total_points', 'wins', 'losses'])
                        updated_count += 1
                        
                        logger.info(f"Updated ranking for team {team.id}: {total_points} points, {total_wins}W-{total_losses}L")
                
                logger.info(f"Ranking recalculation completed. Updated {updated_count} teams. Dedup key: {dedup_key}")
                
                return {
                    'status': 'success',
                    'updated_count': updated_count,
                    'dedup_key': dedup_key
                }
                
        except Tournament.DoesNotExist:
            logger.error(f"Tournament {tournament_id} not found")
            return {'status': 'error', 'message': 'Tournament not found'}
        except Exception as exc:
            logger.error(f"Error in ranking recalculation: {str(exc)}", exc_info=True)
            # Retry on failure
            raise self.retry(exc=exc)
    
    @shared_task(bind=True, name='teams.distribute_tournament_payouts', max_retries=3, default_retry_delay=300)
    def distribute_tournament_payouts(self, tournament_id):
        """
        Distribute coins and payouts after tournament completion.
        
        This task is idempotent - uses transaction flags to prevent double payouts.
        
        Args:
            tournament_id: ID of the completed tournament
        """
        from django.apps import apps
        Tournament = apps.get_model('tournaments', 'Tournament')
        Registration = apps.get_model('tournaments', 'Registration')
        from apps.economy.models import CoinTransaction
        from apps.teams.models import TeamAchievement
        from django.db import transaction
        
        try:
            logger.info(f"Starting payout distribution for tournament {tournament_id}")
            
            # Generate deduplication key
            dedup_key = generate_dedup_key('distribute_payouts', tournament_id=tournament_id)
            
            with transaction.atomic():
                tournament = Tournament.objects.select_for_update().get(id=tournament_id)
                
                # Check if tournament is eligible for payouts
                if tournament.status != 'completed':
                    logger.warning(f"Tournament {tournament_id} is not completed. Skipping payouts.")
                    return {'status': 'skipped', 'reason': 'tournament_not_completed'}
                
                # Check if payouts already distributed (idempotency check)
                existing_transactions = CoinTransaction.objects.filter(
                    transaction_type='tournament_payout',
                    metadata__contains={'tournament_id': tournament_id}
                ).exists()
                
                if existing_transactions:
                    logger.info(f"Payouts already distributed for tournament {tournament_id}. Skipping.")
                    return {'status': 'skipped', 'reason': 'already_distributed', 'dedup_key': dedup_key}
                
                # Get winning teams (top 3)
                top_teams = Registration.objects.filter(
                    tournament=tournament,
                    status='approved'
                ).order_by('-points_earned', '-wins', 'losses')[:3]
                
                payout_distribution = [
                    {'place': 1, 'coins': 1000, 'achievement': 'tournament_champion'},
                    {'place': 2, 'coins': 500, 'achievement': 'tournament_runner_up'},
                    {'place': 3, 'coins': 250, 'achievement': 'tournament_third_place'},
                ]
                
                distributed_payouts = []
                
                for idx, registration in enumerate(top_teams):
                    payout = payout_distribution[idx]
                    team = registration.team
                    
                    # Create coin transaction
                    transaction_obj = CoinTransaction.objects.create(
                        user=team.captain.user if team.captain else None,
                        team=team,
                        amount=payout['coins'],
                        transaction_type='tournament_payout',
                        description=f"Tournament {tournament.name} - Place {payout['place']}",
                        metadata={
                            'tournament_id': tournament_id,
                            'place': payout['place'],
                            'dedup_key': dedup_key,
                        }
                    )
                    
                    # Update team coins
                    team.coins = (team.coins or 0) + payout['coins']
                    team.save(update_fields=['coins'])
                    
                    # Create achievement record
                    achievement, created = TeamAchievement.objects.get_or_create(
                        team=team,
                        achievement_type=payout['achievement'],
                        tournament=tournament,
                        defaults={
                            'title': f"{tournament.name} - Place {payout['place']}",
                            'description': f"Achieved {payout['place']} place in {tournament.name}",
                            'earned_at': timezone.now(),
                        }
                    )
                    
                    distributed_payouts.append({
                        'team_id': team.id,
                        'team_name': team.name,
                        'place': payout['place'],
                        'coins': payout['coins'],
                        'transaction_id': transaction_obj.id,
                        'achievement_created': created,
                    })
                    
                    logger.info(f"Distributed {payout['coins']} coins to team {team.id} for place {payout['place']}")
                
                logger.info(f"Payout distribution completed for tournament {tournament_id}. Dedup key: {dedup_key}")
                
                return {
                    'status': 'success',
                    'tournament_id': tournament_id,
                    'payouts': distributed_payouts,
                    'dedup_key': dedup_key
                }
                
        except Tournament.DoesNotExist:
            logger.error(f"Tournament {tournament_id} not found")
            return {'status': 'error', 'message': 'Tournament not found'}
        except Exception as exc:
            logger.error(f"Error distributing payouts: {str(exc)}", exc_info=True)
            # Retry on failure
            raise self.retry(exc=exc)
    
    @shared_task(bind=True, name='teams.clean_expired_invites', max_retries=3, default_retry_delay=60)
    def clean_expired_invites(self):
        """
        Clean up expired team invites.
        Runs every 6 hours to remove stale invitations.
        """
        from apps.teams.models import TeamInvite
        from datetime import timedelta
        
        try:
            logger.info("Starting expired invites cleanup")
            
            # Delete invites older than 7 days that are still pending
            cutoff_date = timezone.now() - timedelta(days=7)
            
            expired_invites = TeamInvite.objects.filter(
                status='pending',
                created_at__lt=cutoff_date
            )
            
            count = expired_invites.count()
            expired_invites.update(status='expired')
            
            logger.info(f"Expired {count} team invites")
            
            return {
                'status': 'success',
                'expired_count': count
            }
            
        except Exception as exc:
            logger.error(f"Error cleaning expired invites: {str(exc)}", exc_info=True)
            raise self.retry(exc=exc)
    
    @shared_task(bind=True, name='teams.expire_sponsors_task', max_retries=3, default_retry_delay=60)
    def expire_sponsors_task(self):
        """
        Expire sponsors that have passed their end date.
        Runs daily at 3 AM.
        """
        from apps.teams.services import SponsorshipService
        
        try:
            logger.info("Starting sponsor expiration check")
            
            expired_count = SponsorshipService.expire_sponsors()
            
            logger.info(f"Expired {expired_count} sponsors")
            
            return {
                'status': 'success',
                'expired_count': expired_count
            }
            
        except Exception as exc:
            logger.error(f"Error expiring sponsors: {str(exc)}", exc_info=True)
            raise self.retry(exc=exc)
    
    @shared_task(bind=True, name='teams.process_scheduled_promotions_task', max_retries=3, default_retry_delay=60)
    def process_scheduled_promotions_task(self):
        """
        Process scheduled promotions (activate/expire).
        Runs hourly.
        """
        from apps.teams.services import PromotionService
        
        try:
            logger.info("Starting scheduled promotions processing")
            
            activated_count = PromotionService.activate_scheduled_promotions()
            expired_count = PromotionService.expire_promotions()
            
            logger.info(f"Activated {activated_count} promotions, expired {expired_count} promotions")
            
            return {
                'status': 'success',
                'activated_count': activated_count,
                'expired_count': expired_count
            }
            
        except Exception as exc:
            logger.error(f"Error processing scheduled promotions: {str(exc)}", exc_info=True)
            raise self.retry(exc=exc)
    
    @shared_task(bind=True, name='teams.send_roster_change_notification')
    def send_roster_change_notification(self, team_id, change_type, user_id):
        """
        Send notification when roster changes occur.
        
        Args:
            team_id: ID of the team
            change_type: Type of change (added, removed, role_changed)
            user_id: ID of the affected user
        """
        from apps.notifications.services import NotificationService
        from apps.accounts.models import User
        
        try:
            team = Team.objects.get(id=team_id)
            user = User.objects.get(id=user_id)
            
            # Send notification to all team members
            NotificationService.notify_roster_change(
                team=team,
                change_type=change_type,
                affected_user=user
            )
            
            logger.info(f"Sent roster change notification for team {team_id}, type: {change_type}")
            
            return {'status': 'success'}
            
        except Exception as exc:
            logger.error(f"Error sending roster change notification: {str(exc)}", exc_info=True)
            return {'status': 'error', 'message': str(exc)}
    
    @shared_task(bind=True, name='teams.send_invite_notification')
    def send_invite_notification(self, invite_id):
        """
        Send notification when team invite is sent.
        
        Args:
            invite_id: ID of the team invite
        """
        from apps.notifications.services import NotificationService
        from apps.teams.models import TeamInvite
        
        try:
            invite = TeamInvite.objects.select_related('team', 'inviter', 'invitee').get(id=invite_id)
            
            NotificationService.notify_invite_sent(invite)
            
            logger.info(f"Sent invite notification for invite {invite_id}")
            
            return {'status': 'success'}
            
        except Exception as exc:
            logger.error(f"Error sending invite notification: {str(exc)}", exc_info=True)
            return {'status': 'error', 'message': str(exc)}
    
    @shared_task(bind=True, name='teams.send_match_result_notification')
    def send_match_result_notification(self, match_id):
        """
        Send notification when match result is submitted.
        
        Args:
            match_id: ID of the match
        """
        from apps.notifications.services import NotificationService
        from django.apps import apps
        Match = apps.get_model('tournaments', 'Match')
        
        try:
            match = Match.objects.select_related('tournament', 'team1', 'team2').get(id=match_id)
            
            NotificationService.notify_match_result(match)
            
            logger.info(f"Sent match result notification for match {match_id}")
            
            return {'status': 'success'}
            
        except Exception as exc:
            logger.error(f"Error sending match result notification: {str(exc)}", exc_info=True)
            return {'status': 'error', 'message': str(exc)}

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