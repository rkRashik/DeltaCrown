"""
Homepage live data WebSocket consumer.

Pushes real-time ticker updates (live matches, events, signups) and the
Arena live-match count badge to all connected homepage clients without
requiring a page refresh.

Channel group: homepage_live
Push interval: 30 seconds via asyncio background task
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps
from django.db.models import Q

logger = logging.getLogger(__name__)

PUSH_INTERVAL = 30  # seconds between live-data refreshes


class HomepageLiveConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the homepage live feed.

    On connect: join the `homepage_live` group and immediately push current data.
    Every PUSH_INTERVAL seconds: re-fetch and push fresh data.
    On disconnect: leave the group and cancel the background task.
    """

    GROUP_NAME = "homepage_live"

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()
        # Push immediately so the client doesn't wait for the first interval
        await self._push_live_data()
        self._task = asyncio.ensure_future(self._periodic_push())

    async def disconnect(self, code):
        task = getattr(self, "_task", None)
        if task and not task.done():
            task.cancel()
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    # ------------------------------------------------------------------
    # Group broadcast handler — called when another part of the system
    # sends a message to the `homepage_live` group (e.g. after a match
    # state change in a Celery task or match consumer).
    # ------------------------------------------------------------------
    async def homepage_update(self, event: dict):
        await self.send(text_data=json.dumps(event.get("data", {})))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _periodic_push(self):
        try:
            while True:
                await asyncio.sleep(PUSH_INTERVAL)
                await self._push_live_data()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("HomepageLiveConsumer periodic push error: %s", exc)

    async def _push_live_data(self):
        from asgiref.sync import sync_to_async
        data = await sync_to_async(_build_live_payload, thread_sensitive=True)()
        await self.send(text_data=json.dumps(data))


# ------------------------------------------------------------------
# Sync helper — runs in Django's thread pool
# ------------------------------------------------------------------

def _build_live_payload() -> dict[str, Any]:
    """
    Build the live data dict sent to homepage clients.
    Returns:
        {
          "type": "live_update",
          "live_count": int,          # total live matches right now
          "ticker": [{"kind": str, "text": str}],
        }
    """
    live_count = 0
    ticker: list[dict[str, str]] = []

    try:
        Match = apps.get_model("tournaments", "Match")
        live_qs = Match.objects.filter(is_deleted=False, state="live").select_related(
            "tournament", "tournament__game"
        ).order_by("scheduled_time", "id")[:5]
        live_rows = list(live_qs)
        live_count = len(live_rows)

        for m in live_rows:
            game = getattr(m.tournament, "game", None) if m.tournament else None
            game_name = (game.display_name or game.name) if game else "MATCH"
            ticker.append({
                "kind": "live",
                "text": (
                    f"{game_name.upper()} — "
                    f"{m.participant1_name or 'A'} vs {m.participant2_name or 'B'}"
                ),
            })
    except Exception as exc:
        logger.debug("HomepageLive: match fetch failed: %s", exc)

    # Pad with recent registration count if few live matches
    if len(ticker) < 6:
        try:
            from django.utils import timezone
            from datetime import timedelta
            Registration = apps.get_model("tournaments", "Registration")
            since = timezone.now() - timedelta(hours=24)
            count = Registration.objects.filter(
                created_at__gte=since, is_deleted=False
            ).count()
            if count > 0:
                ticker.append({
                    "kind": "signup",
                    "text": f"{count} new registrations in the last 24h",
                })
        except Exception:
            pass

    # Pad with active tournament events
    if len(ticker) < 8:
        try:
            Tournament = apps.get_model("tournaments", "Tournament")
            for t in (
                Tournament.objects.filter(
                    is_deleted=False,
                    status__in=["registration_open", "live"],
                )
                .select_related("game")
                .order_by("-tournament_start")[:3]
            ):
                game = t.game
                game_name = ((game.display_name or game.name) if game else "").upper()
                ticker.append({
                    "kind": "tournament",
                    "text": f"{game_name + ' · ' if game_name else ''}{t.name}",
                })
        except Exception:
            pass

    # Duplicate for marquee seamlessness
    if ticker:
        ticker = ticker + ticker

    return {
        "type": "live_update",
        "live_count": live_count,
        "ticker": ticker,
    }
