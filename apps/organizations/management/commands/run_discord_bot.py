"""
Management command: run_discord_bot

Starts a long-running discord.py Bot that:
  1. Chat & announcement sync — listens in team-configured channels and
     writes inbound messages to the database / WebSocket groups.
  2. Slash commands (App Commands):
       /link        — Send user the DeltaCrown OAuth2 link URL.
       /profile     — View a player's DeltaCrown profile embed.
       /balance     — Check your DeltaCoin balance (@Linked only).
       /tournaments — Browse upcoming tournaments.
  3. Keeps a lightweight in-memory cache of (channel_id -> team_id) so
     that message routing is O(1).

Usage:
  python manage.py run_discord_bot

The bot token is read from settings.DISCORD_BOT_TOKEN.
Run this as a separate process (e.g. via supervisor / systemd / Docker).
"""

import asyncio
import logging
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


# -- Helpers ------------------------------------------------------------------


def _get_discord_user(discord_user_id: str):
    """Return the DeltaCrown User linked to a Discord user ID, or None."""
    try:
        from apps.user_profile.models_main import SocialLink

        social = SocialLink.objects.select_related("user__profile").filter(
            platform="discord",
            url=f"https://discord.com/users/{discord_user_id}",
        ).first()
        return social.user if social else None
    except Exception:
        return None


def _build_link_url(base_url: str, discord_user_id: str) -> str:
    """Build the OAuth2 link URL the bot sends to users for /link."""
    import hashlib
    import time

    raw = f"{discord_user_id}-{time.time()}"
    state = hashlib.sha256(raw.encode()).hexdigest()[:32]

    try:
        from django.core.cache import cache

        cache.set(f"discord_link_state:{state}", discord_user_id, timeout=600)
    except Exception:
        pass
    return f"{base_url.rstrip('/')}/account/discord/link?state={state}"


# -- Management command -------------------------------------------------------


