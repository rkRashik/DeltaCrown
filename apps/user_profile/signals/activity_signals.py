"""
Activity Event Signal Handlers

Automatically creates UserActivity events when:
- Tournament registration confirmed
- Match completed
- Economy transaction created

Design:
- Idempotent (safe to fire multiple times)
- Async-safe (can be called from Celery tasks)
- Non-blocking (failures logged, don't crash main flow)

Integration:
    # Auto-loaded by apps.py ready() method
    from apps.user_profile.signals.activity_signals import *
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='tournaments.Registration')
def on_tournament_registration(sender, instance, created, **kwargs):
    """
    Create TOURNAMENT_JOINED event when registration confirmed.
    
    Triggers when:
    - Registration status changes to CONFIRMED
    - New registration created with CONFIRMED status
    """
    from apps.user_profile.services.activity_service import UserActivityService
    
    # Only record if status is CONFIRMED
    if instance.status != 'confirmed':
        return
    
    try:
        # Record tournament join event (idempotent)
        event = UserActivityService.record_tournament_join(
            user_id=instance.user_id,
            tournament_id=instance.tournament_id,
            registration_id=instance.id,
            timestamp=instance.created_at or timezone.now()
        )
        
        if event:
            logger.info(
                f"Recorded TOURNAMENT_JOINED: user={instance.user_id}, "
                f"tournament={instance.tournament_id}"
            )
    except Exception as e:
        logger.error(
            f"Failed to record tournament join for registration {instance.id}: {e}",
            exc_info=True
        )
        # Don't raise - event recording is non-critical


@receiver(post_save, sender='tournaments.Match')
def on_match_completed(sender, instance, created, **kwargs):
    """
    Create MATCH_PLAYED, MATCH_WON, MATCH_LOST events when match completes.
    
    Triggers when:
    - Match state changes to COMPLETED
    - Match has winner_id and loser_id set
    """
    from apps.user_profile.services.activity_service import UserActivityService
    
    # Only record if match is completed
    if instance.state != 'completed':
        return
    
    # Must have winner and loser
    if not instance.winner_id or not instance.loser_id:
        logger.warning(
            f"Match {instance.id} is COMPLETED but missing winner/loser IDs"
        )
        return
    
    try:
        # Extract scores if available
        winner_score = None
        loser_score = None
        
        if hasattr(instance, 'scores') and instance.scores:
            # Scores format: {'participant1': X, 'participant2': Y}
            # Determine which participant is winner
            if instance.participant1_id == instance.winner_id:
                winner_score = instance.scores.get('participant1')
                loser_score = instance.scores.get('participant2')
            elif instance.participant2_id == instance.winner_id:
                winner_score = instance.scores.get('participant2')
                loser_score = instance.scores.get('participant1')
        
        # Record match result events (idempotent)
        winner_event, loser_event = UserActivityService.record_match_result(
            match_id=instance.id,
            winner_id=instance.winner_id,
            loser_id=instance.loser_id,
            winner_score=winner_score,
            loser_score=loser_score,
            timestamp=instance.completed_at or timezone.now()
        )
        
        if winner_event or loser_event:
            logger.info(
                f"Recorded match result: match={instance.id}, "
                f"winner={instance.winner_id}, loser={instance.loser_id}"
            )
    except Exception as e:
        logger.error(
            f"Failed to record match result for match {instance.id}: {e}",
            exc_info=True
        )
        # Don't raise - event recording is non-critical


@receiver(post_save, sender='economy.DeltaCrownTransaction')
def on_economy_transaction(sender, instance, created, **kwargs):
    """
    Create COINS_EARNED or COINS_SPENT event when transaction created.
    Also sync wallet balance to profile.
    
    Triggers when:
    - New transaction created
    - Transaction must have wallet.user_id
    """
    from apps.user_profile.services.activity_service import UserActivityService
    from apps.user_profile.services.economy_sync import sync_wallet_to_profile
    
    # Only record new transactions
    if not created:
        return
    
    try:
        # Get user_id from wallet.profile.user
        if not hasattr(instance.wallet, 'profile') or not instance.wallet.profile:
            logger.warning(
                f"Transaction {instance.id} wallet has no profile (wallet {instance.wallet_id})"
            )
            return
        
        user_id = instance.wallet.profile.user_id
        
        if not user_id:
            logger.warning(
                f"Transaction {instance.id} profile has no user_id"
            )
            return
        
        # Record economy transaction event (idempotent)
        event = UserActivityService.record_economy_transaction(
            transaction_id=instance.id,
            user_id=user_id,
            amount=float(instance.amount),
            reason=instance.reason,
            timestamp=instance.created_at or timezone.now()
        )
        
        if event:
            event_type = 'EARNED' if instance.amount > 0 else 'SPENT'
            logger.info(
                f"Recorded COINS_{event_type}: user={user_id}, "
                f"amount={abs(instance.amount)}, reason={instance.reason}"
            )
        
        # Sync wallet balance to profile (UP-M3)
        # Ensure wallet.cached_balance is current (recalc happens in transaction.save() but might not be flushed)
        instance.wallet.recalc_and_save()
        sync_wallet_to_profile(instance.wallet_id)
        logger.debug(f"Synced wallet {instance.wallet_id} to profile after transaction {instance.id}")
    except Exception as e:
        logger.error(
            f"Failed to record economy transaction for txn {instance.id}: {e}",
            exc_info=True
        )
        # Don't raise - event recording is non-critical


# Optional: Tournament completion signal (for placement events)
# This would require tournament result tracking - implement when TournamentResult model exists
# @receiver(tournament_completed_signal)
# def on_tournament_completed(sender, tournament, **kwargs):
#     """Create TOURNAMENT_PLACED events for all participants."""
#     pass
