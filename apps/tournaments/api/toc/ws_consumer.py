"""
TOC Sprint 11 — WebSocket Consumer
====================================
S11-B3  WebSocket consumer for TOC real-time updates.
S11-B4  Event dispatch handler.

Connects at: ws/toc/<slug>/

Requires Django Channels to be installed and configured.
Falls back gracefully if Channels is not available.
"""

import json
import logging

logger = logging.getLogger(__name__)

try:
    from channels.generic.websocket import AsyncJsonWebsocketConsumer

    class TOCConsumer(AsyncJsonWebsocketConsumer):
        """
        WebSocket consumer for TOC real-time updates.

        Group name: toc_<slug>

        Incoming messages (from client):
            - {"type": "ping"}

        Outgoing messages (from server → group_send):
            - {"type": "toc.event", "event_type": "...", "payload": {...}}
        """

        async def connect(self):
            self.slug = self.scope["url_route"]["kwargs"]["slug"]
            self.group_name = f"toc_{self.slug}"

            # Join the tournament group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name,
            )
            await self.accept()
            await self.send_json({
                "type": "connected",
                "slug": self.slug,
                "message": "TOC real-time connected",
            })

        async def disconnect(self, code):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

        async def receive_json(self, content):
            msg_type = content.get("type", "")

            if msg_type == "ping":
                await self.send_json({"type": "pong"})

        # ── Group event handlers ──

        async def toc_event(self, event):
            """Handle toc.event messages dispatched to the group."""
            await self.send_json({
                "type": "event",
                "event_type": event.get("event_type", ""),
                "payload": event.get("payload", {}),
            })

except ImportError:
    # Django Channels not installed — provide a no-op placeholder
    class TOCConsumer:
        """Placeholder when Django Channels is not available."""

        def __init__(self, *args, **kwargs):
            pass

        def as_asgi(cls):
            raise NotImplementedError(
                "Django Channels is required for WebSocket support. "
                "Install with: pip install channels channels-redis"
            )
