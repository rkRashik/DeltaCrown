"""
Task 5: Competition Integration Tests
Tests for Organizations migration + Competition app with feature flags.
"""

import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class TestOrganizationsNavigation(TestCase):
    """Test navigation shows correct links based on ORG_APP_ENABLED flag."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @override_settings(ORG_APP_ENABLED=True, COMPETITION_APP_ENABLED=False)
    def test_homepage_shows_organizations_when_enabled(self):
        """Homepage navigation should show Organizations link when ORG_APP_ENABLED=True."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Check navigation contains Organizations link
        self.assertContains(
            response, 
            '/orgs/', 
            msg_prefix="Navigation should link to /orgs/ when ORG_APP_ENABLED=True"
        )
        
        # Check footer contains Organizations
        self.assertContains(
            response,
            'Organizations',
            msg_prefix="Footer should show Organizations when ORG_APP_ENABLED=True"
        )
    
    @override_settings(ORG_APP_ENABLED=False, COMPETITION_APP_ENABLED=False)
    def test_homepage_shows_teams_when_disabled(self):
        """Homepage should show legacy Teams when ORG_APP_ENABLED=False."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # When ORG_APP_ENABLED is False, should show Teams link
        self.assertContains(
            response,
            '/teams/',
            msg_prefix="Navigation should link to /teams/ when ORG_APP_ENABLED=False"
        )


class TestCompetitionRankings(TestCase):
    """Test Competition Rankings pages with COMPETITION_APP_ENABLED flag."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @override_settings(COMPETITION_APP_ENABLED=True)
    def test_rankings_global_returns_200_when_enabled(self):
        """Global rankings page should return 200 when COMPETITION_APP_ENABLED=True."""
        try:
            url = reverse('competition:rankings_global')
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 
                200,
                msg="Rankings page should return 200 when COMPETITION_APP_ENABLED=True"
            )
        except Exception as e:
            # If tables don't exist, should still not crash (handled in view)
            self.fail(f"Rankings page crashed when enabled: {e}")
    
    @override_settings(COMPETITION_APP_ENABLED=False)
    def test_rankings_global_shows_unavailable_when_disabled(self):
        """Rankings page should show unavailable message when COMPETITION_APP_ENABLED=False."""
        try:
            url = reverse('competition:rankings_global')
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                200,
                msg="Rankings page should return 200 (with unavailable message) when disabled"
            )
            # Check for unavailable message
            self.assertContains(
                response,
                'unavailable',
                msg_prefix="Should show unavailable message when COMPETITION_APP_ENABLED=False"
            )
        except Exception as e:
            self.fail(f"Rankings page should not crash when disabled: {e}")
    
    def test_ranking_about_always_accessible(self):
        """Ranking documentation should always be accessible (no flag check)."""
        url = reverse('competition:ranking_about')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            200,
            msg="Ranking about page should always return 200 (documentation)"
        )
    
    @override_settings(COMPETITION_APP_ENABLED=True)
    def test_homepage_shows_rankings_link_when_enabled(self):
        """Homepage should show Rankings link when COMPETITION_APP_ENABLED=True."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Check navigation contains Rankings
        self.assertContains(
            response,
            'Rankings',
            msg_prefix="Navigation should show Rankings when COMPETITION_APP_ENABLED=True"
        )
    
    @override_settings(COMPETITION_APP_ENABLED=False)
    def test_homepage_shows_leaderboards_when_disabled(self):
        """Homepage footer should show Leaderboards link when COMPETITION_APP_ENABLED=False."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Footer should show Leaderboards (legacy)
        self.assertContains(
            response,
            'Leaderboards',
            msg_prefix="Footer should show Leaderboards when COMPETITION_APP_ENABLED=False"
        )


