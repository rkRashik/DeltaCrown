"""
Test settings for DeltaCrown using local Postgres test database.

IMPORTANT: Defaults to dockerized PostgreSQL on port 5433 if DATABASE_URL_TEST not set.
Never run tests against production database or SQLite (incompatible with Postgres-specific features).
"""

import os
import sys
from .settings import *

# Default to docker test DB if not explicitly set (Phase 15 fix)
DATABASE_URL_TEST = os.getenv('DATABASE_URL_TEST')

if not DATABASE_URL_TEST:
    DATABASE_URL_TEST = 'postgresql://dcadmin:dcpass123@localhost:5433/deltacrown_test'
    os.environ['DATABASE_URL_TEST'] = DATABASE_URL_TEST
    # Note: conftest.py will show user-friendly message about docker compose

# Safety check: Prevent using production DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL_TEST == DATABASE_URL:
    raise RuntimeError(
        "\n"
        "=" * 70 + "\n"
        "FATAL: DATABASE_URL_TEST equals DATABASE_URL\n"
        "=" * 70 + "\n\n"
        "You are trying to run tests against the production database!\n"
        "DATABASE_URL_TEST must point to a separate test database.\n"
    )

# Parse DATABASE_URL_TEST for connection details
# Expected format: postgresql://user:password@host:port/database
import dj_database_url

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL_TEST)
}
DATABASES['default']['CONN_MAX_AGE'] = 0

# Ensure we're using PostgreSQL (SQLite not supported)
if 'postgresql' not in DATABASES['default']['ENGINE']:
    raise RuntimeError(
        f"Invalid database engine: {DATABASES['default']['ENGINE']}\n"
        "Tests require PostgreSQL only. SQLite is not supported due to Postgres-specific features.\n"
        "Check your DATABASE_URL_TEST format: postgresql://user:pass@localhost:5432/dbname"
    )

# Safety check: Refuse remote databases for tests (local only)
# Allow localhost on any port (e.g., 5432, 54329 for Docker)
db_host = DATABASES['default'].get('HOST', '')
if db_host and db_host not in ['localhost', '127.0.0.1', '::1', '']:
    # Block remote hosts like neon.tech, aws.com, etc.
    if any(domain in db_host for domain in ['neon.tech', 'aws.', 'azure.', 'gcp.', 'supabase.', 'heroku.']):
        raise RuntimeError(
            "\n"
            "=" * 70 + "\n"
            f"FATAL: Remote database host '{db_host}' not allowed for tests\n"
            "=" * 70 + "\n\n"
            "Tests must use LOCAL database only (localhost/127.0.0.1).\n"
            "Never run tests against remote databases (Neon, AWS, etc).\n"
        )

# Safety check: Database name must contain "test"
db_name = DATABASES['default']['NAME']
if 'test' not in db_name.lower():
    raise RuntimeError(
        "\n"
        "=" * 70 + "\n"
        f"FATAL: Database name '{db_name}' does not contain 'test'\n"
        "=" * 70 + "\n\n"
        "Test database name must contain 'test' to prevent accidental\n"
        "production database usage. Examples: deltacrown_test, testdb, test_db\n"
    )

# Test optimizations
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable Sentry in tests
SENTRY_DSN = None

# Reduce logging noise in tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',  # Changed to DEBUG to see hub logs
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',  # Changed to DEBUG
    },
    'loggers': {
        'apps.organizations.views.hub': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Use in-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Use in-memory channel layer (no Redis required for tests)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# Disable rate limiting in tests
WS_RATE_ENABLED = False

# Allow all origins in tests
WS_ALLOWED_ORIGINS = []

# Test-friendly settings
DEBUG = False
ALLOWED_HOSTS = ['*']
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Enable vNext features for testing (Phase 16+)
TEAM_VNEXT_ADAPTER_ENABLED = True
TEAM_VNEXT_FORCE_LEGACY = False
TEAM_VNEXT_ROUTING_MODE = 'auto'
ORG_APP_ENABLED = True
LEGACY_TEAMS_ENABLED = True  # Keep both available
COMPETITION_APP_ENABLED = True

# Print confirmation (helps catch accidental production DB usage)
print(f"\n{'=' * 70}")
print(f"TEST DATABASE: {DATABASES['default']['NAME']} @ {DATABASES['default']['HOST']}")
print(f"{'=' * 70}\n")
