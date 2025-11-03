# Sprint 1 - Week 1: Development Environment & Authentication Backend

**Sprint Goal:** Set up development environment and implement authentication backend  
**Duration:** Week 1 (5 days)  
**Story Points:** 40  
**Team:** Backend (3), QA (1), DevOps (1)  
**Linked Epic:** Epic 1 - Project Foundation (see `00_BACKLOG_OVERVIEW.md`)

---

## 📋 Task Cards - Backend Track (20 points)

### **BE-001: Docker Development Environment Setup**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 5  
**Assignee:** DevOps Lead  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Set up complete Docker development environment with multi-container orchestration for local development. Include PostgreSQL, Redis, Django application, and Nginx containers with hot-reload capabilities.

**Acceptance Criteria:**
- [ ] `docker-compose.yml` configured with 4 services (django, postgres, redis, nginx)
- [ ] Django app accessible at `http://localhost:8000` with hot reload
- [ ] PostgreSQL 15+ running on port 5432 with persistent volume
- [ ] Redis 7+ running on port 6379 with persistent volume
- [ ] Nginx reverse proxy configured for static files
- [ ] Environment variables managed via `.env` file (not committed)
- [ ] `docker-compose up` starts all services successfully
- [ ] Health checks implemented for all services
- [ ] Documentation updated in `README.md` with setup instructions

**Dependencies:**
- None (foundation task)

**Technical Notes:**
- Use official Docker images: `python:3.11-slim`, `postgres:15-alpine`, `redis:7-alpine`, `nginx:1.25-alpine`
- Configure volumes for persistent data: `postgres_data`, `redis_data`
- Set up bind mounts for code hot-reloading: `./apps:/app/apps`, `./templates:/app/templates`
- Reference: PROPOSAL_PART_5.md Section 3.1 (Environment Setup)

**Files to Create/Modify:**
- `docker-compose.yml` (new)
- `Dockerfile` (new)
- `.dockerignore` (new)
- `.env.example` (new)
- `README.md` (update setup section)

**Testing:**
- Run `docker-compose up` and verify all services start
- Test hot reload by modifying a Python file
- Verify database connection with `docker-compose exec django python manage.py dbshell`

---

### **BE-002: PostgreSQL + Redis Setup & Configuration**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 3  
**Assignee:** Backend Dev 1  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Configure PostgreSQL database with required extensions and Redis for caching/sessions. Set up initial database schema, connection pooling, and Redis cache backend.

**Acceptance Criteria:**
- [ ] PostgreSQL database `deltacrown_dev` created with UTF-8 encoding
- [ ] Required extensions installed: `uuid-ossp`, `pg_trgm`, `unaccent`
- [ ] Database user `deltacrown_user` created with appropriate permissions
- [ ] Django `DATABASES` setting configured with connection pooling (20 connections)
- [ ] Redis configured as Django cache backend (`django.core.cache.backends.redis.RedisCache`)
- [ ] Redis configured as session backend (`django.contrib.sessions.backends.cache`)
- [ ] Database connection verified via `python manage.py dbshell`
- [ ] Redis connection verified via Django shell (`cache.set()`, `cache.get()`)
- [ ] Initial migration runs successfully (`python manage.py migrate`)

**Dependencies:**
- BE-001 (Docker environment must be running)

**Technical Notes:**
- PostgreSQL extensions enable full-text search and UUID primary keys
- Connection pooling prevents database connection exhaustion
- Redis sessions improve performance vs database-backed sessions
- Reference: PROPOSAL_PART_2.md Section 8.1 (Infrastructure Architecture)

**Files to Create/Modify:**
- `deltacrown/settings.py` (update `DATABASES` and `CACHES`)
- `docker-compose.yml` (add postgres/redis environment variables)
- `requirements.txt` (add `psycopg2-binary`, `redis`, `hiredis`)

**Testing:**
- Run `python manage.py dbshell` and execute `\l` to list databases
- Django shell: `from django.core.cache import cache; cache.set('test', 'value'); print(cache.get('test'))`
- Verify session storage: Login and check Redis keys with `redis-cli KEYS "*session*"`

---

### **BE-003: Django Project Structure & Settings**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 2  
**Assignee:** Backend Dev 1  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Refactor Django settings for multi-environment support (development, staging, production). Set up base settings with environment-specific overrides and configure logging.

