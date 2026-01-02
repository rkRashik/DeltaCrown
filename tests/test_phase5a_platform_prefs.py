"""
Tests for Phase 5A: Universal Platform Preferences

Tests:
1. Middleware - activates timezone/language for auth + anonymous
2. Platform settings API - GET/POST with validation
3. Template rendering - format_dt/format_money filters
4. Service layer - get/set with validation
"""

import pytest
import json
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.template import Context, Template

from apps.user_profile.models import UserProfile
from apps.user_profile.services.platform_prefs_service import (
    get_user_platform_prefs,
    set_user_platform_prefs,
    validate_language,
    validate_timezone,
    validate_time_format,
    validate_currency,
    DEFAULT_PREFS,
)
from deltacrown.middleware.platform_prefs_middleware import UserPlatformPrefsMiddleware

User = get_user_model()

pytestmark = pytest.mark.django_db


# ===== FIXTURES =====

@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')


@pytest.fixture
def profile(user):
    """Create test user profile."""
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'display_name': 'Test User',
            'preferred_language': 'en',
            'timezone_pref': 'Asia/Dhaka',
            'time_format': '12h',
        }
    )
    return profile


@pytest.fixture
def client():
    """Create test client."""
    return Client()


@pytest.fixture
def factory():
    """Create request factory."""
    return RequestFactory()


# ===== SERVICE LAYER TESTS =====

class TestPlatformPrefsService:
    """Test platform preferences service functions."""
    
    def test_get_prefs_authenticated_user(self, profile):
        """Test getting prefs for authenticated user."""
        prefs = get_user_platform_prefs(profile)
        
        assert prefs['preferred_language'] == 'en'
        assert prefs['timezone'] == 'Asia/Dhaka'
        assert prefs['time_format'] == '12h'
        assert prefs['currency'] == 'BDT'  # default
    
    def test_get_prefs_anonymous_user(self):
        """Test getting prefs for anonymous user (None profile)."""
        prefs = get_user_platform_prefs(None)
        
        assert prefs == DEFAULT_PREFS
        assert prefs['preferred_language'] == 'en'
        assert prefs['timezone'] == 'Asia/Dhaka'
    
    def test_set_prefs_valid(self, profile):
        """Test setting valid preferences."""
        updated = set_user_platform_prefs(profile, {
            'preferred_language': 'bn',
            'timezone': 'UTC',
            'time_format': '24h',
            'currency': 'USD',
        })
        
        assert updated['preferred_language'] == 'bn'
        assert updated['timezone'] == 'UTC'
        assert updated['time_format'] == '24h'
        assert updated['currency'] == 'USD'
        
        # Verify saved to DB
        profile.refresh_from_db()
        assert profile.preferred_language == 'bn'
        assert profile.timezone_pref == 'UTC'
        assert profile.time_format == '24h'
        assert profile.system_settings['currency'] == 'USD'
    
    def test_set_prefs_invalid_language(self, profile):
        """Test setting invalid language raises ValueError."""
        with pytest.raises(ValueError, match="Invalid language"):
            set_user_platform_prefs(profile, {'preferred_language': 'invalid'})
    
    def test_set_prefs_invalid_timezone(self, profile):
        """Test setting invalid timezone raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timezone"):
            set_user_platform_prefs(profile, {'timezone': 'Invalid/Timezone'})
    
    def test_set_prefs_invalid_time_format(self, profile):
        """Test setting invalid time_format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time_format"):
            set_user_platform_prefs(profile, {'time_format': 'invalid'})
    
    def test_set_prefs_invalid_currency(self, profile):
        """Test setting invalid currency raises ValueError."""
        with pytest.raises(ValueError, match="Invalid currency"):
            set_user_platform_prefs(profile, {'currency': 'INVALID'})
    
    def test_validate_language(self):
        """Test language validation."""
        assert validate_language('en') is True
        assert validate_language('bn') is True
        assert validate_language('invalid') is False
    
    def test_validate_timezone(self):
        """Test timezone validation."""
        assert validate_timezone('Asia/Dhaka') is True
        assert validate_timezone('UTC') is True
        assert validate_timezone('Invalid/Timezone') is False
    
    def test_validate_time_format(self):
        """Test time format validation."""
        assert validate_time_format('12h') is True
        assert validate_time_format('24h') is True
        assert validate_time_format('invalid') is False
    
    def test_validate_currency(self):
        """Test currency validation."""
        assert validate_currency('BDT') is True
        assert validate_currency('USD') is True
        assert validate_currency('INVALID') is False


