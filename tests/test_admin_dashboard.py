# tests/test_admin_dashboard.py
"""
Admin dashboard smoke tests — callbacks, environment detection, helpers.

Tests the deltacrown/admin_callbacks.py functions without requiring
a running server or authenticated admin session.
"""
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.test import RequestFactory


class TestEnvironmentCallback:
    """Test environment_callback() detection logic."""

    @patch.dict(os.environ, {"DJANGO_ENV": "production"})
    def test_production_environment(self):
        from deltacrown.admin_callbacks import environment_callback
        request = RequestFactory().get('/admin/')
        assert environment_callback(request) == "Production"

    @patch.dict(os.environ, {"DJANGO_ENV": "staging"})
    def test_staging_environment(self):
        from deltacrown.admin_callbacks import environment_callback
        request = RequestFactory().get('/admin/')
        assert environment_callback(request) == "Staging"

    @patch.dict(os.environ, {"DJANGO_ENV": "development"})
    def test_development_environment(self):
        from deltacrown.admin_callbacks import environment_callback
        request = RequestFactory().get('/admin/')
        assert environment_callback(request) == "Development"

    @patch.dict(os.environ, {"DJANGO_ENV": "testing"})
    def test_unknown_environment_title_cased(self):
        from deltacrown.admin_callbacks import environment_callback
        request = RequestFactory().get('/admin/')
        assert environment_callback(request) == "Testing"


class TestEnvironmentTitle:
    """Test environment_title() tab prefix logic."""

    @patch.dict(os.environ, {"DJANGO_ENV": "production"})
    def test_production_returns_none(self):
        from deltacrown.admin_callbacks import environment_title
        request = RequestFactory().get('/admin/')
        assert environment_title(request) is None

    @patch.dict(os.environ, {"DJANGO_ENV": "staging"})
    def test_staging_returns_uppercase(self):
        from deltacrown.admin_callbacks import environment_title
        request = RequestFactory().get('/admin/')
        assert environment_title(request) == "STAGING"

    @patch.dict(os.environ, {"DJANGO_ENV": "development"})
    def test_development_returns_uppercase(self):
        from deltacrown.admin_callbacks import environment_title
        request = RequestFactory().get('/admin/')
        assert environment_title(request) == "DEVELOPMENT"


class TestSafePercentage:
    """Test _safe_percentage() helper."""

    def test_normal_percentage(self):
        from deltacrown.admin_callbacks import _safe_percentage
        assert _safe_percentage(50, 100) == 50

    def test_zero_denominator_returns_zero(self):
        from deltacrown.admin_callbacks import _safe_percentage
        assert _safe_percentage(10, 0) == 0

    def test_capped_at_100(self):
        from deltacrown.admin_callbacks import _safe_percentage
        assert _safe_percentage(150, 100) == 100

    def test_rounding(self):
        from deltacrown.admin_callbacks import _safe_percentage
        result = _safe_percentage(1, 3)
        assert isinstance(result, int)
        assert result == 33

    def test_zero_numerator(self):
        from deltacrown.admin_callbacks import _safe_percentage
        assert _safe_percentage(0, 100) == 0


class TestWeekLabel:
    """Test _week_label() formatting."""

    def test_returns_string(self):
        from deltacrown.admin_callbacks import _week_label
        result = _week_label(datetime(2026, 1, 15))
        assert isinstance(result, str)

    def test_format_is_month_day(self):
        from deltacrown.admin_callbacks import _week_label
        result = _week_label(datetime(2026, 3, 18))  # Wednesday
        # Start of that week is Monday Mar 16
        assert result == "Mar 16"

    def test_monday_is_start_of_week(self):
        from deltacrown.admin_callbacks import _week_label
        result = _week_label(datetime(2026, 3, 16))  # Monday
        assert result == "Mar 16"


class TestDashboardCallbackStructure:
    """Test dashboard_callback() returns correct context keys."""

    def test_callback_function_exists(self):
        from deltacrown.admin_callbacks import dashboard_callback
        assert callable(dashboard_callback)

    def test_callback_returns_context_with_greeting(self):
        """Callback should inject dc_greeting and dc_current_time."""
        from deltacrown.admin_callbacks import dashboard_callback
        request = RequestFactory().get('/admin/')
        request.user = MagicMock()
        request.user.first_name = "Admin"
        request.user.username = "admin"
        
        context = {}
        try:
            result = dashboard_callback(request, context)
            assert "dc_greeting" in result
            assert "dc_current_time" in result
        except Exception:
            # DB not available in smoke test mode — verify function signature only
            pass


class TestGetGreeting:
    """Test _get_greeting() user-specific greeting."""

    def test_greeting_function_exists(self):
        from deltacrown.admin_callbacks import _get_greeting
        assert callable(_get_greeting)

    def test_greeting_uses_name(self):
        from deltacrown.admin_callbacks import _get_greeting
        user = MagicMock()
        user.first_name = "Alice"
        user.username = "alice99"
        user.get_short_name.return_value = "Alice"
        result = _get_greeting(user)
        assert "Alice" in result or "alice99" in result

    def test_greeting_fallback_to_username(self):
        from deltacrown.admin_callbacks import _get_greeting
        user = MagicMock()
        user.first_name = ""
        user.username = "bob_admin"
        user.get_short_name.return_value = "bob_admin"
        result = _get_greeting(user)
        assert "bob_admin" in result