**Acceptance Criteria:**
- [ ] Settings split into `settings/base.py`, `settings/development.py`, `settings/staging.py`, `settings/production.py`
- [ ] Environment variable `DJANGO_SETTINGS_MODULE` controls active settings
- [ ] `SECRET_KEY` loaded from environment variable (not hardcoded)
- [ ] `DEBUG` mode controlled by environment variable
- [ ] `ALLOWED_HOSTS` configured per environment
- [ ] Logging configured with rotating file handler and console output
- [ ] `STATIC_ROOT` and `MEDIA_ROOT` configured
- [ ] `INSTALLED_APPS` organized into Django apps, third-party, and local apps
- [ ] All settings documented in `.env.example`

**Dependencies:**
- BE-001 (Docker environment)

**Technical Notes:**
- Use `django-environ` for environment variable management
- Log to `logs/django.log` with daily rotation (keep 30 days)
- Sentry integration placeholder (activated in production)
- Reference: PROPOSAL_PART_5.md Section 6.1 (Deployment Configuration)

**Files to Create/Modify:**
- `deltacrown/settings/base.py` (new)
- `deltacrown/settings/development.py` (new)
- `deltacrown/settings/staging.py` (new)
- `deltacrown/settings/production.py` (new)
- `deltacrown/settings/__init__.py` (new)
- `.env.example` (update with all required variables)
- `requirements.txt` (add `django-environ`)

**Testing:**
- Start server with `DJANGO_SETTINGS_MODULE=deltacrown.settings.development python manage.py runserver`
- Verify `DEBUG=True` in development, `DEBUG=False` in production settings
- Check log file created at `logs/django.log`

---

### **BE-004: User Model Customization**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 5  
**Assignee:** Backend Dev 2  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create custom User model extending Django's `AbstractUser` with additional fields for email-based authentication, profile data, and user roles (player, organizer, admin).

**Acceptance Criteria:**
- [ ] Custom `User` model created in `apps/accounts/models.py`
- [ ] Email field set as unique and used for authentication (not username)
- [ ] Additional fields: `phone_number`, `date_of_birth`, `country`, `avatar`, `bio`
- [ ] `role` field with choices: `PLAYER`, `ORGANIZER`, `ADMIN`
- [ ] `is_verified` boolean field for email verification
- [ ] UUID primary key instead of integer ID
- [ ] Custom `UserManager` with `create_user()` and `create_superuser()` methods
- [ ] Migration created and applied successfully
- [ ] `AUTH_USER_MODEL` setting points to custom model
- [ ] Admin interface registered for User model

**Dependencies:**
- BE-003 (Django settings configured)

**Technical Notes:**
- Use `AbstractUser` (not `AbstractBaseUser`) to retain Django's permission system
- UUID primary keys improve security (no sequential ID enumeration)
- Email-based auth aligns with modern web app standards
- Reference: PROPOSAL_PART_3.md Section 3.1 (User Model Specifications)

**Files to Create/Modify:**
- `apps/accounts/models.py` (create `User` and `UserManager`)
- `apps/accounts/admin.py` (register User admin)
- `deltacrown/settings/base.py` (add `AUTH_USER_MODEL = 'accounts.User'`)
- `apps/accounts/migrations/0001_initial.py` (generated)

**Testing:**
- Create superuser: `python manage.py createsuperuser`
- Login to admin at `/admin/` and verify User model visible
- Create test user via Django shell and verify all fields saved
- Test unique email constraint by attempting to create duplicate user

---

### **BE-005: JWT Authentication Endpoints**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 5  
**Assignee:** Backend Dev 2  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Implement JWT (JSON Web Token) authentication with register, login, token refresh, and logout endpoints. Use `djangorestframework-simplejwt` for token management.

**Acceptance Criteria:**
- [ ] `/api/auth/register/` - POST endpoint for user registration
- [ ] `/api/auth/login/` - POST endpoint returns access + refresh tokens
- [ ] `/api/auth/token/refresh/` - POST endpoint refreshes access token
- [ ] `/api/auth/logout/` - POST endpoint blacklists refresh token
- [ ] `/api/auth/me/` - GET endpoint returns authenticated user data
- [ ] Access token expiry: 1 hour, Refresh token expiry: 7 days
- [ ] Password validation (min 8 chars, must include letter + number)
- [ ] Email validation (valid format, unique)
- [ ] Registration sends welcome email (async with Celery)
- [ ] All endpoints return proper HTTP status codes (200, 201, 400, 401)
- [ ] API documentation generated with drf-spectacular

**Dependencies:**
- BE-004 (User model)
- BE-002 (Redis for token blacklist)

**Technical Notes:**
- Use `djangorestframework-simplejwt` for JWT implementation
- Token blacklist prevents token reuse after logout
- Async email sending prevents blocking registration response
- Reference: PROPOSAL_PART_2.md Section 4.2 (RESTful API Design)

