# 🏗️ DeltaCrown Architecture & Deployment Guide

**Date**: October 4, 2025  
**Status**: Current Architecture Analysis  
**Purpose**: Answer deployment, security, and architecture questions

---

## 📊 Architecture Overview

### System Type: **HYBRID MONOLITH**

```
┌─────────────────────────────────────────────────┐
│          DeltaCrown Django Application          │
│                                                 │
│  ┌──────────────┐        ┌─────────────────┐  │
│  │   Templates  │        │   REST API      │  │
│  │  (SSR HTML)  │◄──────►│  (/api/...)     │  │
│  └──────────────┘        └─────────────────┘  │
│         │                        │             │
│         ▼                        ▼             │
│  ┌──────────────────────────────────────────┐ │
│  │         Django ORM / Models              │ │
│  └──────────────────────────────────────────┘ │
│                     │                          │
└─────────────────────┼──────────────────────────┘
                      ▼
              ┌──────────────┐
              │  PostgreSQL  │
              └──────────────┘
```

---

## 1️⃣ Repo & Deployment

### Repository Structure
**Answer**: ✅ **SINGLE MONOREPO**

```
DeltaCrown/
├── apps/                    # Django apps (tournaments, teams, etc.)
├── deltacrown/              # Django project settings
├── templates/               # Server-side templates
├── static/                  # CSS, JS, images
├── staticfiles/             # Collected static files
├── media/                   # User uploads
├── tests/                   # Test suite
├── docs/                    # Documentation
├── scripts/                 # Helper scripts
├── manage.py
├── requirements.txt
└── pytest.ini
```

**Benefits**:
- ✅ Single source of truth
- ✅ Easy local development
- ✅ Simplified deployments
- ✅ Shared code between templates and API

**Trade-offs**:
- ⚠️ Cannot scale frontend/backend independently
- ⚠️ Single deployment pipeline
- ⚠️ Full rebuild for any change

---

### Current Deployment Setup

**Status**: 🟡 **DEVELOPMENT MODE** (Not production-configured)

**Current Configuration**:
```python
# settings.py
DEBUG = True  # ⚠️ MUST be False in production
SECRET_KEY = "dev-insecure-secret-key-change-me"  # ⚠️ MUST use env var
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.68.100"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # Currently using environment variables or defaults
    }
}
```

**Static Files**:
- Django `collectstatic` → `staticfiles/`
- Served by Django dev server (⚠️ Not production-ready)
- No CDN configured

**Media Files**:
- Local filesystem: `media/`
- No cloud storage (S3/GCS) configured

---

### CI/CD Pipeline

**Status**: ✅ **BASIC CI CONFIGURED**

**GitHub Actions** (`.github/workflows/ci.yml`):
```yaml
✅ Automated testing on push/PR
✅ PostgreSQL 16 service container
✅ Python 3.11
✅ pytest test runner
✅ Migration checks

❌ No CD (Continuous Deployment)
❌ No Docker build
❌ No staging deployment
❌ No production deployment
```

**What's Working**:
- Tests run automatically on every push
- PostgreSQL integration testing
- Migration validation

**What's Missing**:
- Deployment automation
- Environment-specific builds
- Automated rollback
- Performance testing
- Security scanning

---

### Recommended Deployment Architecture

#### **Option 1: Traditional PaaS (Recommended for MVP)**

**Platform**: Heroku, Railway, Render, DigitalOcean App Platform

```
┌─────────────────────────────────────────────┐
│            Load Balancer (HTTPS)            │
└─────────────┬───────────────────────────────┘
              │
    ┌─────────▼──────────┐
    │   Web Dynos/Apps   │  (Gunicorn + Django)
    │  (Auto-scaling)    │
    └────────┬───────────┘
             │
    ┌────────▼───────────┐
    │  Managed Postgres  │
    └────────┬───────────┘
             │
    ┌────────▼───────────┐
    │  CDN (CloudFront)  │  (Static assets)
    └────────────────────┘
```

