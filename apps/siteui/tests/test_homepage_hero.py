"""Tests for the homepage hero + outro context resolver.

Two test layers:
  - HeroUnit*     : fully mocked, no DB required
  - HeroViewTests : integration via Django test client (needs DB)

Run unit tests (no DB):
    python -c "
    import os, django
    os.environ['DJANGO_SETTINGS_MODULE']='deltacrown.settings'
    django.setup()
    import unittest
    from apps.siteui.tests.test_homepage_hero import *
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [HeroGuestTests, HeroOnboardingTests, HeroPendingTests,
                HeroActiveMatchTests, HeroOpsTests, HeroNoTeamTests,
                HeroTeamManagerTests, HeroTeamReadyTests, HeroDefaultTests,
                HeroPriorityOrderTests, HeroURLSafetyTests,
                HeroOutroTests, HeroOutroNeverCreateAccount,
                HeroRotationTests]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    unittest.TextTestRunner(verbosity=2).run(suite)
    "

Run integration tests (requires connected DB):
    python manage.py test apps.siteui.tests.test_homepage_hero.HeroViewTests --keepdb

Run everything:
    python manage.py test apps.siteui.tests.test_homepage_hero --keepdb
"""
from unittest.mock import MagicMock, patch
from unittest import TestCase as PureTestCase

from django.test import TestCase
import apps.siteui.homepage_hero as hh


# ── Test helpers ───────────────────────────────────────────────────────────

def _anon():
    u = MagicMock(); u.is_authenticated = False; return u

def _auth(username="player1"):
    u = MagicMock(); u.is_authenticated = True; u.username = username; return u

def _team(slug="alpha", name="Alpha Squad", is_manager=True):
    t = MagicMock(); t.name = name; t.slug = slug
    return {
        "team_ids":     [1],
        "is_manager":   is_manager,
        "primary_team": t,
        "team_url":     f"/teams/{slug}/{'manage/' if is_manager else ''}",
    }


# ══════════════════════════════════════════════════════════════════════════
#  UNIT TESTS — fully mocked, no DB
# ══════════════════════════════════════════════════════════════════════════

class HeroGuestTests(PureTestCase):
    def _ctx(self): return hh.get_home_hero_context(_anon())

    def test_mode(self):            self.assertEqual(self._ctx()["mode"], "guest")
    def test_create_account_label(self): self.assertIn("Create your account", self._ctx()["primary_cta_label"])
    def test_signup_url(self):       self.assertIn("/account/signup/", self._ctx()["primary_cta_url"])
    def test_secondary_explore(self): self.assertIn("tournament", self._ctx()["secondary_cta_label"].lower())
    def test_no_chips(self):         self.assertIsNone(self._ctx()["hero_chips"])
    def test_subcopy_key_phrase(self): self.assertIn("esports identity", self._ctx()["subcopy"])
    # Outro
    def test_outro_create_account(self): self.assertIn("Create your account", self._ctx()["outro_primary_cta_label"])
    def test_outro_watch_live(self): self.assertIn("Watch live", self._ctx()["outro_secondary_cta_label"])
    def test_outro_subcopy_is_none(self): self.assertIsNone(self._ctx()["outro_subcopy"])


class HeroOnboardingTests(PureTestCase):
    def _ctx(self):
        u = _auth("newbie")
        with patch.object(hh, "_is_profile_incomplete", return_value=True):
            return hh.get_home_hero_context(u)

    def test_mode(self):              self.assertEqual(self._ctx()["mode"], "onboarding")
    def test_primary_cta(self):       self.assertIn("Complete profile", self._ctx()["primary_cta_label"])
    def test_url(self):               self.assertIn("/me/settings/", self._ctx()["primary_cta_url"])
    def test_not_create_account(self): self.assertNotIn("Create your account", self._ctx()["primary_cta_label"])
    # Outro
    def test_outro_complete_profile(self): self.assertIn("Complete", self._ctx()["outro_primary_cta_label"])
    def test_outro_not_create_account(self): self.assertNotIn("Create your account", self._ctx()["outro_primary_cta_label"])
    def test_outro_subcopy_set(self): self.assertIsNotNone(self._ctx()["outro_subcopy"])


