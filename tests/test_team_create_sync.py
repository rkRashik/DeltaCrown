"""
Tests for Team Creation Sync Fix.

Verifies that:
1. Creating a team via /teams/create/ creates vNext Team (organizations_team)
2. Created teams appear in /teams/vnext/ hub
3. Created teams appear in admin proxy queryset
4. No duplicate teams are created (one source of truth)
"""

import pytest
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.organizations.models import Team, Organization
from apps.organizations.admin import TeamAdminProxy

User = get_user_model()


class TestTeamCreationSync(TestCase):
    """Test team creation produces teams visible in hub and admin."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testcaptain',
            email='captain@test.com',
            password='testpass123'
        )
        self.client.login(username='testcaptain', password='testpass123')
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_create_creates_vnext_team(self):
        """
        Test that /teams/create/ page redirects to Organizations create.
        Then API creates vNext Team (organizations_team table).
        """
        # GET /teams/create/ should redirect to canonical route
        response = self.client.get('/teams/create/')
        
        # Should redirect to organizations:team_create
        self.assertEqual(response.status_code, 302)
        self.assertIn('/teams/create/', response.url)  # Redirects to canonical /teams/create/ (handled by orgs)
        
        # Now create team via API
        from apps.games.models import Game
        game = Game.objects.create(
            title="Test Game",
            slug="test-game",
            display_name="Test Game",
            is_active=True
        )
        
        response = self.client.post(
            '/api/vnext/teams/create/',
            data={
                'name': 'Test Esports Team',
                'game_id': game.id,
                'region': 'Bangladesh',
                'tag': 'TEST',
            },
            content_type='application/json'
        )
        
        # Should create successfully
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data.get('ok'))
        self.assertIn('team_id', data)
        
        # Verify team was created in vNext model
        team = Team.objects.get(id=data['team_id'])
        self.assertEqual(team.name, 'Test Esports Team')
        self.assertEqual(team.game_id, game.id)
        self.assertEqual(team.owner, self.user)
        
        # Verify it's NOT in legacy model
        from apps.teams.models import Team as LegacyTeam
        legacy_count = LegacyTeam.objects.filter(name='Test Esports Team').count()
        self.assertEqual(legacy_count, 0, "Team should NOT be created in legacy table")
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_created_team_visible_in_hub(self):
        """
        Test that team created via API appears in /teams/vnext/ hub.
        """
        # Create team
        from apps.games.models import Game
        game = Game.objects.create(
            title="Valorant",
            slug="valorant",
            display_name="Valorant",
            is_active=True
        )
        
        team = Team.objects.create(
            name='Protocol V',
            slug='protocol-v',
            game_id=game.id,
            region='Bangladesh',
            owner=self.user,
            status='ACTIVE',
            is_public=True
        )
        
        # GET /teams/vnext/ hub
        response = self.client.get('/teams/vnext/')
        self.assertEqual(response.status_code, 200)
        
        # Team name should appear in response
        self.assertContains(
            response,
            'Protocol V',
            msg_prefix="Created team should be visible in /teams/vnext/ hub"
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_created_team_visible_in_admin_proxy(self):
        """
        Test that team created via API appears in admin proxy queryset.
        """
        # Create team
        from apps.games.models import Game
        game = Game.objects.create(
            title="CS2",
            slug="cs2",
            display_name="Counter-Strike 2",
            is_active=True
        )
        
        team = Team.objects.create(
            name='Syntax Esports',
            slug='syntax-esports',
            game_id=game.id,
            region='India',
            owner=self.user,
            status='ACTIVE',
            is_public=True
        )
        
        # Query admin proxy model
        admin_teams = TeamAdminProxy.objects.all()
        
        # Team should exist in proxy queryset
        self.assertGreater(admin_teams.count(), 0)
        
        # Find our team
        proxy_team = admin_teams.get(slug='syntax-esports')
        self.assertEqual(proxy_team.name, 'Syntax Esports')
        self.assertEqual(proxy_team.game_id, game.id)
        self.assertEqual(proxy_team._meta.db_table, 'organizations_team')
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_create_uses_same_table_as_proxy(self):
        """
        Test that Team and TeamAdminProxy use same underlying table.
        """
        # Verify table names match
        self.assertEqual(
            Team._meta.db_table,
            'organizations_team',
            "Team model should use organizations_team table"
        )
        
        self.assertEqual(
            TeamAdminProxy._meta.db_table,
            'organizations_team',
            "TeamAdminProxy should proxy organizations_team table"
        )
        
        # Create team via canonical model
        from apps.games.models import Game
        game = Game.objects.create(
            title="MLBB",
            slug="mlbb",
            display_name="Mobile Legends",
            is_active=True
        )
        
        team = Team.objects.create(
            name='Mobile Warriors',
            slug='mobile-warriors',
            game_id=game.id,
            region='Philippines',
            owner=self.user,
            status='ACTIVE'
        )
        
        # Should be queryable via proxy
        proxy_team = TeamAdminProxy.objects.get(slug='mobile-warriors')
        self.assertEqual(proxy_team.id, team.id)
        self.assertEqual(proxy_team.name, team.name)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_org_owned_team_creation(self):
        """
        Test creating team under organization sets correct ownership.
        """
        # Create organization
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.user,
            is_verified=True
        )
        
        # Make user CEO
        from apps.organizations.models import OrganizationMembership
        OrganizationMembership.objects.create(
            organization=org,
            user=self.user,
            role='CEO'
        )
        
        # Create game
        from apps.games.models import Game
        game = Game.objects.create(
            title="Dota 2",
            slug="dota-2",
            display_name="Dota 2",
            is_active=True
        )
        
        # Create org-owned team via API
        response = self.client.post(
            '/api/vnext/teams/create/',
            data={
                'name': 'Test Org Academy',
                'game_id': game.id,
                'region': 'SEA',
                'organization_id': org.id,
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        # Verify team has correct ownership
        team = Team.objects.get(id=data['team_id'])
        self.assertEqual(team.organization, org)
        self.assertIsNone(team.owner)  # Org-owned teams have no owner
        
        # Should be visible in hub
        response = self.client.get('/teams/vnext/')
        self.assertContains(response, 'Test Org Academy')


class TestLegacyTeamCreateRedirect(TestCase):
    """Test that legacy /teams/create/ properly redirects."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_teams_namespace_create_redirects_to_canonical(self):
        """
        Test that /teams/create/ (teams namespace) redirects to canonical route.
        """
        # Access via teams namespace should redirect
        response = self.client.get('/teams/create/')
        
        # Should redirect to canonical organizations route
        self.assertEqual(response.status_code, 302)
    
    @override_settings(ORG_APP_ENABLED=0, LEGACY_TEAMS_ENABLED=1)
    def test_teams_create_uses_legacy_when_org_disabled(self):
        """
        Test that /teams/create/ uses legacy view when ORG_APP_ENABLED=0.
        """
        response = self.client.get('/teams/create/')
        
        # Should render legacy create page (not redirect)
        self.assertEqual(response.status_code, 200)
        # Legacy template should be rendered
        self.assertTemplateUsed(response, 'teams/team_create/index.html')