class Command(BaseCommand):
    help = "Run the DeltaCrown Discord bot (chat sync + slash commands)."

    def handle(self, *args, **options):
        token = (
            getattr(settings, "DISCORD_BOT_TOKEN", "")
            or os.environ.get("DISCORD_BOT_TOKEN", "")
        )
        if not token:
            self.stderr.write(
                self.style.ERROR(
                    "DISCORD_BOT_TOKEN is not set in settings or environment. Aborting."
                )
            )
            sys.exit(1)

        try:
            import discord
            from discord import app_commands
            from discord.ext import commands
        except ImportError:
            self.stderr.write(
                self.style.ERROR(
                    "discord.py is not installed. Run: pip install discord.py"
                )
            )
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS("Starting DeltaCrown Discord bot..."))

        guild_id_str = getattr(settings, "DISCORD_GUILD_ID", "")
        site_url = getattr(settings, "SITE_URL", "https://deltacrown.xyz")

        # -- Channel -> team lookup -------------------------------------------
        from apps.organizations.models import Team

        def build_channel_map() -> dict:
            mapping = {}
            qs = Team.objects.filter(
                discord_bot_active=True,
                discord_guild_id__gt="",
            ).values_list(
                "pk",
                "discord_chat_channel_id",
                "discord_announcement_channel_id",
            )
            for team_id, chat_ch, ann_ch in qs:
                if chat_ch:
                    mapping[chat_ch] = (team_id, "chat")
                if ann_ch:
                    mapping[ann_ch] = (team_id, "announcement")
            return mapping

        channel_map = build_channel_map()

        # -- Bot setup --------------------------------------------------------
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True  # needed for role assignment

        bot = commands.Bot(command_prefix="!", intents=intents)
        guild_obj = discord.Object(id=int(guild_id_str)) if guild_id_str else None

        # -- on_ready ---------------------------------------------------------
        @bot.event
        async def on_ready():
            nonlocal channel_map
            # Wrap the synchronous ORM map builder in a thread
            channel_map = await asyncio.to_thread(build_channel_map)

            guild_count = len(bot.guilds)
            logger.info(
                "Discord bot logged in as %s -- %d guilds, %d channels tracked",
                bot.user,
                guild_count,
                len(channel_map),
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Bot online as {bot.user} in {guild_count} guild(s). "
                    f"Tracking {len(channel_map)} channel(s)."
                )
            )

            def _update_team_status():
                try:
                    from django.core.cache import cache
                    for g in bot.guilds:
                        cache.set(f"discord_bot_online:{g.id}", True, timeout=120)
                    connected = {str(g.id) for g in bot.guilds}
                    Team.objects.filter(discord_guild_id__in=connected).update(discord_bot_active=True)
                except Exception as e:
                    logger.error(f"Error updating team status: {e}")

            # Wrap the synchronous ORM status updater in a thread
            await asyncio.to_thread(_update_team_status)

            # Sync slash commands -- guild-scoped is instant; global takes up to 1 hr
            try:
                if guild_obj:
                    bot.tree.copy_global_to(guild=guild_obj)
                    synced = await bot.tree.sync(guild=guild_obj)
                else:
                    synced = await bot.tree.sync()
                logger.info("Synced %d slash command(s).", len(synced))
                self.stdout.write(self.style.SUCCESS(f"Synced {len(synced)} slash command(s)."))
            except Exception as exc:
                logger.warning("Failed to sync slash commands: %s", exc)

        # -- Member Join Auto-Sync --------------------------------------------
        @bot.event
        async def on_member_join(member: discord.Member):
            """Auto-assign @Linked role if the joining member already linked on the website."""
            def _check_and_get_role():
                from apps.user_profile.models_main import SocialLink
                from django.conf import settings as django_settings

                is_linked = SocialLink.objects.filter(
                    platform="discord",
                    url=f"https://discord.com/users/{member.id}"
                ).exists()

                if is_linked:
                    return getattr(django_settings, "DISCORD_LINKED_ROLE_ID", None)
                return None

            role_id_str = await asyncio.to_thread(_check_and_get_role)

            if role_id_str:
                role = member.guild.get_role(int(role_id_str))
                if role:
                    try:
                        await member.add_roles(role)
                        logger.info("Auto-assigned Linked role to returning user %s", member.display_name)
                    except Exception as e:
                        logger.warning("Failed to auto-assign role to %s: %s", member.display_name, e)

        # -- on_message (chat & announcement sync) ----------------------------
        @bot.event
        async def on_message(message: discord.Message):
            if message.author == bot.user or message.author.bot:
                return

            channel_id_str = str(message.channel.id)
            if channel_id_str not in channel_map:
                return

            team_id, channel_type = channel_map[channel_id_str]
            if channel_type == "chat":
                await _handle_chat_message(message, team_id)
            elif channel_type == "announcement":
                await _handle_announcement(message, team_id)

        async def _handle_chat_message(message: discord.Message, team_id: int):
            from apps.organizations.models.discord_sync import DiscordChatMessage

            def _save():
                linked_user = None
                discord_id_str = str(message.author.id)
                try:
                    from apps.user_profile.models_main import SocialLink

                    social = SocialLink.objects.select_related("user").filter(
                        platform="discord",
                        url=f"https://discord.com/users/{discord_id_str}",
                    ).first()
                    if social:
                        linked_user = social.user
                except Exception:
                    pass

                return DiscordChatMessage.objects.create(
                    team_id=team_id,
                    discord_message_id=str(message.id),
                    discord_channel_id=str(message.channel.id),
                    author_discord_id=discord_id_str,
                    author_discord_name=message.author.display_name,
                    author_user=linked_user,
                    content=message.content[:2000],
                    direction="inbound",
                )

            msg_obj = await asyncio.to_thread(_save)
            logger.debug("Saved inbound chat: team=%s author=%s", team_id, message.author)

            try:
                from channels.layers import get_channel_layer

                layer = get_channel_layer()
                if layer:
                    avatar_url = None
                    if msg_obj.author_user_id:
                        try:
                            profile = msg_obj.author_user.profile
                            if profile.avatar:
                                avatar_url = settings.MEDIA_URL + str(profile.avatar)
                        except Exception:
                            pass
                    await layer.group_send(
                        f"team_{team_id}",
                        {
                            "type": "chat.message",
                            "payload": {
                                "id": msg_obj.pk,
                                "content": msg_obj.content,
                                "author": msg_obj.author_discord_name or "Unknown",
                                "author_id": msg_obj.author_user_id,
                                "avatar_url": avatar_url,
                                "source": "discord",
                                "timestamp": msg_obj.created_at.isoformat(),
                            },
                        },
                    )
            except Exception as exc:
                logger.debug("Could not push chat to WebSocket: %s", exc)

        async def _handle_announcement(message: discord.Message, team_id: int):
            from apps.organizations.models import TeamAnnouncement

            def _save():
                TeamAnnouncement.objects.create(
                    team_id=team_id,
                    content=f"[Discord] {message.author.display_name}: {message.content[:1900]}",
                    announcement_type="general",
                )

            await asyncio.to_thread(_save)

        # -- Guild join/remove ------------------------------------------------
        @bot.event
        async def on_guild_join(guild: discord.Guild):
            nonlocal channel_map
            channel_map = build_channel_map()
            logger.info("Joined guild %s -- refreshed channel map (%d entries)", guild.name, len(channel_map))

        @bot.event
        async def on_guild_remove(guild: discord.Guild):
            nonlocal channel_map
            updated = Team.objects.filter(
                discord_guild_id=str(guild.id), discord_bot_active=True
            ).update(discord_bot_active=False)
            if updated:
                logger.warning("Removed from guild %s -- deactivated %d team(s)", guild.name, updated)
            channel_map = build_channel_map()

        # -- Slash Commands ---------------------------------------------------

        @bot.tree.command(name="link", description="Link your DeltaCrown account to Discord")
        async def cmd_link(interaction: discord.Interaction):
            auth_url = await asyncio.to_thread(
                _build_link_url, site_url, str(interaction.user.id)
            )
            embed = discord.Embed(
                title="Link Your DeltaCrown Account",
                description=(
                    "Click the link below to connect your DeltaCrown account.\n\n"
                    f"[**Tap here to link ->**]({auth_url})\n\n"
                    "_This link expires in 10 minutes._\n"
                    "_Scopes requested: identify (username only — no messages)._"
                ),
                color=discord.Color.from_rgb(255, 215, 0),
            )
            embed.set_footer(text="DeltaCrown - From the Delta to the Crown")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @bot.tree.command(name="profile", description="View a DeltaCrown player profile")
        @app_commands.describe(username="DeltaCrown username (leave blank for your own)")
        async def cmd_profile(interaction: discord.Interaction, username: str = ""):
            await interaction.response.defer(ephemeral=True)

            def _fetch():
                if username:
                    from django.contrib.auth import get_user_model

                    User = get_user_model()
                    try:
                        user = User.objects.select_related("profile").get(username__iexact=username)
                    except User.DoesNotExist:
                        return None
                else:
                    user = _get_discord_user(str(interaction.user.id))
                    if not user:
                        return None
                try:
                    p = user.profile
                except Exception:
                    return None
                return {
                    "username": user.username,
                    "display_name": p.display_name or user.username,
                    "slug": p.slug,
                    "level": p.level,
                    "xp": p.xp,
                    "skill_rating": p.skill_rating,
                    "reputation": p.reputation_score,
                    "balance": float(p.deltacoin_balance),
                }

            data = await asyncio.to_thread(_fetch)
            if data is None:
                hint = "\nUse **/link** to connect your account." if not username else ""
                target = f"@{username}" if username else "your account"
                await interaction.followup.send(
                    f"No DeltaCrown profile found for {target}.{hint}", ephemeral=True
                )
                return

            profile_url = f"{site_url}/players/{data['slug']}/"
            embed = discord.Embed(
                title=f"{data['display_name']}",
                url=profile_url,
                color=discord.Color.from_rgb(0, 216, 255),
            )
            embed.add_field(name="Username", value=data["username"], inline=True)
            embed.add_field(name="Level", value=str(data["level"]), inline=True)
            embed.add_field(name="XP", value=f"{data['xp']:,}", inline=True)
            embed.add_field(name="Skill Rating", value=str(data["skill_rating"]), inline=True)
            embed.add_field(name="Reputation", value=str(data["reputation"]), inline=True)
            embed.add_field(name="DeltaCoins", value=f"{data['balance']:,.2f}", inline=True)
            embed.set_footer(text="deltacrown.xyz")
            await interaction.followup.send(embed=embed, ephemeral=True)

        @bot.tree.command(name="balance", description="Check your DeltaCoin balance")
        async def cmd_balance(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            def _fetch():
                user = _get_discord_user(str(interaction.user.id))
                if not user:
                    return None
                balance = 0.0
                try:
                    balance = float(user.profile.deltacoin_balance)
                except Exception:
                    pass
                try:
                    from apps.economy.models import Wallet

                    wallet = Wallet.objects.filter(user=user).first()
                    if wallet:
                        balance = float(wallet.cached_balance)
                except Exception:
                    pass
                return {"username": user.username, "balance": balance}

            data = await asyncio.to_thread(_fetch)
            if data is None:
                await interaction.followup.send(
                    "Your Discord account is not linked to DeltaCrown.\nUse **/link** to connect.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="DeltaCoin Balance",
                color=discord.Color.from_rgb(255, 184, 0),
            )
            embed.add_field(
                name=data["username"],
                value=f"**{data['balance']:,.2f}** DeltaCoins",
                inline=False,
            )
            embed.set_footer(text=f"View full wallet at {site_url}/dashboard")
            await interaction.followup.send(embed=embed, ephemeral=True)

        @bot.tree.command(name="tournaments", description="Browse upcoming DeltaCrown tournaments")
        @app_commands.describe(game='Filter by game (e.g. "Valorant"). Optional.')
        async def cmd_tournaments(interaction: discord.Interaction, game: str = ""):
            await interaction.response.defer()

            def _fetch():
                from django.utils import timezone

                try:
                    from apps.tournaments.models import Tournament

                    qs = Tournament.objects.filter(
                        status__in=["published", "registration_open"],
                        tournament_start__gte=timezone.now(),
                    ).order_by("tournament_start")
                    if game:
                        qs = qs.filter(game__name__icontains=game)
                    results = []
                    for t in qs[:8]:
                        results.append(
                            {
                                "name": t.name,
                                "game": str(getattr(t, "game", "TBD")),
                                "start": t.tournament_start.strftime("%b %d, %Y") if t.tournament_start else "TBD",
                                "status": t.get_status_display() if hasattr(t, "get_status_display") else t.status,
                                "slug": getattr(t, "slug", ""),
                            }
                        )
                    return results
                except Exception as exc:
                    logger.warning("Tournament query failed: %s", exc)
                    return []

            items = await asyncio.to_thread(_fetch)
            embed = discord.Embed(
                title="Upcoming Tournaments",
                url=f"{site_url}/tournaments/",
                color=discord.Color.from_rgb(255, 70, 85),
            )
            if not items:
                embed.description = (
                    ("No upcoming tournaments found for **" + game + "**." if game else "No upcoming tournaments found.")
                    + f"\n\n[Browse all tournaments ->]({site_url}/tournaments/)"
                )
            else:
                lines = []
                for t in items:
                    link = (
                        f"{site_url}/tournaments/{t['slug']}/"
                        if t["slug"]
                        else f"{site_url}/tournaments/"
                    )
                    lines.append(f"**[{t['name']}]({link})**\n{t['game']} - {t['start']} - {t['status']}")
                embed.description = "\n\n".join(lines)
                embed.set_footer(text=f"View all at {site_url}/tournaments/")
            await interaction.followup.send(embed=embed)

        # -- Run --------------------------------------------------------------
        try:
            bot.run(token, log_handler=None)
        except discord.LoginFailure:
            self.stderr.write(
                self.style.ERROR(
                    "Login failed -- DISCORD_BOT_TOKEN is invalid or expired.\n"
                    "    Generate a new token at https://discord.com/developers/applications"
                )
            )
            sys.exit(1)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Discord bot crashed: {exc}"))
            logger.exception("Discord bot fatal error")
            sys.exit(1)

        self.stdout.write(self.style.WARNING("Discord bot has shut down."))