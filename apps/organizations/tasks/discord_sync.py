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

    # Build content with a link back to the DeltaCrown team page
    team_url = f"https://deltacrown.com/teams/{team.slug}/"
    content = (
        f"**📢 {announcement.get_announcement_type_display()}**\n"
        f"{announcement.content}\n\n"
        f"🔗 [View on DeltaCrown]({team_url})"
    )
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

    Strategy:
      1. Prefer webhook — overrides username + avatar_url so it appears
         as the DeltaCrown user chatting directly in Discord.
      2. Fallback to Bot API if no webhook configured.
    """
    from apps.organizations.models import Team
    from apps.organizations.models.discord_sync import DiscordChatMessage

    try:
        team = Team.objects.get(pk=team_id)
        msg = DiscordChatMessage.objects.select_related('author_user').get(
            pk=chat_message_id,
        )
    except (Team.DoesNotExist, DiscordChatMessage.DoesNotExist):
        return

    # Build identity from the DeltaCrown user
    author_name = 'DeltaCrown User'
    avatar_url = None
    if msg.author_user:
        author_name = msg.author_user.username
        # Try to get display_name + avatar from UserProfile
        try:
            profile = msg.author_user.profile
            if profile.display_name:
                author_name = profile.display_name
            avatar_url = profile.get_avatar_url()
        except Exception:
            pass
    elif msg.author_discord_name:
        author_name = msg.author_discord_name

    # ── Prefer webhook (shows as the actual user in Discord) ────────
    if team.discord_webhook_url:
        ok = _post_webhook(
            team.discord_webhook_url,
            msg.content,
            username=author_name,
            avatar_url=avatar_url,
        )
        if ok:
            return

    # ── Fallback to bot API ─────────────────────────────────────────
    if team.discord_bot_active and team.discord_chat_channel_id:
        content = f"**{author_name}**: {msg.content}"
        result = _bot_send_message(team.discord_chat_channel_id, content)
        if result and result.get('id'):
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
            # Cache the online status in Redis for instant dashboard checks
            try:
                from django.core.cache import cache
                cache.set(f'discord_bot_online:{guild_id}', True, timeout=120)
            except Exception:
                pass
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


# ── Automated Role Sync ─────────────────────────────────────────

_ROLE_TO_FIELD = {
    'OWNER':   'discord_captain_role_id',
    'MANAGER': 'discord_manager_role_id',
}


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def sync_discord_role(
    self, team_id: int, user_id: int, new_role: str, old_role: str | None = None,
):
    """Assign/remove Discord guild roles when a membership role changes.

    - If the new role has a configured Discord role ID → assign it.
    - If the old role had a configured Discord role ID → remove it.
    - Requires: bot active, guild_id configured, user has a linked Discord ID.
    """
    from apps.organizations.models import Team
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        team = Team.objects.get(pk=team_id)
        user = User.objects.get(pk=user_id)
    except (Team.DoesNotExist, User.DoesNotExist):
        return

    if not team.discord_bot_active or not team.discord_guild_id:
        return

    # Resolve the user's Discord ID from SocialLink
    discord_user_id = None
    try:
        from apps.user_profile.models_main import SocialLink
        social = SocialLink.objects.filter(
            user=user, platform='discord',
        ).first()
        if social and social.handle:
            # handle might store numeric ID or username — try numeric first
            handle = social.handle.strip()
            if handle.isdigit():
                discord_user_id = handle
    except Exception:
        pass

    if not discord_user_id:
        logger.info(
            'sync_discord_role skipped: no Discord ID for user=%s team=%s',
            user_id, team_id,
        )
        return

    guild_id = team.discord_guild_id
    headers = _bot_headers()

    # Determine which Discord role IDs to assign and remove
    new_discord_role_field = _ROLE_TO_FIELD.get(new_role)
    old_discord_role_field = _ROLE_TO_FIELD.get(old_role) if old_role else None

    role_to_assign = getattr(team, new_discord_role_field, '') if new_discord_role_field else ''
    role_to_remove = getattr(team, old_discord_role_field, '') if old_discord_role_field else ''

    # Assign new role
    if role_to_assign:
        url = (
            f'https://discord.com/api/v10/guilds/{guild_id}'
            f'/members/{discord_user_id}/roles/{role_to_assign}'
        )
        try:
            resp = requests.put(url, headers=headers, timeout=5)
            if resp.status_code in (200, 204):
                logger.info(
                    'Assigned Discord role %s to user %s in guild %s',
                    role_to_assign, discord_user_id, guild_id,
                )
            else:
                logger.warning(
                    'Failed to assign Discord role %s (HTTP %s): %s',
                    role_to_assign, resp.status_code, resp.text[:200],
                )
        except requests.RequestException as exc:
            logger.warning('Discord role assign failed: %s', exc)

    # Remove old role (if different from new)
    if role_to_remove and role_to_remove != role_to_assign:
        url = (
            f'https://discord.com/api/v10/guilds/{guild_id}'
            f'/members/{discord_user_id}/roles/{role_to_remove}'
        )
        try:
            resp = requests.delete(url, headers=headers, timeout=5)
            if resp.status_code in (200, 204):
                logger.info(
                    'Removed Discord role %s from user %s in guild %s',
                    role_to_remove, discord_user_id, guild_id,
                )
            else:
                logger.warning(
                    'Failed to remove Discord role %s (HTTP %s): %s',
                    role_to_remove, resp.status_code, resp.text[:200],
                )
        except requests.RequestException as exc:
            logger.warning('Discord role remove failed: %s', exc)
