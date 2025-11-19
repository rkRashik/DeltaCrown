"""
Sprint 4: Tournament Leaderboard Tests

Tests for FE-T-010: Tournament Leaderboard Page

Test Coverage:
- Page load and rendering
- Leaderboard calculation and sorting
- Current user highlighting
- Empty state handling
- 404 error handling
- Query optimization
- Mobile responsiveness (template structure)
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Match, Registration, Game
from apps.tournaments.models.bracket import Bracket

User = get_user_model()


class TournamentLeaderboardViewTests(TestCase):
    """Tests for TournamentLeaderboardView (FE-T-010)."""
    
    def setUp(self):
        """Set up test data for leaderboard tests."""
        self.client = Client()
        
        # Create game
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        
        # Create organizer
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='testpass123'
        )
        
        # Create tournament
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.LIVE,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.SOLO,
            max_participants=8,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5),
            is_deleted=False
        )
        
        # Create bracket
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION,
            is_finalized=True
        )
        
        # Create 4 participants (users)
        self.users = []
        for i in range(1, 5):
            user = User.objects.create_user(
                username=f'player{i}',
                email=f'player{i}@test.com',
                password='testpass123'
            )
            self.users.append(user)
        
        # Create registrations
        self.registrations = []
        for user in self.users:
            registration = Registration.objects.create(
                tournament=self.tournament,
                user=user,
                status=Registration.CONFIRMED,
                is_deleted=False
            )
            self.registrations.append(registration)
        
        # Create completed matches with various results
        # Player 1: 3 wins, 0 losses (9 points)
        # Player 2: 2 wins, 1 loss (6 points)
        # Player 3: 1 win, 2 losses (3 points)
        # Player 4: 0 wins, 3 losses (0 points)
        
        # Match 1: Player 1 beats Player 4
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=1,
            match_number=1,
            participant1_id=self.users[0].id,
            participant2_id=self.users[3].id,
            winner_id=self.users[0].id,
            loser_id=self.users[3].id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=0,
            is_deleted=False
        )
        
        # Match 2: Player 2 beats Player 3
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=1,
            match_number=2,
            participant1_id=self.users[1].id,
            participant2_id=self.users[2].id,
            winner_id=self.users[1].id,
            loser_id=self.users[2].id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=1,
            is_deleted=False
        )
        
        # Match 3: Player 1 beats Player 2
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=2,
            match_number=1,
            participant1_id=self.users[0].id,
            participant2_id=self.users[1].id,
            winner_id=self.users[0].id,
            loser_id=self.users[1].id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=0,
            is_deleted=False
        )
        
        # Match 4: Player 1 beats Player 3
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=2,
            match_number=2,
            participant1_id=self.users[0].id,
            participant2_id=self.users[2].id,
            winner_id=self.users[0].id,
            loser_id=self.users[2].id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=1,
            is_deleted=False
        )
        
        # Match 5: Player 2 beats Player 4
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=2,
            match_number=3,
            participant1_id=self.users[1].id,
            participant2_id=self.users[3].id,
            winner_id=self.users[1].id,
            loser_id=self.users[3].id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=0,
            is_deleted=False
        )
        
        # Match 6: Player 3 beats Player 4
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=2,
            match_number=4,
            participant1_id=self.users[2].id,
            participant2_id=self.users[3].id,
            winner_id=self.users[2].id,
            loser_id=self.users[3].id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=1,
            is_deleted=False
        )
    
    def test_leaderboard_page_loads(self):
        """Test that leaderboard page loads successfully."""
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/leaderboard/index.html')
        self.assertContains(response, self.tournament.name)
        self.assertContains(response, 'Leaderboard')
    
    def test_leaderboard_404_missing_tournament(self):
        """Test 404 error for non-existent tournament."""
        url = reverse('tournaments:leaderboard', kwargs={'slug': 'non-existent-tournament'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_leaderboard_displays_standings(self):
        """Test that leaderboard displays all participants with correct stats."""
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check standings are in context
        self.assertIn('standings', response.context)
        standings = response.context['standings']
        
        # Should have 4 participants
        self.assertEqual(len(standings), 4)
        
        # Check each participant appears in response
        for user in self.users:
            self.assertContains(response, user.username)
    
    def test_leaderboard_sorted_by_points(self):
        """Test that leaderboard is sorted correctly (points DESC, wins DESC, games ASC)."""
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        standings = response.context['standings']
        
        # Expected order:
        # 1st: Player 1 (3 wins, 9 points, 3 games)
        # 2nd: Player 2 (2 wins, 6 points, 3 games)
        # 3rd: Player 3 (1 win, 3 points, 3 games)
        # 4th: Player 4 (0 wins, 0 points, 3 games)
        
        self.assertEqual(standings[0]['rank'], 1)
        self.assertEqual(standings[0]['participant'], self.users[0])
        self.assertEqual(standings[0]['wins'], 3)
        self.assertEqual(standings[0]['losses'], 0)
        self.assertEqual(standings[0]['points'], 9)
        self.assertEqual(standings[0]['games_played'], 3)
        
        self.assertEqual(standings[1]['rank'], 2)
        self.assertEqual(standings[1]['participant'], self.users[1])
        self.assertEqual(standings[1]['wins'], 2)
        self.assertEqual(standings[1]['losses'], 1)
        self.assertEqual(standings[1]['points'], 6)
        
        self.assertEqual(standings[2]['rank'], 3)
        self.assertEqual(standings[2]['participant'], self.users[2])
        self.assertEqual(standings[2]['wins'], 1)
        self.assertEqual(standings[2]['losses'], 2)
        self.assertEqual(standings[2]['points'], 3)
        
        self.assertEqual(standings[3]['rank'], 4)
        self.assertEqual(standings[3]['participant'], self.users[3])
        self.assertEqual(standings[3]['wins'], 0)
        self.assertEqual(standings[3]['losses'], 3)
        self.assertEqual(standings[3]['points'], 0)
    
    def test_leaderboard_highlights_current_user(self):
        """Test that current user's row is highlighted if logged in and participating."""
        # Login as player 2
        self.client.login(username='player2', password='testpass123')
        
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        standings = response.context['standings']
        
        # Player 2 should be marked as current user
        player2_standing = next(s for s in standings if s['participant'] == self.users[1])
        self.assertTrue(player2_standing['is_current_user'])
        
        # Other players should not be marked
        player1_standing = next(s for s in standings if s['participant'] == self.users[0])
        self.assertFalse(player1_standing['is_current_user'])
        
        # Check user_rank in context
        self.assertEqual(response.context['user_rank'], 2)
        self.assertIsNotNone(response.context['user_standing'])
        self.assertEqual(response.context['user_standing']['rank'], 2)
    
    def test_leaderboard_no_highlight_for_anonymous(self):
        """Test that no row is highlighted for anonymous users."""
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        standings = response.context['standings']
        
        # No standing should be marked as current user
        for standing in standings:
            self.assertFalse(standing['is_current_user'])
        
        # user_rank should be None
        self.assertIsNone(response.context['user_rank'])
        self.assertIsNone(response.context['user_standing'])
    
    def test_leaderboard_handles_no_matches(self):
        """Test empty state when no matches have been completed."""
        # Create a new tournament with no matches
        new_tournament = Tournament.objects.create(
            name='Empty Tournament',
            slug='empty-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.REGISTRATION_OPEN,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.SOLO,
            max_participants=8,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10),
            tournament_end=timezone.now() + timedelta(days=15),
            is_deleted=False
        )
        
        # Create registrations but no matches
        Registration.objects.create(
            tournament=new_tournament,
            user=self.users[0],
            status=Registration.CONFIRMED,
            is_deleted=False
        )
        
        url = reverse('tournaments:leaderboard', kwargs={'slug': new_tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should use empty state template
        self.assertTemplateUsed(response, 'tournaments/public/leaderboard/_empty_state.html')
        self.assertContains(response, 'No Standings Yet')
        
        # standings should be empty or all participants have 0 games
        standings = response.context['standings']
        if standings:
            for standing in standings:
                self.assertEqual(standing['games_played'], 0)
                self.assertEqual(standing['wins'], 0)
                self.assertEqual(standing['losses'], 0)
                self.assertEqual(standing['points'], 0)
    
    def test_leaderboard_query_optimization(self):
        """Test that leaderboard uses query optimization (select_related)."""
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        
        # Count queries
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        
        # Should have reasonable number of queries:
        # 1. Tournament query with select_related (game, organizer, bracket)
        # 2. Registrations query with select_related (user)
        # 3. Matches EXISTS check
        # 4. Matches list query
        # 5-28. Base template sidebar context (game stats, tournaments, matches, users, etc.)
        # Note: Base template makes ~20-24 queries for sidebar statistics
        # This is acceptable as sidebar is rendered on every page
        # Leaderboard view itself is optimized with select_related and in-memory calculations
        
        query_count = len(queries)
        self.assertLessEqual(query_count, 35, 
            f"Too many queries: {query_count}. Expected ≤35. Queries: {[q['sql'] for q in queries]}")
    
    def test_leaderboard_medal_icons_top3(self):
        """Test that top 3 participants have medal indicators in HTML."""
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        # Check for medal emojis in response (from _leaderboard_row.html)
        self.assertContains(response, '🥇')  # Gold medal for 1st place
        self.assertContains(response, '🥈')  # Silver medal for 2nd place
        self.assertContains(response, '🥉')  # Bronze medal for 3rd place
    
    def test_leaderboard_empty_state(self):
        """Test that empty state is displayed when standings list is truly empty."""
        # Create tournament with NO registrations
        empty_tournament = Tournament.objects.create(
            name='No Participants Tournament',
            slug='no-participants-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.DRAFT,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.SOLO,
            max_participants=8,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10),
            tournament_end=timezone.now() + timedelta(days=15),
            is_deleted=False
        )
        
        url = reverse('tournaments:leaderboard', kwargs={'slug': empty_tournament.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # standings should be empty
        standings = response.context['standings']
        self.assertEqual(len(standings), 0)
        
        # Should show empty state
        self.assertTemplateUsed(response, 'tournaments/public/leaderboard/_empty_state.html')
        self.assertContains(response, 'No Standings Yet')
        self.assertContains(response, 'The leaderboard will be available once matches begin')
    
    def test_leaderboard_handles_tied_participants(self):
        """Test that tied participants are sorted by games played and registration ID."""
        # Create two more users with identical records
        user5 = User.objects.create_user(username='player5', email='player5@test.com', password='testpass123')
        user6 = User.objects.create_user(username='player6', email='player6@test.com', password='testpass123')
        
        reg5 = Registration.objects.create(
            tournament=self.tournament,
            user=user5,
            status=Registration.CONFIRMED,
            is_deleted=False
        )
        reg6 = Registration.objects.create(
            tournament=self.tournament,
            user=user6,
            status=Registration.CONFIRMED,
            is_deleted=False
        )
        
        # Both win 1 match (3 points each)
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=3,
            match_number=1,
            participant1_id=user5.id,
            participant2_id=self.users[3].id,
            winner_id=user5.id,
            loser_id=self.users[3].id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=0,
            is_deleted=False
        )
        
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=3,
            match_number=2,
            participant1_id=user6.id,
            participant2_id=self.users[3].id,
            winner_id=user6.id,
            loser_id=self.users[3].id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=1,
            is_deleted=False
        )
        
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        standings = response.context['standings']
        
        # Find player5 and player6 standings
        player5_standing = next(s for s in standings if s['participant'] == user5)
        player6_standing = next(s for s in standings if s['participant'] == user6)
        
        # Both should have 3 points and 1 win
        self.assertEqual(player5_standing['points'], 3)
        self.assertEqual(player6_standing['points'], 3)
        self.assertEqual(player5_standing['wins'], 1)
        self.assertEqual(player6_standing['wins'], 1)
        
        # Rank should be different (stable sort by registration ID)
        self.assertNotEqual(player5_standing['rank'], player6_standing['rank'])
        
        # Lower registration ID should have better rank
        if reg5.id < reg6.id:
            self.assertLess(player5_standing['rank'], player6_standing['rank'])
        else:
            self.assertLess(player6_standing['rank'], player5_standing['rank'])


class TournamentLeaderboardMobileTests(TestCase):
    """Tests for mobile responsiveness (template structure)."""
    
    def setUp(self):
        """Set up minimal test data."""
        self.game = Game.objects.create(name='Test Game', slug='test-game', is_active=True)
        self.organizer = User.objects.create_user(username='organizer', email='org@test.com', password='testpass123')
        self.tournament = Tournament.objects.create(
            name='Mobile Test Tournament',
            slug='mobile-test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.LIVE,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.SOLO,
            max_participants=8,
            registration_start=timezone.now() - timedelta(days=7),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=timezone.now() - timedelta(days=1),
            tournament_end=timezone.now() + timedelta(days=5),
            is_deleted=False
        )
        
        # Create test data with matches so table is rendered
        self.user1 = User.objects.create_user(username='player1', email='p1@test.com', password='testpass123')
        self.user2 = User.objects.create_user(username='player2', email='p2@test.com', password='testpass123')
        
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION,
            is_finalized=True
        )
        
        Registration.objects.create(
            tournament=self.tournament,
            user=self.user1,
            status=Registration.CONFIRMED,
            is_deleted=False
        )
        Registration.objects.create(
            tournament=self.tournament,
            user=self.user2,
            status=Registration.CONFIRMED,
            is_deleted=False
        )
        
        # Add a match so standings are displayed
        Match.objects.create(
            tournament=self.tournament,
            bracket=self.bracket,
            round_number=1,
            match_number=1,
            participant1_id=self.user1.id,
            participant2_id=self.user2.id,
            winner_id=self.user1.id,
            loser_id=self.user2.id,
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=0,
            is_deleted=False
        )
    
    def test_leaderboard_has_mobile_responsive_classes(self):
        """Test that template includes mobile-responsive CSS classes."""
        url = reverse('tournaments:leaderboard', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        # Check for mobile-responsive elements in template
        self.assertContains(response, 'table-scroll-wrapper')  # Horizontal scroll wrapper
        self.assertContains(response, 'tabindex="0"')  # Keyboard scroll support
        self.assertContains(response, 'role="region"')  # ARIA region for accessibility
        self.assertContains(response, '@media (max-width: 768px)')  # Mobile media query in CSS
