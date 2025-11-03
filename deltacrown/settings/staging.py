"""
DeltaCrown Tournament Engine - Staging Settings
===============================================
Settings for staging environment (pre-production testing).
"""
from .base import *

# =============================================================================
# Debug & Security
# =============================================================================
DEBUG = env.bool('DJANGO_DEBUG', default=False)

# Specific allowed hosts
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['staging.deltacrown.com'])

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=['https://staging.deltacrown.com']
)

# =============================================================================
# Security Settings
# =============================================================================
SECRET_KEY = env('DJANGO_SECRET_KEY')  # Must be set in environment

# Session Security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# CSRF Security
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Security Middleware Settings
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# =============================================================================
# Database - Production PostgreSQL
# =============================================================================
# Uses DATABASE_URL from environment
# Example: postgresql://user:password@host:5432/database

# =============================================================================
# Cache - Redis (Required)
# =============================================================================
# Uses REDIS_URL from environment

# =============================================================================
# Email - SMTP (Gmail or SendGrid)
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@deltacrown.com')

# =============================================================================
# Static & Media Files - AWS S3 or Similar
# =============================================================================
# Use django-storages for cloud storage in staging/production

# Uncomment and configure for AWS S3
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
# AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
# AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
# AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
# AWS_DEFAULT_ACL = 'public-read'
# AWS_S3_OBJECT_PARAMETERS = {
#     'CacheControl': 'max-age=86400',
# }

# =============================================================================
# Logging - File-based with Rotation
# =============================================================================
LOGGING['handlers']['file']['filename'] = '/var/log/deltacrown/staging.log'
LOGGING['handlers']['error_file']['filename'] = '/var/log/deltacrown/staging-errors.log'

# Add Sentry for error tracking (optional)
# SENTRY_DSN = env('SENTRY_DSN', default=None)
# if SENTRY_DSN:
#     import sentry_sdk
#     from sentry_sdk.integrations.django import DjangoIntegration
#     sentry_sdk.init(
#         dsn=SENTRY_DSN,
#         integrations=[DjangoIntegration()],
#         environment='staging',
#         traces_sample_rate=0.1,
#         send_default_pii=False,
#     )

# =============================================================================
# CORS - Specific Origins Only
# =============================================================================
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'https://staging.deltacrown.com',
    ]
)

# =============================================================================
# Celery - Redis Broker
# =============================================================================
# Uses CELERY_BROKER_URL from environment

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
ADMINS = env.list('ADMINS', default=[('Admin', 'admin@deltacrown.com')])
MANAGERS = ADMINS

# =============================================================================
# Feature Flags - Controlled via Environment
# =============================================================================
ENABLE_REGISTRATION = env.bool('ENABLE_REGISTRATION', default=True)
ENABLE_PAYMENT_GATEWAY = env.bool('ENABLE_PAYMENT_GATEWAY', default=False)
ENABLE_SOCIAL_AUTH = env.bool('ENABLE_SOCIAL_AUTH', default=False)
