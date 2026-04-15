# tests/test_match_room_ws.py
"""
Match room WebSocket consumer tests — structure, action dispatch,
presence helpers, chat history, and error handling.

Tests MatchConsumer class without requiring a running channel layer.
"""
import asyncio
import json
import time
from datetime import timedelta
from types import SimpleNamespace
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from django.utils import timezone


class TestMatchConsumerStructure:
    """Verify MatchConsumer class structure and inheritance."""

    def test_consumer_class_importable(self):
        from apps.match_engine.consumers import MatchConsumer
        assert MatchConsumer is not None

    def test_consumer_is_async_json(self):
        from apps.match_engine.consumers import MatchConsumer
        from channels.generic.websocket import AsyncJsonWebsocketConsumer
        assert issubclass(MatchConsumer, AsyncJsonWebsocketConsumer)

    def test_consumer_has_lifecycle_methods(self):
        from apps.match_engine.consumers import MatchConsumer
        assert hasattr(MatchConsumer, 'connect')
        assert hasattr(MatchConsumer, 'disconnect')
        assert hasattr(MatchConsumer, 'receive_json')

    def test_heartbeat_constants_are_reasonable(self):
        from apps.match_engine.consumers import MatchConsumer
        assert MatchConsumer.HEARTBEAT_INTERVAL > 0
        assert MatchConsumer.HEARTBEAT_INTERVAL <= 60
        assert MatchConsumer.HEARTBEAT_TIMEOUT > MatchConsumer.HEARTBEAT_INTERVAL
        assert MatchConsumer.HEARTBEAT_TIMEOUT <= 300

    def test_presence_stale_seconds_defined(self):
        from apps.match_engine.consumers import MatchConsumer
        assert MatchConsumer.PRESENCE_STALE_SECONDS > 0
        assert MatchConsumer.PRESENCE_STALE_SECONDS <= 120

    def test_consumer_has_direct_broadcast(self):
        from apps.match_engine.consumers import MatchConsumer
        assert hasattr(MatchConsumer, 'direct_broadcast')

    def test_consumer_has_presence_methods(self):
        from apps.match_engine.consumers import MatchConsumer
        consumer = MatchConsumer()
        has_register = hasattr(consumer, '_register_presence')
        has_remove = hasattr(consumer, '_unregister_presence')
        has_broadcast = hasattr(consumer, '_broadcast_presence')
        assert has_register, "Missing _register_presence"
        assert has_remove, "Missing _unregister_presence"
        assert has_broadcast, "Missing _broadcast_presence"

    def test_consumer_has_chat_methods(self):
        from apps.match_engine.consumers import MatchConsumer
        consumer = MatchConsumer()
        has_get_history = hasattr(consumer, '_get_chat_history')
        assert has_get_history, "Missing _get_chat_history"

    def test_consumer_has_voice_link_method(self):
        from apps.match_engine.consumers import MatchConsumer
        consumer = MatchConsumer()
        assert hasattr(consumer, '_get_voice_link')

    def test_allowed_origins_method_exists(self):
        from apps.match_engine.consumers import MatchConsumer
        assert hasattr(MatchConsumer, 'get_allowed_origins')


class TestMatchConsumerMessageTypes:
    """Verify that MatchConsumer handles known message types."""

    def _get_consumer(self):
        from apps.match_engine.consumers import MatchConsumer
        consumer = MatchConsumer()
        consumer.match_id = 42
        consumer.tournament_id = 1
        consumer.user = MagicMock(id=5, username="testplayer")
        consumer.side = 1
        consumer.is_participant = True
        consumer.send_json = AsyncMock()
        consumer.last_pong_time = asyncio.get_event_loop().time()
        return consumer

    @pytest.mark.asyncio
    async def test_receive_json_requires_type_field(self):
        consumer = self._get_consumer()
        await consumer.receive_json({})
        consumer.send_json.assert_called_once()
        response = consumer.send_json.call_args[0][0]
        assert response["type"] == "error"
        assert response["code"] == "invalid_schema"

    @pytest.mark.asyncio
    async def test_ping_returns_pong(self):
        consumer = self._get_consumer()
        await consumer.receive_json({"type": "ping", "timestamp": 1234})
        consumer.send_json.assert_called_once()
        response = consumer.send_json.call_args[0][0]
        assert response["type"] == "pong"
        assert response["timestamp"] == 1234

    @pytest.mark.asyncio
    async def test_pong_updates_last_pong_time(self):
        consumer = self._get_consumer()
        consumer._register_presence = AsyncMock()
        old_time = consumer.last_pong_time
        await consumer.receive_json({"type": "pong"})
        assert consumer.last_pong_time >= old_time
        consumer._register_presence.assert_called_once_with(status="online")

    @pytest.mark.asyncio
    async def test_subscribe_returns_subscribed(self):
        consumer = self._get_consumer()
        consumer._broadcast_presence = AsyncMock()
        consumer._build_presence_snapshot = MagicMock(return_value={})
        consumer._get_chat_history = AsyncMock(return_value=[])
        consumer._get_voice_link = AsyncMock(return_value=None)
        await consumer.receive_json({"type": "subscribe"})
        calls = consumer.send_json.call_args_list
        first_response = calls[0][0][0]
        assert first_response["type"] == "subscribed"
        assert first_response["data"]["match_id"] == 42

    @pytest.mark.asyncio
    async def test_unsupported_type_returns_error(self):
        consumer = self._get_consumer()
        consumer._register_presence = AsyncMock()
        await consumer.receive_json({"type": "unknown_action_xyz"})
        found_error = False
        for call in consumer.send_json.call_args_list:
            response = call[0][0]
            if response.get("type") == "error" and response.get("code") == "unsupported_message_type":
                found_error = True
                break
        assert found_error, "Expected unsupported_message_type error"


