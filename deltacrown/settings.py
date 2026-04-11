from pathlib import Path
import mimetypes
import os
import sys
import socket
import dj_database_url
from urllib.parse import urlparse, parse_qs
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Module-level flag to ensure migration guard only prints once
_migration_guard_checked = False

# -----------------------------------------------------------------------------
# Paths & Core
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Deterministic .env loading - explicit path, no override
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

# Ensure .webmanifest files are served with the correct MIME type.
mimetypes.add_type('application/manifest+json', '.webmanifest', strict=True)

# Fail-fast: DATABASE_URL must be set to prevent localhost fallback
if not os.getenv("DATABASE_URL"):
    raise ImproperlyConfigured(
        "DATABASE_URL environment variable is required. "
        "DeltaCrown refuses to start without it to prevent accidental localhost usage. "
        "Create a .env file in project root with DATABASE_URL=postgresql://..."
    )

# -----------------------------------------------------------------------------
# Database URL Parsing Helper
# -----------------------------------------------------------------------------
def parse_database_url(url_string):
    """
    Parse DATABASE_URL with proper handling of quotes and query parameters.
    
    Args:
        url_string: Database URL string, may have quotes from .env
        
    Returns:
        dict: Parsed database configuration
        
    Example:
        >>> url = 'postgresql://user:pass@host:5432/db?sslmode=require'
        >>> config = parse_database_url(url)
        >>> config['NAME']
        'db'
    """
    if not url_string:
        return None
        
    # Strip leading/trailing quotes that might come from .env
    url_string = url_string.strip()
    if url_string.startswith(('"', "'")) and url_string.endswith(('"', "'")):
        url_string = url_string[1:-1]
    
    # Parse using dj_database_url
    config = dj_database_url.parse(url_string)
    
    # Preserve query parameters in OPTIONS
    parsed = urlparse(url_string)
    if parsed.query:
        query_params = parse_qs(parsed.query)
        # Convert query params to single values
        options = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
        config.setdefault('OPTIONS', {}).update(options)
    
    return config


def is_neon_database_url(url_string):
    """Return True when the database host points at Neon."""
    if not url_string:
        return False

    url_string = url_string.strip()
    if url_string.startswith(('"', "'")) and url_string.endswith(('"', "'")):
        url_string = url_string[1:-1]

    return (urlparse(url_string).hostname or '').endswith('neon.tech')


def is_supabase_pooler_database_url(url_string):
    """Return True when the database host points at a Supabase transaction pooler."""
    if not url_string:
        return False

    url_string = url_string.strip()
    if url_string.startswith(('"', "'")) and url_string.endswith(('"', "'")):
        url_string = url_string[1:-1]

    host = (urlparse(url_string).hostname or '').lower()
    return host.endswith('pooler.supabase.com')

def get_database_environment():
    """
    Get database URL and environment label.
    Simple production-like config: DATABASE_URL for everything, DATABASE_URL_TEST for tests.
    
    Returns:
        tuple: (db_url, label) - 'PROD' for DATABASE_URL, 'TEST' for DATABASE_URL_TEST
    """
    import sys
    
    # Tests use DATABASE_URL_TEST (enforced in conftest.py)
    is_test = (
        'test' in sys.argv or 
        'pytest' in sys.argv[0] or
        os.getenv('PYTEST_CURRENT_TEST') or
        os.getenv('DJANGO_SETTINGS_MODULE', '').endswith('_test')
    )
    
    if is_test:
        db_url = os.getenv('DATABASE_URL_TEST')
        if db_url:
            return db_url, 'TEST'
        # Fail fast if DATABASE_URL_TEST not set during tests
        sys.stderr.write("\n❌ DATABASE_URL_TEST required for tests. Set to local postgres URL.\n\n")
        sys.exit(1)
    
    # Default: use DATABASE_URL for everything (runserver, shell, migrate, etc.)
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        sys.stderr.write("\n❌ DATABASE_URL required. Set to Neon database URL.\n\n")
        sys.exit(1)
    
    return db_url, 'PROD'

def get_sanitized_db_info(db_url=None):
    """Get sanitized database info for logging (no passwords)."""
    if db_url is None:
        db_url, _ = get_database_environment()
    if not db_url:
        return {'error': 'DATABASE_URL not set'}
    
    parsed = urlparse(db_url)
    return {
        'engine': parsed.scheme,
        'host': parsed.hostname or 'unknown',
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/') if parsed.path else 'unknown',
        'user': parsed.username or 'unknown',
    }


def _database_host_resolves(db_url: str) -> bool:
    """Return True when the DB hostname resolves via local DNS."""
    try:
        host = (urlparse(db_url).hostname or '').strip()
    except Exception:
        return False

    if not host:
        return False

    try:
        socket.getaddrinfo(host, None)
        return True
    except socket.gaierror:
        return False
    except Exception:
        return False

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"

# Runtime tier controls safe defaults for connection/caching limits.
DEPLOYMENT_TIER = os.getenv("DEPLOYMENT_TIER", "starter").strip().lower()
if DEPLOYMENT_TIER not in {"free", "starter", "pro"}:
    DEPLOYMENT_TIER = "starter"

_TIER_CACHE_MAX_CONNECTIONS = {
    "free": 80,
    "starter": 200,
    "pro": 400,
}[DEPLOYMENT_TIER]

_TIER_DB_CONN_MAX_AGE_POOLED = {
    # Transaction poolers (Neon/Supabase) can drop or recycle backend sockets.
    # CONN_MAX_AGE=0 avoids stale-connection reuse against pooled endpoints.
    # Override with DB_CONN_MAX_AGE_POOLED, DB_CONN_MAX_AGE_NEON, or
    # DB_CONN_MAX_AGE_SUPABASE_POOLER when needed.
    "free": 0,
    "starter": 0,
    "pro": 0,
}[DEPLOYMENT_TIER]

_TIER_DB_CONN_MAX_AGE_DEFAULT = {
    "free": 300,
    "starter": 600,
    "pro": 900,
}[DEPLOYMENT_TIER]

# Safety: refuse to run with the placeholder secret key in production
if not DEBUG and SECRET_KEY == "dev-insecure-secret-key-change-me":
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set in production. "
        "Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    )

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------
# vNext: Organizations & Competition Migration Flags
# See docs/vnext/org-migration-plan.md for migration roadmap

# Competition app: Gated behind feature flag to prevent runtime errors
# when database schema not yet migrated. Set COMPETITION_APP_ENABLED=1 to enable.
COMPETITION_APP_ENABLED = os.getenv("COMPETITION_APP_ENABLED", "0") == "1"

# Organizations app: Enable new Organizations hub and team management
# Default: True (new approach is default, legacy is fallback)
ORG_APP_ENABLED = os.getenv("ORG_APP_ENABLED", "1") == "1"

# Legacy Teams app: Keep legacy team views available as fallback
# Default: True (for compatibility during migration)
LEGACY_TEAMS_ENABLED = os.getenv("LEGACY_TEAMS_ENABLED", "1") == "1"

# Discord Bot: Defaults to disabled on free tier to save ~50-150 MB RAM.
# Set ENABLE_DISCORD_BOT=1 in Render env vars to activate.
ENABLE_DISCORD_BOT = os.getenv("ENABLE_DISCORD_BOT", "0") == "1"

# --- ALLOWED_HOSTS / CSRF (add your LAN IP here) ---
ALLOWED_HOSTS = [
    "localhost", "127.0.0.1",
    "192.168.68.101",
    "192.168.0.153",
    # ngrok rotates:
    ".ngrok-free.app",
    # optional:
    "766cd7c77fe7.ngrok-free.app",
    # For tests and qa_smoke:
    "testserver",
    # Production (Render + Cloudflare)
    "deltacrown.xyz",
    ".deltacrown.xyz",
    ".onrender.com",
]

# Merge extra hosts from env (Render sets ALLOWED_HOSTS or RENDER_EXTERNAL_HOSTNAME)
_extra_hosts = os.getenv("ALLOWED_HOSTS", "")
if _extra_hosts:
    ALLOWED_HOSTS += [h.strip() for h in _extra_hosts.split(",") if h.strip()]
_render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://192.168.68.100:8000",
    "http://192.168.0.153:8000",
    # CSRF origins MUST include scheme; allow all ngrok subdomains:
    "https://*.ngrok-free.app",
    # optional: (not required if using wildcard)
    "https://766cd7c77fe7.ngrok-free.app",
    # Production (Cloudflare)
    "https://deltacrown.xyz",
    "https://www.deltacrown.xyz",
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
# Detect if django-unfold is available (not installed in system Python)
try:
    import unfold  # noqa: F401
    _HAS_UNFOLD = True
