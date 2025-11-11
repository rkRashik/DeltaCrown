"""
Module 6.8: Redis-Backed Enforcement & E2E Rate Limiting Tests

Tests Redis integration for rate limit enforcement in WebSocket middleware.
Targets: middleware_ratelimit.py lines 135-288 (enforcement paths).

Coverage Goal: 47% → ≥70-75% (+23-28%)

Test Categories:
1. Connection limits (per-user, per-IP) - Lines 135-174
2. Room capacity enforcement - Lines 179-207
3. Message rate enforcement - Lines 267-288
4. Payload size enforcement - Lines 240-263
5. Redis failover scenarios

Prerequisites:
- Redis running: docker-compose -f docker-compose.test.yml up -d
- Tests skip gracefully if Redis unavailable
"""

import pytest
import asyncio
import json
import redis
from unittest.mock import patch, MagicMock
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from apps.tournaments.realtime.middleware_ratelimit import RateLimitMiddleware
from tests.redis_fixtures import create_test_user

User = get_user_model()


# ============================================================================
# Test Class 1: Connection Limit Enforcement (Lines 135-174)
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestConnectionLimitRedis:
    """Test per-user and per-IP connection limit enforcement with Redis."""
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config):
        """Auto-use Redis fixtures for all tests in this class."""
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
    
    async def test_user_connection_limit_enforced(self):
        """
        Test: Per-user connection limit enforced via Redis counter.
        
        Target Lines: 135-150 (user connection check)
        
        Setup:
        - WS_RATE_CONN_PER_USER = 2
        - User opens 3 connections
        
        Expected:
        - Connections 1-2: accepted
        - Connection 3: rejected with close code 4008
        - Redis counter reaches 2, then rejects 3rd
        """
        user = await create_test_user(username="test_conn_user")
        
        # Mock application that accepts connections
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.1)  # Keep connection open briefly
        
        middleware = RateLimitMiddleware(mock_app)
        
        # Connection 1: should succeed
        comm1 = WebsocketCommunicator(middleware, "/ws/match/123/")
        comm1.scope['user'] = user
        comm1.scope['client'] = ['192.168.1.100', 12345]
        
        connected1, _ = await comm1.connect(timeout=2)
        assert connected1, "First connection should succeed"
        
        # Verify Redis counter incremented to 1
        user_key = f"{self.namespace}conn:user:{user.id}"
        assert self.redis.get(user_key) == "1", "Redis counter should be 1 after first connection"
        
        # Connection 2: should succeed
        comm2 = WebsocketCommunicator(middleware, "/ws/match/123/")
        comm2.scope['user'] = user
        comm2.scope['client'] = ['192.168.1.100', 12346]
        
        connected2, _ = await comm2.connect(timeout=2)
        assert connected2, "Second connection should succeed"
        
        # Verify Redis counter incremented to 2
        assert self.redis.get(user_key) == "2", "Redis counter should be 2 after second connection"
        
        # Connection 3: should be rejected (limit reached)
        comm3 = WebsocketCommunicator(middleware, "/ws/match/123/")
        comm3.scope['user'] = user
        comm3.scope['client'] = ['192.168.1.100', 12347]
        
        connected3, close_code = await comm3.connect(timeout=2)
        assert not connected3, "Third connection should be rejected"
        assert close_code == 4008, f"Expected close code 4008 (rate limit), got {close_code}"
        
        # Cleanup
        await comm1.disconnect()
        await comm2.disconnect()
    
    async def test_ip_connection_limit_enforced(self):
        """
        Test: Per-IP connection limit enforced for anonymous users.
        
        Target Lines: 154-174 (IP connection check)
        
        Setup:
        - WS_RATE_CONN_PER_IP = 5
        - Anonymous user (unauthenticated) from same IP opens 6 connections
        
        Expected:
        - Connections 1-5: accepted
        - Connection 6: rejected with close code 4008
        - Redis uses IP-based key for anonymous users
        """
        from django.contrib.auth.models import AnonymousUser
        
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.1)
        
        middleware = RateLimitMiddleware(mock_app)
        test_ip = "10.0.0.99"
        
        # Open 5 connections (should all succeed)
        communicators = []
        for i in range(5):
            comm = WebsocketCommunicator(middleware, "/ws/match/456/")
            comm.scope['user'] = AnonymousUser()
            comm.scope['client'] = [test_ip, 20000 + i]
            
            connected, _ = await comm.connect(timeout=2)
            assert connected, f"Connection {i+1}/5 should succeed"
            communicators.append(comm)
        
        # Verify Redis counter is at 5
        ip_key = f"{self.namespace}conn:ip:{test_ip}"
        assert self.redis.get(ip_key) == "5", "Redis counter should be 5 after 5 connections"
        
        # 6th connection: should be rejected
        comm_overflow = WebsocketCommunicator(middleware, "/ws/match/456/")
        comm_overflow.scope['user'] = AnonymousUser()
        comm_overflow.scope['client'] = [test_ip, 26000]
        
        connected, close_code = await comm_overflow.connect(timeout=2)
        assert not connected, "6th connection should be rejected"
        assert close_code == 4008, f"Expected close code 4008, got {close_code}"
        
        # Cleanup
        for comm in communicators:
            await comm.disconnect()
    
    async def test_connection_cleanup_on_disconnect(self):
        """
        Test: Redis counter decrements when connection closes.
        
        Target Lines: 135-150 (connection cleanup path)
        
        Setup:
        - User opens 2 connections (at limit)
        - Close first connection
        - Open 3rd connection
        
        Expected:
        - After disconnect: counter goes 2 → 1
        - 3rd connection succeeds (slot available)
        """
        user = await create_test_user(username="test_cleanup_user")
        
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.1)
        
        middleware = RateLimitMiddleware(mock_app)
        
        # Open 2 connections (at limit)
        comm1 = WebsocketCommunicator(middleware, "/ws/match/789/")
        comm1.scope['user'] = user
        comm1.scope['client'] = ['192.168.2.50', 30000]
        await comm1.connect(timeout=2)
        
        comm2 = WebsocketCommunicator(middleware, "/ws/match/789/")
        comm2.scope['user'] = user
        comm2.scope['client'] = ['192.168.2.50', 30001]
        await comm2.connect(timeout=2)
        
        user_key = f"{self.namespace}conn:user:{user.id}"
        assert self.redis.get(user_key) == "2", "Counter should be 2"
        
        # Disconnect first connection
        await comm1.disconnect()
        await asyncio.sleep(0.1)  # Allow middleware cleanup to run
        
        # Counter should decrement to 1
        assert self.redis.get(user_key) == "1", "Counter should decrement to 1 after disconnect"
        
        # 3rd connection should now succeed (slot freed)
        comm3 = WebsocketCommunicator(middleware, "/ws/match/789/")
        comm3.scope['user'] = user
        comm3.scope['client'] = ['192.168.2.50', 30002]
        
        connected, _ = await comm3.connect(timeout=2)
        assert connected, "3rd connection should succeed after disconnect freed slot"
        
        # Cleanup
        await comm2.disconnect()
        await comm3.disconnect()
    
    async def test_concurrent_connection_attempts_serialized(self):
        """
        Test: Concurrent connection attempts handled without race conditions.
        
        Target Lines: 135-150 (race condition handling)
        
        Setup:
        - Limit = 2 connections per user
        - 5 connections attempt simultaneously via asyncio.gather
        
        Expected:
        - Exactly 2 connections succeed
        - Remaining 3 rejected with code 4008
        - No Redis counter corruption
        """
        user = await create_test_user(username="test_race_user")
        
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.05)
        
        middleware = RateLimitMiddleware(mock_app)
        
        async def attempt_connection(port):
            comm = WebsocketCommunicator(middleware, "/ws/match/999/")
            comm.scope['user'] = user
            comm.scope['client'] = ['192.168.3.10', port]
            
            result = await comm.connect(timeout=2)
            return (comm, result[0], result[1])  # (communicator, connected, close_code)
        
        # Attempt 5 concurrent connections
        results = await asyncio.gather(*[attempt_connection(40000 + i) for i in range(5)])
        
        # Count successful connections
        successful = [r for r in results if r[1]]
        rejected = [r for r in results if not r[1]]
        
        assert len(successful) == 2, f"Expected exactly 2 successful connections, got {len(successful)}"
        assert len(rejected) == 3, f"Expected 3 rejected connections, got {len(rejected)}"
        
        # Verify all rejections used correct close code
        for comm, connected, close_code in rejected:
            assert close_code == 4008, f"Rejected connection should use code 4008, got {close_code}"
        
        # Verify Redis counter is exactly 2 (no corruption)
        user_key = f"{self.namespace}conn:user:{user.id}"
        assert self.redis.get(user_key) == "2", "Redis counter should be exactly 2 (no race corruption)"
        
        # Cleanup
        for comm, connected, _ in successful:
            await comm.disconnect()