class TestMemoryPresenceFallback:
    """Test in-memory presence store (used when Redis is unavailable)."""

    def test_memory_presence_set_and_scan(self):
        from apps.match_engine.consumers import (
            _memory_presence_set,
            _memory_presence_scan,
            _memory_presence,
        )
        key = "presence:match:99:user:5"
        value = json.dumps({"user_id": 5, "side": 1, "status": "online"})
        _memory_presence_set(key, value, ttl=60)
        results = _memory_presence_scan("presence:match:99:user:*")
        assert len(results) >= 1
        found = any(k == key for k, v in results)
        assert found
        # Cleanup
        _memory_presence.pop(key, None)

    def test_memory_presence_del(self):
        from apps.match_engine.consumers import (
            _memory_presence_set,
            _memory_presence_del,
            _memory_presence_scan,
            _memory_presence,
        )
        key = "presence:match:100:user:7"
        _memory_presence_set(key, '{"user_id":7}', ttl=60)
        _memory_presence_del(key)
        results = _memory_presence_scan("presence:match:100:user:*")
        found = any(k == key for k, v in results)
        assert not found

    def test_memory_presence_expired_entries_cleaned(self):
        from apps.match_engine.consumers import (
            _memory_presence_set,
            _memory_presence_scan,
            _memory_presence,
        )
        key = "presence:match:101:user:8"
        _memory_presence_set(key, '{"user_id":8}', ttl=0)
        # Force expiry by setting expires in the past
        _memory_presence[key]["expires"] = time.monotonic() - 1
        results = _memory_presence_scan("presence:match:101:user:*")
        found = any(k == key for k, v in results)
        assert not found


class TestGetLivePresenceSync:
    """Test synchronous presence helper."""

    def test_returns_two_sides_with_defaults(self):
        from apps.match_engine.consumers import get_live_presence_sync
        result = get_live_presence_sync(99999)
        assert "1" in result
        assert "2" in result
        assert result["1"]["online"] is False
        assert result["2"]["online"] is False
        assert result["1"]["status"] == "offline"

    def test_returns_dict_structure(self):
        from apps.match_engine.consumers import get_live_presence_sync
        result = get_live_presence_sync(99999)
        for side in ("1", "2"):
            assert "online" in result[side]
            assert "status" in result[side]
            assert "user_id" in result[side]
            assert "username" in result[side]


class TestGlobalMatchClientRegistry:
    """Test the in-process client registry for direct broadcast."""

    def test_registry_is_dict(self):
        from apps.match_engine.consumers import _global_match_clients
        assert isinstance(_global_match_clients, dict)

    def test_direct_broadcast_method_exists(self):
        from apps.match_engine.consumers import MatchConsumer
        consumer = MatchConsumer()
        assert asyncio.iscoroutinefunction(consumer.direct_broadcast)


