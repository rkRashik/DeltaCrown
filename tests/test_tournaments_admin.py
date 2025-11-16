"""
Comprehensive admin interface tests for tournaments subsystem.
Tests all admin pages to catch errors like queryset slicing, missing fields, etc.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from apps.tournaments.models import (
    Tournament, Game, Registration, Match, Bracket, BracketNode, 
    Payment, Dispute, CustomField
)

User = get_user_model()


class TournamentAdminTests(TestCase):
    """Test Tournament admin interface"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='org123'
        )
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.PUBLISHED,
            format=Tournament.SINGLE_ELIM,
            min_participants=2,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10)
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_tournament_list_loads(self):
        """Test /admin/tournaments/tournament/ loads"""
        response = self.client.get(reverse('admin:tournaments_tournament_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_tournament_add_loads(self):
        """Test /admin/tournaments/tournament/add/ loads"""
        response = self.client.get(reverse('admin:tournaments_tournament_add'))
        self.assertEqual(response.status_code, 200)
    
    def test_tournament_change_loads(self):
        """Test /admin/tournaments/tournament/<id>/change/ loads"""
        response = self.client.get(
            reverse('admin:tournaments_tournament_change', args=[self.tournament.id])
        )
        self.assertEqual(response.status_code, 200)


class GameAdminTests(TestCase):
    """Test Game admin interface"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_game_list_loads(self):
        """Test /admin/tournaments/game/ loads"""
        response = self.client.get(reverse('admin:tournaments_game_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_game_change_loads(self):
        """Test /admin/tournaments/game/<id>/change/ loads"""
        response = self.client.get(
            reverse('admin:tournaments_game_change', args=[self.game.id])
        )
        self.assertEqual(response.status_code, 200)


class RegistrationAdminTests(TestCase):
    """Test Registration admin interface"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='org123'
        )
        self.player = User.objects.create_user(
            username='player',
            email='player@test.com',
            password='player123'
        )
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.PUBLISHED,
            format=Tournament.SINGLE_ELIM,
            min_participants=2,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10)
        )
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.player,
            status=Registration.CONFIRMED
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_registration_list_loads(self):
        """Test /admin/tournaments/registration/ loads"""
        response = self.client.get(reverse('admin:tournaments_registration_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_registration_change_loads(self):
        """Test /admin/tournaments/registration/<id>/change/ loads"""
        response = self.client.get(
            reverse('admin:tournaments_registration_change', args=[self.registration.id])
        )
        self.assertEqual(response.status_code, 200)


class BracketAdminTests(TestCase):
    """Test Bracket admin interface - the one with queryset slice error"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='org123'
        )
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.PUBLISHED,
            format=Tournament.SINGLE_ELIM,
            min_participants=2,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10)
        )
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION,
            is_finalized=False
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_bracket_list_loads(self):
        """Test /admin/tournaments/bracket/ loads"""
        response = self.client.get(reverse('admin:tournaments_bracket_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_bracket_change_loads(self):
        """Test /admin/tournaments/bracket/<id>/change/ loads - THIS WAS FAILING"""
        response = self.client.get(
            reverse('admin:tournaments_bracket_change', args=[self.bracket.id])
        )
        self.assertEqual(response.status_code, 200)


class BracketNodeAdminTests(TestCase):
    """Test BracketNode admin interface"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='org123'
        )
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.PUBLISHED,
            format=Tournament.SINGLE_ELIM,
            min_participants=2,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10)
        )
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format=Bracket.SINGLE_ELIMINATION,
            is_finalized=False
        )
        self.node = BracketNode.objects.create(
            bracket=self.bracket,
            round_number=1,
            match_number_in_round=1,
            position=0,
            bracket_type='winner'
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_bracketnode_list_loads(self):
        """Test /admin/tournaments/bracketnode/ loads"""
        response = self.client.get(reverse('admin:tournaments_bracketnode_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_bracketnode_change_loads(self):
        """Test /admin/tournaments/bracketnode/<id>/change/ loads"""
        response = self.client.get(
            reverse('admin:tournaments_bracketnode_change', args=[self.node.id])
        )
        self.assertEqual(response.status_code, 200)


class MatchAdminTests(TestCase):
    """Test Match admin interface"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='org123'
        )
        self.player1 = User.objects.create_user(
            username='player1',
            email='player1@test.com',
            password='player123'
        )
        self.player2 = User.objects.create_user(
            username='player2',
            email='player2@test.com',
            password='player123'
        )
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.PUBLISHED,
            format=Tournament.SINGLE_ELIM,
            min_participants=2,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10)
        )
        self.reg1 = Registration.objects.create(
            tournament=self.tournament,
            user=self.player1,
            status=Registration.CONFIRMED
        )
        self.reg2 = Registration.objects.create(
            tournament=self.tournament,
            user=self.player2,
            status=Registration.CONFIRMED
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=1,
            participant1_id=self.reg1.id,
            participant2_id=self.reg2.id,
            state=Match.SCHEDULED
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_match_list_loads(self):
        """Test /admin/tournaments/match/ loads"""
        response = self.client.get(reverse('admin:tournaments_match_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_match_change_loads(self):
        """Test /admin/tournaments/match/<id>/change/ loads"""
        response = self.client.get(
            reverse('admin:tournaments_match_change', args=[self.match.id])
        )
        self.assertEqual(response.status_code, 200)


class PaymentAdminTests(TestCase):
    """Test Payment admin interface"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='org123'
        )
        self.player = User.objects.create_user(
            username='player',
            email='player@test.com',
            password='player123'
        )
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.PUBLISHED,
            format=Tournament.SINGLE_ELIM,
            min_participants=2,
            max_participants=16,
            has_entry_fee=True,
            entry_fee_amount=100.00,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10)
        )
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.player,
            status=Registration.CONFIRMED
        )
        self.payment = Payment.objects.create(
            registration=self.registration,
            payment_method=Payment.BKASH,
            amount=100.00,
            status=Payment.SUBMITTED
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_payment_list_loads(self):
        """Test /admin/tournaments/payment/ loads"""
        response = self.client.get(reverse('admin:tournaments_payment_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_payment_change_loads(self):
        """Test /admin/tournaments/payment/<id>/change/ loads"""
        response = self.client.get(
            reverse('admin:tournaments_payment_change', args=[self.payment.id])
        )
        self.assertEqual(response.status_code, 200)


class DisputeAdminTests(TestCase):
    """Test Dispute admin interface"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='org123'
        )
        self.player1 = User.objects.create_user(
            username='player1',
            email='player1@test.com',
            password='player123'
        )
        self.player2 = User.objects.create_user(
            username='player2',
            email='player2@test.com',
            password='player123'
        )
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game=self.game,
            organizer=self.organizer,
            status=Tournament.PUBLISHED,
            format=Tournament.SINGLE_ELIM,
            min_participants=2,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10)
        )
        self.reg1 = Registration.objects.create(
            tournament=self.tournament,
            user=self.player1,
            status=Registration.CONFIRMED
        )
        self.reg2 = Registration.objects.create(
            tournament=self.tournament,
            user=self.player2,
            status=Registration.CONFIRMED
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=1,
            participant1_id=self.reg1.id,
            participant2_id=self.reg2.id,
            state=Match.COMPLETED,
            winner_id=self.reg1.id,
            loser_id=self.reg2.id,
            participant1_score=2,
            participant2_score=1
        )
        self.dispute = Dispute.objects.create(
            match=self.match,
            initiated_by_id=self.player1.id,
            reason=Dispute.SCORE_MISMATCH,
            description='Score is wrong',
            status=Dispute.OPEN
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_dispute_list_loads(self):
        """Test /admin/tournaments/dispute/ loads"""
        response = self.client.get(reverse('admin:tournaments_dispute_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_dispute_change_loads(self):
        """Test /admin/tournaments/dispute/<id>/change/ loads"""
        response = self.client.get(
            reverse('admin:tournaments_dispute_change', args=[self.dispute.id])
        )
        self.assertEqual(response.status_code, 200)
