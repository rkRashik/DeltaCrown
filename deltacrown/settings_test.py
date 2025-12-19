"""
Django settings for test environment.

Implements:
    - Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#test-environment
    - Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md#testing-standards

Optimizes test execution by:
- Using in-memory channel layer (no Redis)
- Faster password hashing
- Disabling rate limiting
- Test-specific database configuration
"""

from .settings import *

# Use in-memory channel layer (no Redis required for tests)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# Disable rate limiting in tests
WS_RATE_ENABLED = False

# Allow all origins in tests (no origin validation)
WS_ALLOWED_ORIGINS = []  # Empty list = allow all origins

# Max payload size for WebSocket messages (16 KB)
WS_MAX_PAYLOAD_BYTES = 16384

# Faster password hashing for tests (significant speedup)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable debug toolbar in tests
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]

# Use console email backend in tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Sentry in tests
SENTRY_DSN = None

# Test database configuration with local Postgres fallback
# Phase 0 Refactor: Support local Postgres when Neon user can't create test DB
import os

# Check if we should use local test database
use_local_test_db = os.environ.get('USE_LOCAL_TEST_DB', 'false').lower() == 'true'

if use_local_test_db:
    # Use local Postgres for tests (fallback when Neon doesn't allow test DB creation)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('LOCAL_TEST_DB_NAME', 'test_deltacrown'),
            'USER': os.environ.get('LOCAL_TEST_DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('LOCAL_TEST_DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('LOCAL_TEST_DB_HOST', 'localhost'),
            'PORT': os.environ.get('LOCAL_TEST_DB_PORT', '5432'),
            'TEST': {
                'NAME': os.environ.get('LOCAL_TEST_DB_NAME', 'test_deltacrown'),
            },
        }
    }
    print(f"\n[WARNING] Using local test database: {DATABASES['default']['NAME']}@{DATABASES['default']['HOST']}\n")
else:
    # Keep existing DATABASE_URL configuration but mark test DB name
    DATABASES['default']['TEST'] = {
        'NAME': 'test_deltacrown',
    }
    print("\n[WARNING] Using DATABASE_URL for tests (may fail if user can't create DB)\n")
    print("[INFO] To use local Postgres, set: USE_LOCAL_TEST_DB=true\n")

# Disable logging during tests (unless --log-cli is passed)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',  # Only show warnings and errors
    },
}
