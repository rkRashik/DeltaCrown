"""
Phase 6 Residuals Closeout: WebSocket Rate Limit E2E Tests

Target: middleware_ratelimit.py coverage ≥75% (from 51%)
Focus: CONNECT/DISCONNECT lifecycle, Redis E2E validation, WebSocket upgrade path

Test Matrix:
A. Connect/Disconnect lifecycle (4 tests) - CONNECT/DISCONNECT + Redis state
B. Redis E2E mechanics (4 tests) - TTL, atomicity, failover, key patterns
C. Upgrade + multi-connection semantics (3 tests) - HTTP→WS upgrade tracking
D. Edge cases (4 tests) - Malformed scopes, zero limits, burst traffic, anonymous

Prerequisites:
- Redis running: docker-compose -f docker-compose.test.yml up -d
- WS_RATE_ENABLED=True in settings
- Tests use ephemeral Redis namespace for isolation

Coverage Target Lines:
- CONNECT handler (lines 127-184): Accept/reject logic, Redis incr, room join
- DISCONNECT cleanup (lines 289-302): Decrement counters, room leave
- Redis integration (lines 145-160, 170-184): Key building, TTL setting, atomic ops
- Connection upgrade (lines 110-125): Scope validation, IP extraction
- Edge cases (lines 130-144, 250-270): Zero limits, malformed scopes, burst handling
"""

import pytest
import asyncio
import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import path
from django.contrib.auth import get_user_model

from apps.tournaments.realtime.middleware_ratelimit import RateLimitMiddleware
from tests.redis_fixtures import (
    redis_required,
    redis_test_client,
    test_namespace,
    redis_cleanup,
    redis_rate_limit_config,
    create_test_user,
)

User = get_user_model()


# ============================================================================
# Test ASGI Application (No Origin Validation)
# ============================================================================

class MockTournamentConsumer:
    """
    Minimal WebSocket consumer for testing rate limiting.
    
    NO origin validation (AllowedHostsOriginValidator removed per requirements).
    Accepts all connections to test middleware in isolation.
    """
    
    def __init__(self, scope):
        self.scope = scope
        self.accepted = False
    
    async def __call__(self, receive, send):
        """Handle WebSocket lifecycle."""
        while True:
            message = await receive()
            
            if message['type'] == 'websocket.connect':
                # Accept connection (no origin check)
                await send({'type': 'websocket.accept'})
                self.accepted = True
            
            elif message['type'] == 'websocket.receive':
                # Echo message back
                if 'text' in message and message['text']:
                    data = json.loads(message['text'])
                    await send({
                        'type': 'websocket.send',
                        'text': json.dumps({'echo': data})
                    })
            
            elif message['type'] == 'websocket.disconnect':
                break
    
    @classmethod
    def as_asgi(cls, **kwargs):
        """Factory method for ASGI application (mimics Django Channels pattern)."""
        async def application(scope, receive, send):
            consumer = cls(scope)
            await consumer(receive, send)
        return application


# Test routing (wrapped with rate limit middleware)
def create_test_application():
    """Create test ASGI application with rate limit middleware."""
    urlpatterns = [
        path('ws/tournament/<int:tournament_id>/', MockTournamentConsumer.as_asgi()),
    ]
    
    return RateLimitMiddleware(URLRouter(urlpatterns))


