"""
Integration tests for Tournament → TeamGameRanking flow.

Tests the end-to-end integration between:
- Tournament results (TournamentResult model)
- Ranking point awards (game_ranking_service.award_tournament_points)
- TeamGameRanking updates
"""

import pytest
from decimal import Decimal
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.organizations.models import Team
from apps.teams.models.ranking import TeamGameRanking
from apps.tournaments.models import Tournament, TournamentResult, Game as TournamentGame
from apps.tournaments.models.registration import Registration

User = get_user_model()


@pytest.mark.django_db
class TestTournamentRankingIntegration(TransactionTestCase):
    """Test tournament results correctly update team rankings."""
    
    def setUp(self):
        """Create test data: game, teams, tournament."""
        # Create a tournament game
        self.game = TournamentGame.objects.create(
            name='VALORANT',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            is_active=True
        )
        
        # Create test user for team ownership
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create teams
        self.team_winner = Team.objects.create(
            name='Winner Team',
            tag='WIN',
            game=self.game.slug
        )
        
        self.team_runner_up = Team.objects.create(
            name='Runner Up Team',
            tag='RUN',
            game=self.game.slug
        )
        
        self.team_third = Team.objects.create(
            name='Third Place Team',
            tag='3RD',
            game=self.game.slug
        )
        
        # Create tournament
        now = timezone.now()
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            description='Test tournament for rankings',
            game=self.game,
            organizer=self.user,
            max_participants=16,
            registration_start=now - timedelta(days=7),
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=8)
        )
        
        # Create registrations for teams
        self.reg_winner = Registration.objects.create(
            tournament=self.tournament,
            team_id=self.team_winner.id,
            status=Registration.CONFIRMED
        )
        
        self.reg_runner_up = Registration.objects.create(
            tournament=self.tournament,
            team_id=self.team_runner_up.id,
            status=Registration.CONFIRMED
        )
        
        self.reg_third = Registration.objects.create(
            tournament=self.tournament,
            team_id=self.team_third.id,
            status=Registration.CONFIRMED
        )
    
    def test_tournament_result_creates_rankings(self):
        """Test that creating a tournament result creates TeamGameRanking records."""
        # Create tournament result
        result = TournamentResult.objects.create(
            tournament=self.tournament,
            winner=self.reg_winner,
            runner_up=self.reg_runner_up,
            third_place=self.reg_third
        )
        
        # Check that rankings exist for all teams
        winner_ranking = TeamGameRanking.objects.filter(
            team=self.team_winner,
            game=self.game.slug
        ).first()
        
        runner_up_ranking = TeamGameRanking.objects.filter(
            team=self.team_runner_up,
            game=self.game.slug
        ).first()
        
        third_ranking = TeamGameRanking.objects.filter(
            team=self.team_third,
            game=self.game.slug
        ).first()
        
        # Assert rankings were created
        self.assertIsNotNone(winner_ranking, "Winner ranking should exist")
        self.assertIsNotNone(runner_up_ranking, "Runner-up ranking should exist")
        self.assertIsNotNone(third_ranking, "Third place ranking should exist")
    
    def test_winner_receives_highest_points(self):
        """Test that winner receives more points than runner-up and third place."""
        result = TournamentResult.objects.create(
            tournament=self.tournament,
            winner=self.reg_winner,
            runner_up=self.reg_runner_up,
            third_place=self.reg_third
        )
        
        winner_ranking = TeamGameRanking.objects.get(team=self.team_winner, game=self.game.slug)
        runner_ranking = TeamGameRanking.objects.get(team=self.team_runner_up, game=self.game.slug)
        third_ranking = TeamGameRanking.objects.get(team=self.team_third, game=self.game.slug)
        
        # Winner should have most points
        self.assertGreater(
            winner_ranking.ranking_points,
            runner_ranking.ranking_points,
            "Winner should have more points than runner-up"
        )
        
        self.assertGreater(
            runner_ranking.ranking_points,
            third_ranking.ranking_points,
            "Runner-up should have more points than third place"
        )
    
    def test_multiple_tournaments_accumulate_points(self):
        """Test that teams accumulate points across multiple tournaments."""
        # First tournament
        result1 = TournamentResult.objects.create(
            tournament=self.tournament,
            winner=self.reg_winner,
            runner_up=self.reg_runner_up,
            third_place=self.reg_third
        )
        
        winner_points_after_first = TeamGameRanking.objects.get(
            team=self.team_winner,
            game=self.game.slug
        ).ranking_points
        
        # Second tournament
        tournament2 = Tournament.objects.create(
            name='Test Tournament 2',
            slug='test-tournament-2',
            description='Second test tournament',
            game=self.game,
            organizer=self.user,
            max_participants=16,
            registration_start=now - timedelta(days=7),
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=8)
        )
        
        # Create new registrations for second tournament
        reg2_winner = Registration.objects.create(
            tournament=tournament2,
            team_id=self.team_winner.id,
            status=Registration.CONFIRMED
        )
        
        reg2_third = Registration.objects.create(
            tournament=tournament2,
            team_id=self.team_third.id,
            status=Registration.CONFIRMED
        )
        
        reg2_runner = Registration.objects.create(
            tournament=tournament2,
            team_id=self.team_runner_up.id,
            status=Registration.CONFIRMED
        )
        
        result2 = TournamentResult.objects.create(
            tournament=tournament2,
            winner=reg2_winner,
            runner_up=reg2_third,
            third_place=reg2_runner
        )
        
        winner_points_after_second = TeamGameRanking.objects.get(
            team=self.team_winner,
            game=self.game.slug
        ).ranking_points
        
        # Points should accumulate
        self.assertGreater(
            winner_points_after_second,
            winner_points_after_first,
            "Points should accumulate across tournaments"
        )
    
    def test_ranking_game_matches_tournament_game(self):
        """Test that ranking records are created for the correct game."""
        result = TournamentResult.objects.create(
            tournament=self.tournament,
            winner=self.reg_winner,
            runner_up=self.reg_runner_up,
            third_place=self.reg_third
        )
        
        winner_ranking = TeamGameRanking.objects.get(team=self.team_winner, game=self.game.slug)
        
        self.assertEqual(
            winner_ranking.game,
            self.game.slug,
            "Ranking should be for the tournament's game"
        )


