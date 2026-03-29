"""
Discord Webhook Service — Automated tournament notifications to Discord.

Phase 1 of the Discord Integration Plan.
Posts rich embeds for tournament lifecycle events to a configured webhook URL.
"""

import logging
from datetime import datetime, timezone as dt_timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Discord embed color palette (matching DeltaCrown brand)
COLORS = {
    'brand': 0x7C3AED,        # dc-purple
    'success': 0x22C55E,      # green-500
    'warning': 0xF59E0B,      # amber-500
    'danger': 0xEF4444,       # red-500
    'info': 0x06B6D4,         # dc-cyan
    'gold': 0xFFD700,         # gold
    'neutral': 0x6B7280,      # gray-500
}


class DiscordWebhookService:
    """
    Sends rich Discord embed messages via tournament webhook URL.

    Usage:
        DiscordWebhookService.send_event(tournament, 'bracket_generated', context)
        DiscordWebhookService.send_event_async(tournament, 'bracket_generated', context)
    """

    TIMEOUT = 10  # seconds

    # ── Game color helper ─────────────────────────────────────────

    @classmethod
    def _game_color(cls, tournament) -> int:
        """
        Return Discord embed sidebar color from the tournament's game primary_color.
        Falls back to dc-purple brand color if game has no color set.
        """
        try:
            hex_color = (
                getattr(getattr(tournament, 'game', None), 'primary_color', None) or ''
            ).lstrip('#')
            if len(hex_color) == 6:
                return int(hex_color, 16)
        except (ValueError, TypeError):
            pass
        return COLORS['brand']  # fallback: DeltaCrown purple

    # ── Core send method ──────────────────────────────────────────

    @classmethod
    def _post_embed_raw(cls, webhook_url: str, embed: dict, content: str = None) -> dict:
        """
        Low-level HTTP dispatch — returns structured result dict.

        Called by the Celery task and by post_embed/send_event.

        Returns:
            {'success': bool, 'status_code': int|None, 'error': str}
        """
        if not webhook_url:
            return {'success': False, 'status_code': None, 'error': 'No webhook URL'}

        payload = {"embeds": [embed]}
        if content:
            payload["content"] = content

        try:
            resp = requests.post(
                webhook_url,
                json=payload,
                timeout=cls.TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 204:
                logger.info("Discord webhook sent successfully to %s", webhook_url[:50])
                return {'success': True, 'status_code': 204, 'error': ''}
            else:
                logger.warning(
                    "Discord webhook returned %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return {
                    'success': False,
                    'status_code': resp.status_code,
                    'error': resp.text[:500],
                }
        except requests.RequestException as e:
            logger.error("Discord webhook failed: %s", e)
            return {'success': False, 'status_code': None, 'error': str(e)}

    @classmethod
    def post_embed(cls, webhook_url: str, embed: dict, content: str = None) -> bool:
        """
        Send a Discord embed message via webhook (synchronous).

        Returns:
            True if sent successfully (204), False otherwise.
        """
        result = cls._post_embed_raw(webhook_url, embed, content)
        return result['success']

    # ── Embed builder ─────────────────────────────────────────────

    @classmethod
    def build_embed(
        cls,
        title: str,
        description: str,
        color: int = COLORS['brand'],
        fields: list = None,
        url: str = None,
        thumbnail: str = None,
        image: str = None,
        footer: str = None,
    ) -> dict:
        """Build a Discord embed dict."""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(dt_timezone.utc).isoformat(),
            "footer": {
                "text": footer or "DeltaCrown — Tournament Platform",
                "icon_url": "https://deltacrown.com/static/img/favicon-32x32.png",
            },
        }
        if fields:
            embed["fields"] = fields
        if url:
            embed["url"] = url
        if thumbnail:
            embed["thumbnail"] = {"url": thumbnail}
        if image:
            embed["image"] = {"url": image}
        return embed

    # ── Event handlers ────────────────────────────────────────────

    @classmethod
    def send_event(cls, tournament, event: str, context: dict = None) -> bool:
        """
        Send a Discord webhook for a tournament event (synchronous).

        Looks up the webhook URL from tournament.discord_webhook_url.
        If no URL is configured, returns False silently.
        Logs the delivery result to DiscordWebhookLog.
        """
        webhook_url = getattr(tournament, 'discord_webhook_url', '') or ''
        if not webhook_url:
            return False

        ctx = context or {}
        base_url = ctx.get('base_url', 'https://deltacrown.com')
        tournament_url = f"{base_url}/tournaments/{tournament.slug}/"
        hub_url = f"{base_url}/tournaments/{tournament.slug}/hub/"

        handler = cls._EVENT_HANDLERS.get(event)
        if handler:
            embed = handler(cls, tournament, tournament_url, hub_url, ctx)
        else:
            # Generic event fallback
            embed = cls.build_embed(
                title=f"📢 {event.replace('_', ' ').title()}",
                description=f"**{tournament.name}** — {event.replace('_', ' ')}",
                color=cls._game_color(tournament),
                url=tournament_url,
            )

        result = cls._post_embed_raw(webhook_url, embed)

        # Log delivery receipt
        try:
            from apps.tournaments.models.discord_webhook_log import DiscordWebhookLog
            DiscordWebhookLog.record(
                tournament_id=tournament.id,
                event=event,
                webhook_url=webhook_url,
                success=result['success'],
                response_code=result.get('status_code'),
                error_message=result.get('error', ''),
            )
        except Exception:
            pass  # Never block on logging

        return result['success']

    @classmethod
    def send_event_async(cls, tournament, event: str, context: dict = None) -> None:
        """
        Dispatch a Discord webhook asynchronously via Celery.

        Builds the embed in the calling thread (so tournament data is fresh),
        then hands off the HTTP dispatch + logging to a background worker.
        Falls back to synchronous dispatch if Celery is unavailable.
        """
        webhook_url = getattr(tournament, 'discord_webhook_url', '') or ''
        if not webhook_url:
            return

        ctx = context or {}
        base_url = ctx.get('base_url', 'https://deltacrown.com')
        tournament_url = f"{base_url}/tournaments/{tournament.slug}/"
        hub_url = f"{base_url}/tournaments/{tournament.slug}/hub/"

        handler = cls._EVENT_HANDLERS.get(event)
        if handler:
            embed = handler(cls, tournament, tournament_url, hub_url, ctx)
        else:
            embed = cls.build_embed(
                title=f"📢 {event.replace('_', ' ').title()}",
                description=f"**{tournament.name}** — {event.replace('_', ' ')}",
                color=cls._game_color(tournament),
                url=tournament_url,
            )

        try:
            from apps.tournaments.tasks.discord_tasks import dispatch_discord_webhook
            dispatch_discord_webhook.delay(
                tournament_id=tournament.id,
                webhook_url=webhook_url,
                embed=embed,
                event=event,
            )
        except Exception as exc:
            # Celery unavailable (dev/test env) — fall back to sync
            logger.warning(
                "Celery unavailable for Discord dispatch (%s) — falling back to sync: %s",
                event, exc,
            )
            cls.send_event(tournament, event, context)

    # ── Individual event embed builders ───────────────────────────

    def _registration_open(self, tournament, t_url, h_url, ctx):
        game_name = tournament.game.display_name if tournament.game else 'Unknown Game'
        fields = [
            {"name": "🎮 Game", "value": game_name, "inline": True},
            {"name": "📋 Format", "value": tournament.get_format_display(), "inline": True},
        ]
        if tournament.prize_pool:
            fields.append({"name": "💰 Prize Pool", "value": f"৳{tournament.prize_pool:,.0f}", "inline": True})
        if tournament.max_participants:
            fields.append({"name": "👥 Slots", "value": str(tournament.max_participants), "inline": True})
        if tournament.has_entry_fee and tournament.entry_fee_amount:
            fields.append({"name": "🎟️ Entry Fee", "value": f"৳{tournament.entry_fee_amount:,.0f}", "inline": True})
        else:
            fields.append({"name": "🎟️ Entry", "value": "FREE", "inline": True})
        if tournament.tournament_start:
            fields.append({"name": "📅 Starts", "value": tournament.tournament_start.strftime("%b %d, %Y at %I:%M %p"), "inline": True})

        return self.build_embed(
            title="🎮 Registration is NOW OPEN!",
            description=f"**{tournament.name}** is accepting registrations.\n\n[👉 Register Now]({t_url})",
            color=self._game_color(tournament),
            fields=fields,
            url=t_url,
            thumbnail=self._get_game_icon(tournament),
        )

    def _registration_closed(self, tournament, t_url, h_url, ctx):
        count = ctx.get('registration_count', '—')
        return self.build_embed(
            title="🔒 Registration Closed",
            description=f"**{tournament.name}** registration is now closed.\n\n**{count}** participants registered.",
            color=COLORS['warning'],
            url=t_url,
        )

    def _checkin_open(self, tournament, t_url, h_url, ctx):
        minutes = ctx.get('minutes', tournament.check_in_minutes_before or 15)
        return self.build_embed(
            title="✅ Check-in is OPEN!",
            description=(
                f"**{tournament.name}** — Check-in has started!\n\n"
                f"⏰ You have **{minutes} minutes** to check in.\n\n"
                f"[👉 Check In Now]({h_url})"
            ),
            color=self._game_color(tournament),
            url=h_url,
        )

    def _checkin_closed(self, tournament, t_url, h_url, ctx):
        checked_in = ctx.get('checked_in_count', '—')
        total = ctx.get('total_count', '—')
        return self.build_embed(
            title="⏰ Check-in Closed",
            description=f"**{tournament.name}** — Check-in period has ended.\n\n**{checked_in}/{total}** participants checked in.",
            color=COLORS['neutral'],
            url=h_url,
        )

    def _bracket_generated(self, tournament, t_url, h_url, ctx):
        return self.build_embed(
            title="🏆 Bracket Generated!",
            description=f"**{tournament.name}** — The bracket has been generated.\n\n[👁️ View Bracket]({h_url})",
            color=self._game_color(tournament),
            url=h_url,
        )

    def _bracket_published(self, tournament, t_url, h_url, ctx):
        return self.build_embed(
            title="📢 Bracket is LIVE!",
            description=f"**{tournament.name}** — The bracket is now published and visible to all participants.\n\n[👁️ View Bracket]({h_url})",
            color=self._game_color(tournament),
            url=h_url,
        )

    def _group_draw_complete(self, tournament, t_url, h_url, ctx):
        group_count = ctx.get('group_count', '—')
        return self.build_embed(
            title="🎲 Group Draw Complete!",
            description=f"**{tournament.name}** — Groups have been drawn!\n\n**{group_count}** groups formed.\n\n[👁️ View Groups]({h_url})",
            color=self._game_color(tournament),
            url=h_url,
        )

    def _match_complete(self, tournament, t_url, h_url, ctx):
        fields = []
        p1 = ctx.get('participant1_name', 'TBD')
        p2 = ctx.get('participant2_name', 'TBD')
        s1 = ctx.get('participant1_score', '—')
        s2 = ctx.get('participant2_score', '—')
        winner = ctx.get('winner_name', '')
        match_label = ctx.get('match_label', 'Match')
        round_name = ctx.get('round_name', '')

        fields.append({"name": p1, "value": f"Score: **{s1}**", "inline": True})
        fields.append({"name": "vs", "value": "⚔️", "inline": True})
        fields.append({"name": p2, "value": f"Score: **{s2}**", "inline": True})
        if winner:
            fields.append({"name": "🏆 Winner", "value": f"**{winner}**", "inline": False})

        return self.build_embed(
            title=f"⚔️ {match_label} Complete" + (f" — {round_name}" if round_name else ""),
            description=f"**{tournament.name}**",
            color=self._game_color(tournament),
            fields=fields,
            url=h_url,
        )

    def _tournament_live(self, tournament, t_url, h_url, ctx):
        game_name = tournament.game.display_name if tournament.game else ''
        return self.build_embed(
            title="🔴 Tournament is LIVE!",
            description=f"**{tournament.name}** is now live!\n\n🎮 {game_name}\n\n[🏟️ Enter Hub]({h_url}) | [👁️ Spectate]({t_url}spectate/)",
            color=COLORS['danger'],
            url=h_url,
            thumbnail=self._get_game_icon(tournament),
        )

    def _tournament_complete(self, tournament, t_url, h_url, ctx):
        winner_name = ctx.get('winner_name', 'TBD')
        fields = [{"name": "🏆 Champion", "value": f"**{winner_name}**", "inline": False}]
        if tournament.prize_pool:
            fields.append({"name": "💰 Prize Pool", "value": f"৳{tournament.prize_pool:,.0f}", "inline": True})

        return self.build_embed(
            title="🎉 Tournament Complete!",
            description=f"**{tournament.name}** has concluded.\n\n[📊 View Results]({t_url})",
            color=COLORS['gold'],
            fields=fields,
            url=t_url,
        )

    def _round_start(self, tournament, t_url, h_url, ctx):
        round_name = ctx.get('round_name', 'Next Round')
        return self.build_embed(
            title=f"🔔 {round_name} Starting",
            description=f"**{tournament.name}** — {round_name} matches are beginning.\n\n[👁️ View Matches]({h_url})",
            color=self._game_color(tournament),
            url=h_url,
        )

    def _announcement(self, tournament, t_url, h_url, ctx):
        subject = ctx.get('subject', 'Announcement')
        body = ctx.get('body', '')
        return self.build_embed(
            title=f"📢 {subject}",
            description=f"**{tournament.name}**\n\n{body}",
            color=self._game_color(tournament),
            url=h_url,
        )

    # ── Event handler registry ────────────────────────────────────

    _EVENT_HANDLERS = {
        'registration_open': _registration_open,
        'registration_closed': _registration_closed,
        'checkin_open': _checkin_open,
        'checkin_closed': _checkin_closed,
        'checkin_reminder': lambda self, t, tu, hu, ctx: self.build_embed(
            title="⏰ Check-in Reminder",
            description=(
                f"**{t.name}** — Check-in is still OPEN!\n\n"
                f"You have not checked in yet. Please check in now before the deadline to avoid being disqualified.\n\n"
                f"[✅ Check In Now]({hu})"
            ),
            color=COLORS['warning'],
            url=hu,
            fields=[{"name": "Pending", "value": str(ctx.get("pending_count", "?")) + " participants", "inline": True}],
        ),
        'bracket_generated': _bracket_generated,
        'bracket_published': _bracket_published,
        'group_draw_complete': _group_draw_complete,
        'match_complete': _match_complete,
        'match_ready': lambda self, t, tu, hu, ctx: self.build_embed(
            title="⏱️ Match Starting Soon",
            description=f"**{t.name}** — A match is about to begin!\n\n[👁️ View Match]({hu})",
            color=self._game_color(t),
            url=hu,
        ),
        'match_reminder_1h': lambda self, t, tu, hu, ctx: self.build_embed(
            title="🕐 Match Reminder (1 Hour)",
            description=f"**{t.name}** — A match starts in about 1 hour.\n\n[👁️ Open Hub]({hu})",
            color=self._game_color(t),
            url=hu,
        ),
        'match_reminder_20m': lambda self, t, tu, hu, ctx: self.build_embed(
            title="⏰ Match Reminder (20 Minutes)",
            description=f"**{t.name}** — A match starts in about 20 minutes.\n\n[👁️ Open Hub]({hu})",
            color=self._game_color(t),
            url=hu,
        ),
        'match_reschedule_proposed': lambda self, t, tu, hu, ctx: self.build_embed(
            title="🗓️ Reschedule Proposed",
            description=f"A participant proposed a new match time in **{t.name}**.\n\n[👁️ Review in Hub]({hu})",
            color=COLORS['warning'],
            url=hu,
        ),
        'match_reschedule_accepted': lambda self, t, tu, hu, ctx: self.build_embed(
            title="✅ Reschedule Accepted",
            description=f"A match time change was accepted in **{t.name}**.\n\n[👁️ View Updated Schedule]({hu})",
            color=COLORS['success'],
            url=hu,
        ),
        'match_reschedule_rejected': lambda self, t, tu, hu, ctx: self.build_embed(
            title="❌ Reschedule Rejected",
            description=f"A proposed match time was rejected in **{t.name}**.\n\n[👁️ Review in Hub]({hu})",
            color=COLORS['danger'],
            url=hu,
        ),
        'tournament_live': _tournament_live,
        'tournament_complete': _tournament_complete,
        'round_start': _round_start,
        'announcement': _announcement,
    }

    # ── Utility ───────────────────────────────────────────────────

    @staticmethod
    def _get_game_icon(tournament) -> Optional[str]:
        """Get game icon URL for embed thumbnail."""
        try:
            if tournament.game and tournament.game.icon:
                return tournament.game.icon.url
        except Exception:
            pass
        return None

    @classmethod
    def test_webhook(cls, webhook_url: str, tournament_name: str = "Test Tournament") -> dict:
        """
        Send a test message to verify the webhook URL works.

        Returns:
            dict with 'success' bool and optional 'error' message.
        """
        embed = cls.build_embed(
            title="✅ Webhook Connected!",
            description=(
                f"This Discord channel is now linked to **{tournament_name}** on DeltaCrown.\n\n"
                "You'll receive automated updates for:\n"
                "• Registration opens/closes\n"
                "• Check-in reminders\n"
                "• Bracket & match updates\n"
                "• Tournament results"
            ),
            color=COLORS['success'],
        )
        success = cls.post_embed(webhook_url, embed)
        if success:
            return {"success": True}
        else:
            return {"success": False, "error": "Failed to send test message. Check the webhook URL."}
