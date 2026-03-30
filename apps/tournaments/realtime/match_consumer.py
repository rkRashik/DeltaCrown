"""
WebSocket consumer for match-specific realtime updates.

Phase 9.3 rebuild goals:
- Preserve existing tested handshake/heartbeat/error semantics.
- Keep core event relay behavior stable.
- Add explicit participant presence snapshots so the room waiting gate can be
  driven directly by socket state.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.tournaments.security import TournamentRole, get_user_tournament_role

logger = logging.getLogger(__name__)


class MatchConsumer(AsyncJsonWebsocketConsumer):
    """Realtime consumer for a single match room."""

    HEARTBEAT_INTERVAL = 25
    HEARTBEAT_TIMEOUT = 50
    PRESENCE_STALE_SECONDS = 45

    # In-process presence registry per room. Keys:
    # - room_group_name -> {channel_name -> presence_row}
    _presence_registry: Dict[str, Dict[str, Dict[str, Any]]] = {}

    @staticmethod
    def get_allowed_origins() -> Optional[list]:
        origins = getattr(settings, "WS_ALLOWED_ORIGINS", None)
        if origins:
            return [o.strip() for o in origins.split(",") if o.strip()]
        return None

    async def connect(self):
        self.match_id = self.scope.get("url_route", {}).get("kwargs", {}).get("match_id")
        if not self.match_id:
            logger.warning("WebSocket connection attempted without match_id")
            await self.close(code=4000)
            return

        try:
            self.match_id = int(self.match_id)
        except (TypeError, ValueError):
            logger.warning("WebSocket connection attempted with invalid match_id", extra={"match_id": self.match_id})
            await self.close(code=4000)
            return

        self.user = self.scope.get("user", AnonymousUser())
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            logger.warning("Unauthenticated WebSocket connection attempt", extra={"match_id": self.match_id})
            await self.close(code=4001)
            return

        from channels.db import database_sync_to_async

        match = await self._get_match(self.match_id)
        if not match:
            logger.warning(
                "WebSocket connection attempted for missing match",
                extra={"match_id": self.match_id, "user_id": self.user.id},
            )
            await self.close(code=4004)
            return

        self.tournament_id = match.tournament_id
        self.user_role = await database_sync_to_async(get_user_tournament_role)(self.user)

        self.is_participant = self.user.id in [match.participant1_id, match.participant2_id]
        self.participant_side = None
        if self.user.id == match.participant1_id:
            self.participant_side = 1
        elif self.user.id == match.participant2_id:
            self.participant_side = 2

        if not self.is_participant:
            try:
                from apps.organizations.models import TeamMembership

                user_team_ids = await database_sync_to_async(
                    lambda: set(
                        TeamMembership.objects.filter(
                            user=self.user,
                            status=TeamMembership.Status.ACTIVE,
                        ).values_list("team_id", flat=True)
                    )
                )()
                if match.participant1_id in user_team_ids:
                    self.is_participant = True
                    self.participant_side = 1
                elif match.participant2_id in user_team_ids:
                    self.is_participant = True
                    self.participant_side = 2
            except Exception:
                logger.exception(
                    "Failed resolving team participant side",
                    extra={"match_id": self.match_id, "user_id": self.user.id},
                )

        allowed_origins = self.get_allowed_origins()
        if allowed_origins:
            origin = self._get_origin()
            if origin and origin not in allowed_origins:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "invalid_origin",
                        "message": "Connection rejected: invalid origin",
                    }
                )
                await self.close(code=4003)
                return

        self.room_group_name = f"match_{self.match_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        self.last_pong_time = asyncio.get_event_loop().time()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        await self.send_json(
            {
                "type": "connection_established",
                "data": {
                    "match_id": self.match_id,
                    "tournament_id": self.tournament_id,
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "role": self.user_role.value,
                    "is_participant": self.is_participant,
                    "participant_side": self.participant_side,
                    "message": f"Connected to match {self.match_id} updates",
                    "heartbeat_interval": self.HEARTBEAT_INTERVAL,
                },
            }
        )

        await self._register_presence(status="online")
        await self._broadcast_presence()

        logger.info(
            "Match WebSocket connected",
            extra={
                "match_id": self.match_id,
                "user_id": self.user.id,
                "role": self.user_role.value,
                "is_participant": self.is_participant,
                "participant_side": self.participant_side,
            },
        )

    async def disconnect(self, close_code):
        if hasattr(self, "heartbeat_task"):
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        await self._unregister_presence()
        await self._broadcast_presence()

        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        logger.info(
            "Match WebSocket disconnected",
            extra={
                "match_id": getattr(self, "match_id", None),
                "user_id": getattr(getattr(self, "user", None), "id", None),
                "close_code": close_code,
            },
        )

    # ---------------------------------------------------------------------
    # Group event handlers
    # ---------------------------------------------------------------------

    async def score_updated(self, event: Dict[str, Any]):
        await self.send_json({"type": "score_updated", "data": event.get("data", {})})

    async def match_completed(self, event: Dict[str, Any]):
        await self.send_json({"type": "match_completed", "data": event.get("data", {})})

    async def dispute_created(self, event: Dict[str, Any]):
        await self.send_json({"type": "dispute_created", "data": event.get("data", {})})

    async def match_started(self, event: Dict[str, Any]):
        await self.send_json({"type": "match_started", "data": event.get("data", {})})

    async def match_state_changed(self, event: Dict[str, Any]):
        await self.send_json({"type": "match_state_changed", "data": event.get("data", {})})

    async def match_room_event(self, event: Dict[str, Any]):
        await self.send_json({"type": "match_room_event", "data": event.get("data", {})})

    async def match_chat_event(self, event: Dict[str, Any]):
        await self.send_json({"type": "match_chat", "data": event.get("data", {})})

    async def match_presence_event(self, event: Dict[str, Any]):
        await self.send_json({"type": "match_presence", "data": event.get("data", {})})

    # ---------------------------------------------------------------------
    # Client message handling
    # ---------------------------------------------------------------------

    async def receive_json(self, content: Dict[str, Any], **kwargs):
        if "type" not in content:
            await self.send_json(
                {
                    "type": "error",
                    "code": "invalid_schema",
                    "message": 'Message must include "type" field',
                }
            )
            return

        message_type = content["type"]

        if message_type == "pong":
            self.last_pong_time = asyncio.get_event_loop().time()
            await self._register_presence(status="online")
            return

        if message_type == "ping":
            await self.send_json({"type": "pong", "timestamp": content.get("timestamp")})
            return

        if message_type == "subscribe":
            await self.send_json(
                {
                    "type": "subscribed",
                    "data": {
                        "match_id": self.match_id,
                        "tournament_id": self.tournament_id,
                        "message": "Successfully subscribed to match updates",
                    },
                }
            )
            await self._broadcast_presence()
            return

        if message_type == "presence_ping":
            status = str(content.get("status") or "online").strip().lower()
            if status not in {"online", "away"}:
                status = "online"
            await self._register_presence(status=status)
            await self._broadcast_presence()
            await self.send_json({"type": "presence_synced", "data": {"status": status}})
            return

        if message_type == "chat_message":
            text = str(content.get("text") or "").strip()
            if not text:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "chat_message_empty",
                        "message": "Chat message cannot be empty.",
                    }
                )
                return

            if len(text) > 400:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "chat_message_too_long",
                        "message": "Chat message cannot exceed 400 characters.",
                    }
                )
                return

            can_chat = self.is_participant or self.user_role in (TournamentRole.ORGANIZER, TournamentRole.ADMIN)
            if not can_chat:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "chat_forbidden",
                        "message": "You are not allowed to send chat messages in this room.",
                    }
                )
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "match_chat_event",
                    "data": {
                        "message_id": f"{self.match_id}:{self.user.id}:{int(timezone.now().timestamp() * 1000)}",
                        "match_id": self.match_id,
                        "user_id": self.user.id,
                        "username": self.user.username,
                        "side": self.participant_side,
                        "is_staff": bool(self.user_role in (TournamentRole.ORGANIZER, TournamentRole.ADMIN)),
                        "text": text,
                        "timestamp": timezone.now().isoformat(),
                    },
                },
            )
            return

        await self.send_json(
            {
                "type": "error",
                "code": "unsupported_message_type",
                "message": f'Message type "{message_type}" not supported',
            }
        )

    # ---------------------------------------------------------------------
    # Heartbeat loop
    # ---------------------------------------------------------------------

    async def _heartbeat_loop(self):
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)

                current_time = asyncio.get_event_loop().time()
                time_since_pong = current_time - self.last_pong_time
                if time_since_pong > self.HEARTBEAT_TIMEOUT:
                    logger.warning(
                        "Heartbeat timeout",
                        extra={
                            "match_id": getattr(self, "match_id", None),
                            "user_id": getattr(getattr(self, "user", None), "id", None),
                            "time_since_pong": time_since_pong,
                        },
                    )
                    await self.close(code=4004)
                    return

                await self.send_json({"type": "ping", "timestamp": current_time})
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception(
                "Heartbeat loop crashed",
                extra={
                    "match_id": getattr(self, "match_id", None),
                    "user_id": getattr(getattr(self, "user", None), "id", None),
                },
            )

    # ---------------------------------------------------------------------
    # Presence helpers
    # ---------------------------------------------------------------------

    def _get_room_presence(self) -> Dict[str, Dict[str, Any]]:
        if not hasattr(self, "room_group_name"):
            return {}
        return self._presence_registry.setdefault(self.room_group_name, {})

    async def _register_presence(self, status: str = "online"):
        if not getattr(self, "is_participant", False):
            return
        if getattr(self, "participant_side", None) not in (1, 2):
            return
        room_presence = self._get_room_presence()
        room_presence[self.channel_name] = {
            "user_id": self.user.id,
            "username": self.user.username,
            "side": int(self.participant_side),
            "status": status if status in {"online", "away"} else "online",
            "last_seen": timezone.now().isoformat(),
        }

    async def _unregister_presence(self):
        if not hasattr(self, "room_group_name"):
            return
        room_presence = self._presence_registry.get(self.room_group_name)
        if not room_presence:
            return
        room_presence.pop(self.channel_name, None)
        if not room_presence:
            self._presence_registry.pop(self.room_group_name, None)

    def _build_presence_snapshot(self) -> Dict[str, Any]:
        room_presence = self._presence_registry.get(getattr(self, "room_group_name", ""), {})
        now = timezone.now()

        sides: Dict[str, Dict[str, Any]] = {
            "1": {"online": False, "status": "offline", "user_id": None, "username": None},
            "2": {"online": False, "status": "offline", "user_id": None, "username": None},
        }

        for row in room_presence.values():
            side = row.get("side")
            if side not in (1, 2):
                continue
            last_seen = parse_datetime(str(row.get("last_seen") or ""))
            if not last_seen:
                continue
            try:
                fresh = (now - last_seen).total_seconds() <= self.PRESENCE_STALE_SECONDS
            except Exception:
                fresh = False
            if not fresh:
                continue

            side_key = str(side)
            status = str(row.get("status") or "online")
            sides[side_key]["online"] = True
            sides[side_key]["status"] = "away" if status == "away" else "online"
            sides[side_key]["user_id"] = row.get("user_id")
            sides[side_key]["username"] = row.get("username")

        return {
            "match_id": getattr(self, "match_id", None),
            "sides": sides,
            "both_online": bool(sides["1"]["online"] and sides["2"]["online"]),
            "updated_at": timezone.now().isoformat(),
        }

    async def _broadcast_presence(self):
        if not hasattr(self, "room_group_name"):
            return
        snapshot = self._build_presence_snapshot()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "match_presence_event",
                "data": snapshot,
            },
        )

    # ---------------------------------------------------------------------
    # Misc helpers
    # ---------------------------------------------------------------------

    def _get_origin(self) -> Optional[str]:
        headers = dict(self.scope.get("headers", []))
        origin = headers.get(b"origin")
        if origin:
            return origin.decode("utf-8")
        return None

    @staticmethod
    async def _get_match(match_id: int):
        from channels.db import database_sync_to_async
        from apps.tournaments.models import Match

        @database_sync_to_async
        def get_match_sync():
            return Match.objects.filter(id=match_id).first()

        return await get_match_sync()


def parse_datetime(value: str):
    """Tiny wrapper to keep parsing local and defensive."""
    from django.utils.dateparse import parse_datetime as django_parse_datetime

    return django_parse_datetime(value)