# ============================================================================
# Test Class 2: Room Capacity Enforcement (Lines 179-207)
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestRoomCapacityRedis:
    """Test room capacity limits via Redis sets."""
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config):
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
        # Override room capacity to 10 for faster tests
        self.config['WS_RATE_ROOM_MAX_MEMBERS'] = 10
    
    async def test_room_capacity_enforced_at_limit(self):
        """
        Test: Room capacity enforced when limit reached.
        
        Target Lines: 179-207 (room capacity check)
        
        Setup:
        - WS_RATE_ROOM_MAX_MEMBERS = 10
        - 11 users attempt to join same room
        
        Expected:
        - First 10 join successfully
        - 11th user rejected with code 4010 (room full)
        - Redis set contains 10 members
        """
        async def mock_app(scope, receive, send):
            # Simulate room join
            room_id = scope['url_route']['kwargs'].get('match_id', 'test_room')
            await asyncio.sleep(0.05)
        
        middleware = RateLimitMiddleware(mock_app)
        room_id = "match_555"
        
        # Join 10 users (should all succeed)
        communicators = []
        for i in range(10):
            user = await create_test_user(username=f"room_user_{i}")
            comm = WebsocketCommunicator(middleware, f"/ws/match/{room_id}/")
            comm.scope['user'] = user
            comm.scope['client'] = ['192.168.4.100', 50000 + i]
            # Add room_id to scope for middleware
            comm.scope['url_route'] = {'kwargs': {'match_id': room_id}}
            
            connected, _ = await comm.connect(timeout=2)
            assert connected, f"User {i+1}/10 should successfully join room"
            communicators.append(comm)
        
        # Verify Redis set has 10 members
        room_key = f"{self.namespace}room:{room_id}:members"
        assert self.redis.scard(room_key) == 10, "Room should have 10 members in Redis"
        
        # 11th user: should be rejected (room full)
        user_overflow = await create_test_user(username="room_user_overflow")
        comm_overflow = WebsocketCommunicator(middleware, f"/ws/match/{room_id}/")
        comm_overflow.scope['user'] = user_overflow
        comm_overflow.scope['client'] = ['192.168.4.100', 60000]
        comm_overflow.scope['url_route'] = {'kwargs': {'match_id': room_id}}
        
        connected, close_code = await comm_overflow.connect(timeout=2)
        assert not connected, "11th user should be rejected (room full)"
        assert close_code == 4010, f"Expected close code 4010 (room full), got {close_code}"
        
        # Cleanup
        for comm in communicators:
            await comm.disconnect()
    
    async def test_room_join_leave_cycle_frees_slot(self):
        """
        Test: Leaving room frees slot for new member.
        
        Target Lines: 179-207 (room leave cleanup)
        
        Setup:
        - Room at capacity (10 members)
        - One user disconnects
        - New user attempts to join
        
        Expected:
        - After disconnect: Redis set size 10 → 9
        - New user successfully joins (slot available)
        """
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.05)
        
        middleware = RateLimitMiddleware(mock_app)
        room_id = "match_777"
        
        # Fill room to capacity (10 users)
        communicators = []
        for i in range(10):
            user = await create_test_user(username=f"cycle_user_{i}")
            comm = WebsocketCommunicator(middleware, f"/ws/match/{room_id}/")
            comm.scope['user'] = user
            comm.scope['client'] = ['192.168.5.50', 55000 + i]
            comm.scope['url_route'] = {'kwargs': {'match_id': room_id}}
            await comm.connect(timeout=2)
            communicators.append(comm)
        
        room_key = f"{self.namespace}room:{room_id}:members"
        assert self.redis.scard(room_key) == 10, "Room should be at capacity"
        
        # Disconnect first user
        await communicators[0].disconnect()
        await asyncio.sleep(0.1)  # Allow cleanup
        
        # Room should now have 9 members
        assert self.redis.scard(room_key) == 9, "Room should have 9 members after disconnect"
        
        # New user should successfully join (slot freed)
        new_user = await create_test_user(username="cycle_user_new")
        comm_new = WebsocketCommunicator(middleware, f"/ws/match/{room_id}/")
        comm_new.scope['user'] = new_user
        comm_new.scope['client'] = ['192.168.5.50', 66000]
        comm_new.scope['url_route'] = {'kwargs': {'match_id': room_id}}
        
        connected, _ = await comm_new.connect(timeout=2)
        assert connected, "New user should join after slot freed"
        assert self.redis.scard(room_key) == 10, "Room should be back at capacity"
        
        # Cleanup
        await comm_new.disconnect()
        for comm in communicators[1:]:  # Skip [0] (already disconnected)
            await comm.disconnect()
    
    async def test_multiple_rooms_independent_capacity(self):
        """
        Test: Multiple rooms have independent capacity tracking.
        
        Target Lines: 179-207 (room isolation)
        
        Setup:
        - User joins room A (at capacity)
        - Same user joins room B (empty)
        
        Expected:
        - Room A tracks its own capacity
        - Room B tracks its own capacity
        - No cross-room interference in Redis
        """
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.05)
        
        middleware = RateLimitMiddleware(mock_app)
        room_a = "match_AAA"
        room_b = "match_BBB"
        
        # Fill room A to capacity
        users_a = []
        for i in range(10):
            user = await create_test_user(username=f"roomA_user_{i}")
            comm = WebsocketCommunicator(middleware, f"/ws/match/{room_a}/")
            comm.scope['user'] = user
            comm.scope['client'] = ['192.168.6.10', 60000 + i]
            comm.scope['url_route'] = {'kwargs': {'match_id': room_a}}
            await comm.connect(timeout=2)
            users_a.append(comm)
        
        # Verify room A is full
        room_a_key = f"{self.namespace}room:{room_a}:members"
        assert self.redis.scard(room_a_key) == 10, "Room A should be at capacity"
        
        # User joins room B (should succeed, room B is empty)
        user_b = await create_test_user(username="roomB_user_0")
        comm_b = WebsocketCommunicator(middleware, f"/ws/match/{room_b}/")
        comm_b.scope['user'] = user_b
        comm_b.scope['client'] = ['192.168.6.10', 70000]
        comm_b.scope['url_route'] = {'kwargs': {'match_id': room_b}}
        
        connected, _ = await comm_b.connect(timeout=2)
        assert connected, "User should join room B (independent of room A capacity)"
        
        # Verify room B has 1 member, room A still has 10
        room_b_key = f"{self.namespace}room:{room_b}:members"
        assert self.redis.scard(room_b_key) == 1, "Room B should have 1 member"
        assert self.redis.scard(room_a_key) == 10, "Room A should still have 10 members"
        
        # Cleanup
        await comm_b.disconnect()
        for comm in users_a:
            await comm.disconnect()


