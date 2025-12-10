"""
Unit Tests for MatchHistoryAdapter

Phase 8, Epic 8.4: Match History Engine
Tests ORM operations via adapter interface with real Django models in test database.
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone

from apps.tournament_ops.adapters.match_history_adapter import DjangoMatchHistoryAdapter
from apps.tournament_ops.dtos import MatchHistoryFilterDTO


@pytest.mark.django_db
class TestDjangoMatchHistoryAdapter:
    """Test Django ORM adapter for match history operations."""
    
    @pytest.fixture
    def adapter(self):
        """Provide adapter instance."""
        return DjangoMatchHistoryAdapter()
    
    @pytest.fixture
    def sample_user(self, django_user_model):
        """Create test user."""
        return django_user_model.objects.create_user(
            username="testplayer",
            email="test@example.com"
        )
    
    @pytest.fixture
    def sample_team(self):
        """Create test team."""
        from apps.teams.models import Team
        return Team.objects.create(
            name="Test Team",
            tag="TST",
            game="valorant"
        )
    
    @pytest.fixture
    def sample_game(self):
        """Create test game."""
        from apps.tournaments.models import Game
        return Game.objects.create(
            name="Valorant",
            slug="valorant",
            icon="games/valorant.png"
        )
    
    @pytest.fixture
    def sample_tournament(self, sample_game, sample_user):
        """Create test tournament."""
        from apps.tournaments.models import Tournament
        return Tournament.objects.create(
            name="Test Tournament",
            game=sample_game,
            description="Test description",
            status="upcoming",
            organizer=sample_user,
            max_participants=16
        )
    
    @pytest.fixture
    def sample_match(self, sample_tournament, sample_user):
        """Create test match."""
        from apps.tournaments.models import Match
        return Match.objects.create(
            tournament=sample_tournament,
            participant1_id=sample_user.id,
            participant2_id=sample_user.id + 1,
            status="completed"
        )
    
    # ========================================================================
    # User Match History Tests
    # ========================================================================
    
    def test_record_user_match_history_creates_entry(
        self, adapter, sample_user, sample_match, sample_tournament
    ):
        """Test recording user match history creates database entry."""
        completed_at = timezone.now()
        
        dto = adapter.record_user_match_history(
            user_id=sample_user.id,
            match_id=sample_match.id,
            tournament_id=sample_tournament.id,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_user_id=sample_user.id + 1,
            opponent_name="Opponent Player",
            score_summary="13-7",
            kills=25,
            deaths=15,
            assists=10,
            had_dispute=False,
            is_forfeit=False,
            completed_at=completed_at,
        )
        
        assert dto.user_id == sample_user.id
        assert dto.match_id == sample_match.id
        assert dto.is_winner is True
        assert dto.kills == 25
        assert dto.deaths == 15
        
        # Verify entry exists in database
        from apps.leaderboards.models import UserMatchHistory
        entry = UserMatchHistory.objects.get(user_id=sample_user.id, match_id=sample_match.id)
        assert entry.game_slug == "valorant"
        assert entry.score_summary == "13-7"
    
    def test_record_user_match_history_is_idempotent(
        self, adapter, sample_user, sample_match, sample_tournament
    ):
        """Test recording same match twice updates existing entry."""
        # First recording
        adapter.record_user_match_history(
            user_id=sample_user.id,
            match_id=sample_match.id,
            tournament_id=sample_tournament.id,
            game_slug="valorant",
            is_winner=False,
            is_draw=False,
            opponent_user_id=sample_user.id + 1,
            opponent_name="Opponent",
            score_summary="7-13",
            kills=15,
            deaths=20,
            assists=5,
            had_dispute=False,
            is_forfeit=False,
            completed_at=timezone.now(),
        )
        
        # Second recording (update)
        dto = adapter.record_user_match_history(
            user_id=sample_user.id,
            match_id=sample_match.id,
            tournament_id=sample_tournament.id,
            game_slug="valorant",
            is_winner=True,  # Changed
            is_draw=False,
            opponent_user_id=sample_user.id + 1,
            opponent_name="Opponent",
            score_summary="13-7",  # Changed
            kills=25,  # Changed
            deaths=15,  # Changed
            assists=10,  # Changed
            had_dispute=True,  # Changed
            is_forfeit=False,
            completed_at=timezone.now(),
        )
        
        assert dto.is_winner is True
        assert dto.kills == 25
        assert dto.had_dispute is True
        
        # Verify only one entry exists
        from apps.leaderboards.models import UserMatchHistory
        count = UserMatchHistory.objects.filter(user_id=sample_user.id, match_id=sample_match.id).count()
        assert count == 1
    
    def test_list_user_history_returns_entries_ordered_by_completed_at(
        self, adapter, sample_user, sample_tournament
    ):
        """Test listing user history returns entries in desc order by completed_at."""
        from apps.tournaments.models import Match
        
        # Create 3 matches at different times
        now = timezone.now()
        matches = []
        for i in range(3):
            match = Match.objects.create(
                tournament=sample_tournament,
                participant1_id=sample_user.id,
                participant2_id=sample_user.id + 1,
                status="completed"
            )
            matches.append(match)
            
            adapter.record_user_match_history(
                user_id=sample_user.id,
                match_id=match.id,
                tournament_id=sample_tournament.id,
                game_slug="valorant",
                is_winner=(i % 2 == 0),
                is_draw=False,
                opponent_user_id=sample_user.id + 1,
                opponent_name="Opponent",
                score_summary="13-7",
                kills=20 + i,
                deaths=15,
                assists=5,
                had_dispute=False,
                is_forfeit=False,
                completed_at=now - timedelta(hours=i),  # Different times
            )
        
        # List history
        filter_dto = MatchHistoryFilterDTO.validate(
            user_id=sample_user.id,
            limit=10,
            offset=0,
        )
        
        results = adapter.list_user_history(filter_dto)
        
        assert len(results) == 3
        # Should be ordered by completed_at DESC (most recent first)
        assert results[0].kills == 20  # i=0 (most recent)
        assert results[1].kills == 21  # i=1
        assert results[2].kills == 22  # i=2 (oldest)
    
    def test_list_user_history_filters_by_game_slug(
        self, adapter, sample_user, sample_tournament
    ):
        """Test listing user history filters by game_slug."""
        from apps.tournaments.models import Match, Tournament
        
        # Create tournament for different game
        csgo_tournament = Tournament.objects.create(
            name="CSGO Tournament",
            game_slug="csgo",
            description="Test",
            status="upcoming"
        )
        
        # Create valorant match
        valorant_match = Match.objects.create(
            tournament=sample_tournament,
            participant1_id=sample_user.id,
            participant2_id=sample_user.id + 1,
            status="completed"
        )
        
        adapter.record_user_match_history(
            user_id=sample_user.id,
            match_id=valorant_match.id,
            tournament_id=sample_tournament.id,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_user_id=None,
            opponent_name="Opponent",
            score_summary="13-7",
            kills=25,
            deaths=15,
            assists=10,
            had_dispute=False,
            is_forfeit=False,
            completed_at=timezone.now(),
        )
        
        # Create csgo match
        csgo_match = Match.objects.create(
            tournament=csgo_tournament,
            participant1_id=sample_user.id,
            participant2_id=sample_user.id + 1,
            status="completed"
        )
        
        adapter.record_user_match_history(
            user_id=sample_user.id,
            match_id=csgo_match.id,
            tournament_id=csgo_tournament.id,
            game_slug="csgo",
            is_winner=False,
            is_draw=False,
            opponent_user_id=None,
            opponent_name="Opponent",
            score_summary="10-16",
            kills=20,
            deaths=18,
            assists=5,
            had_dispute=False,
            is_forfeit=False,
            completed_at=timezone.now(),
        )
        
        # Filter by valorant only
        filter_dto = MatchHistoryFilterDTO.validate(
            user_id=sample_user.id,
            game_slug="valorant",
            limit=10,
            offset=0,
        )
        
        results = adapter.list_user_history(filter_dto)
        
        assert len(results) == 1
        assert results[0].game_slug == "valorant"
        assert results[0].kills == 25
    
    def test_list_user_history_paginates_results(
        self, adapter, sample_user, sample_tournament
    ):
        """Test listing user history respects limit and offset."""
        from apps.tournaments.models import Match
        
        # Create 5 matches
        for i in range(5):
            match = Match.objects.create(
                tournament=sample_tournament,
                participant1_id=sample_user.id,
                participant2_id=sample_user.id + 1,
                status="completed"
            )
            
            adapter.record_user_match_history(
                user_id=sample_user.id,
                match_id=match.id,
                tournament_id=sample_tournament.id,
                game_slug="valorant",
                is_winner=True,
                is_draw=False,
                opponent_user_id=None,
                opponent_name="Opponent",
                score_summary="13-7",
                kills=20 + i,
                deaths=15,
                assists=5,
                had_dispute=False,
                is_forfeit=False,
                completed_at=timezone.now() - timedelta(hours=i),
            )
        
        # Get first page (limit=2, offset=0)
        filter_dto = MatchHistoryFilterDTO.validate(
            user_id=sample_user.id,
            limit=2,
            offset=0,
        )
        
        results = adapter.list_user_history(filter_dto)
        assert len(results) == 2
        
        # Get second page (limit=2, offset=2)
        filter_dto = MatchHistoryFilterDTO.validate(
            user_id=sample_user.id,
            limit=2,
            offset=2,
        )
        
        results = adapter.list_user_history(filter_dto)
        assert len(results) == 2
    
    def test_get_user_history_count_returns_total(
        self, adapter, sample_user, sample_tournament
    ):
        """Test counting user history entries."""
        from apps.tournaments.models import Match
        
        # Create 3 matches
        for i in range(3):
            match = Match.objects.create(
                tournament=sample_tournament,
                participant1_id=sample_user.id,
                participant2_id=sample_user.id + 1,
                status="completed"
            )
            
            adapter.record_user_match_history(
                user_id=sample_user.id,
                match_id=match.id,
                tournament_id=sample_tournament.id,
                game_slug="valorant",
                is_winner=True,
                is_draw=False,
                opponent_user_id=None,
                opponent_name="Opponent",
                score_summary="13-7",
                kills=20,
                deaths=15,
                assists=5,
                had_dispute=False,
                is_forfeit=False,
                completed_at=timezone.now(),
            )
        
        filter_dto = MatchHistoryFilterDTO.validate(
            user_id=sample_user.id,
            limit=10,
            offset=0,
        )
        
        count = adapter.get_user_history_count(filter_dto)
        assert count == 3
    
    # ========================================================================
    # Team Match History Tests
    # ========================================================================
    
    def test_record_team_match_history_creates_entry_with_elo(
        self, adapter, sample_team, sample_match, sample_tournament
    ):
        """Test recording team match history with ELO tracking."""
        completed_at = timezone.now()
        
        dto = adapter.record_team_match_history(
            team_id=sample_team.id,
            match_id=sample_match.id,
            tournament_id=sample_tournament.id,
            game_slug="csgo",
            is_winner=True,
            is_draw=False,
            opponent_team_id=sample_team.id + 1,
            opponent_team_name="Opponent Team",
            score_summary="16-10",
            elo_before=1500,
            elo_after=1520,
            elo_change=20,
            had_dispute=False,
            is_forfeit=False,
            completed_at=completed_at,
        )
        
        assert dto.team_id == sample_team.id
        assert dto.elo_before == 1500
        assert dto.elo_after == 1520
        assert dto.elo_change == 20
        
        # Verify entry exists in database
        from apps.leaderboards.models import TeamMatchHistory
        entry = TeamMatchHistory.objects.get(team_id=sample_team.id, match_id=sample_match.id)
        assert entry.game_slug == "csgo"
        assert entry.elo_change == 20
    
    def test_list_team_history_filters_by_tournament(
        self, adapter, sample_team
    ):
        """Test listing team history filters by tournament_id."""
        from apps.tournaments.models import Match, Tournament
        
        # Create two tournaments
        tournament1 = Tournament.objects.create(
            name="Tournament 1",
            game_slug="csgo",
            description="Test",
            status="upcoming"
        )
        
        tournament2 = Tournament.objects.create(
            name="Tournament 2",
            game_slug="csgo",
            description="Test",
            status="upcoming"
        )
        
        # Create matches in both tournaments
        match1 = Match.objects.create(
            tournament=tournament1,
            participant1_id=sample_team.id,
            participant2_id=sample_team.id + 1,
            status="completed"
        )
        
        match2 = Match.objects.create(
            tournament=tournament2,
            participant1_id=sample_team.id,
            participant2_id=sample_team.id + 1,
            status="completed"
        )
        
        # Record history for both
        adapter.record_team_match_history(
            team_id=sample_team.id,
            match_id=match1.id,
            tournament_id=tournament1.id,
            game_slug="csgo",
            is_winner=True,
            is_draw=False,
            opponent_team_id=None,
            opponent_team_name="Team A",
            score_summary="16-10",
            elo_before=1500,
            elo_after=1520,
            elo_change=20,
            had_dispute=False,
            is_forfeit=False,
            completed_at=timezone.now(),
        )
        
        adapter.record_team_match_history(
            team_id=sample_team.id,
            match_id=match2.id,
            tournament_id=tournament2.id,
            game_slug="csgo",
            is_winner=False,
            is_draw=False,
            opponent_team_id=None,
            opponent_team_name="Team B",
            score_summary="10-16",
            elo_before=1520,
            elo_after=1500,
            elo_change=-20,
            had_dispute=False,
            is_forfeit=False,
            completed_at=timezone.now(),
        )
        
        # Filter by tournament1 only
        filter_dto = MatchHistoryFilterDTO.validate(
            team_id=sample_team.id,
            tournament_id=tournament1.id,
            limit=10,
            offset=0,
        )
        
        results = adapter.list_team_history(filter_dto)
        
        assert len(results) == 1
        assert results[0].tournament_id == tournament1.id
        assert results[0].elo_change == 20
    
    def test_list_team_history_filters_by_only_wins(
        self, adapter, sample_team, sample_tournament
    ):
        """Test listing team history filters by only_wins."""
        from apps.tournaments.models import Match
        
        # Create 2 matches: one win, one loss
        match1 = Match.objects.create(
            tournament=sample_tournament,
            participant1_id=sample_team.id,
            participant2_id=sample_team.id + 1,
            status="completed"
        )
        
        match2 = Match.objects.create(
            tournament=sample_tournament,
            participant1_id=sample_team.id,
            participant2_id=sample_team.id + 1,
            status="completed"
        )
        
        # Record win
        adapter.record_team_match_history(
            team_id=sample_team.id,
            match_id=match1.id,
            tournament_id=sample_tournament.id,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_team_id=None,
            opponent_team_name="Team A",
            score_summary="13-7",
            elo_before=1500,
            elo_after=1520,
            elo_change=20,
            had_dispute=False,
            is_forfeit=False,
            completed_at=timezone.now(),
        )
        
        # Record loss
        adapter.record_team_match_history(
            team_id=sample_team.id,
            match_id=match2.id,
            tournament_id=sample_tournament.id,
            game_slug="valorant",
            is_winner=False,
            is_draw=False,
            opponent_team_id=None,
            opponent_team_name="Team B",
            score_summary="7-13",
            elo_before=1520,
            elo_after=1500,
            elo_change=-20,
            had_dispute=False,
            is_forfeit=False,
            completed_at=timezone.now(),
        )
        
        # Filter for wins only
        filter_dto = MatchHistoryFilterDTO.validate(
            team_id=sample_team.id,
            only_wins=True,
            limit=10,
            offset=0,
        )
        
        results = adapter.list_team_history(filter_dto)
        
        assert len(results) == 1
        assert results[0].is_winner is True
        assert results[0].elo_change == 20
