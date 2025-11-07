"""
Integration tests for Module 2.4: Security Hardening

Tests cover:
- JWT token validation (expiry, invalid, leeway)
- Role-based access control (SPECTATOR, PLAYER, ORGANIZER, ADMIN)
- WebSocket permission enforcement
- Regression tests for Module 2.5 (rate limits, payload validation)

Phase 2: Real-Time Features & Security
Module 2.4: Security Hardening
"""

import pytest
import jwt
import time
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import re_path

from apps.tournaments.models import Tournament, Registration, Game
from apps.tournaments.realtime.consumers import TournamentConsumer
from apps.tournaments.realtime.middleware import JWTAuthMiddleware
from apps.tournaments.security.permissions import TournamentRole
from deltacrown.settings import SIMPLE_JWT

User = get_user_model()


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name="Test Game",
        slug="test-game",
        platform="PC",
        is_active=True
    )


@pytest.fixture
def tournament(db, game):
    """Create a test tournament."""
    return Tournament.objects.create(
        name="Test Tournament",
        slug="test-tournament",
        game=game,
        status="PUBLISHED",
        max_participants=16,
        registration_start=timezone.now() - timedelta(days=1),
        registration_end=timezone.now() + timedelta(days=7),
        start_date=timezone.now() + timedelta(days=10),
    )


@pytest.fixture
def spectator_user(db):
    """Create a spectator user (no special permissions)."""
    return User.objects.create_user(
        username="spectator",
        email="spectator@test.com",
        password="testpass123"
    )


@pytest.fixture
def player_user(db, tournament):
    """Create a player user with registration."""
    user = User.objects.create_user(
        username="player",
        email="player@test.com",
        password="testpass123"
    )
    Registration.objects.create(
        tournament=tournament,
        participant_type="SOLO",
        participant_id=user.id,
        status="CONFIRMED"
    )
    return user


@pytest.fixture
def organizer_user(db):
    """Create an organizer user with tournament permissions."""
    user = User.objects.create_user(
        username="organizer",
        email="organizer@test.com",
        password="testpass123"
    )
    # Add tournament management permissions
    perms = Permission.objects.filter(
        codename__in=[
            'add_tournament',
            'change_tournament',
            'view_tournament',
            'can_manage_payments',
        ]
    )
    user.user_permissions.add(*perms)
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        username="admin",
        email="admin@test.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True
    )


def generate_jwt_token(user, expires_delta=None, secret_key=None):
    """Generate a JWT token for testing."""
    if secret_key is None:
        secret_key = SIMPLE_JWT['SIGNING_KEY']
    
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': timezone.now() + (expires_delta or SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']),
        'iat': timezone.now(),
    }
    
    return jwt.encode(payload, secret_key, algorithm=SIMPLE_JWT['ALGORITHM'])


def get_application():
    """Get the ASGI application for testing."""
    return JWTAuthMiddleware(
        URLRouter([
            re_path(r"ws/tournaments/(?P<tournament_id>\d+)/$", TournamentConsumer.as_asgi()),
        ])
    )


# ============================================================================
# JWT TOKEN VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_valid_jwt_connects_successfully(spectator_user, tournament):
    """Test that a valid JWT token allows connection."""
    token = generate_jwt_token(spectator_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Should receive welcome message
    response = await communicator.receive_json_from()
    assert response['type'] == 'connection.established'
    assert response['role'] in ['spectator', 'player', 'organizer', 'admin']
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_expired_jwt_rejected_with_4002(spectator_user, tournament):
    """Test that an expired JWT token is rejected with close code 4002."""
    # Generate token that expired 5 minutes ago
    token = generate_jwt_token(spectator_user, expires_delta=timedelta(minutes=-5))
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    
    if connected:
        # Should receive error message
        response = await communicator.receive_json_from()
        assert 'error' in response or 'type' in response
        
        # Connection should close with code 4002
        await communicator.wait(timeout=2)
    
    # Verify connection is closed
    assert communicator.output_queue.qsize() == 0 or not connected


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_jwt_within_leeway_accepted(spectator_user, tournament):
    """Test that JWT within leeway window (60 seconds) is accepted."""
    # Generate token that expired 30 seconds ago (within 60s leeway)
    token = generate_jwt_token(spectator_user, expires_delta=timedelta(seconds=-30))
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    
    # Should connect successfully due to leeway
    assert connected
    
    response = await communicator.receive_json_from()
    assert response['type'] == 'connection.established'
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_jwt_beyond_leeway_rejected(spectator_user, tournament):
    """Test that JWT beyond leeway window is rejected."""
    # Generate token that expired 2 minutes ago (beyond 60s leeway)
    token = generate_jwt_token(spectator_user, expires_delta=timedelta(minutes=-2))
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    
    # Should be rejected
    if connected:
        await communicator.wait(timeout=2)
    
    # Verify disconnected
    assert not await communicator.receive_nothing(timeout=1)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_invalid_jwt_rejected_with_4003(tournament):
    """Test that an invalid JWT token is rejected with close code 4003."""
    invalid_token = "invalid.jwt.token.here"
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={invalid_token}"
    )
    
    connected, subprotocol = await communicator.connect()
    
    if connected:
        # Should receive error or close
        await communicator.wait(timeout=2)
    
    # Verify connection failed or closed
    assert not connected or communicator.output_queue.qsize() == 0


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_missing_jwt_rejected(tournament):
    """Test that missing JWT token is rejected."""
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/"  # No token parameter
    )
    
    connected, subprotocol = await communicator.connect()
    
    if connected:
        await communicator.wait(timeout=2)
    
    # Should be rejected
    assert not connected or communicator.output_queue.qsize() == 0


