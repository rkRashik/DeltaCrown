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


class DesignFoundationTests(TestCase):
    BANNED = ("Secure Slot", "View Intel", "Initialize Event", "Tournament Intel", "Runtime Status",
              "Rewards Engine", "Ecosystem Ticker", "Radar Clear", "Command Center", "Load More Intel")

    def test_foundation_stylesheet_ships_and_is_loaded(self):
        self.assertIsNotNone(finders.find("ownlobby/foundation.css"))
        html = self.client.get("/about/").content.decode()
        self.assertIn("ownlobby/foundation.css", html)
        css = open(finders.find("ownlobby/foundation.css"), encoding="utf-8").read()
        for cls in (".ol-btn--primary", ".ol-btn--secondary", ".ol-btn--ghost", ".ol-btn--danger",
                    ".ol-badge--success", ".ol-badge--live", ".ol-empty"):
            self.assertIn(cls, css)

    def test_touched_templates_use_plain_wording(self):
        from pathlib import Path
        from django.conf import settings
        for rel in ("tournaments/list.html", "tournaments/detailPages/detail.html",
                    "tournaments/detailPages/_detail_mobile.html", "partials/primary_navigation.html",
                    "partials/nav_browse_links.html"):
            text = (Path(settings.BASE_DIR) / "templates" / rel).read_text(encoding="utf-8")
            for phrase in self.BANNED:
                self.assertNotIn(phrase, text, "%s still contains %r" % (rel, phrase))

    def test_tournament_list_uses_shared_buttons_and_plain_empty_state(self):
        html = self.client.get("/tournaments/").content.decode()
        self.assertIn("ol-btn", html)
        self.assertIn("No tournaments found", html)
        self.assertNotIn("Clear Scanners", html)


class HomepageBatchBTests(TestCase):
    def test_home_does_not_overclaim_features_or_games(self):
        html = self.client.get("/").content.decode()
        for claim in ("Free Fire", "CS2", "Resets daily", "Always open", "Earns CP", "always-on", "queue, play"):
            self.assertNotIn(claim, html)
        self.assertIn("Competitive Hub", html)
        # the four modes are presented once, as one hub - not as four separate links
        self.assertLessEqual(html.count('href="/dashboard/competitive/"'), 8)
        self.assertNotIn("Operations console", html)
        self.assertNotIn(">Store<", html)

    def test_home_uses_one_points_name(self):
        html = self.client.get("/").content.decode()
        self.assertNotIn("Crown Pts", html)
        self.assertNotRegex(html, r">\s*[0-9,]+ CP\+?\s*<")