**Pros**:
- ✅ Fast deployment (< 30 minutes)
- ✅ Managed database, backups
- ✅ Auto-scaling
- ✅ HTTPS included
- ✅ Low maintenance

**Cons**:
- ⚠️ Higher cost at scale
- ⚠️ Platform lock-in
- ⚠️ Less control

**Cost Estimate**:
- **Heroku**: $25-50/month (Hobby tier + Postgres)
- **Render**: $7-25/month (Starter tier)
- **Railway**: $5-20/month (Usage-based)

---

#### **Option 2: Docker + VPS (Cost-effective, more control)**

**Platform**: DigitalOcean Droplet, Linode, Hetzner, AWS EC2

```
┌─────────────────────────────────────┐
│           Nginx (Reverse Proxy)     │  HTTPS, static files
└─────────────┬───────────────────────┘
              │
    ┌─────────▼──────────┐
    │  Gunicorn + Django │  (Docker container)
    │   (supervisord)    │
    └────────┬───────────┘
             │
    ┌────────▼───────────┐
    │  PostgreSQL 16     │  (Docker container or managed)
    └────────────────────┘
```

**Pros**:
- ✅ Lower cost ($5-20/month)
- ✅ Full control
- ✅ Docker portability
- ✅ Easy local/prod parity

**Cons**:
- ⚠️ Manual setup required
- ⚠️ You manage backups, scaling
- ⚠️ Security updates your responsibility

**Files Needed**:
```dockerfile
# Dockerfile (NOT CURRENTLY IN REPO)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "deltacrown.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml (NOT CURRENTLY IN REPO)
version: '3.8'
services:
  web:
    build: .
    ports: ["8000:8000"]
    depends_on: [db]
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/deltacrown
  
  db:
    image: postgres:16
    volumes: [postgres_data:/var/lib/postgresql/data]
    environment:
      POSTGRES_PASSWORD: changeme

volumes:
  postgres_data:
```

---

#### **Option 3: Cloud-Native (Production Scale)**

**Platform**: AWS (ECS/EKS), GCP (Cloud Run/GKE), Azure

**Not Recommended Yet** - Overkill for current scale, wait until:
- 10,000+ daily active users
- Multiple regions needed
- Team size > 5 developers

---

## 2️⃣ API & Frontend Integration

### API Versioning

**Status**: ❌ **NOT VERSIONED**

**Current Endpoints**:
```python
# deltacrown/urls.py
path("api/tournaments/", include("apps.tournaments.api_urls")),
```

**Actual URLs**:
```
/api/tournaments/              # Tournament list
/api/tournaments/{id}/         # Tournament detail
/api/schedules/                # Schedule list
/api/capacity/                 # Capacity list
/api/finance/                  # Finance list

# State API (used by JavaScript)
/tournaments/api/{slug}/state/
/tournaments/api/{slug}/register/context/
```

**Problem**: ⚠️ **No version prefix** → Breaking changes affect all clients

**Recommendation**: Add versioning before production
```python
# Future-proof structure:
path("api/v1/tournaments/", include("apps.tournaments.api_urls")),
```

---

### API Authentication

**Status**: ✅ **SESSION + CSRF (Secure)**

**Current Setup**:
```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",  # ✅ Cookie-based
        "rest_framework.authentication.BasicAuthentication",   # ⚠️ Dev only
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",  # ⚠️ Too permissive!
    ],
}
```

**How fetch() calls work**:
```javascript
// Frontend uses session cookies + CSRF token
fetch('/api/tournaments/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken'),  // ✅ CSRF protection
        'Content-Type': 'application/json'
    },
    credentials: 'same-origin'  // ✅ Send cookies
})
```

**Security Status**:
- ✅ CSRF protection enabled
- ✅ Session-based authentication
- ⚠️ BasicAuth should be disabled in production
- ⚠️ `AllowAny` permissions too permissive