**Files to Create/Modify:**
- `apps/accounts/serializers.py` (new - `RegisterSerializer`, `LoginSerializer`, `UserSerializer`)
- `apps/accounts/views.py` (new - `RegisterView`, `LoginView`, etc.)
- `apps/accounts/urls.py` (new)
- `deltacrown/urls.py` (include accounts urls)
- `requirements.txt` (add `djangorestframework`, `djangorestframework-simplejwt`, `drf-spectacular`)

**Testing:**
- POST `/api/auth/register/` with valid data → 201, returns tokens
- POST `/api/auth/login/` with valid credentials → 200, returns tokens
- GET `/api/auth/me/` with token in header → 200, returns user data
- GET `/api/auth/me/` without token → 401 Unauthorized
- POST `/api/auth/logout/` → 200, token blacklisted

**API Examples:**
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass1234","first_name":"John","last_name":"Doe"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass1234"}'

# Get user info
curl -X GET http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer {access_token}"
```

---

## 📋 Task Cards - DevOps Track (15 points)

### **DO-001: GitHub Repository Setup & Branch Protection**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 2  
**Assignee:** DevOps Lead  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Set up GitHub repository with branch protection rules, PR templates, issue templates, and repository settings for collaborative development.

**Acceptance Criteria:**
- [ ] Repository created at `github.com/rkRashik/DeltaCrown`
- [ ] Branch protection enabled for `master` branch (requires PR, 2 approvals)
- [ ] Branch protection enabled for `develop` branch (requires PR, 1 approval)
- [ ] PR template created (`.github/pull_request_template.md`)
- [ ] Issue templates created for bug reports, feature requests
- [ ] `.gitignore` configured for Python, Django, Node, Docker
- [ ] `CODEOWNERS` file created assigning review responsibilities
- [ ] Repository settings: Squash merging enabled, delete branches after merge
- [ ] Repository secrets configured for CI/CD (TBD in DO-002)

**Dependencies:**
- None (foundation task)

**Technical Notes:**
- Use GitHub's branch protection to enforce code review
- PR template ensures consistent description format
- CODEOWNERS automates reviewer assignment
- Reference: PROPOSAL_PART_5.md Section 6.1 (CI/CD Pipeline)

**Files to Create/Modify:**
- `.github/pull_request_template.md` (new)
- `.github/ISSUE_TEMPLATE/bug_report.md` (new)
- `.github/ISSUE_TEMPLATE/feature_request.md` (new)
- `.github/CODEOWNERS` (new)
- `.gitignore` (new)

**Testing:**
- Create test PR and verify 2 approvals required for merge to `master`
- Verify squash merge is default option
- Create test issue and verify templates appear

---

### **DO-002: CI/CD Pipeline (GitHub Actions)**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 8  
**Assignee:** DevOps Lead  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Implement complete CI/CD pipeline with GitHub Actions for automated testing, linting, security scanning, and deployment to staging environment on PR merge.

**Acceptance Criteria:**
- [ ] **CI Workflow** (`.github/workflows/ci.yml`) runs on every PR:
  - Linting with `flake8`, `pylint`, `black --check`
  - Type checking with `mypy`
  - Unit tests with `pytest` (requires >80% coverage)
  - Security scan with `bandit`, `safety`
  - Dependency vulnerability check with `pip-audit`
- [ ] **CD Workflow** (`.github/workflows/deploy-staging.yml`) runs on merge to `develop`:
  - Build Docker image
  - Push to container registry (Docker Hub or GitHub Container Registry)
  - Deploy to staging environment
  - Run smoke tests
- [ ] Build status badge added to `README.md`
- [ ] Slack notification on CI failure
- [ ] Parallel job execution (lint, test, security run simultaneously)
- [ ] CI completes in <5 minutes for typical PR

**Dependencies:**
- DO-001 (GitHub repository)
- BE-001 (Docker environment)

**Technical Notes:**
- Use GitHub Actions matrix strategy for parallel jobs
- Cache dependencies to speed up builds (`actions/cache`)
- Use secrets for sensitive data (Docker registry credentials, Slack webhook)
- Reference: PROPOSAL_PART_5.md Section 6.1 (CI/CD Pipeline)

**Files to Create/Modify:**
- `.github/workflows/ci.yml` (new)
- `.github/workflows/deploy-staging.yml` (new)
- `pytest.ini` (configure pytest)
- `.flake8` (configure flake8)
- `pyproject.toml` (configure black, mypy)
- `requirements-dev.txt` (add dev dependencies)

**Testing:**
- Create test PR with failing test → CI should fail
- Create test PR with passing tests → CI should pass, shows green checkmark
- Merge PR to `develop` → CD should trigger, deploy to staging
- Verify Slack notification received on CI failure

**GitHub Actions Example:**
```yaml
name: CI

