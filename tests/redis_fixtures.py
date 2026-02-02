"""
Redis test fixtures for Module 6.8 - Rate limit enforcement with Redis backend.

Provides:
- Ephemeral Redis setup/teardown
- Per-test namespace isolation
- Deterministic TTLs for fast tests
- Graceful skip if Redis unavailable
"""

import uuid
import pytest
import redis
from unittest.mock import patch
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================================================================
# Redis Test Configuration
# ============================================================================

REDIS_TEST_DB = 15  # Use DB 15 to avoid conflicts with dev/prod (0-14)
REDIS_TEST_HOST = 'localhost'
REDIS_TEST_PORT = 6379


def is_redis_available():
    """Check if Redis is available for testing."""
    try:
        client = redis.Redis(host=REDIS_TEST_HOST, port=REDIS_TEST_PORT, db=REDIS_TEST_DB, socket_timeout=1)
        client.ping()
        return True
    except (redis.ConnectionError, redis.TimeoutError):
        return False


# Skip marker for Redis tests
redis_required = pytest.mark.skipif(
    not is_redis_available(),
    reason="Redis not available (start Redis instance on localhost:6379)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def redis_test_client():
    """
    Session-scoped Redis client for test DB.
    
    Returns Redis client connected to test DB (15).
    Verifies connection at session start.
    """
    client = redis.Redis(
        host=REDIS_TEST_HOST,
        port=REDIS_TEST_PORT,
        db=REDIS_TEST_DB,
        decode_responses=True,
        socket_timeout=5
    )
    
    # Verify connection
    try:
        client.ping()
    except (redis.ConnectionError, redis.TimeoutError) as e:
        pytest.skip(f"Redis not available: {e}")
    
    yield client
    
    # Cleanup: flush test DB at session end
    client.flushdb()
    client.close()


@pytest.fixture
def test_namespace():
    """
    Generate unique namespace for test isolation.
    
    Returns string like "test:abc123de:" to prefix all Redis keys.
    Prevents cross-test key leakage.
    """
    return f"test:{uuid.uuid4().hex[:8]}:"


@pytest.fixture
def redis_cleanup(redis_test_client, test_namespace):
    """
    Cleanup fixture that runs after each test.
    
    Deletes all keys matching test namespace pattern.
    Ensures no key leakage between tests.
    """
    yield  # Test runs here
    
    # Delete all keys with test namespace prefix
    pattern = f"{test_namespace}*"
    keys = redis_test_client.keys(pattern)
    if keys:
        redis_test_client.delete(*keys)


@pytest.fixture
def redis_rate_limit_config(test_namespace, settings):
    """
    Configure rate limit settings for Redis-backed tests.
    
    Sets deterministic, low limits for fast test execution:
    - Connection limits: 2 per user, 5 per IP
    - Message rate: 5 RPS, burst 10
    - Payload: 1KB max
    - Room capacity: 10 members
    - Fast TTLs: 200ms cooldown windows
    - Redis backend via django-redis
    """
    # Configure Django cache to use Redis (not LocMem)
    settings.CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{REDIS_TEST_HOST}:{REDIS_TEST_PORT}/{REDIS_TEST_DB}",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_CLASS_KWARGS": {"max_connections": 50},
                "KEY_PREFIX": test_namespace,  # Namespace isolation
            },
        }
    }
    
    # Configure rate limit settings
    settings.WS_RATE_ENABLED = True
    settings.WS_RATE_CONN_PER_USER = 2
    settings.WS_RATE_CONN_PER_IP = 5
    settings.WS_RATE_MSG_RPS = 5.0
    settings.WS_RATE_MSG_BURST = 10
    settings.WS_MAX_PAYLOAD_BYTES = 1024
    settings.WS_RATE_ROOM_MAX_MEMBERS = 10
    
    yield settings


@pytest.fixture
def fast_cooldown(settings):
    """
    Configure fast cooldown windows for deterministic timing tests.
    
    Sets TTLs to 200ms for quick test execution.
    Use with asyncio.sleep(0.25) to verify cooldown recovery.
    """
    settings.WS_RATE_MSG_WINDOW_MS = 200  # 200ms message rate window
    settings.WS_RATE_CONN_TTL_SEC = 1     # 1s connection TTL (for cleanup tests)
    
    yield settings


# ============================================================================
# Helper Utilities
# ============================================================================

def get_redis_key_count(redis_client, namespace):
    """Get count of keys in namespace."""
    pattern = f"{namespace}*"
    return len(redis_client.keys(pattern))


def get_redis_counter(redis_client, namespace, key_suffix):
    """Get Redis counter value for key in namespace."""
    full_key = f"{namespace}{key_suffix}"
    value = redis_client.get(full_key)
    return int(value) if value else 0


def set_redis_counter(redis_client, namespace, key_suffix, value, ttl_sec=None):
    """Set Redis counter value with optional TTL."""
    full_key = f"{namespace}{key_suffix}"
    redis_client.set(full_key, value)
    if ttl_sec:
        redis_client.expire(full_key, ttl_sec)


# ============================================================================
# Async User Factory (for async tests)
# ============================================================================

@sync_to_async
def create_test_user(username=None, email=None, is_staff=False, is_superuser=False):
    """
    Create a test user from async context.
    
    Wraps synchronous User.objects.create_user with sync_to_async.
    Use this instead of direct user_factory in async tests.
    
    Usage:
        user = await create_test_user(username="testuser", email="test@example.com")
    """
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