**Recommended Changes**:
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",  # Better default
    ],
}
```

---

### API Stability & Contracts

**Status**: 🟡 **SEMI-STABLE** (Phase 1 models complete)

**Stable Endpoints** (Safe for frontend to use):
```
✅ /api/tournaments/              # Tournament CRUD
✅ /api/schedules/                # Schedule data
✅ /api/capacity/                 # Capacity tracking
✅ /api/finance/                  # Finance data
✅ /tournaments/api/{slug}/state/ # Real-time state (NEW in Phase B)
```

**Contract Status**:
- ✅ Phase 1 models finalized (Schedule, Capacity, Finance, Rules, Media, Archive)
- ✅ Serializers defined
- ✅ ViewSets implemented
- ⚠️ No OpenAPI/Swagger docs
- ⚠️ No API versioning
- ⚠️ No deprecation policy

**Recommendation**: Add API documentation
```bash
pip install drf-spectacular
# Generates OpenAPI 3.0 schema automatically
```

---

## 3️⃣ Testing & Environments

### Test Coverage

**Status**: ✅ **GOOD COVERAGE** (Phase 1 & 2 complete)

**Current Tests**:
```
✅ 18/18 core integration tests passing
✅ Model tests (Tournament, Phase 1 models)
✅ API endpoint tests (ViewSets)
✅ Template rendering tests
✅ Admin interface tests
⚠️ 10/10 archive tests blocked (Stage 4 deferred)
```

**Test Types**:
- ✅ Unit tests (models, utilities)
- ✅ Integration tests (API, views)
- ✅ Template tests (rendering)
- ❌ E2E tests (Selenium/Playwright)
- ❌ Performance tests (load testing)
- ❌ Security tests (penetration testing)

**CI/CD Integration**:
```yaml
# .github/workflows/ci.yml
✅ Tests run on every push
✅ PostgreSQL 16 in CI
✅ Python 3.11
✅ pytest --maxfail=1
```

---

### Environments

**Status**: ❌ **NO STAGING ENVIRONMENT**

**Current Setup**:
```
Development → Production
     ↓             ❌
  (local)      (no staging!)
```

**Recommended Setup**:
```
Development → Staging → Production
     ↓            ↓          ↓
  (local)    (test env)  (live)
```

**Environment Variables Needed**:
```bash
# Development (current)
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=dev-key

# Staging (recommended)
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=staging-key-from-env
DATABASE_URL=postgresql://...
SENTRY_DSN=https://...
ALLOWED_HOSTS=staging.deltacrown.com