class TestMatchConsumerLobbyWindowGate:
    """Validate WS connect uses canonical lobby timing gate for participants."""

    def _build_consumer(self, user_id=101, username="player-one"):
        from apps.match_engine.consumers import MatchConsumer

        consumer = MatchConsumer()
        consumer.scope = {
            "url_route": {"kwargs": {"match_id": "42"}},
            "user": SimpleNamespace(
                id=user_id,
                username=username,
                is_authenticated=True,
            ),
            "query_string": b"",
            "headers": [],
            "session": {},
        }
        consumer.channel_layer = SimpleNamespace(
            group_add=AsyncMock(),
            group_discard=AsyncMock(),
        )
        consumer.channel_name = "test-channel"
        consumer.accept = AsyncMock()
        consumer.close = AsyncMock()
        consumer.send_json = AsyncMock()
        consumer._register_presence = AsyncMock()
        consumer._broadcast_presence = AsyncMock()
        consumer._build_presence_snapshot = MagicMock(return_value={"1": {}, "2": {}})
        consumer._heartbeat_loop = AsyncMock(return_value=None)
        return consumer

    @pytest.mark.asyncio
    async def test_connect_rejects_participant_before_lobby_window(self, monkeypatch):
        import apps.match_engine.consumers as consumers_module
        from apps.tournaments.security import TournamentRole

        consumer = self._build_consumer(user_id=101)
        consumer._get_match = AsyncMock(
            return_value=SimpleNamespace(
                id=42,
                tournament_id=77,
                state="scheduled",
                participant1_id=101,
                participant2_id=202,
                participant1_name="P1",
                participant2_name="P2",
                scheduled_time=timezone.now() + timedelta(hours=2),
                lobby_info={},
            )
        )
        monkeypatch.setattr(
            consumers_module,
            "get_user_tournament_role",
            lambda _user: TournamentRole.PLAYER,
        )

        await consumer.connect()

        consumer.close.assert_awaited_with(code=4403)
        consumer.accept.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_rejects_participant_after_lobby_window(self, monkeypatch):
        import apps.match_engine.consumers as consumers_module
        from apps.tournaments.security import TournamentRole

        consumer = self._build_consumer(user_id=101)
        consumer._get_match = AsyncMock(
            return_value=SimpleNamespace(
                id=42,
                tournament_id=77,
                state="scheduled",
                participant1_id=101,
                participant2_id=202,
                participant1_name="P1",
                participant2_name="P2",
                scheduled_time=timezone.now() - timedelta(minutes=20),
                lobby_info={},
            )
        )
        monkeypatch.setattr(
            consumers_module,
            "get_user_tournament_role",
            lambda _user: TournamentRole.PLAYER,
        )

        await consumer.connect()

        consumer.close.assert_awaited_with(code=4403)
        consumer.accept.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_allows_participant_in_live_reentry(self, monkeypatch):
        import apps.match_engine.consumers as consumers_module
        from apps.tournaments.security import TournamentRole

        consumer = self._build_consumer(user_id=101)
        consumer._get_match = AsyncMock(
            return_value=SimpleNamespace(
                id=42,
                tournament_id=77,
                state="live",
                participant1_id=101,
                participant2_id=202,
                participant1_name="P1",
                participant2_name="P2",
                scheduled_time=timezone.now() - timedelta(hours=4),
                lobby_info={},
            )
        )
        monkeypatch.setattr(
            consumers_module,
            "get_user_tournament_role",
            lambda _user: TournamentRole.PLAYER,
        )

        await consumer.connect()

        consumer.accept.assert_awaited_once()
        consumer.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_treats_organizer_participant_as_participant_without_admin_mode(self, monkeypatch):
        import apps.match_engine.consumers as consumers_module
        from apps.tournaments.security import TournamentRole

        consumer = self._build_consumer(user_id=101, username="organizer-player")
        consumer._get_match = AsyncMock(
            return_value=SimpleNamespace(
                id=42,
                tournament_id=77,
                state="scheduled",
                participant1_id=101,
                participant2_id=202,
                participant1_name="P1",
                participant2_name="P2",
                scheduled_time=timezone.now() + timedelta(hours=2),
                lobby_info={},
            )
        )
        monkeypatch.setattr(
            consumers_module,
            "get_user_tournament_role",
            lambda _user: TournamentRole.ORGANIZER,
        )

        await consumer.connect()

        consumer.close.assert_awaited_with(code=4403)
        consumer.accept.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_denies_organizer_without_toc_admin_mode(self, monkeypatch):
        import apps.match_engine.consumers as consumers_module
        from apps.tournaments.security import TournamentRole

        consumer = self._build_consumer(user_id=999, username="organizer")
        consumer._get_match = AsyncMock(
            return_value=SimpleNamespace(
                id=42,
                tournament_id=77,
                state="scheduled",
                participant1_id=101,
                participant2_id=202,
                participant1_name="P1",
                participant2_name="P2",
                scheduled_time=timezone.now() + timedelta(hours=2),
                lobby_info={},
            )
        )
        monkeypatch.setattr(
            consumers_module,
            "get_user_tournament_role",
            lambda _user: TournamentRole.ORGANIZER,
        )

        await consumer.connect()

        consumer.close.assert_awaited_with(code=4403)
        consumer.accept.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_allows_toc_authorized_admin_mode(self, monkeypatch):
        import apps.match_engine.consumers as consumers_module
        from apps.tournaments.security import TournamentRole

        consumer = self._build_consumer(user_id=999, username="organizer")
        consumer.scope["query_string"] = b"admin=1&admin_token=valid-token"
        consumer._get_match = AsyncMock(
            return_value=SimpleNamespace(
                id=42,
                tournament_id=77,
                state="scheduled",
                participant1_id=101,
                participant2_id=202,
                participant1_name="P1",
                participant2_name="P2",
                scheduled_time=timezone.now() + timedelta(hours=2),
                lobby_info={},
            )
        )
        monkeypatch.setattr(
            consumers_module,
            "get_user_tournament_role",
            lambda _user: TournamentRole.ORGANIZER,
        )
        monkeypatch.setattr(
            consumers_module,
            "validate_match_room_admin_token",
            lambda _session, **_kwargs: True,
        )

        await consumer.connect()

        consumer.accept.assert_awaited_once()
        consumer.close.assert_not_awaited()
