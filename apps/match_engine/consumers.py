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
                health_check_interval=10,
                socket_connect_timeout=3,
                socket_timeout=3,
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

# In-memory presence fallback when Redis is unavailable (local dev).
# Structure: { "presence:match:{id}:user:{uid}": {"payload": str, "expires": float} }
_memory_presence: dict = {}

# MatchChatMessage is used for persistent chat storage (Phase 8).
# Old _memory_chat_history dict has been removed.


def _memory_presence_set(key: str, value: str, ttl: int) -> None:
    """Store presence in memory with a TTL (seconds)."""
    import time
    _memory_presence[key] = {"payload": value, "expires": time.monotonic() + ttl}


def _memory_presence_del(key: str) -> None:
    """Remove presence from memory store."""
    _memory_presence.pop(key, None)


def _memory_presence_scan(pattern: str):
    """Return list of (key, value) matching a glob pattern from memory store."""
    import fnmatch
    import time
    now = time.monotonic()
    results = []
    expired_keys = []
    for k, v in _memory_presence.items():
        if v["expires"] < now:
            expired_keys.append(k)
            continue
        if fnmatch.fnmatch(k, pattern):
            results.append((k, v["payload"]))
    for k in expired_keys:
        _memory_presence.pop(k, None)
    return results


def get_live_presence_sync(match_id: int) -> dict:
    """Synchronous helper: read live presence from Redis/memory for a match.

    Returns dict like:
        {"1": {"online": True, "status": "online", "user_id": 5, ...},
         "2": {"online": False, "status": "offline", ...}}

    Safe to call from Django views (sync context).
    """
    import json as _json
    pattern = f"presence:match:{match_id}:user:*"
    sides: dict = {
        "1": {"online": False, "status": "offline", "user_id": None, "username": None},
        "2": {"online": False, "status": "offline", "user_id": None, "username": None},
    }

    def _apply(raw: str) -> None:
        try:
            row = _json.loads(raw)
        except (ValueError, TypeError):
            return
        side = row.get("side")
        if side not in (1, 2):
            return
        key = str(side)
        status = str(row.get("status") or "online")
        sides[key]["online"] = True
        sides[key]["status"] = "away" if status == "away" else "online"
        sides[key]["user_id"] = row.get("user_id")
        sides[key]["username"] = row.get("username")

    # 1) Try Redis (production)
    import os
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            import redis as _sync_redis
            from deltacrown.settings import _redis_url_with_db
            url = _redis_url_with_db(redis_url, 2)
            client = _sync_redis.Redis.from_url(
                url, decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor=cursor, match=pattern, count=20)
                if keys:
                    values = client.mget(*keys)
                    for raw in values:
                        if raw:
                            _apply(raw)
                if cursor == 0:
                    break
            return sides
        except Exception:
            pass  # fall through to memory

    # 2) In-memory fallback (local dev without Redis)
    for _key, raw in _memory_presence_scan(pattern):
        _apply(raw)

    return sides


