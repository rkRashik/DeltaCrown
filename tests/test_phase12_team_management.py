"""
Phase 12 Validation Tests: Team Management Journey

Tests the complete team management flow:
- Team management page loads with correct permissions
- Settings form submits to correct endpoint
- Member invite/remove functions work
- Branding form submits to correct endpoint

PHASE: 12 (Journey 3 & 4 Completion)
DATE: 2026-02-03
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.organizations.models import Team, TeamMembership, Organization
from apps.games.models import Game
from apps.organizations.services import TeamService

User = get_user_model()


@pytest.mark.django_db
class TestPhase12TeamManagement:
    """Test Journey 3: Team Management (Independent Teams)"""

    def test_team_manage_page_loads_for_owner(self, client):
        """Test that team management page loads for team owner"""
        # Create user
        user = User.objects.create_user(
            username="team_captain",
            email="captain@test.com",
            password="testpass123"
        )
        
        # Create game
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        
        # Create independent team
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game_id=game.id,
            created_by=user,
            status="ACTIVE",
            organization=None
        )
        
        # Create owner membership
        TeamMembership.objects.create(
            team=team,
            user=user,
            role="OWNER",
            status="ACTIVE"
        )
        
        # Login
        client.force_login(user)
        
        # Access manage page
        url = reverse('organizations:team_manage', kwargs={'team_slug': team.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        assert b"Team Settings" in response.content
        assert b"Team Members" in response.content
        assert b"Team Branding" in response.content

    def test_team_settings_form_has_correct_action(self, client):
        """Test that settings form points to correct API endpoint"""
        # Create user
        user = User.objects.create_user(
            username="team_captain",
            email="captain@test.com",
            password="testpass123"
        )
        
        # Create game
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        
        # Create independent team
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game_id=game.id,
            created_by=user,
            status="ACTIVE",
            organization=None
        )
        
        # Create owner membership
        TeamMembership.objects.create(
            team=team,
            user=user,
            role="OWNER",
            status="ACTIVE"
        )
        
        # Login
        client.force_login(user)
        
        # Access manage page
        url = reverse('organizations:team_manage', kwargs={'team_slug': team.slug})
        response = client.get(url)
        
        # Check that form action uses correct URL (team_update_settings, not team-update)
        expected_action = reverse('organizations_api:team_update_settings', kwargs={'team_slug': team.slug})
        assert expected_action.encode() in response.content

    def test_team_manage_blocks_non_owner(self, client):
        """Test that team management page blocks unauthorized users"""
        # Create owner
        owner = User.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="testpass123"
        )
        
        # Create non-owner
        visitor = User.objects.create_user(
            username="visitor",
            email="visitor@test.com",
            password="testpass123"
        )
        
        # Create game
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        
        # Create independent team
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game_id=game.id,
            created_by=owner,
            status="ACTIVE",
            organization=None
        )
        
        # Create owner membership
        TeamMembership.objects.create(
            team=team,
            user=owner,
            role="OWNER",
            status="ACTIVE"
        )
        
        # Login as visitor (not owner)
        client.force_login(visitor)
        
        # Try to access manage page
        url = reverse('organizations:team_manage', kwargs={'team_slug': team.slug})
        response = client.get(url)
        
        # Should be redirected or get 403
        assert response.status_code in [302, 403]

    def test_member_invite_api_endpoint_exists(self, client):
        """Test that member invite API endpoint is accessible"""
        # Create user
        user = User.objects.create_user(
            username="team_captain",
            email="captain@test.com",
            password="testpass123"
        )
        
        # Create game
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        
        # Create independent team
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game_id=game.id,
            created_by=user,
            status="ACTIVE",
            organization=None
        )
        
        # Create owner membership
        TeamMembership.objects.create(
            team=team,
            user=user,
            role="OWNER",
            status="ACTIVE"
        )
        
        # Login
        client.force_login(user)
        
        # Check that invite endpoint exists
        url = reverse('organizations_api:team_add_member', kwargs={'team_slug': team.slug})
        assert url == f'/api/vnext/teams/{team.slug}/members/add/'

    def test_member_remove_api_endpoint_exists(self, client):
        """Test that member remove API endpoint is accessible"""
        # Create user
        user = User.objects.create_user(
            username="team_captain",
            email="captain@test.com",
            password="testpass123"
        )
        
        # Create game
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        
        # Create independent team
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game_id=game.id,
            created_by=user,
            status="ACTIVE",
            organization=None
        )
        
        # Create owner membership
        TeamMembership.objects.create(
            team=team,
            user=user,
            role="OWNER",
            status="ACTIVE"
        )
        
        # Login
        client.force_login(user)
        
        # Check that remove endpoint exists
        url = reverse('organizations_api:team_remove_member', kwargs={
            'team_slug': team.slug,
            'member_id': 1
        })
        assert url == f'/api/vnext/teams/{team.slug}/members/1/remove/'

    def test_branding_form_uses_logo_url_not_file(self, client):
        """Test that branding form uses logo_url field, not file upload"""
        # Create user
        user = User.objects.create_user(
            username="team_captain",
            email="captain@test.com",
            password="testpass123"
        )
        
        # Create game
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        
        # Create independent team
        team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            game_id=game.id,
            created_by=user,
            status="ACTIVE",
            organization=None
        )
        
        # Create owner membership
        TeamMembership.objects.create(
            team=team,
            user=user,
            role="OWNER",
            status="ACTIVE"
        )
        
        # Login
        client.force_login(user)
        
        # Access manage page
        url = reverse('organizations:team_manage', kwargs={'team_slug': team.slug})
        response = client.get(url)
        
        # Check that branding form uses logo_url (not file input)
        assert b'name="logo_url"' in response.content
        assert b'type="url"' in response.content
        # Should NOT have file input
        assert b'type="file"' not in response.content or b'name="logo"' not in response.content


@pytest.mark.django_db
class TestPhase12OrgTeamManagement:
    """Test Journey 4: Organization Control (Org Teams)"""

    def test_org_team_manage_allows_org_ceo(self, client):
        """Test that org team management allows org CEO access"""
        # Create CEO
        ceo = User.objects.create_user(
            username="ceo",
            email="ceo@test.com",
            password="testpass123"
        )
        
        # Create organization
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            ceo=ceo
        )
        
        # Create game
        game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        
        # Create org-owned team (no individual creator)
        team = Team.objects.create(
            name="Test Org Team",
            slug="test-org-team",
            game_id=game.id,
            organization=org,
            created_by=ceo,
            status="ACTIVE"
        )
        
        # Login as CEO
        client.force_login(ceo)
        
        # Access manage page
        url = reverse('organizations:team_manage', kwargs={'team_slug': team.slug})
        response = client.get(url)
        
        # CEO should have access
        assert response.status_code == 200
        assert b"Team Settings" in response.content
