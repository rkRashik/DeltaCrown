"""
Tests to verify Django admin interfaces don't crash
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament, Game, Bracket, BracketNode, TournamentPaymentMethod
from apps.teams.models import Team
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class TournamentAdminStabilityTest(TestCase):
    """Test that tournament admin pages load without crashing"""
    
    def setUp(self):
        self.client = Client()
        
        # Create superuser
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123"
        )
        self.client.login(username="admin", password="admin123")
        
        # Create test data
        self.game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        
        self.organizer = User.objects.create_user(
            username="organizer",
            password="pass123"
        )
        
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            slug="test-tournament",
            game=self.game,
            organizer=self.organizer,
            status=Tournament.REGISTRATION_OPEN,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10),
            max_participants=16
        )
    
    def test_tournament_admin_list_loads(self):
        """Test that tournament admin list page loads"""
        url = reverse('admin:tournaments_tournament_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_tournament_admin_detail_loads(self):
        """Test that tournament admin detail page loads"""
        url = reverse('admin:tournaments_tournament_change', args=[self.tournament.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_game_admin_list_loads(self):
        """Test that game admin list page loads"""
        url = reverse('admin:tournaments_game_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_game_admin_detail_loads(self):
        """Test that game admin detail page loads"""
        url = reverse('admin:tournaments_game_change', args=[self.game.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)


class BracketAdminStabilityTest(TestCase):
    """Test that bracket admin doesn't crash"""
    
    def setUp(self):
        self.client = Client()
        
        # Create superuser
        self.admin = User.objects.create_superuser(
            username="admin",
            password="admin123"
        )
        self.client.login(username="admin", password="admin123")
        
        # Create test data
        self.game = Game.objects.create(name="Test Game", slug="test-game", is_active=True)
        self.organizer = User.objects.create_user(username="org", password="pass")
        
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            slug="test-tournament",
            game=self.game,
            organizer=self.organizer,
            status=Tournament.REGISTRATION_OPEN,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10),
            max_participants=16
        )
        
        self.bracket = Bracket.objects.create(
            tournament=self.tournament,
            format='single-elimination',
            total_rounds=3,
            total_matches=7
        )
        
        # Create bracket node
        self.node = BracketNode.objects.create(
            bracket=self.bracket,
            position=1,
            round_number=1,
            match_number_in_round=1,
            bracket_type='main',
            participant1_name="Player 1",
            participant2_name="Player 2"
        )
    
    def test_bracket_admin_list_loads(self):
        """Test that bracket admin list loads"""
        url = reverse('admin:tournaments_bracket_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_bracket_admin_detail_loads(self):
        """Test that bracket admin detail loads"""
        url = reverse('admin:tournaments_bracket_change', args=[self.bracket.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_bracketnode_admin_list_loads(self):
        """Test that bracket node admin list loads"""
        url = reverse('admin:tournaments_bracketnode_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_bracketnode_admin_detail_loads(self):
        """Test that bracket node detail loads without AttributeError"""
        url = reverse('admin:tournaments_bracketnode_change', args=[self.node.id])
        response = self.client.get(url)
        
        # This was crashing before with AttributeError
        self.assertEqual(response.status_code, 200)


class TeamAdminStabilityTest(TestCase):
    """Test that team admin doesn't crash"""
    
    def setUp(self):
        self.client = Client()
        
        self.admin = User.objects.create_superuser(
            username="admin",
            password="admin123"
        )
        self.client.login(username="admin", password="admin123")
        
        self.captain = User.objects.create_user(
            username="captain",
            password="pass123"
        )
        
        self.team = Team.objects.create(
            name="Test Team",
            tag="TT",
            slug="test-team",
            game="pubg",
            region="bd_dhaka",
            captain=self.captain,
            is_active=True
        )
    
    def test_team_admin_list_loads(self):
        """Test that team admin list loads"""
        url = reverse('admin:teams_team_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_team_admin_detail_loads(self):
        """Test that team admin detail loads"""
        url = reverse('admin:teams_team_change', args=[self.team.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
