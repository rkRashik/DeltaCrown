"""
Celery tasks for tournament automation and workflows
"""
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='tournaments.check_tournament_wrapup', max_retries=3, default_retry_delay=300)
def check_tournament_wrapup(self):
    """
    Check for completed tournaments that need wrap-up processing.
    Runs hourly to trigger ranking updates and payouts for newly completed tournaments.
    """
    from apps.tournaments.models import Tournament
    from apps.teams.tasks import recompute_team_rankings, distribute_tournament_payouts
    
    try:
        logger.info("Checking for tournaments needing wrap-up")
        
        # Find tournaments that just completed (status = completed, but payouts not distributed)
        from apps.economy.models import CoinTransaction
        
        completed_tournaments = Tournament.objects.filter(
            status='completed'
        )
        
        processed_count = 0
        
        for tournament in completed_tournaments:
            # Check if payouts already distributed
            existing_payouts = CoinTransaction.objects.filter(
                transaction_type='tournament_payout',
                metadata__contains={'tournament_id': tournament.id}
            ).exists()
            
            if not existing_payouts:
                logger.info(f"Processing wrap-up for tournament {tournament.id}: {tournament.name}")
                
                # Trigger ranking recalculation
                recompute_team_rankings.delay(tournament_id=tournament.id)
                
                # Trigger payout distribution
                distribute_tournament_payouts.delay(tournament_id=tournament.id)
                
                processed_count += 1
        
        logger.info(f"Tournament wrap-up check completed. Processed {processed_count} tournaments.")
        
        return {
            'status': 'success',
            'tournaments_processed': processed_count
        }
        
    except Exception as exc:
        logger.error(f"Error in tournament wrap-up check: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, name='tournaments.send_tournament_registration_notification')
def send_tournament_registration_notification(self, tournament_id, team_id):
    """
    Send notification when team registers for tournament.
    
    Args:
        tournament_id: ID of the tournament
        team_id: ID of the registered team
    """
    from apps.notifications.services import NotificationService
    from apps.tournaments.models import Tournament
    from apps.teams.models import Team
    
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        team = Team.objects.get(id=team_id)
        
        NotificationService.notify_tournament_registration(tournament, team)
        
        logger.info(f"Sent tournament registration notification for tournament {tournament_id}, team {team_id}")
        
        return {'status': 'success'}
        
    except Exception as exc:
        logger.error(f"Error sending tournament registration notification: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}


@shared_task(bind=True, name='tournaments.send_bracket_ready_notification')
def send_bracket_ready_notification(self, tournament_id):
    """
    Send notification when tournament bracket is generated.
    
    Args:
        tournament_id: ID of the tournament
    """
    from apps.notifications.services import NotificationService
    from apps.tournaments.models import Tournament
    
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        
        NotificationService.notify_bracket_ready(tournament)
        
        logger.info(f"Sent bracket ready notification for tournament {tournament_id}")
        
        return {'status': 'success'}
        
    except Exception as exc:
        logger.error(f"Error sending bracket ready notification: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}


@shared_task(bind=True, name='tournaments.send_match_scheduled_notification')
def send_match_scheduled_notification(self, match_id):
    """
    Send notification when match is scheduled.
    
    Args:
        match_id: ID of the match
    """
    from apps.notifications.services import NotificationService
    from apps.tournaments.models import Match
    
    try:
        match = Match.objects.select_related('tournament', 'team1', 'team2').get(id=match_id)
        
        NotificationService.notify_match_scheduled(match)
        
        logger.info(f"Sent match scheduled notification for match {match_id}")
        
        return {'status': 'success'}
        
    except Exception as exc:
        logger.error(f"Error sending match scheduled notification: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}


@shared_task(bind=True, name='tournaments.finalize_tournament')
def finalize_tournament(self, tournament_id):
    """
    Finalize tournament and trigger all post-tournament tasks.
    
    Args:
        tournament_id: ID of the tournament to finalize
    """
    from apps.tournaments.models import Tournament
    from apps.teams.tasks import recompute_team_rankings, distribute_tournament_payouts
    
    try:
        logger.info(f"Finalizing tournament {tournament_id}")
        
        with transaction.atomic():
            tournament = Tournament.objects.select_for_update().get(id=tournament_id)
            
            # Verify tournament can be finalized
            if tournament.status == 'completed':
                logger.info(f"Tournament {tournament_id} already finalized")
                return {'status': 'skipped', 'reason': 'already_finalized'}
            
            if tournament.status != 'ongoing':
                logger.warning(f"Tournament {tournament_id} is not in ongoing status")
                return {'status': 'error', 'reason': 'invalid_status'}
            
            # Update tournament status
            tournament.status = 'completed'
            tournament.save(update_fields=['status'])
            
            logger.info(f"Tournament {tournament_id} status updated to completed")
        
        # Trigger async tasks for ranking and payouts
        recompute_team_rankings.delay(tournament_id=tournament_id)
        distribute_tournament_payouts.delay(tournament_id=tournament_id)
        
        logger.info(f"Tournament {tournament_id} finalization completed")
        
        return {
            'status': 'success',
            'tournament_id': tournament_id
        }
        
    except Tournament.DoesNotExist:
        logger.error(f"Tournament {tournament_id} not found")
        return {'status': 'error', 'message': 'Tournament not found'}
    except Exception as exc:
        logger.error(f"Error finalizing tournament: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}
