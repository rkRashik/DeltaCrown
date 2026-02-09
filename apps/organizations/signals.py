"""
Django signals for the Organizations app.

Handles:
  - Discord announcement sync on TeamAnnouncement creation
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='organizations.TeamAnnouncement')
def sync_announcement_to_discord(sender, instance, created, **kwargs):
    """Fire send_discord_announcement Celery task when a new announcement is created."""
    if not created:
        return

    team = instance.team

    # Only dispatch if team has any Discord output channel configured
    if not (team.discord_webhook_url or
            (team.discord_bot_active and team.discord_announcement_channel_id)):
        return

    try:
        from apps.organizations.tasks.discord_sync import send_discord_announcement
        send_discord_announcement.delay(team.pk, instance.pk)
        logger.info(
            'Dispatched Discord announcement sync for team=%s announcement=%s',
            team.pk, instance.pk,
        )
    except Exception:
        logger.exception('Failed to dispatch Discord announcement task')