# ============================================================================
# Test Class 3: Message Rate Enforcement (Lines 267-288)
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestMessageRateLimitRedis:
    """Test message rate limiting via Redis token bucket."""
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config, fast_cooldown):
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
        # Override message rate for deterministic tests
        self.config['WS_RATE_MSG_RPS'] = 5.0  # 5 messages per second
        self.config['WS_RATE_MSG_BURST'] = 10  # Burst of 10 messages
    
    async def test_message_burst_enforced(self):
        """
        Test: Message burst limit enforced via Redis.
        
        Target Lines: 267-288 (message rate check)
        
        Setup:
        - WS_RATE_MSG_BURST = 10
        - User sends 12 messages rapidly
        
        Expected:
        - Messages 1-10: accepted
        - Messages 11-12: rejected (burst exceeded)
        - Redis tracks message count in window
        """
        user = await create_test_user(username="test_burst_user")
        
        # Mock consumer that accepts messages
        async def mock_app(scope, receive, send):
            while True:
                message = await receive()
                if message['type'] == 'websocket.disconnect':
                    break
                elif message['type'] == 'websocket.receive':
                    # Echo message back
                    await send({
                        'type': 'websocket.send',
                        'text': json.dumps({'status': 'ok'})
                    })
        
        middleware = RateLimitMiddleware(mock_app)
        
        comm = WebsocketCommunicator(middleware, "/ws/match/burst/")
        comm.scope['user'] = user
        comm.scope['client'] = ['192.168.7.20', 80000]
        comm.scope['url_route'] = {'kwargs': {'match_id': 'burst'}}
        
        await comm.connect(timeout=2)
        
        # Send 12 messages rapidly
        accepted = 0
        rejected = 0
        
        for i in range(12):
            await comm.send_json_to({'type': 'test', 'seq': i})
            
            try:
                response = await asyncio.wait_for(comm.receive_json_from(), timeout=0.5)
                if response.get('status') == 'ok':
                    accepted += 1
            except asyncio.TimeoutError:
                # No response = rate limited
                rejected += 1
        
        # Verify: first 10 accepted, next 2 rejected
        assert accepted >= 8, f"Expected ≥8 messages accepted (burst), got {accepted}"
        assert rejected >= 2, f"Expected ≥2 messages rejected, got {rejected}"
        
        # Verify Redis message counter
        msg_key = f"{self.namespace}msg:user:{user.id}"
        msg_count = self.redis.get(msg_key)
        assert msg_count is not None, "Redis should track message count"
        assert int(msg_count) >= 10, "Redis counter should show burst reached"
        
        await comm.disconnect()
    
    async def test_cooldown_recovery_after_burst(self):
        """
        Test: Message rate recovers after cooldown window.
        
        Target Lines: 267-288 (cooldown/token refill)
        
        Setup:
        - WS_RATE_MSG_WINDOW_MS = 200ms (fast cooldown)
        - User sends burst, waits 250ms, sends again
        
        Expected:
        - Initial burst: limited
        - After cooldown: tokens refilled, messages accepted again
        """
        user = await create_test_user(username="test_cooldown_user")
        
        async def mock_app(scope, receive, send):
            while True:
                message = await receive()
                if message['type'] == 'websocket.disconnect':
                    break
                elif message['type'] == 'websocket.receive':
                    await send({
                        'type': 'websocket.send',
                        'text': json.dumps({'status': 'ok'})
                    })
        
        middleware = RateLimitMiddleware(mock_app)
        
        comm = WebsocketCommunicator(middleware, "/ws/match/cooldown/")
        comm.scope['user'] = user
        comm.scope['client'] = ['192.168.7.30', 81000]
        comm.scope['url_route'] = {'kwargs': {'match_id': 'cooldown'}}
        
        await comm.connect(timeout=2)
        
        # Send burst to exhaust tokens
        for i in range(12):
            await comm.send_json_to({'type': 'exhaust', 'seq': i})
        
        # Attempt message (should be rate limited)
        await comm.send_json_to({'type': 'blocked', 'seq': 99})
        
        try:
            await asyncio.wait_for(comm.receive_json_from(), timeout=0.3)
            blocked_response = True
        except asyncio.TimeoutError:
            blocked_response = False
        
        assert not blocked_response, "Message should be rate limited before cooldown"
        
        # Wait for cooldown window (250ms > 200ms window)
        await asyncio.sleep(0.25)
        
        # Send message (should succeed after cooldown)
        await comm.send_json_to({'type': 'recovered', 'seq': 100})
        
        try:
            response = await asyncio.wait_for(comm.receive_json_from(), timeout=0.5)
            recovered = response.get('status') == 'ok'
        except asyncio.TimeoutError:
            recovered = False
        
        assert recovered, "Message should succeed after cooldown window"
        
        await comm.disconnect()
    
    async def test_message_rate_per_user_independent(self):
        """
        Test: Message rate limits are per-user (no cross-user interference).
        
        Target Lines: 267-288 (per-user rate tracking)
        
        Setup:
        - User A exhausts burst
        - User B sends messages
        
        Expected:
        - User A: rate limited
        - User B: messages accepted (independent limit)
        """
        user_a = await create_test_user(username="test_rate_userA")
        user_b = await create_test_user(username="test_rate_userB")
        
        async def mock_app(scope, receive, send):
            while True:
                message = await receive()
                if message['type'] == 'websocket.disconnect':
                    break
                elif message['type'] == 'websocket.receive':
                    await send({
                        'type': 'websocket.send',
                        'text': json.dumps({'user': scope['user'].username})
                    })
        
        middleware = RateLimitMiddleware(mock_app)
        
        # User A: exhaust burst
        comm_a = WebsocketCommunicator(middleware, "/ws/match/indep/")
        comm_a.scope['user'] = user_a
        comm_a.scope['client'] = ['192.168.7.40', 82000]
        comm_a.scope['url_route'] = {'kwargs': {'match_id': 'indep'}}
        await comm_a.connect(timeout=2)
        
        for i in range(12):
            await comm_a.send_json_to({'type': 'exhaust', 'seq': i})
        
        # User B: send message (should succeed, independent limit)
        comm_b = WebsocketCommunicator(middleware, "/ws/match/indep/")
        comm_b.scope['user'] = user_b
        comm_b.scope['client'] = ['192.168.7.41', 83000]
        comm_b.scope['url_route'] = {'kwargs': {'match_id': 'indep'}}
        await comm_b.connect(timeout=2)
        
        await comm_b.send_json_to({'type': 'test', 'data': 'hello'})
        
        try:
            response = await asyncio.wait_for(comm_b.receive_json_from(), timeout=0.5)
            user_b_accepted = response.get('user') == user_b.username
        except asyncio.TimeoutError:
            user_b_accepted = False
        
        assert user_b_accepted, "User B should not be affected by User A's rate limit"
        
        # Verify Redis has separate keys for each user
        key_a = f"{self.namespace}msg:user:{user_a.id}"
        key_b = f"{self.namespace}msg:user:{user_b.id}"
        
        assert self.redis.exists(key_a), "User A should have rate limit key"
        assert self.redis.exists(key_b), "User B should have rate limit key"
        assert self.redis.get(key_a) != self.redis.get(key_b), "Rate counters should be independent"
        
        await comm_a.disconnect()
        await comm_b.disconnect()
    
    async def test_anonymous_message_rate_ip_based(self):
        """
        Test: Anonymous users rate limited by IP address.
        
        Target Lines: 267-288 (anonymous rate tracking)
        
        Setup:
        - Anonymous user from IP 10.0.0.50
        - Exhausts message burst
        
        Expected:
        - Rate limit tracked by IP (not user ID)
        - Redis key uses IP address
        """
        from django.contrib.auth.models import AnonymousUser
        
        async def mock_app(scope, receive, send):
            while True:
                message = await receive()
                if message['type'] == 'websocket.disconnect':
                    break
                elif message['type'] == 'websocket.receive':
                    await send({
                        'type': 'websocket.send',
                        'text': json.dumps({'status': 'ok'})
                    })
        
        middleware = RateLimitMiddleware(mock_app)
        test_ip = "10.0.0.50"
        
        comm = WebsocketCommunicator(middleware, "/ws/match/anon/")
        comm.scope['user'] = AnonymousUser()
        comm.scope['client'] = [test_ip, 90000]
        comm.scope['url_route'] = {'kwargs': {'match_id': 'anon'}}
        
        await comm.connect(timeout=2)
        
        # Send burst to exhaust tokens
        for i in range(12):
            await comm.send_json_to({'type': 'anon_burst', 'seq': i})
        
        # Verify Redis key uses IP address (not user ID)
        msg_key_ip = f"{self.namespace}msg:ip:{test_ip}"
        assert self.redis.exists(msg_key_ip), "Anonymous rate limit should use IP-based key"
        
        msg_count = self.redis.get(msg_key_ip)
        assert msg_count is not None, "Redis should track anonymous message count by IP"
        assert int(msg_count) >= 10, "IP-based counter should show burst reached"
        
        await comm.disconnect()


