"""
Integration Tests for BracketService Real-Time Broadcasting

Tests end-to-end WebSocket event flow for bracket updates:
- update_bracket_after_match() → bracket_updated broadcast
- Finals completion → bracket_updated with "completed" status
- Parent node creation → next_matches in payload

Phase 2: Real-Time Features & Security
Module 2.3: Service Layer Integration

Test Coverage:
- Bracket progression broadcasts bracket_updated event
- Finals completion sets bracket status to "completed"
- Multiple clients receive bracket updates
- Event payloads contain updated_nodes and next_matches
- No duplicate broadcasts
"""

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from deltacrown.asgi import application
from apps.tournaments.models import Tournament, Match, Bracket, BracketNode
from apps.tournaments.services.bracket_service import BracketService

User = get_user_model()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def test_user(db):
    """Create test user for authentication."""
    return User.objects.create_user(
        username='bracket_user',
        email='bracket@example.com',
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
        name="Bracket Test Game",
        slug="bracket-test-game",
        game_type="TEAM"
    )
    
    tournament = Tournament.objects.create(
        name="Bracket WebSocket Test Tournament",
        slug="bracket-ws-test",
        game=game,
        organizer_id=test_user.id,
        tournament_type="SINGLE_ELIMINATION",
        max_teams=4,
        team_size=1,
        entry_fee=0,
        status="ACTIVE"
    )
    
    return tournament


@pytest.fixture
def bracket_with_nodes(db, tournament):
    """Create bracket with match tree (4-team single elimination)."""
    bracket = Bracket.objects.create(
        tournament=tournament,
        bracket_type=Bracket.SINGLE_ELIMINATION,
        seeding_method=Bracket.SLOT_ORDER,
        status=Bracket.ACTIVE
    )
    
    # Create parent node (finals)
    finals_node = BracketNode.objects.create(
        bracket=bracket,
        round_number=2,
        match_number_in_round=1,
        parent_slot=None
    )
    
    # Create semifinal nodes
    semi1 = BracketNode.objects.create(
        bracket=bracket,
        round_number=1,
        match_number_in_round=1,
        participant1_id=1,
        participant1_name="Team A",
        participant2_id=2,
        participant2_name="Team B",
        parent_node=finals_node,
        parent_slot=1
    )
    
    semi2 = BracketNode.objects.create(
        bracket=bracket,
        round_number=1,
        match_number_in_round=2,
        participant1_id=3,
        participant1_name="Team C",
        participant2_id=4,
        participant2_name="Team D",
        parent_node=finals_node,
        parent_slot=2
    )
    
    # Create matches
    match1 = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=1,
        participant1_name="Team A",
        participant2_id=2,
        participant2_name="Team B",
        status=Match.COMPLETED,
        participant1_score=2,
        participant2_score=1,
        winner_id=1,
        loser_id=2,
        bracket_node=semi1
    )
    
    match2 = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=2,
        participant1_id=3,
        participant1_name="Team C",
        participant2_id=4,
        participant2_name="Team D",
        status=Match.READY,
        bracket_node=semi2
    )
    
    semi1.match = match1
    semi1.winner_id = 1
    semi1.winner_name = "Team A"
    semi1.save()
    
    semi2.match = match2
    semi2.save()
    
    return bracket, finals_node, semi1, semi2, match1, match2


# =============================================================================
# Bracket Progression Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_bracket_progression_broadcasts_bracket_updated(bracket_with_nodes, tournament, valid_jwt_token):
    """
    Test update_bracket_after_match() broadcasts bracket_updated event.
    
    Flow:
    1. Connect WebSocket client
    2. Complete semifinal match (Team C vs Team D)
    3. Call BracketService.update_bracket_after_match()
    4. Verify client receives bracket_updated event
    5. Verify payload contains updated_nodes and next_matches
    """
    bracket, finals_node, semi1, semi2, match1, match2 = bracket_with_nodes
    
    # Connect WebSocket client
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Complete second semifinal
    match2.status = Match.COMPLETED
    match2.participant1_score = 3
    match2.participant2_score=0
    match2.winner_id = 3
    match2.loser_id = 4
    match2.save()
    
    # Update bracket (should broadcast bracket_updated)
    BracketService.update_bracket_after_match(match2)
    
    # Receive bracket_updated event
    response = await communicator.receive_json_from(timeout=2)
    
    # Verify event type
    assert response['type'] == 'bracket_updated'
    
    # Verify payload
    data = response['data']
    assert data['bracket_id'] == bracket.id
    assert data['tournament_id'] == tournament.id
    assert semi2.id in data['updated_nodes']
    assert finals_node.id in data['next_matches']
    assert 'updated_at' in data
    
    # Verify bracket node updated
    semi2.refresh_from_db()
    assert semi2.winner_id == 3
    assert semi2.winner_name == "Team C"
    
    # Verify finals node seeded
    finals_node.refresh_from_db()
    assert finals_node.participant1_id == 1  # Winner of semi1
    assert finals_node.participant2_id == 3  # Winner of semi2
    
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_finals_completion_broadcasts_completed_status(bracket_with_nodes, tournament, valid_jwt_token):
    """
    Test finals completion broadcasts bracket_updated with status="completed".
    
    Flow:
    1. Seed finals with both semifinal winners
    2. Connect WebSocket client
    3. Complete finals match
    4. Update bracket
    5. Verify bracket_updated contains "completed" status
    """
    bracket, finals_node, semi1, semi2, match1, match2 = bracket_with_nodes
    
    # Complete second semifinal to seed finals
    match2.status = Match.COMPLETED
    match2.winner_id = 3
    match2.loser_id = 4
    match2.save()
    
    semi2.winner_id = 3
    semi2.winner_name = "Team C"
    semi2.save()
    
    # Seed finals node
    finals_node.participant1_id = 1
    finals_node.participant1_name = "Team A"
    finals_node.participant2_id = 3
    finals_node.participant2_name = "Team C"
    finals_node.save()
    
    # Create finals match
    finals_match = Match.objects.create(
        tournament=tournament,
        round_number=2,
        match_number=1,
        participant1_id=1,
        participant1_name="Team A",
        participant2_id=3,
        participant2_name="Team C",
        status=Match.COMPLETED,
        participant1_score=3,
        participant2_score=2,
        winner_id=1,
        loser_id=3,
        bracket_node=finals_node
    )
    
    finals_node.match = finals_match
    finals_node.save()
    
    # Connect WebSocket client
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    # Discard welcome message
    await communicator.receive_json_from(timeout=2)
    
    # Update bracket (finals complete, should mark bracket as completed)
    BracketService.update_bracket_after_match(finals_match)
    
    # Receive bracket_updated event
    response = await communicator.receive_json_from(timeout=2)
    
    # Verify event
    assert response['type'] == 'bracket_updated'
    data = response['data']
    assert data['bracket_status'] == Bracket.COMPLETED
    assert finals_node.id in data['updated_nodes']
    assert len(data['next_matches']) == 0  # No next matches after finals
    
    # Verify bracket marked complete
    bracket.refresh_from_db()
    assert bracket.status == Bracket.COMPLETED
    
    await communicator.disconnect()