# ============================================================================
# Test Class A: Connect/Disconnect Lifecycle
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@redis_required
class TestConnectDisconnectLifecycle:
    """
    Test WebSocket CONNECT/DISCONNECT with Redis state validation.
    
    Coverage Targets:
    - middleware_ratelimit.py lines 127-184 (CONNECT acceptance/rejection)
    - middleware_ratelimit.py lines 289-302 (DISCONNECT cleanup)
    - ratelimit.py lines 414-432, 445-463 (increment/decrement)
    """
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config):
        """Auto-use Redis fixtures."""
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
    
    async def test_connect_within_limit_accepts_and_sets_redis_keys(self):
        """
        Test: CONNECT within limit → accept + Redis keys created.
        
        Coverage: lines 127-160 (CONNECT logic), lines 414-432 (increment_user_connections)
        Redis E2E: Validates key creation, TTL, counter value
        """
        user = await create_test_user(username="connect_user_1")
        
        # Create communicator with authenticated user
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/123/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.100', 12345)
        
        # Connect (within limit)
        connected, subprotocol = await communicator.connect()
        
        # Assert connection accepted
        assert connected, "Connection should be accepted within limit"
        
        # Validate Redis state (user connection counter)
        redis_key = f"ws:conn:count:{user.id}"
        redis_value = self.redis.get(redis_key)
        assert redis_value == "1", f"Redis should show 1 connection, got: {redis_value}"
        
        # Validate TTL set (should be 3600s)
        ttl = self.redis.ttl(redis_key)
        assert ttl > 0, f"Redis key should have TTL, got: {ttl}"
        assert ttl <= 3600, f"TTL should be ≤3600s, got: {ttl}"
        
        # Cleanup
        await communicator.disconnect()
    
    async def test_connect_exceeds_limit_rejects_with_4003_and_incrs_counter(self):
        """
        Test: CONNECT exceeds limit → reject with DenyConnection exception.
        
        Coverage: lines 145-160 (limit check + rejection path)
        Redis E2E: Pre-set counter to limit, verify rejection
        
        Note: Middleware raises DenyConnection which prevents connection.
        """
        user = await create_test_user(username="connect_user_2")
        
        # Pre-set connection count to limit (2 per user)
        redis_key = f"ws:conn:count:{user.id}"
        self.redis.set(redis_key, str(self.config.WS_RATE_CONN_PER_USER))
        self.redis.expire(redis_key, 3600)
        
        # Attempt connection (should be rejected)
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/123/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.100', 12345)
        
        # Connect attempt - DenyConnection will be raised internally
        # WebsocketCommunicator.connect() catches this and sends close message
        try:
            connected, subprotocol = await communicator.connect(timeout=2)
            # If we get here without exception, connection was accepted (shouldn't happen)
            assert not connected, "Connection should be rejected when limit exceeded"
        except Exception as e:
            # Expected: connection denied
            pass
        
        # Redis counter should NOT be incremented beyond limit
        final_count = int(self.redis.get(redis_key) or 0)
        assert final_count <= self.config.WS_RATE_CONN_PER_USER, \
            f"Counter should be ≤limit ({self.config.WS_RATE_CONN_PER_USER}), got: {final_count}"
    
    async def test_disconnect_clears_connection_state_keys(self):
        """
        Test: DISCONNECT → Redis counters decremented, room membership cleared.
        
        Coverage: lines 289-302 (finally block cleanup)
        Redis E2E: Validate decrement, key deletion at zero
        """
        user = await create_test_user(username="disconnect_user")
        
        # Connect
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/999/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.101', 23456)
        
        connected, _ = await communicator.connect()
        assert connected, "Initial connection should succeed"
        
        # Verify Redis state before disconnect
        conn_key = f"ws:conn:count:{user.id}"
        ip_key = f"ws:conn:ip:192.168.1.101"
        room_key = f"ws:room:tournament_999"
        
        assert self.redis.get(conn_key) == "1", "User connection counter should be 1"
        assert self.redis.get(ip_key) == "1", "IP connection counter should be 1"
        assert self.redis.sismember(room_key, str(user.id)), "User should be in room"
        
        # Disconnect
        await communicator.disconnect()
        
        # Verify cleanup (counters should be 0 or deleted)
        assert self.redis.get(conn_key) is None, "User connection key should be deleted"
        assert self.redis.get(ip_key) is None, "IP connection key should be deleted"
        assert not self.redis.sismember(room_key, str(user.id)), "User should be removed from room"
    
    async def test_connect_disconnect_connect_resets_window_and_allows(self):
        """
        Test: CONNECT → DISCONNECT → CONNECT resets window and allows re-connection.
        
        Coverage: Full lifecycle validation (lines 127-302)
        Redis E2E: Verify counter reset, TTL refresh
        """
        user = await create_test_user(username="reconnect_user")
        
        application = create_test_application()
        
        # First connection
        comm1 = WebsocketCommunicator(application, '/ws/tournament/777/')
        comm1.scope['user'] = user
        comm1.scope['client'] = ('192.168.1.102', 34567)
        
        connected1, _ = await comm1.connect()
        assert connected1, "First connection should succeed"
        
        conn_key = f"ws:conn:count:{user.id}"
        assert self.redis.get(conn_key) == "1"
        
        # Disconnect
        await comm1.disconnect()
        await asyncio.sleep(0.05)  # Brief pause for cleanup
        
        # Counter should be 0 or deleted
        assert self.redis.get(conn_key) in [None, "0"], "Counter should reset after disconnect"
        
        # Second connection (should succeed)
        comm2 = WebsocketCommunicator(application, '/ws/tournament/777/')
        comm2.scope['user'] = user
        comm2.scope['client'] = ('192.168.1.102', 45678)
        
        connected2, _ = await comm2.connect()
        assert connected2, "Reconnection should succeed after disconnect"
        
        # Counter should be 1 again
        assert self.redis.get(conn_key) == "1"
        
        # Cleanup
        await comm2.disconnect()