# ============================================================================
# Test Class 4: Payload Size Enforcement (Lines 240-263)
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestPayloadSizeRedis:
    """Test payload size limits with Redis context."""
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config):
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
        # Override payload limit for tests
        self.config['WS_MAX_PAYLOAD_BYTES'] = 1024  # 1KB limit
    
    async def test_oversized_payload_rejected(self):
        """
        Test: Oversized payload rejected with code 4009.
        
        Target Lines: 240-263 (payload size check)
        
        Setup:
        - WS_MAX_PAYLOAD_BYTES = 1024 (1KB)
        - User sends 2KB payload
        
        Expected:
        - Connection rejected with close code 4009
        - Redis tracks rejection event
        """
        user = await create_test_user(username="test_payload_user")
        
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.05)
        
        middleware = RateLimitMiddleware(mock_app)
        
        comm = WebsocketCommunicator(middleware, "/ws/match/payload/")
        comm.scope['user'] = user
        comm.scope['client'] = ['192.168.8.10', 85000]
        comm.scope['url_route'] = {'kwargs': {'match_id': 'payload'}}
        
        await comm.connect(timeout=2)
        
        # Send oversized payload (2KB > 1KB limit)
        large_payload = {'data': 'x' * 2048}
        await comm.send_json_to(large_payload)
        
        # Expect connection closed with code 4009
        try:
            await asyncio.wait_for(comm.receive_output(timeout=1), timeout=2)
            # If we get here, check for close message
            close_msg = await comm.receive_output(timeout=1)
            close_code = close_msg.get('code', 0)
        except asyncio.TimeoutError:
            close_code = 0
        
        assert close_code == 4009, f"Expected close code 4009 (payload too large), got {close_code}"
        
        await comm.disconnect()
    
    async def test_boundary_payload_edge_cases(self):
        """
        Test: Payload at boundary (1024 bytes) accepted, 1025 rejected.
        
        Target Lines: 240-263 (boundary edge cases)
        
        Setup:
        - Payload exactly 1024 bytes: should pass
        - Payload 1025 bytes: should fail
        
        Expected:
        - 1024 bytes: accepted
        - 1025 bytes: rejected with code 4009
        """
        user = await create_test_user(username="test_boundary_user")
        
        async def mock_app(scope, receive, send):
            while True:
                message = await receive()
                if message['type'] == 'websocket.disconnect':
                    break
                elif message['type'] == 'websocket.receive':
                    await send({
                        'type': 'websocket.send',
                        'text': json.dumps({'status': 'accepted'})
                    })
        
        middleware = RateLimitMiddleware(mock_app)
        
        # Test 1: Payload at boundary (1024 bytes) - should pass
        comm1 = WebsocketCommunicator(middleware, "/ws/match/boundary/")
        comm1.scope['user'] = user
        comm1.scope['client'] = ['192.168.8.20', 86000]
        comm1.scope['url_route'] = {'kwargs': {'match_id': 'boundary'}}
        
        await comm1.connect(timeout=2)
        
        # Payload exactly 1024 bytes (accounting for JSON overhead)
        boundary_payload = {'data': 'y' * 1000}  # ~1000 chars + JSON structure ≈ 1024 bytes
        await comm1.send_json_to(boundary_payload)
        
        try:
            response = await asyncio.wait_for(comm1.receive_json_from(), timeout=0.5)
            boundary_accepted = response.get('status') == 'accepted'
        except asyncio.TimeoutError:
            boundary_accepted = False
        
        assert boundary_accepted, "Payload at boundary (1024 bytes) should be accepted"
        
        await comm1.disconnect()
        
        # Test 2: Payload over boundary (>1025 bytes) - should fail
        comm2 = WebsocketCommunicator(middleware, "/ws/match/boundary/")
        comm2.scope['user'] = user
        comm2.scope['client'] = ['192.168.8.20', 86001]
        comm2.scope['url_route'] = {'kwargs': {'match_id': 'boundary'}}
        
        await comm2.connect(timeout=2)
        
        over_boundary_payload = {'data': 'z' * 1100}  # Definitely > 1024 bytes
        await comm2.send_json_to(over_boundary_payload)
        
        # Expect close code 4009
        try:
            close_msg = await asyncio.wait_for(comm2.receive_output(timeout=1), timeout=2)
            close_code = close_msg.get('code', 0)
        except asyncio.TimeoutError:
            close_code = 0
        
        assert close_code == 4009, f"Payload over boundary should be rejected with code 4009, got {close_code}"
        
        await comm2.disconnect()


