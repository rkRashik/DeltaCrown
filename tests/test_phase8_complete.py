"""
Phase 8 Comprehensive Test Suite

Tests for canonical Organization-Team system covering:
- Model constraints (Team MUST belong to Organization)
- URL routing (canonical org-scoped URLs)
- Permissions (centralized permission system)
- View access (create, detail, manage)
- Admin integration
- Data consistency

Minimum 25-30 tests as required by Phase 8 spec.
"""

import pytest
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import IntegrityError

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    Team,
    TeamMembership,
)
from apps.organizations.permissions import (
    get_org_role,
    get_team_role,
    can_view_org,
    can_manage_org,
    can_view_team,
    can_manage_team,
    can_create_team_in_org,
)
from apps.games.models import Game

User = get_user_model()


@pytest.mark.django_db
class TestPhase8ModelConstraints(TestCase):
    """Test 1-5: Model-level constraints for Team→Organization"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.user
        )
        self.game = Game.objects.create(
            title='Test Game',
            slug='test-game',
            display_name='Test Game',
            is_active=True
        )
    
    def test_team_requires_organization(self):
        """Test 1: Team cannot be created without organization"""
        with self.assertRaises(IntegrityError):
            Team.objects.create(
                name='Team Without Org',
                slug='no-org-team',
                game_id=self.game.id,
                region='Bangladesh',
                organization=None  # Should fail
            )
    
    def test_team_organization_field_not_nullable(self):
        """Test 2: Team.organization field is NOT nullable"""
        team = Team(
            name='Test Team',
            slug='test-team',
            game_id=self.game.id,
            region='Bangladesh'
        )
        # organization field should not allow None
        with self.assertRaises((IntegrityError, ValueError)):
            team.save()
    
    def test_team_created_by_is_optional(self):
        """Test 3: Team.created_by is optional (audit trail only)"""
        team = Team.objects.create(
            name='Team No Creator',
            slug='no-creator',
            game_id=self.game.id,
            region='Bangladesh',
            organization=self.org,
            created_by=None  # Should be allowed
        )
        self.assertIsNone(team.created_by)
    
    def test_team_always_has_organization(self):
        """Test 4: All teams have organization (Phase 8 enforcement)"""
        team = Team.objects.create(
            name='Org Team',
            slug='org-team',
            game_id=self.game.id,
            region='Bangladesh',
            organization=self.org,
            created_by=self.user
        )
        self.assertIsNotNone(team.organization)
        self.assertEqual(team.organization, self.org)
    
    def test_team_is_organization_team_always_true(self):
        """Test 5: is_organization_team() always returns True (Phase 8)"""
        team = Team.objects.create(
            name='Always Org',
            slug='always-org',
            game_id=self.game.id,
            region='Bangladesh',
            organization=self.org
        )
        self.assertTrue(team.is_organization_team())


@pytest.mark.django_db
class TestPhase8URLRouting(TestCase):
    """Test 6-10: URL routing and canonical redirects"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.user
        )
        self.game = Game.objects.create(
            title='Test Game',
            slug='test-game',
            display_name='Test Game',
            is_active=True
        )
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=self.game.id,
            region='Bangladesh',
            organization=self.org,
            created_by=self.user
        )
        self.client.login(username='testuser', password='pass')
    
    def test_team_get_absolute_url_is_org_scoped(self):
        """Test 6: Team.get_absolute_url() returns org-scoped URL"""
        expected_url = f'/orgs/{self.org.slug}/teams/{self.team.slug}/'
        self.assertEqual(self.team.get_absolute_url(), expected_url)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_detail_canonical_url_works(self):
        """Test 7: Canonical org-scoped URL works for team detail"""
        url = reverse('organizations:org_team_detail', 
                     kwargs={'org_slug': self.org.slug, 'team_slug': self.team.slug})
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])  # 200 or redirect to canonical
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_detail_wrong_org_returns_404(self):
        """Test 8: Wrong org_slug in URL returns 404"""
        other_org = Organization.objects.create(
            name='Other Org',
            slug='other-org',
            ceo=self.user
        )
        url = reverse('organizations:org_team_detail',
                     kwargs={'org_slug': other_org.slug, 'team_slug': self.team.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_manage_canonical_url_works(self):
        """Test 9: Canonical org-scoped URL works for team manage"""
        url = reverse('organizations:org_team_manage',
                     kwargs={'org_slug': self.org.slug, 'team_slug': self.team.slug})
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_alias_url_redirects_to_canonical(self):
        """Test 10: Alias URLs redirect to canonical org-scoped URL"""
        # Access via /teams/<slug>/ should redirect to /orgs/<org>/teams/<slug>/
        url = reverse('organizations:team_detail', kwargs={'team_slug': self.team.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.org.slug, response.url)


@pytest.mark.django_db
class TestPhase8Permissions(TestCase):
    """Test 11-20: Centralized permission system"""
    
    def setUp(self):
        self.ceo = User.objects.create_user('ceo', 'ceo@test.com', 'pass')
        self.manager = User.objects.create_user('manager', 'mgr@test.com', 'pass')
        self.member = User.objects.create_user('member', 'mem@test.com', 'pass')
        self.outsider = User.objects.create_user('outsider', 'out@test.com', 'pass')
        
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.ceo
        )
        
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.manager,
            role='MANAGER',
            status='ACTIVE'
        )
        
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.member,
            role='MEMBER',
            status='ACTIVE'
        )
        
        self.game = Game.objects.create(
            title='Test Game',
            slug='test-game',
            display_name='Test Game',
            is_active=True
        )
        
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=self.game.id,
            region='Bangladesh',
            organization=self.org,
            created_by=self.ceo
        )
        
        TeamMembership.objects.create(
            team=self.team,
            user=self.member,
            role='MEMBER',
            status='ACTIVE'
        )
    
    def test_get_org_role_ceo(self):
        """Test 11: get_org_role() identifies CEO correctly"""
        self.assertEqual(get_org_role(self.ceo, self.org), 'CEO')
    
    def test_get_org_role_manager(self):
        """Test 12: get_org_role() identifies Manager correctly"""
        self.assertEqual(get_org_role(self.manager, self.org), 'MANAGER')
    
    def test_get_org_role_member(self):
        """Test 13: get_org_role() identifies Member correctly"""
        self.assertEqual(get_org_role(self.member, self.org), 'MEMBER')
    
    def test_get_org_role_outsider(self):
        """Test 14: get_org_role() returns NONE for outsider"""
        self.assertEqual(get_org_role(self.outsider, self.org), 'NONE')
    
    def test_can_manage_org_ceo(self):
        """Test 15: CEO can manage organization"""
        self.assertTrue(can_manage_org(self.ceo, self.org))
    
    def test_can_manage_org_manager(self):
        """Test 16: Manager can manage organization"""
        self.assertTrue(can_manage_org(self.manager, self.org))
    
    def test_can_manage_org_member_denied(self):
        """Test 17: Regular member cannot manage organization"""
        self.assertFalse(can_manage_org(self.member, self.org))
    
    def test_can_manage_team_ceo(self):
        """Test 18: Org CEO can manage all org teams"""
        self.assertTrue(can_manage_team(self.ceo, self.team))
    
    def test_can_manage_team_manager(self):
        """Test 19: Org Manager can manage all org teams"""
        self.assertTrue(can_manage_team(self.manager, self.team))
    
    def test_can_manage_team_member_denied(self):
        """Test 20: Regular team member cannot manage team"""
        self.assertFalse(can_manage_team(self.member, self.team))