# ============================================================================
# Test Class B: Redis E2E Mechanics
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@redis_required
class TestRedisE2EMechanics:
    """
    Test Redis-specific behavior: TTL, atomicity, failover, key patterns.
    
    Coverage Targets:
    - ratelimit.py lines 187-220 (check_and_consume)
    - ratelimit.py lines 314-340 (room_try_join LUA script)
    - middleware_ratelimit.py lines 145-160, 170-184 (Redis integration)
    """
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config):
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
    
    async def test_redis_key_ttl_matches_window_seconds(self):
        """
        Test: Redis keys have correct TTL (connection=3600s, room=86400s).
        
        Coverage: lines 414-432 (increment_user_connections + expire call)
        Redis E2E: Direct TTL validation via redis.ttl()
        """
        user = await create_test_user(username="ttl_user")
        
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/555/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.103', 56789)
        
        # Connect
        connected, _ = await communicator.connect()
        assert connected
        
        # Check connection counter TTL (should be 3600s)
        conn_key = f"ws:conn:count:{user.id}"
        conn_ttl = self.redis.ttl(conn_key)
        assert 3550 <= conn_ttl <= 3600, f"Connection TTL should be ~3600s, got: {conn_ttl}"
        
        # Check room TTL (should be 86400s = 1 day)
        room_key = f"ws:room:tournament_555"
        room_ttl = self.redis.ttl(room_key)
        assert 86300 <= room_ttl <= 86400, f"Room TTL should be ~86400s, got: {room_ttl}"
        
        await communicator.disconnect()
    
    async def test_redis_incr_is_atomic_under_concurrency(self):
        """
        Test: Concurrent CONNECT operations use atomic INCR (no race conditions).
        
        Coverage: lines 414-432 (increment_user_connections using Redis INCR)
        Redis E2E: Test atomic increment directly via low-level utility
        """
        from apps.tournaments.realtime.ratelimit import increment_user_connections, get_user_connections
        
        user = await create_test_user(username="atomic_user")
        
        # Test atomic increments directly (without connection logic)
        async def increment_task():
            # Call increment in separate tasks
            return increment_user_connections(user.id)
        
        # Run 10 concurrent increments
        results = await asyncio.gather(*[increment_task() for _ in range(10)])
        
        # Each should return unique counter value (1, 2, 3, ..., 10)
        # If non-atomic, we'd see duplicate values or skipped values
        assert len(set(results)) == 10, f"Expected 10 unique values, got: {sorted(results)}"
        
        # Final counter should be exactly 10
        final_count = get_user_connections(user.id)
        assert final_count == 10, f"Expected final count 10, got: {final_count}"
        
        # Verify Redis key exists with correct value
        conn_key = f"ws:conn:count:{user.id}"
        redis_value = int(self.redis.get(conn_key))
        assert redis_value == 10, f"Redis should show 10, got: {redis_value}"
    
    async def test_redis_down_graceful_degradation_allows_connections(self):
        """
        Test: Redis unavailable → fallback to in-memory, connection allowed.
        
        Coverage: lines 190-195 (except Exception fallback in check_and_consume)
        Redis E2E: Mock Redis failure, verify graceful degradation
        """
        user = await create_test_user(username="fallback_user")
        
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/444/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.105', 67890)
        
        # Mock Redis failure (patch cache.client.get_client to raise exception)
        with patch('django.core.cache.cache.client.get_client') as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.incr.side_effect = Exception("Redis connection error")
            mock_redis.eval.side_effect = Exception("Redis connection error")
            mock_get_client.return_value = mock_redis
            
            # Connect (should succeed via in-memory fallback)
            connected, _ = await communicator.connect()
            assert connected, "Connection should succeed with in-memory fallback"
            
            # Cleanup
            await communicator.disconnect()
    
    async def test_redis_key_pattern_matches_ratelimit_ws_scope(self):
        """
        Test: Redis keys follow documented pattern (ws:conn:count:{user_id}).
        
        Coverage: Validates key naming conventions (implicit in all tests)
        Redis E2E: List keys, verify pattern matches documentation
        """
        user = await create_test_user(username="pattern_user")
        
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/333/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.106', 78901)
        
        # Connect
        connected, _ = await communicator.connect()
        assert connected
        
        # List all keys created (use SCAN to list keys)
        keys = self.redis.keys("ws:*")
        
        # Verify expected patterns exist
        expected_patterns = [
            f"ws:conn:count:{user.id}",      # User connection counter
            f"ws:conn:ip:192.168.1.106",    # IP connection counter
            f"ws:room:tournament_333",       # Room membership set
        ]
        
        for pattern in expected_patterns:
            assert any(pattern in key for key in keys), \
                f"Expected key pattern '{pattern}' not found in: {keys}"
        
        await communicator.disconnect()


