"""
Smoke-test settings — in-memory SQLite, no external services needed.

Used exclusively by the Phase 10 smoke test script when PostgreSQL is not
available locally (Docker offline, CI-less dev machine, etc.).

NOT for formal pytest runs — those must use settings_test.py + PostgreSQL.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Minimal required env stubs so settings.py imports don't blow up ─────────
os.environ.setdefault("DATABASE_URL", "sqlite:///smoke_placeholder")
os.environ.setdefault("SECRET_KEY", "smoke-test-not-a-secret-key-12345678901234")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ALLOWED_HOSTS", "*")

# Pull in the full app config from base settings, then override DB below.
# We set env vars FIRST so the base settings module doesn't fail-fast.
from deltacrown.settings import *  # noqa: E402, F401, F403, F811

# ── Override DB to in-memory SQLite ─────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ── Silence slow-query/migration guards ─────────────────────────────────────
SILENCED_SYSTEM_CHECKS = ["models.W042"]

# ── Celery: always-eager so tasks run synchronously in-process ──────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ── Disable external services not needed for unit smoke ─────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Riot sync overrides: no delays, all passports eligible
RIOT_SYNC_REQUIRE_VERIFIED = False
RIOT_SYNC_MAX_MATCHES = 10
RIOT_SYNC_MATCH_DELAY_SECONDS = 0.0
RIOT_SYNC_PASSPORT_DELAY_SECONDS = 0.0
RIOT_SYNC_MAX_RETRY_ATTEMPTS = 2
RIOT_SYNC_RATE_LIMIT_BACKOFF_SECONDS = 0.0

# Media/static stubs
MEDIA_ROOT = BASE_DIR / "media"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Logging: only show warnings and above during smoke run ───────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "apps.user_profile.tasks": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
