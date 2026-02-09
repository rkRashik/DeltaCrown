"""
Management command: run_discord_bot

Starts a long-running discord.py bot client that:
  1. Listens in each team's configured chat channel and writes
     inbound DiscordChatMessages to the database.
  2. Listens in announcement channels and creates TeamAnnouncements
     for messages from external Discord users.
  3. Keeps a lightweight in-memory cache of (guild_id → team_id) so
     that channel lookups are O(1).

Usage:
  python manage.py run_discord_bot

The bot token is read from settings.DISCORD_BOT_TOKEN.
Run this as a separate process (e.g. via supervisor / systemd).
"""

import asyncio
import logging
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the DeltaCrown Discord bot listener for chat & announcement sync.'

    def handle(self, *args, **options):
        token = getattr(settings, 'DISCORD_BOT_TOKEN', '') or os.environ.get('DISCORD_BOT_TOKEN', '')
        if not token:
            self.stderr.write(self.style.ERROR(
                'DISCORD_BOT_TOKEN is not set in settings or environment. Aborting.'
            ))
            sys.exit(1)

        # Lazy import so the command is discoverable even without discord.py
        try:
            import discord  # noqa: F811
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'discord.py is not installed. Run: pip install discord.py'
            ))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS('Starting DeltaCrown Discord bot…'))

        # ── Build channel → team lookup ────────────────────────────────
        from apps.organizations.models import Team

        def build_channel_map() -> dict:
            """Return {channel_id_str: (team_id, channel_type)} for all
            teams with active bot integration."""
            mapping = {}
            qs = Team.objects.filter(
                discord_bot_active=True,
                discord_guild_id__gt='',
            ).values_list(
                'pk',
                'discord_chat_channel_id',
                'discord_announcement_channel_id',
            )
            for team_id, chat_ch, ann_ch in qs:
                if chat_ch:
                    mapping[chat_ch] = (team_id, 'chat')
                if ann_ch:
                    mapping[ann_ch] = (team_id, 'announcement')
            return mapping

        channel_map = build_channel_map()

        # ── Discord client setup ───────────────────────────────────────
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            guild_count = len(client.guilds)
            logger.info('Discord bot logged in as %s — %d guilds', client.user, guild_count)
            self.stdout.write(self.style.SUCCESS(
                f'Bot online as {client.user} in {guild_count} guild(s). '
                f'Tracking {len(channel_map)} channel(s).'
            ))

            # Set Redis cache for instant bot-status checks on the dashboard
            try:
                from django.core.cache import cache
                connected_guild_ids = {str(g.id) for g in client.guilds}
                for gid in connected_guild_ids:
                    cache.set(f'discord_bot_online:{gid}', True, timeout=120)
                # Bulk-activate teams whose guild_id matches a connected guild
                from apps.organizations.models import Team
                Team.objects.filter(
                    discord_guild_id__in=connected_guild_ids,
                ).update(discord_bot_active=True)
            except Exception:
                pass  # Redis may not be available

        @client.event
        async def on_message(message: discord.Message):
            # Ignore our own messages
            if message.author == client.user:
                return
            # Ignore bot messages
            if message.author.bot:
                return

            channel_id_str = str(message.channel.id)
            if channel_id_str not in channel_map:
                return

            team_id, channel_type = channel_map[channel_id_str]

            if channel_type == 'chat':
                await _handle_chat_message(message, team_id)
            elif channel_type == 'announcement':
                await _handle_announcement(message, team_id)

        async def _handle_chat_message(message: discord.Message, team_id: int):
            """Persist an inbound Discord chat message.

            Attempts to resolve the Discord author to a DeltaCrown user
            by looking up their discord_id in SocialLink records.
            Then pushes the message to the WebSocket group for real-time
            display on the web UI.
            """
            from apps.organizations.models.discord_sync import DiscordChatMessage

            # Run DB write in a thread to avoid blocking the event loop
            def _save():
                # Try to resolve the Discord user → DeltaCrown user
                linked_user = None
                discord_id_str = str(message.author.id)
                try:
                    from apps.user_profile.models_main import SocialLink
                    social = SocialLink.objects.select_related('user').filter(
                        platform='discord',
                        handle__icontains=discord_id_str,
                    ).first()
                    if social:
                        linked_user = social.user
                    else:
                        # Fallback: check by Discord username#discriminator
                        discord_tag = str(message.author)
                        social = SocialLink.objects.select_related('user').filter(
                            platform='discord',
                            handle__iexact=discord_tag,
                        ).first()
                        if social:
                            linked_user = social.user
                except Exception:
                    pass  # Graceful fallback — save without linking

                obj = DiscordChatMessage.objects.create(
                    team_id=team_id,
                    discord_message_id=str(message.id),
                    discord_channel_id=str(message.channel.id),
                    author_discord_id=discord_id_str,
                    author_discord_name=message.author.display_name,
                    author_user=linked_user,
                    content=message.content[:2000],
                    direction='inbound',
                )
                return obj

            msg_obj = await asyncio.to_thread(_save)
            logger.debug(
                'Saved inbound chat: team=%s author=%s',
                team_id, message.author.display_name,
            )

            # Push to Django Channels WebSocket group for real-time web display
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                layer = get_channel_layer()
                if layer:
                    # Resolve avatar URL
                    avatar_url = None
                    if msg_obj.author_user_id:
                        try:
                            profile = msg_obj.author_user.profile
                            if profile.avatar:
                                from django.conf import settings as _s
                                avatar_url = _s.MEDIA_URL + str(profile.avatar)
                        except Exception:
                            pass

                    await layer.group_send(
                        f'team_{team_id}',
                        {
                            'type': 'chat.message',
                            'payload': {
                                'id': msg_obj.pk,
                                'content': msg_obj.content,
                                'author': msg_obj.author_discord_name or 'Unknown',
                                'author_id': msg_obj.author_user_id,
                                'avatar_url': avatar_url,
                                'source': 'discord',
                                'timestamp': msg_obj.created_at.isoformat(),
                            },
                        },
                    )
            except Exception as e:
                logger.debug('Could not push chat message to WebSocket: %s', e)

        async def _handle_announcement(message: discord.Message, team_id: int):
            """Persist an inbound Discord announcement as a TeamAnnouncement."""
            from apps.organizations.models import TeamAnnouncement

            def _save():
                TeamAnnouncement.objects.create(
                    team_id=team_id,
                    content=f"[Discord] {message.author.display_name}: {message.content[:1900]}",
                    announcement_type='general',
                )

            await asyncio.to_thread(_save)
            logger.info(
                'Saved inbound announcement: team=%s author=%s',
                team_id, message.author.display_name,
            )

        @client.event
        async def on_guild_join(guild: discord.Guild):
            """Refresh channel map when bot joins a new guild."""
            nonlocal channel_map
            channel_map = build_channel_map()
            logger.info('Joined guild %s — channel map refreshed (%d entries)',
                        guild.name, len(channel_map))

        @client.event
        async def on_guild_remove(guild: discord.Guild):
            """Mark teams as bot-inactive when removed from a guild."""
            nonlocal channel_map
            guild_id = str(guild.id)
            from apps.organizations.models import Team
            updated = Team.objects.filter(
                discord_guild_id=guild_id, discord_bot_active=True,
            ).update(discord_bot_active=False)
            if updated:
                logger.warning('Removed from guild %s — deactivated %d team(s)', guild.name, updated)
            channel_map = build_channel_map()

        # ── Run the client ─────────────────────────────────────────────
        try:
            client.run(token, log_handler=None)  # Django logging handles output
        except discord.LoginFailure:
            self.stderr.write(self.style.ERROR(
                '❌  Login failed — DISCORD_BOT_TOKEN is invalid or expired.\n'
                '    Generate a new token at https://discord.com/developers/applications'
            ))
            sys.exit(1)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(
                f'❌  Discord bot crashed: {exc}'
            ))
            logger.exception('Discord bot fatal error')
            sys.exit(1)

        self.stdout.write(self.style.WARNING('Discord bot has shut down.'))