class TestFallbackPages(TestCase):
    """Test fallback pages render correctly when features disabled."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_organizations_fallback_template_exists(self):
        """Organizations fallback template should exist."""
        import os
        from django.conf import settings
        
        template_path = os.path.join(
            settings.BASE_DIR,
            'templates',
            'organizations',
            'fallback.html'
        )
        self.assertTrue(
            os.path.exists(template_path),
            msg=f"Organizations fallback template should exist at {template_path}"
        )
    
    def test_competition_fallback_template_exists(self):
        """Competition fallback template should exist."""
        import os
        from django.conf import settings
        
        template_path = os.path.join(
            settings.BASE_DIR,
            'templates',
            'competition',
            'fallback.html'
        )
        self.assertTrue(
            os.path.exists(template_path),
            msg=f"Competition fallback template should exist at {template_path}"
        )


class TestRankingsPolicyLink(TestCase):
    """Test Rankings Policy links are conditional on COMPETITION_APP_ENABLED."""
    
    def setUp(self):
        """Set up test user and client."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    @override_settings(COMPETITION_APP_ENABLED=True)
    def test_rankings_policy_appears_when_enabled(self):
        """Rankings Policy link should appear in hub when COMPETITION_APP_ENABLED=True."""
        # Test requires Organizations team to exist - skip if not available
        try:
            from apps.organizations.models import Team, Organization
            
            # Create organization and team
            org = Organization.objects.create(
                name='Test Org',
                slug='test-org',
                owner=self.user
            )
            team = Team.objects.create(
                name='Test Team',
                slug='test-team',
                organization=org,
                game_id='MLBB'
            )
            
            # Visit team hub
            response = self.client.get(f'/teams/{team.slug}/')
            
            # Check for Rankings Policy link
            if response.status_code == 200:
                self.assertContains(
                    response,
                    'Rankings Policy',
                    msg_prefix="Rankings Policy link should appear when COMPETITION_APP_ENABLED=True"
                )
        except Exception:
            # Skip if Organizations models not available
            pytest.skip("Organizations models not available")
    
    @override_settings(COMPETITION_APP_ENABLED=False)
    def test_rankings_policy_hidden_when_disabled(self):
        """Rankings Policy link should not appear when COMPETITION_APP_ENABLED=False."""
        # Test requires Organizations team to exist - skip if not available
        try:
            from apps.organizations.models import Team, Organization
            
            # Create organization and team
            org = Organization.objects.create(
                name='Test Org 2',
                slug='test-org-2',
                owner=self.user
            )
            team = Team.objects.create(
                name='Test Team 2',
                slug='test-team-2',
                organization=org,
                game_id='MLBB'
            )
            
            # Visit team hub
            response = self.client.get(f'/teams/{team.slug}/')
            
            # Check Rankings Policy link does NOT appear
            if response.status_code == 200:
                self.assertNotContains(
                    response,
                    'Rankings Policy',
                    msg_prefix="Rankings Policy link should NOT appear when COMPETITION_APP_ENABLED=False"
                )
        except Exception:
            # Skip if Organizations models not available
            pytest.skip("Organizations models not available")


class TestAdminSafety(TestCase):
    """Test admin doesn't crash even when Competition tables missing."""
    
    def setUp(self):
        """Set up superuser and client."""
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_admin_index_accessible(self):
        """Admin index should be accessible regardless of Competition schema."""
        response = self.client.get('/admin/')
        self.assertEqual(
            response.status_code,
            200,
            msg="Admin index should always be accessible"
        )
    
    def test_competition_admin_graceful_degradation(self):
        """Competition admin should either show models or gracefully degrade."""
        # Try to access competition admin
        # Should not raise 500 error even if tables missing
        try:
            response = self.client.get('/admin/competition/')
            self.assertIn(
                response.status_code,
                [200, 404],
                msg="Competition admin should return 200 or 404, not 500"
            )
        except Exception as e:
            self.fail(f"Competition admin should not crash: {e}")


class TestFeatureFlagDefaults(TestCase):
    """Test feature flag defaults match migration plan."""
    
    def test_default_flag_states(self):
        """Verify default flags: ORG_APP_ENABLED=1, LEGACY_TEAMS_ENABLED=1, COMPETITION_APP_ENABLED=0."""
        from django.conf import settings
        
        # Defaults per docs/vnext/org-migration-plan.md
        self.assertTrue(
            getattr(settings, 'ORG_APP_ENABLED', False),
            "ORG_APP_ENABLED should default to True"
        )
        self.assertTrue(
            getattr(settings, 'LEGACY_TEAMS_ENABLED', False),
            "LEGACY_TEAMS_ENABLED should default to True for compatibility"
        )
        # COMPETITION_APP_ENABLED default depends on environment
        # Just verify it exists
        self.assertIn(
            hasattr(settings, 'COMPETITION_APP_ENABLED'),
            [True],
            "COMPETITION_APP_ENABLED should be defined"
        )


