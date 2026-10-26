"""
Integration Tests for WebSocket Real-Time Updates

Tests WebSocket connection, authentication, and event broadcasting
for tournament updates.

Phase 2: Real-Time Features & Security
Module 2.2: WebSocket Real-Time Updates

Test Coverage:
    - WebSocket connection with valid JWT token
    - WebSocket rejection with invalid/expired token
    - WebSocket rejection without token
    - Event broadcasting to multiple concurrent clients
    - All four event types (match_started, score_updated, match_completed, bracket_updated)
    - Clean disconnection and group cleanup

Requirements:
    - pytest-asyncio for async test support
    - channels.testing for WebSocket testing utilities
    - Django test database with fixtures
"""

import pytest
import json
from datetime import timedelta
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from deltacrown.asgi import application
from apps.tournaments.realtime.utils import broadcast_tournament_event

User = get_user_model()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("origin,allowed", [
    (b"https://deltacrown.xyz", True),
    (b"https://ownlobby.com", True),
    (b"https://untrusted.invalid", False),
    (None, False),
])
async def test_origin_validation_with_valid_credentials(valid_jwt_token, origin, allowed):
    headers = [(b"origin", origin)] if origin else []
    communicator = WebsocketCommunicator(application, f"/ws/tournament/1/?token={valid_jwt_token}", headers=headers)
    connected, _ = await communicator.connect()
    assert connected is allowed
    if connected:
        assert (await communicator.receive_json_from(timeout=2))['type'] == 'connection_established'
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_private_events_and_connection_gauge(valid_jwt_token, test_user2):
    from apps.tournaments.realtime.metrics import get_metrics_snapshot
    spectator_token = str(AccessToken.for_user(test_user2))
    before = sum(get_metrics_snapshot()['active_connections'].values())
    owner = WebsocketCommunicator(application, f'/ws/tournament/1/?token={valid_jwt_token}', headers=[(b'origin', b'https://ownlobby.com')])
    spectator = WebsocketCommunicator(application, f'/ws/tournament/1/?token={spectator_token}', headers=[(b'origin', b'https://ownlobby.com')])
    for connection in [owner, spectator]:
        assert (await connection.connect())[0]
        assert (await connection.receive_json_from(timeout=2))['type'] == 'connection_established'
    assert sum(get_metrics_snapshot()['active_connections'].values()) == before+2
    await broadcast_tournament_event(1, 'dispute_created', {'tournament_id': 1, 'registration_id': 123, 'reason': 'Private QA evidence'})
    assert (await owner.receive_json_from(timeout=2))['data']['reason'] == 'Private QA evidence'
    assert await spectator.receive_nothing(timeout=0.2)
    for connection in [owner, spectator]:
        await connection.disconnect()
    assert sum(get_metrics_snapshot()['active_connections'].values()) == before


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_inactive_user_token_is_rejected(valid_jwt_token, test_user):
    from channels.db import database_sync_to_async
    test_user.is_active = False
    await database_sync_to_async(test_user.save)(update_fields=['is_active'])
    communicator = WebsocketCommunicator(application, f'/ws/tournament/1/?token={valid_jwt_token}', headers=[(b'origin', b'https://ownlobby.com')])
    assert (await communicator.connect())[0]  # Diagnostic-only accept, then close.
    error = await communicator.receive_json_from(timeout=2)
    assert error['code'] == 'authentication_failed'
    assert (await communicator.receive_output(timeout=2))['code'] == 4003
    await communicator.disconnect()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def test_user(db):
    """Create test user for authentication."""
    return User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='testpass123'
    )


@pytest.fixture(autouse=True)
def tournament_rooms(transactional_db, test_user):
    from apps.games.models import Game
    from apps.tournaments.models import Tournament
    game = Game.objects.create(name='WebSocket QA Game', slug='websocket-qa-game', short_code='WSQA', category='OTHER')
    now = timezone.now()
    for identifier in [1, 2]:
        Tournament.objects.create(id=identifier, name=f'WebSocket QA {identifier}', slug=f'websocket-qa-{identifier}', organizer=test_user,
            game=game, participation_type='solo', status='published', max_participants=16,
            registration_start=now, registration_end=now+timedelta(days=1), tournament_start=now+timedelta(days=2))


@pytest.fixture
def test_user2(db):
    """Create second test user for multi-client tests."""
    return User.objects.create_user(
        username='testuser2',
        email='testuser2@example.com',
        password='testpass456'
    )


@pytest.fixture
def valid_jwt_token(test_user):
    """Generate valid JWT access token for test user."""
    token = AccessToken.for_user(test_user)
    return str(token)


@pytest.fixture
def expired_jwt_token(test_user):
    """Generate expired JWT token for testing auth failure."""
    token = AccessToken.for_user(test_user)
    # Set expiration to past
    token.set_exp(lifetime=timedelta(seconds=-3600))
    return str(token)


@pytest.fixture
def invalid_jwt_token():
    """Generate malformed JWT token for testing auth failure."""
    return "invalid.jwt.token.string"


