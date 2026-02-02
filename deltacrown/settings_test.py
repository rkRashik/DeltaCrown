"""
Test settings for DeltaCrown using Neon Postgres test database.

IMPORTANT: This module requires DATABASE_URL_TEST environment variable.
Never run tests against production database.
"""

import os
import sys
from .settings import *

# Safety check: Require explicit test database URL
DATABASE_URL_TEST = os.getenv('DATABASE_URL_TEST')

if not DATABASE_URL_TEST:
    raise RuntimeError(
        "\n"
        "=" * 70 + "\n"
        "ERROR: DATABASE_URL_TEST environment variable is required for tests.\n"
        "=" * 70 + "\n\n"
        "To run tests, you must set DATABASE_URL_TEST to a dedicated test database.\n"
        "Example:\n"
        "  export DATABASE_URL_TEST='postgresql://user:pass@host/testdb'\n\n"
        "NEVER point DATABASE_URL_TEST to your production database.\n"
        "Use a dedicated Neon test database or separate test instance.\n"
    )

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
    'default': dj_database_url.parse(DATABASE_URL_TEST, conn_max_age=0)
}

# Ensure we're using PostgreSQL
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise RuntimeError(
        f"Invalid database engine: {DATABASES['default']['ENGINE']}\n"
        "Tests require PostgreSQL. Check your DATABASE_URL_TEST format."
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
            'level': 'WARNING',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
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

# Print confirmation (helps catch accidental production DB usage)
print(f"\n{'=' * 70}")
print(f"TEST DATABASE: {DATABASES['default']['NAME']} @ {DATABASES['default']['HOST']}")
print(f"{'=' * 70}\n")
