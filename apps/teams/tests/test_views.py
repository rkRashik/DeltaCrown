"""
Tests for team views (list, profile, create)
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership

User = get_user_model()


class TeamPublicViewsTest(TestCase):
    """Test public team pages"""
    
    def setUp(self):
        self.client = Client()
        
        # Create captain user
        self.captain = User.objects.create_user(
            username="captain",
            email="captain@test.com",
            password="password123"
        )
        
        # Create team
        self.team = Team.objects.create(
            name="Test Team",
            tag="TT",
            slug="test-team",
            game="pubg",
            region="bd_dhaka",
            captain=self.captain,
            is_active=True,
            is_public=True
        )
    
    def test_team_list_page_loads(self):
        """Test that team list page loads successfully"""
        url = reverse('teams:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Team")
    
    def test_team_profile_page_loads(self):
        """Test that team profile page loads successfully"""
        url = reverse('teams:detail', kwargs={'slug': self.team.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team.name)
        self.assertContains(response, self.team.tag)
    
    def test_nonexistent_team_returns_404(self):
        """Test that accessing non-existent team returns 404"""
        url = reverse('teams:detail', kwargs={'slug': 'nonexistent'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class TeamCreateViewTest(TestCase):
    """Test team creation flow"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="password123"
        )
    
    def test_create_page_requires_login(self):
        """Test that team create page requires authentication"""
        url = reverse('teams:create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_create_page_loads_for_authenticated_user(self):
        """Test that authenticated users can access create page"""
        self.client.login(username="testuser", password="password123")
        url = reverse('teams:create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Your Team")
    
    def test_team_creation_with_valid_data(self):
        """Test creating a team with valid data"""
        self.client.login(username="testuser", password="password123")
        url = reverse('teams:create')
        
        data = {
            'name': 'New Team',
            'tag': 'NT',
            'game': 'pubg',
            'region': 'bd_dhaka',
            'description': 'Test description'
        }
        
        response = self.client.post(url, data)
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Team should be created
        team = Team.objects.filter(name='New Team').first()
        self.assertIsNotNone(team)
        self.assertEqual(team.captain, self.user)


class TeamListFilteringTest(TestCase):
    """Test team list filtering and search"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="captain", password="pass")
        
        # Create multiple teams
        for i in range(5):
            Team.objects.create(
                name=f"Team {i}",
                tag=f"T{i}",
                slug=f"team-{i}",
                game="pubg" if i < 3 else "codm",
                region="bd_dhaka",
                captain=self.user,
                is_active=True,
                is_public=True
            )
    
    def test_game_filter_works(self):
        """Test filtering teams by game"""
        url = reverse('teams:list') + '?game=pubg'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team 0")
        self.assertContains(response, "Team 1")
    
    def test_search_works(self):
        """Test searching for teams"""
        url = reverse('teams:list') + '?search=Team+1'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team 1")
