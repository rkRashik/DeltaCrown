# tests/test_ranking_service_module_4_2.py
"""
Module 4.2: Ranking & Seeding Integration Tests

Tests for TournamentRankingService and ranked seeding in bracket generation.
Covers:
- Ranked participant sorting with deterministic tie-breaking
- Integration with apps.teams ranking system
- Validation for missing/incomplete ranking data
- Edge cases (ties, missing ranks, individual participants)
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.tournaments.models import Tournament, Bracket, Game
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.ranking_service import ranking_service
from apps.teams.models import Team, TeamRankingBreakdown
from apps.user_profile.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestRankingServiceCore:
    """Core unit tests for TournamentRankingService."""

    @pytest.fixture
    def game(self):
        """Create a game for tournaments."""
        return Game.objects.create(
            name="VALORANT",
            slug="valorant",
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
            is_active=True
        )

    @pytest.fixture
    def tournament(self, game):
        """Create a tournament for testing."""
        organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="testpass123"
        )
        return Tournament.objects.create(
            name="Ranked Test Tournament",
            slug="ranked-test",
            game=game,
            organizer=organizer,
            format='single_elimination',
            participation_type='team',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(days=7),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=1),
            max_participants=8,
            min_participants=2
        )

    @pytest.fixture
    def teams_with_rankings(self, game):
        """Create 4 teams with different ranking points."""
        teams = []
        for i in range(1, 5):
            team = Team.objects.create(
                name=f"Team {i}",
                tag=f"T{i}",
                game=game.slug,
                created_at=timezone.now() - timedelta(days=i*30)  # Different ages
            )
            # Create ranking breakdown
            TeamRankingBreakdown.objects.create(
                team=team,
                team_age_points=100,
                member_count_points=50,
                tournament_participation_points=0,
                tournament_winner_points=(500 if i == 1 else 0),  # Team 1 is winner
                tournament_runner_up_points=(300 if i == 2 else 0),  # Team 2 is runner-up
                tournament_top_4_points=0,
                achievement_points=0,
                manual_adjustment_points=0
            )
            team.refresh_from_db()  # Ensure total_points is calculated
            teams.append(team)
        
        return teams

    def test_get_ranked_participants_sorts_by_points(self, tournament, teams_with_rankings):
        """Test that participants are sorted by ranking points (DESC)."""
        participants = [
            {'participant_id': team.id, 'is_team': True, 'name': team.name}
            for team in teams_with_rankings
        ]
        
        sorted_participants = ranking_service.get_ranked_participants(
            participants=participants,
            tournament=tournament
        )
        
        # Team 1 (winner) should be seed 1, Team 2 (runner-up) seed 2, etc.
        assert sorted_participants[0]['seed'] == 1
        assert sorted_participants[0]['participant_id'] == teams_with_rankings[0].id
        assert sorted_participants[0]['_ranking_points'] == 650  # 100+50+500
        
        assert sorted_participants[1]['seed'] == 2
        assert sorted_participants[1]['participant_id'] == teams_with_rankings[1].id
        assert sorted_participants[1]['_ranking_points'] == 450  # 100+50+300
        
        assert sorted_participants[2]['seed'] == 3
        assert sorted_participants[3]['seed'] == 4

    def test_get_ranked_participants_deterministic_tie_breaking(self, tournament, game):
        """Test that ties are broken deterministically by team age, then ID."""
        # Create 3 teams with identical points but different ages
        teams = []
        for i in range(1, 4):
            team = Team.objects.create(
                name=f"TiedTeam {i}",
                tag=f"TT{i}",
                game=game.slug,
                created_at=timezone.now() - timedelta(days=i*10)
            )
            TeamRankingBreakdown.objects.create(
                team=team,
                team_age_points=100,
                member_count_points=50,
                tournament_participation_points=0,
                tournament_winner_points=0,
                tournament_runner_up_points=0,
                tournament_top_4_points=0,
                achievement_points=0,
                manual_adjustment_points=0
            )
            teams.append(team)
        
        participants = [
            {'participant_id': team.id, 'is_team': True, 'name': team.name}
            for team in teams
        ]
        
        sorted_participants = ranking_service.get_ranked_participants(
            participants=participants,
            tournament=tournament
        )
        
        # All teams have 150 points, so sort by age (older first)
        assert sorted_participants[0]['participant_id'] == teams[2].id  # Oldest (30 days)
        assert sorted_participants[1]['participant_id'] == teams[1].id  # 20 days
        assert sorted_participants[2]['participant_id'] == teams[0].id  # Newest (10 days)
        
        # Seeds assigned correctly
        assert sorted_participants[0]['seed'] == 1
        assert sorted_participants[1]['seed'] == 2
        assert sorted_participants[2]['seed'] == 3

    def test_get_ranked_participants_raises_on_missing_rankings(self, tournament, game):
        """Test that ValidationError is raised if a team lacks ranking data."""
        # Create team WITHOUT ranking breakdown
        team_without_rank = Team.objects.create(
            name="Unranked Team",
            tag="UT",
            game=game.slug
        )
        
        participants = [
            {'participant_id': team_without_rank.id, 'is_team': True, 'name': team_without_rank.name}
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            ranking_service.get_ranked_participants(
                participants=participants,
                tournament=tournament
            )
        
        assert "Missing rankings for: Unranked Team" in str(exc_info.value)

    def test_get_ranked_participants_raises_on_individual_participants(self, tournament):
        """Test that ValidationError is raised for individual participants."""
        user = User.objects.create_user(username="player1", email="p1@test.com", password="pass")
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'display_name': 'Player 1'})
        
        participants = [
            {'participant_id': profile.id, 'is_team': False, 'name': 'Player 1'}
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            ranking_service.get_ranked_participants(
                participants=participants,
                tournament=tournament
            )
        
        assert "only supported for team-based tournaments" in str(exc_info.value)

    def test_get_ranked_participants_handles_empty_list(self, tournament):
        """Test that empty participant list returns empty list."""
        result = ranking_service.get_ranked_participants(
            participants=[],
            tournament=tournament
        )
        assert result == []


@pytest.mark.django_db
class TestBracketServiceRankedIntegration:
    """Integration tests for ranked seeding in BracketService."""

    @pytest.fixture
    def game(self):
        return Game.objects.create(
            name="CS2",
            slug="cs2",
            default_team_size=5,
            profile_id_field='steam_id',
            default_result_type='map_score',
            is_active=True
        )

    @pytest.fixture
    def tournament(self, game):
        organizer = User.objects.create_user(
            username="org2", email="org2@test.com", password="pass"
        )
        return Tournament.objects.create(
            name="Ranked Bracket Test",
            slug="ranked-bracket",
            game=game,
            organizer=organizer,
            format='single_elimination',
            participation_type='team',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(days=7),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=1),
            max_participants=8,
            min_participants=2
        )

    @pytest.fixture
    def ranked_teams(self, game):
        """Create 4 teams with distinct rankings."""
        teams = []
        points_list = [1000, 750, 500, 250]  # Clear ranking order
        for i, points in enumerate(points_list, start=1):
            team = Team.objects.create(
                name=f"RankedTeam {i}",
                tag=f"RT{i}",
                game=game.slug
            )
            TeamRankingBreakdown.objects.create(
                team=team,
                team_age_points=points // 2,
                member_count_points=points // 2,
                tournament_participation_points=0,
                tournament_winner_points=0,
                tournament_runner_up_points=0,
                tournament_top_4_points=0,
                achievement_points=0,
                manual_adjustment_points=0
            )
            teams.append(team)
        return teams

    def test_apply_seeding_ranked_method(self, tournament, ranked_teams):
        """Test BracketService.apply_seeding with RANKED method."""
        participants = [
            {'participant_id': team.id, 'is_team': True, 'name': team.name}
            for team in ranked_teams
        ]
        
        seeded = BracketService.apply_seeding(
            participants=participants,
            seeding_method=Bracket.RANKED,
            tournament=tournament
        )
        
        # Should be sorted by ranking (highest points first)
        assert seeded[0]['seed'] == 1
        assert seeded[0]['participant_id'] == ranked_teams[0].id  # 1000 points
        
        assert seeded[1]['seed'] == 2
        assert seeded[1]['participant_id'] == ranked_teams[1].id  # 750 points
        
        assert seeded[2]['seed'] == 3
        assert seeded[2]['participant_id'] == ranked_teams[2].id  # 500 points
        
        assert seeded[3]['seed'] == 4
        assert seeded[3]['participant_id'] == ranked_teams[3].id  # 250 points

    def test_apply_seeding_ranked_raises_on_missing_tournament(self, ranked_teams):
        """Test that ranked seeding requires tournament parameter."""
        participants = [
            {'participant_id': team.id, 'is_team': True, 'name': team.name}
            for team in ranked_teams
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            BracketService.apply_seeding(
                participants=participants,
                seeding_method=Bracket.RANKED,
                tournament=None  # Missing tournament
            )
        
        assert "Tournament required for ranked seeding" in str(exc_info.value)

    def test_apply_seeding_ranked_raises_on_incomplete_rankings(self, tournament, game):
        """Test that ranked seeding fails if any team lacks rankings."""
        # One team with ranking, one without
        team1 = Team.objects.create(name="Ranked", tag="R", game=game.slug)
        TeamRankingBreakdown.objects.create(
            team=team1,
            team_age_points=100,
            member_count_points=50,
            tournament_participation_points=0,
            tournament_winner_points=0,
            tournament_runner_up_points=0,
            tournament_top_4_points=0,
            achievement_points=0,
            manual_adjustment_points=0
        )
        
        team2 = Team.objects.create(name="Unranked", tag="U", game=game.slug)
        # No ranking breakdown for team2
        
        participants = [
            {'participant_id': team1.id, 'is_team': True, 'name': team1.name},
            {'participant_id': team2.id, 'is_team': True, 'name': team2.name},
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            BracketService.apply_seeding(
                participants=participants,
                seeding_method=Bracket.RANKED,
                tournament=tournament
            )
        
        assert "Missing rankings for: Unranked" in str(exc_info.value)


@pytest.mark.django_db
class TestRankedSeedingEdgeCases:
    """Edge case tests for ranked seeding."""

    @pytest.fixture
    def game(self):
        return Game.objects.create(
            name="eFOOTBALL",
            slug="efootball",
            default_team_size=1,
            profile_id_field='ea_id',
            default_result_type='point_based',
            is_active=True
        )

    @pytest.fixture
    def tournament(self, game):
        organizer = User.objects.create_user(
            username="org3", email="org3@test.com", password="pass"
        )
        return Tournament.objects.create(
            name="Edge Case Tournament",
            slug="edge-case",
            game=game,
            organizer=organizer,
            format='single_elimination',
            participation_type='team',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(days=7),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=1),
            max_participants=2,
            min_participants=2
        )

    def test_ranked_seeding_with_single_participant(self, tournament, game):
        """Test ranked seeding works with just 1 participant."""
        team = Team.objects.create(name="Solo Team", tag="ST", game=game.slug)
        TeamRankingBreakdown.objects.create(
            team=team,
            team_age_points=50,
            member_count_points=25,
            tournament_participation_points=0,
            tournament_winner_points=0,
            tournament_runner_up_points=0,
            tournament_top_4_points=0,
            achievement_points=0,
            manual_adjustment_points=0
        )
        
        participants = [{'participant_id': team.id, 'is_team': True, 'name': team.name}]
        
        result = ranking_service.get_ranked_participants(
            participants=participants,
            tournament=tournament
        )
        
        assert len(result) == 1
        assert result[0]['seed'] == 1

    def test_ranked_seeding_all_teams_zero_points(self, tournament, game):
        """Test ranked seeding when all teams have 0 points (tie-break by age)."""
        teams = []
        for i in range(1, 4):
            team = Team.objects.create(
                name=f"ZeroTeam {i}",
                tag=f"ZT{i}",
                game=game.slug,
                created_at=timezone.now() - timedelta(days=i*5)
            )
            TeamRankingBreakdown.objects.create(
                team=team,
                team_age_points=0,
                member_count_points=0,
                tournament_participation_points=0,
                tournament_winner_points=0,
                tournament_runner_up_points=0,
                tournament_top_4_points=0,
                achievement_points=0,
                manual_adjustment_points=0
            )
            teams.append(team)
        
        participants = [
            {'participant_id': team.id, 'is_team': True, 'name': team.name}
            for team in teams
        ]
        
        result = ranking_service.get_ranked_participants(
            participants=participants,
            tournament=tournament
        )
        
        # All have 0 points, sorted by age (oldest first)
        assert result[0]['participant_id'] == teams[2].id  # 15 days old
        assert result[1]['participant_id'] == teams[1].id  # 10 days old
        assert result[2]['participant_id'] == teams[0].id  # 5 days old

    def test_ranked_seeding_preserves_participant_metadata(self, tournament, game):
        """Test that ranked seeding preserves original participant dict keys."""
        team = Team.objects.create(name="MetaTeam", tag="MT", game=game.slug)
        TeamRankingBreakdown.objects.create(
            team=team,
            team_age_points=100,
            member_count_points=50,
            tournament_participation_points=0,
            tournament_winner_points=0,
            tournament_runner_up_points=0,
            tournament_top_4_points=0,
            achievement_points=0,
            manual_adjustment_points=0
        )
        
        participants = [
            {
                'participant_id': team.id,
                'is_team': True,
                'name': team.name,
                'custom_field': 'custom_value',
                'another_field': 123
            }
        ]
        
        result = ranking_service.get_ranked_participants(
            participants=participants,
            tournament=tournament
        )
        
        assert result[0]['custom_field'] == 'custom_value'
        assert result[0]['another_field'] == 123
        assert result[0]['seed'] == 1
        assert '_ranking_points' in result[0]  # Added by service


@pytest.mark.django_db
class TestRankedSeedingAPIValidation:
    """Tests for API-level validation with ranked seeding."""

    @pytest.fixture
    def game(self):
        return Game.objects.create(
            name="Dota 2",
            slug="dota2",
            default_team_size=5,
            profile_id_field='steam_id',
            default_result_type='best_of',
            is_active=True
        )

    @pytest.fixture
    def tournament(self, game):
        organizer = User.objects.create_user(
            username="org4", email="org4@test.com", password="pass"
        )
        return Tournament.objects.create(
            name="API Validation Test",
            slug="api-valid",
            game=game,
            organizer=organizer,
            format='single_elimination',
            participation_type='team',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(days=7),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=1),
            max_participants=16,
            min_participants=2
        )

    def test_validation_error_is_400_not_500(self, tournament, game):
        """Test that ValidationError from ranked seeding results in 400, not 500."""
        # Create team without ranking
        team = Team.objects.create(name="NoRank", tag="NR", game=game.slug)
        
        participants = [
            {'participant_id': team.id, 'is_team': True, 'name': team.name}
        ]
        
        # BracketService should raise ValidationError (not generic Exception)
        with pytest.raises(ValidationError) as exc_info:
            BracketService.apply_seeding(
                participants=participants,
                seeding_method=Bracket.RANKED,
                tournament=tournament
            )
        
        # ValidationError should have user-friendly message
        error_message = str(exc_info.value)
        assert "Missing rankings" in error_message
        assert "NoRank" in error_message

    def test_exception_handling_wraps_unexpected_errors(self, tournament, game, monkeypatch):
        """Test that unexpected errors are wrapped in ValidationError with context."""
        team = Team.objects.create(name="TestTeam", tag="TT", game=game.slug)
        TeamRankingBreakdown.objects.create(
            team=team,
            team_age_points=100,
            member_count_points=50,
            tournament_participation_points=0,
            tournament_winner_points=0,
            tournament_runner_up_points=0,
            tournament_top_4_points=0,
            achievement_points=0,
            manual_adjustment_points=0
        )
        
        participants = [
            {'participant_id': team.id, 'is_team': True, 'name': team.name}
        ]
        
        # Mock ranking_service to raise unexpected error
        from apps.tournaments.services.ranking_service import ranking_service as rs
        
        def mock_get_ranked_participants(*args, **kwargs):
            raise RuntimeError("Database connection lost")
        
        monkeypatch.setattr(rs, 'get_ranked_participants', mock_get_ranked_participants)
        
        # Should wrap RuntimeError in ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BracketService.apply_seeding(
                participants=participants,
                seeding_method=Bracket.RANKED,
                tournament=tournament
            )
        
        error_message = str(exc_info.value)
        assert "Failed to apply ranked seeding" in error_message
        assert "Database connection lost" in error_message
