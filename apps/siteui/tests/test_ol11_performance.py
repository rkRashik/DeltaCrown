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