@pytest.mark.django_db
class TestRankingServiceEdgeCases(TransactionTestCase):
    """Test edge cases in ranking point calculation."""
    
    def setUp(self):
        """Create minimal test data."""
        self.game = TournamentGame.objects.create(
            name='Counter-Strike 2',
            slug='cs2',
            default_team_size=5,
            profile_id_field='steam_id',
            is_active=True
        )
        
        self.user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        self.team = Team.objects.create(
            name='Test Team',
            tag='TST',
            game=self.game.slug
        )
    
    def test_ranking_created_for_new_team(self):
        """Test that ranking is auto-created when team participates."""
        # Initially no ranking
        self.assertFalse(
            TeamGameRanking.objects.filter(team=self.team, game=self.game.slug).exists()
        )
        
        # Create tournament and result
        now = timezone.now()
        tournament = Tournament.objects.create(
            name='First Tournament',
            slug='first-tournament',
            description='First test tournament',
            game=self.game,
            organizer=self.user,
            max_participants=8,
            registration_start=now - timedelta(days=7),
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=8)
        )
        
        # Create another team for runner-up
        team2 = Team.objects.create(
            name='Team 2',
            tag='T2',
            game=self.game.slug
        )
        
        # Create registrations
        reg_winner = Registration.objects.create(
            tournament=tournament,
            team_id=self.team.id,
            status=Registration.CONFIRMED
        )
        
        reg_runner = Registration.objects.create(
            tournament=tournament,
            team_id=team2.id,
            status=Registration.CONFIRMED
        )
        
        result = TournamentResult.objects.create(
            tournament=tournament,
            winner=reg_winner,
            runner_up=reg_runner
        )
        
        # Now ranking should exist
        self.assertTrue(
            TeamGameRanking.objects.filter(team=self.team, game=self.game.slug).exists(),
            "Ranking should be created after tournament participation"
        )
