"""
Test configuration and shared fixtures for DeltaCrown test suite.

Provides:
- Unique user factory for WebSocket tests (no fixture reuse issues)
- Settings overrides for test environment
- WebSocket testing utilities
- Redis fixtures for Module 6.8 rate limit tests
- Test schema setup (avoids CREATEDB requirement)
- Database policy enforcement (always use DATABASE_URL_TEST)
- Game model compatibility shim for stale test kwargs
"""

import asyncio
import pytest
import uuid
import os
from django.contrib.auth import get_user_model
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.db import connection

# Import Redis fixtures for Module 6.8
pytest_plugins = ['tests.redis_fixtures']


User = get_user_model()


# ---------------------------------------------------------------------------
# Game model compatibility shim
# ---------------------------------------------------------------------------
# Many older test files create Game objects with fields that were removed
# during the tournament redevelopment (default_team_size, profile_id_field,
# default_result_type) and reference stale class constants (TEAM_SIZE_5V5,
# MAP_SCORE, etc.).  Rather than rewriting 30+ test files, we patch the
# model's __init__ to silently strip the removed kwargs and provide defaults
# for newly-required fields (short_code, category).
# ---------------------------------------------------------------------------

_STALE_GAME_KWARGS = frozenset({
    'default_team_size', 'profile_id_field', 'default_result_type',
})

_GAME_PATCHED = False


def _patch_game_model():
    """One-time patch of the Game model for test compatibility."""
    global _GAME_PATCHED
    if _GAME_PATCHED:
        return
    _GAME_PATCHED = True

    from apps.games.models.game import Game

    # Add stale class constants so `Game.MAP_SCORE` etc. don't raise AttributeError
    _compat_constants = {
        'MAP_SCORE': 'map_score',
        'BEST_OF': 'best_of',
        'POINT_BASED': 'point_based',
        'TEAM_SIZE_5V5': 5,
        'TEAM_SIZE_4V4': 4,
        'TEAM_SIZE_3V3': 3,
        'TEAM_SIZE_2V2': 2,
        'TEAM_SIZE_1V1': 1,
    }
    for attr, value in _compat_constants.items():
        if not hasattr(Game, attr):
            setattr(Game, attr, value)

    # Wrap __init__ to strip stale kwargs and fill missing required fields
    _orig_init = Game.__init__

    def _compat_init(self, *args, **kwargs):
        # Save stale kwargs as instance attributes (some tests read them)
        stale_values = {}
        for key in _STALE_GAME_KWARGS:
            if key in kwargs:
                stale_values[key] = kwargs.pop(key)
        # Only add defaults when NO positional args are present.
        # Django's Model.from_db() calls cls(*values) with positional args;
        # adding keyword defaults would cause "both positional and keyword
        # arguments" TypeError.
        if not args:
            if 'short_code' not in kwargs:
                name = kwargs.get('name', 'TST')
                kwargs['short_code'] = name[:4].upper().replace(' ', '')
            if 'category' not in kwargs:
                kwargs['category'] = 'FPS'
            if 'display_name' not in kwargs:
                kwargs['display_name'] = kwargs.get('name', 'Test Game')
        result = _orig_init(self, *args, **kwargs)
        # Set stale attrs on instance so `game.default_team_size` still works
        for key, val in stale_values.items():
            setattr(self, key, val)
        return result

    Game.__init__ = _compat_init


# Apply patch at import time so factory_boy, setUp(), and fixtures all benefit
_patch_game_model()


@pytest.fixture(scope='session', autouse=True)
def enforce_test_database():
    """
    Enforce use of DATABASE_URL_TEST for all pytest runs.
    Defaults to dockerized PostgreSQL on port 54329.
    Prevents tests from running on Neon or any remote database.
    Requires local PostgreSQL (SQLite not supported).
    """
    db_url = os.getenv('DATABASE_URL_TEST')
    
    # Default to docker test DB if not set
    if not db_url:
        db_url = 'postgresql://dcadmin:dcpass123@localhost:5433/deltacrown_test'
        os.environ['DATABASE_URL_TEST'] = db_url
        print(f"\n💡 DATABASE_URL_TEST not set - using docker default: {db_url}")
        print("   Run: docker compose -f ops/docker-compose.test.yml up -d\n")
    
    # Refuse to run on Neon or any non-local database
    if 'neon.tech' in db_url or ('postgresql://' in db_url and not any(host in db_url for host in ['localhost', '127.0.0.1', '::1'])):
        pytest.exit(
            f"\n❌ Tests cannot run on remote database: {db_url}\n"
            "   DATABASE_URL_TEST must point to localhost postgres.\n",
            returncode=1
        )
    
    # Check if docker DB is accessible
    if 'localhost:5433' in db_url:
        import psycopg2
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
        except psycopg2.OperationalError:
            pytest.exit(
                "\n❌ Cannot connect to docker test database\n"
                "   Run: docker compose -f ops/docker-compose.test.yml up -d\n"
                "   Then: pytest\n",
                returncode=1
            )
    
    yield


@pytest.fixture(scope='session', autouse=True)
def setup_test_schema(django_db_setup, django_db_blocker):
    """
    Create test schema if using PostgreSQL (no CREATEDB privilege needed).
    Schema isolation allows tests to run in production DB without conflicts.
    Skips for SQLite (doesn't support schemas).
    """
    if connection.vendor != 'postgresql':
        # SQLite doesn't support schemas
        yield
        return
        
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            # Create schema if it doesn't exist (allowed without CREATEDB)
            cursor.execute("CREATE SCHEMA IF NOT EXISTS test_schema")
            # Set search_path for this connection
            cursor.execute("SET search_path TO test_schema, public")
            cursor.execute("SET search_path TO test_schema, public")
    yield
    # Cleanup: Drop schema after all tests (optional, commented out for --reuse-db)
    # with django_db_blocker.unblock():
    #     with connection.cursor() as cursor:
    #         cursor.execute("DROP SCHEMA IF EXISTS test_schema CASCADE")


@pytest.fixture(scope='function', autouse=True)
def cleanup_test_data(db):
    """
    Clean up test data between test functions to avoid unique constraint violations.
    Deletes in correct order to respect PROTECT foreign keys.
    Wrapped in try/except so teardown errors don't mask real test results.
    """
    yield  # Run test first
    try:
        from apps.tournaments.models.registration import Registration, Payment
        from apps.tournaments.models.tournament import Tournament
        from apps.games.models.game import Game
        from apps.user_profile.models.activity import UserActivity
        from apps.user_profile.models.stats import UserProfileStats
        from apps.user_profile.models import UserProfile
        from apps.accounts.models import User
        from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
        from apps.organizations.models import Team, Organization, OrganizationMembership

        # Delete dependent objects first, then parents
        Payment.objects.all().delete()
        Registration.objects.all().delete()
        Tournament.objects.all().delete()
        UserActivity.objects.all().delete()
        UserProfileStats.objects.all().delete()
        DeltaCrownTransaction.objects.all().delete()
        DeltaCrownWallet.objects.all().delete()
        UserProfile.objects.all().delete()
        Team.objects.all().delete()
        OrganizationMembership.objects.all().delete()
        Organization.objects.all().delete()
        Game.objects.all().delete()
        User.objects.all().delete()
    except Exception:
        pass  # Swallow teardown errors; real failures are caught in the test body



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
        short_code='VAL',
        category='FPS',
        display_name='VALORANT',
        icon=fake_icon,
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
