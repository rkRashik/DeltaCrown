"""
Tests for UserActivityService

Validates:
- Event creation correctness
- Idempotency (duplicate prevention)
- Source tracking (tournament/match/economy)
- Event data integrity
"""

import pytest
import uuid
from django.utils import timezone
from apps.user_profile.services.activity_service import UserActivityService
from apps.user_profile.models.activity import UserActivity, EventType
from apps.accounts.models import User
from apps.user_profile.models import UserProfile


def unique_id():
    """Generate unique ID for test data to avoid constraint violations."""
    return abs(hash(uuid.uuid4())) % 1000000


@pytest.fixture
def test_user(db):
    """Create test user with profile."""
    user = User.objects.create_user(
        username=f'testuser_{unique_id()}',
        email=f'test_{unique_id()}@example.com',
        password='testpass123'
    )
    # Profile created by signal
    return user


@pytest.mark.django_db
class TestTournamentEvents:
    """Test tournament event recording."""
    
    def test_record_tournament_join(self, test_user):
        """Should create TOURNAMENT_JOINED event."""
        reg_id = unique_id()
        tourn_id = unique_id()
        event = UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=tourn_id,
            registration_id=reg_id
        )
        
        assert event is not None
        assert event.event_type == EventType.TOURNAMENT_JOINED
        assert event.user_id == test_user.id
        assert event.source_model == 'registration'
        assert event.source_id == reg_id
        assert event.metadata['tournament_id'] == tourn_id
        assert event.metadata['registration_id'] == reg_id
    
    def test_tournament_join_idempotency(self, test_user):
        """Should not create duplicate events."""
        reg_id = unique_id()
        # First call creates event
        event1 = UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=unique_id(),
            registration_id=reg_id
        )
        assert event1 is not None
        
        # Second call returns None (idempotent)
        event2 = UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=event1.metadata['tournament_id'],
            registration_id=reg_id
        )
        assert event2 is None
        
        # Verify only one event exists
        count = UserActivity.objects.filter(
            event_type=EventType.TOURNAMENT_JOINED,
            user_id=test_user.id,
            source_id=reg_id
        ).count()
        assert count == 1
    
    def test_record_tournament_placed(self, test_user):
        """Should create TOURNAMENT_WON event for 1st place."""
        event = UserActivityService.record_tournament_placed(
            user_id=test_user.id,
            tournament_id=unique_id(),
            placement=1,
            prize_amount=500.00
        )
        
        assert event is not None
        assert event.event_type == EventType.TOURNAMENT_WON
        assert event.metadata['placement'] == 1
        assert event.metadata['prize_amount'] == 500.00
    
    def test_record_tournament_placed_runner_up(self, test_user):
        """Should create TOURNAMENT_PLACED event for non-winners."""
        event = UserActivityService.record_tournament_placed(
            user_id=test_user.id,
            tournament_id=unique_id(),
            placement=2,
            prize_amount=200.00
        )
        
        assert event is not None
        assert event.event_type == EventType.TOURNAMENT_PLACED
        assert event.metadata['placement'] == 2


