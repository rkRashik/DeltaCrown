"""
DeltaCrown Tournament Engine - Production Settings
==================================================
Settings for production environment.
"""
from .base import *

# =============================================================================
# Debug & Security
# =============================================================================
DEBUG = False

# Specific allowed hosts (must be set)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')  # Must be provided in production

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS')

# =============================================================================
# Security Settings (Strict)
# =============================================================================
SECRET_KEY = env('DJANGO_SECRET_KEY')  # Must be set, no default

# Session Security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# CSRF Security
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_USE_SESSIONS = True

# Security Middleware Settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# =============================================================================
# Database - Production PostgreSQL with Optimizations
# =============================================================================
# Uses DATABASE_URL from environment
# Connection pooling is critical in production
DATABASES['default']['CONN_MAX_AGE'] = 600

# Enable database connection health checks
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# =============================================================================
# Cache - Redis (Required in Production)
# =============================================================================
CACHES['default']['OPTIONS']['IGNORE_EXCEPTIONS'] = False  # Fail loudly in production

# =============================================================================
# Email - Production SMTP
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = env('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# =============================================================================
# Static & Media Files - AWS S3
# =============================================================================
# Use django-storages for cloud storage

# AWS S3 Configuration
USE_S3 = env.bool('USE_S3', default=True)

if USE_S3:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = env(
        'AWS_S3_CUSTOM_DOMAIN',
        default=f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    )
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # 1 day
    }
    AWS_QUERYSTRING_AUTH = False
    
    # Static files
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    
    # Media files
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# =============================================================================
# Logging - Production with Rotation + Sentry
# =============================================================================
# File logging
LOGGING['handlers']['file']['filename'] = '/var/log/deltacrown/production.log'
LOGGING['handlers']['error_file']['filename'] = '/var/log/deltacrown/production-errors.log'

# Sentry Error Tracking (Highly Recommended for Production)
SENTRY_DSN = env('SENTRY_DSN', default=None)
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        environment='production',
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% of transactions
        send_default_pii=False,  # Don't send user data
        before_send=lambda event, hint: event if not DEBUG else None,
    )

# =============================================================================
# CORS - Specific Origins Only
# =============================================================================
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# Celery - Production Configuration
# =============================================================================
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# =============================================================================
# Django Channels - Redis Channel Layer
# =============================================================================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL')],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# =============================================================================
# Admin & Staff
# =============================================================================
ADMINS = env.list('ADMINS')
MANAGERS = ADMINS

# =============================================================================
# REST Framework - Production Rate Limiting
# =============================================================================
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '50/hour',  # Stricter for production
    'user': '500/hour',
}

# =============================================================================
# Feature Flags - Controlled via Environment
# =============================================================================
ENABLE_REGISTRATION = env.bool('ENABLE_REGISTRATION', default=True)
ENABLE_PAYMENT_GATEWAY = env.bool('ENABLE_PAYMENT_GATEWAY', default=True)
ENABLE_SOCIAL_AUTH = env.bool('ENABLE_SOCIAL_AUTH', default=False)

# =============================================================================
# Performance Optimizations
# =============================================================================
# Template caching
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# =============================================================================
# Monitoring & Health Checks
# =============================================================================
# Add health check endpoints for load balancers
# /healthz/ is already configured in urls.py

# =============================================================================
# Backup & Disaster Recovery
# =============================================================================
# Database backups should be configured at infrastructure level
# Recommendation: Daily automated backups with 30-day retention