on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install flake8 black pylint
      - run: flake8 apps/
      - run: black --check apps/
  
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: docker-compose up -d
      - run: docker-compose exec django pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

### **DO-003: Environment Configuration & Secrets Management**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 3  
**Assignee:** DevOps Lead  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Set up environment variable management for local development, staging, and production environments. Configure secrets management and create environment-specific configuration files.

**Acceptance Criteria:**
- [ ] `.env.example` file with all required environment variables documented
- [ ] Local `.env` file for development (added to `.gitignore`)
- [ ] GitHub repository secrets configured for CI/CD
- [ ] Staging environment variables configured (AWS Parameter Store, Heroku Config Vars, or equivalent)
- [ ] Production environment variables configured (separate from staging)
- [ ] Secrets rotation policy documented (90-day rotation for sensitive keys)
- [ ] Environment variables categorized: Database, Cache, API Keys, Feature Flags
- [ ] `python-decouple` or `django-environ` used for variable loading
- [ ] README section documenting all required environment variables

**Dependencies:**
- BE-003 (Django settings)

**Technical Notes:**
- Never commit `.env` file to version control
- Use different database credentials for each environment
- Feature flags enable gradual rollout of new features
- Reference: PROPOSAL_PART_5.md Section 10 (Appendix: Environment Variables)

**Environment Variables Required:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0

# Django
SECRET_KEY=generate-random-50-char-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@deltacrown.com
EMAIL_HOST_PASSWORD=app-specific-password

# AWS (for production)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=deltacrown-media

# Sentry (error tracking)
SENTRY_DSN=https://xxx@sentry.io/yyy

# Feature Flags
ENABLE_REGISTRATION=True
ENABLE_PAYMENT_GATEWAY=False
```

**Files to Create/Modify:**
- `.env.example` (new)
- `README.md` (add environment setup section)
- `deltacrown/settings/base.py` (load from environment)

**Testing:**
- Start server without `.env` file → should fail with clear error message
- Set invalid `DATABASE_URL` → should fail with connection error
- Toggle feature flag `ENABLE_REGISTRATION` → verify registration endpoint enabled/disabled

---

### **DO-004: Database Migration Scripts & Backup Strategy**

**Type:** Story  
**Priority:** Medium (P2)  
**Story Points:** 2  
**Assignee:** Backend Dev 1  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create database migration management scripts and automated backup strategy for development and production databases.

**Acceptance Criteria:**
- [ ] Migration script `scripts/migrate.sh` that runs migrations safely
- [ ] Backup script `scripts/backup_db.sh` that creates timestamped database dumps
- [ ] Restore script `scripts/restore_db.sh` that restores from backup file
- [ ] Automated daily backups configured for staging/production (cron job or cloud service)
- [ ] Backup retention policy: 7 daily, 4 weekly, 12 monthly
- [ ] Migration rollback procedure documented
- [ ] Pre-migration backup automatically created before applying migrations
- [ ] Database backup stored in secure location (AWS S3 or equivalent)
- [ ] Backup verification script (ensures backup is valid)

**Dependencies:**
- BE-002 (PostgreSQL configured)
- DO-003 (Environment variables)

**Technical Notes:**
- Use `pg_dump` for PostgreSQL backups
- Compress backups with `gzip` to save storage
- Test restore process quarterly
- Reference: PROPOSAL_PART_5.md Section 6.2 (Backup & Disaster Recovery)

**Files to Create/Modify:**
- `scripts/migrate.sh` (new)
- `scripts/backup_db.sh` (new)
- `scripts/restore_db.sh` (new)
- `scripts/verify_backup.sh` (new)
- `docs/DATABASE_BACKUP_RESTORE.md` (new)

**Backup Script Example:**
```bash
#!/bin/bash
# scripts/backup_db.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backups/deltacrown_${TIMESTAMP}.sql.gz"

docker-compose exec -T postgres pg_dump -U deltacrown_user deltacrown_dev | gzip > $BACKUP_FILE