class TestPhase7Permissions(TestCase):
    """Phase 7: Test permission enforcement across views and admin."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create users
        self.owner = User.objects.create_user('owner', 'owner@test.com', 'pass')
        self.manager = User.objects.create_user('manager', 'manager@test.com', 'pass')
        self.member = User.objects.create_user('member', 'member@test.com', 'pass')
        self.outsider = User.objects.create_user('outsider', 'outsider@test.com', 'pass')
        
        # Create org
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.owner
        )
        
        # Add manager to org
        from apps.organizations.models import OrganizationMembership
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.manager,
            role='MANAGER'
        )
        
        # Create team
        from apps.games.models import Game
        game = Game.objects.create(
            title='Test Game',
            slug='test-game',
            display_name='Test Game',
            is_active=True
        )
        
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=game.id,
            region='Bangladesh',
            organization=self.org,
            status='ACTIVE'
        )
        
        # Add member to team
        from apps.organizations.models import TeamMembership
        TeamMembership.objects.create(
            team=self.team,
            user=self.member,
            role='MEMBER',
            status='ACTIVE'
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_owner_can_manage_team(self):
        """Org CEO should be able to manage team."""
        self.client.login(username='owner', password='pass')
        response = self.client.get(f'/orgs/{self.org.slug}/teams/{self.team.slug}/manage/')
        self.assertEqual(response.status_code, 200)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_manager_can_manage_team(self):
        """Org manager should be able to manage team."""
        self.client.login(username='manager', password='pass')
        response = self.client.get(f'/orgs/{self.org.slug}/teams/{self.team.slug}/manage/')
        self.assertEqual(response.status_code, 200)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_member_cannot_manage_team(self):
        """Regular team member should NOT be able to manage team."""
        self.client.login(username='member', password='pass')
        response = self.client.get(f'/orgs/{self.org.slug}/teams/{self.team.slug}/manage/')
        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/orgs/{self.org.slug}/teams/{self.team.slug}/', response.url)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_outsider_cannot_manage_team(self):
        """User with no relationship to team should NOT be able to manage."""
        self.client.login(username='outsider', password='pass')
        response = self.client.get(f'/orgs/{self.org.slug}/teams/{self.team.slug}/manage/')
        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_visible_in_org_admin_inline(self):
        """Team should appear in Organization admin inline."""
        # Verify team is queryable via admin proxy
        from apps.organizations.admin import TeamAdminProxy
        teams = TeamAdminProxy.objects.filter(organization=self.org)
        self.assertEqual(teams.count(), 1)
        self.assertEqual(teams.first().slug, 'test-team')
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_org_scoped_url_enforced(self):
        """Wrong org_slug should return 404."""
        # Create another org
        other_org = Organization.objects.create(
            name='Other Org',
            slug='other-org',
            ceo=self.outsider
        )
        
        self.client.login(username='owner', password='pass')
        # Try to access team with wrong org_slug
        response = self.client.get(f'/orgs/{other_org.slug}/teams/{self.team.slug}/')
        self.assertEqual(response.status_code, 404)