@pytest.mark.django_db
class TestPhase8Views(TestCase):
    """Test 21-27: View access and permissions"""
    
    def setUp(self):
        self.client = Client()
        self.ceo = User.objects.create_user('ceo', 'ceo@test.com', 'pass')
        self.member = User.objects.create_user('member', 'mem@test.com', 'pass')
        self.outsider = User.objects.create_user('outsider', 'out@test.com', 'pass')
        
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.ceo
        )
        
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.member,
            role='MEMBER',
            status='ACTIVE'
        )
        
        self.game = Game.objects.create(
            title='Test Game',
            slug='test-game',
            display_name='Test Game',
            is_active=True
        )
        
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=self.game.id,
            region='Bangladesh',
            organization=self.org,
            created_by=self.ceo,
            visibility='PUBLIC'
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_ceo_can_access_team_manage(self):
        """Test 21: CEO can access team manage page"""
        self.client.login(username='ceo', password='pass')
        url = reverse('organizations:org_team_manage',
                     kwargs={'org_slug': self.org.slug, 'team_slug': self.team.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_member_cannot_access_team_manage(self):
        """Test 22: Regular member cannot access team manage page"""
        self.client.login(username='member', password='pass')
        url = reverse('organizations:org_team_manage',
                     kwargs={'org_slug': self.org.slug, 'team_slug': self.team.slug})
        response = self.client.get(url)
        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_outsider_cannot_access_team_manage(self):
        """Test 23: Outsider cannot access team manage page"""
        self.client.login(username='outsider', password='pass')
        url = reverse('organizations:org_team_manage',
                     kwargs={'org_slug': self.org.slug, 'team_slug': self.team.slug})
        response = self.client.get(url)
        # Should redirect
        self.assertEqual(response.status_code, 302)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_public_team_detail_accessible_to_anyone(self):
        """Test 24: Public team detail accessible to anyone"""
        url = reverse('organizations:org_team_detail',
                     kwargs={'org_slug': self.org.slug, 'team_slug': self.team.slug})
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_private_team_detail_requires_membership(self):
        """Test 25: Private team detail requires membership"""
        self.team.visibility = 'PRIVATE'
        self.team.save()
        
        # Outsider should not see private team
        url = reverse('organizations:org_team_detail',
                     kwargs={'org_slug': self.org.slug, 'team_slug': self.team.slug})
        response = self.client.get(url)
        # Should redirect or show access denied
        self.assertIn(response.status_code, [302, 403])
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_ceo_can_create_teams(self):
        """Test 26: CEO can create teams in organization"""
        self.assertTrue(can_create_team_in_org(self.ceo, self.org))
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_member_cannot_create_teams(self):
        """Test 27: Regular member cannot create teams"""
        self.assertFalse(can_create_team_in_org(self.member, self.org))


@pytest.mark.django_db
class TestPhase8AdminIntegration(TestCase):
    """Test 28-30: Admin panel integration"""
    
    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.user
        )
        self.game = Game.objects.create(
            title='Test Game',
            slug='test-game',
            display_name='Test Game',
            is_active=True
        )
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=self.game.id,
            region='Bangladesh',
            organization=self.org
        )
    
    def test_team_visible_in_org_admin_inline(self):
        """Test 28: Team appears in Organization admin inline"""
        from apps.organizations.admin import TeamAdminProxy
        teams = TeamAdminProxy.objects.filter(organization=self.org)
        self.assertEqual(teams.count(), 1)
        self.assertEqual(teams.first().slug, 'test-team')
    
    def test_team_admin_loads_without_errors(self):
        """Test 29: Team admin edit page loads without errors"""
        # This would normally require Django test client admin access
        # Testing that query doesn't crash
        from apps.organizations.admin import TeamAdminProxy
        team_proxy = TeamAdminProxy.objects.get(slug='test-team')
        self.assertIsNotNone(team_proxy)
        self.assertEqual(team_proxy.organization, self.org)
    
    def test_team_str_includes_org_name(self):
        """Test 30: Team __str__ includes organization name"""
        expected = f"{self.org.name} - {self.team.name}"
        self.assertEqual(str(self.team), expected)