@pytest.mark.django_db
class TestMatchEvents:
    """Test match event recording."""
    
    def test_record_match_result(self, test_user, db):
        """Should create MATCH_WON and MATCH_LOST events."""
        loser = User.objects.create_user(
            username=f'loser_{unique_id()}',
            email=f'loser_{unique_id()}@example.com',
            password='pass123'
        )
        UserProfile.objects.get_or_create(user=loser)
        
        match_id = unique_id()
        winner_event, loser_event = UserActivityService.record_match_result(
            match_id=match_id,
            winner_id=test_user.id,
            loser_id=loser.id,
            winner_score=3,
            loser_score=1
        )
        
        # Winner event
        assert winner_event is not None
        assert winner_event.event_type == EventType.MATCH_WON
        assert winner_event.user_id == test_user.id
        assert winner_event.metadata['opponent_id'] == loser.id
        assert winner_event.metadata['score'] == 3
        
        # Loser event
        assert loser_event is not None
        assert loser_event.event_type == EventType.MATCH_LOST
        assert loser_event.user_id == loser.id
        assert loser_event.metadata['opponent_id'] == test_user.id
        assert loser_event.metadata['score'] == 1
    
    def test_match_result_idempotency(self, test_user, db):
        """Should not create duplicate match events."""
        loser = User.objects.create_user(
            username=f'loser2_{unique_id()}',
            email=f'loser2_{unique_id()}@example.com',
            password='pass123'
        )
        UserProfile.objects.get_or_create(user=loser)
        
        match_id = unique_id()
        # First call creates events
        events1 = UserActivityService.record_match_result(
            match_id=match_id,
            winner_id=test_user.id,
            loser_id=loser.id
        )
        assert events1[0] is not None
        
        # Second call returns None (idempotent)
        events2 = UserActivityService.record_match_result(
            match_id=match_id,
            winner_id=test_user.id,
            loser_id=loser.id
        )
        assert events2[0] is None


@pytest.mark.django_db
class TestEconomyEvents:
    """Test economy event recording."""
    
    def test_record_coins_earned(self, test_user):
        """Should create COINS_EARNED event for positive amount."""
        event = UserActivityService.record_economy_transaction(
            transaction_id=unique_id(),
            user_id=test_user.id,
            amount=100.00,
            reason='TOURNAMENT_WIN'
        )
        
        assert event is not None
        assert event.event_type == EventType.COINS_EARNED
        assert event.metadata['amount'] == 100.00
        assert event.metadata['reason'] == 'TOURNAMENT_WIN'
    
    def test_record_coins_spent(self, test_user):
        """Should create COINS_SPENT event for negative amount."""
        event = UserActivityService.record_economy_transaction(
            transaction_id=unique_id(),
            user_id=test_user.id,
            amount=-50.00,
            reason='ENTRY_FEE'
        )
        
        assert event is not None
        assert event.event_type == EventType.COINS_SPENT
        assert event.metadata['amount'] == 50.00  # Stored as absolute
        assert event.metadata['reason'] == 'ENTRY_FEE'
    
    def test_economy_transaction_idempotency(self, test_user):
        """Should not create duplicate economy events."""
        txn_id = unique_id()
        # First call
        event1 = UserActivityService.record_economy_transaction(
            transaction_id=txn_id,
            user_id=test_user.id,
            amount=100.00,
            reason='TEST'
        )
        assert event1 is not None
        
        # Second call (idempotent)
        event2 = UserActivityService.record_economy_transaction(
            transaction_id=txn_id,
            user_id=test_user.id,
            amount=100.00,
            reason='TEST'
        )
        assert event2 is None


@pytest.mark.django_db
class TestEventQueries:
    """Test event querying."""
    
    def test_get_user_events(self, test_user):
        """Should retrieve all events for user."""
        # Create multiple events
        UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=100,
            registration_id=200
        )
        UserActivityService.record_economy_transaction(
            transaction_id=400,
            user_id=test_user.id,
            amount=50.00,
            reason='TEST'
        )
        
        events = UserActivity.objects.filter(user_id=test_user.id)
        assert events.count() == 2
    
    def test_event_ordering(self, test_user):
        """Should order events by timestamp desc."""
        # Create events with different timestamps
        ts1 = timezone.now()
        ts2 = timezone.now() + timezone.timedelta(hours=1)
        
        UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=100,
            registration_id=200,
            timestamp=ts1
        )
        UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=101,
            registration_id=201,
            timestamp=ts2
        )
        
        events = UserActivity.objects.filter(user_id=test_user.id)
        # Default ordering is -timestamp (newest first)
        assert events.first().metadata['tournament_id'] == 101
        assert events.last().metadata['tournament_id'] == 100
