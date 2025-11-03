"""
DeltaCrown Tournament Engine - Development Settings
===================================================
Settings for local development environment.
"""
from .base import *

# =============================================================================
# Debug & Development
# =============================================================================
DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# CSRF trusted origins for local development
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://192.168.0.153:8000',
    'http://192.168.68.100:8000',
    'https://*.ngrok-free.app',  # For ngrok testing
]

# =============================================================================
# Database - Local PostgreSQL
# =============================================================================
# Uses environment variables from .env file
# Default: postgresql://deltacrown_user:dev_password@localhost:5432/deltacrown_dev

# =============================================================================
# Cache - Use Redis or fallback to locmem
# =============================================================================
# Uses REDIS_URL from .env if available
# Fallback to in-memory cache for quick testing
if not env('REDIS_URL', default=None):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# =============================================================================
# Email - Console Backend for Development
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =============================================================================
# Static & Media Files
# =============================================================================
# Django's development server will serve static files automatically
# No need for collectstatic in development

# =============================================================================
# Security - Relaxed for Development
# =============================================================================
SECRET_KEY = env('DJANGO_SECRET_KEY', default='dev-insecure-change-me-only-for-development')

# Session
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF
CSRF_COOKIE_SECURE = False

# =============================================================================
# CORS - Allow All Origins in Development
# =============================================================================
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# Celery - Synchronous in Development (Optional)
# =============================================================================
# Uncomment to run tasks synchronously (no Celery worker needed)
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True

# =============================================================================
# Django Channels - In-Memory for Development
# =============================================================================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# =============================================================================
# Logging - More Verbose in Development
# =============================================================================
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['deltacrown']['level'] = 'DEBUG'

# Add SQL query logging (useful for debugging)
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}

# =============================================================================
# Development Tools
# =============================================================================
# Django Debug Toolbar (if installed)
if 'django_debug_toolbar' in INSTALLED_APPS:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Django Extensions (if installed)
try:
    import django_extensions
    INSTALLED_APPS += ['django_extensions']
except ImportError:
    pass

# =============================================================================
# Testing Optimizations
# =============================================================================
# Fast password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# =============================================================================
# Feature Flags - All Enabled in Development
# =============================================================================
ENABLE_REGISTRATION = True
ENABLE_PAYMENT_GATEWAY = True
ENABLE_SOCIAL_AUTH = env.bool('ENABLE_ALLAUTH', default=False)

# =============================================================================
# Optional: django-allauth (Social Authentication)
# =============================================================================
if env.bool('ENABLE_ALLAUTH', default=False):
    INSTALLED_APPS += [
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'allauth.socialaccount.providers.google',
    ]
    AUTHENTICATION_BACKENDS += [
        'allauth.account.auth_backends.AuthenticationBackend',
    ]
    ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
    ACCOUNT_EMAIL_REQUIRED = True
    ACCOUNT_EMAIL_VERIFICATION = 'optional'
    ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
    ACCOUNT_USERNAME_REQUIRED = True

# =============================================================================
# Development Utilities
# =============================================================================
# Show more detailed error pages
ADMINS = [('Developer', 'dev@deltacrown.com')]
MANAGERS = ADMINS

# Print settings on startup (optional - uncomment for debugging)
# print(f"🚀 Development server starting...")
# print(f"   DEBUG: {DEBUG}")
# print(f"   DATABASE: {DATABASES['default']['NAME']}")
# print(f"   CACHE: {CACHES['default']['BACKEND']}")
