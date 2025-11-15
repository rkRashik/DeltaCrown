"""
Sprint 3: Public Live Tournament Experience - Test Suite

Tests for FE-T-008 (Bracket View), FE-T-009 (Match Detail), FE-T-018 (Results)

Test Coverage:
- Bracket view functionality and edge cases
- Match detail view functionality and edge cases
- Results view functionality and edge cases
- Query optimizations
- URL validation
- Permission checks
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Match, Registration, Game
from apps.tournaments.models.bracket import Bracket
from apps.tournaments.models.result import TournamentResult

User = get_user_model()


class TournamentBracketViewTests(TestCase):
    """Tests for FE-T-008: Live Bracket View"""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create organizer
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@example.com',
            password='orgpass123'
        )
        
        # Create game
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
        )
        
        # Create live tournament with bracket
        self.tournament = Tournament.objects.create(
            name='Live Tournament',
            slug='live-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.LIVE,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5)
        )
        
        # Create bracket
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION,
            seeding_method=Bracket.RANKED,
            is_finalized=True,
            bracket_structure={
                'format': 'single-elimination',
                'total_participants': 4,
                'rounds': [
                    {'round_number': 1, 'round_name': 'Semi Finals', 'matches': 2},
                    {'round_number': 2, 'round_name': 'Finals', 'matches': 1}
                ]
            }
        )
        
        # Create matches
        self.match1 = Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=1,
            participant1_id=1,
            participant2_id=2,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=1,
            winner_id=1,
            loser_id=2,
            scheduled_time=timezone.now() - timedelta(hours=2)
        )
        
        self.match2 = Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=2,
            participant1_id=3,
            participant2_id=4,
            state=Match.LIVE,
            participant1_score=1,
            participant2_score=1,
            scheduled_time=timezone.now()
        )

    def test_bracket_page_loads_for_live_tournament(self):
        """Test that bracket page loads successfully for live tournament."""
        url = reverse('tournaments:bracket', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/live/bracket.html')
        self.assertEqual(response.context['tournament'], self.tournament)
        self.assertTrue(response.context['bracket_available'])
        self.assertIn('matches_by_round', response.context)

    def test_bracket_view_organizes_matches_by_round(self):
        """Test that matches are properly organized by round."""
        url = reverse('tournaments:bracket', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        matches_by_round = response.context['matches_by_round']
        self.assertEqual(len(matches_by_round), 1)  # Only round 1 has matches
        self.assertEqual(matches_by_round[0]['round_number'], 1)
        self.assertEqual(len(matches_by_round[0]['matches']), 2)
        self.assertEqual(matches_by_round[0]['round_name'], 'Semi Finals')

    def test_bracket_page_shows_not_ready_for_early_tournament(self):
        """Test that bracket shows 'not ready' for tournaments in registration phase."""
        # Create tournament in registration phase
        early_tournament = Tournament.objects.create(
            name='Early Tournament',
            slug='early-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=2),
            registration_end=timezone.now() + timedelta(days=3),
            tournament_start=timezone.now() + timedelta(days=5),
            tournament_end=timezone.now() + timedelta(days=10)
        )
        
        url = reverse('tournaments:bracket', kwargs={'slug': early_tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['bracket_available'])
        self.assertIn('not_ready_reason', response.context)
        self.assertIn('still accepting registrations', response.context['not_ready_reason'])

    def test_bracket_view_404_for_invalid_slug(self):
        """Test that invalid tournament slug returns 404."""
        url = reverse('tournaments:bracket', kwargs={'slug': 'nonexistent'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_bracket_view_shows_cancelled_state(self):
        """Test that cancelled tournament shows appropriate message."""
        cancelled_tournament = Tournament.objects.create(
            name='Cancelled Tournament',
            slug='cancelled-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.CANCELLED,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5)
        )
        
        url = reverse('tournaments:bracket', kwargs={'slug': cancelled_tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['bracket_available'])
        self.assertIn('cancelled', response.context['not_ready_reason'].lower())


class MatchDetailViewTests(TestCase):
    """Tests for FE-T-009: Match Watch / Match Detail Page"""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test users
        self.participant1 = User.objects.create_user(
            username='participant1',
            email='p1@example.com',
            password='pass123'
        )
        
        self.participant2 = User.objects.create_user(
            username='participant2',
            email='p2@example.com',
            password='pass123'
        )
        
        self.spectator = User.objects.create_user(
            username='spectator',
            email='spectator@example.com',
            password='pass123'
        )
        
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@example.com',
            password='orgpass123'
        )
        
        # Create game
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
        )
        
        # Create tournament
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.LIVE,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5)
        )
        
        # Create match
        self.match = Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=1,
            participant1_id=self.participant1.id,
            participant2_id=self.participant2.id,
            state=Match.LIVE,
            participant1_score=1,
            participant2_score=1,
            scheduled_time=timezone.now(),
            lobby_info='Lobby Code: ABC123'
        )

    def test_match_detail_page_loads(self):
        """Test that match detail page loads successfully."""
        url = reverse('tournaments:match_detail', kwargs={
            'slug': self.tournament.slug,
            'match_id': self.match.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/live/match_detail.html')
        self.assertEqual(response.context['match'], self.match)
        self.assertEqual(response.context['tournament'], self.tournament)

    def test_match_detail_404_for_invalid_match_id(self):
        """Test that invalid match ID returns 404."""
        url = reverse('tournaments:match_detail', kwargs={
            'slug': self.tournament.slug,
            'match_id': 99999
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_match_detail_validates_tournament_slug(self):
        """Test that match detail validates tournament slug matches."""
        # Create another tournament
        other_tournament = Tournament.objects.create(
            name='Other Tournament',
            slug='other-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.LIVE,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5)
        )
        
        # Try to access match with wrong tournament slug
        url = reverse('tournaments:match_detail', kwargs={
            'slug': other_tournament.slug,
            'match_id': self.match.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_match_detail_shows_lobby_info_to_participants_only(self):
        """Test that lobby info is only visible to match participants."""
        url = reverse('tournaments:match_detail', kwargs={
            'slug': self.tournament.slug,
            'match_id': self.match.id
        })
        
        # Test as participant1
        self.client.login(username='participant1', password='pass123')
        response = self.client.get(url)
        self.assertTrue(response.context['is_participant'])
        self.assertTrue(response.context['show_lobby_info'])
        
        # Test as spectator
        self.client.logout()
        self.client.login(username='spectator', password='pass123')
        response = self.client.get(url)
        self.assertFalse(response.context['is_participant'])
        self.assertFalse(response.context['show_lobby_info'])
        
        # Test as anonymous user
        self.client.logout()
        response = self.client.get(url)
        self.assertFalse(response.context['is_participant'])
        self.assertFalse(response.context['show_lobby_info'])

    def test_match_detail_handles_bye_match(self):
        """Test that match detail handles bye matches (one participant null)."""
        bye_match = Match.objects.create(
            tournament=self.tournament,
            round_number=2,
            match_number=1,
            participant1_id=self.participant1.id,
            participant2_id=None,  # Bye
            state=Match.SCHEDULED,
            scheduled_time=timezone.now() + timedelta(hours=2)
        )
        
        url = reverse('tournaments:match_detail', kwargs={
            'slug': self.tournament.slug,
            'match_id': bye_match.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['participant1'])
        self.assertIsNone(response.context['participant2'])

    def test_match_detail_timeline_generation(self):
        """Test that match timeline is generated correctly."""
        url = reverse('tournaments:match_detail', kwargs={
            'slug': self.tournament.slug,
            'match_id': self.match.id
        })
        response = self.client.get(url)
        
        self.assertIn('timeline', response.context)
        timeline = response.context['timeline']
        self.assertIsInstance(timeline, list)
        self.assertGreater(len(timeline), 0)


class TournamentResultsViewTests(TestCase):
    """Tests for FE-T-018: Tournament Results Page"""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test users
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@example.com',
            password='orgpass123'
        )
        
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='pass123'
        )
        
        # Create game
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
        )
        
        # Create completed tournament
        self.tournament = Tournament.objects.create(
            name='Completed Tournament',
            slug='completed-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.COMPLETED,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=14),
            registration_end=timezone.now() - timedelta(days=9),
            tournament_start=timezone.now() - timedelta(days=8),
            tournament_end=timezone.now() - timedelta(days=1)
        )
        
        # Create registrations
        self.reg1 = Registration.objects.create(
            tournament=self.tournament,
            user=self.user1,
            status=Registration.CONFIRMED,
            seed=1
        )
        
        self.reg2 = Registration.objects.create(
            tournament=self.tournament,
            user=self.user2,
            status=Registration.CONFIRMED,
            seed=2
        )
        
        self.reg3 = Registration.objects.create(
            tournament=self.tournament,
            user=self.user3,
            status=Registration.CONFIRMED,
            seed=3
        )
        
        # Create tournament result
        self.result = TournamentResult.objects.create(
            tournament=self.tournament,
            winner=self.reg1,
            runner_up=self.reg2,
            third_place=self.reg3,
            determination_method='normal',
            rules_applied={'determination': 'bracket_resolution', 'steps': ['final_match_winner']}
        )
        
        # Create completed matches
        self.match1 = Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=1,
            participant1_id=self.user1.id,
            participant2_id=self.user3.id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=0,
            winner_id=self.user1.id,
            loser_id=self.user3.id,
            scheduled_time=timezone.now() - timedelta(days=2)
        )

    def test_results_page_loads_for_completed_tournament(self):
        """Test that results page loads for completed tournament."""
        url = reverse('tournaments:results', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/live/results.html')
        self.assertEqual(response.context['tournament'], self.tournament)
        self.assertTrue(response.context['has_results'])

    def test_results_page_redirects_for_live_tournament(self):
        """Test that results page returns 404 for live tournament."""
        live_tournament = Tournament.objects.create(
            name='Live Tournament',
            slug='live-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.LIVE,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5)
        )
        
        url = reverse('tournaments:results', kwargs={'slug': live_tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_results_page_shows_winner_podium(self):
        """Test that results page displays winner podium."""
        url = reverse('tournaments:results', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.context['winner'], self.reg1)
        self.assertEqual(response.context['runner_up'], self.reg2)
        self.assertEqual(response.context['third_place'], self.reg3)
        self.assertIn('result', response.context)

    def test_results_page_shows_final_leaderboard(self):
        """Test that results page displays final leaderboard."""
        url = reverse('tournaments:results', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        leaderboard = response.context['leaderboard']
        self.assertEqual(leaderboard.count(), 3)
        # Check that registrations are present
        self.assertIn(self.reg1, leaderboard)
        self.assertIn(self.reg2, leaderboard)
        self.assertIn(self.reg3, leaderboard)

    def test_results_page_shows_tournament_stats(self):
        """Test that tournament stats are calculated correctly."""
        url = reverse('tournaments:results', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        stats = response.context['stats']
        self.assertEqual(stats['total_participants'], 3)
        self.assertEqual(stats['total_matches'], 1)
        self.assertEqual(stats['completed_matches'], 1)
        self.assertIn('duration_days', stats)


class QueryOptimizationTests(TestCase):
    """Tests for query optimization using select_related and prefetch_related"""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test data
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@example.com',
            password='orgpass123'
        )
        
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.LIVE,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5)
        )
        
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION,
            seeding_method=Bracket.RANKED,
            is_finalized=True
        )
        
        for i in range(3):
            Match.objects.create(
                tournament=self.tournament,
                round_number=1,
                match_number=i + 1,
                participant1_id=i * 2 + 1,
                participant2_id=i * 2 + 2,
                state=Match.SCHEDULED,
                scheduled_time=timezone.now() + timedelta(hours=i)
            )

    def test_bracket_view_uses_prefetch_related(self):
        """Test that bracket view uses prefetch_related for matches."""
        url = reverse('tournaments:bracket', kwargs={'slug': self.tournament.slug})
        
        # Use assertNumQueries to verify query optimization
        # Note: Includes ~6 queries from sidebar context processor
        with self.assertNumQueries(8):  # Tournament+bracket+matches+sidebar queries
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_match_detail_uses_select_related(self):
        """Test that match detail view uses select_related."""
        match = self.tournament.matches.first()
        url = reverse('tournaments:match_detail', kwargs={
            'slug': self.tournament.slug,
            'match_id': match.id
        })
        
        # Query count should be minimal due to select_related
        # Note: Includes ~6 queries from sidebar context processor
        with self.assertNumQueries(9):  # Match with tournament/game + participant lookups + sidebar
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)


class URLValidationTests(TestCase):
    """Tests for URL pattern validation"""

    def setUp(self):
        """Set up test data."""
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@example.com',
            password='orgpass123'
        )
        
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.LIVE,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5)
        )

    def test_bracket_url_resolves_correctly(self):
        """Test that bracket URL resolves to correct view."""
        url = reverse('tournaments:bracket', kwargs={'slug': 'test-tournament'})
        self.assertEqual(url, '/tournaments/test-tournament/bracket/')

    def test_match_detail_url_resolves_correctly(self):
        """Test that match detail URL resolves to correct view."""
        url = reverse('tournaments:match_detail', kwargs={
            'slug': 'test-tournament',
            'match_id': 123
        })
        self.assertEqual(url, '/tournaments/test-tournament/matches/123/')

    def test_results_url_resolves_correctly(self):
        """Test that results URL resolves to correct view."""
        url = reverse('tournaments:results', kwargs={'slug': 'test-tournament'})
        self.assertEqual(url, '/tournaments/test-tournament/results/')
