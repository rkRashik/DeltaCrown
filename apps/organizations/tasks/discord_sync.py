"""
Celery tasks for Discord integration.

All Discord HTTP calls happen ONLY inside these tasks — never in the
Django request/response cycle.

Tasks:
  send_discord_announcement — push a TeamAnnouncement to the guild's
                              announcement channel via webhook.
  send_discord_chat_message — push a web-originated chat message to
                              the guild's chat channel via webhook/bot.
  validate_discord_bot_presence — check the bot is in the guild and
                                  can see the configured channels.
"""

import logging

import requests
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Webhook-based delivery (fastest, no bot needed) ────────────────


def _post_webhook(webhook_url: str, content: str, username: str = 'DeltaCrown',
                  avatar_url: str | None = None) -> bool:
    """Fire-and-forget POST to a Discord webhook URL."""
    payload = {
        'content': content,
        'username': username,
    }
    if avatar_url:
        payload['avatar_url'] = avatar_url
    try:
        resp = requests.post(webhook_url, json=payload, timeout=5)
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning('Discord webhook POST failed: %s', exc)
        return False


# ── Bot-based delivery (uses Bot token, needed for non-webhook ops) ─


def _bot_headers() -> dict:
    """Return Authorization headers for the platform Discord bot."""
    token = getattr(settings, 'DISCORD_BOT_TOKEN', '')
    return {
        'Authorization': f'Bot {token}',
        'Content-Type': 'application/json',
    }


def _bot_send_message(channel_id: str, content: str) -> dict | None:
    """Send a message to a Discord channel via the Bot REST API."""
    url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
    try:
        resp = requests.post(url, headers=_bot_headers(),
                             json={'content': content}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning('Discord Bot message failed (ch=%s): %s', channel_id, exc)
        return None


# ── Shared tasks ────────────────────────────────────────────────────


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_discord_announcement(self, team_id: int, announcement_id: int):
    """Push a TeamAnnouncement to the team's Discord announcement channel.

    Strategy:
      1. If team has a webhook_url configured → use webhook (fastest)
      2. Else if team has guild + announcement channel + bot active → use bot
      3. Else skip silently
    """
    from apps.organizations.models import Team, TeamAnnouncement

    try:
        team = Team.objects.get(pk=team_id)
        announcement = TeamAnnouncement.objects.get(pk=announcement_id)
    except (Team.DoesNotExist, TeamAnnouncement.DoesNotExist):
        return  # stale task

    content = f"**📢 {announcement.get_announcement_type_display()}**\n{announcement.content}"
    author_name = (
        announcement.author.username if announcement.author else 'DeltaCrown'
    )

    # Prefer webhook delivery
    if team.discord_webhook_url:
        ok = _post_webhook(
            team.discord_webhook_url,
            content,
            username=f'{author_name} via DeltaCrown',
        )
        if ok:
            return

    # Fallback to bot channel message
    if team.discord_bot_active and team.discord_announcement_channel_id:
        _bot_send_message(team.discord_announcement_channel_id, content)


@shared_task(bind=True, max_retries=2, default_retry_delay=3)
def send_discord_chat_message(self, team_id: int, chat_message_id: int):
    """Push a web-originated chat message to Discord.

    Uses the Bot API to send to the team's chat channel so that
    Discord users see the message in <500 ms.
    """
    from apps.organizations.models import Team
    from apps.organizations.models.discord_sync import DiscordChatMessage

    try:
        team = Team.objects.get(pk=team_id)
        msg = DiscordChatMessage.objects.get(pk=chat_message_id)
    except (Team.DoesNotExist, DiscordChatMessage.DoesNotExist):
        return

    if not team.discord_bot_active or not team.discord_chat_channel_id:
        return

    author_name = 'Unknown'
    if msg.author_user:
        author_name = msg.author_user.username
    elif msg.author_discord_name:
        author_name = msg.author_discord_name

    content = f"**{author_name}** (via DeltaCrown): {msg.content}"
    result = _bot_send_message(team.discord_chat_channel_id, content)

    if result and result.get('id'):
        # Store the Discord message ID for future reference
        msg.discord_message_id = result['id']
        msg.discord_channel_id = team.discord_chat_channel_id
        msg.save(update_fields=['discord_message_id', 'discord_channel_id'])


@shared_task(bind=True, max_retries=1, default_retry_delay=5)
def validate_discord_bot_presence(self, team_id: int):
    """Verify the platform bot is in the team's Discord guild.

    Called when a team saves their Discord config.  Sets
    ``team.discord_bot_active`` accordingly.
    """
    from apps.organizations.models import Team

    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist:
        return

    guild_id = team.discord_guild_id
    if not guild_id:
        Team.objects.filter(pk=team_id).update(discord_bot_active=False)
        return

    # Check if the bot is a member of the guild
    url = f'https://discord.com/api/v10/guilds/{guild_id}'
    try:
        resp = requests.get(url, headers=_bot_headers(), timeout=5)
        if resp.status_code == 200:
            Team.objects.filter(pk=team_id).update(discord_bot_active=True)
            logger.info('Discord bot verified in guild %s for team %s', guild_id, team_id)
        else:
            Team.objects.filter(pk=team_id).update(discord_bot_active=False)
            logger.warning(
                'Discord bot NOT in guild %s (HTTP %s) for team %s',
                guild_id, resp.status_code, team_id,
            )
    except requests.RequestException as exc:
        logger.warning('Discord guild check failed: %s', exc)
        Team.objects.filter(pk=team_id).update(discord_bot_active=False)
