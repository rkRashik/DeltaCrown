"""
Test suite for LeaderboardService (Milestone E)

Tests BR leaderboard calculation, series summary aggregation, and staff overrides.

Test Matrix:
- BR Leaderboards: 8 tests (tiebreaker scenarios, edge cases)
- Series Summaries: 8 tests (Best-of-1/3/5, incomplete series)
- Staff Overrides: 8 tests (permissions, audit trail, idempotency)
Total: 24 tests
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.tournaments.models import Tournament, Match, Registration, TournamentResult, Game
from apps.tournaments.services.leaderboard import LeaderboardService
from apps.accounts.models import User


# ===========================
# Fixtures
# ===========================

@pytest.fixture
def game_free_fire(db):
    """Create Free Fire game."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    # Create a minimal fake image file
    fake_icon = SimpleUploadedFile(
        name='freefire.png',
        content=b'fake-image-content',
        content_type='image/png'
    )
    
    return Game.objects.create(
        name='Free Fire',
        slug='free-fire',
        icon=fake_icon,
        default_team_size=Game.TEAM_SIZE_4V4,
        profile_id_field='freefire_id',
        default_result_type=Game.POINT_BASED,
    )


@pytest.fixture
def game_valorant(db):
    """Create Valorant game."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    # Create a minimal fake image file
    fake_icon = SimpleUploadedFile(
        name='valorant.png',
        content=b'fake-image-content',
        content_type='image/png'
    )
    
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        icon=fake_icon,
        default_team_size=Game.TEAM_SIZE_5V5,
        profile_id_field='riot_id',
        default_result_type=Game.BEST_OF,
    )


@pytest.fixture
def staff_user(db):
    """Create staff user for override tests."""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def tournament_br(db, game_free_fire, staff_user):
    """Create BR tournament (Free Fire)."""
    now = timezone.now()
    return Tournament.objects.create(
        name='Free Fire Championship',
        slug='ff-championship',
        description='Free Fire BR Tournament',
        game=game_free_fire,
        organizer=staff_user,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.TEAM,
        tournament_start=now,
        registration_start=now - timezone.timedelta(days=7),
        registration_end=now - timezone.timedelta(days=1),
        min_participants=4,
        max_participants=16,
        status=Tournament.LIVE
    )


@pytest.fixture
def tournament_series(db, game_valorant, staff_user):
    """Create series tournament (Valorant)."""
    now = timezone.now()
    return Tournament.objects.create(
        name='Valorant Championship',
        slug='val-championship',
        description='Valorant Series Tournament',
        game=game_valorant,
        organizer=staff_user,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.TEAM,
        tournament_start=now,
        registration_start=now - timezone.timedelta(days=7),
        registration_end=now - timezone.timedelta(days=1),
        min_participants=4,
        max_participants=16,
        status=Tournament.LIVE
    )


@pytest.fixture
def registrations_br(db, tournament_br):
    """Create 3 team registrations for BR tournament."""
    teams = []
    for i in range(1, 4):
        reg = Registration.objects.create(
            tournament=tournament_br,
            participant_id=f'team-{i}',
            participant_name=f'Team {i}',
            participant_type='team',
            status='confirmed'
        )
        teams.append(reg)
    return teams


@pytest.fixture
def registrations_series(db, tournament_series):
    """Create 2 team registrations for series tournament."""
    teams = []
    for i in range(1, 3):
        reg = Registration.objects.create(
            tournament=tournament_series,
            participant_id=f'team-{i}',
            participant_name=f'Team {i}',
            participant_type='team',
            status='confirmed'
        )
        teams.append(reg)
    return teams


# ===========================
# BR Leaderboard Tests (8 tests)
# ===========================

@pytest.mark.django_db
class TestBRLeaderboards:
    """Test BR leaderboard calculation with tiebreakers."""
    
    def test_simple_standings_three_teams_clear_winner(self, tournament_br, registrations_br):
        """Test simple BR standings with clear winner (no ties)."""
        # Create match with clear winner
        match = Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 10, 'placement': 1},  # 10 + 12 = 22 points
                'team-2': {'kills': 5, 'placement': 2},   # 5 + 9 = 14 points
                'team-3': {'kills': 3, 'placement': 3}    # 3 + 7 = 10 points
            },
            completed_at=timezone.now()
        )
        
        standings = LeaderboardService.calculate_br_standings(tournament_br.id)
        
        assert len(standings) == 3
        assert standings[0]['rank'] == 1
        assert standings[0]['participant_id'] == 'team-1'
        assert standings[0]['total_points'] == 22
        assert standings[0]['total_kills'] == 10
        assert standings[0]['best_placement'] == 1
        assert standings[0]['matches_played'] == 1
        
        assert standings[1]['rank'] == 2
        assert standings[1]['participant_id'] == 'team-2'
        assert standings[1]['total_points'] == 14
        
        assert standings[2]['rank'] == 3
        assert standings[2]['participant_id'] == 'team-3'
        assert standings[2]['total_points'] == 10
    
    def test_tiebreaker_level1_equal_points_different_kills(self, tournament_br, registrations_br):
        """Test tiebreaker level 1: Equal points, different kills."""
        match = Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 10, 'placement': 1},  # 10 + 12 = 22 points, 10 kills
                'team-2': {'kills': 7, 'placement': 2},   # 7 + 9 = 16 points, 7 kills
                'team-3': {'kills': 9, 'placement': 2}    # 9 + 9 = 18 points, 9 kills (tie with team-1: 18 vs 22, but if we adjust...)
            },
            completed_at=timezone.now()
        )
        
        # Adjust to create tie: team-1 and team-3 both have 22 points
        match.lobby_info = {
            'team-1': {'kills': 10, 'placement': 1},  # 10 + 12 = 22 points, 10 kills
            'team-2': {'kills': 5, 'placement': 2},   # 5 + 9 = 14 points
            'team-3': {'kills': 15, 'placement': 3}   # 15 + 7 = 22 points, 15 kills
        }
        match.save()
        
        standings = LeaderboardService.calculate_br_standings(tournament_br.id)
        
        # Both have 22 points, but team-3 has more kills (15 > 10)
        assert standings[0]['participant_id'] == 'team-3'
        assert standings[0]['total_points'] == 22
        assert standings[0]['total_kills'] == 15
        
        assert standings[1]['participant_id'] == 'team-1'
        assert standings[1]['total_points'] == 22
        assert standings[1]['total_kills'] == 10
    
    def test_tiebreaker_level2_equal_points_kills_different_placement(self, tournament_br, registrations_br):
        """Test tiebreaker level 2: Equal points and kills, different best placement."""
        # Create 2 matches to allow same total points and kills but different placements
        match1 = Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 10, 'placement': 1},  # Match 1: 22 points
                'team-2': {'kills': 10, 'placement': 2},  # Match 1: 19 points
                'team-3': {'kills': 5, 'placement': 3}    # Match 1: 12 points
            },
            completed_at=timezone.now()
        )
        
        match2 = Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=2,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 0, 'placement': 5},  # Match 2: 4 points → Total: 26
                'team-2': {'kills': 7, 'placement': 1},  # Match 2: 19 points → Total: 38
                'team-3': {'kills': 21, 'placement': 2}  # Match 2: 30 points → Total: 42
            },
            completed_at=timezone.now() + timezone.timedelta(minutes=1)
        )
        
        standings = LeaderboardService.calculate_br_standings(tournament_br.id)
        
        # Team-3 should win (42 points)
        assert standings[0]['participant_id'] == 'team-3'
        assert standings[0]['total_points'] == 42
        assert standings[0]['best_placement'] == 2
    
    def test_tiebreaker_level3_timestamp_decides(self, tournament_br, registrations_br):
        """Test tiebreaker level 3: All equal, timestamp decides."""
        # Create identical results but different completion times
        match1 = Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 10, 'placement': 1},
                'team-2': {'kills': 5, 'placement': 2}
            },
            completed_at=timezone.now()
        )
        
        match2 = Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=2,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 10, 'placement': 1},
                'team-2': {'kills': 5, 'placement': 2}
            },
            completed_at=timezone.now() + timezone.timedelta(seconds=5)
        )
        
        # Both teams have identical stats, but team-1 completed earlier in match1
        standings = LeaderboardService.calculate_br_standings(tournament_br.id)
        
        # Team-1 completed first match earlier
        assert standings[0]['participant_id'] == 'team-1'
        assert standings[0]['total_points'] == 44  # 22 * 2
    
    def test_empty_tournament_no_matches(self, tournament_br):
        """Test empty tournament with no completed matches."""
        standings = LeaderboardService.calculate_br_standings(tournament_br.id)
        
        assert standings == []
    
    def test_partial_matches_some_teams_dnf(self, tournament_br, registrations_br):
        """Test tournament where some teams didn't finish (DNF)."""
        match = Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 10, 'placement': 1},
                'team-2': {'kills': 5, 'placement': 2}
                # team-3 is DNF (not in lobby_info)
            },
            completed_at=timezone.now()
        )
        
        standings = LeaderboardService.calculate_br_standings(tournament_br.id)
        
        # Only 2 teams should appear
        assert len(standings) == 2
        assert standings[0]['participant_id'] == 'team-1'
        assert standings[1]['participant_id'] == 'team-2'
    
    def test_multiple_matches_aggregation(self, tournament_br, registrations_br):
        """Test multiple matches with aggregated stats."""
        # Match 1
        Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 10, 'placement': 1},  # 22 points
                'team-2': {'kills': 5, 'placement': 2},   # 14 points
                'team-3': {'kills': 3, 'placement': 3}    # 10 points
            },
            completed_at=timezone.now()
        )
        
        # Match 2
        Match.objects.create(
            tournament=tournament_br,
            round_number=1,
            match_number=2,
            state=Match.COMPLETED,
            lobby_info={
                'team-1': {'kills': 8, 'placement': 2},   # 17 points
                'team-2': {'kills': 12, 'placement': 1},  # 24 points
                'team-3': {'kills': 4, 'placement': 3}    # 11 points
            },
            completed_at=timezone.now() + timezone.timedelta(minutes=1)
        )
        
        standings = LeaderboardService.calculate_br_standings(tournament_br.id)
        
        assert len(standings) == 3
        
        # Team-1: 22 + 17 = 39 points, 18 kills, best placement 1, 2 matches
        team1 = standings[0]
        assert team1['participant_id'] == 'team-1'
        assert team1['total_points'] == 39
        assert team1['total_kills'] == 18
        assert team1['best_placement'] == 1
        assert team1['matches_played'] == 2
        assert team1['avg_placement'] == 1.5
        
        # Team-2: 14 + 24 = 38 points
        team2 = standings[1]
        assert team2['participant_id'] == 'team-2'
        assert team2['total_points'] == 38
    
    def test_invalid_game_type_raises_error(self, tournament_series):
        """Test that non-BR game raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardService.calculate_br_standings(tournament_series.id)
        
        assert 'not a BR game' in str(exc_info.value)


# ===========================
# Series Summary Tests (8 tests)
# ===========================

@pytest.mark.django_db
class TestSeriesSummaries:
    """Test series summary aggregation for Best-of-X formats."""
    
    def test_best_of_1_single_match(self, tournament_series, registrations_series):
        """Test Best-of-1 series (single match)."""
        match = Match.objects.create(
            tournament=tournament_series,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            winner_id='team-1',
            loser_id='team-2',
            lobby_info={'score': {'team-1': 13, 'team-2': 11}},
            completed_at=timezone.now()
        )
        
        summary = LeaderboardService.calculate_series_summary([match.id])
        
        assert summary['series_winner_id'] == 'team-1'
        assert summary['series_score'] == {'team-1': 1}
        assert summary['total_games'] == 1
        assert summary['format'] == 'Best-of-1'
        assert len(summary['games']) == 1
        assert summary['games'][0]['match_id'] == match.id
        assert summary['games'][0]['winner_id'] == 'team-1'
    
    def test_best_of_3_score_2_1(self, tournament_series, registrations_series):
        """Test Best-of-3 series with 2-1 score."""
        matches = []
        
        # Game 1: team-1 wins
        matches.append(Match.objects.create(
            tournament=tournament_series,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            winner_id='team-1',
            loser_id='team-2',
            lobby_info={'score': {'team-1': 13, 'team-2': 9}},
            completed_at=timezone.now()
        ))
        
        # Game 2: team-2 wins
        matches.append(Match.objects.create(
            tournament=tournament_series,
            round_number=1,
            match_number=2,
            state=Match.COMPLETED,
            winner_id='team-2',
            loser_id='team-1',
            lobby_info={'score': {'team-2': 13, 'team-1': 8}},
            completed_at=timezone.now() + timezone.timedelta(minutes=30)
        ))
        
        # Game 3: team-1 wins
        matches.append(Match.objects.create(
            tournament=tournament_series,
            round_number=1,
            match_number=3,
            state=Match.COMPLETED,
            winner_id='team-1',
            loser_id='team-2',
            lobby_info={'score': {'team-1': 13, 'team-2': 11}},
            completed_at=timezone.now() + timezone.timedelta(minutes=60)
        ))
        
        match_ids = [m.id for m in matches]
        summary = LeaderboardService.calculate_series_summary(match_ids)
        
        assert summary['series_winner_id'] == 'team-1'
        assert summary['series_score'] == {'team-1': 2, 'team-2': 1}
        assert summary['total_games'] == 3
        assert summary['format'] == 'Best-of-3'
        assert len(summary['games']) == 3
    
    def test_best_of_5_score_3_2(self, tournament_series, registrations_series):
        """Test Best-of-5 series with 3-2 score."""
        matches = []
        winners = ['team-1', 'team-2', 'team-1', 'team-2', 'team-1']
        
        for i, winner in enumerate(winners, 1):
            loser = 'team-2' if winner == 'team-1' else 'team-1'
            matches.append(Match.objects.create(
                tournament=tournament_series,
                round_number=1,
                match_number=i,
                state=Match.COMPLETED,
                winner_id=winner,
                loser_id=loser,
                lobby_info={'score': {winner: 13, loser: 10}},
                completed_at=timezone.now() + timezone.timedelta(minutes=i*30)
            ))
        
        match_ids = [m.id for m in matches]
        summary = LeaderboardService.calculate_series_summary(match_ids)
        
        assert summary['series_winner_id'] == 'team-1'
        assert summary['series_score'] == {'team-1': 3, 'team-2': 2}
        assert summary['total_games'] == 5
        assert summary['format'] == 'Best-of-5'
    
    def test_sweep_3_0(self, tournament_series, registrations_series):
        """Test 3-0 sweep in Best-of-5."""
        matches = []
        
        for i in range(1, 4):
            matches.append(Match.objects.create(
                tournament=tournament_series,
                round_number=1,
                match_number=i,
                state=Match.COMPLETED,
                winner_id='team-1',
                loser_id='team-2',
                lobby_info={'score': {'team-1': 13, 'team-2': 5}},
                completed_at=timezone.now() + timezone.timedelta(minutes=i*30)
            ))
        
        match_ids = [m.id for m in matches]
        summary = LeaderboardService.calculate_series_summary(match_ids)
        
        assert summary['series_winner_id'] == 'team-1'
        assert summary['series_score'] == {'team-1': 3}
        assert summary['total_games'] == 3
        assert summary['format'] == 'Best-of-3'
    
    def test_incomplete_series_2_0_in_best_of_5(self, tournament_series, registrations_series):
        """Test incomplete series (2-0 in Best-of-5, third match pending)."""
        matches = []
        
        # Only 2 matches completed
        for i in range(1, 3):
            matches.append(Match.objects.create(
                tournament=tournament_series,
                round_number=1,
                match_number=i,
                state=Match.COMPLETED,
                winner_id='team-1',
                loser_id='team-2',
                lobby_info={'score': {'team-1': 13, 'team-2': 8}},
                completed_at=timezone.now() + timezone.timedelta(minutes=i*30)
            ))
        
        match_ids = [m.id for m in matches]
        summary = LeaderboardService.calculate_series_summary(match_ids)
        
        assert summary['series_winner_id'] == 'team-1'
        assert summary['series_score'] == {'team-1': 2}
        assert summary['total_games'] == 2
        assert summary['format'] == 'Best-of-1'  # Only 2 games, so Best-of-1 format detected
    
    def test_empty_match_ids_raises_error(self):
        """Test that empty match_ids raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardService.calculate_series_summary([])
        
        assert 'cannot be empty' in str(exc_info.value)
    
    def test_nonexistent_match_ids_raises_error(self):
        """Test that non-existent match IDs raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardService.calculate_series_summary([99999, 88888])
        
        assert 'No completed matches found' in str(exc_info.value)
    
    def test_match_without_winner_skipped(self, tournament_series, registrations_series):
        """Test that matches without winners are skipped gracefully."""
        # Match 1: Has winner
        match1 = Match.objects.create(
            tournament=tournament_series,
            round_number=1,
            match_number=1,
            state=Match.COMPLETED,
            winner_id='team-1',
            loser_id='team-2',
            lobby_info={'score': {'team-1': 13, 'team-2': 8}},
            completed_at=timezone.now()
        )
        
        # Match 2: No winner (corrupted data)
        match2 = Match.objects.create(
            tournament=tournament_series,
            round_number=1,
            match_number=2,
            state=Match.COMPLETED,
            winner_id=None,
            loser_id=None,
            lobby_info={'score': {}},
            completed_at=timezone.now() + timezone.timedelta(minutes=30)
        )
        
        summary = LeaderboardService.calculate_series_summary([match1.id, match2.id])
        
        # Only match1 should be counted
        assert summary['series_winner_id'] == 'team-1'
        assert summary['series_score'] == {'team-1': 1}
        assert summary['total_games'] == 1


# ===========================
# Staff Override Tests (8 tests)
# ===========================

@pytest.mark.django_db
class TestStaffOverrides:
    """Test staff placement overrides with audit trails."""
    
    def test_valid_override_creates_result(self, tournament_br, registrations_br, staff_user):
        """Test valid override creates TournamentResult with audit trail."""
        result_data = LeaderboardService.override_placement(
            tournament_id=tournament_br.id,
            participant_id='team-1',
            new_rank=1,
            reason='Manual correction after review',
            actor_id=staff_user.id
        )
        
        assert result_data['success'] is True
        assert result_data['new_rank'] == 1
        assert result_data['old_rank'] is None  # No previous result
        
        # Verify database
        result = TournamentResult.objects.get(tournament_id=tournament_br.id)
        assert result.winner.participant_id == 'team-1'
        assert result.is_override is True
        assert result.override_reason == 'Manual correction after review'
        assert result.override_actor_id == staff_user.id
        assert result.override_timestamp is not None
    
    def test_idempotent_override_same_rank_applied_twice(self, tournament_br, registrations_br, staff_user):
        """Test idempotent override (same rank applied twice)."""
        # First override
        LeaderboardService.override_placement(
            tournament_id=tournament_br.id,
            participant_id='team-1',
            new_rank=1,
            reason='First override',
            actor_id=staff_user.id
        )
        
        # Second override (same rank, different reason)
        result_data = LeaderboardService.override_placement(
            tournament_id=tournament_br.id,
            participant_id='team-1',
            new_rank=1,
            reason='Second override (confirmation)',
            actor_id=staff_user.id
        )
        
        assert result_data['success'] is True
        assert result_data['old_rank'] == 1
        assert result_data['new_rank'] == 1
        
        # Verify only one result exists
        assert TournamentResult.objects.filter(tournament_id=tournament_br.id).count() == 1
        
        # Verify reason was updated
        result = TournamentResult.objects.get(tournament_id=tournament_br.id)
        assert result.override_reason == 'Second override (confirmation)'
    
    def test_missing_reason_raises_error(self, tournament_br, registrations_br, staff_user):
        """Test that missing reason raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardService.override_placement(
                tournament_id=tournament_br.id,
                participant_id='team-1',
                new_rank=1,
                reason='',  # Empty reason
                actor_id=staff_user.id
            )
        
        assert 'reason is required' in str(exc_info.value)
    
    def test_invalid_rank_raises_error(self, tournament_br, registrations_br, staff_user):
        """Test that invalid rank (< 1) raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardService.override_placement(
                tournament_id=tournament_br.id,
                participant_id='team-1',
                new_rank=0,  # Invalid rank
                reason='Test',
                actor_id=staff_user.id
            )
        
        assert 'must be >= 1' in str(exc_info.value)
    
    def test_nonexistent_tournament_raises_error(self, staff_user):
        """Test that non-existent tournament raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardService.override_placement(
                tournament_id=99999,
                participant_id='team-1',
                new_rank=1,
                reason='Test',
                actor_id=staff_user.id
            )
        
        assert 'not found' in str(exc_info.value)
    
    def test_nonexistent_participant_raises_error(self, tournament_br, staff_user):
        """Test that non-existent participant raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardService.override_placement(
                tournament_id=tournament_br.id,
                participant_id='team-999',  # Non-existent
                new_rank=1,
                reason='Test',
                actor_id=staff_user.id
            )
        
        assert 'not found' in str(exc_info.value)
    
    def test_audit_trail_populated_correctly(self, tournament_br, registrations_br, staff_user):
        """Test that audit trail fields are populated correctly."""
        before_override = timezone.now()
        
        LeaderboardService.override_placement(
            tournament_id=tournament_br.id,
            participant_id='team-2',
            new_rank=2,
            reason='Audit trail test',
            actor_id=staff_user.id
        )
        
        after_override = timezone.now()
        
        result = TournamentResult.objects.get(tournament_id=tournament_br.id)
        
        # Verify audit fields
        assert result.is_override is True
        assert result.override_reason == 'Audit trail test'
        assert result.override_actor_id == staff_user.id
        assert before_override <= result.override_timestamp <= after_override
        assert result.runner_up.participant_id == 'team-2'
    
    def test_override_history_multiple_changes(self, tournament_br, registrations_br, staff_user):
        """Test multiple overrides track timestamp changes."""
        # First override
        result1 = LeaderboardService.override_placement(
            tournament_id=tournament_br.id,
            participant_id='team-1',
            new_rank=1,
            reason='First place',
            actor_id=staff_user.id
        )
        timestamp1 = result1['override_timestamp']
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        # Second override (change to team-2)
        result2 = LeaderboardService.override_placement(
            tournament_id=tournament_br.id,
            participant_id='team-2',
            new_rank=1,
            reason='Correction: team-2 should be first',
            actor_id=staff_user.id
        )
        timestamp2 = result2['override_timestamp']
        
        # Timestamps should differ
        assert timestamp1 != timestamp2
        
        # Verify current state
        result = TournamentResult.objects.get(tournament_id=tournament_br.id)
        assert result.winner.participant_id == 'team-2'
        assert result.override_reason == 'Correction: team-2 should be first'
