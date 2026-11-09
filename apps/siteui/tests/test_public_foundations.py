"""Public-site foundation regressions: links, branding, landmarks, dev-route exposure."""
import re

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import TestCase, override_settings

from deltacrown.branding import BRAND


def _hrefs(html):
    return re.findall(r'href="([^"]*)"', html)


class PublicBrandingContactTests(TestCase):
    def test_support_email_and_youtube_defaults(self):
        self.assertEqual(BRAND["support_email"], "support@ownlobby.com")
        self.assertEqual(BRAND["social"]["youtube"], "")

    def test_contact_page_shows_official_email_only(self):
        html = self.client.get("/contact/").content.decode()
        self.assertIn("support@ownlobby.com", html)
        self.assertNotIn("deltacrownhq@gmail.com", html)

    def test_footer_hides_unverified_and_unready_entries(self):
        html = render_to_string("partials/footer_modern.html", {"brand": BRAND})
        self.assertNotIn("youtube", html.lower())
        self.assertNotIn("/crownstore/", html)
        self.assertNotIn("<form", html)
        self.assertNotIn("ewsletter", html)
        # Valid configured socials stay
        self.assertIn(BRAND["social"]["facebook"], html)
        self.assertIn(BRAND["social"]["instagram"], html)


class PublicNavigationTests(TestCase):
    def test_home_has_no_dead_public_destinations(self):
        hrefs = _hrefs(self.client.get("/").content.decode())
        for dead in ("/games/", "/support/", "/support/rules/", "/support/faq/",
                     "/dashboard/showdown/", "/dashboard/missions/", "/dashboard/bounty/", "/dashboard/dropzone/"):
            self.assertNotIn(dead, hrefs)
        self.assertNotIn("/crownstore/", hrefs)
        self.assertFalse([h for h in hrefs if "DeltaCrownGG" in h])

    def test_navigation_uses_canonical_auth_urls_and_hides_store(self):
        html = self.client.get("/tournaments/").content.decode()
        nav = html[html.index('id="dc-navbar"'):html.index('id="dc-mobile-drawer"')]
        self.assertNotIn("/crownstore/", nav)
        self.assertIn('href="/account/login/"', nav)
        self.assertNotIn("/accounts/login/", html)
        self.assertNotIn("/accounts/signup/", html)

    def test_mobile_drawer_lists_public_destinations_for_visitors(self):
        html = self.client.get("/about/").content.decode()
        drawer = html[html.index('id="dc-mobile-drawer"'):html.index('id="dc-backdrop"')]
        self.assertIn('role="dialog"', drawer)
        self.assertIn(" inert", html[html.index('id="dc-mobile-drawer"'):][:200])
        for href in ("/tournaments/", "/teams/", "/competition/rankings/", "/community/", "/arena/",
                     "/about/", "/faq/", "/rules/", "/contact/"):
            self.assertIn('href="%s"' % href, drawer)
        self.assertIn("data-nav-search", drawer)
        self.assertNotIn("/crownstore/", drawer)

    def test_pages_render_a_single_main_landmark(self):
        for path in ("/about/", "/faq/", "/contact/", "/rules/", "/terms/", "/privacy/", "/community/", "/arena/"):
            html = self.client.get(path).content.decode()
            self.assertEqual(len(re.findall(r"<main\b", html)), 1, path)


class TeamBannerFallbackTests(TestCase):
    def test_team_banner_fallback_points_to_an_existing_static_asset(self):
        from apps.organizations.services.team_detail_context import FALLBACK_URLS
        url = FALLBACK_URLS["team_banner"]
        self.assertTrue(url.startswith("/static/"))
        self.assertIsNotNone(finders.find(url[len("/static/"):]), url)


@override_settings(DEBUG=False)
class DevRouteExposureTests(TestCase):
    paths = ("/ui/", "/favicon-test/", "/test-game-assets/")

    def test_anonymous_and_regular_users_get_404(self):
        for path in self.paths:
            self.assertEqual(self.client.get(path).status_code, 404, path)
        user = get_user_model().objects.create_user("plain_user", "plain@example.test", "pw-12345-x")
        self.client.force_login(user)
        for path in self.paths:
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_staff_can_still_open_internal_qa_pages(self):
        staff = get_user_model().objects.create_superuser("qa_staff", "qa@example.test", "pw-12345-x")
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/favicon-test/").status_code, 200)
        self.assertEqual(self.client.get("/ui/").status_code, 200)
