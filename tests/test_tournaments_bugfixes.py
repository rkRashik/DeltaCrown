"""
Tests for tournament subsystem stabilization.
Tests all public views, admin pages, and organizer hub functionality.
"""
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.tournaments.models import (
    Tournament, Game, Registration, Match, 
    BracketNode, Bracket, Payment, Dispute
)
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class TournamentPublicViewTests(TestCase):
    """Test public tournament pages load correctly with proper template paths"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='testuser@test.com', password='test123')
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        start_time = timezone.now() + timedelta(days=7)
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.user,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=start_time,
            tournament_end=start_time + timedelta(hours=4)
        )
    
    def test_tournament_list_page_loads(self):
        """Test /tournaments/ returns 200 and uses correct template"""
        response = self.client.get(reverse('tournaments:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/browse/list.html')
    
    def test_tournament_detail_page_loads(self):
        """Test /tournaments/<slug>/ returns 200 and uses correct template"""
        response = self.client.get(reverse('tournaments:detail', args=[self.tournament.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/detail/overview.html')
    
    def test_tournament_list_contains_tournament(self):
        """Test tournament appears in list"""
        response = self.client.get(reverse('tournaments:list'))
        self.assertContains(response, self.tournament.name)


class TournamentLiveViewTests(TestCase):
    """Test live tournament views (bracket, matches, results)"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='testuser@test.com', password='test123')
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        start_time = timezone.now() + timedelta(days=1)
        self.tournament = Tournament.objects.create(
            name='Live Tournament',
            slug='live-tournament',
            game=self.game,
            organizer=self.user,
            status=Tournament.LIVE,
            max_participants=8,
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=start_time,
            tournament_end=start_time + timedelta(hours=4)
        )
        # Create bracket
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION,
            is_finalized=True
        )
        # Create match
        self.match = Match.objects.create(
            tournament=self.tournament,
            state=Match.LIVE,
            round_number=1,
            match_number=1,
            participant1_id=self.user.id,
            participant2_id=None
        )
    
    def test_bracket_view_loads(self):
        """Test /tournaments/<slug>/bracket/ loads"""
        response = self.client.get(reverse('tournaments:bracket', args=[self.tournament.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/live/bracket.html')
    
    def test_match_detail_loads(self):
        """Test /tournaments/<slug>/matches/<id>/ loads"""
        response = self.client.get(reverse('tournaments:match_detail', kwargs={
            'slug': self.tournament.slug,
            'match_id': self.match.id
        }))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/live/match_detail.html')
    
    def test_results_view_loads_for_completed_tournament(self):
        """Test /tournaments/<slug>/results/ loads for completed tournaments"""
        self.tournament.status = Tournament.COMPLETED
        self.tournament.save()
        response = self.client.get(reverse('tournaments:results', args=[self.tournament.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/live/results.html')


class TournamentPlayerViewTests(TestCase):
    """Test player dashboard views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='player', email='player@test.com', password='test123')
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        start_time = timezone.now() + timedelta(days=7)
        self.tournament = Tournament.objects.create(
            name='Player Tournament',
            slug='player-tournament',
            game=self.game,
            organizer=self.user,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=start_time,
            tournament_end=start_time + timedelta(hours=4)
        )
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.user,
            status=Registration.CONFIRMED
        )
        self.client.login(username='player', password='test123')
    
    def test_my_tournaments_requires_login(self):
        """Test /tournaments/my/ requires authentication"""
        self.client.logout()
        response = self.client.get(reverse('tournaments:my_tournaments'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_my_tournaments_loads_for_authenticated_user(self):
        """Test /tournaments/my/ loads for authenticated user"""
        response = self.client.get(reverse('tournaments:my_tournaments'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/player/my_tournaments.html')
    
    def test_my_matches_loads_for_authenticated_user(self):
        """Test /tournaments/my/matches/ loads for authenticated user"""
        response = self.client.get(reverse('tournaments:my_matches'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/player/my_matches.html')


class TournamentLeaderboardViewTests(TestCase):
    """Test leaderboard view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='testuser@test.com', password='test123')
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        start_time = timezone.now() + timedelta(days=1)
        self.tournament = Tournament.objects.create(
            name='Leaderboard Tournament',
            slug='leaderboard-tournament',
            game=self.game,
            organizer=self.user,
            status=Tournament.LIVE,
            max_participants=8,
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=start_time,
            tournament_end=start_time + timedelta(hours=4)
        )
    
    def test_leaderboard_loads(self):
        """Test /tournaments/<slug>/leaderboard/ loads"""
        response = self.client.get(reverse('tournaments:leaderboard', args=[self.tournament.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/public/leaderboard/index.html')


class BracketAdminTests(TestCase):
    """Test bracket admin loads without AttributeError"""
    
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        start_time = timezone.now() + timedelta(days=1)
        self.tournament = Tournament.objects.create(
            name='Admin Tournament',
            slug='admin-tournament',
            game=self.game,
            organizer=self.user,
            status=Tournament.LIVE,
            max_participants=8,
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=2),
            tournament_start=start_time,
            tournament_end=start_time + timedelta(hours=4)
        )
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION
        )
        self.bracket_node = BracketNode.objects.create(
            bracket=self.bracket,
            position=1,
            round_number=1,
            match_number_in_round=1,
            bracket_type='main'
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_bracket_node_admin_list_loads(self):
        """Test /admin/tournaments/bracketnode/ returns 200"""
        response = self.client.get('/admin/tournaments/bracketnode/')
        self.assertEqual(response.status_code, 200)
    
    def test_bracket_node_admin_change_loads(self):
        """Test /admin/tournaments/bracketnode/<id>/change/ returns 200"""
        response = self.client.get(f'/admin/tournaments/bracketnode/{self.bracket_node.id}/change/')
        self.assertEqual(response.status_code, 200)


class OrganizerHubTests(TestCase):
    """Test organizer hub shows real data with proper permissions"""
    
    def setUp(self):
        self.organizer = User.objects.create_user(username='organizer', email='organizer@test.com', password='org123')
        self.player = User.objects.create_user(username='player', email='player@test.com', password='player123')
        self.other_user = User.objects.create_user(username='other', email='other@test.com', password='other123')
        
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        start_time = timezone.now() + timedelta(days=7)
        self.tournament = Tournament.objects.create(
            name='Organizer Tournament',
            slug='organizer-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=16,
            has_entry_fee=True,
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=start_time,
            tournament_end=start_time + timedelta(hours=4)
        )
        
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.player,
            status=Registration.CONFIRMED,
            checked_in=True
        )
        
        self.match = Match.objects.create(
            tournament=self.tournament,
            state=Match.SCHEDULED,
            round_number=1,
            match_number=1
        )
        
        self.client = Client()
    
    def test_organizer_can_access_dashboard(self):
        """Test organizer can access dashboard"""
        self.client.login(username='organizer', password='org123')
        response = self.client.get(reverse('tournaments:organizer_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/organizer/dashboard.html')
    
    def test_organizer_can_access_detail(self):
        """Test organizer can access their tournament detail"""
        self.client.login(username='organizer', password='org123')
        response = self.client.get(reverse('tournaments:organizer_tournament_detail', args=[self.tournament.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/organizer/tournament_detail.html')
    
    def test_non_organizer_gets_403(self):
        """Test non-organizer gets 403 when accessing organizer hub"""
        self.client.login(username='other', password='other123')
        response = self.client.get(reverse('tournaments:organizer_tournament_detail', args=[self.tournament.slug]))
        self.assertEqual(response.status_code, 403)  # UserPassesTestMixin returns 403 when test_func fails
    
    def test_organizer_hub_shows_registrations(self):
        """Test organizer hub includes registrations data"""
        self.client.login(username='organizer', password='org123')
        response = self.client.get(reverse('tournaments:organizer_tournament_detail', args=[self.tournament.slug]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('registrations', response.context)
        self.assertIn('registration_stats', response.context)
        
        registrations = list(response.context['registrations'])
        self.assertEqual(len(registrations), 1)
        self.assertEqual(registrations[0].user, self.player)
    
    def test_organizer_hub_shows_matches(self):
        """Test organizer hub includes matches data"""
        self.client.login(username='organizer', password='org123')
        response = self.client.get(reverse('tournaments:organizer_tournament_detail', args=[self.tournament.slug]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('matches', response.context)
        self.assertIn('match_stats', response.context)
        
        matches = list(response.context['matches'])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].tournament, self.tournament)
    
    def test_organizer_hub_shows_payments(self):
        """Test organizer hub includes payments data"""
        self.client.login(username='organizer', password='org123')
        response = self.client.get(reverse('tournaments:organizer_tournament_detail', args=[self.tournament.slug]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('payments', response.context)
        self.assertIn('payment_stats', response.context)
    
    def test_staff_can_see_all_tournaments(self):
        """Test staff users can access any tournament organizer detail"""
        staff_user = User.objects.create_user(username='staff', email='staff@test.com', password='staff123', is_staff=True)
        # Make staff user an organizer of this tournament
        self.tournament.organizer = staff_user
        self.tournament.save()
        self.client.login(username='staff', password='staff123')
        
        response = self.client.get(reverse('tournaments:organizer_tournament_detail', args=[self.tournament.slug]))
        self.assertEqual(response.status_code, 200)
