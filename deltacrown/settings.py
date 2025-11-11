from pathlib import Path
import os
import sys

# -----------------------------------------------------------------------------
# Paths & Core
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"

# --- ALLOWED_HOSTS / CSRF (add your LAN IP here) ---
ALLOWED_HOSTS = [
    "localhost", "127.0.0.1",
    "192.168.68.100",
    "192.168.0.153",
    # ngrok rotates:
    ".ngrok-free.app",
    # optional:
    "766cd7c77fe7.ngrok-free.app",
    # For tests and qa_smoke:
    "testserver",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://192.168.68.100:8000",
    "http://192.168.0.153:8000",
    # CSRF origins MUST include scheme; allow all ngrok subdomains:
    "https://*.ngrok-free.app",
    # optional: (not required if using wildcard)
    "https://766cd7c77fe7.ngrok-free.app",
]

# -----------------------------------------------------------------------------
# CORS Configuration (Frontend Integration - Phase 3 Prep)
# -----------------------------------------------------------------------------
# Implements: Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#frontend-integration
# Implements: Documents/FRONTEND_INTEGRATION.md#cors-configuration

# Parse comma-separated list of origins from environment
import os
_cors_allowed = os.getenv('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_allowed.split(',') if origin.strip()]

# Default frontend origins for development
if DEBUG and not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",      # React default
        "http://localhost:5173",      # Vite default
        "http://localhost:4200",      # Angular default
        "http://localhost:8080",      # Vue default
    ]

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Allowed methods for CORS requests
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Allowed headers for CORS requests
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# WebSocket CORS origins (for Channel's ASGI)
_ws_allowed = os.getenv('WS_ALLOWED_ORIGINS', '')
WS_ALLOWED_ORIGINS = [origin.strip() for origin in _ws_allowed.split(',') if origin.strip()]

if DEBUG and not WS_ALLOWED_ORIGINS:
    WS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS  # Mirror HTTP origins in dev

# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Monitoring (must be FIRST for middleware timing)
    "django_prometheus",  # Prometheus metrics (Phase 3 Prep)
    
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sites",

    # Third-party
    "django.contrib.sitemaps",
    "rest_framework",
    "django_ckeditor_5",
    "corsheaders",  # CORS headers for frontend integration
    # allauth is optional; enabled via ENABLE_ALLAUTH=1. See conditional block below.

    # Core infrastructure (MUST be first)
    "apps.core",

    # Local apps
    "apps.common",
    "apps.corelib",
    "apps.teams",
    # Legacy tournament system moved to legacy_backup/ (November 2, 2025)
    # New Tournament Engine being built (Phase 1, Module 1.2 - November 2025)
    "apps.tournaments",
    # "apps.game_valorant",
    # "apps.game_efootball",
    "apps.user_profile",
    "apps.notifications",
    "apps.ecommerce",
    "apps.economy",
    "apps.shop",
    "apps.siteui",
    "apps.accounts",
    "channels",

]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # Prometheus timing (FIRST)
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS (must be before CommonMiddleware)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",  # Prometheus timing (LAST)
]

ROOT_URLCONF = "deltacrown.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # optional templates dir
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                "apps.notifications.context_processors.notification_counts",
                "apps.common.context.ui_settings",
                "apps.common.context_processors.game_assets_context",
                "apps.common.context_homepage.homepage_context",
                "apps.siteui.context.site_settings",
                "apps.siteui.nav_context.nav_context",


            ],
            'builtins': [
                "django.templatetags.static",
                'apps.common.templatetags.seo_tags',
                'apps.common.templatetags.assets',
                'apps.common.templatetags.dashboard_widgets',
                'apps.common.templatetags.string_utils',
            ],
        },
    },
]
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "apps.notifications.context_processors.unread_notifications",
]

# ensure cache exists (in dev the locmem cache is fine)
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


WSGI_APPLICATION = "deltacrown.wsgi.application"

# -----------------------------------------------------------------------------
# Database (PostgreSQL)
#   Uses env vars when present; otherwise defaults match what you created.
# -----------------------------------------------------------------------------
DB_NAME = os.getenv("DB_NAME", "deltacrown")
DB_USER = os.getenv("DB_USER", "dc_user")          # you created: dc_user
DB_PASSWORD = os.getenv("DB_PASSWORD", "Rashik0001")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
    }
}

# -----------------------------------------------------------------------------
# Passwords, Auth, I18N
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Auth redirects
# -----------------------------------------------------------------------------
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"


# -----------------------------------------------------------------------------
# Static & Media
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Django REST Framework Configuration (Phase 2: JWT Authentication)
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # JWT authentication (Phase 2) - for API and WebSocket
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # Session auth - for browser-based requests
        "rest_framework.authentication.SessionAuthentication",
        # Basic auth - for development/testing
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# -----------------------------------------------------------------------------
# SimpleJWT Configuration (Phase 2)
# -----------------------------------------------------------------------------
from datetime import timedelta

