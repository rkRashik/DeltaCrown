"""
WebSocket consumer for match-specific realtime updates.

Phase 9.3 rebuild goals:
- Preserve existing tested handshake/heartbeat/error semantics.
- Keep core event relay behavior stable.
- Add explicit participant presence snapshots so the room waiting gate can be
  driven directly by socket state.

Canonical location: apps.match_engine.consumers (Phase 6 extraction).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.tournaments.security import TournamentRole, get_user_tournament_role

logger = logging.getLogger(__name__)


def _get_redis_presence():
    """Return an async Redis client for presence (DB 2, or same as REDIS_URL).

    Falls back to None when Redis is unavailable (dev without Redis).
    Uses a shared connection pool to avoid creating a new TCP connection per
    operation.  The pool is lazily created once and cached on the module.
    """
    import os

    try:
        import redis.asyncio as aioredis
    except ImportError:
        return None
    base_url = os.getenv("REDIS_URL", "")
    if not base_url:
        return None

    global _redis_presence_pool  # noqa: PLW0603
    if _redis_presence_pool is None:
        try:
            from deltacrown.settings import _redis_url_with_db
            url = _redis_url_with_db(base_url, 2)
            _redis_presence_pool = aioredis.ConnectionPool.from_url(
                url, decode_responses=True, max_connections=8,
            )
        except Exception:
            logger.debug("Redis presence pool creation failed — presence disabled")
            return None

    try:
        return aioredis.Redis(connection_pool=_redis_presence_pool)
    except Exception:
        return None


# Module-level connection pool (lazily initialised by _get_redis_presence).
_redis_presence_pool = None


class MatchConsumer(AsyncJsonWebsocketConsumer):
    """Realtime consumer for a single match room."""

    HEARTBEAT_INTERVAL = 25
    HEARTBEAT_TIMEOUT = 50
    PRESENCE_STALE_SECONDS = 45

    # Presence now lives in Redis (Phase 1 migration).
    # Key pattern: presence:match:{match_id}:user:{user_id}
    # Value: JSON blob, TTL = HEARTBEAT_TIMEOUT seconds.

    @staticmethod
    def get_allowed_origins() -> Optional[list]:
        origins = getattr(settings, "WS_ALLOWED_ORIGINS", None)
        if origins:
            return [o.strip() for o in origins.split(",") if o.strip()]
        return None

    async def connect(self) -> None:
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
        self.is_official_staff = bool(self.user_role in (TournamentRole.ORGANIZER, TournamentRole.ADMIN))
        self.chat_display_name = "Organizer" if self.is_official_staff else self.user.username
        self.chat_avatar_url = await self._get_user_avatar_url(self.user.id)

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
        self._last_chat_ts = 0.0  # monotonic timestamp of last chat message

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

    async def disconnect(self, close_code) -> None:
        if hasattr(self, "heartbeat_task"):
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except (asyncio.CancelledError, Exception):
                pass

        try:
            await self._unregister_presence()
        except (asyncio.CancelledError, Exception):
            logger.debug(
                "Presence unregister suppressed during disconnect",
                extra={"match_id": getattr(self, "match_id", None)},
            )

        try:
            await self._broadcast_presence()
        except (asyncio.CancelledError, Exception):
            logger.debug(
                "Presence broadcast suppressed during disconnect",
                extra={"match_id": getattr(self, "match_id", None)},
            )

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

    async def score_updated(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "score_updated", "data": event.get("data", {})})

    async def match_completed(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "match_completed", "data": event.get("data", {})})

    async def dispute_created(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "dispute_created", "data": event.get("data", {})})

    async def match_started(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "match_started", "data": event.get("data", {})})

    async def match_state_changed(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "match_state_changed", "data": event.get("data", {})})

    async def match_room_event(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "match_room_event", "data": event.get("data", {})})

    async def match_chat_event(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "match_chat", "data": event.get("data", {})})

    async def match_presence_event(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "match_presence", "data": event.get("data", {})})

    # ---------------------------------------------------------------------
    # Client message handling
    # ---------------------------------------------------------------------

    async def receive_json(self, content: Dict[str, Any], **kwargs) -> None:
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
            now_mono = asyncio.get_event_loop().time()
            if now_mono - self._last_chat_ts < 2.0:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "rate_limited",
                        "message": "You are sending messages too quickly. Please wait.",
                    }
                )
                return

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
                        "display_name": self.chat_display_name,
                        "side": self.participant_side,
                        "is_staff": self.is_official_staff,
                        "persona": "organizer" if self.is_official_staff else "participant",
                        "avatar_url": self.chat_avatar_url,
                        "text": text,
                        "timestamp": timezone.now().isoformat(),
                    },
                },
            )
            self._last_chat_ts = now_mono
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

    async def _heartbeat_loop(self) -> None:
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
    # Presence helpers  (Redis-backed — Phase 1)
    # ---------------------------------------------------------------------

    @staticmethod
    def _presence_key(match_id: int, user_id: int) -> str:
        return f"presence:match:{match_id}:user:{user_id}"

    @staticmethod
    def _presence_pattern(match_id: int) -> str:
        return f"presence:match:{match_id}:user:*"

    async def _register_presence(self, status: str = "online") -> None:
        if not getattr(self, "is_participant", False):
            return
        if getattr(self, "participant_side", None) not in (1, 2):
            return
        rds = _get_redis_presence()
        if rds is None:
            return
        key = self._presence_key(self.match_id, self.user.id)
        payload = json.dumps({
            "user_id": self.user.id,
            "username": self.user.username,
            "side": int(self.participant_side),
            "status": status if status in {"online", "away"} else "online",
            "last_seen": timezone.now().isoformat(),
        })
        try:
            await rds.setex(key, self.HEARTBEAT_TIMEOUT, payload)
        except Exception:
            logger.debug("Redis presence SET failed", extra={"match_id": self.match_id, "user_id": self.user.id})

    async def _unregister_presence(self) -> None:
        match_id = getattr(self, "match_id", None)
        user = getattr(self, "user", None)
        if not match_id or not user or not getattr(user, "id", None):
            return
        rds = _get_redis_presence()
        if rds is None:
            return
        key = self._presence_key(match_id, user.id)
        try:
            await rds.delete(key)
        except Exception:
            logger.debug("Redis presence DEL failed", extra={"match_id": match_id, "user_id": user.id})

    async def _build_presence_snapshot(self) -> Dict[str, Any]:
        match_id = getattr(self, "match_id", None)
        sides: Dict[str, Dict[str, Any]] = {
            "1": {"online": False, "status": "offline", "user_id": None, "username": None},
            "2": {"online": False, "status": "offline", "user_id": None, "username": None},
        }
        if not match_id:
            return {"match_id": None, "sides": sides, "both_online": False, "updated_at": timezone.now().isoformat()}

        rds = _get_redis_presence()
        if rds is None:
            return {"match_id": match_id, "sides": sides, "both_online": False, "updated_at": timezone.now().isoformat()}

        try:
            pattern = self._presence_pattern(match_id)
            cursor = 0
            while True:
                cursor, keys = await rds.scan(cursor=cursor, match=pattern, count=20)
                if keys:
                    values = await rds.mget(*keys)
                    for raw in values:
                        if not raw:
                            continue
                        row = json.loads(raw)
                        side = row.get("side")
                        if side not in (1, 2):
                            continue
                        side_key = str(side)
                        status = str(row.get("status") or "online")
                        sides[side_key]["online"] = True
                        sides[side_key]["status"] = "away" if status == "away" else "online"
                        sides[side_key]["user_id"] = row.get("user_id")
                        sides[side_key]["username"] = row.get("username")
                if cursor == 0:
                    break
        except Exception:
            logger.debug("Redis presence SCAN failed", extra={"match_id": match_id})

        return {
            "match_id": match_id,
            "sides": sides,
            "both_online": bool(sides["1"]["online"] and sides["2"]["online"]),
            "updated_at": timezone.now().isoformat(),
        }

    async def _broadcast_presence(self) -> None:
        if not hasattr(self, "room_group_name"):
            return
        snapshot = await self._build_presence_snapshot()
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

    @staticmethod
    async def _get_user_avatar_url(user_id: int) -> str:
        from django.contrib.auth import get_user_model

        User = get_user_model()

        @database_sync_to_async
        def _resolve() -> str:
            try:
                user = User.objects.select_related("profile").get(pk=user_id)
            except Exception:
                return ""

            profile = getattr(user, "profile", None)
            if not profile:
                return ""

            try:
                avatar_url = profile.get_avatar_url() if hasattr(profile, "get_avatar_url") else ""
            except Exception:
                avatar_url = ""

            if avatar_url:
                return str(avatar_url)

            try:
                if getattr(profile, "avatar", None):
                    return str(profile.avatar.url or "")
            except Exception:
                return ""

            return ""

        return await _resolve()

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