# ===== MIDDLEWARE TESTS =====

class TestPlatformPrefsMiddleware:
    """Test middleware timezone/language activation."""
    
    def test_middleware_authenticated_user(self, factory, profile):
        """Test middleware activates prefs for authenticated user."""
        def get_response(request):
            # Check that prefs are activated
            assert hasattr(request, 'user_platform_prefs')
            assert request.user_platform_prefs['timezone'] == 'Asia/Dhaka'
            assert request.user_platform_prefs['time_format'] == '12h'
            assert request.LANGUAGE_CODE == 'en'
            return None
        
        middleware = UserPlatformPrefsMiddleware(get_response)
        request = factory.get('/')
        request.user = profile.user
        request.user.profile = profile
        
        middleware(request)
    
    def test_middleware_anonymous_user(self, factory):
        """Test middleware uses defaults for anonymous user."""
        def get_response(request):
            assert hasattr(request, 'user_platform_prefs')
            assert request.user_platform_prefs == DEFAULT_PREFS
            return None
        
        middleware = UserPlatformPrefsMiddleware(get_response)
        request = factory.get('/')
        
        # Mock anonymous user
        class AnonymousUser:
            is_authenticated = False
        
        request.user = AnonymousUser()
        
        middleware(request)
    
    def test_middleware_invalid_timezone_fallback(self, factory, profile):
        """Test middleware falls back to settings.TIME_ZONE if invalid."""
        # Set invalid timezone
        profile.timezone_pref = 'Invalid/Timezone'
        profile.save()
        
        def get_response(request):
            # Should not crash, falls back gracefully
            assert hasattr(request, 'user_platform_prefs')
            return None
        
        middleware = UserPlatformPrefsMiddleware(get_response)
        request = factory.get('/')
        request.user = profile.user
        request.user.profile = profile
        
        # Should not raise exception
        middleware(request)


# ===== API TESTS =====

