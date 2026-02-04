"""
Phase 11 End-to-End Regression Tests
Tests team creation, org creation, hub display, admin stability
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.organizations.models import (
    Team, 
    TeamMembership, 
    Organization, 
    OrganizationMembership
)
from apps.games.models import Game

User = get_user_model()


@pytest.mark.django_db
class TestTeamCreationRegression(TestCase):
    """Regression tests for Phase 11 team creation bug fix"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testcreator',
            email='creator@test.com',
            password='testpass123'
        )
        self.client.login(username='testcreator', password='testpass123')
        
        # Ensure at least one game exists
        self.game = Game.objects.first()
        if not self.game:
            self.game = Game.objects.create(
                name='Valorant',
                short_name='VAL',
                slug='valorant',
                status='ACTIVE',
                display_name='VALORANT'
            )
    
    def test_independent_team_creation_uses_created_by_field(self):
        """
        BLOCKER FIX: Verify team creation uses created_by, not owner
        Bug: API was using team_data['owner'] but Team model has 'created_by' field
        """
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Phoenix Rising',
            'tag': 'PHX',
            'game_id': self.game.id,
            'region': 'NA',
            'visibility': 'PUBLIC',
        })
        
        # Should return 201 Created (not 500 TypeError)
        self.assertEqual(response.status_code, 201, 
                        f"Expected 201, got {response.status_code}: {response.content.decode()}")
        
        data = response.json()
        self.assertTrue(data.get('ok'), f"Response should have ok=true: {data}")
        self.assertIn('team_slug', data)
        self.assertIn('team_url', data)
        
        # Verify team exists in database with correct field
        team = Team.objects.get(slug=data['team_slug'])
        self.assertEqual(team.name, 'Phoenix Rising')
        self.assertEqual(team.created_by, self.user)
        self.assertIsNone(team.organization)
        self.assertEqual(team.status, 'ACTIVE')
        
        # Verify OWNER membership created automatically
        owner_membership = TeamMembership.objects.filter(
            team=team,
            user=self.user,
            role='OWNER',
            status='ACTIVE'
        ).first()
        self.assertIsNotNone(owner_membership, "OWNER membership should be auto-created")
    
    def test_org_owned_team_creation(self):
        """
        Verify org-owned team creation sets organization FK correctly
        """
        # Create organization first
        org = Organization.objects.create(
            name='Test Esports',
            slug='test-esports',
            ceo=self.user
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=self.user,
            role='CEO',
            status='ACTIVE'
        )
        
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test Academy',
            'tag': 'TST',
            'game_id': self.game.id,
            'region': 'NA',
            'organization_id': org.id,
            'visibility': 'PUBLIC',
        })
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        # Verify team has organization set
        team = Team.objects.get(slug=data['team_slug'])
        self.assertEqual(team.organization, org)
        self.assertEqual(team.created_by, self.user)
    
    def test_team_appears_in_vnext_hub(self):
        """
        Verify created team appears in /teams/vnext/ list
        """
        # Create team
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Visibility Test',
            'tag': 'VIS',
            'game_id': self.game.id,
            'region': 'SEA',
            'visibility': 'PUBLIC',
        })
        
        self.assertEqual(response.status_code, 201)
        
        # Check hub page loads
        list_response = self.client.get('/teams/vnext/')
        self.assertEqual(list_response.status_code, 200)
        
        # Team should be visible in response
        content = list_response.content.decode()
        self.assertIn('Visibility Test', content, 
                     "Created team should appear in vNext hub")
    
    def test_team_detail_page_accessible(self):
        """
        Verify team detail page loads after creation
        """
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Detail Test',
            'tag': 'DTL',
            'game_id': self.game.id,
            'region': 'EU',
            'visibility': 'PUBLIC',
        })
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        team_url = data['team_url']
        
        # Access team detail page
        detail_response = self.client.get(team_url)
        self.assertIn(detail_response.status_code, [200, 302], 
                     "Team detail should be accessible")
    
    def test_independent_team_has_no_organization(self):
        """
        Verify independent team correctly has organization=None
        """
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Independent Squad',
            'tag': 'IND',
            'game_id': self.game.id,
            'region': 'NA',
            'visibility': 'PUBLIC',
        })
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        team = Team.objects.get(slug=data['team_slug'])
        self.assertIsNone(team.organization, 
                         "Independent team should have organization=None")
        self.assertIsNotNone(team.created_by,
                           "Independent team should have created_by set")


