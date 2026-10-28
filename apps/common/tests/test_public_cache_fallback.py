"""No production cache or database is used in these tests."""
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.common.public_cache import public_cache_get_or_set
from apps.siteui import cache_safe


class PublicCacheFallbackTests(SimpleTestCase):
    def setUp(self):
        self.previous_cooldown = cache_safe._CACHE_FAIL_UNTIL_MONO
        cache_safe._CACHE_FAIL_UNTIL_MONO = 0.0
        self.addCleanup(setattr, cache_safe, "_CACHE_FAIL_UNTIL_MONO", self.previous_cooldown)

    def test_cached_empty_result_is_not_rebuilt(self):
        builder = Mock()
        with patch("apps.common.public_cache.safe_cache_get", return_value=[]):
            self.assertEqual(public_cache_get_or_set("public:empty", builder, 60), [])
        builder.assert_not_called()

    def test_cache_timeout_renders_listing_and_enters_cooldown(self):
        builder = Mock(return_value={"total": 3})
        with patch.object(cache_safe.cache, "get", side_effect=TimeoutError("synthetic Redis timeout")) as get, patch.object(cache_safe.cache, "set") as set_:
            self.assertEqual(public_cache_get_or_set("public:teams", builder, 60), {"total": 3})
            self.assertEqual(public_cache_get_or_set("public:teams", builder, 60), {"total": 3})
            self.assertEqual(get.call_count, 1)
            set_.assert_not_called()
        self.assertEqual(builder.call_count, 2)

    def test_cache_write_failure_does_not_break_page(self):
        builder = Mock(return_value=["game"])
        with patch.object(cache_safe.cache, "get", side_effect=lambda key, default=None: default), patch.object(cache_safe.cache, "set", side_effect=TimeoutError("synthetic Redis write timeout")):
            self.assertEqual(public_cache_get_or_set("public:games", builder, 900), ["game"])

    def test_builder_exception_is_never_swallowed(self):
        with patch("apps.common.public_cache.safe_cache_get", return_value=__import__('apps.common.public_cache', fromlist=['_MISS'])._MISS):
            with self.assertRaisesRegex(ValueError, "database failed"):
                public_cache_get_or_set("public:games", lambda: (_ for _ in ()).throw(ValueError("database failed")), 900)
