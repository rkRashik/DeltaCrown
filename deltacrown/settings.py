from pathlib import Path
import os
import sys

# -----------------------------------------------------------------------------
# Paths & Core
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

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

    # Third-party
    "django.contrib.sitemaps",
    "rest_framework",
    "django_ckeditor_5",

    # Local apps
    "apps.corelib",
    "apps.teams",
    "apps.tournaments.apps.TournamentsConfig",
    "apps.game_valorant",
    "apps.game_efootball",
    "apps.user_profile",
    "apps.notifications",
    "apps.ecommerce",

]

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


            ],
            'builtins': [
                'apps.common.templatetags.seo_tags',
                'apps.common.templatetags.assets',
                'apps.common.templatetags.dashboard_widgets',
            ],
        },
    },
]
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "apps.notifications.context_processors.unread_notifications",
]


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
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

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
        "rest_framework.permissions.AllowAny",
    ],
}


# -----------------------------------------------------------------------------
# Email config (settings)
# -----------------------------------------------------------------------------

# DEFAULT_FROM_EMAIL = os.getenv("DeltaCrownEmail", "deltacrownhq@gmail.com")
# EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
# EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
# EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", DEFAULT_FROM_EMAIL)
# EMAIL_HOST_PASSWORD = os.getenv("DeltaCrownEmailAppPassword", "")  # Use a Gmail App Password

# -----------------------------------------------------------------------------
# Email (dev-safe)
# -----------------------------------------------------------------------------
# Print emails to the console during development.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "DeltaCrown <no-reply@deltacrown.local>"
SERVER_EMAIL = "errors@deltacrown.local"



# -----------------------------------------------------------------------------
# CKEditor 5 (keep it quiet/harmless in tests)
# -----------------------------------------------------------------------------
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": "full",
    }
}
CKEDITOR_5_CUSTOM_CSS = None
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"

# -----------------------------------------------------------------------------
# Email (in-memory for tests)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# -----------------------------------------------------------------------------
# Testing niceties
# -----------------------------------------------------------------------------
# Faster hashing during tests
if os.getenv("FAST_TESTS", "1") == "1":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



TEST_RUNNER = 'deltacrown.test_runner.CustomTestRunner'