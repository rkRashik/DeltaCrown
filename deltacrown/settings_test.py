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

# Test database configuration
DATABASES['default']['TEST'] = {
    'NAME': 'test_deltacrown',
}

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
