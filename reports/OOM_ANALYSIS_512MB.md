# DeltaCrown — OOM Analysis & 512 MB RAM Optimization Plan

> **Date:** March 18, 2026  
> **Target:** Render Free Tier — 512 MB RAM hard limit  
> **Safety Budget:** ≤ 450 MB peak usage (62 MB buffer)  
> **Stack:** Django 5.2, Daphne (ASGI), Celery (solo pool), Redis (Upstash), Neon PostgreSQL

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Dependency Audit](#2-dependency-audit)
3. [Memory Leak Detection](#3-memory-leak-detection)
4. [Process Optimization](#4-process-optimization)
5. [Resource-Intensive Apps](#5-resource-intensive-apps)
6. [Step-by-Step Action Plan](#6-step-by-step-action-plan)

---

## 1. Executive Summary

The DeltaCrown instance runs **four processes in a single 512 MB container**:

| Process | Baseline RAM | Peak RAM | Status |
|---------|-------------|----------|--------|
| **Daphne** (ASGI server) | ~80–120 MB | ~180 MB | Always on |
| **Celery Worker** (solo pool) | ~60–100 MB | ~200 MB | Always on |
| **Celery Beat** (scheduler) | ~30–50 MB | ~60 MB | Opt-in (currently off) |
| **Discord Bot** (discord.py) | ~50–80 MB | ~150+ MB | Conditional |
| **Python import overhead** | ~40–60 MB | — | Shared baseline |

**Worst-case total: ~550–590 MB** — exceeds the 512 MB limit, triggering OOM kills.

**Root causes (ordered by impact):**
1. **Too many processes** sharing 512 MB — Daphne + Celery alone consume ~200–300 MB
2. **Heavy dev/doc dependencies** installed in production (~30+ packages never used at runtime)
3. **Discord Bot** adds 50–150 MB when active; no memory cap
4. **Certificate generation** (ReportLab + Pillow) creates 2–5 MB per PDF/PNG in-memory spikes
5. **DATA_UPLOAD_MAX_MEMORY_SIZE = 10 MB** — allows large in-memory request buffers

---

## 2. Dependency Audit

### 2.1 Packages NOT Required in Production

The current `requirements.txt` has **179 packages**. The following **~40 packages** are dev/test/doc tools that should be removed from the production install:

#### Testing Frameworks & Utilities
| Package | Size Impact | Why Remove |
|---------|------------|------------|
| `pytest` | ~5 MB | Test runner — not used at runtime |
| `pytest-asyncio` | ~1 MB | Async test support |
| `pytest-benchmark` | ~2 MB | Performance benchmarking |
| `pytest-cov` | ~1 MB | Coverage measurement |
| `pytest-django` | ~1 MB | Django test integration |
| `pytest-playwright` | ~1 MB | Browser testing |
| `pytest-base-url` | <1 MB | Test URL config |
| `playwright` | ~50 MB | Browser automation (massive) |
| `coverage` | ~3 MB | Code coverage |
| `factory_boy` | ~2 MB | Test fixture factories |
| `Faker` | ~20 MB | Fake data generation (huge locale data) |
| `hypothesis` | ~5 MB | Property-based testing |
| `moto` | ~15 MB | AWS service mocking |
| `responses` | ~1 MB | HTTP response mocking |
| `py-cpuinfo` | ~1 MB | CPU info (pytest-benchmark dep) |
| `sortedcontainers` | <1 MB | hypothesis dependency |

#### Code Quality & Linting
| Package | Size Impact | Why Remove |
|---------|------------|------------|
| `black` | ~8 MB | Code formatter |
| `flake8` | ~2 MB | Linter |
| `isort` | ~1 MB | Import sorter |
| `mypy` | ~15 MB | Static type checker (very heavy) |
| `mypy_extensions` | <1 MB | mypy dependency |
| `django-stubs` | ~5 MB | Django type stubs |
| `django-stubs-ext` | ~1 MB | django-stubs dependency |
| `types-PyYAML` | <1 MB | Type stubs |
| `pycodestyle` | <1 MB | flake8 dependency |
| `pyflakes` | <1 MB | flake8 dependency |
| `mccabe` | <1 MB | flake8 dependency |
| `pathspec` | <1 MB | black dependency |
| `typing-inspection` | <1 MB | mypy dependency |

#### Documentation
| Package | Size Impact | Why Remove |
|---------|------------|------------|
| `Sphinx` | ~10 MB | Documentation generator |
| `sphinx-rtd-theme` | ~5 MB | Sphinx theme |
| `sphinxcontrib-applehelp` | <1 MB | Sphinx extension |
| `sphinxcontrib-devhelp` | <1 MB | Sphinx extension |
| `sphinxcontrib-htmlhelp` | <1 MB | Sphinx extension |
| `sphinxcontrib-jquery` | <1 MB | Sphinx extension |
| `sphinxcontrib-jsmath` | <1 MB | Sphinx extension |
| `sphinxcontrib-qthelp` | <1 MB | Sphinx extension |
| `sphinxcontrib-serializinghtml` | <1 MB | Sphinx extension |
| `alabaster` | <1 MB | Default Sphinx theme |
| `babel` | ~30 MB | Sphinx i18n dependency |
| `snowballstemmer` | <1 MB | Sphinx dependency |
| `imagesize` | <1 MB | Sphinx dependency |
| `docutils` | ~2 MB | Sphinx dependency |

#### Build & Publishing Tools
| Package | Size Impact | Why Remove |
|---------|------------|------------|
| `twine` | ~2 MB | PyPI upload tool |
| `build` | ~1 MB | Python build frontend |
| `check-manifest` | <1 MB | Manifest checker |
| `pkginfo` | <1 MB | twine dependency |
| `readme_renderer` | <1 MB | twine dependency |
| `keyring` | ~1 MB | twine dependency |
| `rfc3986` | <1 MB | twine dependency |
| `requests-toolbelt` | <1 MB | twine dependency |
| `jaraco.classes` | <1 MB | keyring dep |
| `jaraco.context` | <1 MB | keyring dep |
| `jaraco.functools` | <1 MB | keyring dep |
| `pyproject_hooks` | <1 MB | build dependency |
| `pytokens` | <1 MB | check-manifest dep |
| `id` | <1 MB | twine dep |

#### Possibly Unnecessary in Production
| Package | Size Impact | Why Remove |
|---------|------------|------------|
| `Werkzeug` | ~3 MB | Flask debugger — Django doesn't use this |
| `gunicorn` | ~2 MB | WSGI server — project uses Daphne (ASGI) |
| `astor` | <1 MB | AST manipulation — no runtime usage found |
| `roman-numerals-py` | <1 MB | No runtime usage found |
| `py-partiql-parser` | <1 MB | moto dependency |
| `xmltodict` | <1 MB | moto dependency |

### 2.2 Clean Production Requirements

Below is the **minimal production requirements** list. Split into a `requirements-prod.txt`:

```txt
# ── Core Framework ──
Django==5.2.8
asgiref==3.10.0
daphne==4.2.1
channels==4.3.1
channels_redis==4.3.0

# ── Database ──
psycopg2-binary==2.9.11
dj-database-url==3.0.1

# ── Task Queue ──
celery==5.5.3
kombu==5.5.4
amqp==5.3.1
billiard==4.2.2
vine==5.1.0
redis==7.0.1
click==8.3.0
click-didyoumean==0.3.1
click-plugins==1.1.1.2
click-repl==0.3.0

# ── REST API ──
djangorestframework==3.16.1
djangorestframework_simplejwt==5.5.1
drf-nested-routers==0.95.0
drf-spectacular==0.27.2
inflection==0.5.1
uritemplate==4.2.0
PyJWT==2.10.1
pydantic==2.12.4
pydantic_core==2.41.5

# ── Auth & Security ──
django-allauth==65.13.0
cryptography==46.0.3
pyOpenSSL==25.3.0
PyNaCl==1.5.0
certifi==2025.10.5

# ── Storage & Media ──
django-storages==1.14.6
cloudinary==1.40.0
django-cloudinary-storage==0.3.0
boto3==1.40.71
botocore==1.40.71
s3transfer==0.14.0
jmespath==1.0.1
whitenoise==6.6.0
pillow==12.0.0
python-magic==0.4.27

# ── Utilities ──
django-environ==0.12.0
python-decouple==3.8
python-dotenv==1.2.1
python-slugify==8.0.4
text-unidecode==1.3
django-countries==7.6.1
django-cors-headers==4.9.0
django-filter==25.2
django-ckeditor-5==0.2.18
bleach==6.3.0
nh3==0.3.2
beautifulsoup4==4.14.3
soupsieve==2.8.1
python-dateutil==2.9.0.post0
pytz==2025.2
tzdata==2025.2
PyYAML==6.0.3
requests==2.32.5
urllib3==2.5.0
idna==3.11
charset-normalizer==3.4.4
packaging==25.0
six==1.17.0

# ── PDF & Image Generation ──
reportlab==4.4.4
cairocffi==1.7.1
CairoSVG==2.8.2
svglib==1.6.0
lxml==6.0.2
PyPDF2==3.0.1
pycairo==1.28.0
qrcode==8.2
cssselect2==0.8.0
tinycss2==1.4.0
defusedxml==0.7.1
webencodings==0.5.1
freetype-py==2.5.1
rlPyCairo==0.4.0

# ── Monitoring ──
django-prometheus==2.4.1
prometheus_client==0.23.1
sentry-sdk==2.43.0
python-json-logger==4.0.0

# ── Admin UI ──
django-unfold==0.80.0

# ── Discord (conditional — can be omitted if bot disabled) ──
discord.py==2.6.4
aiohttp==3.13.3
aiohappyeyeballs==2.6.1
aiosignal==1.4.0
frozenlist==1.8.0
multidict==6.7.1
yarl==1.22.0
attrs==25.4.0

# ── Email ──
resend==2.23.0

# ── Misc Runtime Dependencies ──
annotated-types==0.7.0
cffi==2.0.0
pycparser==2.23
colorama==0.4.6
Jinja2==3.1.6
MarkupSafe==3.0.3
marshmallow==4.1.0
msgpack==1.1.2
more-itertools==10.8.0
jsonschema==4.25.1
jsonschema-specifications==2025.9.1
referencing==0.37.0
rpds-py==0.30.0
platformdirs==4.5.0
propcache==0.4.1
prompt_toolkit==3.0.52
wcwidth==0.2.14
Pygments==2.19.2
rich==14.2.0
mdurl==0.1.2
markdown-it-py==4.0.0
setuptools==80.9.0
sqlparse==0.5.3
typing_extensions==4.15.0
greenlet==3.3.0

# ── Twisted (Daphne dependency) ──
Twisted==25.5.0
autobahn==25.10.2
Automat==25.4.16
constantly==23.10.4
hyperlink==21.0.0
incremental==24.7.2
txaio==25.9.2
service-identity==24.2.0
pyasn1==0.6.1
pyasn1_modules==0.4.2
zope.interface==8.0.1

# ── Windows only (conditional) ──
# pywin32-ctypes==0.2.3
```

**Estimated disk savings:** ~180 MB+ (Faker, Playwright, mypy, Sphinx, moto, babel are the largest).  
**Estimated RAM savings:** ~10–20 MB from not loading heavy import chains.

---

## 3. Memory Leak Detection

### 3.1 Large Global Variables

| Location | Variable | Risk | Detail |
|----------|----------|------|--------|
| `apps/organizations/services/org_detail_service.py` | `_game_cache = {}` | **Medium** | Unbounded module-level dict. No TTL, no max size, no eviction. Grows with every unique game queried. On long-running Daphne/Celery processes, never cleared. |
| `apps/organizations/utils/schema_compat.py` | `_SCHEMA_CACHE = {}` | Low | Small — only a few table introspection results. |
| `deltacrown/celery.py` — EventBus | `_event_history: List` | Low | Capped at 1000 entries (~500 KB max). |
| `deltacrown/settings.py` | `SPECTACULAR_SETTINGS` | Low | ~5 KB static config dict. One-time allocation. |

**Fix for `_game_cache`:**
```python
# Replace _game_cache = {} with:
from functools import lru_cache

@lru_cache(maxsize=64)
def _get_game(game_id):
    ...
```

### 3.2 Unclosed / Long-Lived Handlers

| Location | Issue | Risk |
|----------|-------|------|
| `apps/tournaments/services/certificate_service.py` | Creates `BytesIO()` buffers for PDF generation. Buffers are returned but rely on caller to close/GC. In batch operations, multiple 2–5 MB buffers can coexist. | **Medium** |
| `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 MB` (settings.py:574) | Allows Django to buffer 10 MB per POST request in memory. Under load, 3–4 concurrent uploads = 30–40 MB consumed. | **Medium** |
| Discord Bot (`run_discord_bot`) | Long-lived asyncio process. discord.py caches guild members, channels, roles in memory. No periodic cleanup observed. | **High** |

### 3.3 Middleware Stack Analysis

The middleware stack has **15 middleware classes** (17 in DEBUG):

| Middleware | Per-Request Cost | Note |
|-----------|-----------------|------|
| `PrometheusBeforeMiddleware` | ~0.5 KB | Counter/histogram objects — shared |
| `MetricsMiddleware` | ~0.2 KB | Timestamp only |
| `SecurityMiddleware` | Negligible | Header injection |
| `CSPMiddleware` | Negligible | Cached policy string |
| `WhiteNoiseMiddleware` | ~1–2 MB static file cache | **One-time init scans all static files** |
| `MediaProxyMiddleware` | Negligible | URL rewrite |
| `CorsMiddleware` | Negligible | Header injection |
| `BotProbeShieldMiddleware` | ~50 KB | Compiled regex patterns — shared |
| `SessionMiddleware` | ~1 KB/req | Session data via Redis/DB |
| `RequestLoggingMiddleware` | ~0.5 KB/req | Builds log dict, discards after emit |
| `UserPlatformPrefsMiddleware` | ~0.2 KB/req | DB lookup, cached |
| `BlockScheduledDeletionMiddleware` | Negligible | Flag check |
| `TOCAuditMiddleware` | ~0.3 KB/req | Selective — only TOC write endpoints |
| `PrometheusAfterMiddleware` | ~0.5 KB | Counter/histogram objects — shared |

**WhiteNoise** is the most memory-relevant middleware. It scans and caches all static file metadata at startup. With a large `staticfiles/` directory, this can consume **5–15 MB**. This is acceptable.

### 3.4 Context Processors

**7 custom context processors** run on every template-rendered request:

| Processor | Cost | Concern |
|-----------|------|---------|
| `notification_counts` | 1 DB query | Runs on every page load |
| `unread_notifications` | 1 DB query | Runs on every page load |
| `ui_settings` | Light | Likely cached |
| `game_assets_context` | 1+ DB query | Runs on every page load — loads game list |
| `homepage_context` | 1+ DB query | Runs on every page load even for non-homepage URLs |
| `site_settings` | 1 DB query | Runs on every page load |
| `nav_context` | 1+ DB query | Runs on every page load |
| `vnext_feature_flags` | Light | Flag checks |
| `user_platform_prefs` | 1 DB query | Runs on every page load |

**Issue:** `homepage_context` likely runs on every request, not just the homepage. Each processor adds cumulative query overhead. On a 512 MB system, the DB connection overhead per request is the concern, not the context processor memory itself.

---

## 4. Process Optimization

### 4.1 Current Startup Architecture (start.sh)

```
┌─────────────────────────────────────────────┐
│              512 MB Container                │
│                                              │
│   ┌──────────────┐  ┌──────────────────┐    │
│   │ Celery Worker │  │   Celery Beat    │    │
│   │ (solo pool)   │  │  (opt-in, off)   │    │
│   │ ~80–120 MB    │  │  ~30–50 MB       │    │
│   └──────────────┘  └──────────────────┘    │
│                                              │
│   ┌──────────────┐  ┌──────────────────┐    │
│   │ Discord Bot   │  │     Daphne       │    │
│   │ (conditional) │  │   (foreground)   │    │
│   │ ~50–150 MB    │  │  ~80–120 MB      │    │
│   └──────────────┘  └──────────────────┘    │
│                                              │
│   Total baseline: ~270–440 MB                │
│   Peak with load: ~450–600 MB  ← OOM !!     │
└─────────────────────────────────────────────┘
```

### 4.2 Daphne Optimization

Current config (already reasonable):
- `--http-timeout 60` ✅
- `--websocket_connect_timeout 5` ✅
- `--ping-interval 20` / `--ping-timeout 30` ✅
- `--application-close-timeout 5` ✅

**Recommendations:**
- Add `--server-name deltacrown` for log clarity
- **Reduce WebSocket connection limits** in settings:
  - `WS_RATE_CONN_PER_USER = 2` (from 3)
  - `WS_RATE_CONN_PER_IP = 5` (from 10)
  - `WS_RATE_ROOM_MAX_MEMBERS = 500` (from 2000)
- **Reduce Channel Layer capacity**:
  - `capacity: 500` (from 1500) — each buffered message is ~1–5 KB

### 4.3 Celery Optimization

Current config (already good):
- `--pool=solo` ✅ (no fork overhead)
- `--concurrency=1` ✅
- `--prefetch-multiplier=1` ✅
- `--without-gossip --without-mingle --without-heartbeat` ✅

**Recommendations:**
- Add `--max-memory-per-child=150000` (150 MB) — auto-restart worker if it exceeds this
- Add `CELERY_WORKER_MAX_TASKS_PER_CHILD=200` in settings — recycle worker after 200 tasks to prevent memory creep
- Set `CELERY_TASK_SOFT_TIME_LIMIT=120` and `CELERY_TASK_TIME_LIMIT=180` — kill stuck tasks before they hog RAM

### 4.4 Discord Bot — Alternative Architecture

The Discord bot is the **single largest discretionary memory consumer** (50–150 MB). On 512 MB, this is unsustainable.

**Option A: Disable the Bot Entirely (Recommended for Free Tier)**
```bash
ENABLE_DISCORD_BOT=0
```
Use Discord webhooks for one-way platform → Discord notifications (tournament results, match announcements). Webhooks are stateless HTTP POST calls — zero resident memory.

**Option B: Move to a Separate Free Tier Service**
Deploy the bot as its own Render Free Tier web service or use a free-tier bot hosting platform (Railway, Fly.io). This completely isolates its memory from the Django process.

**Option C: Scheduled Sync Instead of Live Bot**
Replace the live bot with a Celery task that periodically syncs messages (every 5–10 minutes) via Discord HTTP API. This replaces:
- ~100 MB persistent bot → ~5 MB per sync task (runs 30 seconds, then exits)

### 4.5 Celery Beat — Keep Disabled

`ENABLE_CELERY_BEAT=0` is already the default. The heavy schedule (20+ tasks, some every 2 minutes) would add **30–50 MB** and cause task accumulation. For free tier:
- Keep on-demand task dispatch only
- Run periodic operations manually via management commands or Render Cron Jobs (free tier gets 1 cron job)

---

## 5. Resource-Intensive Apps

### 5.1 By Memory Footprint

| App/Module | Import Cost | Runtime Peak | Key Libraries |
|------------|------------|--------------|---------------|
| `tournaments/services/certificate_service.py` | ~20 MB (reportlab + PIL) | ~5 MB per PDF/PNG | ReportLab, Pillow, qrcode, Cairo |
| `user_profile/services/certificate_service.py` | ~15 MB (PIL) | ~3 MB per PNG | Pillow, ImageDraw, ImageFont |
| Discord Bot (`run_discord_bot`) | ~30 MB (discord.py + aiohttp) | ~150 MB (24h) | discord.py, aiohttp, asyncio |
| `drf_spectacular` schema gen | ~10 MB | ~20 MB (schema render) | drf-spectacular, inflection |
| `django-unfold` admin theme | ~5 MB | ~10 MB (admin pages) | unfold |
| `django-ckeditor-5` | ~3 MB | ~5 MB | ckeditor-5 |
| `sentry_sdk` (with integrations) | ~5 MB | ~8 MB | sentry-sdk, Django/Celery/Redis integrations |
| `leaderboards` tasks (if beat on) | ~2 MB | ~10+ MB (snapshot batch) | ORM, aggregation queries |
| `organizations` ranking recalc | ~2 MB | ~10+ MB (batch) | ORM queryset iteration |

### 5.2 PDF/Image Generation Deep Dive

Both certificate services share the same pattern:
1. Open `BytesIO()` buffer
2. Create ReportLab canvas or PIL Image (1920×1080)
3. Render content (text, QR codes, backgrounds)
4. Save to buffer → return `HttpResponse`

**Peak memory per certificate:**
- PDF: ~500 KB–2 MB
- PNG: ~2–5 MB (1920×1080 RGBA = 8.3 MB uncompressed, ~2–3 MB after encoding)

**Batch concern:** Tournament wrap-up can generate certificates for all participants. If 20 participants = 20 × 3 MB = **60 MB spike**.

**Fix:** Process certificates sequentially via Celery tasks with `rate_limit='1/m'`, not in a single view.

---

## 6. Step-by-Step Action Plan

### Phase 1: Immediate — Stop the OOM Crashes (saves ~100–200 MB)

#### Step 1.1: Disable Discord Bot
```bash
# In Render environment variables:
ENABLE_DISCORD_BOT=0
```
**Savings: ~50–150 MB**

#### Step 1.2: Split requirements into prod/dev
Create `requirements-prod.txt` with only production dependencies (see Section 2.2). Update `render_build.sh`:
```bash
# Change from:
pip install --no-cache-dir -r requirements.txt
# To:
pip install --no-cache-dir -r requirements-prod.txt
```
**Savings: ~10–20 MB RAM, ~180 MB disk**

#### Step 1.3: Reduce DATA_UPLOAD_MAX_MEMORY_SIZE
```python
# settings.py — change from 10 MB to 2.5 MB (Django default)
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB
```
**Savings: Up to 30 MB under concurrent uploads**

#### Step 1.4: Add Celery Worker Memory Guard
```bash
# In start.sh, modify the celery worker command:
celery -A deltacrown worker \
    --loglevel=warning \
    --pool="${CELERY_POOL}" \
    --concurrency="${CELERY_CONCURRENCY}" \
    --optimization=fair \
    --prefetch-multiplier="${CELERY_PREFETCH_MULTIPLIER}" \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --max-memory-per-child=150000 \
    &
```

Add to `settings.py`:
```python
# Celery memory safety net
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.getenv('CELERY_MAX_TASKS_PER_CHILD', '200'))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', '120'))
CELERY_TASK_TIME_LIMIT = int(os.getenv('CELERY_TASK_TIME_LIMIT', '180'))
```

---

### Phase 2: Quick Wins — Tighten Resource Bounds (saves ~20–50 MB)

#### Step 2.1: Reduce Channel Layer Capacity
```python
# settings.py — CHANNEL_LAYERS config
'CONFIG': {
    'hosts': [_REDIS_CHANNEL_URL],
    'prefix': 'dc-ws',
    'capacity': 500,      # was 1500
    'expiry': 10,
},
```

#### Step 2.2: Reduce WebSocket Limits
```bash
# Render environment variables:
WS_RATE_CONN_PER_USER=2
WS_RATE_CONN_PER_IP=5
WS_RATE_ROOM_MAX_MEMBERS=500
```

#### Step 2.3: Disable drf-spectacular Schema Generation in Production
The schema endpoint loads all serializers and viewsets into memory. Disable the serve views:
```python
# settings.py
SPECTACULAR_SETTINGS = {
    ...
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
    ...
}
```
Or gate the URL pattern behind `DEBUG`:
```python
# urls.py
if settings.DEBUG:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(), name='swagger-ui'),
    ]
```

#### Step 2.4: Guard homepage_context Processor
Ensure `homepage_context` short-circuits for non-homepage URLs:
```python
def homepage_context(request):
    if request.path != '/':
        return {}
    # ... expensive queries only for homepage
```

#### Step 2.5: Cap _game_cache with LRU
```python
# apps/organizations/services/org_detail_service.py
from functools import lru_cache

@lru_cache(maxsize=64)
def get_game_by_id(game_id):
    ...
```

---

### Phase 3: Architecture — Discord Without the Bot

#### Step 3.1: Replace Bot with Webhooks
For platform → Discord notifications (tournament results, team updates), use Discord webhooks:
```python
# apps/notifications/services/discord_webhook.py
import requests

def send_discord_notification(webhook_url, embed):
    """Stateless webhook call — zero resident memory."""
    requests.post(webhook_url, json={"embeds": [embed]}, timeout=5)
```

#### Step 3.2: Use Render Cron Job for Periodic Sync
Instead of Celery Beat, use Render's free cron job (1 per free tier):
```yaml
# render.yaml — add cron job
  - type: cron
    name: deltacrown-daily-tasks
    runtime: python
    schedule: "0 1 * * *"  # Daily at 1 AM UTC
    buildCommand: pip install -r requirements-prod.txt
    startCommand: python manage.py run_daily_tasks
```

Create a single management command that runs all daily tasks sequentially:
```python
# apps/core/management/commands/run_daily_tasks.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        call_command('recalculate_rankings')
        call_command('clean_expired_invites')
        call_command('send_daily_digest')
```

---

### Phase 4: Certificate Generation Safety

#### Step 4.1: Rate-Limit Certificate Tasks
```python
# apps/tournaments/tasks.py
@app.task(rate_limit='2/m', soft_time_limit=60, time_limit=90)
def generate_certificate(participant_id, tournament_id):
    ...
```

#### Step 4.2: Stream PDFs Instead of Buffering
For large batch generations, yield certificates one at a time rather than holding all in memory.

---

### Final Memory Budget

After implementing all phases:

| Process | Expected RAM |
|---------|-------------|
| **Daphne** (ASGI) | 80–120 MB |
| **Celery Worker** (solo, capped) | 60–100 MB |
| **Python base + imports** | 40–60 MB |
| **WhiteNoise static cache** | 5–15 MB |
| **Prometheus metrics** | 1–2 MB |
| **Request headroom** | 50–100 MB |
| **TOTAL** | **~236–397 MB** |

```
┌─────────────────────────────────────────────┐
│              512 MB Container                │
│                                              │
│   ┌──────────────┐  ┌──────────────────┐    │
│   │ Celery Worker │  │     Daphne       │    │
│   │ (solo, capped │  │   (foreground)   │    │
│   │  at 150 MB)   │  │  ~100 MB         │    │
│   └──────────────┘  └──────────────────┘    │
│                                              │
│   Discord Bot: DISABLED (use webhooks)       │
│   Celery Beat: DISABLED (use Render cron)    │
│                                              │
│   Peak estimated: ~350–400 MB                │
│   Safety buffer:  ~112–162 MB  ✅            │
└─────────────────────────────────────────────┘
```

---

### Priority Matrix

| Action | Effort | RAM Saved | Priority |
|--------|--------|-----------|----------|
| Disable Discord Bot | 1 min | 50–150 MB | **P0 — Do Now** |
| Split requirements (prod/dev) | 30 min | 10–20 MB | **P0 — Do Now** |
| Add `--max-memory-per-child` | 2 min | prevents leak | **P0 — Do Now** |
| Reduce `DATA_UPLOAD_MAX_MEMORY_SIZE` | 1 min | up to 30 MB | **P1 — This Week** |
| Reduce Channel Layer capacity | 1 min | 5–10 MB | **P1 — This Week** |
| Reduce WebSocket limits | 1 min | 5–10 MB | **P1 — This Week** |
| Guard homepage_context | 10 min | 1–5 MB/req | **P1 — This Week** |
| Cap `_game_cache` with LRU | 5 min | prevents leak | **P1 — This Week** |
| Disable schema serve in prod | 5 min | 10–20 MB | **P2 — Sprint** |
| Replace bot with webhooks | 2–4 hrs | permanent | **P2 — Sprint** |
| Render Cron for daily tasks | 1 hr | 30–50 MB | **P2 — Sprint** |
| Certificate rate limiting | 30 min | prevents spikes | **P2 — Sprint** |
| Add Celery task time limits | 5 min | prevents stuck tasks | **P1 — This Week** |

---

*Report generated from full codebase analysis of DeltaCrown as of March 18, 2026.*