except ImportError:
    _HAS_UNFOLD = False

INSTALLED_APPS = [
    # ASGI server (must be FIRST to override runserver with Daphne)
    "daphne",

    # Monitoring (must be early for middleware timing)
    "django_prometheus",  # Prometheus metrics (Phase 3 Prep)
    
    # Admin theme (must be BEFORE django.contrib.admin)
    *([  "unfold", "unfold.contrib.forms"] if _HAS_UNFOLD else []),

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
    "drf_spectacular",  # OpenAPI 3 schema generation (Phase 9, Epic 9.1)
    "django_ckeditor_5",
    "django_countries",  # UP.3 Extension: Country field with flags
    "corsheaders",  # CORS headers for frontend integration
    # allauth is optional; enabled via ENABLE_ALLAUTH=1. See conditional block below.

    # Core infrastructure (MUST be first)
    "apps.core",

    # Local apps
    "apps.common",
    "apps.corelib",
    "apps.match_engine",  # Phase 6: Match room engine (consumer, pipeline) — before games (re-exports)
    "apps.brackets",  # Phase 6: Bracket models & generation services — before tournaments (re-exports)
    "apps.games",  # Phase 3: Centralized game configuration
    "apps.organizations.apps.OrganizationsConfig",  # ALL team/org logic
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
    "apps.moderation",  # Phase 8: Admin & Moderation (sanctions, audit, reports)
    "apps.leaderboards",  # Phase E/F: Leaderboards Service + Engine V2
    "apps.spectator",  # Phase G: Spectator Live Views
    "apps.support",  # FAQ, Contact, Testimonials
    "apps.challenges",  # Phase B: Challenge Hub (wager matches, bounties)
    "channels",

]

# Phase 3A-C0: Conditionally enable competition app if database ready
if COMPETITION_APP_ENABLED:
    INSTALLED_APPS.append("apps.competition")  # Phase 3A-B: Multi-game ranking & match reporting

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # Prometheus timing (FIRST)
    "deltacrown.metrics.MetricsMiddleware",  # Module 9.5: Metrics collection
    "django.middleware.security.SecurityMiddleware",
    "deltacrown.middleware.security_headers.CSPMiddleware",  # Content Security Policy
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Serve static files on Render/production
    "deltacrown.middleware.media_proxy.MediaProxyMiddleware",  # Dev: proxy missing media to production
    "corsheaders.middleware.CorsMiddleware",  # CORS (must be before CommonMiddleware)
    "deltacrown.middleware.bot_probe.BotProbeShieldMiddleware",  # Fast-fail scanner probes
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "deltacrown.middleware.logging.RequestLoggingMiddleware",  # Module 9.5: Request logging (AFTER auth)
    "deltacrown.middleware.platform_prefs_middleware.UserPlatformPrefsMiddleware",  # PHASE-5A: Global platform preferences
    "apps.accounts.deletion_middleware.BlockScheduledDeletionMiddleware",  # Phase 3B: Block scheduled deletions
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.tournaments.api.toc.audit_middleware.TOCAuditMiddleware",  # TOC Sprint 11: Audit trail for TOC write ops
    "django_prometheus.middleware.PrometheusAfterMiddleware",  # Prometheus timing (LAST)
]

# TEMP: PHASE4_STEP4_2 - Add deprecated endpoint tracer in DEBUG mode - REMOVE AFTER FIX
if DEBUG:
    MIDDLEWARE.insert(4, "deltacrown.middleware.debug_deprecated.DeprecatedEndpointTracerMiddleware")

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
                "apps.common.context_processors.user_platform_prefs",  # PHASE-5A: Global platform prefs


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
    "apps.organizations.context_processors.vnext_feature_flags",  # vNext feature flags for UI gating
]

# -----------------------------------------------------------------------------
# Redis DB Isolation (TASK-010)
# DB 0 = Cache, DB 1 = Celery Broker, DB 2 = Celery Results, DB 3 = Channels
# Uses a single REDIS_URL and appends /N for each subsystem.
# -----------------------------------------------------------------------------
def _redis_url_with_db(base_url: str, db: int) -> str:
    """Append or replace the DB number on a Redis URL.

    Upstash only supports logical DB 0 — any other DB number raises
    "Only 0th database is supported!".  Force db=0 when the host is on
    upstash.io so Channels (/3), Celery broker (/1) and results (/2)
    all resolve to the single supported database.
    """
    if not base_url:
        return base_url
    import re
    if 'upstash.io' in base_url:
        db = 0
    return re.sub(r'/\d*$', '', base_url.rstrip('/')) + f'/{db}'

_BASE_REDIS_URL = os.getenv("REDIS_URL", "")

# Cache: Redis in production (shared across workers), local memory for dev
_CACHE_REDIS = _redis_url_with_db(_BASE_REDIS_URL, 0) if _BASE_REDIS_URL else None
if _CACHE_REDIS and not DEBUG:
    # Keep Redis cache IO fail-fast to avoid long request stalls on free-tier networking jitter.
    _cache_socket_timeout = float(os.getenv("CACHE_REDIS_SOCKET_TIMEOUT", "2.0"))
    _cache_connect_timeout = float(os.getenv("CACHE_REDIS_CONNECT_TIMEOUT", "2.0"))
    _cache_max_connections = int(
        os.getenv("CACHE_REDIS_MAX_CONNECTIONS", str(_TIER_CACHE_MAX_CONNECTIONS))
    )
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _CACHE_REDIS,
            "KEY_PREFIX": "dc",
            "OPTIONS": {
                "socket_timeout": _cache_socket_timeout,
                "socket_connect_timeout": _cache_connect_timeout,
                "retry_on_timeout": True,
                "health_check_interval": 30,
                "max_connections": _cache_max_connections,
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "deltacrown-local",
            "TIMEOUT": 300,
            "OPTIONS": {
                "MAX_ENTRIES": 1000,
                "CULL_FREQUENCY": 3,
            },
        }
    }

# CRITICAL: Keep auth/session flow independent from Redis/cache outages.
# Free-tier Redis quotas or DNS/connectivity issues must not break session middleware.
_SESSION_ENGINE_OVERRIDE = os.getenv("SESSION_ENGINE", "").strip()
if _SESSION_ENGINE_OVERRIDE:
    SESSION_ENGINE = _SESSION_ENGINE_OVERRIDE
elif not DEBUG:
    # cached_db keeps DB as source-of-truth while dramatically reducing read load.
    # It works with Redis (preferred) and degrades to configured cache backend.
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
else:
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

SESSION_CACHE_ALIAS = os.getenv("SESSION_CACHE_ALIAS", "default")


WSGI_APPLICATION = "deltacrown.wsgi.application"

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------
# Simple production-standard database config:
# - DATABASE_URL: Runtime database (Neon production)
# - DATABASE_URL_TEST: Test database (local Postgres only)
#
# Tests use DATABASE_URL_TEST (enforced in conftest.py).
# Everything else (runserver, shell, migrate, admin) uses DATABASE_URL.

# Determine which database to use
database_url, db_label = get_database_environment()

# Local dev safety valve: if Neon DNS is temporarily unavailable, fall back to
# DATABASE_URL_TEST to keep runserver usable. This path is DEBUG-only and opt-in.
if DEBUG and db_label == 'PROD':
    _allow_dns_fallback = os.getenv('DB_FALLBACK_TO_TEST_ON_DNS_FAILURE', '1').lower() == 'true' or os.getenv('DB_FALLBACK_TO_TEST_ON_DNS_FAILURE', '1') == '1'
    _fallback_test_url = os.getenv('DATABASE_URL_TEST', '')
    if _allow_dns_fallback and _fallback_test_url and not _database_host_resolves(database_url):
        sys.stderr.write(
            "\n⚠️ DATABASE_URL host DNS lookup failed in DEBUG mode; using DATABASE_URL_TEST fallback.\n\n"
        )
        database_url = _fallback_test_url
        db_label = 'TEST_FALLBACK'

if not database_url:
    raise ImproperlyConfigured(
        "No database URL configured. Set:\n"
        "  DATABASE_URL       - Neon database (runtime)\n"
        "  DATABASE_URL_TEST  - Local Postgres (tests only)\n"
    )

# Parse database URL with robust quote handling
db_config = parse_database_url(database_url)
if not db_config:
    raise ImproperlyConfigured(f"Failed to parse database URL for {db_label} environment")

