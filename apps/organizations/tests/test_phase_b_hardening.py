"""
Tests for Create Team Phase B: Real Data Wiring + Validation + Submission

These tests verify the hardened Phase B implementation:
- Validation endpoints (name/tag uniqueness)
- Create team submission with all fields
- API response schema compliance (hub pattern)
- Query count performance
- Permission checks
"""

import pytest
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

from apps.organizations.models import Organization, OrganizationMembership, Team
from apps.games.models import Game

User = get_user_model()


@pytest.mark.django_db
class TestTeamValidationEndpoints(TestCase):
    """Test validate-name and validate-tag endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test game
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            display_name='TEST GAME',
            is_active=True
        )
        
        # Create existing team for uniqueness testing
        self.existing_team = Team.objects.create(
            name='Existing Team',
            game_id=self.game.id,
            owner=self.user,
            region='US',
            status='ACTIVE'
        )
    
    def test_validate_name_requires_auth(self):
        """Test that validation requires authentication."""
        self.client.logout()
        response = self.client.get('/api/vnext/teams/validate-name/', {
            'name': 'New Team',
            'game_slug': 'test-game',
            'mode': 'independent'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_validate_name_available(self):
        """Test name validation for available name."""
        response = self.client.get('/api/vnext/teams/validate-name/', {
            'name': 'New Team',
            'game_slug': 'test-game',
            'mode': 'independent'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ok'], True)
        self.assertEqual(response.data['available'], True)
    
    def test_validate_name_unavailable(self):
        """Test name validation for existing name."""
        response = self.client.get('/api/vnext/teams/validate-name/', {
            'name': 'Existing Team',
            'game_slug': 'test-game',
            'mode': 'independent'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ok'], False)
        self.assertEqual(response.data['available'], False)
        self.assertIn('field_errors', response.data)
        self.assertIn('name', response.data['field_errors'])
    
    def test_validate_name_missing_params(self):
        """Test name validation with missing params."""
        response = self.client.get('/api/vnext/teams/validate-name/', {
            'name': 'Test'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ok'], False)
        self.assertIn('field_errors', response.data)
    
    def test_validate_name_too_short(self):
        """Test name validation with minimum length check."""
        response = self.client.get('/api/vnext/teams/validate-name/', {
            'name': 'Ab',  # Only 2 chars
            'game_slug': 'test-game',
            'mode': 'independent'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ok'], False)
        self.assertIn('field_errors', response.data)
    
    def test_validate_name_invalid_game(self):
        """Test name validation with invalid game slug."""
        response = self.client.get('/api/vnext/teams/validate-name/', {
            'name': 'New Team',
            'game_slug': 'nonexistent-game',
            'mode': 'independent'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ok'], False)
        self.assertIn('field_errors', response.data)
    
    def test_validate_tag_available(self):
        """Test tag validation for available tag."""
        response = self.client.get('/api/vnext/teams/validate-tag/', {
            'tag': 'NEW',
            'game_slug': 'test-game',
            'mode': 'independent'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ok'], True)
        self.assertEqual(response.data['available'], True)
    
    def test_validate_tag_too_short(self):
        """Test tag validation with minimum length."""
        response = self.client.get('/api/vnext/teams/validate-tag/', {
            'tag': 'A',  # Only 1 char
            'game_slug': 'test-game',
            'mode': 'independent'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ok'], False)
        self.assertIn('field_errors', response.data)
    
    def test_validate_tag_too_long(self):
        """Test tag validation with maximum length."""
        response = self.client.get('/api/vnext/teams/validate-tag/', {
            'tag': 'TOOLONG',  # 7 chars
            'game_slug': 'test-game',
            'mode': 'independent'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ok'], False)
        self.assertIn('field_errors', response.data)


@pytest.mark.django_db
@override_settings(
    TEAM_VNEXT_ADAPTER_ENABLED=True,
    TEAM_VNEXT_FORCE_LEGACY=False,
    TEAM_VNEXT_ROUTING_MODE='vnext_first'
)
class TestCreateTeamEndpoint(TestCase):
    """Test create team POST endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test game
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            display_name='TEST GAME',
            is_active=True
        )
        
        # Create test organization
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.user
        )
        
        # Create CEO membership
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role='CEO',
            status='ACTIVE'
        )
    
    def test_create_independent_team_success(self):
        """Test creating an independent team."""
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'My New Team',
            'game_slug': 'test-game',
            'mode': 'independent',
            'region': 'United States',
            'description': 'Test team description'
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ok'], True)
        self.assertIn('team_id', response.data)
        self.assertIn('team_slug', response.data)
        self.assertIn('team_url', response.data)
        
        # Verify team created in database
        team = Team.objects.get(id=response.data['team_id'])
        self.assertEqual(team.name, 'My New Team')
        self.assertEqual(team.game_id, self.game.id)
        self.assertEqual(team.owner, self.user)
        self.assertEqual(team.region, 'United States')
    
    def test_create_org_owned_team_success(self):
        """Test creating an org-owned team as CEO."""
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Org Team',
            'game_slug': 'test-game',
            'mode': 'org',
            'organization_id': self.org.id,
            'region': 'US'
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ok'], True)
        
        # Verify team is org-owned
        team = Team.objects.get(id=response.data['team_id'])
        self.assertEqual(team.organization_id, self.org.id)
        self.assertIsNone(team.owner)
    
    def test_create_team_with_logo_upload(self):
        """Test creating team with logo file upload."""
        logo_file = SimpleUploadedFile(
            name='test_logo.png',
            content=b'fake_image_content',
            content_type='image/png'
        )
        
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Team With Logo',
            'game_slug': 'test-game',
            'mode': 'independent',
            'logo': logo_file
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.get(id=response.data['team_id'])
        self.assertTrue(team.logo)
    
    def test_create_team_missing_required_fields(self):
        """Test validation error for missing required fields."""
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test Team'
            # Missing game_slug
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['ok'], False)
        self.assertIn('field_errors', response.data)
    
    def test_create_org_team_permission_denied(self):
        """Test org-owned team creation without permission."""
        # Create another org where user is not CEO/MANAGER
        other_org = Organization.objects.create(
            name='Other Org',
            slug='other-org',
            ceo=User.objects.create_user(username='otherceo', email='other@test.com')
        )
        
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Unauthorized Team',
            'game_slug': 'test-game',
            'mode': 'org',
            'organization_id': other_org.id
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['ok'], False)
        self.assertEqual(response.data['error_code'], 'permission_denied')
    
    def test_create_team_invalid_game(self):
        """Test validation error for invalid game slug."""
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test Team',
            'game_slug': 'nonexistent-game',
            'mode': 'independent'
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['ok'], False)