# Production
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=prod-key-from-vault
DATABASE_URL=postgresql://...
SENTRY_DSN=https://...
ALLOWED_HOSTS=deltacrown.com,www.deltacrown.com
```

---

### Testing Full Flows

**Registration Flow**: ✅ Can test locally
```
1. Create tournament (admin)
2. User registers
3. Captain approves
4. Check-in
5. Tournament runs
```

**Payment Flow**: ⚠️ **NOT IMPLEMENTED**
```
❌ No payment gateway integration
❌ No Stripe/bKash/Nagad setup
❌ Entry fee collection manual
```

**Recommendation**: 
- Add staging environment for payment testing (Stripe test mode)
- Use ngrok for webhook testing locally

---

## 4️⃣ Ops & Security

### Static Asset Serving

**Status**: 🟡 **DEVELOPMENT SETUP** (Not production-ready)

**Current Setup**:
```python
# settings.py
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Served by Django dev server
python manage.py runserver  # ⚠️ Inefficient for production
```

**Production Recommendation**:

**Option 1: Nginx + Django** (Traditional)
```nginx
# nginx.conf
location /static/ {
    alias /app/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

location /media/ {
    alias /app/media/;
    expires 7d;
}

location / {
    proxy_pass http://gunicorn:8000;
}
```

**Option 2: CDN** (Recommended for scale)
```python
# settings.py (production)
STATIC_URL = "https://cdn.deltacrown.com/static/"
AWS_STORAGE_BUCKET_NAME = "deltacrown-static"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
```

**Cost**:
- CloudFront + S3: ~$5-10/month for 100GB transfer
- CloudFlare CDN: Free tier available

---

### Logging & Monitoring

**Status**: ❌ **NOT CONFIGURED**

**Current Logging**:
```python
# No LOGGING configuration in settings.py
# Django default logging only (console)
```

**What's Missing**:
- ❌ Structured logging (JSON format)
- ❌ Log aggregation (CloudWatch, DataDog)
- ❌ Error tracking (Sentry, Rollbar)
- ❌ Performance monitoring (New Relic, Scout APM)
- ❌ Application metrics (requests/sec, response times)
- ❌ Database query monitoring

**Recommendation: Add Sentry** (Free tier available)
```python
# settings.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "development"),
    traces_sample_rate=0.1,  # 10% of transactions
)
```

**Cost**:
- Sentry: Free up to 5k events/month
- CloudWatch: ~$5-20/month
- DataDog: $15/host/month

---

### Rate Limiting & WAF

**Status**: ❌ **NOT CONFIGURED**

**Current Protection**:
```python
# Only Django's built-in CSRF protection
MIDDLEWARE = [
    "django.middleware.csrf.CsrfViewMiddleware",  # ✅ CSRF protection
]

# ❌ No rate limiting
# ❌ No WAF (Web Application Firewall)
# ❌ No DDoS protection
```

**Recommendation: Add Django Ratelimit**
```python
# Install
pip install django-ratelimit

# Usage
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='10/m', method='POST')
def register_view(request):
    # Allow 10 POST requests per minute per IP
    pass