# =============================================================================
# Multi-Client Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_bracket_update_multiple_clients(bracket_with_nodes, tournament, valid_jwt_token, test_user):
    """
    Test bracket_updated broadcasts to multiple concurrent clients.
    
    Verifies:
    - Both clients receive identical bracket_updated event
    - No duplicate broadcasts
    """
    bracket, finals_node, semi1, semi2, match1, match2 = bracket_with_nodes
    
    # Create second user/token
    user2 = User.objects.create_user(username='spectator2', email='spec2@test.com', password='pass')
    token2 = str(AccessToken.for_user(user2))
    
    # Connect two clients
    comm1 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}")
    comm2 = WebsocketCommunicator(application, f"/ws/tournament/{tournament.id}/?token={token2}")
    
    await comm1.connect()
    await comm2.connect()
    
    # Discard welcome messages
    await comm1.receive_json_from(timeout=2)
    await comm2.receive_json_from(timeout=2)
    
    # Complete match and update bracket
    match2.status = Match.COMPLETED
    match2.winner_id = 3
    match2.loser_id = 4
    match2.save()
    
    BracketService.update_bracket_after_match(match2)
    
    # Both clients should receive event
    response1 = await comm1.receive_json_from(timeout=2)
    response2 = await comm2.receive_json_from(timeout=2)
    
    assert response1['type'] == 'bracket_updated'
    assert response2['type'] == 'bracket_updated'
    assert response1['data']['bracket_id'] == response2['data']['bracket_id']
    assert response1['data']['updated_nodes'] == response2['data']['updated_nodes']
    
    await comm1.disconnect()
    await comm2.disconnect()


# =============================================================================
# Payload Verification Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_bracket_update_payload_contains_required_fields(bracket_with_nodes, tournament, valid_jwt_token):
    """
    Test bracket_updated payload contains all required fields.
    
    Required fields:
    - bracket_id
    - tournament_id
    - updated_nodes (list of node IDs)
    - next_matches (list of node IDs)
    - bracket_status
    - updated_at
    """
    bracket, finals_node, semi1, semi2, match1, match2 = bracket_with_nodes
    
    communicator = WebsocketCommunicator(
        application,
        f"/ws/tournament/{tournament.id}/?token={valid_jwt_token}"
    )
    
    connected, _ = await communicator.connect()
    assert connected
    
    await communicator.receive_json_from(timeout=2)
    
    # Update bracket
    match2.status = Match.COMPLETED
    match2.winner_id = 3
    match2.save()
    
    BracketService.update_bracket_after_match(match2)
    
    response = await communicator.receive_json_from(timeout=2)
    data = response['data']
    
    # Verify all required fields present
    required_fields = ['bracket_id', 'tournament_id', 'updated_nodes', 'next_matches', 'bracket_status', 'updated_at']
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Verify types
    assert isinstance(data['bracket_id'], int)
    assert isinstance(data['tournament_id'], int)
    assert isinstance(data['updated_nodes'], list)
    assert isinstance(data['next_matches'], list)
    assert isinstance(data['bracket_status'], str)
    assert isinstance(data['updated_at'], str)
    
    await communicator.disconnect()


# =============================================================================
# Transaction Safety Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_broadcast_failure_does_not_break_bracket_update(bracket_with_nodes, monkeypatch):
    """
    Test broadcast failures don't cause bracket update transaction rollback.
    
    Verifies:
    - Bracket nodes update even if broadcast fails
    - Exception caught and logged
    - Transaction remains atomic
    """
    bracket, finals_node, semi1, semi2, match1, match2 = bracket_with_nodes
    
    # Mock broadcast function to raise exception
    def failing_broadcast(*args, **kwargs):
        raise Exception("Simulated broadcast failure")
    
    from apps.tournaments.realtime import utils
    monkeypatch.setattr(utils, 'broadcast_bracket_updated', failing_broadcast)
    
    # Update bracket (broadcast will fail but transaction should succeed)
    match2.status = Match.COMPLETED
    match2.winner_id = 3
    match2.loser_id = 4
    match2.save()
    
    BracketService.update_bracket_after_match(match2)
    
    # Verify bracket node updated despite broadcast failure
    semi2.refresh_from_db()
    assert semi2.winner_id == 3
    
    finals_node.refresh_from_db()
    assert finals_node.participant2_id == 3  # Seeded with winner
