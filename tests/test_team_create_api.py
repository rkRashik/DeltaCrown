"""
Tests for Team Create API (Journey 1).

Tests backend /api/vnext/teams/create/ endpoint for:
- Independent team creation
- Org-owned team creation
- Validation errors
- Platform rule enforcement (one active team per user per game)
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.organizations.models import (
    Team,
    TeamMembership,
    TeamMembershipEvent,
    Organization,
    OrganizationMembership,
)
from apps.organizations.choices import MembershipRole, MembershipStatus, MembershipEventType
from apps.games.models import Game

User = get_user_model()


@pytest.fixture
def api_client():
    """Provide an API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='testpass123'
    )


@pytest.fixture
def another_user(db):
    """Create another test user."""
    return User.objects.create_user(
        username='anotheruser',
        email='another@example.com',
        password='testpass123'
    )


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        status='ACTIVE'
    )


@pytest.fixture
def organization(db, user):
    """Create a test organization with user as CEO."""
    org = Organization.objects.create(
        name='Test Org',
        slug='test-org',
        status='ACTIVE',
        created_by=user
    )
    # Create CEO membership
    OrganizationMembership.objects.create(
        organization=org,
        user=user,
        role='CEO',
        status='ACTIVE'
    )
    return org


@pytest.mark.django_db
class TestTeamCreateAPI:
    """Test suite for /api/vnext/teams/create/ endpoint."""
    
    def test_create_team_independent_returns_team_url(self, api_client, user, game):
        """
        Test that creating an independent team:
        - Returns 201 status
        - Returns team_url
        - Creates team with creator as MANAGER (not OWNER)
        - Creates JOINED membership event
        """
        api_client.force_authenticate(user=user)
        
        data = {
            'name': 'Cloud9 Blue',
            'game_id': game.id,
            'tag': 'C9B',
            'tagline': 'Test tagline',
            'region': 'NA',
            'mode': 'independent'
        }
        
        response = api_client.post('/api/vnext/teams/create/', data, format='json')
        
        # Verify response
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.data}"
        assert response.data['ok'] is True
        assert 'team_url' in response.data
        assert 'team_slug' in response.data
        assert response.data['team_slug'] == 'cloud9-blue'
        
        # Verify team created
        team = Team.objects.get(slug='cloud9-blue')
        assert team.name == 'Cloud9 Blue'
        assert team.game_id == game.id
        assert team.created_by == user
        assert team.organization is None  # Independent team
        
        # Verify creator membership with MANAGER role (vNext rule)
        membership = TeamMembership.objects.get(team=team, user=user)
        assert membership.role == MembershipRole.MANAGER  # NOT OWNER
        assert membership.status == MembershipStatus.ACTIVE
        
        # Verify JOINED event created (Foundation requirement)
        event = TeamMembershipEvent.objects.get(
            team=team,
            user=user,
            event_type=MembershipEventType.JOINED
        )
        assert event.membership == membership
        assert event.new_role == MembershipRole.MANAGER
        assert event.new_status == MembershipStatus.ACTIVE
        assert event.metadata.get('is_creator') is True
    
    def test_create_team_org_owned_returns_org_team_url(self, api_client, user, game, organization):
        """
        Test that creating an org-owned team:
        - Returns 201 status
        - Returns team_url with org slug
        - Sets organization FK correctly
        - Does NOT create creator membership (org-owned teams use org roles)
        """
        api_client.force_authenticate(user=user)
        
        data = {
            'name': 'Test Org Academy',
            'game_id': game.id,
            'organization_id': organization.id,
            'tag': 'TOA',
            'region': 'NA',
            'mode': 'organization'
        }
        
        response = api_client.post('/api/vnext/teams/create/', data, format='json')
        
        # Verify response
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.data}"
        assert response.data['ok'] is True
        assert 'team_url' in response.data
        # Org-owned team URL should include org slug
        assert f'/orgs/{organization.slug}/teams/' in response.data['team_url']
        
        # Verify team created with org FK
        team = Team.objects.get(slug='test-org-academy')
        assert team.organization == organization
        assert team.created_by == user
        
        # Org-owned teams should NOT create creator membership
        # (they use organization memberships instead)
        membership_count = TeamMembership.objects.filter(team=team, user=user).count()
        assert membership_count == 0, "Org-owned teams should not create creator membership"
    
    def test_create_team_duplicate_name_returns_field_error(self, api_client, user, game):
        """
        Test that creating a team with duplicate name:
        - Returns 400 or 409 status
        - Returns field_errors with 'name' key
        - Does not create team
        """
        api_client.force_authenticate(user=user)
        
        # Create first team
        Team.objects.create(
            name='Existing Team',
            slug='existing-team',
            game_id=game.id,
            created_by=user,
            status='ACTIVE'
        )
        
        # Try to create duplicate
        data = {
            'name': 'Existing Team',
            'game_id': game.id,
            'tag': 'ET2',
            'mode': 'independent'
        }
        
        response = api_client.post('/api/vnext/teams/create/', data, format='json')
        
        # Should fail with validation error
        assert response.status_code in [400, 409], f"Expected 400/409, got {response.status_code}"
        assert response.data['ok'] is False
        
        # Should have field error for name
        assert 'field_errors' in response.data or 'safe_message' in response.data
        
        # Verify only one team exists
        assert Team.objects.filter(name='Existing Team').count() == 1
    
    def test_create_team_enforces_one_active_team_per_user_per_game(self, api_client, user, game):
        """
        Test platform rule: one active team per user per game.
        
        Creating a second ACTIVE team for the same user+game:
        - Should fail with 400/409 status
        - Should return appropriate error message
        """
        api_client.force_authenticate(user=user)
        
        # Create first active team
        first_team = Team.objects.create(
            name='First Team',
            slug='first-team',
            game_id=game.id,
            created_by=user,
            status='ACTIVE'
        )
        TeamMembership.objects.create(
            team=first_team,
            user=user,
            role=MembershipRole.MANAGER,
            status=MembershipStatus.ACTIVE
        )
        
        # Try to create second active team for same user+game
        data = {
            'name': 'Second Team',
            'game_id': game.id,
            'tag': 'ST',
            'mode': 'independent'
        }
        
        response = api_client.post('/api/vnext/teams/create/', data, format='json')
        
        # Should fail (platform rule enforcement)
        assert response.status_code in [400, 409], f"Expected 400/409, got {response.status_code}"
        assert response.data['ok'] is False
        
        # Should have appropriate error message
        error_msg = response.data.get('safe_message', '').lower()
        assert 'already' in error_msg or 'active' in error_msg or 'existing' in error_msg, \
            f"Error message should mention existing active team: {error_msg}"
        
        # Verify only one ACTIVE team exists for this user+game
        active_teams = Team.objects.filter(
            game_id=game.id,
            created_by=user,
            status='ACTIVE'
        )
        assert active_teams.count() == 1
    
    def test_create_team_requires_authentication(self, api_client, game):
        """Test that unauthenticated requests are rejected."""
        data = {
            'name': 'Test Team',
            'game_id': game.id,
            'mode': 'independent'
        }
        
        response = api_client.post('/api/vnext/teams/create/', data, format='json')
        
        # Should fail with 401 or 403
        assert response.status_code in [401, 403]
    
    def test_create_team_org_requires_ceo_or_manager_permission(self, api_client, another_user, game, organization):
        """
        Test that creating org-owned team requires CEO/MANAGER role.
        
        User without org membership should be rejected with 403.
        """
        # another_user is NOT a member of organization
        api_client.force_authenticate(user=another_user)
        
        data = {
            'name': 'Unauthorized Team',
            'game_id': game.id,
            'organization_id': organization.id,
            'mode': 'organization'
        }
        
        response = api_client.post('/api/vnext/teams/create/', data, format='json')
        
        # Should fail with permission error
        assert response.status_code == 403
        assert response.data['ok'] is False
        assert 'permission' in response.data.get('safe_message', '').lower()    
    def test_create_team_returns_json_on_error_not_500_html(self, api_client, user, game):
        """
        Test that validation errors return JSON (not 500 HTML).
        
        Force a validation error and verify:
        - Response is JSON
        - Response has ok=False
        - Response has safe_message
        - Status code is 400, not 500
        """
        api_client.force_authenticate(user=user)
        
        # Force validation error by omitting required field (name)
        data = {
            'game_id': game.id,
            'tag': 'TST',
            'mode': 'independent'
            # Missing 'name' - required field
        }
        
        response = api_client.post('/api/vnext/teams/create/', data, format='json')
        
        # Should return 400, not 500
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        # Response should be JSON
        assert response['Content-Type'].startswith('application/json')
        
        # Response should have error structure
        assert 'ok' in response.data
        assert response.data['ok'] is False
        assert 'safe_message' in response.data or 'field_errors' in response.data
        
        # Should NOT be an HTML error page
        content = str(response.content)
        assert '<html' not in content.lower(), "Response should be JSON, not HTML"
    
    def test_create_team_does_not_crash_if_cache_backend_lacks_delete_pattern(self, api_client, user, game, monkeypatch):
        """
        Test that team creation succeeds even if cache backend doesn't support delete_pattern.
        
        This is critical for LocMemCache in dev environments.
        Cache invalidation should be best-effort and never crash requests.
        """
        api_client.force_authenticate(user=user)
        
        # Mock cache to remove delete_pattern support (like LocMemCache)
        from django.core.cache import cache
        original_delete_pattern = getattr(cache, 'delete_pattern', None)
        
        # Remove delete_pattern method to simulate LocMemCache
        if hasattr(cache, 'delete_pattern'):
            monkeypatch.delattr(cache.__class__, 'delete_pattern')
        
        try:
            data = {
                'name': 'Cache Test Team',
                'game_id': game.id,
                'tag': 'CTT',
                'mode': 'independent'
            }
            
            response = api_client.post('/api/vnext/teams/create/', data, format='json')
            
            # Should succeed despite cache backend lacking delete_pattern
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.data}"
            assert response.data['ok'] is True
            assert 'team_url' in response.data
            
            # Verify team was actually created
            team = Team.objects.get(slug='cache-test-team')
            assert team.name == 'Cache Test Team'
            
        finally:
            # Restore delete_pattern if it existed
            if original_delete_pattern:
                monkeypatch.setattr(cache.__class__, 'delete_pattern', original_delete_pattern)
    
    def test_create_team_slug_collision_returns_unique_slug(self, api_client, user, game):
        """
        Test that creating teams with similar names generates unique slugs.
        
        The Team model's save() method handles slug collision by appending -2, -3, etc.
        This test verifies that mechanism works correctly.
        """
        api_client.force_authenticate(user=user)
        
        # Create first team
        data1 = {
            'name': 'Test Team',
            'game_id': game.id,
            'tag': 'TT1',
            'mode': 'independent'
        }
        response1 = api_client.post('/api/vnext/teams/create/', data1, format='json')
        assert response1.status_code == 201
        assert response1.data['team_slug'] == 'test-team'
        
        # Create another user for second team (to avoid one_team_per_game constraint)
        user2 = User.objects.create_user(
            username='testuser2',
            email='testuser2@example.com',
            password='testpass123'
        )
        api_client.force_authenticate(user=user2)
        
        # Try to create second team with same name
        data2 = {
            'name': 'Test Team',
            'game_id': game.id,
            'tag': 'TT2',
            'mode': 'independent'
        }
        response2 = api_client.post('/api/vnext/teams/create/', data2, format='json')
        
        # Should succeed with auto-generated unique slug
        assert response2.status_code == 201, f"Expected 201, got {response2.status_code}: {response2.data}"
        assert response2.data['ok'] is True
        assert response2.data['team_slug'] in ['test-team-1', 'test-team-2']  # Auto-appended suffix
        
        # Verify both teams exist with different slugs
        team1 = Team.objects.get(slug='test-team')
        team2 = Team.objects.get(slug__startswith='test-team-')
        assert team1.name == 'Test Team'
        assert team2.name == 'Test Team'
        assert team1.slug != team2.slug
    
    def test_create_team_tag_conflict_returns_field_error(self, api_client, user, game):
        """
        Test that creating team with duplicate tag returns field_errors.tag.
        
        Tag uniqueness is enforced per game by unique_tag_per_game constraint.
        """
        api_client.force_authenticate(user=user)
        
        # Create first team with tag
        data1 = {
            'name': 'First Team',
            'game_id': game.id,
            'tag': 'DUPL',
            'mode': 'independent'
        }
        response1 = api_client.post('/api/vnext/teams/create/', data1, format='json')
        assert response1.status_code == 201
        
        # Create another user for second team
        user2 = User.objects.create_user(
            username='testuser2',
            email='testuser2@example.com',
            password='testpass123'
        )
        api_client.force_authenticate(user=user2)
        
        # Try to create second team with same tag for same game
        data2 = {
            'name': 'Second Team',
            'game_id': game.id,
            'tag': 'DUPL',  # Duplicate tag
            'mode': 'independent'
        }
        response2 = api_client.post('/api/vnext/teams/create/', data2, format='json')
        
        # Should fail with 409 and field_errors.tag
        assert response2.status_code == 409, f"Expected 409, got {response2.status_code}"
        assert response2.data['ok'] is False
        assert 'field_errors' in response2.data
        assert 'tag' in response2.data['field_errors']
        
        # Verify error message mentions the tag
        tag_error = response2.data['field_errors']['tag']
        assert isinstance(tag_error, list)
        assert 'DUPL' in tag_error[0] or 'already taken' in tag_error[0].lower()
        
        # Verify only first team exists
        assert Team.objects.filter(tag='DUPL').count() == 1
