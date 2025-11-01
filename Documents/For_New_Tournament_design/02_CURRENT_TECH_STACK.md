# Current Technology Stack

**Document:** 02 - Current Tech Stack  
**Date:** November 2, 2025  
**Purpose:** Comprehensive list of all technologies, libraries, and infrastructure used in DeltaCrown

---

## 🐍 Core Technology

### Python
- **Version:** 3.11+
- **Required:** Minimum Python 3.10, recommended 3.11
- **Features Used:**
  - Type hints (annotations)
  - Async/await (limited usage)
  - Dataclasses
  - Pattern matching (minimal)
  - Modern standard library

---

## 🎸 Django Framework

### Django Core
- **Version:** 4.2.x LTS
- **Why Django 4.2:** Long-term support release (until April 2026)
- **Key Features Used:**
  - Class-based views and function-based views
  - Django ORM with advanced queries
  - Model relationships (OneToOne, ForeignKey, ManyToMany)
  - Signals (heavily used - part of the problem)
  - Middleware
  - Template engine with custom tags
  - Form handling and validation
  - Admin interface (heavily customized)
  - Authentication system (custom user model)
  - Permissions and authorization
  - Migrations system
  - Management commands

### Django Packages Used

#### **django.contrib modules:**
```python
INSTALLED_APPS = [
    "django.contrib.admin",           # Admin interface
    "django.contrib.auth",            # Authentication
    "django.contrib.contenttypes",    # Content types framework
    "django.contrib.sessions",        # Session management
    "django.contrib.messages",        # Flash messages
    "django.contrib.staticfiles",     # Static file handling
    "django.contrib.humanize",        # Human-readable filters
    "django.contrib.sites",           # Multi-site support
    "django.contrib.sitemaps",        # SEO sitemaps
]
```

---

## 🗄️ Database

### PostgreSQL
- **Version:** 12+ (compatible with 12, 13, 14, 15, 16)
- **Current Setup:**
  - **Database Name:** `deltacrown`
  - **User:** `dc_user`
  - **Host:** `localhost` (development)
  - **Port:** `5432` (default)
  - **Timezone:** Asia/Dhaka
- **Features Used:**
  - JSONB fields (for flexible data)
  - Array fields (for lists - Valorant map pool)
  - Full-text search capabilities (planned)
  - Transaction management
  - Database constraints (UNIQUE, CHECK)
  - Database indexes for performance

