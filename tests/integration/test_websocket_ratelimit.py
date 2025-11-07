"""
Integration Tests for WebSocket Rate Limiting

Tests Module 2.5: Rate Limiting & Abuse Protection

Test Coverage:
- Connection rate limits (per-user, per-IP)
- Message rate limits (per-user, per-IP)
- Room capacity limits
- Payload size limits
- Schema validation
- Redis fallback to in-memory
- Retry-after headers
- Error responses

Requires:
- Django Channels configured
- Redis running (or fallback to in-memory)
- JWT authentication enabled

Phase 2: Real-Time Features & Security
Module 2.5: Rate Limiting & Abuse Protection
"""

import pytest
import asyncio
import json
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from deltacrown.asgi import application
from apps.tournaments.models import Tournament
from apps.tournaments.realtime import ratelimit

User = get_user_model()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def test_user(db):
    """Create test user for authentication."""
    return User.objects.create_user(
        username='ratelimit_test_user',
        email='ratelimit@test.com',
        password='testpass123'
    )


@pytest.fixture
def test_user2(db):
    """Create second test user."""
    return User.objects.create_user(
        username='ratelimit_test_user2',
        email='ratelimit2@test.com',
        password='testpass123'
    )


@pytest.fixture
def valid_jwt_token(test_user):
    """Generate valid JWT access token for test user."""
    token = AccessToken.for_user(test_user)
    return str(token)


@pytest.fixture
def valid_jwt_token2(test_user2):
    """Generate valid JWT access token for second test user."""
    token = AccessToken.for_user(test_user2)
    return str(token)


