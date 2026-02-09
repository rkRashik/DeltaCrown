"""
Django signals for the Organizations app.

Handles:
  - Discord announcement sync on TeamAnnouncement creation
  - Discord role sync on TeamMembership role changes
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ── Membership role change → Discord role sync ────────────────────

@receiver(pre_save, sender='organizations.TeamMembership')
def _capture_old_role(sender, instance, **kwargs):
    """Stash the previous role before save so post_save can compute the diff."""
    if instance.pk:
        try:
            instance._old_role = sender.objects.filter(pk=instance.pk).values_list('role', flat=True).first()
        except Exception:
            instance._old_role = None
    else:
        instance._old_role = None


@receiver(post_save, sender='organizations.TeamMembership')
def sync_membership_role_to_discord(sender, instance, created, **kwargs):
    """Fire sync_discord_role task when a membership role changes or is created."""
    old_role = getattr(instance, '_old_role', None)
    new_role = instance.role

    # Only fire on creation or actual role change
    if not created and old_role == new_role:
        return

    team = instance.team
    # Only dispatch if team has Discord bot + guild configured
    if not team.discord_bot_active or not team.discord_guild_id:
        return

    # Only dispatch if team has at least one Discord role ID configured
    if not (team.discord_captain_role_id or team.discord_manager_role_id):
        return

    try:
        from apps.organizations.tasks.discord_sync import sync_discord_role
        sync_discord_role.delay(
            team.pk,
            instance.user_id,
            new_role,
            old_role=old_role,
        )
        logger.info(
            'Dispatched Discord role sync: team=%s user=%s %s→%s',
            team.pk, instance.user_id, old_role, new_role,
        )
    except Exception:
        logger.exception('Failed to dispatch Discord role sync task')


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