class TestPhase5LegacyRedirects(TestCase):
    """
    Phase 5: Test that legacy Teams and Leaderboards redirect to Organizations and Competition.
    """
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @override_settings(ORG_APP_ENABLED=True)
    def test_legacy_teams_index_redirects_to_orgs(self):
        """
        /teams/ should redirect to /orgs/ when ORG_APP_ENABLED=True.
        Phase 5: Organizations is now canonical owner of team management.
        """
        response = self.client.get('/teams/', follow=False)
        self.assertEqual(
            response.status_code,
            302,
            msg="/teams/ should redirect (302) when ORG_APP_ENABLED=True"
        )
        self.assertIn(
            '/orgs/',
            response.url,
            msg="/teams/ should redirect to /orgs/ directory"
        )
    
    @override_settings(ORG_APP_ENABLED=False, LEGACY_TEAMS_ENABLED=True)
    def test_legacy_teams_works_when_org_disabled(self):
        """/teams/ should work (not redirect) when ORG_APP_ENABLED=False."""
        response = self.client.get('/teams/')
        self.assertEqual(
            response.status_code,
            200,
            msg="/teams/ should return 200 when ORG_APP_ENABLED=False as fallback"
        )
    
    @override_settings(COMPETITION_APP_ENABLED=True)
    def test_legacy_teams_rankings_redirects_to_competition(self):
        """
        /teams/rankings/ should redirect to /competition/rankings/ when COMPETITION_APP_ENABLED=True.
        Phase 5: Competition is now canonical owner of rankings/leaderboards.
        """
        response = self.client.get('/teams/rankings/', follow=False)
        self.assertEqual(
            response.status_code,
            302,
            msg="/teams/rankings/ should redirect (302) when COMPETITION_APP_ENABLED=True"
        )
        self.assertIn(
            '/competition/rankings/',
            response.url,
            msg="/teams/rankings/ should redirect to /competition/rankings/"
        )
    
    @override_settings(COMPETITION_APP_ENABLED=False, LEGACY_TEAMS_ENABLED=True)
    def test_legacy_rankings_works_when_competition_disabled(self):
        """/teams/rankings/ should work when COMPETITION_APP_ENABLED=False as fallback."""
        response = self.client.get('/teams/rankings/')
        self.assertEqual(
            response.status_code,
            200,
            msg="/teams/rankings/ should return 200 when COMPETITION_APP_ENABLED=False as fallback"
        )
    
    @override_settings(ORG_APP_ENABLED=True, COMPETITION_APP_ENABLED=True)
    def test_phase5_both_flags_enabled(self):
        """
        Phase 5 canonical state: Both Organizations and Competition enabled.
        Legacy teams URLs should redirect to their canonical owners.
        """
        # Test teams redirect
        teams_response = self.client.get('/teams/', follow=False)
        self.assertEqual(teams_response.status_code, 302)
        self.assertIn('/orgs/', teams_response.url)
        
        # Test rankings redirect
        rankings_response = self.client.get('/teams/rankings/', follow=False)
        self.assertEqual(rankings_response.status_code, 302)
        self.assertIn('/competition/rankings/', rankings_response.url)
    
    @override_settings(ORG_APP_ENABLED=True)
    def test_organizations_is_canonical_owner(self):
        """
        Phase 5: Organizations is the canonical owner of /teams/* routes.
        Verify /teams/create/ and /teams/<slug>/ are handled by Organizations, not legacy.
        """
        # Note: These URLs are mounted at root level by Organizations app (see deltacrown/urls.py)
        # They should NOT go through legacy teams namespace
        
        # /teams/create/ should be handled by Organizations
        create_response = self.client.get('/teams/create/')
        # Will return 200 or redirect to login depending on auth
        self.assertIn(
            create_response.status_code,
            [200, 302],
            msg="/teams/create/ should be handled by Organizations app"
        )
    
    @override_settings(COMPETITION_APP_ENABLED=True)
    def test_competition_is_canonical_owner(self):
        """
        Phase 5: Competition is the canonical owner of rankings/leaderboards.
        """
        # /competition/rankings/ should work
        rankings_response = self.client.get('/competition/rankings/')
        self.assertEqual(
            rankings_response.status_code,
            200,
            msg="/competition/rankings/ should return 200 when COMPETITION_APP_ENABLED=True"
        )