### Database Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("DB_NAME", "deltacrown"),
        'USER': os.getenv("DB_USER", "dc_user"),
        'PASSWORD': os.getenv("DB_PASSWORD", "Rashik0001"),
        'HOST': os.getenv("DB_HOST", "localhost"),
        'PORT': os.getenv("DB_PORT", "5432"),
    }
}
```

**Why PostgreSQL:**
- Robust relational database
- Advanced features (JSON, arrays, full-text search)
- Excellent Django support
- Production-grade performance
- ACID compliance

---

## 🔴 Redis

### Redis Server
- **Version:** 6.0+ recommended
- **Usage:**
  1. **Celery Broker** - Task queue management
  2. **Celery Result Backend** - Task result storage
  3. **Django Channels** - WebSocket message layer (planned)
  4. **Cache Backend** - Application caching (configured but minimal usage)

### Redis Configuration
```python
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'  # Development
        # Production should use: 'channels_redis.core.RedisChannelLayer'
    }
}
```

**Current Status:** Redis required for Celery, Channels using in-memory layer

---

## ⚙️ Async Task Processing

### Celery
- **Version:** 5.x
- **Broker:** Redis
- **Result Backend:** Redis
- **Configuration:**
  ```python
  CELERY_ACCEPT_CONTENT = ['json']
  CELERY_TASK_SERIALIZER = 'json'
  CELERY_RESULT_SERIALIZER = 'json'
  CELERY_TIMEZONE = 'UTC'
  CELERY_ENABLE_UTC = True
  CELERY_TASK_ALWAYS_EAGER = False  # True in tests
  ```

### Celery Tasks Used:
- Tournament notifications
- Email sending (async)
- Discord webhook delivery
- Background data processing
- Scheduled tasks (beat integration ready)

**Files:**
- `deltacrown/celery.py` - Celery app configuration
- `apps/tournaments/tasks.py` - Tournament-related tasks
- `apps/teams/tasks.py` - Team-related tasks
- `apps/notifications/tasks.py` - Notification tasks

**Running Celery:**
```bash
celery -A deltacrown worker -l info
celery -A deltacrown beat -l info  # For scheduled tasks
```

---

## 🌐 Real-Time / WebSocket

### Django Channels
- **Version:** 4.x
- **Purpose:** WebSocket support for real-time features
- **Current Implementation:**
  - Tournament live updates
  - Match result notifications
  - Bracket updates
  - Channel layer: In-memory (development)

### ASGI Configuration
```python
ASGI_APPLICATION = 'deltacrown.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}
```

**Files:**
- `deltacrown/asgi.py` - ASGI configuration
- `apps/tournaments/consumers.py` - WebSocket consumers
- `apps/tournaments/routing.py` - WebSocket routing

**Current Status:** Basic implementation, not production-ready

---

## 📡 REST API

### Django REST Framework (DRF)
- **Version:** 3.14+
- **Purpose:** RESTful API for tournaments and other entities
- **Features Used:**
  - ViewSets and routers
  - Serializers with validation
  - Authentication (Session, Basic)
  - Permissions
  - Pagination
  - Throttling (rate limiting)

### DRF Configuration
```python
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
```

### API Endpoints:
- `/api/tournaments/` - Tournament CRUD
- `/api/tournaments/<id>/schedule/` - Schedule management
- `/api/tournaments/<id>/capacity/` - Capacity management
- `/api/tournaments/<id>/finance/` - Finance management
- Many more endpoints in tournaments app

**Files:**
- `apps/tournaments/serializers.py` - Serializers (500+ lines)
- `apps/tournaments/viewsets.py` - ViewSets (600+ lines)
- `apps/tournaments/api_urls.py` - API routing
- `apps/tournaments/api_views.py` - Custom API views

---

## ✏️ Rich Text Editor

### CKEditor 5
- **Package:** `django-ckeditor-5`
- **Purpose:** Rich text editing for tournament descriptions, rules, etc.
- **Features:**
  - Bold, italic, underline
  - Links and lists
  - Block quotes
  - Tables
  - Image uploads (configured)

### CKEditor Configuration
```python
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "bold", "italic", "underline", "|",
            "link", "bulletedList", "numberedList", "|",
            "blockQuote", "insertTable", "undo", "redo",
        ],
    }
}
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"
```

**Used In:**
- Tournament descriptions
- Tournament rules
- Game-specific rules
- Support articles
- Static pages

---

## 🔐 Authentication Extensions

### Django Allauth (Optional)
- **Package:** `django-allauth`
- **Status:** Conditionally enabled via `ENABLE_ALLAUTH=1`
- **Purpose:** Social authentication (Google OAuth)
- **Features:**
  - Google OAuth login
  - Email verification
  - Account management

### Custom Authentication
- **Backend:** `EmailOrUsernameBackend`
- **Location:** `apps/accounts/backends.py`
- **Features:**
  - Login with email OR username
  - Custom validation
  - Integrated with Django auth

---

## 📧 Email System

### Email Backend
- **Development:** Console backend (prints to terminal)
- **Production:** SMTP backend (Gmail)

### Gmail SMTP Configuration
```python
if os.getenv("DeltaCrownEmailAppPassword"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "deltacrownhq@gmail.com")
    EMAIL_HOST_PASSWORD = os.getenv("DeltaCrownEmailAppPassword")
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

**Used For:**
- Tournament notifications
- Registration confirmations
- Password resets
- System announcements
- Dispute notifications

---

## 🔔 External Integrations

### Discord Webhooks
- **Purpose:** Send notifications to Discord channels
- **Configuration:**
  ```python
  DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
  DISCORD_NOTIFICATIONS_ENABLED = bool(DISCORD_WEBHOOK_URL)
  ```
- **Notification Types:**
  - Tournament registrations
  - Match results
  - Dispute updates
  - System alerts

### Notification Channels
```python
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
```

---

## 🧪 Testing Framework

### Pytest
- **Package:** `pytest`, `pytest-django`
- **Configuration:** `pytest.ini`
- **Test Count:** 94+ test files
- **Coverage Areas:**
  - Tournament core functionality
  - Team management
  - Payment processing
  - Game integrations
  - API endpoints
  - Admin interfaces