SIMPLE_JWT = {
    # Token lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),      # 1 hour access
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),         # 7 days refresh
    
    # Token rotation for security
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    # Algorithm and signing
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    # Token headers
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    # Token validation
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    # Sliding tokens (optional)
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}

# JWT clock skew tolerance for WebSocket connections (Module 2.4: Security Hardening)
# Allows tokens to be accepted if expiry is within this many seconds
# Prevents connection failures due to slight clock differences between client/server
JWT_LEEWAY_SECONDS = int(os.getenv('JWT_LEEWAY_SECONDS', '60'))  # Default: 60 seconds


LOGIN_URL = "/account/login/"
LOGIN_REDIRECT_URL = "/account/profile/"
LOGOUT_REDIRECT_URL = "/"

# Dev email backend (password reset prints to console)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@deltacrown.local"


# Where your site runs
# SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")
SITE_URL = os.getenv("SITE_URL", "http://192.168.68.100:8000")

# Google OAuth Client
GOOGLE_OAUTH_CLIENT_ID = os.getenv("DeltaCrown_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("DeltaCrown_OAUTH_CLIENT_SECRET", "")


# --- Email (Gmail SMTP) ---
# Use console backend in tests, SMTP in dev/lan when creds present.
if os.getenv("DeltaCrownEmailAppPassword"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "deltacrownhq@gmail.com")
    EMAIL_HOST_PASSWORD = os.getenv("DeltaCrownEmailAppPassword")
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
else:
    # fallback (CI/tests)
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "no-reply@deltacrown.local"



# -----------------------------------------------------------------------------
# Email (in-memory for tests)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", EMAIL_BACKEND)

# -----------------------------------------------------------------------------
# Testing niceties
# -----------------------------------------------------------------------------
# Faster hashing during tests
if os.getenv("FAST_TESTS", "1") == "1":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



TEST_RUNNER = 'deltacrown.test_runner.CustomTestRunner'

# notifications
NOTIFICATIONS_EMAIL_ENABLED = False  # set True to email in addition to in-app



# -----------------------------------------------------------------------------
# CKEditor 5 (keep it quiet/harmless in tests)
# -----------------------------------------------------------------------------
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "bold", "italic", "underline", "|",
            "link", "bulletedList", "numberedList", "|",
            "blockQuote", "insertTable", "undo", "redo",
        ],
    }
}
CKEDITOR_5_CUSTOM_CSS = None
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"
# Sites framework (required for allauth)
SITE_ID = int(os.getenv("SITE_ID", "1"))

# Allauth authentication backends
AUTHENTICATION_BACKENDS = (
    "apps.accounts.backends.EmailOrUsernameBackend",
)

# Optional: django-allauth wiring (guarded to avoid ImportError in dev without package)
if os.getenv("ENABLE_ALLAUTH", "0") == "1":
    INSTALLED_APPS += [
        "allauth",
        "allauth.account",
        "allauth.socialaccount",
        "allauth.socialaccount.providers.google",
    ]
    AUTHENTICATION_BACKENDS = (
        "apps.accounts.backends.EmailOrUsernameBackend",
        "allauth.account.auth_backends.AuthenticationBackend",
    )
    ACCOUNT_AUTHENTICATION_METHOD = "username_email"
    ACCOUNT_EMAIL_REQUIRED = True
    ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "optional")
    ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
    ACCOUNT_USERNAME_REQUIRED = True
    ACCOUNT_ADAPTER = os.getenv("ACCOUNT_ADAPTER", "allauth.account.adapter.DefaultAccountAdapter")
    SOCIALACCOUNT_ADAPTER = os.getenv("SOCIALACCOUNT_ADAPTER", "allauth.socialaccount.adapter.DefaultSocialAccountAdapter")
    SOCIALACCOUNT_PROVIDERS = {
        "google": {
            "APP": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "key": "",
            }
        }
    }

ASGI_APPLICATION = 'deltacrown.asgi.application'

# -----------------------------------------------------------------------------
# Django Channels Configuration (Phase 2: Real-Time Features)
# -----------------------------------------------------------------------------
CHANNEL_LAYERS = {
    'default': {
        # Use Redis for production/development with Redis running
        # Falls back to InMemory for testing or when Redis unavailable
        'BACKEND': os.getenv(
            'CHANNEL_LAYERS_BACKEND',
            'channels_redis.core.RedisChannelLayer' if not DEBUG or os.getenv('USE_REDIS_CHANNELS') else 'channels.layers.InMemoryChannelLayer'
        ),
        'CONFIG': {
            "hosts": [(
                os.getenv('CHANNEL_LAYERS_HOST', 'localhost'),
                int(os.getenv('CHANNEL_LAYERS_PORT', 6379))
            )],
            # Connection pool settings
            "capacity": 1500,  # Maximum messages in queue
            "expiry": 10,      # Message expiry in seconds
        } if not DEBUG or os.getenv('USE_REDIS_CHANNELS') else {}
    }
}