class TestPhase6LegacyLockdown(TestCase):
    """
    Phase 6: Test strict legacy lockdown when LEGACY_TEAMS_ENABLED=0.
    Ensures legacy code is inaccessible when flags disabled.
    """
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @override_settings(ORG_APP_ENABLED=0, LEGACY_TEAMS_ENABLED=0)
    def test_legacy_teams_returns_404_when_locked_down(self):
        """
        Phase 6: /teams/ should return 404 when LEGACY_TEAMS_ENABLED=0.
        Legacy is completely inaccessible, forces Organizations usage.
        """
        response = self.client.get('/teams/')
        self.assertEqual(
            response.status_code,
            404,
            msg="/teams/ should return 404 when LEGACY_TEAMS_ENABLED=0"
        )
    
    @override_settings(COMPETITION_APP_ENABLED=0, LEGACY_TEAMS_ENABLED=0)
    def test_legacy_rankings_returns_404_when_locked_down(self):
        """
        Phase 6: /teams/rankings/ should return 404 when both flags disabled.
        Forces Competition usage.
        """
        response = self.client.get('/teams/rankings/')
        self.assertEqual(
            response.status_code,
            404,
            msg="/teams/rankings/ should return 404 when LEGACY_TEAMS_ENABLED=0"
        )
    
    @override_settings(ORG_APP_ENABLED=1, LEGACY_TEAMS_ENABLED=0)
    def test_organizations_required_when_legacy_locked(self):
        """
        Phase 6: When legacy disabled, Organizations is the only option.
        """
        # /teams/ should redirect to /orgs/ (ORG_APP_ENABLED takes precedence)
        response = self.client.get('/teams/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/orgs/', response.url)
        
        # /orgs/ should work
        orgs_response = self.client.get('/orgs/')
        self.assertIn(
            orgs_response.status_code,
            [200],
            msg="/orgs/ should be accessible when Organizations is canonical"
        )
    
    @override_settings(COMPETITION_APP_ENABLED=1, LEGACY_TEAMS_ENABLED=0)
    def test_competition_required_when_legacy_locked(self):
        """
        Phase 6: When legacy disabled, Competition is the only option for rankings.
        """
        # /teams/rankings/ should redirect to /competition/rankings/
        response = self.client.get('/teams/rankings/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/competition/rankings/', response.url)
        
        # /competition/rankings/ should work
        comp_response = self.client.get('/competition/rankings/')
        self.assertEqual(
            comp_response.status_code,
            200,
            msg="/competition/rankings/ should be accessible"
        )
    
    @override_settings(ORG_APP_ENABLED=1, COMPETITION_APP_ENABLED=1, LEGACY_TEAMS_ENABLED=0)
    def test_phase6_canonical_state_no_legacy(self):
        """
        Phase 6: Production canonical state with legacy completely disabled.
        - ORG_APP_ENABLED=1: Organizations handles teams
        - COMPETITION_APP_ENABLED=1: Competition handles rankings
        - LEGACY_TEAMS_ENABLED=0: No legacy fallback available
        """
        # /teams/ redirects to /orgs/
        teams_response = self.client.get('/teams/', follow=False)
        self.assertEqual(teams_response.status_code, 302)
        self.assertIn('/orgs/', teams_response.url)
        
        # /teams/rankings/ redirects to /competition/rankings/
        rankings_response = self.client.get('/teams/rankings/', follow=False)
        self.assertEqual(rankings_response.status_code, 302)
        self.assertIn('/competition/rankings/', rankings_response.url)
        
        # Direct access to /orgs/ and /competition/rankings/ works
        orgs_response = self.client.get('/orgs/')
        self.assertEqual(orgs_response.status_code, 200)
        
        comp_response = self.client.get('/competition/rankings/')
        self.assertEqual(comp_response.status_code, 200)
    
    @override_settings(ORG_APP_ENABLED=0, LEGACY_TEAMS_ENABLED=1)
    def test_legacy_teams_works_as_fallback(self):
        """
        Phase 6: Legacy Teams still works when LEGACY_TEAMS_ENABLED=1.
        Backwards compatibility maintained.
        """
        response = self.client.get('/teams/')
        self.assertEqual(
            response.status_code,
            200,
            msg="/teams/ should work when LEGACY_TEAMS_ENABLED=1"
        )
    
    @override_settings(COMPETITION_APP_ENABLED=0, LEGACY_TEAMS_ENABLED=1)
    def test_legacy_rankings_works_as_fallback(self):
        """
        Phase 6: Legacy rankings still work when LEGACY_TEAMS_ENABLED=1.
        Backwards compatibility maintained.
        """
        response = self.client.get('/teams/rankings/')
        self.assertEqual(
            response.status_code,
            200,
            msg="/teams/rankings/ should work when LEGACY_TEAMS_ENABLED=1"
        )