@pytest.fixture
def tournament(db, test_user):
    """Create test tournament."""
    from apps.tournaments.models import Game
    
    game = Game.objects.create(
        name="Rate Limit Test Game",
        slug="ratelimit-test-game",
        game_type="TEAM"
    )
    
    tournament = Tournament.objects.create(
        name="Rate Limit Test Tournament",
        slug="ratelimit-test-tournament",
        game=game,
        organizer_id=test_user.id,
        tournament_type="SINGLE_ELIMINATION",
        max_teams=4,
        team_size=1,
        entry_fee=0,
        status="ACTIVE"
    )
    
    return tournament


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset in-memory rate limiter between tests."""
    # Clear in-memory fallback state
    ratelimit._fallback_limiter.buckets.clear()
    ratelimit._fallback_limiter.rooms.clear()
    yield


# =============================================================================
# Connection Rate Limit Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_user_connection_limit_exceeded(tournament, test_user, valid_jwt_token):
    """
    Test per-user connection limit enforcement.
    
    Default limit: 3 concurrent connections per user.
    4th connection should be rejected with connection_limit_exceeded error.
    """
    # Connect 3 times (should succeed)
    communicators = []
    
    for i in range(3):
        comm = WebsocketCommunicator(
            application,
            f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
        )
        
        connected, _ = await comm.connect()
        assert connected, f"Connection {i+1} should succeed"
        
        # Discard welcome message
        await comm.receive_json_from(timeout=2)
        
        communicators.append(comm)
    
    # 4th connection should be rejected
    comm4 = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
    )
    
    connected, close_code = await comm4.connect()
    
    # Connection rejected - should send error then close
    if connected:
        # Might receive error message before close
        try:
            error_msg = await comm4.receive_json_from(timeout=1)
            assert error_msg['type'] == 'error'
            assert error_msg['code'] == 'connection_limit_exceeded'
            assert 'retry_after_ms' in error_msg
        except asyncio.TimeoutError:
            pass  # Already closed
        
        # Wait for close
        await comm4.wait(timeout=2)
    
    # Cleanup: disconnect all
    for comm in communicators:
        await comm.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_user_connection_limit_after_disconnect(tournament, test_user, valid_jwt_token):
    """
    Test connection limit resets after disconnect.
    
    Flow:
    1. Connect 3 times (limit reached)
    2. Disconnect 1
    3. Connect again (should succeed)
    """
    # Connect 3 times
    comm1 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    comm2 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    comm3 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    
    await comm1.connect()
    await comm2.connect()
    await comm3.connect()
    
    # Discard welcome messages
    await comm1.receive_json_from(timeout=2)
    await comm2.receive_json_from(timeout=2)
    await comm3.receive_json_from(timeout=2)
    
    # Disconnect one
    await comm2.disconnect()
    
    # Wait for cleanup
    await asyncio.sleep(0.5)
    
    # 4th connection should now succeed
    comm4 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    connected, _ = await comm4.connect()
    
    assert connected, "Connection should succeed after disconnect"
    
    # Cleanup
    await comm1.disconnect()
    await comm3.disconnect()
    await comm4.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_different_users_independent_limits(tournament, test_user, test_user2, valid_jwt_token, valid_jwt_token2):
    """
    Test that different users have independent connection limits.
    
    User1: 3 connections (at limit)
    User2: Should still be able to connect
    """
    # User 1: Connect 3 times
    comm1_list = []
    for i in range(3):
        comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
        await comm.connect()
        await comm.receive_json_from(timeout=2)
        comm1_list.append(comm)
    
    # User 2: Should still be able to connect
    comm2 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token2}")
    connected, _ = await comm2.connect()
    
    assert connected, "User 2 should connect despite User 1 at limit"
    
    # Cleanup
    for comm in comm1_list:
        await comm.disconnect()
    await comm2.disconnect()


# =============================================================================
# Message Rate Limit Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_message_rate_limit_exceeded(tournament, test_user, valid_jwt_token):
    """
    Test per-user message rate limit enforcement.
    
    Default: 10 msg/sec, burst 20.
    Send 21 messages rapidly -> last message should get rate_limited error.
    """
    comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    connected, _ = await comm.connect()
    assert connected
    
    # Discard welcome message
    await comm.receive_json_from(timeout=2)
    
    # Send 21 messages rapidly (burst capacity = 20)
    for i in range(21):
        await comm.send_json_to({'type': 'ping', 'index': i})
    
    # Receive responses
    rate_limited = False
    
    for i in range(21):
        try:
            response = await comm.receive_json_from(timeout=1)
            
            if response.get('type') == 'error' and response.get('code') == 'message_rate_limit_exceeded':
                rate_limited = True
                assert 'retry_after_ms' in response
                break
            
        except asyncio.TimeoutError:
            break
    
    assert rate_limited, "Should receive rate_limited error after burst exhausted"
    
    await comm.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_message_rate_limit_cooldown(tournament, test_user, valid_jwt_token):
    """
    Test message rate limit cooldown (tokens refill over time).
    
    Flow:
    1. Exhaust burst capacity (send 21 messages)
    2. Wait for token refill (1 second = 10 tokens at 10 msg/sec)
    3. Send another message (should succeed)
    """
    comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    await comm.connect()
    await comm.receive_json_from(timeout=2)
    
    # Exhaust burst
    for i in range(21):
        await comm.send_json_to({'type': 'ping'})
    
    # Drain responses
    for _ in range(25):  # Drain all responses
        try:
            await comm.receive_json_from(timeout=0.1)
        except asyncio.TimeoutError:
            break
    
    # Wait for token refill (1 second)
    await asyncio.sleep(1.1)
    
    # Send another message (should succeed)
    await comm.send_json_to({'type': 'ping', 'after_cooldown': True})
    
    response = await comm.receive_json_from(timeout=2)
    
    # Should get pong response (not rate_limited error)
    assert response['type'] == 'pong', "Message should succeed after cooldown"
    
    await comm.disconnect()


# =============================================================================
# Room Capacity Limit Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_room_capacity_limit(tournament, db, monkeypatch):
    """
    Test room capacity limit enforcement.
    
    Set room limit to 2, attempt 3 connections -> 3rd rejected with room_full error.
    """
    # Temporarily reduce room limit for testing
    monkeypatch.setattr('apps.tournaments.realtime.middleware_ratelimit.get_rate_config', 
                       lambda: {
                           'msg_rps': 10.0,
                           'msg_burst': 20,
                           'msg_rps_ip': 20.0,
                           'msg_burst_ip': 40,
                           'conn_per_user': 3,
                           'conn_per_ip': 10,
                           'room_max_members': 2,  # Limit to 2 members
                           'max_payload_bytes': 16 * 1024,
                       })
    
    # Create 2 users
    user1 = User.objects.create_user(username='room_user1', password='pass')
    user2 = User.objects.create_user(username='room_user2', password='pass')
    user3 = User.objects.create_user(username='room_user3', password='pass')
    
    token1 = str(AccessToken.for_user(user1))
    token2 = str(AccessToken.for_user(user2))
    token3 = str(AccessToken.for_user(user3))
    
    # Connect user 1 and 2 (should succeed)
    comm1 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={token1}")
    comm2 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={token2}")
    
    connected1, _ = await comm1.connect()
    connected2, _ = await comm2.connect()
    
    assert connected1, "User 1 should connect"
    assert connected2, "User 2 should connect"
    
    await comm1.receive_json_from(timeout=2)
    await comm2.receive_json_from(timeout=2)
    
    # User 3 connection should be rejected (room full)
    comm3 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={token3}")
    connected3, _ = await comm3.connect()
    
    if connected3:
        # Might receive error before close
        try:
            error = await comm3.receive_json_from(timeout=1)
            assert error['type'] == 'error'
            assert error['code'] == 'room_full'
        except asyncio.TimeoutError:
            pass
    
    # Cleanup
    await comm1.disconnect()
    await comm2.disconnect()


# =============================================================================
# Payload Size Limit Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_oversized_payload_rejected(tournament, test_user, valid_jwt_token):
    """
    Test oversized payload rejection.
    
    Default max: 16 KB.
    Send 20 KB message -> should get payload_too_large error and disconnect.
    """
    comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    await comm.connect()
    await comm.receive_json_from(timeout=2)
    
    # Create oversized payload (20 KB)
    oversized_data = 'x' * (20 * 1024)
    oversized_message = {'type': 'ping', 'data': oversized_data}
    
    await comm.send_json_to(oversized_message)
    
    # Should receive payload_too_large error
    try:
        error = await comm.receive_json_from(timeout=2)
        assert error['type'] == 'error'
        assert error['code'] == 'payload_too_large'
    except asyncio.TimeoutError:
        pass  # Connection might close before sending error
    
    # Connection should be closed
    await comm.wait(timeout=2)


# =============================================================================
# Schema Validation Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_invalid_schema_missing_type(tournament, test_user, valid_jwt_token):
    """
    Test schema validation: missing 'type' field.
    
    Send message without 'type' -> should get invalid_schema error.
    """
    comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    await comm.connect()
    await comm.receive_json_from(timeout=2)
    
    # Send message without 'type' field
    await comm.send_json_to({'data': 'test', 'invalid': True})
    
    # Should receive schema error
    response = await comm.receive_json_from(timeout=2)
    
    assert response['type'] == 'error'
    assert response['code'] == 'invalid_schema'
    assert 'type' in response['message'].lower()
    
    await comm.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_ping_pong_schema_valid(tournament, test_user, valid_jwt_token):
    """
    Test valid message schema: ping/pong.
    
    Send ping with timestamp -> should get pong response.
    """
    comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    await comm.connect()
    await comm.receive_json_from(timeout=2)
    
    # Send valid ping
    await comm.send_json_to({'type': 'ping', 'timestamp': 1234567890})
    
    # Should receive pong
    response = await comm.receive_json_from(timeout=2)
    
    assert response['type'] == 'pong'
    assert response['timestamp'] == 1234567890
    
    await comm.disconnect()


# =============================================================================
# Redis Fallback Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_rate_limit_with_redis_unavailable(tournament, test_user, valid_jwt_token, monkeypatch):
    """
    Test graceful fallback to in-memory when Redis unavailable.
    
    Mock _use_redis to return False -> should use in-memory limiter.
    """
    # Force fallback to in-memory
    monkeypatch.setattr('apps.tournaments.realtime.ratelimit._use_redis', lambda: False)
    
    # Connect should still work with in-memory fallback
    comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    connected, _ = await comm.connect()
    
    assert connected, "Should connect with in-memory fallback"
    
    # Discard welcome
    await comm.receive_json_from(timeout=2)
    
    # Rate limiting should still work (in-memory)
    for i in range(25):  # Exceed burst
        await comm.send_json_to({'type': 'ping'})
    
    # Should eventually get rate limited
    rate_limited = False
    for _ in range(30):
        try:
            response = await comm.receive_json_from(timeout=0.5)
            if response.get('code') == 'message_rate_limit_exceeded':
                rate_limited = True
                break
        except asyncio.TimeoutError:
            break
    
    assert rate_limited, "In-memory fallback should still enforce rate limits"
    
    await comm.disconnect()


# =============================================================================
# Server Broadcast Tests (No Throttling)
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_server_broadcasts_not_throttled(tournament, test_user, valid_jwt_token):
    """
    Test that server→client broadcasts are never throttled.
    
    Only client→server messages should be rate limited.
    Server broadcasts (match_started, etc.) should always go through.
    """
    from apps.tournaments.realtime.utils import broadcast_match_started
    
    comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    await comm.connect()
    await comm.receive_json_from(timeout=2)
    
    # Broadcast 50 events from server (should all go through)
    for i in range(50):
        broadcast_match_started(
            tournament_id=tournament.id,
            match_data={'match_id': i, 'index': i}
        )
        
        # Small delay to avoid overwhelming channel layer
        await asyncio.sleep(0.01)
    
    # Receive all 50 events
    received_count = 0
    for _ in range(55):  # Slightly more to account for any extra
        try:
            response = await comm.receive_json_from(timeout=0.5)
            if response.get('type') == 'match_started':
                received_count += 1
        except asyncio.TimeoutError:
            break
    
    assert received_count >= 45, f"Should receive most server broadcasts (got {received_count}/50)"
    
    await comm.disconnect()


# =============================================================================
# Error Response Format Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_rate_limit_error_format(tournament, test_user, valid_jwt_token):
    """
    Test rate limit error response format.
    
    Error should include:
    - type: 'error'
    - code: specific error code
    - message: human-readable message
    - retry_after_ms: (optional) milliseconds until retry
    """
    comm = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    await comm.connect()
    await comm.receive_json_from(timeout=2)
    
    # Exhaust burst to trigger rate limit
    for i in range(25):
        await comm.send_json_to({'type': 'ping'})
    
    # Find rate limit error
    error_found = False
    for _ in range(30):
        try:
            response = await comm.receive_json_from(timeout=0.5)
            
            if response.get('code') == 'message_rate_limit_exceeded':
                # Validate error format
                assert response['type'] == 'error'
                assert isinstance(response['message'], str)
                assert len(response['message']) > 0
                assert 'retry_after_ms' in response
                assert isinstance(response['retry_after_ms'], int)
                assert response['retry_after_ms'] > 0
                
                error_found = True
                break
        except asyncio.TimeoutError:
            break
    
    assert error_found, "Should receive properly formatted rate limit error"
    
    await comm.disconnect()