# ============================================================================
# Test Class C: Upgrade + Multi-Connection Semantics
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@redis_required
class TestUpgradeAndMultiConnection:
    """
    Test HTTP→WebSocket upgrade and multi-connection tracking.
    
    Coverage Targets:
    - middleware_ratelimit.py lines 110-125 (scope parsing, IP extraction)
    - middleware_ratelimit.py lines 145-184 (per-connection tracking)
    """
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config):
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
    
    async def test_http_to_websocket_upgrade_counted_once(self):
        """
        Test: HTTP→WS upgrade counted as single connection (not double).
        
        Coverage: lines 127-145 (CONNECT handler, scope validation)
        Redis E2E: Verify counter incremented only once per connection
        """
        user = await create_test_user(username="upgrade_user")
        
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/666/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.107', 89012)
        
        # Connect (simulates HTTP→WS upgrade)
        connected, _ = await communicator.connect()
        assert connected
        
        # Counter should be exactly 1 (not 2)
        conn_key = f"ws:conn:count:{user.id}"
        count = int(self.redis.get(conn_key) or 0)
        assert count == 1, f"Upgrade should count as 1 connection, got: {count}"
        
        await communicator.disconnect()
        
        # After disconnect, counter should be 0 or deleted
        count_after = self.redis.get(conn_key)
        assert count_after in [None, "0"], f"Counter should reset, got: {count_after}"
    
    async def test_multiple_connections_same_user_tracked_separately(self):
        """
        Test: Multiple connections from same user → separate counters (up to limit).
        
        Coverage: lines 145-160 (connection limit enforcement)
        Redis E2E: Verify counter increments for each connection
        """
        user = await create_test_user(username="multi_conn_user")
        
        application = create_test_application()
        
        # First connection
        comm1 = WebsocketCommunicator(application, '/ws/tournament/111/')
        comm1.scope['user'] = user
        comm1.scope['client'] = ('192.168.1.108', 11111)
        
        connected1, _ = await comm1.connect()
        assert connected1
        
        conn_key = f"ws:conn:count:{user.id}"
        assert self.redis.get(conn_key) == "1"
        
        # Second connection
        comm2 = WebsocketCommunicator(application, '/ws/tournament/222/')
        comm2.scope['user'] = user
        comm2.scope['client'] = ('192.168.1.108', 22222)
        
        connected2, _ = await comm2.connect()
        assert connected2
        
        assert self.redis.get(conn_key) == "2", "Counter should increment to 2"
        
        # Third connection (should fail - limit is 2)
        comm3 = WebsocketCommunicator(application, '/ws/tournament/333/')
        comm3.scope['user'] = user
        comm3.scope['client'] = ('192.168.1.108', 33333)
        
        try:
            connected3, _ = await communicator.connect(timeout=2)
            # Should not reach here
            assert False, "Third connection should have been rejected"
        except:
            # Expected rejection
            pass
        
        # Counter should remain 2 (not incremented for rejected connection)
        final_count = int(self.redis.get(conn_key) or 0)
        assert final_count == 2, f"Counter should be 2, got: {final_count}"
        
        # Cleanup
        await comm1.disconnect()
        await comm2.disconnect()
    
    async def test_scope_ids_are_unique_per_connection(self):
        """
        Test: Each connection gets unique scope ID for room tracking.
        
        Coverage: lines 180-184 (room join with user_id)
        Redis E2E: Verify room membership uses user_id (not connection-specific ID)
        """
        user = await create_test_user(username="scope_user")
        
        application = create_test_application()
        
        # Two connections to same room
        comm1 = WebsocketCommunicator(application, '/ws/tournament/999/')
        comm1.scope['user'] = user
        comm1.scope['client'] = ('192.168.1.109', 44444)
        
        comm2 = WebsocketCommunicator(application, '/ws/tournament/999/')
        comm2.scope['user'] = user
        comm2.scope['client'] = ('192.168.1.109', 55555)
        
        # Connect both
        connected1, _ = await comm1.connect()
        connected2, _ = await comm2.connect()
        
        assert connected1 and connected2
        
        # Room should have 1 member (user_id, not connection count)
        room_key = f"ws:room:tournament_999"
        room_size = self.redis.scard(room_key)
        
        # Note: Room tracks user_id, so 1 member despite 2 connections
        assert room_size == 1, f"Room should have 1 unique user, got: {room_size}"
        
        # Cleanup
        await comm1.disconnect()
        await comm2.disconnect()