is_neon_database = is_neon_database_url(database_url)
is_supabase_pooler_database = is_supabase_pooler_database_url(database_url)
is_pooled_database = is_neon_database or is_supabase_pooler_database

# Apply optimized connection settings
# Pooled DB endpoints (Neon/Supabase pooler) can recycle backend connections.
# Keep CONN_MAX_AGE=0 by default for pooled endpoints; keep health checks enabled
# so any explicit nonzero override still validates reused sockets first.
if is_neon_database:
    db_config['CONN_MAX_AGE'] = int(
        os.getenv(
            'DB_CONN_MAX_AGE_NEON',
            os.getenv('DB_CONN_MAX_AGE_POOLED', str(_TIER_DB_CONN_MAX_AGE_POOLED)),
        )
    )
elif is_supabase_pooler_database:
    db_config['CONN_MAX_AGE'] = int(
        os.getenv(
            'DB_CONN_MAX_AGE_SUPABASE_POOLER',
            os.getenv('DB_CONN_MAX_AGE_POOLED', str(_TIER_DB_CONN_MAX_AGE_POOLED)),
        )
    )
else:
    db_config['CONN_MAX_AGE'] = int(
        os.getenv('DB_CONN_MAX_AGE_DEFAULT', str(_TIER_DB_CONN_MAX_AGE_DEFAULT))
    )
db_config['CONN_HEALTH_CHECKS'] = os.getenv('DB_CONN_HEALTH_CHECKS', 'True').lower() == 'true'

# Connection hardening for pooled endpoints (handles pooler timeout / dropped sockets)
if is_pooled_database:
    db_config.setdefault('OPTIONS', {}).update({
        'sslmode': 'require',
        'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '5')),  # fail fast on pooler/cold-start stalls
        'keepalives': 1,                      # enable TCP keepalives
        'keepalives_idle': 30,                # idle seconds before first probe
        'keepalives_interval': 10,            # seconds between probes
        'keepalives_count': 5,                # failed probes before giving up
    })
    db_config['DISABLE_SERVER_SIDE_CURSORS'] = (
        os.getenv('DB_DISABLE_SERVER_SIDE_CURSORS', 'True').lower() == 'true'
    )

DATABASES = {
    'default': db_config
}

# Store database environment label
DB_ENVIRONMENT = db_label

# Show connection info in debug mode
if DEBUG:
    db_info = get_sanitized_db_info(database_url)
    print(f"[{db_label}] {db_info['host']}:{db_info['port']}/{db_info['database']}")

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

# Request body limit — keep low on 512 MB tier to prevent concurrent-upload RAM spikes.
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB (Django default)

# -----------------------------------------------------------------------------
# Storage Backends (Django 5.x STORAGES dict)
# -----------------------------------------------------------------------------
STORAGES = {
    "staticfiles": {
        "BACKEND": "deltacrown.storage.RobustStaticFilesStorage",
    },
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"
        if os.getenv("CLOUDINARY_URL")
        else "django.core.files.storage.FileSystemStorage",
    },
}

# WhiteNoise: immutable cache headers for hashed static assets (1 year).
# CompressedManifestStaticFilesStorage adds content hashes to filenames,
# making aggressive caching safe.
WHITENOISE_MAX_AGE = 31536000  # 1 year in seconds

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
        # Basic auth - dev only (sends credentials in cleartext)
        *([
            "rest_framework.authentication.BasicAuthentication",
        ] if DEBUG else []),
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON_RATE", "100/hour"),
        "user": os.getenv("THROTTLE_USER_RATE", "1000/hour"),
        "discovery_read": os.getenv("THROTTLE_DISCOVERY_READ_RATE", "240/min"),
        "analytics_read": os.getenv("THROTTLE_ANALYTICS_READ_RATE", "180/min"),
        "leaderboard_read": os.getenv("THROTTLE_LEADERBOARD_READ_RATE", "120/min"),
        "registration_write": os.getenv("THROTTLE_REGISTRATION_WRITE_RATE", "90/min"),
        "results_inbox_read": os.getenv("THROTTLE_RESULTS_INBOX_READ_RATE", "180/min"),
        "results_inbox_write": os.getenv("THROTTLE_RESULTS_INBOX_WRITE_RATE", "60/min"),
        "match_ops_read": os.getenv("THROTTLE_MATCH_OPS_READ_RATE", "180/min"),
        "match_ops_write": os.getenv("THROTTLE_MATCH_OPS_WRITE_RATE", "90/min"),
        "login": os.getenv("THROTTLE_LOGIN_RATE", "10/min"),
        "password_reset": os.getenv("THROTTLE_PASSWORD_RESET_RATE", "5/min"),
        "payout_write": os.getenv("THROTTLE_PAYOUT_WRITE_RATE", "20/min"),
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Module 9.5: Custom exception handler for consistent error responses
    "EXCEPTION_HANDLER": "deltacrown.exception_handlers.custom_exception_handler",
    # Phase 9, Epic 9.1: OpenAPI schema generation with drf-spectacular
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# -----------------------------------------------------------------------------
# drf-spectacular Configuration (Phase 9, Epic 9.1)
# -----------------------------------------------------------------------------
# OpenAPI 3.0 schema generation for API documentation
# Implements: Phase 9, Epic 9.1 - API Documentation Generator
# Documentation: PHASE9_EPIC91_COMPLETION_SUMMARY.md

