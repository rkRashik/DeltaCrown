"""
Discord Sync Models — bi-directional chat & announcement synchronization.

DiscordChatMessage: lobby-style chat messages synced between Web ↔ Discord.
Direction:
  INBOUND  = Discord → Web  (bot listener pushes to DB, frontend polls/WS)
  OUTBOUND = Web → Discord  (user posts on Web, Celery pushes to Discord)
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class DiscordChatMessage(models.Model):
    """A single chat message in the team's Discord ↔ Web lobby."""

    DIRECTION_CHOICES = [
        ('inbound', 'Discord → Web'),
        ('outbound', 'Web → Discord'),
    ]

    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='discord_chat_messages',
    )
    # Discord metadata (always populated for inbound; set after send for outbound)
    discord_message_id = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text='Discord message snowflake ID',
    )
    discord_channel_id = models.CharField(
        max_length=20,
        blank=True,
        help_text='Discord channel this message belongs to',
    )

    # Author info
    author_discord_id = models.CharField(
        max_length=20,
        blank=True,
        help_text='Discord user snowflake ID',
    )
    author_discord_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Discord display name at time of message',
    )
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discord_chat_messages',
        help_text='Linked DeltaCrown user (if known)',
    )

    content = models.TextField(
        max_length=2000,
        help_text='Message text content',
    )
    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        help_text='inbound = Discord→Web, outbound = Web→Discord',
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        app_label = 'organizations'
        db_table = 'organizations_discord_chat_message'
        ordering = ['created_at']
        indexes = [
            models.Index(
                fields=['team', '-created_at'],
                name='dchat_team_created_idx',
            ),
            models.Index(
                fields=['team', 'direction', '-created_at'],
                name='dchat_team_dir_idx',
            ),
        ]

    def __str__(self):
        tag = self.team.tag or self.team.slug
        author = self.author_discord_name or (self.author_user and self.author_user.username) or '?'
        return f"[{tag}] {self.direction} {author}: {self.content[:40]}"