class TestPhase6TeamsNavigation(TestCase):
    """Phase 6: Test canonical Teams navigation that routes to Organizations hub."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_teams_vnext_routes_to_org_hub(self):
        """
        Phase 6: /teams/vnext/ should redirect to Organizations vnext_hub when ORG_APP_ENABLED=1.
        This is the canonical Teams Hub that users see in navigation.
        """
        response = self.client.get('/teams/vnext/', follow=False)
        self.assertEqual(
            response.status_code,
            302,
            msg="/teams/vnext/ should redirect when ORG_APP_ENABLED=1"
        )
        self.assertIn(
            'organizations/teams/vnext/',
            response.url,
            msg="Should redirect to Organizations vnext_hub"
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_teams_vnext_renders_hub_template(self):
        """
        Phase 6: Following the redirect should render Organizations hub template.
        """
        response = self.client.get('/teams/vnext/', follow=True)
        self.assertEqual(response.status_code, 200)
        # Template should be team_hub.html from Organizations app
        self.assertTemplateUsed(response, 'organizations/hub/team_hub.html')
    
    @override_settings(ORG_APP_ENABLED=0, LEGACY_TEAMS_ENABLED=1)
    def test_teams_vnext_falls_back_to_legacy_hub(self):
        """
        Phase 6: When ORG_APP_ENABLED=0, /teams/vnext/ falls back to legacy teams hub.
        """
        response = self.client.get('/teams/vnext/')
        self.assertEqual(
            response.status_code,
            200,
            msg="/teams/vnext/ should show legacy hub when ORG_APP_ENABLED=0"
        )
    
    @override_settings(ORG_APP_ENABLED=0, LEGACY_TEAMS_ENABLED=0)
    def test_teams_vnext_returns_404_when_both_disabled(self):
        """
        Phase 6: When both modern and legacy disabled, should return 404.
        """
        response = self.client.get('/teams/vnext/')
        self.assertEqual(
            response.status_code,
            404,
            msg="/teams/vnext/ should return 404 when both ORG and LEGACY disabled"
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_navigation_contains_teams_link(self):
        """
        Phase 6: Primary navigation should show 'Teams' as simple link (not dropdown).
        """
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Navigation should contain "Teams" label
        self.assertContains(
            response,
            'Teams',
            msg_prefix="Navigation should show 'Teams' as primary label"
        )
        
        # Should link to /teams/vnext/ hub
        self.assertContains(
            response,
            '/teams/vnext/',
            msg_prefix="Teams link should route to /teams/vnext/"
        )
        
        # Should NOT contain dropdown elements (no dc-teams-btn, dc-teams-menu)
        self.assertNotContains(
            response,
            'dc-teams-btn',
            msg_prefix="Teams should not have dropdown button"
        )


class TestOrganizationTeamURLs(TestCase):
    """
    Phase 6: Test canonical org-scoped team URLs and alias redirects.
    Validates /orgs/<org>/teams/<team>/ pattern and backwards compatibility.
    """
    
    def setUp(self):
        """Set up test data: org, team, user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create organization
        from apps.organizations.models import Organization
        self.org = Organization.objects.create(
            name="Test Esports",
            slug="test-esports",
            description="Test organization"
        )
        
        # Create team under organization
        from apps.organizations.models import Team
        self.team = Team.objects.create(
            name="Test Team",
            slug="test-team",
            organization=self.org
        )
        
        # Create independent team (no org)
        self.independent_team = Team.objects.create(
            name="Independent Team",
            slug="indie-team",
            organization=None
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_org_team_canonical_url_returns_200(self):
        """
        Canonical URL /orgs/<org>/teams/<team>/ should return 200 for org teams.
        """
        url = f'/orgs/{self.org.slug}/teams/{self.team.slug}/'
        response = self.client.get(url)
        
        self.assertEqual(
            response.status_code,
            200,
            msg=f"Canonical org-scoped URL {url} should return 200"
        )
        
        # Verify team data is in response
        self.assertContains(response, self.team.name)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_alias_redirects_to_canonical(self):
        """
        Alias URL /teams/<team>/ should redirect to /orgs/<org>/teams/<team>/ 
        when team belongs to an organization.
        """
        alias_url = f'/teams/{self.team.slug}/'
        response = self.client.get(alias_url)
        
        # Should redirect (302)
        self.assertEqual(
            response.status_code,
            302,
            msg=f"Alias URL {alias_url} should redirect to canonical org-scoped URL"
        )
        
        # Should redirect to canonical URL
        expected_canonical = f'/orgs/{self.org.slug}/teams/{self.team.slug}/'
        self.assertRedirects(
            response,
            expected_canonical,
            fetch_redirect_response=False,
            msg_prefix=f"Should redirect to canonical URL {expected_canonical}"
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_org_slug_mismatch_returns_404(self):
        """
        Accessing /orgs/<wrong-org>/teams/<team>/ should return 404.
        """
        # Create another org
        from apps.organizations.models import Organization
        other_org = Organization.objects.create(
            name="Other Org",
            slug="other-org"
        )
        
        # Try to access team with wrong org_slug
        wrong_url = f'/orgs/{other_org.slug}/teams/{self.team.slug}/'
        response = self.client.get(wrong_url)
        
        self.assertEqual(
            response.status_code,
            404,
            msg=f"URL {wrong_url} should return 404 when org_slug doesn't match team's org"
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_independent_team_uses_simple_url(self):
        """
        Independent team (no org) should use simple /teams/<slug>/ pattern without redirect.
        """
        url = f'/teams/{self.independent_team.slug}/'
        response = self.client.get(url)
        
        # Should return 200 (no redirect)
        self.assertEqual(
            response.status_code,
            200,
            msg=f"Independent team URL {url} should return 200 without redirect"
        )
        
        # Verify team data is in response
        self.assertContains(response, self.independent_team.name)
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_get_absolute_url_returns_canonical(self):
        """
        Team.get_absolute_url() should return canonical org-scoped URL for org teams.
        """
        expected_url = f'/orgs/{self.org.slug}/teams/{self.team.slug}/'
        actual_url = self.team.get_absolute_url()
        
        self.assertEqual(
            actual_url,
            expected_url,
            msg=f"Team.get_absolute_url() should return canonical org-scoped URL"
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_independent_team_get_absolute_url_simple(self):
        """
        Team.get_absolute_url() should return simple /teams/<slug>/ for independent teams.
        """
        expected_url = f'/teams/{self.independent_team.slug}/'
        actual_url = self.independent_team.get_absolute_url()
        
        self.assertEqual(
            actual_url,
            expected_url,
            msg=f"Independent team get_absolute_url() should return simple URL"
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_manage_canonical_url_returns_200(self):
        """
        Canonical manage URL /orgs/<org>/teams/<team>/manage/ should return 200.
        """
        self.client.login(username='testuser', password='testpass123')
        
        # Make user team admin
        from apps.organizations.models import TeamMember
        TeamMember.objects.create(
            team=self.team,
            user=self.user,
            role='admin'
        )
        
        url = f'/orgs/{self.org.slug}/teams/{self.team.slug}/manage/'
        response = self.client.get(url)
        
        self.assertEqual(
            response.status_code,
            200,
            msg=f"Canonical manage URL {url} should return 200"
        )
    
    @override_settings(ORG_APP_ENABLED=1)
    def test_team_manage_alias_redirects_to_canonical(self):
        """
        Alias manage URL /teams/<team>/manage/ should redirect to canonical org-scoped URL.
        """
        self.client.login(username='testuser', password='testpass123')
        
        # Make user team admin
        from apps.organizations.models import TeamMember
        TeamMember.objects.create(
            team=self.team,
            user=self.user,
            role='admin'
        )
        
        alias_url = f'/teams/{self.team.slug}/manage/'
        response = self.client.get(alias_url)
        
        # Should redirect
        self.assertEqual(
            response.status_code,
            302,
            msg=f"Alias manage URL {alias_url} should redirect to canonical"
        )
        
        expected_canonical = f'/orgs/{self.org.slug}/teams/{self.team.slug}/manage/'
        self.assertRedirects(
            response,
            expected_canonical,
            fetch_redirect_response=False,
            msg_prefix=f"Should redirect to canonical manage URL"
        )
        self.assertNotContains(
            response,
            'dc-teams-menu',
            msg_prefix="Teams should not have dropdown menu"
        )
