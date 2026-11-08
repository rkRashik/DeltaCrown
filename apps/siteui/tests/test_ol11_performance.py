"""OL-11 performance regressions (synthetic: no network, no database)."""
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.siteui import homepage_extras as h
from apps.siteui import nav_context as nav


class HomepageExtrasCacheTests(SimpleTestCase):
    def setUp(self):
        self.store = {}
        self.builds = 0
        self.lock = threading.Lock()
        patches = [
            patch.object(h, "safe_cache_get", side_effect=lambda k, d=None: self.store.get(k, d)),
            patch.object(h, "safe_cache_set", side_effect=lambda k, v, t=0: self.store.__setitem__(k, v)),
            patch.object(h, "_featured_tournament", side_effect=self.slow_build),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        for name in ("_live_ribbon", "_recent_ribbon", "_hero_stats", "_quick_jump", "_ticker_items", "_upcoming_cards",
                     "_game_posters", "_ecosystem_modules", "_competitive_pillars", "_tier_rail", "_top_teams",
                     "_player_spotlight", "_activity_feed", "_comparison_rows", "_testimonials", "_roadmap_items",
                     "_organizer_steps", "_personas", "_path_stages"):
            p = patch.object(h, name, return_value=[])
            p.start()
            self.addCleanup(p.stop)

    def slow_build(self):
        with self.lock:
            self.builds += 1
        time.sleep(0.15)
        return None

    def test_concurrent_cold_requests_build_once(self):
        results = []
        threads = [threading.Thread(target=lambda: results.append(h.get_homepage_extras())) for _ in range(8)]
        [t.start() for t in threads]
        [t.join(10) for t in threads]
        self.assertEqual(len(results), 8)
        self.assertEqual(self.builds, 1)  # before: every cold request rebuilt (~38 queries each)
        self.assertTrue(all(r is results[0] or r == results[0] for r in results))

    def test_stale_entry_is_served_immediately_and_refreshed_once_in_the_background(self):
        h.get_homepage_extras()
        entry = self.store[h._EXTRAS_KEY]
        entry["_built_at"] -= h._EXTRAS_FRESH_SECONDS + 5
        self.builds = 0
        started = time.monotonic()
        served = [h.get_homepage_extras() for _ in range(5)]
        self.assertLess(time.monotonic() - started, 0.1)  # nobody waited for the rebuild
        self.assertTrue(all(s is entry for s in served))
        for _ in range(100):
            if self.builds and not h._extras_lock.locked():
                break
            time.sleep(0.05)
        self.assertEqual(self.builds, 1)
        self.assertIsNot(self.store[h._EXTRAS_KEY], entry)
        self.assertFalse(h._extras_stale(self.store[h._EXTRAS_KEY]))

    def test_warm_up_only_builds_when_missing_or_stale(self):
        h.warm_homepage_extras()
        h.warm_homepage_extras()
        self.assertEqual(self.builds, 1)


class NavLiveCacheTests(SimpleTestCase):
    def test_a_cached_false_is_a_hit_not_a_query_on_every_page(self):
        request = SimpleNamespace(path="/", user=SimpleNamespace(is_authenticated=False))
        cache = {"siteui:nav_live:v1": False, "siteui:nav_live_count:v1": 0}
        with patch.object(nav, "safe_cache_get", side_effect=lambda k, d=None: cache.get(k, d)), patch.object(
                nav.apps, "get_model", side_effect=AssertionError("must not query")) as get_model:
            self.assertFalse(nav.nav_context(request)["nav_live"])
        get_model.assert_not_called()


class HeroCacheTests(SimpleTestCase):
    def test_signed_in_hero_is_resolved_once_per_30_seconds_and_guests_are_never_cached(self):
        from apps.siteui import views
        store, calls = {}, []
        user = SimpleNamespace(is_authenticated=True, pk=7)
        resolver = lambda u: calls.append(u) or {"mode": "registered"}
        with patch.object(views, "safe_cache_get", side_effect=lambda k, d=None: store.get(k, d)), patch.object(
                views, "safe_cache_set", side_effect=lambda k, v, t=0: store.__setitem__(k, v)):
            views._cached_hero_context(user, resolver)
            views._cached_hero_context(user, resolver)
            self.assertEqual(len(calls), 1)
            guest = SimpleNamespace(is_authenticated=False, pk=None)
            views._cached_hero_context(guest, resolver)
            views._cached_hero_context(guest, resolver)
            self.assertEqual(len(calls), 3)
            self.assertEqual(list(store), ["home_hero:v1:7"])
            views._cached_hero_context(user, lambda u: {"unpicklable": lambda: 1})  # cached hit: not even resolved
            self.assertEqual(len(calls), 3)
            store.clear()
            self.assertEqual(views._cached_hero_context(SimpleNamespace(is_authenticated=True, pk=8), lambda u: {"f": lambda: 1})["f"](), 1)
            self.assertEqual(store, {})  # an unpicklable context is served but never cached


class TemplateWarmupTests(SimpleTestCase):
    def test_warm_up_runs_once_and_survives_a_broken_template(self):
        h._templates_warmed = False
        with patch("django.template.loader.get_template", side_effect=[None, RuntimeError("x"), None, None]) as get:
            h.warm_templates()
            h.warm_templates()
        self.assertEqual(get.call_count, len(h._WARM_TEMPLATES))


class ImgUrlHelperTests(SimpleTestCase):
    def test_non_governed_values_keep_their_plain_url(self):
        from apps.siteui import views
        self.assertEqual(views._img_url(SimpleNamespace(url="/static/x.png"), "thumb"), "/static/x.png")
