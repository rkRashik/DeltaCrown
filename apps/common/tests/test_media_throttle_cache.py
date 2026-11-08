"""Media cache reliability: synthetic requests, no Redis or production reads."""
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache as global_cache
from django.core.cache.backends.locmem import LocMemCache
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.common.media.throttles import DerivativeReadThrottle, MediaReadThrottle


class MediaReadThrottleCacheTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        MediaReadThrottle.cache.clear()
        self.addCleanup(MediaReadThrottle.cache.clear)

    def request(self, address="192.0.2.23"):
        req = self.factory.get("/files/games.game/logo/7/", REMOTE_ADDR=address)
        req.user = AnonymousUser()
        return req

    @override_settings(MEDIA_READ_RATE="2/min")
    def test_media_reads_not_dependent_on_unavailable_shared_redis(self):
        self.assertIsInstance(MediaReadThrottle.cache, LocMemCache)
        self.assertIsNot(MediaReadThrottle.cache, global_cache)
        req = self.request()
        with patch.object(global_cache, "get", side_effect=TimeoutError("synthetic redis timeout")):
            self.assertTrue(MediaReadThrottle().allow_request(req, None))
            self.assertTrue(MediaReadThrottle().allow_request(req, None))
            self.assertFalse(MediaReadThrottle().allow_request(req, None))

    @override_settings(MEDIA_READ_RATE="1/min")
    def test_distinct_ips_keep_independent_budgets(self):
        self.assertTrue(MediaReadThrottle().allow_request(self.request("192.0.2.10"), None))
        self.assertFalse(MediaReadThrottle().allow_request(self.request("192.0.2.10"), None))
        self.assertTrue(MediaReadThrottle().allow_request(self.request("192.0.2.11"), None))

    def test_cache_has_bounded_entries(self):
        self.assertLessEqual(MediaReadThrottle.cache._max_entries, 1024)


class DerivativeThrottleTests(MediaReadThrottleCacheTests):
    @override_settings(MEDIA_READ_RATE="1/min", MEDIA_DERIVATIVE_READ_RATE="3/min")
    def test_derivatives_have_their_own_larger_budget_that_originals_cannot_exhaust(self):
        req = self.request()
        self.assertTrue(MediaReadThrottle().allow_request(req, None))
        self.assertFalse(MediaReadThrottle().allow_request(req, None))  # originals: strict budget spent
        for _ in range(3):
            self.assertTrue(DerivativeReadThrottle().allow_request(req, None))
        self.assertFalse(DerivativeReadThrottle().allow_request(req, None))
        self.assertEqual(DerivativeReadThrottle().get_rate(), "3/min")

    def test_default_derivative_budget_covers_a_dozen_page_views_per_minute(self):
        self.assertEqual(DerivativeReadThrottle().get_rate(), "1500/min")