### Test Configuration
```ini
[pytest]
DJANGO_SETTINGS_MODULE = deltacrown.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Testing Command
```bash
pytest                    # Run all tests
pytest -v                # Verbose output
pytest tests/test_part1_tournament_core.py  # Specific file
pytest -k "payment"      # Keyword matching
```

**Test Categories:**
- `test_part1_*` - Core tournament tests
- `test_part2_*` - Game config tests
- `test_part3_*` - Payment tests
- `test_part4_*` - Team tests
- `test_part5_*` - Economy tests
- And 80+ more test files

---

## 📦 Other Django Packages

### Sites Framework
```python
SITE_ID = 1  # Required for django.contrib.sites
```
- Used for multi-site support
- Required by django-allauth

### Humanize
- **Purpose:** Human-readable date/number formatting
- **Usage:** `{{ date|naturaltime }}`, `{{ number|intcomma }}`

### Sitemaps
- **Purpose:** SEO optimization
- **File:** `deltacrown/sitemaps.py`
- **Generates:** XML sitemap for search engines

---

## 🎨 Frontend Technologies

### Template Engine
- **Engine:** Django Templates
- **Custom Template Tags:**
  - `seo_tags` - Meta tags and Open Graph
  - `assets` - Asset management
  - `dashboard_widgets` - Dashboard components
  - `string_utils` - String manipulation

### CSS Framework
- **Primary:** Custom CSS
- **Files:** `static/css/`
- **Themes:** Modern and Cyberpunk designs

### JavaScript
- **Location:** `static/js/`
- **Libraries:** Minimal external dependencies
- **Usage:**
  - Form validation
  - Dynamic UI updates
  - AJAX requests
  - WebSocket connections

---

## 🔧 Development Tools

### Environment Variables
Required environment variables:
```bash
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=your-secret-key
DB_NAME=deltacrown
DB_USER=dc_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
CELERY_BROKER_URL=redis://localhost:6379/0
DISCORD_WEBHOOK_URL=your-webhook-url
DeltaCrownEmailAppPassword=your-app-password
EMAIL_HOST_USER=deltacrownhq@gmail.com
```

### ngrok Support
- **Purpose:** Test with external services (webhooks, OAuth)
- **Configuration:** Wildcard ngrok domains allowed in `ALLOWED_HOSTS`
```python
ALLOWED_HOSTS = [".ngrok-free.app"]
CSRF_TRUSTED_ORIGINS = ["https://*.ngrok-free.app"]
```

---

## 📁 Static & Media Files

### Static Files
```python
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
```
- **Location:** `static/` directory
- **Collections:** `python manage.py collectstatic`

### Media Files
```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```
- **Purpose:** User uploads (avatars, banners, evidence files)
- **Future:** S3-compatible storage planned

---

## 🚀 Production Considerations

### Current Status
- **Environment:** Development/Staging
- **Production-Ready:** Partial
- **Missing for Production:**
  - Redis-backed Channels layer
  - S3 for media storage
  - Proper caching strategy
  - Load balancing
  - Database replication
  - Monitoring and logging
  - Error tracking (Sentry integration planned)

### Production Requirements
1. **ASGI Server:** Daphne or Uvicorn
2. **WSGI Server:** Gunicorn (for non-WebSocket views)
3. **Reverse Proxy:** Nginx
4. **Redis:** Production instance
5. **PostgreSQL:** Production instance
6. **Celery Workers:** Background task processing
7. **Static Files:** CDN (CloudFlare, AWS CloudFront)
8. **Media Files:** S3-compatible storage

---

## 📊 Performance Considerations

### Database Optimization
- **Indexes:** Created on frequently queried fields
- **select_related:** Used for foreign key queries
- **prefetch_related:** Used for reverse foreign key queries
- **Query Optimization:** Ongoing effort

### Caching
```python
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}
```
- **Current:** In-memory cache (development)
- **Planned:** Redis-backed cache

### Testing Performance
```python
if os.getenv("FAST_TESTS", "1") == "1":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
```
- **Purpose:** Speed up test execution
- **Usage:** Weaker password hashing in tests only

---

## 🔍 Code Quality Tools

### Current Setup
- **Linting:** Not configured (recommended: flake8, black)
- **Type Checking:** Not configured (recommended: mypy)
- **Code Formatting:** Not enforced (recommended: black, isort)
- **Pre-commit Hooks:** Not configured

### Recommended Additions
```bash
# Future improvements
pip install black flake8 mypy isort pre-commit
```

---

## 📝 Summary

### Technology Choices - Why?

1. **Django 4.2 LTS:** Stable, long-term support, mature ecosystem
2. **PostgreSQL:** Advanced features, production-grade
3. **Redis:** Fast, versatile (cache, broker, channel layer)
4. **Celery:** Industry standard for async tasks
5. **DRF:** Best Django API framework
6. **Channels:** Official Django WebSocket support
7. **CKEditor 5:** Modern, actively maintained

### Current Limitations

1. **No Type Checking:** Python type hints used but not enforced
2. **Limited Testing:** 94+ tests but coverage gaps exist
3. **No Code Formatting:** Manual formatting, inconsistent style
4. **Development-Only Cache:** In-memory cache not production-ready
5. **Channel Layer:** In-memory not suitable for production
6. **Manual Deployments:** No CI/CD pipeline

### Technology Debt

1. **Outdated Patterns:** Some code uses older Django patterns
2. **Mixed Paradigms:** CBVs and FBVs mixed inconsistently
3. **Signal Overuse:** Business logic hidden in signals
4. **Tight Coupling:** Apps depend on each other tightly
5. **Configuration Spread:** Settings across multiple files

---

**Next Document:** `03_TOURNAMENT_MODELS_REFERENCE.md` - Detailed tournament models documentation
