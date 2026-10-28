"""Sanitized, bounded homepage performance telemetry without user data."""
from unittest.mock import patch

from django.test import SimpleTestCase
from apps.siteui.views import _homepage_timed


class HomepagePhaseTimingTests(SimpleTestCase):
    def test_fast_call_has_no_warning(self):
        with patch("apps.siteui.views.time.monotonic", side_effect=[100, 100.11]):
            with self.assertNoLogs("deltacrown.homepage_performance", level="WARNING"):
                self.assertEqual(_homepage_timed("context", lambda: 42), 42)

    def test_slow_call_logs_only_phase_and_duration(self):
        with patch("apps.siteui.views.time.monotonic", side_effect=[100, 100.75]):
            with self.assertLogs("deltacrown.homepage_performance", level="WARNING") as logs:
                result = _homepage_timed("extras", lambda: {"private": "never logged"})
        self.assertEqual(result, {"private": "never logged"})
        self.assertIn("homepage_phase phase=extras elapsed_ms=750", logs.output[0])
        self.assertNotIn("private", logs.output[0])

    def test_exception_is_preserved_not_suppressed(self):
        def fail():
            raise ValueError("synthetic")
        with patch("apps.siteui.views.time.monotonic", side_effect=[100, 100.8]):
            with self.assertLogs("deltacrown.homepage_performance", level="WARNING"):
                with self.assertRaisesRegex(ValueError, "synthetic"):
                    _homepage_timed("render", fail)
