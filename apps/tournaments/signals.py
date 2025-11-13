"""
Milestone F: Tournament Notification Signals

Django signals for tournament-related events that trigger notifications.

Events Covered:
1. Payment Verified - When staff verifies a payment
2. Payment Rejected - When staff rejects a payment  
3. Payment Refunded - When payment is refunded
4. Match Started - When match transitions to LIVE
5. Match Completed - When match finishes
6. Match Disputed - When match has a dispute
7. Tournament Completed - When tournament finishes

Signal Handlers:
- handle_payment_status_change() - Detects payment status transitions
- handle_match_state_change() - Detects match state transitions  
- handle_tournament_completed() - Detects tournament completion

Feature Flags (settings.py):
- NOTIFICATIONS_EMAIL_ENABLED (default: False)
- NOTIFICATIONS_WEBHOOK_ENABLED (default: False)

Planning Documents:
- Documents/ExecutionPlan/MILESTONES_E_F_PLAN.md
- Documents/ExecutionPlan/MILESTONES_E_F_STATUS.md
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings

from apps.tournaments.models import PaymentVerification, Match, Tournament
from apps.notifications.services import notify

logger = logging.getLogger(__name__)


# Feature flags (with safe defaults)
EMAIL_ENABLED = getattr(settings, 'NOTIFICATIONS_EMAIL_ENABLED', False)
WEBHOOK_ENABLED = getattr(settings, 'NOTIFICATIONS_WEBHOOK_ENABLED', False)


# ===========================
# Payment Notification Signals
# ===========================

@receiver(post_save, sender=PaymentVerification)
def handle_payment_status_change(sender, instance, created, **kwargs):
    """
    Notify registrant when payment status changes.
    
    Events:
    - payment_verified: Status changes to VERIFIED
    - payment_rejected: Status changes to REJECTED
    - payment_refunded: Status changes to REFUNDED
    
    Recipients: Registration owner (user)
    
    Feature Flags:
    - NOTIFICATIONS_EMAIL_ENABLED: Send email notifications
    - NOTIFICATIONS_WEBHOOK_ENABLED: Send webhook notifications
    """
    # Skip notifications if created (initial submission)
    if created:
        return
    
    # Skip if no status change
    if not hasattr(instance, '_original_status'):
        return
    
    old_status = instance._original_status
    new_status = instance.status
    
    # Skip if status didn't actually change
    if old_status == new_status:
        return
    
    registration = instance.registration
    user = registration.user
    tournament = registration.tournament
    
    # Determine event type and notification content
    event = None
    title = None
    body = None
    email_template = None
    
    if new_status == PaymentVerification.Status.VERIFIED:
        event = 'payment_verified'
        title = f'Payment Verified - {tournament.name}'
        body = f'Your payment for {tournament.name} has been verified. Your registration is now confirmed!'
        email_template = 'payment_verified'
        
        logger.info(
            f"Payment verified: payment_id={instance.id}, registration_id={registration.id}, "
            f"user_id={user.id if user else None}, tournament_id={tournament.id}"
        )
    
    elif new_status == PaymentVerification.Status.REJECTED:
        event = 'payment_rejected'
        rejection_reason = instance.notes.get('rejection_reason', 'Invalid payment details')
        title = f'Payment Rejected - {tournament.name}'
        body = f'Your payment for {tournament.name} has been rejected. Reason: {rejection_reason}. Please resubmit with correct details.'
        email_template = 'payment_rejected'
        
        logger.info(
            f"Payment rejected: payment_id={instance.id}, registration_id={registration.id}, "
            f"user_id={user.id if user else None}, reason='{rejection_reason}'"
        )
    
    elif new_status == PaymentVerification.Status.REFUNDED:
        event = 'payment_refunded'
        refund_reason = instance.notes.get('refund_reason', 'Tournament cancelled or registration cancelled')
        title = f'Payment Refunded - {tournament.name}'
        body = f'Your payment for {tournament.name} has been refunded. Reason: {refund_reason}'
        email_template = 'payment_refunded'
        
        logger.info(
            f"Payment refunded: payment_id={instance.id}, registration_id={registration.id}, "
            f"user_id={user.id if user else None}, reason='{refund_reason}'"
        )
    
    # Send notification if event was triggered
    if event and user:
        notify_kwargs = {
            'recipients': [user],
            'event': event,
            'title': title,
            'body': body,
            'tournament_id': tournament.id,
            'url': f'/tournaments/{tournament.slug}/',
        }
        
        # Add email parameters if enabled
        if EMAIL_ENABLED and email_template:
            notify_kwargs['email_subject'] = title
            notify_kwargs['email_template'] = email_template
            notify_kwargs['email_ctx'] = {
                'user': user,
                'tournament': tournament,
                'registration': registration,
                'payment': instance,
            }
        
        result = notify(**notify_kwargs)
        
        logger.debug(
            f"Payment notification sent: event={event}, created={result.get('created', 0)}, "
            f"email_sent={result.get('email_sent', 0)}"
        )


@receiver(pre_save, sender=PaymentVerification)
def track_payment_status_change(sender, instance, **kwargs):
    """
    Track original status before save for comparison in post_save.
    
    Stores instance._original_status for use in handle_payment_status_change().
    """
    if instance.pk:
        try:
            old_instance = PaymentVerification.objects.get(pk=instance.pk)
            instance._original_status = old_instance.status
        except PaymentVerification.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


# ===========================
# Match Notification Signals
# ===========================

@receiver(post_save, sender=Match)
def handle_match_state_change(sender, instance, created, **kwargs):
    """
    Notify participants when match state changes.
    
    Events:
    - match_started: State changes to LIVE
    - match_completed: State changes to COMPLETED
    - match_disputed: State changes to DISPUTED
    
    Recipients: Both match participants
    
    Feature Flags:
    - NOTIFICATIONS_EMAIL_ENABLED: Send email notifications
    - NOTIFICATIONS_WEBHOOK_ENABLED: Send webhook notifications
    """
    # Skip notifications if created (initial creation)
    if created:
        return
    
    # Skip if no state change
    if not hasattr(instance, '_original_state'):
        return
    
    old_state = instance._original_state
    new_state = instance.state
    
    # Skip if state didn't actually change
    if old_state == new_state:
        return
    
    tournament = instance.tournament
    
    # Get participants (may be users or teams)
    # For now, we'll need to resolve participants based on participant IDs
    # This is a simplified version - full implementation would need to resolve teams
    recipients = []
    
    # Determine event type and notification content
    event = None
    title = None
    body = None
    email_template = None
    
    if new_state == Match.LIVE:
        event = 'match_started'
        title = f'Match Started - {tournament.name}'
        body = f'Your match in {tournament.name} has started! Join the lobby now.'
        email_template = 'match_started'
        
        logger.info(
            f"Match started: match_id={instance.id}, tournament_id={tournament.id}, "
            f"round={instance.round_number}, match_num={instance.match_number}"
        )
    
    elif new_state == Match.COMPLETED:
        event = 'match_completed'
        winner_identifier = f"Participant {instance.winner_id}"
        title = f'Match Completed - {tournament.name}'
        body = f'Your match in {tournament.name} has been completed. Winner: {winner_identifier}'
        email_template = 'match_completed'
        
        logger.info(
            f"Match completed: match_id={instance.id}, tournament_id={tournament.id}, "
            f"winner_id={instance.winner_id}, score={instance.participant1_score}-{instance.participant2_score}"
        )
    
    elif new_state == Match.DISPUTED:
        event = 'match_disputed'
        title = f'Match Disputed - {tournament.name}'
        body = f'A dispute has been raised for your match in {tournament.name}. An organizer will review it soon.'
        email_template = 'match_disputed'
        
        logger.info(
            f"Match disputed: match_id={instance.id}, tournament_id={tournament.id}, "
            f"disputes_count={instance.disputes.count()}"
        )
    
    # Send notification if event was triggered
    # Note: Recipients list is empty in this simplified version
    # Full implementation would resolve participant users from teams
    if event:
        logger.debug(
            f"Match state change detected: event={event}, match_id={instance.id}, "
            f"old_state={old_state}, new_state={new_state}"
        )
        
        # TODO: Resolve actual user recipients from participant IDs
        # For now, just log the event
        # In full implementation:
        # if recipients:
        #     notify(
        #         recipients=recipients,
        #         event=event,
        #         title=title,
        #         body=body,
        #         tournament=tournament,
        #         match=instance,
        #         url=f'/tournaments/{tournament.slug}/matches/{instance.id}/',
        #         email_subject=title if EMAIL_ENABLED else None,
        #         email_template=email_template if EMAIL_ENABLED else None,
        #         email_ctx={'match': instance, 'tournament': tournament} if EMAIL_ENABLED else None
        #     )


@receiver(pre_save, sender=Match)
def track_match_state_change(sender, instance, **kwargs):
    """
    Track original state before save for comparison in post_save.
    
    Stores instance._original_state for use in handle_match_state_change().
    """
    if instance.pk:
        try:
            old_instance = Match.objects.get(pk=instance.pk)
            instance._original_state = old_instance.state
        except Match.DoesNotExist:
            instance._original_state = None
    else:
        instance._original_state = None


# ===========================
# Tournament Notification Signals
# ===========================

@receiver(post_save, sender=Tournament)
def handle_tournament_completed(sender, instance, created, **kwargs):
    """
    Notify all participants when tournament is completed.
    
    Events:
    - tournament_completed: Status changes to COMPLETED
    
    Recipients: All confirmed registrations
    
    Feature Flags:
    - NOTIFICATIONS_EMAIL_ENABLED: Send email notifications
    - NOTIFICATIONS_WEBHOOK_ENABLED: Send webhook notifications
    """
    # Skip notifications if created (initial creation)
    if created:
        return
    
    # Skip if no status change
    if not hasattr(instance, '_original_status'):
        return
    
    old_status = instance._original_status
    new_status = instance.status
    
    # Skip if status didn't actually change
    if old_status == new_status:
        return
    
    # Only notify on COMPLETED transition
    if new_status != Tournament.COMPLETED:
        return
    
    logger.info(
        f"Tournament completed: tournament_id={instance.id}, name='{instance.name}', "
        f"participants={instance.registrations.filter(status='confirmed').count()}"
    )
    
    # Get all confirmed participants
    confirmed_registrations = instance.registrations.filter(
        status='confirmed',
        is_deleted=False
    ).select_related('user')
    
    recipients = [reg.user for reg in confirmed_registrations if reg.user]
    
    if not recipients:
        logger.debug(f"No recipients for tournament_completed event: tournament_id={instance.id}")
        return
    
    # Notification content
    event = 'tournament_completed'
    title = f'Tournament Completed - {instance.name}'
    body = f'{instance.name} has been completed! Check the final results and standings.'
    email_template = 'tournament_completed'
    
    notify_kwargs = {
        'recipients': recipients,
        'event': event,
        'title': title,
        'body': body,
        'tournament_id': instance.id,
        'url': f'/tournaments/{instance.slug}/results/',
    }
    
    # Add email parameters if enabled
    if EMAIL_ENABLED:
        notify_kwargs['email_subject'] = title
        notify_kwargs['email_template'] = email_template
        notify_kwargs['email_ctx'] = {
            'tournament': instance,
        }
    
    result = notify(**notify_kwargs)
    
    logger.info(
        f"Tournament completion notifications sent: tournament_id={instance.id}, "
        f"created={result.get('created', 0)}, email_sent={result.get('email_sent', 0)}"
    )


@receiver(pre_save, sender=Tournament)
def track_tournament_status_change(sender, instance, **kwargs):
    """
    Track original status before save for comparison in post_save.
    
    Stores instance._original_status for use in handle_tournament_completed().
    """
    if instance.pk:
        try:
            old_instance = Tournament.objects.get(pk=instance.pk)
            instance._original_status = old_instance.status
        except Tournament.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None