class HeroPendingTests(PureTestCase):
    def _ctx(self, label="check-in required"):
        u = _auth()
        pending = {"url": "/tournaments/slug/hub/", "label": label}
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=pending):
            return hh.get_home_hero_context(u)

    def test_mode(self):             self.assertEqual(self._ctx()["mode"], "pending_action")
    def test_primary_cta(self):      self.assertIn("Resolve action", self._ctx()["primary_cta_label"])
    def test_url_is_match(self):     self.assertIn("/hub/", self._ctx()["primary_cta_url"])
    def test_secondary_ops(self):    self.assertIn("operation", self._ctx()["secondary_cta_label"].lower())
    def test_not_create_account(self): self.assertNotIn("Create your account", self._ctx()["primary_cta_label"])
    def test_dispute_label(self):    self.assertEqual(self._ctx("dispute active")["mode"], "pending_action")
    # Outro
    def test_outro_resolve(self):    self.assertIn("Resolve", self._ctx()["outro_primary_cta_label"])
    def test_outro_not_create(self): self.assertNotIn("Create your account", self._ctx()["outro_primary_cta_label"])
    def test_outro_subcopy(self):    self.assertIn("step", self._ctx()["outro_subcopy"])


class HeroActiveMatchTests(PureTestCase):
    def _ctx(self):
        u = _auth()
        match = {"url": "/tournaments/cup/hub/", "name": "Test Cup 2026"}
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=None), \
             patch.object(hh, "_get_active_match", return_value=match):
            return hh.get_home_hero_context(u)

    def test_mode(self):             self.assertEqual(self._ctx()["mode"], "active_match")
    def test_primary_cta(self):      self.assertIn("match room", self._ctx()["primary_cta_label"].lower())
    def test_secondary_tournaments(self): self.assertIn("tournament", self._ctx()["secondary_cta_label"].lower())
    def test_not_create_account(self): self.assertNotIn("Create your account", self._ctx()["primary_cta_label"])
    # Outro
    def test_outro_match_room(self): self.assertIn("match room", self._ctx()["outro_primary_cta_label"].lower())
    def test_outro_subcopy(self):    self.assertIn("match", self._ctx()["outro_subcopy"].lower())


class HeroOpsTests(PureTestCase):
    def _ctx(self):
        u = _auth()
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=None), \
             patch.object(hh, "_get_active_match", return_value=None), \
             patch.object(hh, "_has_ops", return_value=True):
            return hh.get_home_hero_context(u)

    def test_mode(self):             self.assertEqual(self._ctx()["mode"], "operations")
    def test_primary_cta(self):      self.assertIn("operation", self._ctx()["primary_cta_label"].lower())
    def test_primary_url(self):      self.assertIn("/dashboard/competitive/", self._ctx()["primary_cta_url"])
    # Outro
    def test_outro_ops(self):        self.assertIn("operation", self._ctx()["outro_primary_cta_label"].lower())
    def test_outro_subcopy(self):    self.assertIn("operations", self._ctx()["outro_subcopy"].lower())


class HeroNoTeamTests(PureTestCase):
    def _ctx(self):
        u = _auth()
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=None), \
             patch.object(hh, "_get_active_match", return_value=None), \
             patch.object(hh, "_has_ops", return_value=False), \
             patch.object(hh, "_get_team_info", return_value=None):
            return hh.get_home_hero_context(u)

    def test_mode(self):             self.assertEqual(self._ctx()["mode"], "no_team")
    def test_primary_cta(self):      self.assertIn("Create a team", self._ctx()["primary_cta_label"])
    def test_url(self):              self.assertIn("/teams/create/", self._ctx()["primary_cta_url"])
    def test_secondary_tournaments(self): self.assertIn("tournament", self._ctx()["secondary_cta_label"].lower())
    def test_not_create_account(self): self.assertNotIn("Create your account", self._ctx()["primary_cta_label"])
    # Outro
    def test_outro_create_team(self): self.assertIn("team", self._ctx()["outro_primary_cta_label"].lower())
    def test_outro_not_create_account(self): self.assertNotIn("Create your account", self._ctx()["outro_primary_cta_label"])
    def test_outro_subcopy(self):    self.assertIn("roster", self._ctx()["outro_subcopy"].lower())