SPECTACULAR_SETTINGS = {
    "TITLE": "DeltaCrown Tournament Platform API",
    "DESCRIPTION": (
        "Comprehensive REST API for the DeltaCrown esports tournament platform. "
        "Supports tournament management, team registration, match scheduling, "
        "results submission, dispute resolution, user/team statistics, analytics, "
        "and leaderboards across 11+ games."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    
    # API contact and license
    "CONTACT": {
        "name": "DeltaCrown API Support",
        "email": "api@deltacrown.com",
    },
    "LICENSE": {
        "name": "Proprietary",
    },
    
    # Authentication schemes
    "SECURITY": [
        {
            "bearerAuth": [],  # JWT authentication
        },
        {
            "cookieAuth": [],  # Session authentication
        },
    ],
    "AUTHENTICATION_WHITELIST": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    
    # Schema generation settings
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "filter": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
    "SWAGGER_UI_FAVICON_HREF": "/static/favicon.ico",
    
    # Schema customization
    "SCHEMA_PATH_PREFIX": r"/api/",
    "SERVE_PERMISSIONS": [
        "rest_framework.permissions.AllowAny" if DEBUG
        else "rest_framework.permissions.IsAdminUser"
    ],
    "SERVE_AUTHENTICATION": None if DEBUG else [
        "rest_framework.authentication.SessionAuthentication",
    ],
    
    # Response wrapping
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
    
    # Tags grouping
    "TAGS": [
        {"name": "Registration", "description": "Tournament registration operations"},
        {"name": "Eligibility", "description": "Registration eligibility checks"},
        {"name": "Payments", "description": "Entry fee payment processing"},
        {"name": "Tournaments", "description": "Tournament lifecycle management"},
        {"name": "Matches", "description": "Match scheduling and management"},
        {"name": "Results", "description": "Match result submission and approval"},
        {"name": "Disputes", "description": "Dispute creation and resolution"},
        {"name": "Scheduling", "description": "Manual match scheduling"},
        {"name": "Staffing", "description": "Staff assignment and management"},
        {"name": "MOCC", "description": "Match Organizer Control Center"},
        {"name": "Audit Logs", "description": "Audit trail and compliance"},
        {"name": "User Stats", "description": "Individual user statistics"},
        {"name": "Team Stats", "description": "Team statistics and rankings"},
        {"name": "Match History", "description": "Historical match records"},
        {"name": "Analytics", "description": "Advanced analytics and insights"},
        {"name": "Leaderboards", "description": "Competitive leaderboards"},
        {"name": "Seasons", "description": "Seasonal ranking management"},
    ],
    
    # Enum generation
    "ENUM_NAME_OVERRIDES": {
        "TournamentStatusEnum": "apps.tournaments.models.Tournament.status.field.choices",
        "MatchStatusEnum": "apps.matches.models.Match.status.field.choices",
        "DisputeStatusEnum": "apps.disputes.models.Dispute.status.field.choices",
    },
    
    # Extensions for custom serializers
    "PREPROCESSING_HOOKS": [
        "apps.api.schema.spectacular_extensions.preprocess_dto_serializers",
    ],
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
_default_site = "https://deltacrown.xyz" if not DEBUG else "http://192.168.68.100:8000"
SITE_URL = os.getenv("SITE_URL", _default_site)

# Google OAuth Client
# Env vars: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (standard names)
# Legacy fallbacks: DeltaCrown_OAUTH_CLIENT_ID / DeltaCrown_OAUTH_CLIENT_SECRET
GOOGLE_OAUTH_CLIENT_ID = (
    os.getenv("GOOGLE_CLIENT_ID")
    or os.getenv("DeltaCrown_OAUTH_CLIENT_ID", "")
)
GOOGLE_OAUTH_CLIENT_SECRET = (
    os.getenv("GOOGLE_CLIENT_SECRET")
    or os.getenv("DeltaCrown_OAUTH_CLIENT_SECRET", "")
)

# Riot OAuth Client (RSO)
# Required env vars for Riot Sign-On flow:
# - RIOT_CLIENT_ID
# - RIOT_CLIENT_SECRET
# - RIOT_REDIRECT_URI
RIOT_CLIENT_ID = os.getenv("RIOT_CLIENT_ID", "").strip()
RIOT_CLIENT_SECRET = os.getenv("RIOT_CLIENT_SECRET", "").strip()
RIOT_REDIRECT_URI = os.getenv("RIOT_REDIRECT_URI", "").strip()
RIOT_API_KEY = os.getenv("RIOT_API_KEY", "").strip()
STEAM_API_KEY = os.getenv("STEAM_API_KEY", "").strip()
EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID", "").strip()
EPIC_CLIENT_SECRET = os.getenv("EPIC_CLIENT_SECRET", "").strip()

# Optional Riot OAuth tuning
RIOT_OAUTH_SCOPES = os.getenv("RIOT_OAUTH_SCOPES", "openid offline_access").strip() or "openid offline_access"
RIOT_OAUTH_TIMEOUT_SECONDS = int(os.getenv("RIOT_OAUTH_TIMEOUT_SECONDS", "10"))
RIOT_ACCOUNT_API_CLUSTERS = [
    cluster.strip().lower()
    for cluster in os.getenv("RIOT_ACCOUNT_API_CLUSTERS", "americas,asia,europe").split(",")
    if cluster.strip()
]


# --- Email ---
# Priority: Resend (production) > Gmail SMTP (dev/LAN) > console (CI/tests)
if os.getenv("RESEND_API_KEY"):
    # Production: Resend transactional email via SMTP relay
    # IMPORTANT: The sender domain MUST be verified in your Resend account.
    # Using gmail.com or any unverified domain → 550 rejection.
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.resend.com"
    EMAIL_PORT = 465
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
    EMAIL_HOST_USER = "resend"  # Resend uses literal "resend" as username
    EMAIL_HOST_PASSWORD = os.getenv("RESEND_API_KEY")
    DEFAULT_FROM_EMAIL = "DeltaCrown <noreply@deltacrown.xyz>"
elif os.getenv("DeltaCrownEmailAppPassword"):
    # Dev/LAN: Gmail SMTP
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "deltacrownhq@gmail.com")
    EMAIL_HOST_PASSWORD = os.getenv("DeltaCrownEmailAppPassword")
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
else:
    # Fallback (CI/tests)
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "no-reply@deltacrown.local"



# -----------------------------------------------------------------------------
# Email (in-memory for tests)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", EMAIL_BACKEND)

# Prevent SMTP connections from hanging indefinitely (seconds).
# Without this, a stuck SMTP server can block a Gunicorn worker until the
# worker-timeout fires → Render returns 502 to the user.
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))

# -----------------------------------------------------------------------------
# Testing niceties
# -----------------------------------------------------------------------------
# All existing passwords in the database are MD5-hashed (legacy).  Django's
# default PASSWORD_HASHERS does NOT include MD5, which means check_password()
# silently fails → nobody can log in.
#
# Fix: include MD5PasswordHasher at the end of the list.  PBKDF2 stays first,
# so any *new* passwords (or password changes) are hashed with PBKDF2.  When a
# user logs in with an MD5 hash, Django transparently re-hashes it to PBKDF2.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.MD5PasswordHasher",   # legacy — verify existing hashes
]

# Under pytest, use MD5-only for speed (test passwords are throwaway)
import sys as _sys
if "pytest" in _sys.modules or "_pytest" in _sys.modules:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



TEST_RUNNER = 'deltacrown.test_runner.CustomTestRunner'

# notifications
NOTIFICATIONS_EMAIL_ENABLED = False  # set True to email in addition to in-app
# Disable long-lived SSE by default on Daphne/Render to avoid request timeout churn.
# Frontends use polling as the primary live update mechanism.
NOTIFICATIONS_SSE_ENABLED = os.getenv("NOTIFICATIONS_SSE_ENABLED", "0") == "1"
NOTIFICATIONS_UNREAD_CACHE_TTL = int(os.getenv("NOTIFICATIONS_UNREAD_CACHE_TTL", "15"))



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

# Optional: Cloudinary media storage (only when deployed with CLOUDINARY_URL)
try:
    import cloudinary  # noqa: F401
    import cloudinary_storage  # noqa: F401
    INSTALLED_APPS += [
        "cloudinary",
        "cloudinary_storage",
    ]
    # Set generous upload timeout so Render ↔ Cloudinary doesn't time-out
    # on larger banners / card images (default is no timeout).
    cloudinary.config(
        timeout=30,          # 30 s per upload request
    )
except ImportError:
    pass

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
# Production (DEBUG=False): Redis via REDIS_URL env var (Upstash/Render)
# Development (DEBUG=True) : InMemoryChannelLayer (no Redis needed locally)
# Override dev → Redis:     set USE_REDIS_CHANNELS=1 in .env
# -----------------------------------------------------------------------------
_USE_REDIS_CHANNELS = (not DEBUG) or os.getenv('USE_REDIS_CHANNELS', '0') == '1'
_REDIS_CHANNEL_URL = _redis_url_with_db(_BASE_REDIS_URL, 3) if _BASE_REDIS_URL else 'redis://localhost:6379/3'

if _USE_REDIS_CHANNELS:
    # For Upstash (and any other rediss:// provider), SSL certificate
    # verification must be disabled or the TLS handshake silently fails.
    # Pass ssl_cert_reqs=None via the host dict; plain redis:// uses URL string.
    _CHANNEL_HOST = (
        {'address': _REDIS_CHANNEL_URL, 'ssl_cert_reqs': None}
        if _REDIS_CHANNEL_URL.startswith('rediss://')
        else _REDIS_CHANNEL_URL
    )
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [_CHANNEL_HOST],
                'prefix': 'dc-ws',
                'capacity': 500,   # lowered from 1500 — saves RAM on 512 MB tier
                'expiry': 10,
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
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
# DB isolation: Broker=DB1, Results=DB2 (Cache=DB0, Channels=DB3).
# CELERY_BROKER_URL / CELERY_RESULT_BACKEND env vars override if set explicitly.

def _celery_ssl_url(url: str) -> str:
    """
    Celery requires ssl_cert_reqs on rediss:// (TLS Redis) URLs or it raises:
      ValueError: A rediss:// URL must have parameter ssl_cert_reqs

    This helper appends '?ssl_cert_reqs=CERT_NONE' when the URL is a TLS Redis
    URL that doesn't already carry the parameter.  Safe no-op for plain redis://
    or any other scheme.

    Why CERT_NONE: managed Redis providers (Upstash, Render) use self-signed or
    intermediate certs that Python's ssl module can't verify by default.
    """
    if not url or not url.startswith('rediss://') or 'ssl_cert_reqs' in url:
        return url
    sep = '&' if '?' in url else '?'
    return url + sep + 'ssl_cert_reqs=CERT_NONE'


