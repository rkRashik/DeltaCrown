"""
Tests for MatchService organizer actions (reschedule, forfeit, override_score, cancel).

Phase 0 Refactor: Tests for ORM mutations moved from organizer views to service layer.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game, Match, Bracket
from apps.tournaments.services.match_service import MatchService

User = get_user_model()

# Print DB config at module load
print(f"\n{'='*60}")
print(f"TEST DATABASE CONFIGURATION")
print(f"{'='*60}")
import os
from django.conf import settings
if os.environ.get('USE_LOCAL_TEST_DB', 'false').lower() == 'true':
    db_config = settings.DATABASES['default']
    print(f"✓ Using LOCAL test database")
    print(f"  Database: {db_config['NAME']}")
    print(f"  Host: {db_config['HOST']}")
    print(f"  User: {db_config['USER']}")
else:
    print(f"⚠ Using DATABASE_URL (Neon) - may fail if user can't create test DB")
    print(f"  To use local: set USE_LOCAL_TEST_DB=true")
print(f"{'='*60}\n")


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name='Test Game',
        slug='test-game',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='map_score'
    )


@pytest.fixture
def organizer_user(db):
    """Create an organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def tournament(db, game, organizer_user):
    """Create a test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        game=game,
        organizer=organizer_user,
        max_teams=16,
        registration_start=timezone.now() - timedelta(days=2),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=14),
        tournament_end=timezone.now() + timedelta(days=15),
        status='upcoming'
    )


@pytest.fixture
def bracket(db, tournament):
    """Create a test bracket."""
    return Bracket.objects.create(
        tournament=tournament,
        name='Main Bracket',
        bracket_type='single_elimination',
        size=8,
        current_round=1
    )


@pytest.fixture
def scheduled_match(db, tournament, bracket):
    """Create a scheduled match."""
    scheduled_time = timezone.now() + timedelta(days=7)
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        state='scheduled',
        scheduled_time=scheduled_time,
        participant1_id=101,
        participant1_name='Team A',
        participant2_id=102,
        participant2_name='Team B',
        score1=0,
        score2=0
    )


@pytest.fixture
def live_match(db, tournament, bracket):
    """Create a live match."""
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=2,
        state='live',
        participant1_id=103,
        participant1_name='Team C',
        participant2_id=104,
        participant2_name='Team D',
        score1=5,
        score2=3
    )


@pytest.mark.django_db
class TestMatchServiceReschedule:
    """Test MatchService.organizer_reschedule_match()"""
    
    def test_reschedule_match_updates_time_and_stores_metadata(
        self, 
        scheduled_match, 
        organizer_user
    ):
        """Test rescheduling a match updates scheduled_time and stores audit info"""
        # Before
        old_time = scheduled_match.scheduled_time
        assert 'rescheduled' not in scheduled_match.lobby_info
        
        # New time 2 hours later
        new_time = old_time + timedelta(hours=2)
        reason = "Participant requested delay"
        
        # Act
        result = MatchService.organizer_reschedule_match(
            scheduled_match,
            new_time,
            reason,
            organizer_user.username
        )
        
        # After
        scheduled_match.refresh_from_db()
        assert result.scheduled_time == new_time
        assert scheduled_match.scheduled_time == new_time
        assert 'rescheduled' in scheduled_match.lobby_info
        assert scheduled_match.lobby_info['rescheduled']['old_time'] == old_time.isoformat()
        assert scheduled_match.lobby_info['rescheduled']['new_time'] == new_time.isoformat()
        assert scheduled_match.lobby_info['rescheduled']['reason'] == reason
        assert scheduled_match.lobby_info['rescheduled']['rescheduled_by'] == organizer_user.username


@pytest.mark.django_db
class TestMatchServiceForfeit:
    """Test MatchService.organizer_forfeit_match()"""
    
    def test_forfeit_participant1_sets_participant2_as_winner(
        self,
        scheduled_match,
        organizer_user
    ):
        """Test forfeiting participant 1 makes participant 2 the winner"""
        # Before
        assert scheduled_match.winner_id is None
        assert scheduled_match.state == 'scheduled'
        
        # Act: Participant 1 forfeits
        result = MatchService.organizer_forfeit_match(
            scheduled_match,
            1,  # participant 1 forfeits
            "No-show",
            organizer_user.username
        )
        
        # After
        scheduled_match.refresh_from_db()
        assert result.winner_id == scheduled_match.participant2_id
        assert scheduled_match.winner_id == scheduled_match.participant2_id
        assert scheduled_match.loser_id == scheduled_match.participant1_id
        assert scheduled_match.score1 == 0
        assert scheduled_match.score2 == 1
        assert scheduled_match.state == 'completed'
        assert 'forfeit' in scheduled_match.lobby_info
        assert scheduled_match.lobby_info['forfeit']['forfeiting_participant'] == 1
    
    def test_forfeit_participant2_sets_participant1_as_winner(
        self,
        scheduled_match,
        organizer_user
    ):
        """Test forfeiting participant 2 makes participant 1 the winner"""
        # Act: Participant 2 forfeits
        result = MatchService.organizer_forfeit_match(
            scheduled_match,
            2,  # participant 2 forfeits
            "Team disbanded",
            organizer_user.username
        )
        
        # After
        scheduled_match.refresh_from_db()
        assert result.winner_id == scheduled_match.participant1_id
        assert scheduled_match.winner_id == scheduled_match.participant1_id
        assert scheduled_match.loser_id == scheduled_match.participant2_id
        assert scheduled_match.score1 == 1
        assert scheduled_match.score2 == 0


@pytest.mark.django_db
class TestMatchServiceOverrideScore:
    """Test MatchService.organizer_override_score()"""
    
    def test_override_score_updates_scores_and_determines_winner(
        self,
        live_match,
        organizer_user
    ):
        """Test overriding score updates scores and sets correct winner"""
        # Before
        old_score1 = live_match.score1
        old_score2 = live_match.score2
        assert old_score1 == 5
        assert old_score2 == 3
        
        # Act: Override score to 10-15 (participant 2 wins)
        result = MatchService.organizer_override_score(
            live_match,
            10,
            15,
            "Score reporting error correction",
            organizer_user.username
        )
        
        # After
        live_match.refresh_from_db()
        assert result.score1 == 10
        assert result.score2 == 15
        assert live_match.score1 == 10
        assert live_match.score2 == 15
        assert live_match.winner_id == live_match.participant2_id
        assert live_match.loser_id == live_match.participant1_id
        assert live_match.state == 'completed'
        assert 'score_override' in live_match.lobby_info
        assert live_match.lobby_info['score_override']['old_score1'] == old_score1
        assert live_match.lobby_info['score_override']['new_score1'] == 10
    
    def test_override_score_participant1_wins_when_score1_higher(
        self,
        live_match,
        organizer_user
    ):
        """Test override sets participant1 as winner when score1 > score2"""
        # Act: Score 20-10 (participant 1 wins)
        result = MatchService.organizer_override_score(
            live_match,
            20,
            10,
            "Admin correction",
            organizer_user.username
        )
        
        # After
        live_match.refresh_from_db()
        assert live_match.winner_id == live_match.participant1_id
        assert live_match.loser_id == live_match.participant2_id


@pytest.mark.django_db
class TestMatchServiceCancel:
    """Test MatchService.organizer_cancel_match()"""
    
    def test_cancel_match_sets_state_and_stores_reason(
        self,
        scheduled_match,
        organizer_user
    ):
        """Test cancelling match sets state to cancelled and stores metadata"""
        # Before
        assert scheduled_match.state == 'scheduled'
        assert 'cancelled' not in scheduled_match.lobby_info
        
        # Act
        result = MatchService.organizer_cancel_match(
            scheduled_match,
            "Tournament cancelled due to low attendance",
            organizer_user.username
        )
        
        # After
        scheduled_match.refresh_from_db()
        assert result.state == 'cancelled'
        assert scheduled_match.state == 'cancelled'
        assert 'cancelled' in scheduled_match.lobby_info
        assert scheduled_match.lobby_info['cancelled']['reason'] == "Tournament cancelled due to low attendance"
        assert scheduled_match.lobby_info['cancelled']['cancelled_by'] == organizer_user.username
        assert 'cancelled_at' in scheduled_match.lobby_info['cancelled']