class HeroTeamManagerTests(PureTestCase):
    def _ctx(self):
        u = _auth()
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=None), \
             patch.object(hh, "_get_active_match", return_value=None), \
             patch.object(hh, "_has_ops", return_value=False), \
             patch.object(hh, "_get_team_info", return_value=_team()):
            return hh.get_home_hero_context(u)

    def test_mode(self):             self.assertEqual(self._ctx()["mode"], "team_manager")
    def test_primary_cta(self):      self.assertIn("Manage roster", self._ctx()["primary_cta_label"])
    def test_url_manage(self):       self.assertIn("/manage/", self._ctx()["primary_cta_url"])
    def test_secondary_events(self): self.assertIn("event", self._ctx()["secondary_cta_label"].lower())
    # Outro
    def test_outro_manage(self):     self.assertIn("Manage roster", self._ctx()["outro_primary_cta_label"])
    def test_outro_not_create(self): self.assertNotIn("Create your account", self._ctx()["outro_primary_cta_label"])
    def test_outro_subcopy(self):    self.assertIn("roster", self._ctx()["outro_subcopy"].lower())


class HeroTeamReadyTests(PureTestCase):
    def _ctx(self):
        u = _auth()
        tc = _team(is_manager=False)
        tc["team_url"] = "/teams/alpha/"
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=None), \
             patch.object(hh, "_get_active_match", return_value=None), \
             patch.object(hh, "_has_ops", return_value=False), \
             patch.object(hh, "_get_team_info", return_value=tc), \
             patch.object(hh, "_has_active_reg", return_value=False):
            return hh.get_home_hero_context(u)

    def test_mode(self):             self.assertEqual(self._ctx()["mode"], "team_ready")
    def test_primary_events(self):   self.assertIn("event", self._ctx()["primary_cta_label"].lower())
    def test_secondary_manage(self): self.assertIn("team", self._ctx()["secondary_cta_label"].lower())
    # Outro
    def test_outro_register(self):   self.assertIn("ournament", self._ctx()["outro_primary_cta_label"])
    def test_outro_subcopy(self):    self.assertIsNotNone(self._ctx()["outro_subcopy"])


class HeroDefaultTests(PureTestCase):
    def _ctx(self):
        u = _auth("veteran")
        tc = _team(is_manager=False); tc["team_url"] = "/teams/gamma/"
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=None), \
             patch.object(hh, "_get_active_match", return_value=None), \
             patch.object(hh, "_has_ops", return_value=False), \
             patch.object(hh, "_get_team_info", return_value=tc), \
             patch.object(hh, "_has_active_reg", return_value=True):
            return hh.get_home_hero_context(u)

    def test_mode(self):             self.assertEqual(self._ctx()["mode"], "default")
    def test_primary_dashboard(self): self.assertIn("dashboard", self._ctx()["primary_cta_label"].lower())
    def test_url_dashboard(self):    self.assertIn("/dashboard/", self._ctx()["primary_cta_url"])
    def test_secondary_arena(self):  self.assertIn("arena", self._ctx()["secondary_cta_label"].lower())
    def test_not_create_account(self): self.assertNotIn("Create your account", self._ctx()["primary_cta_label"])
    def test_subcopy_crown(self):    self.assertIn("Crown", self._ctx()["subcopy"])
    # Outro
    def test_outro_dashboard(self):  self.assertIn("dashboard", self._ctx()["outro_primary_cta_label"].lower())
    def test_outro_not_create(self): self.assertNotIn("Create your account", self._ctx()["outro_primary_cta_label"])
    def test_outro_subcopy_crown(self): self.assertIn("Crown", self._ctx()["outro_subcopy"])