```

**Cloud WAF** (if using cloud provider):
- AWS WAF: ~$5/month + $1 per million requests
- CloudFlare: Free tier includes basic DDoS protection

---

### Security Headers

**Status**: ⚠️ **BASIC SECURITY** (Needs hardening)

**Current Headers**:
```python
# Clickjacking protection
MIDDLEWARE = [
    "django.middleware.clickjacking.XFrameOptionsMiddleware",  # ✅
]
```

**Recommendation: Add Security Headers**
```python
# settings.py (production)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
```

---

## 🚨 Security Audit Findings

### Critical (Fix Before Production)

1. **DEBUG = True** ⚠️ **CRITICAL**
   ```python
   # Current: DEBUG = True
   # Fix: DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
   ```

2. **Insecure SECRET_KEY** ⚠️ **CRITICAL**
   ```python
   # Current: SECRET_KEY = "dev-insecure-secret-key-change-me"
   # Fix: SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")  # From vault
   ```

3. **AllowAny API Permissions** ⚠️ **HIGH**
   ```python
   # Current: DEFAULT_PERMISSION_CLASSES = ["AllowAny"]
   # Fix: Use IsAuthenticatedOrReadOnly
   ```

4. **BasicAuthentication in Production** ⚠️ **MEDIUM**
   ```python
   # Remove BasicAuthentication from REST_FRAMEWORK in production
   ```

---

### Medium Priority

5. **No rate limiting** → Add django-ratelimit
6. **No error tracking** → Add Sentry
7. **Static files served by Django** → Use Nginx or CDN
8. **No logging configuration** → Add structured logging
9. **No API versioning** → Add `/api/v1/` prefix

---

### Low Priority

10. **No staging environment** → Set up before major releases
11. **No E2E tests** → Add Playwright/Cypress tests
12. **No OpenAPI docs** → Add drf-spectacular
13. **No CDN** → Add CloudFront/CloudFlare for static assets

---

## 📋 Pre-Production Checklist

### Must-Have (Critical)

- [ ] Set `DEBUG = False`
- [ ] Use secure `SECRET_KEY` from environment
- [ ] Configure HTTPS/SSL
- [ ] Set up proper `ALLOWED_HOSTS`
- [ ] Enable `SECURE_SSL_REDIRECT`
- [ ] Configure secure cookie settings
- [ ] Remove `BasicAuthentication` from API
- [ ] Add rate limiting to authentication endpoints
- [ ] Set up error tracking (Sentry)
- [ ] Configure proper logging
- [ ] Set up database backups
- [ ] Add health check endpoint (✅ already have `/healthz/`)

### Should-Have (Important)

- [ ] Set up staging environment
- [ ] Add API versioning (`/api/v1/`)
- [ ] Configure CDN for static assets
- [ ] Set up monitoring (metrics, uptime)
- [ ] Add security headers
- [ ] Configure CSP (Content Security Policy)
- [ ] Set up automated backups
- [ ] Add load testing
- [ ] Document API endpoints (OpenAPI)
- [ ] Set up CI/CD deployment pipeline

### Nice-to-Have (Optional)

- [ ] Add E2E tests
- [ ] Set up A/B testing
- [ ] Add performance monitoring (APM)
- [ ] Configure auto-scaling
- [ ] Set up multi-region deployment
- [ ] Add feature flags
- [ ] Set up blue-green deployments
- [ ] Add automated rollback

---

## 🎯 Recommended Next Steps

### Phase 1: Security Hardening (2 hours)

1. **Create production settings file**
   ```python
   # deltacrown/settings_production.py
   from .settings import *
   
   DEBUG = False
   SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
   ALLOWED_HOSTS = os.environ["ALLOWED_HOSTS"].split(",")
   # ... security headers
   ```

2. **Add environment variable template**
   ```bash
   # .env.example
   DJANGO_DEBUG=0
   DJANGO_SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgresql://...
   ALLOWED_HOSTS=deltacrown.com,www.deltacrown.com
   ```

3. **Install Sentry for error tracking**
   ```bash
   pip install sentry-sdk
   ```

### Phase 2: Deployment Setup (4 hours)

1. **Choose deployment platform** (Render/Railway/Heroku)
2. **Create Dockerfile**
3. **Set up staging environment**
4. **Configure CI/CD deployment**
5. **Set up database backups**

### Phase 3: Monitoring & Operations (2 hours)

1. **Configure structured logging**
2. **Set up uptime monitoring** (UptimeRobot, Pingdom)
3. **Add performance monitoring** (New Relic free tier)
4. **Document runbooks** (incident response)

---

## 📞 Summary of Answers

| Question | Answer | Status |
|----------|--------|--------|
| **Single repo or split?** | Single monorepo | ✅ |
| **How deploying?** | Currently dev mode, need to choose PaaS or Docker | 🟡 |
| **CI/CD pipeline?** | Basic CI (tests), no CD | 🟡 |
| **API versioned?** | No versioning | ❌ |
| **Stable endpoints?** | Phase 1 models stable, no OpenAPI docs | 🟡 |
| **Auth method?** | Session cookies + CSRF | ✅ |
| **Staging environment?** | No staging | ❌ |
| **Tests in CI?** | Yes, pytest on every push | ✅ |
| **Static assets?** | Django dev server (not production-ready) | 🟡 |
| **Logging/monitoring?** | Not configured | ❌ |
| **Rate limiting?** | Not configured | ❌ |
| **WAF?** | Not configured | ❌ |

**Overall Status**: 🟡 **Good for development, needs hardening for production**

---

## 💡 Recommendation

Before deploying to production:

1. **Spend 2 hours on security hardening** (settings, env vars, Sentry)
2. **Choose deployment platform** (I recommend Render or Railway for MVP)
3. **Set up staging environment** (use same platform, smaller tier)
4. **Add monitoring** (Sentry free tier + UptimeRobot free)
5. **Document deployment process** (runbook for team)

**Then deploy with confidence!** 🚀

---

*Questions or need a 15-minute call? Happy to help!*
