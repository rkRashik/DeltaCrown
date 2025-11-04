"""
DeltaCrown Tournament Engine - Base Settings
=============================================
Common settings shared across all environments (development, staging, production).
Environment-specific settings should override these in their respective files.
"""
import os
from pathlib import Path
import environ

# Initialize environ
env = environ.Env(
    # Set defaults
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# =============================================================================
# Security Settings
# =============================================================================
SECRET_KEY = env('DJANGO_SECRET_KEY', default='dev-insecure-secret-key-change-me-in-production')
DEBUG = env.bool('DJANGO_DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# CSRF Settings
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]
)

# =============================================================================
# Application Definition
# =============================================================================
INSTALLED_APPS = [
    # Django Core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.sitemaps',

    # Third-party Apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'django_ckeditor_5',
    'channels',
    'corsheaders',
    'widget_tweaks',

    # Core Infrastructure
    'apps.core',

    # DeltaCrown Apps
    'apps.common',
    'apps.corelib',
    'apps.accounts',
    'apps.teams',
    'apps.user_profile',
    'apps.notifications',
    'apps.ecommerce',
    'apps.economy',
    'apps.siteui',
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# =============================================================================
# Middleware
# =============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =============================================================================
# URL Configuration
# =============================================================================
ROOT_URLCONF = 'deltacrown.urls'

# =============================================================================
# Templates
# =============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Custom context processors
                'apps.notifications.context_processors.notification_counts',
                'apps.notifications.context_processors.unread_notifications',
                'apps.common.context.ui_settings',
                'apps.common.context_processors.game_assets_context',
                'apps.common.context_homepage.homepage_context',
                'apps.siteui.context.site_settings',
                'apps.siteui.nav_context.nav_context',
            ],
            'builtins': [
                'django.templatetags.static',
                'apps.common.templatetags.seo_tags',
                'apps.common.templatetags.assets',
                'apps.common.templatetags.dashboard_widgets',
                'apps.common.templatetags.string_utils',
            ],
        },
    },
]

# =============================================================================
# WSGI / ASGI
# =============================================================================
WSGI_APPLICATION = 'deltacrown.wsgi.application'
ASGI_APPLICATION = 'deltacrown.asgi.application'

# =============================================================================
# Database Configuration
# =============================================================================
DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default=f"postgresql://{env('DB_USER', default='deltacrown_user')}:"
                f"{env('DB_PASSWORD', default='dev_password')}@"
                f"{env('DB_HOST', default='localhost')}:"
                f"{env('DB_PORT', default='5432')}/"
                f"{env('DB_NAME', default='deltacrown_dev')}"
    )
}

# Connection pooling
DATABASES['default']['CONN_MAX_AGE'] = env.int('DB_CONN_MAX_AGE', default=600)
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'options': '-c search_path=public',
}

# =============================================================================
# Cache Configuration (Redis)
# =============================================================================
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            # 'PARSER_CLASS': 'redis.connection.HiredisParser',  # Commented out - requires hiredis package
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'deltacrown',
        'TIMEOUT': 300,
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# =============================================================================
# Password Validation
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# Authentication Backends
# =============================================================================
AUTHENTICATION_BACKENDS = [
    'apps.accounts.backends.EmailOrUsernameBackend',
]

# Authentication URLs
LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/account/profile/'
LOGOUT_REDIRECT_URL = '/'

# =============================================================================
# Internationalization
# =============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = env('TIME_ZONE', default='Asia/Dhaka')
USE_I18N = True
USE_TZ = True

# =============================================================================
# Static Files (CSS, JavaScript, Images)
# =============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# =============================================================================
# Media Files (User Uploads)
# =============================================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =============================================================================
# Default Primary Key Field Type
# =============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# Sites Framework
# =============================================================================
SITE_ID = env.int('SITE_ID', default=1)
SITE_URL = env('SITE_URL', default='http://localhost:8000')

# =============================================================================
# Django REST Framework
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# =============================================================================
# JWT Settings (Simple JWT)
# =============================================================================
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    
    'JTI_CLAIM': 'jti',
}

# =============================================================================
# CORS Settings
# =============================================================================
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://localhost:3000',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]
)
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# Celery Configuration
# =============================================================================
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = True

# =============================================================================
# Django Channels (WebSockets)
# =============================================================================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}

# =============================================================================
# Email Configuration
# =============================================================================
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@deltacrown.com')

# =============================================================================
# Notifications
# =============================================================================
NOTIFICATIONS_EMAIL_ENABLED = env.bool('NOTIFICATIONS_EMAIL_ENABLED', default=False)
DISCORD_WEBHOOK_URL = env('DISCORD_WEBHOOK_URL', default='')
DISCORD_NOTIFICATIONS_ENABLED = bool(DISCORD_WEBHOOK_URL)

NOTIFICATION_CHANNELS = ['in_app', 'email', 'discord']
DEFAULT_NOTIFICATION_PREFERENCES = {
    'invite_sent': ['in_app', 'email'],
    'invite_accepted': ['in_app', 'email'],
    'roster_changed': ['in_app'],
    'tournament_registered': ['in_app', 'email'],
    'match_result': ['in_app', 'email'],
    'ranking_changed': ['in_app'],
    'sponsor_approved': ['in_app', 'email'],
    'promotion_started': ['in_app'],
}

# =============================================================================
# CKEditor 5 Configuration
# =============================================================================
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': [
            'bold', 'italic', 'underline', '|',
            'link', 'bulletedList', 'numberedList', '|',
            'blockQuote', 'insertTable', 'undo', 'redo',
        ],
    }
}
CKEDITOR_5_CUSTOM_CSS = None
CKEDITOR_5_FILE_UPLOAD_PERMISSION = 'staff'

# =============================================================================
# Logging Configuration
# =============================================================================
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 30,  # Keep 30 days
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 30,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'deltacrown': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# Custom Test Runner
# =============================================================================
TEST_RUNNER = 'deltacrown.test_runner.CustomTestRunner'

# =============================================================================
# Testing Configuration
# =============================================================================
if env.bool('FAST_TESTS', default=False):
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