class HeroPriorityOrderTests(PureTestCase):
    def test_pending_beats_no_team(self):
        u = _auth()
        pending = {"url": "/t/h/", "label": "check-in required"}
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=pending), \
             patch.object(hh, "_get_team_info", return_value=None):
            ctx = hh.get_home_hero_context(u)
        self.assertEqual(ctx["mode"], "pending_action")

    def test_pending_beats_active_match(self):
        u = _auth()
        pending = {"url": "/t/h/", "label": "dispute active"}
        match   = {"url": "/t/h2/", "name": "Cup"}
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=pending), \
             patch.object(hh, "_get_active_match", return_value=match):
            ctx = hh.get_home_hero_context(u)
        self.assertEqual(ctx["mode"], "pending_action")

    def test_onboarding_beats_pending(self):
        u = _auth()
        pending = {"url": "/t/h/", "label": "check-in required"}
        with patch.object(hh, "_is_profile_incomplete", return_value=True), \
             patch.object(hh, "_get_pending_action", return_value=pending):
            ctx = hh.get_home_hero_context(u)
        self.assertEqual(ctx["mode"], "onboarding")

    def test_active_match_beats_ops(self):
        u = _auth()
        match = {"url": "/t/h/", "name": "Cup"}
        with patch.object(hh, "_is_profile_incomplete", return_value=False), \
             patch.object(hh, "_get_pending_action", return_value=None), \
             patch.object(hh, "_get_active_match", return_value=match), \
             patch.object(hh, "_has_ops", return_value=True):
            ctx = hh.get_home_hero_context(u)
        self.assertEqual(ctx["mode"], "active_match")


class HeroURLSafetyTests(PureTestCase):
    """Every CTA URL in every mode must start with '/'."""

    def _ctx_for(self, mode):
        u_anon = _anon(); u = _auth()
        if mode == "guest":
            return hh.get_home_hero_context(u_anon)
        t = _team()
        specs = {
            "onboarding":    [("_is_profile_incomplete", True)],
            "pending_action":[("_is_profile_incomplete", False),
                              ("_get_pending_action", {"url":"/t/h/","label":"x"})],
            "active_match":  [("_is_profile_incomplete", False),
                              ("_get_pending_action", None),
                              ("_get_active_match",   {"url":"/t/h/","name":"C"})],
            "operations":    [("_is_profile_incomplete", False),
                              ("_get_pending_action", None),
                              ("_get_active_match",   None),
                              ("_has_ops",            True)],
            "no_team":       [("_is_profile_incomplete", False),
                              ("_get_pending_action", None),
                              ("_get_active_match",   None),
                              ("_has_ops",            False),
                              ("_get_team_info",      None)],
            "team_manager":  [("_is_profile_incomplete", False),
                              ("_get_pending_action", None),
                              ("_get_active_match",   None),
                              ("_has_ops",            False),
                              ("_get_team_info",      t)],
            "team_ready":    [("_is_profile_incomplete", False),
                              ("_get_pending_action", None),
                              ("_get_active_match",   None),
                              ("_has_ops",            False),
                              ("_get_team_info",      {**t,"is_manager":False,"team_url":"/teams/x/"}),
                              ("_has_active_reg",     False)],
            "default":       [("_is_profile_incomplete", False),
                              ("_get_pending_action", None),
                              ("_get_active_match",   None),
                              ("_has_ops",            False),
                              ("_get_team_info",      {**t,"is_manager":False,"team_url":"/teams/x/"}),
                              ("_has_active_reg",     True)],
        }
        ps = [patch.object(hh, name,
              return_value=val if not callable(val) else val)
              for name, val in specs.get(mode, [])]
        for p in ps: p.start()
        try:
            ctx = hh.get_home_hero_context(u)
        finally:
            for p in ps: p.stop()
        return ctx

    def test_all_main_urls_are_paths(self):
        modes = ["guest","onboarding","pending_action","active_match",
                 "operations","no_team","team_manager","team_ready","default"]
        for mode in modes:
            with self.subTest(mode=mode):
                ctx = self._ctx_for(mode)
                for key in ("primary_cta_url", "secondary_cta_url"):
                    self.assertTrue(ctx[key].startswith("/"),
                        f"{mode}.{key}={ctx[key]!r} doesn't start with '/'")

    def test_all_outro_urls_are_paths(self):
        modes = ["guest","onboarding","pending_action","active_match",
                 "operations","no_team","team_manager","team_ready","default"]
        for mode in modes:
            with self.subTest(mode=mode):
                ctx = self._ctx_for(mode)
                for key in ("outro_primary_cta_url", "outro_secondary_cta_url"):
                    self.assertTrue(ctx[key].startswith("/"),
                        f"{mode}.{key}={ctx[key]!r} doesn't start with '/'")

    def test_no_create_account_for_auth_users(self):
        auth_modes = ["onboarding","pending_action","active_match",
                      "operations","no_team","team_manager","team_ready","default"]
        for mode in auth_modes:
            with self.subTest(mode=mode):
                ctx = self._ctx_for(mode)
                for key in ("primary_cta_label", "outro_primary_cta_label"):
                    self.assertNotIn(
                        "Create your account", ctx[key],
                        f"{mode}.{key} shows 'Create your account' to auth user")


