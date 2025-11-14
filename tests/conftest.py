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
def user(db):
    """Create regular authenticated user."""
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123"
    )


@pytest.fixture
def staff_user(db):
    """Create staff user (superuser so signal sets is_staff=True)."""
    user = User.objects.create(
        username="staffuser",
        email="staff@example.com",
        is_superuser=True,  # Signal will automatically set is_staff=True for superusers
        is_staff=True
    )
    user.set_password("testpass123")
    user.save()
    return user


@pytest.fixture
def other_user(db):
    """Create another regular user (for permission tests)."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="testpass123"
    )


@pytest.fixture
def game_valorant(db):
    """Create Valorant game for testing."""
    from apps.tournaments.models import Game
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    fake_icon = SimpleUploadedFile(
        name='valorant.png',
        content=b'fake-image-content',
        content_type='image/png'
    )
    
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        icon=fake_icon,
        default_team_size=Game.TEAM_SIZE_5V5,
        profile_id_field='riot_id',
        default_result_type=Game.BEST_OF,
    )


@pytest.fixture
def template_private(db, user, game_valorant):
    """Create a private tournament template."""
    from apps.tournaments.models import TournamentTemplate
    
    return TournamentTemplate.objects.create(
        name="Private Template",
        slug="private-template",
        game=game_valorant,
        created_by=user,
        visibility=TournamentTemplate.PRIVATE,
        is_active=True,
        template_config={
            "format": "single_elimination",
            "max_participants": 16,
        }
    )


@pytest.fixture
def template_global(db, staff_user, game_valorant):
    """Create a global tournament template."""
    from apps.tournaments.models import TournamentTemplate
    
    return TournamentTemplate.objects.create(
        name="Global Template",
        slug="global-template",
        game=game_valorant,
        created_by=staff_user,
        visibility=TournamentTemplate.GLOBAL,
        is_active=True,
        template_config={
            "format": "round_robin",
            "max_participants": 8,
        }
    )


@pytest.fixture
def template_inactive(db, user, game_valorant):
    """Create an inactive tournament template."""
    from apps.tournaments.models import TournamentTemplate
    
    return TournamentTemplate.objects.create(
        name="Inactive Template",
        slug="inactive-template",
        game=game_valorant,
        created_by=user,
        visibility=TournamentTemplate.PRIVATE,
        is_active=False,
        template_config={
            "format": "single_elimination",
            "max_participants": 32,
        }
    )


@pytest.fixture
def template_with_config(db, user, game_valorant):
    """Create a template with detailed config for apply tests."""
    from apps.tournaments.models import TournamentTemplate
    
    return TournamentTemplate.objects.create(
        name="Config Template",
        slug="config-template",
        game=game_valorant,
        created_by=user,
        visibility=TournamentTemplate.PRIVATE,
        is_active=True,
        template_config={
            "format": "single_elimination",
            "max_participants": 16,
            "has_entry_fee": True,
            "entry_fee_amount": "500.00",
            "rules": "Standard rules apply",
        }
    )


@pytest.fixture
def client():
    """DRF API test client."""
    from rest_framework.test import APIClient
    return APIClient()


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
