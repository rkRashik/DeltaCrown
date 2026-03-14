"""Dedicated minimal SQLite settings for fast OAuth-focused test runs."""

import os

from .settings import *


class DisableMigrations(dict):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


os.environ["DELTA_MINIMAL_TEST_APPS"] = "1"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_countries",
    "apps.accounts",
    "apps.games",
    "apps.organizations",
    "apps.user_profile",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MIGRATION_MODULES = DisableMigrations()
ROOT_URLCONF = "tests.oauth_test_urls"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

SENTRY_DSN = None

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

WS_RATE_ENABLED = False
WS_ALLOWED_ORIGINS = []

DEBUG = False
ALLOWED_HOSTS = ["*"]
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

TEAM_VNEXT_ADAPTER_ENABLED = True
TEAM_VNEXT_FORCE_LEGACY = False
TEAM_VNEXT_ROUTING_MODE = "auto"
ORG_APP_ENABLED = True
LEGACY_TEAMS_ENABLED = True
COMPETITION_APP_ENABLED = True

TEAM_LEGACY_WRITE_BLOCKED = False
TEAM_LEGACY_WRITE_BYPASS_ENABLED = True

print(f"\n{'=' * 70}")
print("TEST DATABASE: SQLite :memory:")
print(f"{'=' * 70}\n")