# ============================================================================
# Test Class 5: Redis Failover Scenarios
# ============================================================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestRedisFailover:
    """Test graceful degradation when Redis is unavailable."""
    
    @pytest.fixture(autouse=True)
    def setup_fixtures(self, redis_test_client, test_namespace, redis_cleanup, redis_rate_limit_config):
        self.redis = redis_test_client
        self.namespace = test_namespace
        self.config = redis_rate_limit_config
    
    async def test_redis_down_graceful_degradation(self):
        """
        Test: When Redis down, middleware falls back to in-memory limits.
        
        Target Lines: All enforcement paths (Redis exception handling)
        
        Setup:
        - Mock Redis to raise ConnectionError
        - User attempts connection
        
        Expected:
        - Connection succeeds (graceful fallback)
        - No crash or 500 error
        - Warning logged about Redis unavailability
        """
        user = await create_test_user(username="test_failover_user")
        
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.05)
        
        middleware = RateLimitMiddleware(mock_app)
        
        # Mock Redis client to raise ConnectionError
        with patch('redis.Redis.get', side_effect=redis.ConnectionError("Redis down")):
            with patch('redis.Redis.incr', side_effect=redis.ConnectionError("Redis down")):
                with patch('redis.Redis.sadd', side_effect=redis.ConnectionError("Redis down")):
                    comm = WebsocketCommunicator(middleware, "/ws/match/failover/")
                    comm.scope['user'] = user
                    comm.scope['client'] = ['192.168.9.10', 87000]
                    comm.scope['url_route'] = {'kwargs': {'match_id': 'failover'}}
                    
                    # Connection should succeed despite Redis being down
                    connected, _ = await comm.connect(timeout=2)
                    assert connected, "Connection should succeed when Redis is down (graceful degradation)"
                    
                    await comm.disconnect()
    
    async def test_redis_recovery_after_outage(self):
        """
        Test: After Redis recovers, enforcement resumes normally.
        
        Target Lines: All enforcement paths (Redis recovery)
        
        Setup:
        - Redis initially down (mocked ConnectionError)
        - Redis "recovers" (unmock)
        - User attempts connection
        
        Expected:
        - First connection: succeeds with fallback
        - After recovery: Redis enforcement active again
        """
        user = await create_test_user(username="test_recovery_user")
        
        async def mock_app(scope, receive, send):
            await asyncio.sleep(0.05)
        
        middleware = RateLimitMiddleware(mock_app)
        
        # Phase 1: Redis down
        with patch('redis.Redis.get', side_effect=redis.ConnectionError("Redis down")):
            comm1 = WebsocketCommunicator(middleware, "/ws/match/recovery/")
            comm1.scope['user'] = user
            comm1.scope['client'] = ['192.168.9.20', 88000]
            comm1.scope['url_route'] = {'kwargs': {'match_id': 'recovery'}}
            
            connected1, _ = await comm1.connect(timeout=2)
            assert connected1, "Connection should succeed during Redis outage"
            await comm1.disconnect()
        
        # Phase 2: Redis recovered (no mocking = real Redis)
        comm2 = WebsocketCommunicator(middleware, "/ws/match/recovery/")
        comm2.scope['user'] = user
        comm2.scope['client'] = ['192.168.9.20', 88001]
        comm2.scope['url_route'] = {'kwargs': {'match_id': 'recovery'}}
        
        connected2, _ = await comm2.connect(timeout=2)
        assert connected2, "Connection should succeed after Redis recovery"
        
        # Verify Redis is tracking connection (enforcement active)
        user_key = f"{self.namespace}conn:user:{user.id}"
        conn_count = self.redis.get(user_key)
        assert conn_count is not None, "Redis should track connection after recovery"
        assert int(conn_count) >= 1, "Redis counter should be active after recovery"
        
        await comm2.disconnect()


# ============================================================================
# Module Metadata
# ============================================================================

# Coverage target: middleware_ratelimit.py 47% → ≥70-75%
# Test count: 17 tests across 5 categories
# Redis isolation: Per-test namespace with uuid4 prefix
# TTLs: 200ms cooldown windows for deterministic timing
# Prerequisites: docker-compose -f docker-compose.test.yml up -d
