"""
Integration Tests for MatchService Real-Time Broadcasting

Tests end-to-end WebSocket event flow for match lifecycle:
- transition_to_live() → match_started broadcast
- submit_result() → score_updated broadcast  
- confirm_result() → match_completed broadcast (+ bracket_updated via BracketService)

Phase 2: Real-Time Features & Security
Module 2.3: Service Layer Integration

Test Coverage:
- Match start broadcasts match_started event
- Score submission broadcasts score_updated event
- Result confirmation broadcasts match_completed event
- Result confirmation triggers bracket_updated broadcast (via BracketService)
- Multiple clients receive all events in same tournament room
- Events contain correct payload data
- Transaction atomicity preserved (broadcast failures don't break state changes)
"""

import pytest
from datetime import datetime, timedelta
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from deltacrown.asgi import application
from apps.tournaments.models import Tournament, Match, Bracket, BracketNode, Registration
from apps.tournaments.services.match_service import MatchService
from apps.tournaments.services.bracket_service import BracketService

User = get_user_model()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def test_user(db):
    """Create test user for authentication."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123'
    )


@pytest.fixture
def valid_jwt_token(test_user):
    """Generate valid JWT access token for test user."""
    token = AccessToken.for_user(test_user)
    return str(token)


@pytest.fixture
def tournament(db, test_user):
    """Create test tournament."""
    from apps.tournaments.models import Game
    
    game = Game.objects.create(
        name="Test Game",
        slug="test-game",
        game_type="TEAM"
    )
    
    tournament = Tournament.objects.create(
        name="WebSocket Test Tournament",
        slug="ws-test-tournament",
        game=game,
        organizer_id=test_user.id,
        tournament_type="SINGLE_ELIMINATION",
        max_teams=4,
        team_size=1,
        entry_fee=0,
        status="REGISTRATION_OPEN"
    )
    
    return tournament


@pytest.fixture
def match_ready(db, tournament):
    """Create a match ready to start (READY state)."""
    match = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=1,
        participant1_name="Player 1",
        participant2_id=2,
        participant2_name="Player 2",
        status=Match.READY,
        scheduled_time=timezone.now()
    )
    return match


@pytest.fixture
def match_live(db, tournament):
    """Create a match in LIVE state."""
    match = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=2,
        participant1_id=3,
        participant1_name="Player 3",
        participant2_id=4,
        participant2_name="Player 4",
        status=Match.LIVE,
        started_at=timezone.now()
    )
    return match


@pytest.fixture
def match_with_result(db, tournament):
    """Create a match with submitted result (PENDING_RESULT state)."""
    match = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=3,
        participant1_id=5,
        participant1_name="Player 5",
        participant2_id=6,
        participant2_name="Player 6",
        status=Match.PENDING_RESULT,
        participant1_score=2,
        participant2_score=1,
        winner_id=5,
        loser_id=6
    )
    return match


# =============================================================================
# Match Start Tests (transition_to_live → match_started)
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_match_start_broadcasts_match_started(tournament, match_ready, valid_jwt_token):
    """
    Test transition_to_live() broadcasts match_started event.
    
    Flow:
    1. Connect WebSocket client to tournament room
    2. Call MatchService.transition_to_live()
    3. Verify client receives match_started event
    4. Verify event payload contains correct match data
    """
    # Connect WebSocket client
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
    )
    
    connected, _ = await communicator.connect()
    assert connected, "WebSocket should connect successfully"
    
    # Discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Transition match to LIVE (should broadcast match_started)
    MatchService.transition_to_live(match_ready)
    
    # Receive match_started event
    response = await communicator.receive_json_from(timeout=2)
    
    # Verify event type
    assert response['type'] == 'match_started', f"Expected match_started, got {response['type']}"
    
    # Verify payload
    data = response['data']
    assert data['match_id'] == match_ready.id
    assert data['tournament_id'] == tournament.id
    assert data['status'] == Match.LIVE
    assert data['participant1_name'] == "Player 1"
    assert data['participant2_name'] == "Player 2"
    assert data['round'] == 1
    assert 'started_at' in data
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_match_start_multiple_clients_receive_event(tournament, match_ready, valid_jwt_token, test_user):
    """
    Test match_started event broadcasts to multiple concurrent clients.
    
    Verifies:
    - Both clients receive identical match_started event
    - No race conditions in broadcasting
    """
    # Create second token
    user2 = User.objects.create_user(username='spectator', email='spec@test.com', password='pass')
    token2 = str(AccessToken.for_user(user2))
    
    # Connect two clients
    comm1 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    comm2 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={token2}")
    
    await comm1.connect()
    await comm2.connect()
    
    # Discard welcome messages
    await comm1.receive_json_from(timeout=2)
    await comm2.receive_json_from(timeout=2)
    
    # Transition match to LIVE
    MatchService.transition_to_live(match_ready)
    
    # Both clients should receive event
    response1 = await comm1.receive_json_from(timeout=2)
    response2 = await comm2.receive_json_from(timeout=2)
    
    assert response1['type'] == 'match_started'
    assert response2['type'] == 'match_started'
    assert response1['data']['match_id'] == response2['data']['match_id']
    
    await comm1.disconnect()
    await comm2.disconnect()


# =============================================================================
# Score Update Tests (submit_result → score_updated)
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_score_submission_broadcasts_score_updated(tournament, match_live, valid_jwt_token):
    """
    Test submit_result() broadcasts score_updated event.
    
    Flow:
    1. Connect WebSocket client
    2. Call MatchService.submit_result()
    3. Verify client receives score_updated event
    4. Verify scores and winner in payload
    """
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Submit result (should broadcast score_updated)
    MatchService.submit_result(
        match=match_live,
        submitted_by_id=3,  # participant1_id
        participant1_score=2,
        participant2_score=1
    )
    
    # Receive score_updated event
    response = await communicator.receive_json_from(timeout=2)
    
    # Verify event
    assert response['type'] == 'score_updated'
    data = response['data']
    assert data['match_id'] == match_live.id
    assert data['participant1_score'] == 2
    assert data['participant2_score'] == 1
    assert data['winner_id'] == 3
    assert data['submitted_by'] == 3
    assert 'updated_at' in data
    
    await communicator.disconnect()


# =============================================================================
# Match Completion Tests (confirm_result → match_completed + bracket_updated)
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_result_confirmation_broadcasts_match_completed(tournament, match_with_result, valid_jwt_token):
    """
    Test confirm_result() broadcasts match_completed event.
    
    Flow:
    1. Connect WebSocket client
    2. Call MatchService.confirm_result()
    3. Verify client receives match_completed event
    4. Verify winner/loser data in payload
    """
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Confirm result (should broadcast match_completed)
    MatchService.confirm_result(match_with_result, confirmed_by_id=6)
    
    # Receive match_completed event
    response = await communicator.receive_json_from(timeout=2)
    
    # Verify event
    assert response['type'] == 'match_completed'
    data = response['data']
    assert data['match_id'] == match_with_result.id
    assert data['winner_id'] == 5
    assert data['winner_name'] == "Player 5"
    assert data['loser_id'] == 6
    assert data['loser_name'] == "Player 6"
    assert data['participant1_score'] == 2
    assert data['participant2_score'] == 1
    assert data['confirmed_by'] == 6
    assert 'completed_at' in data
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_match_completion_triggers_bracket_update_broadcast(tournament, valid_jwt_token, db):
    """
    Test confirm_result() → BracketService.update_bracket_after_match() → bracket_updated broadcast.
    
    Flow:
    1. Create bracket with match linked to bracket node
    2. Connect WebSocket client
    3. Confirm match result
    4. Verify client receives match_completed event
    5. Verify client receives bracket_updated event (from BracketService)
    
    This tests the integration between MatchService and BracketService broadcasting.
    """
    # Create bracket with nodes
    bracket = Bracket.objects.create(
        tournament=tournament,
        bracket_type=Bracket.SINGLE_ELIMINATION,
        seeding_method=Bracket.SLOT_ORDER,
        status=Bracket.ACTIVE
    )
    
    # Create bracket node
    node = BracketNode.objects.create(
        bracket=bracket,
        round_number=1,
        match_number_in_round=1,
        participant1_id=10,
        participant1_name="Team A",
        participant2_id=11,
        participant2_name="Team B",
        parent_slot=None
    )
    
    # Create match linked to bracket node
    match = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=10,
        participant1_name="Team A",
        participant2_id=11,
        participant2_name="Team B",
        status=Match.PENDING_RESULT,
        participant1_score=2,
        participant2_score=1,
        winner_id=10,
        loser_id=11,
        bracket_node=node
    )
    
    node.match = match
    node.save()
    
    # Connect WebSocket client
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Confirm result (should broadcast match_completed AND bracket_updated)
    MatchService.confirm_result(match, confirmed_by_id=11)
    
    # Receive first event (match_completed)
    response1 = await communicator.receive_json_from(timeout=2)
    assert response1['type'] == 'match_completed'
    assert response1['data']['match_id'] == match.id
    
    # Receive second event (bracket_updated from BracketService)
    response2 = await communicator.receive_json_from(timeout=2)
    assert response2['type'] == 'bracket_updated'
    data = response2['data']
    assert data['bracket_id'] == bracket.id
    assert data['tournament_id'] == tournament.id
    assert node.id in data['updated_nodes']
    assert 'updated_at' in data
    
    await communicator.disconnect()


# =============================================================================
# Transaction Safety Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_broadcast_failure_does_not_break_transaction(tournament, match_ready, monkeypatch):
    """
    Test broadcast failures don't cause transaction rollback.
    
    Verifies:
    - Match state updates even if broadcast fails
    - Exception caught and logged
    - Transaction remains atomic
    """
    # Mock broadcast function to raise exception
    def failing_broadcast(*args, **kwargs):
        raise Exception("Simulated broadcast failure")
    
    from apps.tournaments.realtime import utils
    monkeypatch.setattr(utils, 'broadcast_match_started', failing_broadcast)
    
    # Transition match (broadcast will fail but transaction should succeed)
    MatchService.transition_to_live(match_ready)
    
    # Verify match state updated despite broadcast failure
    match_ready.refresh_from_db()
    assert match_ready.status == Match.LIVE
    assert match_ready.started_at is not None