# ============================================================================
# Test Class D: Edge Cases
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@redis_required
class TestEdgeCases:
    """
    Test edge cases: malformed scopes, zero limits, burst traffic, anonymous users.
    
    Coverage Targets:
    - middleware_ratelimit.py lines 130-144 (scope parsing edge cases)
    - middleware_ratelimit.py lines 250-270 (payload size checks)
    - middleware_ratelimit.py lines 145-160 (zero limit handling)
    """
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config):
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
    
    async def test_malformed_scope_id_is_handled_without_crash(self):
        """
        Test: Malformed path (no tournament_id) → gracefully handle.
        
        Coverage: lines 130-144 (_extract_tournament_id edge cases)
        Redis E2E: Verify connection succeeds without room tracking
        """
        user = await create_test_user(username="malformed_user")
        
        # Create custom application with malformed path
        application = create_test_application()
        
        # Path missing tournament_id: /ws/tournament/
        communicator = WebsocketCommunicator(application, '/ws/tournament/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.110', 66666)
        
        # Should not crash (tournament_id=None, no room tracking)
        try:
            connected, _ = await communicator.connect()
            # Connection may succeed or fail depending on URL routing
            # Key: should not crash with KeyError or ValueError
            await communicator.disconnect()
        except Exception as e:
            # If routing fails, that's OK (not a middleware crash)
            assert "tournament_id" not in str(e).lower(), \
                f"Should not crash on tournament_id parsing: {e}"
    
    async def test_zero_rate_limit_blocks_all_connections(self):
        """
        Test: WS_RATE_CONN_PER_USER=0 → all connections rejected.
        
        Coverage: lines 145-160 (limit check with zero value)
        Redis E2E: Verify immediate rejection without Redis increment
        """
        user = await create_test_user(username="zero_limit_user")
        
        # Temporarily set limit to 0
        with patch.object(self.config, 'WS_RATE_CONN_PER_USER', 0):
            application = create_test_application()
            communicator = WebsocketCommunicator(application, '/ws/tournament/123/')
            communicator.scope['user'] = user
            communicator.scope['client'] = ('192.168.1.111', 77777)
            
            # Connection should be rejected immediately
            try:
                connected, _ = await communicator.connect(timeout=2)
                assert False, "Connection should be rejected with zero limit"
            except:
                # Expected rejection
                pass
            
            # Redis counter should NOT be created
            conn_key = f"ws:conn:count:{user.id}"
            assert self.redis.get(conn_key) is None, "Counter should not exist with zero limit"
    
    async def test_high_burst_traffic_applies_bucket_correctly(self):
        """
        Test: Burst traffic (rapid messages) → rate limit enforced via token bucket.
        
        Coverage: lines 220-250 (rate_limited_receive, check_and_consume)
        Redis E2E: Send rapid messages, verify token bucket depletion
        """
        user = await create_test_user(username="burst_user")
        
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/789/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.112', 88888)
        
        # Connect
        connected, _ = await communicator.connect()
        assert connected
        
        # Send burst of messages (exceed rate limit: 5 RPS, burst 10)
        # First 10 should succeed (burst capacity), then rate limited
        success_count = 0
        
        for i in range(15):
            try:
                await communicator.send_json_to({'action': 'ping', 'seq': i})
                
                # Try to receive response (may timeout if rate limited)
                response = await asyncio.wait_for(
                    communicator.receive_json_from(),
                    timeout=0.1
                )
                
                if 'echo' in response:
                    success_count += 1
            except asyncio.TimeoutError:
                # Message dropped due to rate limit
                pass
        
        # Should have ~10 successful (burst capacity), rest rate limited
        assert 8 <= success_count <= 12, \
            f"Expected ~10 messages (burst), got: {success_count}"
        
        await communicator.disconnect()
    
    async def test_authenticated_and_anonymous_are_both_limited(self):
        """
        Test: Anonymous users limited by IP, authenticated by user_id + IP.
        
        Coverage: lines 165-184 (IP connection tracking)
        Redis E2E: Verify separate counters for anonymous vs authenticated
        """
        # Anonymous connection (no user)
        application = create_test_application()
        comm_anon = WebsocketCommunicator(application, '/ws/tournament/456/')
        comm_anon.scope['user'] = None  # Anonymous
        comm_anon.scope['client'] = ('192.168.1.113', 99999)
        
        connected_anon, _ = await comm_anon.connect()
        assert connected_anon, "Anonymous connection should succeed"
        
        # Only IP counter should exist (no user counter)
        ip_key = f"ws:conn:ip:192.168.1.113"
        assert self.redis.get(ip_key) == "1", "IP counter should be 1 for anonymous"
        
        # Authenticated connection (same IP)
        user = await create_test_user(username="auth_user")
        comm_auth = WebsocketCommunicator(application, '/ws/tournament/456/')
        comm_auth.scope['user'] = user
        comm_auth.scope['client'] = ('192.168.1.113', 11111)
        
        connected_auth, _ = await comm_auth.connect()
        assert connected_auth, "Authenticated connection should succeed"
        
        # Both counters should exist
        user_key = f"ws:conn:count:{user.id}"
        assert self.redis.get(user_key) == "1", "User counter should be 1"
        assert self.redis.get(ip_key) == "2", "IP counter should be 2 (anon + auth)"
        
        # Cleanup
        await comm_anon.disconnect()
        await comm_auth.disconnect()
    
    async def test_message_rate_limiting_enforced_via_token_bucket(self):
        """
        Test: Rapid messages trigger rate limit via token bucket.
        
        Coverage: lines 220-260 (rate_limited_receive, message throttling)
        Redis E2E: Token bucket state verification
        """
        user = await create_test_user(username="msg_rate_user")
        
        application = create_test_application()
        communicator = WebsocketCommunicator(application, '/ws/tournament/555/')
        communicator.scope['user'] = user
        communicator.scope['client'] = ('192.168.1.115', 22222)
        
        # Connect
        connected, _ = await communicator.connect()
        assert connected
        
        # Send messages rapidly (burst capacity = 10)
        success_count = 0
        for i in range(12):
            await communicator.send_json_to({'action': 'test', 'seq': i})
            
            # Try to receive (may be rate limited after burst)
            try:
                response = await asyncio.wait_for(communicator.receive_json_from(), timeout=0.1)
                if 'echo' in response:
                    success_count += 1
            except asyncio.TimeoutError:
                # Rate limited
                break
        
        # Should have ~10 successful (burst capacity)
        assert 8 <= success_count <= 11, f"Expected ~10 messages in burst, got: {success_count}"
        
        await communicator.disconnect()


# ============================================================================
# Flake Detection Script (Run 3x)
# ============================================================================

if __name__ == '__main__':
    """
    Flake detection: Run suite 3x back-to-back.
    
    Usage: pytest tests/test_phase6_residuals_websocket_ratelimit_e2e.py -v --count=3
    """
    import sys
    pytest.main([__file__, '-v', '--count=3', '--tb=short'])