class HeroOutroTests(PureTestCase):
    """Outro-specific tests: all modes have correct outro_* keys."""

    def _ctx(self, mode):
        return HeroURLSafetyTests()._ctx_for(mode)

    def test_all_modes_have_outro_keys(self):
        modes = ["guest","onboarding","pending_action","active_match",
                 "operations","no_team","team_manager","team_ready","default"]
        required = ["outro_primary_cta_label", "outro_primary_cta_url",
                    "outro_secondary_cta_label", "outro_secondary_cta_url"]
        for mode in modes:
            ctx = self._ctx(mode)
            with self.subTest(mode=mode):
                for key in required:
                    self.assertIn(key, ctx, f"{mode} missing {key}")
                    self.assertIsNotNone(ctx[key], f"{mode}.{key} is None")

    def test_outro_subcopy_present_for_logged_in(self):
        auth_modes = ["onboarding","pending_action","active_match",
                      "operations","no_team","team_manager","team_ready","default"]
        for mode in auth_modes:
            ctx = self._ctx(mode)
            with self.subTest(mode=mode):
                self.assertIsNotNone(ctx["outro_subcopy"],
                    f"{mode} should have outro_subcopy set")

    def test_outro_subcopy_none_for_guest(self):
        ctx = self._ctx("guest")
        self.assertIsNone(ctx["outro_subcopy"],
            "Guest outro_subcopy must be None (template uses static copy)")


class HeroOutroNeverCreateAccount(PureTestCase):
    """Specific check: no auth mode outro ever shows 'Create your account'."""

    def _ctx(self, mode):
        return HeroURLSafetyTests()._ctx_for(mode)

    def test_never_create_account_in_outro_for_auth(self):
        auth_modes = ["onboarding","pending_action","active_match",
                      "operations","no_team","team_manager","team_ready","default"]
        for mode in auth_modes:
            ctx = self._ctx(mode)
            with self.subTest(mode=mode):
                self.assertNotIn(
                    "Create your account",
                    ctx["outro_primary_cta_label"],
                    f"Mode '{mode}' outro shows 'Create your account'",
                )


# ══════════════════════════════════════════════════════════════════════════
#  INTEGRATION TESTS — need connected DB
#  python manage.py test apps.siteui.tests.test_homepage_hero.HeroViewTests --keepdb
# ══════════════════════════════════════════════════════════════════════════

class HeroViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="test_hero_view", email="thv@test.com", password="pass123",
        )

    def test_anonymous_renders_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_sees_create_account_in_html(self):
        resp = self.client.get("/")
        self.assertIn(b"Create your account", resp.content)

    def test_authenticated_renders_200(self):
        self.client.force_login(self.user)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_authenticated_no_create_account_button(self):
        """The rendered page must not contain 'Create your account' as a CTA button."""
        self.client.force_login(self.user)
        resp = self.client.get("/")
        # The phrase might appear in marketing text but NOT as a button label
        # We check for the btn-primary/btn-xl context via the CTA structure
        self.assertNotIn(b"Create your account", resp.content,
            "Authenticated homepage contains 'Create your account' somewhere")

    def test_hero_ctx_in_template_context(self):
        resp = self.client.get("/")
        self.assertIn("hero_ctx", resp.context)

    def test_hero_ctx_has_outro_keys(self):
        resp = self.client.get("/")
        ctx = resp.context["hero_ctx"]
        for key in ("outro_primary_cta_label", "outro_primary_cta_url",
                    "outro_secondary_cta_label", "outro_secondary_cta_url"):
            self.assertIn(key, ctx)

    def test_no_reversal_errors(self):
        self.client.force_login(self.user)
        try:
            resp = self.client.get("/")
        except Exception as exc:
            self.fail(f"Homepage raised {type(exc).__name__}: {exc}")
        self.assertEqual(resp.status_code, 200)

    def test_authenticated_outro_cta_not_signup(self):
        self.client.force_login(self.user)
        resp = self.client.get("/")
        ctx = resp.context["hero_ctx"]
        self.assertNotIn("Create your account", ctx["outro_primary_cta_label"])
        self.assertNotIn("/account/signup/", ctx["outro_primary_cta_url"])

    def test_rotation_items_key_present(self):
        """hero_ctx must always contain rotation_items key."""
        resp = self.client.get("/")
        self.assertIn("rotation_items", resp.context["hero_ctx"])

    def test_homepage_renders_no_500(self):
        """Homepage must not crash even with empty tournament/event data."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_sees_signup_cta_text(self):
        """Guest homepage must contain a signup CTA."""
        resp = self.client.get("/")
        # The guest CTA label "Create your account" must appear somewhere on the page
        self.assertIn(b"Create your account", resp.content)

    def test_authenticated_no_create_account_cta_anywhere(self):
        """Authenticated user must not see 'Create your account' as any CTA button."""
        self.client.force_login(self.user)
        resp = self.client.get("/")
        self.assertNotIn(b"Create your account", resp.content)

    def test_coming_up_empty_state_copy_in_template(self):
        """Template must contain the improved COMING UP empty state copy."""
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        # Just verify the template can be loaded and contains the new copy
        resp = self.client.get("/")
        # The improved copy should appear in HTML (when no upcoming events)
        # We check the template contains the key phrase either statically or dynamically
        html = resp.content.decode("utf-8", errors="replace")
        # The "Browse open tournaments" link or "No events scheduled yet" should appear
        self.assertTrue(
            "Browse open tournaments" in html or "No events scheduled yet" in html
            or "status=registration_open" in html,
            "Improved empty-state copy or registration_open link not found in homepage HTML",
        )

    def test_footer_single_youtube_icon_link(self):
        """Footer social section must contain exactly one YouTube icon-button link."""
        resp = self.client.get("/")
        html = resp.content.decode("utf-8", errors="replace")
        # Count occurrences of the YouTube icon social button (the w-12 icon grid)
        # We check the specific title="YouTube" attribute to count icon buttons
        youtube_icon_count = html.count('title="YouTube"')
        self.assertEqual(youtube_icon_count, 1,
            f"Expected exactly 1 YouTube icon button, found {youtube_icon_count}"
        )


class HeroRotationTests(PureTestCase):
    """Tests for rotation_items field across all states."""

    def _ctx(self, mode):
        return HeroURLSafetyTests()._ctx_for(mode)

    # ── States that must NOT rotate ────────────────────────────────────────
    def test_guest_no_rotation(self):
        ctx = self._ctx("guest")
        items = ctx.get("rotation_items")
        self.assertFalse(items, "Guest must not have rotation_items")

    def test_onboarding_no_rotation(self):
        ctx = self._ctx("onboarding")
        self.assertFalse(ctx.get("rotation_items"),
            "Onboarding must not rotate — keep directive copy")

    def test_pending_action_no_rotation(self):
        ctx = self._ctx("pending_action")
        self.assertFalse(ctx.get("rotation_items"),
            "Pending action must never rotate — urgency must stay clear")

    def test_no_team_no_rotation(self):
        ctx = self._ctx("no_team")
        self.assertFalse(ctx.get("rotation_items"),
            "No-team state should not rotate — message must stay clear")

    # ── States that DO rotate ──────────────────────────────────────────────
    def test_active_match_has_rotation(self):
        ctx = self._ctx("active_match")
        items = ctx.get("rotation_items")
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 2)

    def test_operations_has_rotation(self):
        ctx = self._ctx("operations")
        items = ctx.get("rotation_items")
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 2)

    def test_team_manager_has_rotation(self):
        ctx = self._ctx("team_manager")
        items = ctx.get("rotation_items")
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 2)

    def test_team_ready_has_rotation(self):
        ctx = self._ctx("team_ready")
        items = ctx.get("rotation_items")
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 2)

    def test_default_has_rotation(self):
        ctx = self._ctx("default")
        items = ctx.get("rotation_items")
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 2)

    # ── Each rotation item must be a dict with at least a subcopy key ─────
    def test_rotation_items_are_dicts_with_subcopy(self):
        rotating_modes = ["active_match", "operations", "team_manager",
                          "team_ready", "default"]
        for mode in rotating_modes:
            ctx = self._ctx(mode)
            items = ctx.get("rotation_items") or []
            with self.subTest(mode=mode):
                for i, item in enumerate(items):
                    self.assertIsInstance(item, dict,
                        f"{mode} rotation item {i} is not a dict: {item!r}")
                    self.assertIn("subcopy", item,
                        f"{mode} rotation item {i} missing 'subcopy' key")
                    self.assertTrue((item.get("subcopy") or "").strip(),
                        f"{mode} rotation item {i} has empty subcopy")

    # ── Full-CTA rotation states have primary_label / secondary_label ──────
    def test_full_cta_rotation_states_have_labels(self):
        full_cta_modes = ["operations", "team_manager", "team_ready", "default"]
        for mode in full_cta_modes:
            ctx = self._ctx(mode)
            items = ctx.get("rotation_items") or []
            with self.subTest(mode=mode):
                # At least one item should have primary_label
                has_primary = any(item.get("primary_label") for item in items)
                self.assertTrue(has_primary,
                    f"{mode} rotation has no items with primary_label")

    # ── All rotation item URL values must start with '/' ───────────────────
    def test_rotation_item_urls_are_safe_paths(self):
        rotating_modes = ["active_match", "operations", "team_manager",
                          "team_ready", "default"]
        for mode in rotating_modes:
            ctx = self._ctx(mode)
            items = ctx.get("rotation_items") or []
            with self.subTest(mode=mode):
                for i, item in enumerate(items):
                    for url_key in ("primary_url", "secondary_url"):
                        url = item.get(url_key)
                        if url:
                            self.assertTrue(url.startswith("/"),
                                f"{mode} item {i}.{url_key}={url!r} not a safe path")

    # ── Rotation items must never contain signup/account copy ──────────────
    def test_rotation_items_never_create_account(self):
        all_modes = ["guest","onboarding","pending_action","active_match",
                     "operations","no_team","team_manager","team_ready","default"]
        for mode in all_modes:
            ctx = self._ctx(mode)
            items = ctx.get("rotation_items") or []
            with self.subTest(mode=mode):
                for item in items:
                    label = item.get("primary_label", "") or ""
                    self.assertNotIn(
                        "Create your account", label,
                        f"{mode} rotation item primary_label contains 'Create your account'",
                    )