@pytest.mark.django_db
class TestCreateTeamUIView(TestCase):
    """Test the UI view for team creation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test games
        for i in range(3):
            Game.objects.create(
                name=f'Game {i}',
                slug=f'game-{i}',
                display_name=f'GAME {i}',
                is_active=True
            )
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_FORCE_LEGACY=False
    )
    def test_team_create_view_loads(self):
        """Test that team create UI view loads successfully."""
        response = self.client.get('/teams/create/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'Forge Your')
        self.assertContains(response, 'Squad')
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_FORCE_LEGACY=False
    )
    def test_team_create_context_games(self):
        """Test that games are passed to template context."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/teams/create/')
        
        self.assertIn('games', response.context)
        self.assertEqual(response.context['games'].count(), 3)
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_FORCE_LEGACY=False
    )
    def test_team_create_context_organizations(self):
        """Test that user's organizations are passed to context."""
        # Create org where user is CEO
        org = Organization.objects.create(
            name='My Org',
            slug='my-org',
            ceo=self.user
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=self.user,
            role='CEO',
            status='ACTIVE'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/teams/create/')
        
        self.assertIn('user_organizations', response.context)
        self.assertEqual(response.context['user_organizations'].count(), 1)
        self.assertEqual(response.context['user_organizations'][0].id, org.id)
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_FORCE_LEGACY=False
    )
    def test_team_create_context_countries(self):
        """Test that countries list is passed to context."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/teams/create/')
        
        self.assertIn('countries', response.context)
        self.assertIsInstance(response.context['countries'], list)
        self.assertGreater(len(response.context['countries']), 0)
        # Check structure
        self.assertIn('code', response.context['countries'][0])
        self.assertIn('name', response.context['countries'][0])


# Query count tests (performance)
@pytest.mark.django_db
class TestQueryPerformance(TestCase):
    """Test query count performance targets."""
    
    def setUp(self):
        """Set up test fixtures."""
        from django.test.utils import override_settings
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            display_name='TEST GAME',
            is_active=True
        )
    
    def test_validate_name_query_count(self):
        """Test that validate-name uses ≤2 queries."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        
        with CaptureQueriesContext(connection) as context:
            self.client.get('/api/vnext/teams/validate-name/', {
                'name': 'New Team',
                'game_slug': 'test-game',
                'mode': 'independent'
            })
        
        # Target: ≤2 queries (game lookup + team exists check)
        self.assertLessEqual(len(context.captured_queries), 2,
                           f"Validation endpoint used {len(context.captured_queries)} queries (target: ≤2)")
    
    def test_validate_tag_query_count(self):
        """Test that validate-tag uses ≤2 queries."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        
        with CaptureQueriesContext(connection) as context:
            self.client.get('/api/vnext/teams/validate-tag/', {
                'tag': 'NEW',
                'game_slug': 'test-game',
                'mode': 'independent'
            })
        
        self.assertLessEqual(len(context.captured_queries), 2)
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_FORCE_LEGACY=False
    )
    def test_team_create_view_query_count(self):
        """Test that team create view uses ≤5 queries."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        
        self.client.login(username='testuser', password='testpass123')
        
        with CaptureQueriesContext(connection) as context:
            self.client.get('/teams/create/')
        
        # Target: ≤5 queries (session, user, games, orgs, prefetch)
        self.assertLessEqual(len(context.captured_queries), 5,
                           f"Create view used {len(context.captured_queries)} queries (target: ≤5)")
