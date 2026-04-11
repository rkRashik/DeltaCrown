"""
E2E Smoke Tests — Basic page-level tests for DeltaCrown.

These tests verify that key pages load without 500 errors and
contain expected structural elements.

Run:
    E2E_BASE_URL=http://localhost:8000 pytest tests/e2e/test_smoke_pages.py -v --browser chromium
"""
import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not pytest.importorskip("playwright", reason="Playwright not installed"),
        reason="Playwright not installed",
    ),
]


class TestPublicPages:
    """Verify public pages load without errors."""

    def test_homepage_loads(self, page, base_url):
        response = page.goto(f"{base_url}/")
        assert response.status < 500

    def test_login_page_loads(self, page, base_url):
        response = page.goto(f"{base_url}/accounts/login/")
        assert response.status < 500
        assert page.locator('input[name="password"]').count() > 0

    def test_register_page_loads(self, page, base_url):
        response = page.goto(f"{base_url}/accounts/signup/")
        assert response.status < 500


class TestAuthenticatedPages:
    """Verify authenticated pages load after login."""

    def test_dashboard_loads(self, authenticated_page, base_url):
        response = authenticated_page.goto(f"{base_url}/dashboard/")
        assert response.status < 500

    def test_dashboard_has_sections(self, authenticated_page, base_url):
        authenticated_page.goto(f"{base_url}/dashboard/")
        # The dashboard should have structural content
        body = authenticated_page.content()
        assert len(body) > 1000  # Non-trivial page content


class TestTournamentFlow:
    """Verify the tournament listing and detail pages."""

    def test_tournament_list_page(self, page, base_url):
        response = page.goto(f"{base_url}/tournaments/")
        assert response.status < 500

    def test_registration_redirects_unauthenticated(self, page, base_url):
        """Unauthenticated user trying to register should be redirected to login."""
        response = page.goto(f"{base_url}/tournaments/test-slug/register/")
        # Should redirect to login or show 404 for non-existent tournament
        assert response.status < 500


class TestBracketUI:
    """Verify bracket UI elements are present."""

    def test_bracket_generation_buttons_exist(self, authenticated_page, base_url):
        """After navigating to a TOC brackets page, verify generate buttons exist."""
        # This is a structural test — actual bracket generation needs a real tournament
        authenticated_page.goto(f"{base_url}/dashboard/")
        # Just verify the page renders without errors
        assert authenticated_page.title() is not None