class TestPlatformPrefsAPI:
    """Test platform preferences API endpoints."""
    
    def test_get_platform_settings(self, client, profile):
        """Test GET /me/settings/platform-global/."""
        client.force_login(profile.user)
        
        response = client.get('/me/settings/platform-global/')
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True
        assert 'preferences' in data
        assert 'available_options' in data
        
        # Check preferences
        prefs = data['preferences']
        assert prefs['preferred_language'] == 'en'
        assert prefs['timezone'] == 'Asia/Dhaka'
        assert prefs['time_format'] == '12h'
        assert prefs['currency'] == 'BDT'
        
        # Check available options
        options = data['available_options']
        assert len(options['languages']) >= 2  # en, bn
        assert len(options['timezones']) >= 5  # Common timezones
        assert len(options['time_formats']) == 2  # 12h, 24h
        assert len(options['currencies']) >= 2  # BDT, USD
    
    def test_save_platform_settings_valid(self, client, profile):
        """Test POST /me/settings/platform-global/save/ with valid data."""
        client.force_login(profile.user)
        
        response = client.post(
            '/me/settings/platform-global/save/',
            data=json.dumps({
                'preferred_language': 'bn',
                'timezone': 'UTC',
                'time_format': '24h',
                'currency': 'USD',
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == 'Platform preferences updated successfully'
        
        # Verify saved
        profile.refresh_from_db()
        assert profile.preferred_language == 'bn'
        assert profile.timezone_pref == 'UTC'
        assert profile.time_format == '24h'
    
    def test_save_platform_settings_invalid_language(self, client, profile):
        """Test POST with invalid language returns 400."""
        client.force_login(profile.user)
        
        response = client.post(
            '/me/settings/platform-global/save/',
            data=json.dumps({'preferred_language': 'invalid'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'Invalid language' in data['error']
    
    def test_save_platform_settings_invalid_timezone(self, client, profile):
        """Test POST with invalid timezone returns 400."""
        client.force_login(profile.user)
        
        response = client.post(
            '/me/settings/platform-global/save/',
            data=json.dumps({'timezone': 'Invalid/Timezone'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'Invalid timezone' in data['error']
    
    def test_api_requires_login(self, client):
        """Test API endpoints require login."""
        # GET endpoint
        response = client.get('/me/settings/platform-global/')
        assert response.status_code == 302  # Redirect to login
        
        # POST endpoint
        response = client.post('/me/settings/platform-global/save/', data='{}', content_type='application/json')
        assert response.status_code == 302  # Redirect to login


# ===== TEMPLATE FILTER TESTS =====

class TestTemplateFilters:
    """Test template filters for datetime and money formatting."""
    
    def test_format_dt_12h(self):
        """Test format_dt filter with 12-hour format."""
        from apps.common.templatetags.platform_filters import format_dt
        
        dt = datetime(2026, 1, 2, 15, 30, 0, tzinfo=ZoneInfo('UTC'))
        formatted = format_dt(dt, '12h')
        
        assert 'PM' in formatted or 'AM' in formatted
        assert '15:' not in formatted  # Should not use 24-hour
    
    def test_format_dt_24h(self):
        """Test format_dt filter with 24-hour format."""
        from apps.common.templatetags.platform_filters import format_dt
        
        # Use naive datetime, will be made aware by filter
        dt = datetime(2026, 1, 2, 15, 30, 0)
        dt_aware = timezone.make_aware(dt, timezone=ZoneInfo('Asia/Dhaka'))
        formatted = format_dt(dt_aware, '24h')
        
        assert '15:30' in formatted  # Should use 24-hour
        assert 'PM' not in formatted and 'AM' not in formatted
    
    def test_format_dt_none(self):
        """Test format_dt with None returns empty string."""
        from apps.common.templatetags.platform_filters import format_dt
        
        assert format_dt(None) == ""
    
    def test_format_money_bdt(self):
        """Test format_money filter with BDT."""
        from apps.common.templatetags.platform_filters import format_money
        
        amount = Decimal('1234.50')
        formatted = format_money(amount, 'BDT')
        
        assert '৳' in formatted
        assert '1,234.50' in formatted
    
    def test_format_money_usd(self):
        """Test format_money filter with USD."""
        from apps.common.templatetags.platform_filters import format_money
        
        amount = Decimal('1234.50')
        formatted = format_money(amount, 'USD')
        
        assert '$' in formatted
        assert '1,234.50' in formatted
    
    def test_format_money_none(self):
        """Test format_money with None defaults to 0.00."""
        from apps.common.templatetags.platform_filters import format_money
        
        formatted = format_money(None, 'BDT')
        assert '0.00' in formatted
    
    def test_template_integration(self):
        """Test filters work in template rendering."""
        template = Template(
            "{% load platform_filters %}"
            "{{ dt|format_dt:'12h' }}"
        )
        
        dt = timezone.now()
        context = Context({'dt': dt})
        rendered = template.render(context)
        
        assert rendered  # Should not be empty
        assert 'AM' in rendered or 'PM' in rendered


# ===== CONTEXT PROCESSOR TESTS =====

class TestContextProcessor:
    """Test platform_prefs context processor."""
    
    def test_context_processor_with_prefs(self, factory, profile):
        """Test context processor injects prefs."""
        from apps.common.context_processors import user_platform_prefs
        
        request = factory.get('/')
        request.user_platform_prefs = {
            'preferred_language': 'en',
            'timezone': 'Asia/Dhaka',
            'time_format': '12h',
            'currency': 'BDT',
        }
        
        context = user_platform_prefs(request)
        
        assert 'user_platform_prefs' in context
        assert 'is_24h' in context
        assert 'currency_symbol' in context
        assert 'currency_code' in context
        assert 'locale_code' in context
        
        assert context['is_24h'] is False
        assert context['currency_symbol'] == '৳'
        assert context['currency_code'] == 'BDT'
        assert context['locale_code'] == 'en'
    
    def test_context_processor_fallback(self, factory):
        """Test context processor falls back to defaults."""
        from apps.common.context_processors import user_platform_prefs
        
        request = factory.get('/')
        # No user_platform_prefs set (middleware didn't run)
        
        context = user_platform_prefs(request)
        
        assert context['user_platform_prefs'] == DEFAULT_PREFS