# -----------------------------------------------------------------------------
# WebSocket Rate Limiting Configuration (Module 2.5)
# -----------------------------------------------------------------------------

# Message rate limits (token bucket algorithm)
WS_RATE_MSG_RPS = float(os.getenv('WS_RATE_MSG_RPS', '10.0'))  # Messages per second per user
WS_RATE_MSG_BURST = int(os.getenv('WS_RATE_MSG_BURST', '20'))  # Burst capacity per user

# IP-based message rate limits (for anonymous/unauthenticated connections)
WS_RATE_MSG_RPS_IP = float(os.getenv('WS_RATE_MSG_RPS_IP', '20.0'))  # Messages per second per IP
WS_RATE_MSG_BURST_IP = int(os.getenv('WS_RATE_MSG_BURST_IP', '40'))  # Burst capacity per IP

# Connection limits
WS_RATE_CONN_PER_USER = int(os.getenv('WS_RATE_CONN_PER_USER', '3'))  # Max concurrent connections per user
WS_RATE_CONN_PER_IP = int(os.getenv('WS_RATE_CONN_PER_IP', '10'))  # Max concurrent connections per IP

# Room limits
WS_RATE_ROOM_MAX_MEMBERS = int(os.getenv('WS_RATE_ROOM_MAX_MEMBERS', '2000'))  # Max spectators per tournament room

# Payload limits
WS_MAX_PAYLOAD_BYTES = int(os.getenv('WS_MAX_PAYLOAD_BYTES', str(16 * 1024)))  # 16 KB max message size

# Origin validation (comma-separated list of allowed origins)
# Leave empty to disable origin checking (development mode)
# Example: "https://deltacrown.com,https://www.deltacrown.com"
WS_ALLOWED_ORIGINS = os.getenv('WS_ALLOWED_ORIGINS', '')  # Empty = allow all origins (dev only)

# -----------------------------------------------------------------------------
# Celery Configuration
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task deduplication - prevent double execution
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'False') == 'True'
CELERY_TASK_EAGER_PROPAGATES = True

# -----------------------------------------------------------------------------
# Discord Webhook Configuration
# -----------------------------------------------------------------------------
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
DISCORD_NOTIFICATIONS_ENABLED = bool(DISCORD_WEBHOOK_URL)

# -----------------------------------------------------------------------------
# Notification Preferences
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Sentry Error Tracking (Phase 2: Monitoring & Logging)
# -----------------------------------------------------------------------------
SENTRY_DSN = os.getenv('SENTRY_DSN', '')

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
        # Performance monitoring
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        
        # Error sampling
        sample_rate=1.0,  # Capture 100% of errors
        
        # Send user PII (disable for GDPR compliance)
        send_default_pii=os.getenv('SENTRY_SEND_PII', 'False') == 'True',
        
        # Environment
        environment='production' if not DEBUG else 'development',
        
        # Release tracking (optional - set via CI/CD)
        release=os.getenv('SENTRY_RELEASE', None),
        
        # Before send hook (optional - filter sensitive data)
        # before_send=lambda event, hint: event if should_send_event(event) else None,
    )

# -----------------------------------------------------------------------------
# Structured Logging (Phase 2: JSON Logging)
# -----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
        # JSON formatter for production (requires python-json-logger)
        'json': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s',
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter' if os.getenv('USE_JSON_LOGGING') else 'logging.Formatter',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json' if os.getenv('USE_JSON_LOGGING') else 'simple',
        },
        'console_debug': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'deltacrown.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'json' if os.getenv('USE_JSON_LOGGING') else 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Tournament app logging (Phase 2)
        'apps.tournaments': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.tournaments.realtime': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Celery logging
        'celery': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# -----------------------------------------------------------------------------
# Security Settings (Phase 2: Production Hardening)
# -----------------------------------------------------------------------------
if not DEBUG:
    # HTTPS/SSL Configuration
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', 31536000))  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cookie security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    
    # Browser security
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Content Security Policy (optional - customize per app needs)
    # CSP_DEFAULT_SRC = ("'self'",)
    # CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
    # CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")

# -----------------------------------------------------------------------------
# Media Upload Validation (Phase 2: Security)
# -----------------------------------------------------------------------------
# Maximum upload sizes
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB for images
MAX_PAYMENT_PROOF_SIZE = 10 * 1024 * 1024  # 10MB for payment proofs

# Allowed MIME types for uploads
ALLOWED_IMAGE_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
]

ALLOWED_DOCUMENT_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
]