echo "Backup created: $BACKUP_FILE"
```

**Testing:**
- Run `./scripts/backup_db.sh` → verify backup file created
- Run `./scripts/restore_db.sh backups/deltacrown_xxx.sql.gz` → verify database restored
- Delete database, restore from backup, verify all data present

---

## 📋 Task Cards - Quality Track (5 points)

### **QA-001: Test Framework Setup (pytest)**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 3  
**Assignee:** QA Engineer  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Set up pytest test framework with Django integration, coverage reporting, fixtures, and test database configuration.

**Acceptance Criteria:**
- [ ] `pytest` and `pytest-django` installed and configured
- [ ] `pytest.ini` configured with test discovery settings
- [ ] Test database configured (separate from development database)
- [ ] Factory fixtures created with `factory_boy` for User model
- [ ] Coverage reporting configured (`pytest-cov`, target >80%)
- [ ] Test command: `pytest` runs all tests
- [ ] Coverage report generated: `pytest --cov --cov-report=html`
- [ ] `conftest.py` with common fixtures (database, API client, authenticated user)
- [ ] Example test created: `tests/test_example.py` (demonstrates fixture usage)
- [ ] CI integration: tests run on every PR

**Dependencies:**
- BE-004 (User model)
- DO-002 (CI pipeline)

**Technical Notes:**
- Use `pytest-django` for Django-specific fixtures (`db`, `client`)
- Factory fixtures reduce test boilerplate
- Parallel test execution with `pytest-xdist` (speeds up CI)
- Reference: PROPOSAL_PART_5.md Section 5.1 (Testing & QA Strategy)

**Files to Create/Modify:**
- `pytest.ini` (new)
- `conftest.py` (new)
- `tests/factories.py` (new - `UserFactory`)
- `tests/test_example.py` (new)
- `requirements-dev.txt` (add pytest dependencies)

**pytest.ini Configuration:**
```ini
[pytest]
DJANGO_SETTINGS_MODULE = deltacrown.settings.development
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --reuse-db
    --cov=apps
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
```

**Testing:**
- Run `pytest` → all tests should pass
- Run `pytest --cov` → coverage report shows >80%
- Create failing test → pytest should exit with error code 1
- Verify test database created/destroyed automatically

---

### **QA-002: Code Quality Tools (pylint, black, mypy)**

**Type:** Story  
**Priority:** Medium (P2)  
**Story Points:** 2  
**Assignee:** QA Engineer  
**Sprint:** Sprint 1  
**Epic:** Epic 1 - Project Foundation

**Description:**
Configure code quality tools (linter, formatter, type checker) with pre-commit hooks to enforce code standards automatically.

**Acceptance Criteria:**
- [ ] `black` configured as code formatter (88 char line length)
- [ ] `flake8` configured as linter (ignores black conflicts)
- [ ] `pylint` configured for advanced linting
- [ ] `mypy` configured for type checking
- [ ] `isort` configured for import sorting
- [ ] Pre-commit hooks configured (`.pre-commit-config.yaml`)
- [ ] Pre-commit runs automatically on `git commit`
- [ ] Editor configuration (`.editorconfig`) for consistent formatting
- [ ] CI runs all quality checks on every PR
- [ ] Documentation in `CONTRIBUTING.md` explaining code standards

**Dependencies:**
- DO-002 (CI pipeline)

**Technical Notes:**
- Pre-commit hooks prevent committing code that fails quality checks
- Black is opinionated formatter (no configuration needed)
- Type hints improve code maintainability
- Reference: PROPOSAL_PART_5.md Section 5.1 (Testing & QA Strategy)

**Files to Create/Modify:**
- `.pre-commit-config.yaml` (new)
- `.editorconfig` (new)
- `.flake8` (new)
- `pyproject.toml` (add black, isort, mypy config)
- `.pylintrc` (new)
- `CONTRIBUTING.md` (new)
- `requirements-dev.txt` (add code quality tools)

**Pre-commit Configuration Example:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

**Testing:**
- Install pre-commit: `pre-commit install`
- Create file with bad formatting, attempt commit → pre-commit should auto-format
- Push code with linting errors → CI should fail
- Run `black --check apps/` → should pass after formatting

---

## 📊 Sprint 1 Summary

**Total Story Points:** 40  
**Total Tasks:** 11  
**Completion Criteria:** All tasks pass QA, CI pipeline green, staging deployment successful

**Team Allocation:**
- Backend Dev 1: BE-002, BE-003, DO-004 (8 points)
- Backend Dev 2: BE-004, BE-005 (10 points)
- DevOps Lead: BE-001, DO-001, DO-002, DO-003 (18 points)
- QA Engineer: QA-001, QA-002 (5 points)

**Definition of Done:**
All committed stories are code-complete, reviewed, tested, and deployed on staging with no high-priority bugs.

---

**Document Location:** `Documents/WorkList/Sprint_01_Week_01_Tasks.md`  
**Last Updated:** November 3, 2025  
**Version:** v1.0