class MatchConsumer(AsyncJsonWebsocketConsumer):
    """Realtime consumer for a single match room."""

    HEARTBEAT_INTERVAL = 30
    HEARTBEAT_TIMEOUT = 90
    PRESENCE_STALE_SECONDS = 60

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
        self.chat_display_name = self.user.username  # Set after side resolution below
        self.chat_avatar_url = None  # Resolved lazily on first chat message

        self.is_participant = self.user.id in [match.participant1_id, match.participant2_id]
        self.participant_side = None
        if self.user.id == match.participant1_id:
            self.participant_side = 1
        elif self.user.id == match.participant2_id:
            self.participant_side = 2

        # Fallback: participant IDs may store Registration.id instead of User.id
        if not self.is_participant:
            try:
                from apps.tournaments.models.registration import Registration

                user_reg_ids = await database_sync_to_async(
                    lambda: set(
                        Registration.objects.filter(
                            user=self.user,
                            tournament_id=match.tournament_id,
                            is_deleted=False,
                        ).values_list("id", flat=True)
                    )
                )()
                if match.participant1_id in user_reg_ids:
                    self.is_participant = True
                    self.participant_side = 1
                elif match.participant2_id in user_reg_ids:
                    self.is_participant = True
                    self.participant_side = 2
            except Exception:
                logger.debug(
                    "Failed resolving registration participant side",
                    extra={"match_id": self.match_id, "user_id": self.user.id},
                )

        # Fallback: team-based tournaments — check TeamMembership
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

        # Display name: use participant name for participants, real username for staff
        if self.is_participant and self.participant_side:
            side_name = match.participant1_name if self.participant_side == 1 else match.participant2_name
            self.chat_display_name = side_name or self.user.username
        elif self.is_official_staff:
            self.chat_display_name = self.user.username

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

        try:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        except Exception as e:
            logger.error(
                "group_add failed — channel layer unreachable: %s",
                e,
                extra={"match_id": self.match_id},
            )
            await self.close(code=1011)
            return
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
        try:
            await self._broadcast_presence()
        except Exception:
            logger.debug(
                "Presence broadcast suppressed during connect",
                extra={"match_id": self.match_id, "user_id": self.user.id},
            )

        # Direct presence delivery — guarantees the connecting client receives
        # the current snapshot even if group_send fails to deliver.
        try:
            snapshot = await self._build_presence_snapshot()
            await self.send_json({"type": "match_presence", "data": snapshot})
        except Exception:
            logger.debug(
                "Direct presence delivery suppressed during connect",
                extra={"match_id": self.match_id, "user_id": self.user.id},
            )

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
            await asyncio.wait_for(self._unregister_presence(), timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            pass

        try:
            await asyncio.wait_for(self._broadcast_presence(), timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            pass

        if hasattr(self, "room_group_name"):
            try:
                await asyncio.wait_for(
                    self.channel_layer.group_discard(self.room_group_name, self.channel_name),
                    timeout=2.0,
                )
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                pass

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
        data = dict(event.get("data", {}))
        # Mark as echo for the original sender so the frontend dedup skips re-render
        user_id = getattr(getattr(self, "user", None), "id", None)
        is_echo = user_id is not None and event.get("sender_user_id") == user_id
        if is_echo:
            data["echo"] = True
        logger.info(
            "match_chat_event relay → user=%s echo=%s sender=%s text_len=%s",
            user_id, is_echo, event.get("sender_user_id"), len(str(data.get("text", ""))),
            extra={"match_id": getattr(self, "match_id", None)},
        )
        try:
            await self.send_json({"type": "match_chat", "data": data})
        except Exception:
            logger.exception(
                "match_chat_event relay failed",
                extra={"match_id": getattr(self, "match_id", None), "user_id": user_id},
            )

    async def match_typing_event(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "typing_indicator", "data": event.get("data", {})})

    async def match_presence_event(self, event: Dict[str, Any]) -> None:
        await self.send_json({"type": "match_presence", "data": event.get("data", {})})

    async def voice_widget_update(self, event: Dict[str, Any]) -> None:
        """Relay voice widget state to the connected client."""
        await self.send_json({"type": "voice_widget_update", "data": event.get("data", {})})

    # ---------------------------------------------------------------------
    # Client message handling
    # ---------------------------------------------------------------------

    async def receive_json(self, content: Dict[str, Any], **kwargs) -> None:
        # Any message from the client proves liveness — prevent heartbeat timeout
        # even if the explicit "pong" frame was lost in transit.
        self.last_pong_time = asyncio.get_event_loop().time()

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
            try:
                await self._broadcast_presence()
            except Exception:
                logger.debug(
                    "Presence broadcast suppressed during subscribe",
                    extra={"match_id": self.match_id, "user_id": self.user.id},
                )
            # Direct presence delivery — guaranteed even if group_send fails
            try:
                snapshot = await self._build_presence_snapshot()
                await self.send_json({"type": "match_presence", "data": snapshot})
            except Exception:
                pass
            # Send chat history so the client can replay messages after connect/refresh
            try:
                history = await self._get_chat_history()
                if history:
                    await self.send_json({"type": "chat_history", "data": {"messages": history}})
            except Exception:
                pass
            # Send current voice widget state (if a link was previously set)
            try:
                vc = await self._get_voice_link()
                if vc:
                    await self.send_json({"type": "voice_widget_update", "data": vc})
            except Exception:
                pass
            return

        if message_type == "presence_ping":
            status = str(content.get("status") or "online").strip().lower()
            if status not in {"online", "away"}:
                status = "online"
            await self._register_presence(status=status)
            try:
                await self._broadcast_presence()
            except Exception:
                logger.debug(
                    "Presence broadcast suppressed during presence_ping",
                    extra={"match_id": self.match_id, "user_id": self.user.id},
                )
            # Always send direct snapshot — guaranteed delivery if group_send fails
            try:
                snapshot = await self._build_presence_snapshot()
                await self.send_json({"type": "match_presence", "data": snapshot})
            except Exception:
                pass
            await self.send_json({"type": "presence_synced", "data": {"status": status}})
            return

        if message_type == "typing_indicator":
            if not self.is_participant:
                return
            typing = bool(content.get("typing", False))
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "match_typing_event",
                        "data": {
                            "user_id": self.user.id,
                            "side": self.participant_side,
                            "typing": typing,
                        },
                    },
                )
            except Exception:
                pass
            return

        if message_type == "chat_message":
            now_mono = asyncio.get_event_loop().time()
            if now_mono - self._last_chat_ts < 0.5:
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

            # Lazily resolve avatar on first chat message
            if self.chat_avatar_url is None:
                try:
                    self.chat_avatar_url = await self._get_user_avatar_url(self.user.id) or ""
                except Exception:
                    self.chat_avatar_url = ""

            is_official_in_chat = self.is_official_staff and not self.is_participant

            # Build msg_data immediately
            msg_data = {
                "message_id": f"msg:{self.match_id}:{self.user.id}:{int(timezone.now().timestamp() * 1000)}",
                "match_id": self.match_id,
                "user_id": self.user.id,
                "username": self.user.username,
                "sender_name": self.chat_display_name, # Critical for UI
                "role": "admin" if is_official_in_chat else ("host" if self.participant_side == 1 else "guest"), # Critical for UI
                "side": self.participant_side or 0,
                "is_official": is_official_in_chat,
                "avatar_url": self.chat_avatar_url or "",
                "message": text, # Critical for UI
                "text": text,
                "msg_type": "chat",
                "timestamp": timezone.now().isoformat(),
            }

            logger.info(
                "Chat message received",
                extra={
                    "match_id": self.match_id,
                    "user_id": self.user.id,
                    "side": self.participant_side,
                    "text_len": len(text),
                },
            )

            # Broadcast to ALL group members (including sender).
            # match_chat_event adds echo:True for the sender so the frontend dedup
            # finds the optimistic bubble and swaps it — no duplicate render.
            logger.info(
                "group_send → group=%s user=%s text_len=%s",
                self.room_group_name, self.user.id, len(text),
                extra={"match_id": self.match_id},
            )
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "match_chat_event",
                        "data": msg_data,
                        "sender_user_id": self.user.id,
                    },
                )
            except Exception as e:
                logger.error(
                    "group_send (chat_message) failed: %s",
                    e,
                    extra={"match_id": self.match_id, "user_id": self.user.id},
                )
            # Persist to DB asynchronously — never block the broadcast path
            asyncio.ensure_future(self._store_chat_message_bg(msg_data))
            self._last_chat_ts = now_mono
            return

        if message_type == "voice_link":
            # Admin-only: set/update the persistent voice channel widget
            if not self.is_official_staff:
                await self.send_json({"type": "error", "code": "forbidden", "message": "Only staff can post voice links."})
                return
            voice_url = str(content.get("url") or "").strip()
            label = str(content.get("label") or "Voice Channel").strip()[:80]
            if not voice_url or len(voice_url) > 500:
                await self.send_json({"type": "error", "code": "invalid_url", "message": "Invalid voice link URL."})
                return

            # Persist to Match.lobby_info for durability across reconnects
            widget_data = {
                "voice_url": voice_url,
                "voice_label": label,
                "set_by": self.user.username,
                "set_at": timezone.now().isoformat(),
            }
            asyncio.ensure_future(self._save_voice_link(widget_data))

            # Broadcast widget update to ALL clients (NOT a chat message)
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "voice_widget_update", "data": widget_data},
                )
            except Exception as e:
                logger.error(
                    "group_send (voice_widget_update) failed: %s",
                    e,
                    extra={"match_id": self.match_id, "user_id": self.user.id},
                )

            # Also post a one-line system chat announcement
            sys_data = {
                "message_id": f"vc:{self.match_id}:{self.user.id}:{int(timezone.now().timestamp() * 1000)}",
                "match_id": self.match_id,
                "user_id": self.user.id,
                "display_name": self.chat_display_name,
                "side": 0,
                "is_official": True,
                "avatar_url": "",
                "text": f"\U0001f50a {self.user.username} linked a voice channel: {label}",
                "msg_type": "system",
                "timestamp": timezone.now().isoformat(),
            }
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "match_chat_event", "data": sys_data, "sender_user_id": self.user.id},
                )
            except Exception:
                pass

            # Fire Discord webhook asynchronously (if configured)
            asyncio.ensure_future(self._fire_discord_webhook(voice_url, label))
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
                    await self.close(code=1000)
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
        key = self._presence_key(self.match_id, self.user.id)
        payload = json.dumps({
            "user_id": self.user.id,
            "username": self.user.username,
            "side": int(self.participant_side),
            "status": status if status in {"online", "away"} else "online",
            "last_seen": timezone.now().isoformat(),
        })
        rds = _get_redis_presence()
        if rds is None:
            _memory_presence_set(key, payload, self.HEARTBEAT_TIMEOUT)
            return
        try:
            await rds.setex(key, self.HEARTBEAT_TIMEOUT, payload)
        except Exception:
            _memory_presence_set(key, payload, self.HEARTBEAT_TIMEOUT)
            logger.debug("Redis presence SET failed, using memory fallback", extra={"match_id": self.match_id, "user_id": self.user.id})

    async def _unregister_presence(self) -> None:
        match_id = getattr(self, "match_id", None)
        user = getattr(self, "user", None)
        if not match_id or not user or not getattr(user, "id", None):
            return
        key = self._presence_key(match_id, user.id)
        rds = _get_redis_presence()
        if rds is None:
            _memory_presence_del(key)
            return
        try:
            await rds.delete(key)
        except Exception:
            _memory_presence_del(key)
            logger.debug("Redis presence DEL failed, using memory fallback", extra={"match_id": match_id, "user_id": user.id})

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
            # In-memory fallback (local dev without Redis)
            pattern = self._presence_pattern(match_id)
            for _key, raw in _memory_presence_scan(pattern):
                try:
                    row = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                side = row.get("side")
                if side not in (1, 2):
                    continue
                side_key = str(side)
                status = str(row.get("status") or "online")
                sides[side_key]["online"] = True
                sides[side_key]["status"] = "away" if status == "away" else "online"
                sides[side_key]["user_id"] = row.get("user_id")
                sides[side_key]["username"] = row.get("username")
            return {
                "match_id": match_id,
                "sides": sides,
                "both_online": bool(sides["1"]["online"] and sides["2"]["online"]),
                "updated_at": timezone.now().isoformat(),
            }

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
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "match_presence_event",
                    "data": snapshot,
                },
            )
        except Exception as e:
            logger.error(
                "group_send (presence) failed: %s",
                e,
                extra={"match_id": self.match_id},
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
            return (
                Match.objects
                .filter(id=match_id)
                .only(
                    "id", "tournament_id", "state",
                    "participant1_id", "participant2_id",
                    "participant1_name", "participant2_name",
                )
                .first()
            )

        return await get_match_sync()

    # ------------------------------------------------------------------
    # Chat persistence (DB-backed — Phase 8, non-blocking)
    # ------------------------------------------------------------------

    async def _store_chat_message_bg(self, msg_data: dict) -> None:
        """Persist a chat message to MatchChatMessage in the background.

        Fire-and-forget via asyncio.ensure_future — never blocks the
        broadcast hot-path.
        """
        from apps.match_engine.models import MatchChatMessage

        @database_sync_to_async
        def _create() -> None:
            MatchChatMessage.objects.create(
                match_id=msg_data.get("match_id"),
                user_id=msg_data.get("user_id") or None,
                display_name=msg_data.get("display_name", ""),
                avatar_url=msg_data.get("avatar_url", ""),
                side=msg_data.get("side", 0),
                text=msg_data.get("text", ""),
                msg_type=msg_data.get("msg_type", "chat"),
                is_official=bool(msg_data.get("is_official", False)),
                extra=msg_data.get("extra") or {},
            )

        try:
            await _create()
        except Exception:
            logger.warning(
                "Background chat persist failed",
                extra={"match_id": msg_data.get("match_id"), "user_id": msg_data.get("user_id")},
            )

    async def _get_chat_history(self, limit: int = 50) -> list:
        """Retrieve the last N chat messages for this match from the DB."""
        from apps.match_engine.models import MatchChatMessage

        @database_sync_to_async
        def _fetch():
            qs = (
                MatchChatMessage.objects
                .filter(match_id=self.match_id)
                .order_by("-created_at")[:limit]
            )
            # Reverse so oldest first (natural chat order)
            return [m.to_ws_dict() for m in reversed(list(qs))]

        return await _fetch()

    # ------------------------------------------------------------------
    # Voice Channel Widget (persistent in lobby_info)
    # ------------------------------------------------------------------

    async def _save_voice_link(self, widget_data: dict) -> None:
        """Save voice channel URL into Match.lobby_info['voice_channel']."""
        from apps.tournaments.models import Match

        @database_sync_to_async
        def _update():
            try:
                match = Match.objects.filter(id=self.match_id).first()
                if match:
                    info = match.lobby_info or {}
                    info["voice_channel"] = widget_data
                    match.lobby_info = info
                    match.save(update_fields=["lobby_info"])
            except Exception:
                logger.warning("Failed saving voice link to lobby_info", extra={"match_id": self.match_id})

        await _update()

    async def _get_voice_link(self) -> Optional[dict]:
        """Read current voice channel from Match.lobby_info."""
        from apps.tournaments.models import Match

        @database_sync_to_async
        def _read():
            match = Match.objects.filter(id=self.match_id).only("lobby_info").first()
            if match and match.lobby_info:
                return match.lobby_info.get("voice_channel")
            return None

        return await _read()

    async def _fire_discord_webhook(self, voice_url: str, label: str) -> None:
        """Fire a lightweight Discord webhook embed (non-blocking, 3s timeout).

        Only fires if DISCORD_WEBHOOK_URL is configured in settings/env.
        """
        import os
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        if not webhook_url:
            return

        try:
            import aiohttp
            payload = {
                "embeds": [{
                    "title": f"\U0001f3ae Match #{self.match_id} — Voice Channel Linked",
                    "description": f"**{label}**\n[Join Voice]({voice_url})",
                    "color": 5793266,  # #5865F2 in decimal
                    "footer": {"text": f"Set by {self.user.username} via DeltaCrown"},
                }]
            }
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status >= 400:
                        logger.warning("Discord webhook failed: HTTP %s", resp.status)
        except ImportError:
            # aiohttp not installed — try synchronous fallback
            try:
                import requests
                payload = {
                    "embeds": [{
                        "title": f"\U0001f3ae Match #{self.match_id} — Voice Channel Linked",
                        "description": f"**{label}**\n[Join Voice]({voice_url})",
                        "color": 5793266,
                        "footer": {"text": f"Set by {self.user.username} via DeltaCrown"},
                    }]
                }

                @database_sync_to_async
                def _post():
                    requests.post(webhook_url, json=payload, timeout=3)

                await _post()
            except Exception:
                logger.debug("Discord webhook (requests fallback) failed")
        except Exception:
            logger.debug("Discord webhook fire-and-forget failed")


def parse_datetime(value: str):
    """Tiny wrapper to keep parsing local and defensive."""
    from django.utils.dateparse import parse_datetime as django_parse_datetime

    return django_parse_datetime(value)