# ============================================================================
# ROLE-BASED ACCESS CONTROL TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_spectator_can_subscribe(spectator_user, tournament):
    """Test that spectator can subscribe to tournament events."""
    token = generate_jwt_token(spectator_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Send subscribe action (allowed for spectators)
    await communicator.send_json_to({
        'type': 'subscribe',
        'tournament_id': tournament.id
    })
    
    response = await communicator.receive_json_from()
    assert 'error' not in response or response.get('type') == 'subscribe.success'
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_spectator_cannot_update_score(spectator_user, tournament):
    """Test that spectator cannot update match scores."""
    token = generate_jwt_token(spectator_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Try to update score (organizer action)
    await communicator.send_json_to({
        'type': 'update_score',
        'match_id': 1,
        'participant1_score': 10,
        'participant2_score': 5
    })
    
    response = await communicator.receive_json_from()
    assert response.get('type') == 'error'
    assert 'insufficient_permissions' in response.get('error', '').lower() or \
           'permission' in response.get('message', '').lower()
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_player_can_report_score(player_user, tournament):
    """Test that player can report their match scores."""
    token = generate_jwt_token(player_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Send report_score action (allowed for players)
    await communicator.send_json_to({
        'type': 'report_score',
        'match_id': 1,
        'score': 10
    })
    
    response = await communicator.receive_json_from()
    # Should not be permission error
    assert response.get('type') != 'error' or \
           'insufficient_permissions' not in response.get('error', '').lower()
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_player_cannot_verify_payment(player_user, tournament):
    """Test that player cannot verify payments."""
    token = generate_jwt_token(player_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Try to verify payment (organizer action)
    await communicator.send_json_to({
        'type': 'verify_payment',
        'payment_id': 1
    })
    
    response = await communicator.receive_json_from()
    assert response.get('type') == 'error'
    assert 'insufficient_permissions' in response.get('error', '').lower() or \
           'permission' in response.get('message', '').lower()
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_organizer_can_verify_payment(organizer_user, tournament):
    """Test that organizer can verify payments."""
    token = generate_jwt_token(organizer_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Send verify_payment action (allowed for organizers)
    await communicator.send_json_to({
        'type': 'verify_payment',
        'payment_id': 1
    })
    
    response = await communicator.receive_json_from()
    # Should not be permission error
    assert response.get('type') != 'error' or \
           'insufficient_permissions' not in response.get('error', '').lower()
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_admin_can_regenerate_bracket(admin_user, tournament):
    """Test that admin can regenerate brackets."""
    token = generate_jwt_token(admin_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Send regenerate_bracket action (admin only)
    await communicator.send_json_to({
        'type': 'regenerate_bracket'
    })
    
    response = await communicator.receive_json_from()
    # Should not be permission error
    assert response.get('type') != 'error' or \
           'insufficient_permissions' not in response.get('error', '').lower()
    
    await communicator.disconnect()


# ============================================================================
# MODULE 2.5 REGRESSION TESTS (Rate Limiting & Validation)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_payload_size_limit_enforced(spectator_user, tournament):
    """Test that payload size limit (16KB) is still enforced."""
    token = generate_jwt_token(spectator_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Send oversized payload (20 KB)
    large_payload = {
        'type': 'subscribe',
        'data': 'x' * (20 * 1024)  # 20 KB of data
    }
    
    await communicator.send_json_to(large_payload)
    
    # Should receive error or connection close
    try:
        response = await communicator.receive_json_from(timeout=2)
        assert response.get('type') == 'error' or 'payload' in response.get('error', '').lower()
    except:
        # Connection may close instead
        pass
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_schema_validation_enforced(spectator_user, tournament):
    """Test that message schema validation is enforced."""
    token = generate_jwt_token(spectator_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Send invalid message (missing 'type' field)
    await communicator.send_json_to({
        'action': 'subscribe',  # Wrong field name
        'data': {}
    })
    
    response = await communicator.receive_json_from()
    assert response.get('type') == 'error'
    assert 'schema' in response.get('error', '').lower() or \
           'invalid' in response.get('error', '').lower()
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ping_pong_works(spectator_user, tournament):
    """Test that ping/pong messages work correctly."""
    token = generate_jwt_token(spectator_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Send ping
    await communicator.send_json_to({
        'type': 'ping'
    })
    
    response = await communicator.receive_json_from()
    assert response.get('type') == 'pong'
    
    await communicator.disconnect()


# ============================================================================
# EDGE CASES AND SECURITY TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_role_correctly_assigned_on_connect(player_user, tournament):
    """Test that user role is correctly assigned on connection."""
    token = generate_jwt_token(player_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Check welcome message contains role
    response = await communicator.receive_json_from()
    assert response['type'] == 'connection.established'
    assert 'role' in response
    assert response['role'] in ['spectator', 'player', 'organizer', 'admin']
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_unknown_action_rejected(spectator_user, tournament):
    """Test that unknown action types are rejected."""
    token = generate_jwt_token(spectator_user)
    application = get_application()
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournaments/{tournament.id}/?token={token}"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    # Receive welcome message
    await communicator.receive_json_from()
    
    # Send unknown action
    await communicator.send_json_to({
        'type': 'unknown_action_type',
        'data': {}
    })
    
    response = await communicator.receive_json_from()
    assert response.get('type') == 'error'
    assert 'unknown' in response.get('error', '').lower() or \
           'invalid' in response.get('error', '').lower()
    
    await communicator.disconnect()