def _normalized_env_url(name: str) -> str:
    """Return a stripped env URL value, treating blank or quoted-blank as unset."""
    value = os.getenv(name, '')
    if not value:
        return ''

    value = value.strip()
    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
        value = value[1:-1].strip()

    return value


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a bool-like environment variable with a safe default."""
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

# Build defaults: append DB number then add TLS params if needed.
_celery_broker_default = _celery_ssl_url(
    _redis_url_with_db(_BASE_REDIS_URL, 1) if _BASE_REDIS_URL else 'redis://localhost:6379/1'
)
_celery_result_default = _celery_ssl_url(
    _redis_url_with_db(_BASE_REDIS_URL, 2) if _BASE_REDIS_URL else 'redis://localhost:6379/2'
)

# Use normalized env overrides so empty, whitespace-only, or quoted-empty
# values still fall back to Redis defaults instead of leaving Celery with an
# invalid broker string that can collapse to localhost AMQP defaults.
CELERY_BROKER_URL = _celery_ssl_url(_normalized_env_url('CELERY_BROKER_URL') or _celery_broker_default)
CELERY_RESULT_BACKEND = _celery_ssl_url(_normalized_env_url('CELERY_RESULT_BACKEND') or _celery_result_default)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Memory safety: recycle worker after N tasks to prevent slow leaks
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.getenv('CELERY_MAX_TASKS_PER_CHILD', '200'))
# Kill stuck/runaway tasks before they exhaust RAM
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', '120'))
CELERY_TASK_TIME_LIMIT = int(os.getenv('CELERY_TASK_TIME_LIMIT', '180'))
# Expire old results from Redis after 1 hour to prevent unbounded growth
CELERY_RESULT_EXPIRES = int(os.getenv('CELERY_RESULT_EXPIRES', '3600'))

# Local dev safety: avoid request hangs when Redis/Celery broker is not running.
# Default to eager sync execution on local Windows/dev when broker URLs are unset
# (which otherwise fall back to localhost Redis and can block on retries).
_celery_urls_unset = not _normalized_env_url('CELERY_BROKER_URL') and not _BASE_REDIS_URL
_local_windows_runtime = os.name == 'nt' and not os.getenv('RENDER')
_default_local_sync_fallback = _local_windows_runtime or (_celery_urls_unset and DEBUG)

CELERY_LOCAL_FALLBACK_SYNC = _env_bool('CELERY_LOCAL_FALLBACK_SYNC', _default_local_sync_fallback)

if CELERY_LOCAL_FALLBACK_SYNC:
    # Local-only: avoid Redis dependencies entirely.
    CELERY_BROKER_URL = _normalized_env_url('CELERY_BROKER_URL_LOCAL_FALLBACK') or 'memory://'
    CELERY_RESULT_BACKEND = _normalized_env_url('CELERY_RESULT_BACKEND_LOCAL_FALLBACK') or 'cache+memory://'

# Primary toggle: can still be overridden explicitly via env var.
CELERY_TASK_ALWAYS_EAGER = _env_bool('CELERY_TASK_ALWAYS_EAGER', CELERY_LOCAL_FALLBACK_SYNC)
CELERY_TASK_EAGER_PROPAGATES = _env_bool(
    'CELERY_TASK_EAGER_PROPAGATES',
    default=False if CELERY_TASK_ALWAYS_EAGER else True,
)
CELERY_TASK_STORE_EAGER_RESULT = _env_bool('CELERY_TASK_STORE_EAGER_RESULT', default=False)
CELERY_TASK_IGNORE_RESULT = _env_bool('CELERY_TASK_IGNORE_RESULT', default=CELERY_LOCAL_FALLBACK_SYNC)

# Fail fast when asynchronous Celery is used and broker is degraded/unreachable.
CELERY_TASK_PUBLISH_RETRY = _env_bool('CELERY_TASK_PUBLISH_RETRY', default=not CELERY_TASK_ALWAYS_EAGER)
CELERY_BROKER_CONNECTION_RETRY = _env_bool('CELERY_BROKER_CONNECTION_RETRY', default=not CELERY_TASK_ALWAYS_EAGER)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = _env_bool(
    'CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP',
    default=not CELERY_TASK_ALWAYS_EAGER,
)
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'max_retries': int(os.getenv('CELERY_BROKER_MAX_RETRIES', '0' if CELERY_TASK_ALWAYS_EAGER else '1')),
    'interval_start': float(os.getenv('CELERY_BROKER_RETRY_INTERVAL_START', '0')),
    'interval_step': float(os.getenv('CELERY_BROKER_RETRY_INTERVAL_STEP', '0.2')),
    'interval_max': float(os.getenv('CELERY_BROKER_RETRY_INTERVAL_MAX', '0.5')),
    'socket_connect_timeout': float(os.getenv('CELERY_BROKER_SOCKET_CONNECT_TIMEOUT', '1.0')),
    'socket_timeout': float(os.getenv('CELERY_BROKER_SOCKET_TIMEOUT', '1.0')),
}

# -----------------------------------------------------------------------------
# Discord Webhook Configuration
# -----------------------------------------------------------------------------
# Discord Configuration
# -----------------------------------------------------------------------------
# Global webhook (platform-level notifications)
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
DISCORD_NOTIFICATIONS_ENABLED = bool(DISCORD_WEBHOOK_URL)

# Bot integration (per-team chat & announcement sync)
# Create a bot at https://discord.com/developers/applications
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '')
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '') or os.getenv('DISCORD_APPLICATION_ID', '')  # For OAuth2 bot invite URL
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', '')  # OAuth2 client secret

# Guild / server identity
DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID', '')  # The DeltaCrown Discord Server ID

# Role IDs (set these once the bot is registered in the server)
DISCORD_LINKED_ROLE_ID = os.getenv('DISCORD_LINKED_ROLE_ID', '')  # @Linked role granted on OAuth link

# Channel IDs for platform → Discord webhook announcements
DISCORD_TOURNAMENT_ANNOUNCEMENTS_CHANNEL_ID = os.getenv('DISCORD_TOURNAMENT_ANNOUNCEMENTS_CHANNEL_ID', '')
DISCORD_MATCH_RESULTS_CHANNEL_ID = os.getenv('DISCORD_MATCH_RESULTS_CHANNEL_ID', '')

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
            'level': os.getenv('DJANGO_SERVER_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('DJANGO_REQUEST_LOG_LEVEL', 'ERROR'),
            'propagate': False,
        },
        'deltacrown.requests': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('REQUEST_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        # Startup/bootstrap loggers (free-tier noise reduction)
        'apps.core.events': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.core.registry': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.core.plugins': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.core.apps': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.accounts.apps': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.accounts.events': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.notifications.apps': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.notifications.events': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.siteui.apps': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.siteui.events': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.user_profile.apps': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps.user_profile.events': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('STARTUP_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        # Tournament app logging (Phase 2)
        'apps.tournaments': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('TOURNAMENTS_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'apps.tournaments.realtime': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('TOURNAMENTS_REALTIME_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'apps.tournaments.services.certificate_service': {
            'handlers': ['console', 'file'] if not DEBUG else ['console_debug'],
            'level': os.getenv('CERTIFICATE_SERVICE_LOG_LEVEL', 'WARNING'),
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

# Free-tier runtime hardening toggles
BOT_PROBE_SHIELD_ENABLED = os.getenv('BOT_PROBE_SHIELD_ENABLED', 'True').lower() == 'true'
REQUEST_LOG_SLOW_MS = int(os.getenv('REQUEST_LOG_SLOW_MS', '1200'))
VNEXT_FLAGS_CONTEXT_DEBUG = os.getenv('VNEXT_FLAGS_CONTEXT_DEBUG', 'False').lower() == 'true'
STARTUP_LOG_LEVEL = os.getenv('STARTUP_LOG_LEVEL', 'WARNING')
DISCOVERY_API_CACHE_TTL = int(os.getenv('DISCOVERY_API_CACHE_TTL', '45'))
ANALYTICS_API_CACHE_TTL = int(os.getenv('ANALYTICS_API_CACHE_TTL', '60'))
LEADERBOARD_API_CACHE_TTL = int(os.getenv('LEADERBOARD_API_CACHE_TTL', '30'))

# -----------------------------------------------------------------------------
# Field-Level Encryption (TASK-006: OAuth tokens at rest)
# Set FIELD_ENCRYPTION_KEY in env for production. If unset, derives from SECRET_KEY.
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# -----------------------------------------------------------------------------
FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY', None)

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

# -----------------------------------------------------------------------------
# Moderation Enforcement Feature Flags (Phase 8.3)
# -----------------------------------------------------------------------------
# Master switch: enables all moderation enforcement when True
# Default: False (no behavior change until explicitly enabled)
MODERATION_ENFORCEMENT_ENABLED = os.getenv('MODERATION_ENFORCEMENT_ENABLED', 'False').lower() == 'true'

# WebSocket enforcement: blocks CONNECT for banned/suspended users
# Requires MODERATION_ENFORCEMENT_ENABLED = True to take effect
MODERATION_ENFORCEMENT_WS = os.getenv('MODERATION_ENFORCEMENT_WS', 'False').lower() == 'true'

# Economy/Shop enforcement: blocks purchases for banned/muted users
# Requires MODERATION_ENFORCEMENT_ENABLED = True to take effect
MODERATION_ENFORCEMENT_PURCHASE = os.getenv('MODERATION_ENFORCEMENT_PURCHASE', 'False').lower() == 'true'

# Moderation policy cache: read-through cache for get_all_active_policies()
# TTL: 60 seconds, invalidated on create/revoke sanction
# Default: False (no caching, direct DB queries)
MODERATION_POLICY_CACHE_ENABLED = os.getenv('MODERATION_POLICY_CACHE_ENABLED', 'False').lower() == 'true'

# Moderation Observability (test-only, Phase 8.3 hardening)
# -----------------------------------------------------------------------------
# Event emission for enforcement decisions (disabled in production)
MODERATION_OBSERVABILITY_ENABLED = os.getenv('MODERATION_OBSERVABILITY_ENABLED', 'False').lower() == 'true'

# Sampling rate for observability events (0.0 = none, 1.0 = all)
# Only applies when MODERATION_OBSERVABILITY_ENABLED = True
MODERATION_OBSERVABILITY_SAMPLE_RATE = float(os.getenv('MODERATION_OBSERVABILITY_SAMPLE_RATE', '0.0'))

# -----------------------------------------------------------------------------
# Certificate S3 Storage Feature Flags (Module 6.5)
# -----------------------------------------------------------------------------
# Dual-write mode: Write certificates to both S3 (primary) and local FS (shadow)
# Default: False (local-only storage, no S3 uploads)
CERT_S3_DUAL_WRITE = os.getenv('CERT_S3_DUAL_WRITE', 'False').lower() == 'true'

# Read-primary mode: Prefer S3 for reads with fallback to local FS
# Default: False (read from local FS only)
CERT_S3_READ_PRIMARY = os.getenv('CERT_S3_READ_PRIMARY', 'False').lower() == 'true'

# Backfill migration job: Enable background migration of existing certificates to S3
# Default: False (migration disabled)
CERT_S3_BACKFILL_ENABLED = os.getenv('CERT_S3_BACKFILL_ENABLED', 'False').lower() == 'true'

# S3 Bucket Configuration (only used if CERT_S3_DUAL_WRITE or CERT_S3_READ_PRIMARY is True)
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'deltacrown-certificates-prod')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
MODERATION_OBSERVABILITY_SAMPLE_RATE = float(os.getenv('MODERATION_OBSERVABILITY_SAMPLE_RATE', '0.0'))

# -----------------------------------------------------------------------------
# Bracket Generation Feature Flags (Phase 3, Epic 3.1)
# -----------------------------------------------------------------------------
# Enable universal bracket engine (TournamentOps DTO-based generators)
# Default: False (use legacy bracket generation logic)
# When True: Uses BracketEngineService with pluggable generators
# Rollback: Set to False to revert to legacy implementation
# Reference: CLEANUP_AND_TESTING_PART_6.md §4.5 (Safe Rollback)
# TODO (Epic 3.4): Enable by default after bracket editor integration complete
BRACKETS_USE_UNIVERSAL_ENGINE = os.getenv('BRACKETS_USE_UNIVERSAL_ENGINE', 'False').lower() == 'true'

# -----------------------------------------------------------------------------
# Team & Organization vNext Feature Flags (Phase 3)
# -----------------------------------------------------------------------------
# Emergency killswitch: Forces ALL adapter traffic to legacy system
# Default: False (normal operation)
# Set to True for immediate rollback (no code changes required)
# Reference: Documents/Team & Organization/Execution/TEAM_ORG_VNEXT_TRACKER.md (P3-T2)
#
# Environment Variables (optional overrides):
#   TEAM_VNEXT_FORCE_LEGACY=true/false       - Emergency killswitch
#   TEAM_VNEXT_ADAPTER_ENABLED=true/false    - Enable adapter routing
#   TEAM_VNEXT_ROUTING_MODE=legacy_only|vnext_only|auto  - Routing strategy
#
# Dev Mode Defaults (DEBUG=True, no env override):
#   - ADAPTER_ENABLED = True (allows vNext access)
#   - FORCE_LEGACY = False (no emergency blocking)
#   - ROUTING_MODE = "auto" (gradual rollout mode)
#
# Production Defaults (DEBUG=False, no env override):
#   - ADAPTER_ENABLED = True (vNext fully migrated, legacy retired)
#   - FORCE_LEGACY = False (normal operation)
#   - ROUTING_MODE = "vnext_only" (100% vNext traffic)
#
TEAM_VNEXT_FORCE_LEGACY = os.getenv('TEAM_VNEXT_FORCE_LEGACY', 'False').lower() == 'true'

# vNext adapter — enabled by default (legacy migration complete)
TEAM_VNEXT_ADAPTER_ENABLED = os.getenv('TEAM_VNEXT_ADAPTER_ENABLED', 'True').lower() == 'true'

# Routing mode: Controls which backend to use
# Options: "legacy_only", "vnext_only" (default), "auto"
# - legacy_only: All traffic to legacy (emergency rollback only)
# - vnext_only: All traffic to vNext (production default)
# - auto: Use allowlist for gradual rollout
TEAM_VNEXT_ROUTING_MODE = os.getenv('TEAM_VNEXT_ROUTING_MODE', 'vnext_only')

# Allowlist: Team IDs that can use vNext in auto mode
# Default: [] (empty, no teams use vNext)
# Example: [123, 456, 789] for gradual rollout
# Only applies when ROUTING_MODE="auto"
TEAM_VNEXT_TEAM_ALLOWLIST = []

# -----------------------------------------------------------------------------
# Leaderboards Feature Flags (Phase E)
# -----------------------------------------------------------------------------
# Enable leaderboard computation (Celery tasks, service layer)
# Default: False (computation disabled, all queries return empty)
LEADERBOARDS_COMPUTE_ENABLED = os.getenv('LEADERBOARDS_COMPUTE_ENABLED', 'False').lower() == 'true'

# Enable Redis caching for leaderboard reads
# Default: False (no caching, direct DB queries)
# TTL Strategy: 5min (tournament), 1h (season), 24h (all-time)
LEADERBOARDS_CACHE_ENABLED = os.getenv('LEADERBOARDS_CACHE_ENABLED', 'False').lower() == 'true'

# Enable public API endpoints (/api/tournaments/leaderboards/...)
# Default: False (API returns 404)
# Requires COMPUTE_ENABLED=True for non-empty responses
LEADERBOARDS_API_ENABLED = os.getenv('LEADERBOARDS_API_ENABLED', 'False').lower() == 'true'

# -----------------------------------------------------------------------------
# User Profile Integration Feature Flags
# -----------------------------------------------------------------------------
# Enable User Profile ↔ Tournament integration (activity tracking, stats recompute, audit)
# Default: False (integration disabled, tournament operations unaffected)
# When True: Tournament lifecycle events trigger UserActivity, UserAuditEvent, and stats recompute
# Rollback: Set to False to disable integration (no impact on tournaments)
# Reference: Documents/UserProfile_CommandCenter_v1/03_Planning/UP_TOURNAMENT_INTEGRATION_CONTRACT.md
USER_PROFILE_INTEGRATION_ENABLED = os.getenv('USER_PROFILE_INTEGRATION_ENABLED', 'False').lower() == 'true'

# -----------------------------------------------------------------------------
# Settings Control Deck Feature Flag (Phase 1A)
# -----------------------------------------------------------------------------
# Enable new Settings Control Deck UI (settings_control_deck.html)
# Default: True (Phase 1A - READY controls only)
# When False: Falls back to legacy settings_v4.html
# Rollback: Set to False to revert to old settings page
# Reference: PHASE_1A_QA_REPORT.md, SETTINGS_PAGE_IMPLEMENTATION_PLAN.md
SETTINGS_CONTROL_DECK_ENABLED = os.getenv('SETTINGS_CONTROL_DECK_ENABLED', 'True').lower() == 'true'

# -----------------------------------------------------------------------------
# Django Unfold Admin Theme (Phase 1.5)
# -----------------------------------------------------------------------------
from django.urls import reverse_lazy
from django.templatetags.static import static as static_url

if _HAS_UNFOLD:
    UNFOLD = {
    "SITE_TITLE": "DeltaCrown Admin",
    "SITE_HEADER": "DeltaCrown",
    "SITE_SUBHEADER": "Tournament Platform Console",
    "SITE_URL": "/",
    "SITE_SYMBOL": "trophy",  # Material Symbols icon
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,

    # ---------------------------------------------------------------------------
    # Environment badge (top bar)
    # ---------------------------------------------------------------------------
    "ENVIRONMENT": "deltacrown.admin_callbacks.environment_callback",
    "ENVIRONMENT_TITLE_PREFIX": "deltacrown.admin_callbacks.environment_title",

    # ---------------------------------------------------------------------------
    # DeltaCrown color system — Cyan primary (dc-cyan #06b6d4)
    # oklch values from Tailwind CSS v4 cyan palette
    # ---------------------------------------------------------------------------
    "COLORS": {
        "base": {
            "50": "oklch(98.5% .002 247.839)",
            "100": "oklch(96.7% .003 264.542)",
            "200": "oklch(92.8% .006 264.531)",
            "300": "oklch(87.2% .01 258.338)",
            "400": "oklch(70.7% .022 261.325)",
            "500": "oklch(55.1% .027 264.364)",
            "600": "oklch(44.6% .03 256.802)",
            "700": "oklch(37.3% .034 259.733)",
            "800": "oklch(27.8% .033 256.848)",
            "900": "oklch(21% .034 264.665)",
            "950": "oklch(13% .028 261.692)",
        },
        "primary": {
            "50": "oklch(98.4% .019 200.873)",
            "100": "oklch(95.6% .045 203.388)",
            "200": "oklch(90.1% .076 205.101)",
            "300": "oklch(82.8% .111 205.395)",
            "400": "oklch(74.6% .136 202.009)",
            "500": "oklch(65.5% .163 195.768)",
            "600": "oklch(55.3% .146 195.326)",
            "700": "oklch(48.8% .118 196.839)",
            "800": "oklch(42% .096 197.859)",
            "900": "oklch(37.3% .076 200.386)",
            "950": "oklch(28.2% .058 204.071)",
        },
        "font": {
            "subtle-light": "var(--color-base-500)",
            "subtle-dark": "var(--color-base-400)",
            "default-light": "var(--color-base-600)",
            "default-dark": "var(--color-base-300)",
            "important-light": "var(--color-base-900)",
            "important-dark": "var(--color-base-100)",
        },
    },

    # ---------------------------------------------------------------------------
    # Sidebar navigation — grouped by domain
    # ---------------------------------------------------------------------------
    "SIDEBAR": {
        "show_search": False,  # Disabled: unfold 0.80 sidebar search overlay intermittently sticks visible
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Navigation",
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            # ── Esports Management ──
            {
                "title": "Esports Management",
                "separator": True,
                "items": [
                    {
                        "title": "Games",
                        "icon": "sports_esports",
                        "link": reverse_lazy("admin:games_game_changelist"),
                    },
                    {
                        "title": "Tournaments",
                        "icon": "emoji_events",
                        "link": reverse_lazy("admin:tournaments_tournament_changelist"),
                    },
                    {
                        "title": "Registrations",
                        "icon": "how_to_reg",
                        "link": reverse_lazy("admin:tournaments_registration_changelist"),
                    },
                    {
                        "title": "Matches",
                        "icon": "swords",
                        "link": reverse_lazy("admin:tournaments_match_changelist"),
                    },
                    {
                        "title": "Brackets",
                        "icon": "account_tree",
                        "link": reverse_lazy("admin:brackets_bracket_changelist"),
                    },
                    {
                        "title": "Results",
                        "icon": "leaderboard",
                        "link": reverse_lazy("admin:tournaments_tournamentresult_changelist"),
                    },
                    {
                        "title": "Disputes",
                        "icon": "gavel",
                        "link": reverse_lazy("admin:tournaments_disputerecord_changelist"),
                    },
                    {
                        "title": "Challenges",
                        "icon": "local_fire_department",
                        "link": reverse_lazy("admin:challenges_challenge_changelist"),
                    },
                    {
                        "title": "Group Stages",
                        "icon": "grid_view",
                        "link": reverse_lazy("admin:tournaments_groupstage_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "workspaces",
                        "link": reverse_lazy("admin:tournaments_group_changelist"),
                    },
                ],
            },
            # ── Tournament Configuration ──
            {
                "title": "Tournament Config",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Templates",
                        "icon": "content_copy",
                        "link": reverse_lazy("admin:tournaments_tournamenttemplate_changelist"),
                    },
                    {
                        "title": "Form Configs",
                        "icon": "dynamic_form",
                        "link": reverse_lazy("admin:tournaments_tournamentformconfiguration_changelist"),
                    },
                    {
                        "title": "Reg Form Templates",
                        "icon": "description",
                        "link": reverse_lazy("admin:tournaments_registrationformtemplate_changelist"),
                    },
                    {
                        "title": "Reg Forms",
                        "icon": "edit_note",
                        "link": reverse_lazy("admin:tournaments_tournamentregistrationform_changelist"),
                    },
                    {
                        "title": "Form Responses",
                        "icon": "checklist",
                        "link": reverse_lazy("admin:tournaments_formresponse_changelist"),
                    },
                    {
                        "title": "Custom Fields",
                        "icon": "tune",
                        "link": reverse_lazy("admin:tournaments_customfield_changelist"),
                    },
                    {
                        "title": "Payment Methods",
                        "icon": "payments",
                        "link": reverse_lazy("admin:tournaments_tournamentpaymentmethod_changelist"),
                    },
                    {
                        "title": "Payment Verifications",
                        "icon": "verified",
                        "link": reverse_lazy("admin:tournaments_paymentverification_changelist"),
                    },
                    {
                        "title": "Payments",
                        "icon": "credit_card",
                        "link": reverse_lazy("admin:tournaments_payment_changelist"),
                    },
                    {
                        "title": "Announcements",
                        "icon": "campaign",
                        "link": reverse_lazy("admin:tournaments_tournamentannouncement_changelist"),
                    },
                    {
                        "title": "Sponsors",
                        "icon": "handshake",
                        "link": reverse_lazy("admin:tournaments_tournamentsponsor_changelist"),
                    },
                    {
                        "title": "Versions",
                        "icon": "history",
                        "link": reverse_lazy("admin:tournaments_tournamentversion_changelist"),
                    },
                    {
                        "title": "Staff Assignments",
                        "icon": "assignment_ind",
                        "link": reverse_lazy("admin:tournaments_tournamentstaffassignment_changelist"),
                    },
                    {
                        "title": "Staff Roles",
                        "icon": "admin_panel_settings",
                        "link": reverse_lazy("admin:tournaments_tournamentstaffrole_changelist"),
                    },
                    {
                        "title": "Webhooks",
                        "icon": "webhook",
                        "link": reverse_lazy("admin:tournaments_formwebhook_changelist"),
                    },
                    {
                        "title": "Webhook Deliveries",
                        "icon": "send",
                        "link": reverse_lazy("admin:tournaments_webhookdelivery_changelist"),
                    },
                    {
                        "title": "Game Configs",
                        "icon": "settings_applications",
                        "link": reverse_lazy("admin:games_gametournamentconfig_changelist"),
                    },
                    {
                        "title": "Game Roster Configs",
                        "icon": "groups",
                        "link": reverse_lazy("admin:games_gamerosterconfig_changelist"),
                    },
                ],
            },
            # ── User & Org Management ──
            {
                "title": "Users & Organizations",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                    },
                    {
                        "title": "User Profiles",
                        "icon": "badge",
                        "link": reverse_lazy("admin:user_profile_userprofile_changelist"),
                    },
                    {
                        "title": "Game Profiles",
                        "icon": "stadia_controller",
                        "link": reverse_lazy("admin:user_profile_gameprofile_changelist"),
                    },
                    {
                        "title": "Organizations",
                        "icon": "corporate_fare",
                        "link": reverse_lazy("admin:organizations_organization_changelist"),
                    },
                    {
                        "title": "Org Memberships",
                        "icon": "group",
                        "link": reverse_lazy("admin:organizations_organizationmembership_changelist"),
                    },
                    {
                        "title": "Teams",
                        "icon": "groups_3",
                        "link": reverse_lazy("admin:organizations_team_changelist"),
                    },
                    {
                        "title": "Team Memberships",
                        "icon": "person_add",
                        "link": reverse_lazy("admin:organizations_teammembership_changelist"),
                    },
                    {
                        "title": "Team Rankings",
                        "icon": "military_tech",
                        "link": reverse_lazy("admin:organizations_teamranking_changelist"),
                    },
                    {
                        "title": "Org Rankings",
                        "icon": "workspace_premium",
                        "link": reverse_lazy("admin:organizations_organizationranking_changelist"),
                    },
                    {
                        "title": "Pending Signups",
                        "icon": "person_search",
                        "link": reverse_lazy("admin:accounts_pendingsignup_changelist"),
                    },
                ],
            },
            # ── Finance & Rewards ──
            {
                "title": "Finance & Rewards",
                "separator": True,
                "items": [
                    {
                        "title": "Wallets",
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:economy_deltacrownwallet_changelist"),
                    },
                    {
                        "title": "Transactions",
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:economy_deltacrowntransaction_changelist"),
                    },
                    {
                        "title": "Top-Up Requests",
                        "icon": "add_card",
                        "link": reverse_lazy("admin:economy_topuprequest_changelist"),
                    },
                    {
                        "title": "Withdrawals",
                        "icon": "money_off",
                        "link": reverse_lazy("admin:economy_withdrawalrequest_changelist"),
                    },
                    {
                        "title": "Prize Payouts",
                        "icon": "paid",
                        "link": reverse_lazy("admin:tournaments_prizetransaction_changelist"),
                    },
                    {
                        "title": "Prize Claims",
                        "icon": "redeem",
                        "link": reverse_lazy("admin:tournaments_prizeclaim_changelist"),
                    },
                    {
                        "title": "Certificates",
                        "icon": "card_membership",
                        "link": reverse_lazy("admin:tournaments_certificate_changelist"),
                    },
                    {
                        "title": "Coin Policy",
                        "icon": "policy",
                        "link": reverse_lazy("admin:economy_coinpolicy_changelist"),
                    },
                    {
                        "title": "Gift Requests",
                        "icon": "card_giftcard",
                        "link": reverse_lazy("admin:economy_giftrequest_changelist"),
                    },
                    {
                        "title": "Trade Requests",
                        "icon": "swap_horiz",
                        "link": reverse_lazy("admin:economy_traderequest_changelist"),
                    },
                    {
                        "title": "Inventory Items",
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:economy_inventoryitem_changelist"),
                    },
                    {
                        "title": "User Inventory",
                        "icon": "backpack",
                        "link": reverse_lazy("admin:economy_userinventoryitem_changelist"),
                    },
                ],
            },
            # ── Shop & E-Commerce ──
            {
                "title": "Shop & E-Commerce",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Shop Items",
                        "icon": "storefront",
                        "link": reverse_lazy("admin:shop_shopitem_changelist"),
                    },
                    {
                        "title": "Reservations",
                        "icon": "bookmark_added",
                        "link": reverse_lazy("admin:shop_reservationhold_changelist"),
                    },
                    {
                        "title": "Orders",
                        "icon": "local_shipping",
                        "link": reverse_lazy("admin:ecommerce_order_changelist"),
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": reverse_lazy("admin:ecommerce_category_changelist"),
                    },
                    {
                        "title": "Brands",
                        "icon": "branding_watermark",
                        "link": reverse_lazy("admin:ecommerce_brand_changelist"),
                    },
                    {
                        "title": "Coupons",
                        "icon": "local_offer",
                        "link": reverse_lazy("admin:ecommerce_coupon_changelist"),
                    },
                    {
                        "title": "Reviews",
                        "icon": "rate_review",
                        "link": reverse_lazy("admin:ecommerce_review_changelist"),
                    },
                    {
                        "title": "Wishlists",
                        "icon": "favorite",
                        "link": reverse_lazy("admin:ecommerce_wishlist_changelist"),
                    },
                    {
                        "title": "Loyalty Program",
                        "icon": "loyalty",
                        "link": reverse_lazy("admin:ecommerce_loyaltyprogram_changelist"),
                    },
                ],
            },
            # ── Competition & Rankings ──
            {
                "title": "Competition & Rankings",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Ranking Configs",
                        "icon": "tune",
                        "link": reverse_lazy("admin:competition_gamerankingconfig_changelist"),
                    },
                    {
                        "title": "Match Reports",
                        "icon": "summarize",
                        "link": reverse_lazy("admin:competition_matchreport_changelist"),
                    },
                    {
                        "title": "Match Verifications",
                        "icon": "fact_check",
                        "link": reverse_lazy("admin:competition_matchverification_changelist"),
                    },
                    {
                        "title": "Bounties",
                        "icon": "target",
                        "link": reverse_lazy("admin:competition_bounty_changelist"),
                    },
                    {
                        "title": "Bounty Claims",
                        "icon": "redeem",
                        "link": reverse_lazy("admin:competition_bountyclaim_changelist"),
                    },
                    {
                        "title": "Comp. Challenges",
                        "icon": "bolt",
                        "link": reverse_lazy("admin:competition_challenge_changelist"),
                    },
                    {
                        "title": "Ranking Adj. Logs",
                        "icon": "trending_up",
                        "link": reverse_lazy("admin:organizations_teamrankingadjustmentlog_changelist"),
                    },
                    {
                        "title": "Team Activity Logs",
                        "icon": "history",
                        "link": reverse_lazy("admin:organizations_teamactivitylog_changelist"),
                    },
                ],
            },
            # ── Platform Content & Support ──
            {
                "title": "Content & Support",
                "separator": True,
                "items": [
                    {
                        "title": "Home Page",
                        "icon": "home",
                        "link": reverse_lazy("admin:siteui_homepagecontent_changelist"),
                    },
                    {
                        "title": "Notifications",
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                    },
                    {
                        "title": "FAQs",
                        "icon": "help",
                        "link": reverse_lazy("admin:support_faq_changelist"),
                    },
                    {
                        "title": "Contact Messages",
                        "icon": "mail",
                        "link": reverse_lazy("admin:support_contactmessage_changelist"),
                    },
                    {
                        "title": "Testimonials",
                        "icon": "format_quote",
                        "link": reverse_lazy("admin:support_testimonial_changelist"),
                    },
                ],
            },
            # ── Moderation & Security ──
            {
                "title": "Moderation & Security",
                "separator": True,
                "items": [
                    {
                        "title": "Sanctions",
                        "icon": "shield",
                        "link": reverse_lazy("admin:moderation_moderationsanction_changelist"),
                    },
                    {
                        "title": "Abuse Reports",
                        "icon": "report",
                        "link": reverse_lazy("admin:moderation_abusereport_changelist"),
                    },
                    {
                        "title": "Audit Trail",
                        "icon": "security",
                        "link": reverse_lazy("admin:moderation_moderationaudit_changelist"),
                    },
                    {
                        "title": "User Audit Events",
                        "icon": "manage_search",
                        "link": reverse_lazy("admin:user_profile_userauditevent_changelist"),
                    },
                    {
                        "title": "Account Deletions",
                        "icon": "person_remove",
                        "link": reverse_lazy("admin:accounts_accountdeletionrequest_changelist"),
                    },
                ],
            },
            # ── User Profile Features ──
            {
                "title": "Profile Features",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Badges",
                        "icon": "military_tech",
                        "link": reverse_lazy("admin:user_profile_badge_changelist"),
                    },
                    {
                        "title": "User Badges",
                        "icon": "workspace_premium",
                        "link": reverse_lazy("admin:user_profile_userbadge_changelist"),
                    },
                    {
                        "title": "Skill Endorsements",
                        "icon": "thumb_up",
                        "link": reverse_lazy("admin:user_profile_skillendorsement_changelist"),
                    },
                    {
                        "title": "Highlight Clips",
                        "icon": "movie",
                        "link": reverse_lazy("admin:user_profile_highlightclip_changelist"),
                    },
                    {
                        "title": "Stream Configs",
                        "icon": "live_tv",
                        "link": reverse_lazy("admin:user_profile_streamconfig_changelist"),
                    },
                    {
                        "title": "Hardware Gear",
                        "icon": "mouse",
                        "link": reverse_lazy("admin:user_profile_hardwaregear_changelist"),
                    },
                    {
                        "title": "Privacy Settings",
                        "icon": "lock",
                        "link": reverse_lazy("admin:user_profile_privacysettings_changelist"),
                    },
                    {
                        "title": "Game Roles",
                        "icon": "assignment_ind",
                        "link": reverse_lazy("admin:games_gamerole_changelist"),
                    },
                    {
                        "title": "Game ID Configs",
                        "icon": "fingerprint",
                        "link": reverse_lazy("admin:games_gameplayeridentityconfig_changelist"),
                    },
                ],
            },
        ],
    },

    # ---------------------------------------------------------------------------
    # Dashboard callback (Phase 1.5.2)
    # ---------------------------------------------------------------------------
    "DASHBOARD_CALLBACK": "deltacrown.admin_callbacks.dashboard_callback",
}
