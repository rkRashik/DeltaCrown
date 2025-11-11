"""
Test configuration and shared fixtures for DeltaCrown test suite.

Provides:
- Unique user factory for WebSocket tests (no fixture reuse issues)
- Settings overrides for test environment
- WebSocket testing utilities
- Redis fixtures for Module 6.8 rate limit tests
"""

import asyncio
import pytest
import uuid
from django.contrib.auth import get_user_model
from channels.testing import WebsocketCommunicator
from django.conf import settings

# Import Redis fixtures for Module 6.8
pytest_plugins = ['tests.redis_fixtures']


User = get_user_model()


@pytest.fixture
def unique_username():
    """Generate unique username for test isolation"""
    return f"user_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def user_factory(db):
    """
    Factory for creating unique users in tests.
    
    Avoids fixture reuse issues by creating fresh users with unique emails/usernames.
    Use this instead of shared fixtures like 'admin_user', 'organizer_user', etc.
    
    Usage:
        def test_something(user_factory):
            admin = user_factory(is_staff=True, is_superuser=True)
            regular = user_factory()
    """
    def make_user(username=None, email=None, is_staff=False, is_superuser=False):
        unique_id = uuid.uuid4().hex[:10]
        u = User.objects.create_user(
            username=username or f"user_{unique_id}",
            email=email or f"{unique_id}@example.com",
            password="testpass123",
        )
        if is_staff or is_superuser:
            u.is_staff = is_staff
            u.is_superuser = is_superuser
            u.save(update_fields=["is_staff", "is_superuser"])
        return u
    return make_user


@pytest.fixture
def settings_ws_disabled(settings):
    """
    Override settings for WebSocket tests without Redis.
    
    Ensures:
    - Rate limiting is disabled (no Redis required)
    - In-memory channel layer is used
    """
    settings.WS_RATE_ENABLED = False
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
    return settings
