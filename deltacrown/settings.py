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
# Applications
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
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
    # allauth is optional; enabled via ENABLE_ALLAUTH=1. See conditional block below.

    # Local apps
    "apps.common",
    "apps.corelib",
    "apps.teams",
    "apps.tournaments.apps.TournamentsConfig",
    "apps.game_valorant",
    "apps.game_efootball",
    "apps.user_profile",
    "apps.notifications",
    "apps.ecommerce",
    "apps.economy",
    "apps.siteui",
    "apps.accounts",
    "channels",

]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
# DRF (minimal, fine for tests)
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
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
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

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