"""
Test configuration and shared fixtures for DeltaCrown test suite.

Provides:
- Unique user factory for WebSocket tests (no fixture reuse issues)
- Settings overrides for test environment
- WebSocket testing utilities
- Redis fixtures for Module 6.8 rate limit tests
- Test schema setup (avoids CREATEDB requirement)
- Database policy enforcement (always use DATABASE_URL_TEST)
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
    if 'localhost:54329' in db_url:
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
    Truncates only user_profile tables used by tests.
    """
    yield  # Run test first
    # Cleanup after test
    from apps.user_profile.models.activity import UserActivity
    from apps.user_profile.models.stats import UserProfileStats
    from apps.user_profile.models import UserProfile
    from apps.accounts.models import User
    from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
    
    # Delete in correct order (respect foreign keys)
    UserActivity.objects.all().delete()
    UserProfileStats.objects.all().delete()
    DeltaCrownTransaction.objects.all().delete()
    DeltaCrownWallet.objects.all().delete()
    UserProfile.objects.all().delete()
    User.objects.all().delete()



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