@pytest.mark.django_db
class TestOrganizationCreation(TestCase):
    """End-to-end tests for organization creation"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='orgfounder',
            email='founder@test.com',
            password='testpass123'
        )
        self.client.login(username='orgfounder', password='testpass123')
    
    def test_organization_creation_response_format(self):
        """
        Verify org creation returns correct response format with ok and organization_url
        """
        response = self.client.post('/api/vnext/organizations/create/', {
            'name': 'Phoenix Esports',
            'slug': 'phoenix-esports',
            'badge': 'PHX',
            'founded_year': 2026,
            'description': 'Rising from the ashes'
        })
        
        self.assertEqual(response.status_code, 201,
                        f"Expected 201, got {response.status_code}: {response.content.decode()}")
        
        data = response.json()
        self.assertTrue(data.get('ok'), "Response should have ok=true")
        self.assertIn('organization_url', data, "Response should have organization_url")
        self.assertIn('organization_slug', data)
        
        # Verify org exists
        org = Organization.objects.get(slug=data['organization_slug'])
        self.assertEqual(org.name, 'Phoenix Esports')
        self.assertEqual(org.ceo, self.user)
        
        # Verify CEO membership created
        ceo_membership = OrganizationMembership.objects.filter(
            organization=org,
            user=self.user,
            role='CEO',
            status='ACTIVE'
        ).first()
        self.assertIsNotNone(ceo_membership, "CEO membership should be auto-created")
    
    def test_org_detail_page_accessible(self):
        """
        Verify org detail page loads after creation
        """
        response = self.client.post('/api/vnext/organizations/create/', {
            'name': 'Detail Org',
            'slug': 'detail-org',
            'badge': 'DTL',
        })
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        detail_response = self.client.get(data['organization_url'])
        self.assertEqual(detail_response.status_code, 200,
                        "Org detail page should be accessible")


@pytest.mark.django_db
class TestAdminStability(TestCase):
    """Tests to ensure admin panel doesn't have FieldErrors"""
    
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')
        
        self.game = Game.objects.first() or Game.objects.create(
            name='Test Game',
            slug='test-game',
            status='ACTIVE'
        )
        
        # Create test team
        self.user = User.objects.create_user(
            username='player',
            email='player@test.com',
            password='pass123'
        )
        self.team = Team.objects.create(
            name='Admin Test Team',
            slug='admin-test-team',
            game_id=self.game.id,
            created_by=self.user,
            status='ACTIVE'
        )
    
    def test_team_admin_list_view(self):
        """
        Verify TeamAdminProxy list view loads without FieldError
        """
        response = self.client.get('/admin/organizations/teamadminproxy/')
        self.assertEqual(response.status_code, 200,
                        "Admin list view should load without errors")
        
        # Should not contain FieldError messages
        content = response.content.decode()
        self.assertNotIn('FieldError', content)
        self.assertNotIn('has no field named', content)
    
    def test_team_admin_change_view(self):
        """
        Verify TeamAdminProxy change view loads without FieldError
        """
        response = self.client.get(f'/admin/organizations/teamadminproxy/{self.team.id}/change/')
        self.assertEqual(response.status_code, 200,
                        "Admin change view should load without errors")
        
        content = response.content.decode()
        self.assertNotIn('FieldError', content)
        self.assertNotIn('has no field named', content)
    
    def test_team_admin_displays_correct_fields(self):
        """
        Verify admin shows correct team fields (not legacy fields)
        """
        response = self.client.get(f'/admin/organizations/teamadminproxy/{self.team.id}/change/')
        content = response.content.decode()
        
        # Should have correct field labels
        self.assertIn('created_by', content.lower())
        self.assertIn('game_id', content.lower())
        
        # Should NOT reference legacy fields
        self.assertNotIn('is_public', content.lower())
        self.assertNotIn('is_verified', content.lower())
        """
        # Create team
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Detail Page Test',
            'tag': 'DPT',
            'game_id': self.game.id,
            'visibility': 'PUBLIC',
            'team_type': 'independent',
        })
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        team_url = data['team_url']
        
        # Access team detail page
        detail_response = self.client.get(team_url)
        self.assertEqual(detail_response.status_code, 200,
                        f"Team detail page at {team_url} should be accessible")
        
        content = detail_response.content.decode()
        self.assertIn('Detail Page Test', content)
    
    def test_independent_team_has_no_organization(self):
        """
        Ensure independent teams explicitly have organization=None
        """
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Independent Team',
            'tag': 'IND',
            'game_id': self.game.id,
            'team_type': 'independent',
        })
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        team = Team.objects.get(slug=data['team_slug'])
        self.assertIsNone(team.organization, 
                         "Independent team must have organization=None")
        self.assertEqual(team.created_by, self.user,
                        "Independent team must have created_by set")
