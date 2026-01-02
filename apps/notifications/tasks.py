"""
Celery tasks for notification delivery and management
"""
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import send_mail, send_mass_mail
from django.db.models import Q
import requests
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def _map_notification_type_to_category(notification_type):
    """
    Map notification type to category for enforcement.
    
    Args:
        notification_type: Notification.Type value
    
    Returns:
        str: Category name ('tournaments', 'teams', 'bounties', 'messages', 'system')
    """
    # Tournament-related
    if notification_type in ['reg_confirmed', 'bracket_ready', 'match_scheduled', 
                              'result_verified', 'checkin_open', 'tournament_registered', 
                              'match_result', 'ranking_changed']:
        return 'tournaments'
    
    # Team-related
    if notification_type in ['invite_sent', 'invite_accepted', 'roster_changed', 
                              'sponsor_approved', 'promotion_started']:
        return 'teams'
    
    # Economy/bounty-related
    if notification_type in ['payment_verified', 'payout_received', 'achievement_earned']:
        return 'bounties'
    
    # System
    return 'system'


@shared_task(bind=True, name='notifications.send_daily_digest', max_retries=3, default_retry_delay=300)
def send_daily_digest(self):
    """
    Send daily digest emails to users with unread notifications.
    Runs daily at 8 AM (configurable per user).
    """
    from apps.notifications.models import Notification, NotificationDigest, NotificationPreference
    from apps.accounts.models import User
    
    try:
        logger.info("Starting daily digest email task")
        
        # Get all users who have unread notifications and digest enabled
        yesterday = timezone.now() - timedelta(days=1)
        
        users_with_notifications = User.objects.filter(
            notifications__is_read=False,
            notifications__created_at__gte=yesterday
        ).distinct()
        
        sent_count = 0
        skipped_count = 0
        
        for user in users_with_notifications:
            try:
                # Get user preferences
                prefs = NotificationPreference.get_or_create_for_user(user)
                
                # Skip if digest disabled or email opted out
                if not prefs.enable_daily_digest or prefs.opt_out_email:
                    skipped_count += 1
                    continue
                
                # Get unread notifications from yesterday
                unread_notifications = Notification.objects.filter(
                    recipient=user,
                    is_read=False,
                    created_at__gte=yesterday
                ).order_by('-created_at')[:50]  # Limit to 50 most recent
                
                if not unread_notifications:
                    skipped_count += 1
                    continue
                
                # Create or get digest record
                digest, created = NotificationDigest.objects.get_or_create(
                    user=user,
                    digest_date=date.today(),
                    defaults={'is_sent': False}
                )
                
                # Skip if already sent today
                if digest.is_sent:
                    skipped_count += 1
                    continue
                
                # Add notifications to digest
                digest.notifications.set(unread_notifications)
                
                # Send email
                subject = f"DeltaCrown Daily Digest - {len(unread_notifications)} unread notifications"
                
                # Group notifications by type
                notifications_by_type = {}
                for notif in unread_notifications:
                    notif_type = notif.get_type_display()
                    if notif_type not in notifications_by_type:
                        notifications_by_type[notif_type] = []
                    notifications_by_type[notif_type].append(notif)
                
                html_message = render_to_string('notifications/email/daily_digest.html', {
                    'user': user,
                    'notifications': unread_notifications,
                    'notifications_by_type': notifications_by_type,
                    'total_count': len(unread_notifications),
                })
                
                plain_message = render_to_string('notifications/email/daily_digest.txt', {
                    'user': user,
                    'notifications': unread_notifications,
                    'notifications_by_type': notifications_by_type,
                    'total_count': len(unread_notifications),
                })
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                
                # Mark digest as sent
                digest.is_sent = True
                digest.sent_at = timezone.now()
                digest.save()
                
                sent_count += 1
                logger.info(f"Sent daily digest to {user.email} with {len(unread_notifications)} notifications")
                
            except Exception as user_exc:
                logger.error(f"Error sending digest to user {user.id}: {str(user_exc)}", exc_info=True)
                continue
        
        logger.info(f"Daily digest task completed. Sent: {sent_count}, Skipped: {skipped_count}")
        
        return {
            'status': 'success',
            'sent_count': sent_count,
            'skipped_count': skipped_count
        }
        
    except Exception as exc:
        logger.error(f"Error in daily digest task: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, name='notifications.send_email_notification')
def send_email_notification(self, notification_id):
    """
    Send individual email notification.
    
    Args:
        notification_id: ID of the notification to send
    """
    from apps.notifications.models import Notification, NotificationPreference
    from apps.notifications.enforcement import can_deliver_notification, get_blocked_reason, log_suppressed_notification
    
    try:
        notification = Notification.objects.select_related('recipient').get(id=notification_id)
        user = notification.recipient
        
        # PHASE 5B: Enforce delivery rules (channel, category, quiet hours)
        # Map notification type to category
        category = _map_notification_type_to_category(notification.type)
        
        if not can_deliver_notification(user, 'email', category):
            reason = get_blocked_reason(user, 'email', category)
            log_suppressed_notification(user, 'email', category, reason or 'unknown', notification.title)
            return {'status': 'skipped', 'reason': reason or 'user_preferences'}
        
        # Send email
        subject = notification.title
        
        html_message = render_to_string('notifications/email/single_notification.html', {
            'user': user,
            'notification': notification,
        })
        
        plain_message = render_to_string('notifications/email/single_notification.txt', {
            'user': user,
            'notification': notification,
        })
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Sent email notification {notification_id} to {user.email}")
        
        return {'status': 'success'}
        
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {'status': 'error', 'message': 'Notification not found'}
    except Exception as exc:
        logger.error(f"Error sending email notification: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}


@shared_task(bind=True, name='notifications.send_discord_notification')
def send_discord_notification(self, notification_data):
    """
    Send notification to Discord webhook.
    
    Args:
        notification_data: Dict with title, body, url, color
    """
    if not settings.DISCORD_NOTIFICATIONS_ENABLED:
        logger.info("Discord notifications disabled")
        return {'status': 'skipped', 'reason': 'discord_disabled'}
    
    try:
        webhook_url = settings.DISCORD_WEBHOOK_URL
        
        # Build Discord embed
        embed = {
            "title": notification_data.get('title', 'DeltaCrown Notification'),
            "description": notification_data.get('body', ''),
            "color": notification_data.get('color', 3447003),  # Blue by default
            "timestamp": timezone.now().isoformat(),
        }
        
        if notification_data.get('url'):
            embed['url'] = notification_data['url']
        
        if notification_data.get('thumbnail'):
            embed['thumbnail'] = {'url': notification_data['thumbnail']}
        
        payload = {
            "embeds": [embed]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        
        logger.info(f"Sent Discord notification: {notification_data.get('title')}")
        
        return {'status': 'success'}
        
    except requests.RequestException as exc:
        logger.error(f"Error sending Discord notification: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}


@shared_task(bind=True, name='notifications.cleanup_old_notifications', max_retries=3, default_retry_delay=60)
def cleanup_old_notifications(self, days_to_keep=90):
    """
    Clean up old read notifications.
    Keeps last 90 days of read notifications by default.
    """
    from apps.notifications.models import Notification
    
    try:
        logger.info(f"Starting notification cleanup (keeping {days_to_keep} days)")
        
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        old_notifications = Notification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date
        )
        
        count = old_notifications.count()
        old_notifications.delete()
        
        logger.info(f"Deleted {count} old notifications")
        
        return {
            'status': 'success',
            'deleted_count': count
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up notifications: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, name='notifications.batch_send_notifications')
def batch_send_notifications(self, user_ids, notification_type, title, body, url='', **metadata):
    """
    Send the same notification to multiple users in batch.
    
    Args:
        user_ids: List of user IDs to notify
        notification_type: Type of notification (from Notification.Type)
        title: Notification title
        body: Notification body
        url: Optional URL
        **metadata: Additional metadata (tournament_id, match_id, etc.)
    """
    from apps.notifications.models import Notification
    from apps.accounts.models import User
    
    try:
        logger.info(f"Sending batch notifications to {len(user_ids)} users")
        
        users = User.objects.filter(id__in=user_ids)
        
        notifications_to_create = []
        for user in users:
            notification = Notification(
                recipient=user,
                type=notification_type,
                title=title,
                body=body,
                url=url,
                **{k: v for k, v in metadata.items() if hasattr(Notification, k)}
            )
            notifications_to_create.append(notification)
        
        # Bulk create for performance
        Notification.objects.bulk_create(notifications_to_create)
        
        logger.info(f"Created {len(notifications_to_create)} batch notifications")
        
        return {
            'status': 'success',
            'created_count': len(notifications_to_create)
        }
        
    except Exception as exc:
        logger.error(f"Error sending batch notifications: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}