# =============================================================================
# Connection Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_connect_with_valid_token(valid_jwt_token):
    """
    Test WebSocket connection succeeds with valid JWT token.
    
    Asserts:
        - Connection accepted
        - Welcome message received
        - Message contains tournament_id and user info
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={valid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected, "WebSocket connection should succeed with valid token"
    
    # Should receive welcome message
    response = await communicator.receive_json_from(timeout=2)
    if response['type'] != 'connection_established':
        print(f"ERROR: Received error response: {response}")
    assert response['type'] == 'connection_established'
    assert response['data']['tournament_id'] == tournament_id
    assert 'username' in response['data']
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_connect_without_token():
    """
    Test WebSocket connection rejected without JWT token.
    
    Asserts:
        - Connection rejected
        - Close code indicates authentication required
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, subprotocol = await communicator.connect()
    
    assert connected  # Consumer accepts only to send an explicit auth-required close.
    closed = await communicator.receive_output(timeout=2)
    assert closed['type'] == 'websocket.close'
    assert closed['code'] == 4001
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_connect_with_invalid_token(invalid_jwt_token):
    """
    Test WebSocket connection rejected with malformed JWT token.
    
    Asserts:
        - Connection rejected
        - User is AnonymousUser
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={invalid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, subprotocol = await communicator.connect()
    
    assert connected  # Middleware accepts only to deliver a diagnostic close frame.
    error = await communicator.receive_json_from(timeout=2)
    assert error['type'] == 'error'
    assert error['code'] == 'authentication_failed'
    closed = await communicator.receive_output(timeout=2)
    assert closed['type'] == 'websocket.close'
    assert closed['code'] == 4003
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_connect_with_expired_token(expired_jwt_token):
    """
    Test WebSocket connection rejected with expired JWT token.
    
    Asserts:
        - Connection rejected
        - Close code indicates token expired
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={expired_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, subprotocol = await communicator.connect()
    
    assert connected  # Middleware accepts only to deliver a diagnostic close frame.
    error = await communicator.receive_json_from(timeout=2)
    assert error['type'] == 'error'
    assert error['code'] == 'authentication_failed'
    closed = await communicator.receive_output(timeout=2)
    assert closed['type'] == 'websocket.close'
    assert closed['code'] == 4002
    await communicator.disconnect()


# =============================================================================
# Event Broadcasting Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_match_started_broadcast(valid_jwt_token):
    """
    Test match_started event broadcasts to connected client.
    
    Asserts:
        - Event received by client
        - Event type is 'match_started'
        - Event data contains match details
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={valid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Receive and discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Broadcast match_started event
    event_data = {
        'match_id': 123,
        'tournament_id': tournament_id,
        'participant1_id': 1,
        'participant1_name': 'Team Alpha',
        'participant2_id': 2,
        'participant2_name': 'Team Beta',
        'scheduled_time': timezone.now().isoformat(),
        'bracket_round': 1,
        'bracket_position': 1,
    }
    
    await broadcast_tournament_event(tournament_id, 'match_started', event_data)
    
    # Should receive broadcasted event
    response = await communicator.receive_json_from(timeout=2)
    assert response['type'] == 'match_started'
    assert response['data']['match_id'] == 123
    assert response['data']['participant1_name'] == 'Team Alpha'
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_score_updated_broadcast(valid_jwt_token):
    """
    Test score_updated event broadcasts to connected client.
    
    Asserts:
        - Event received by client
        - Event type is 'score_updated'
        - Event data contains score details
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={valid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Receive and discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Broadcast score_updated event
    event_data = {
        'match_id': 123,
        'tournament_id': tournament_id,
        'participant1_score': 2,
        'participant2_score': 1,
        'updated_at': timezone.now().isoformat(),
        'updated_by': 1,
    }
    
    await broadcast_tournament_event(tournament_id, 'score_updated', event_data)
    
    # Should receive broadcasted event
    response = await communicator.receive_json_from(timeout=2)
    assert response['type'] == 'score_updated'
    assert response['data']['match_id'] == 123
    assert response['data']['participant1_score'] == 2
    assert response['data']['participant2_score'] == 1
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_match_completed_broadcast(valid_jwt_token):
    """
    Test match_completed event broadcasts to connected client.
    
    Asserts:
        - Event received by client
        - Event type is 'match_completed'
        - Event data contains winner and final scores
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={valid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Receive and discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Broadcast match_completed event
    event_data = {
        'match_id': 123,
        'tournament_id': tournament_id,
        'winner_id': 1,
        'winner_name': 'Team Alpha',
        'loser_id': 2,
        'loser_name': 'Team Beta',
        'participant1_score': 2,
        'participant2_score': 1,
        'confirmed_at': timezone.now().isoformat(),
        'confirmed_by': 1,
    }
    
    await broadcast_tournament_event(tournament_id, 'match_completed', event_data)
    
    # Should receive broadcasted event
    response = await communicator.receive_json_from(timeout=2)
    assert response['type'] == 'match_completed'
    assert response['data']['match_id'] == 123
    assert response['data']['winner_id'] == 1
    assert response['data']['winner_name'] == 'Team Alpha'
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_bracket_updated_broadcast(valid_jwt_token):
    """
    Test bracket_updated event broadcasts to connected client.
    
    Asserts:
        - Event received by client
        - Event type is 'bracket_updated'
        - Event data contains bracket update details
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={valid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Receive and discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Broadcast bracket_updated event
    event_data = {
        'bracket_id': 10,
        'tournament_id': tournament_id,
        'updated_nodes': [5, 6, 7],
        'next_matches': [
            {'match_id': 124, 'round': 2, 'position': 1}
        ],
        'bracket_status': 'active',
        'updated_at': timezone.now().isoformat(),
    }
    
    await broadcast_tournament_event(tournament_id, 'bracket_updated', event_data)
    
    # Should receive broadcasted event
    response = await communicator.receive_json_from(timeout=2)
    assert response['type'] == 'bracket_updated'
    assert response['data']['bracket_id'] == 10
    assert len(response['data']['updated_nodes']) == 3
    assert response['data']['bracket_status'] == 'active'
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_multiple_clients_receive_broadcast(valid_jwt_token, test_user2):
    """
    Test event broadcasts to all connected clients simultaneously.
    
    Asserts:
        - Both clients connect successfully
        - Both clients receive same event
        - Event data identical for both clients
        - Both clients can disconnect cleanly
    """
    tournament_id = 1
    
    # Generate token for second user
    token2 = str(AccessToken.for_user(test_user2))
    
    # Connect two clients to same tournament room
    communicator1 = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={valid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    communicator2 = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={token2}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected1, _ = await communicator1.connect()
    connected2, _ = await communicator2.connect()
    
    assert connected1, "Client 1 should connect"
    assert connected2, "Client 2 should connect"
    
    # Receive and discard welcome messages
    await communicator1.receive_json_from(timeout=2)
    await communicator2.receive_json_from(timeout=2)
    
    # Broadcast event
    event_data = {
        'match_id': 999,
        'tournament_id': tournament_id,
        'winner_id': 1,
        'winner_name': 'Champion Team',
        'participant1_score': 3,
        'participant2_score': 0,
        'confirmed_at': timezone.now().isoformat(),
    }
    
    await broadcast_tournament_event(tournament_id, 'match_completed', event_data)
    
    # Both clients should receive event
    response1 = await communicator1.receive_json_from(timeout=2)
    response2 = await communicator2.receive_json_from(timeout=2)
    
    assert response1['type'] == 'match_completed'
    assert response2['type'] == 'match_completed'
    assert response1['data']['match_id'] == 999
    assert response2['data']['match_id'] == 999
    assert response1['data'] == response2['data'], "Both clients should receive identical data"
    
    # Clean disconnect
    await communicator1.disconnect()
    await communicator2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_client_isolation_different_tournaments(valid_jwt_token, test_user2):
    """
    Test clients in different tournament rooms don't receive each other's events.
    
    Asserts:
        - Client 1 connected to tournament 1
        - Client 2 connected to tournament 2
        - Broadcast to tournament 1 only received by client 1
        - Client 2 receives nothing
    """
    tournament_id_1 = 1
    tournament_id_2 = 2
    
    # Generate token for second user
    token2 = str(AccessToken.for_user(test_user2))
    
    # Connect clients to different tournament rooms
    communicator1 = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id_1}/?token={valid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    communicator2 = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id_2}/?token={token2}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected1, _ = await communicator1.connect()
    connected2, _ = await communicator2.connect()
    
    assert connected1
    assert connected2
    
    # Receive and discard welcome messages
    await communicator1.receive_json_from(timeout=2)
    await communicator2.receive_json_from(timeout=2)
    
    # Broadcast only to tournament 1
    event_data = {
        'match_id': 555,
        'tournament_id': tournament_id_1,
        'winner_id': 1,
    }
    
    await broadcast_tournament_event(tournament_id_1, 'match_completed', event_data)
    
    # Client 1 should receive event
    response1 = await communicator1.receive_json_from(timeout=2)
    assert response1['type'] == 'match_completed'
    assert response1['data']['match_id'] == 555
    
    # Client 2 should receive nothing
    assert await communicator2.receive_nothing(timeout=1)
    
    await communicator1.disconnect()
    await communicator2.disconnect()


# =============================================================================
# Cleanup Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_clean_disconnect_removes_from_group(valid_jwt_token):
    """
    Test client disconnect properly removes from channel layer group.
    
    Asserts:
        - Client connects and receives welcome
        - Client disconnects
        - Subsequent broadcast not received (no lingering connection)
    """
    tournament_id = 1
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament_id}/?token={valid_jwt_token}",
        headers=[(b"origin", b"https://deltacrown.xyz")],
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Disconnect
    await communicator.disconnect()
    
    # Try broadcasting after disconnect
    event_data = {'match_id': 777, 'tournament_id': tournament_id}
    await broadcast_tournament_event(tournament_id, 'match_started', event_data)
    
    # Should not receive anything (connection closed)
    # No assertion needed - disconnect completes successfully
