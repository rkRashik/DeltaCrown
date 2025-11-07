# Architecture Decision Records (ADRs)

**Project:** DeltaCrown Tournament Engine  
**Version:** 1.0  
**Last Updated:** November 7, 2025

---

## Overview

This document records all significant architecture decisions made for the DeltaCrown Tournament Engine. Each decision includes context, options considered, chosen solution, and rationale.

---

## ADR-001: Service Layer Pattern

**Status:** ✅ Accepted  
**Date:** November 7, 2025  
**Deciders:** Development Team

### Context
Need to separate business logic from views and maintain clean architecture. Original planning docs placed logic in views, which makes testing difficult and violates separation of concerns.

### Decision
Implement service layer pattern with dedicated service classes for all business logic.

### Alternatives Considered
1. **Fat Models** - Put logic in model methods
   - ❌ Models become bloated
   - ❌ Hard to test in isolation
   
2. **Fat Views** - Keep logic in views
   - ❌ Views not reusable
   - ❌ Difficult to test
   
3. **Service Layer** - Separate service classes
   - ✅ Clean separation of concerns
   - ✅ Easy to test
   - ✅ Reusable across views/APIs

### Implementation
```python
# apps/tournaments/services/tournament_service.py
class TournamentService:
    @staticmethod
    def create_tournament(organizer, data):
        """Business logic for creating tournament"""
        pass
    
    @staticmethod
    def publish_tournament(tournament_id, user):
        """Business logic for publishing tournament"""
        pass
```

### Consequences
- ✅ Better testability
- ✅ Cleaner views
- ✅ Reusable logic
- ⚠️ More files to maintain
- ⚠️ Learning curve for team

### References
- **Source:** PART_2.2_SERVICES_INTEGRATION.md, Section 2

---

## ADR-002: API Versioning from Day 1

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
API will be consumed by frontend and potentially mobile apps. Need to support evolution without breaking existing clients.

### Decision
Implement URL-based API versioning starting with `/api/v1/` from the beginning.

### Alternatives Considered
1. **No Versioning** - Add later when needed
   - ❌ Breaking changes affect all clients
   - ❌ Harder to add later
   
2. **Header-Based Versioning** - Version in Accept header
   - ❌ Less visible
   - ❌ Harder to test in browser
   
3. **URL-Based Versioning** - `/api/v1/`, `/api/v2/`
   - ✅ Clear and explicit
   - ✅ Easy to test
   - ✅ Standard practice

### Implementation
```python
# deltacrown/urls.py
urlpatterns = [
    path('api/v1/', include('apps.tournaments.api.v1.urls')),
]
```

### Consequences
- ✅ Future-proof API
- ✅ Can maintain multiple versions
- ✅ Clear deprecation path
- ⚠️ More URL structure to maintain

### References
- **Source:** Strategic Recommendations, Enhancement #2

---

## ADR-003: Soft Delete Strategy

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need audit trail and ability to recover deleted data. Hard deletes lose valuable historical information and break compliance requirements.

### Decision
Implement soft delete pattern for all user-facing models using `is_deleted` flag and `deleted_at` timestamp.

### Alternatives Considered
1. **Hard Delete** - Actually delete from database
   - ❌ Data loss
   - ❌ No audit trail
   
2. **Soft Delete** - Flag as deleted
   - ✅ Data preserved
   - ✅ Audit trail maintained
   - ✅ Recovery possible
   
3. **Archive Table** - Move to separate table
   - ⚠️ Complex queries
   - ⚠️ Data duplication

### Implementation
```python
# apps/common/models.py
class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    
    class Meta:
        abstract = True
```

### Consequences
- ✅ Data preservation
- ✅ Audit trail
- ✅ Recovery capability
- ⚠️ Queries must filter is_deleted=False
- ⚠️ Storage overhead

### References
- **Source:** Strategic Recommendations, Enhancement #3

---

## ADR-004: PostgreSQL as Primary Database

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need reliable, feature-rich database for tournament management with complex queries, transactions, and concurrent access.

### Decision
Use PostgreSQL 15 as primary database.

### Alternatives Considered
1. **MySQL** - Popular open-source database
   - ⚠️ Less advanced features
   
2. **PostgreSQL** - Advanced open-source database
   - ✅ JSONB support
   - ✅ Better concurrency
   - ✅ Full-text search
   - ✅ Array types
   
3. **MongoDB** - NoSQL database
   - ❌ No transactions
   - ❌ Schema flexibility issues

### Implementation
```python
# deltacrown/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'deltacrown',
        'HOST': 'db',
        'PORT': 5432,
    }
}
```

### Consequences
- ✅ Advanced features (JSONB, arrays)
- ✅ Excellent performance
- ✅ Strong data integrity
- ✅ Great community support

### References
- **Source:** PART_2.1_ARCHITECTURE_FOUNDATIONS.md, Section 1.2

---

## ADR-005: Redis for Caching and Message Broker

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need fast caching layer and message broker for Celery tasks and real-time features.

### Decision
Use Redis 7 for both caching and Celery message broker.

### Alternatives Considered
1. **Memcached** - Pure caching
   - ❌ Can't be Celery broker
   
2. **Redis** - Cache + broker
   - ✅ Single solution for both
   - ✅ Rich data structures
   - ✅ Pub/sub support
   
3. **RabbitMQ** - Dedicated broker
   - ⚠️ Need separate cache solution

### Implementation
```python
# deltacrown/settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
    }
}

CELERY_BROKER_URL = 'redis://redis:6379/0'
```

### Consequences
- ✅ Unified solution
- ✅ Excellent performance
- ✅ Rich features
- ⚠️ Single point of failure (mitigated with replication)

### References
- **Source:** PART_2.1_ARCHITECTURE_FOUNDATIONS.md, Section 1.2

---

## ADR-006: Celery for Background Tasks

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need to handle long-running tasks (bracket generation, certificate creation, email sending) without blocking web requests.

### Decision
Use Celery with Redis broker for background task processing.

### Alternatives Considered
1. **Django-RQ** - Simpler queue
   - ⚠️ Less features
   
2. **Celery** - Full-featured task queue
   - ✅ Battle-tested
   - ✅ Rich features (retries, priorities, schedules)
   - ✅ Great monitoring tools
   
3. **Huey** - Lightweight queue
   - ⚠️ Less mature

### Implementation
```python
# deltacrown/celery.py
app = Celery('deltacrown')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### Consequences
- ✅ Non-blocking web requests
- ✅ Task retry logic
- ✅ Scheduled tasks (Celery Beat)
- ⚠️ Additional infrastructure to maintain

### References
- **Source:** PART_2.1_ARCHITECTURE_FOUNDATIONS.md, Section 1.2

---

## ADR-007: Django Channels for Real-time Features

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need real-time updates for live match progress, bracket updates, and spectator chat.

### Decision
Use Django Channels with WebSocket support for real-time features.

### Alternatives Considered
1. **Polling** - Regular AJAX requests
   - ❌ High latency
   - ❌ Server overhead
   
2. **Server-Sent Events (SSE)** - One-way streaming
   - ⚠️ Only server-to-client
   
3. **WebSocket (Channels)** - Full duplex
   - ✅ Low latency
   - ✅ Bi-directional
   - ✅ Native Django integration

### Implementation
```python
# apps/tournaments/routing.py
websocket_urlpatterns = [
    path('ws/tournament/<uuid:tournament_id>/', TournamentConsumer.as_asgi()),
]
```

### Consequences
- ✅ Real-time updates
- ✅ Better user experience
- ⚠️ More complex deployment (ASGI server)
- ⚠️ Connection management overhead

### References
- **Source:** PART_2.3_REALTIME_SECURITY.md, Section 1

---

## ADR-008: HTMX for Frontend Interactivity

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need interactive frontend without complex JavaScript framework. Want to leverage Django's template system.

### Decision
Use HTMX for AJAX requests and Alpine.js for client-side interactivity.

### Alternatives Considered
1. **React/Vue** - Full SPA framework
   - ❌ Complexity overhead
   - ❌ Separate frontend build
   
2. **jQuery** - Traditional library
   - ❌ Verbose
   - ❌ Outdated patterns
   
3. **HTMX + Alpine.js** - Modern HTML-centric
   - ✅ Simple and powerful
   - ✅ Works with Django templates
   - ✅ Progressive enhancement

### Implementation
```html
<!-- templates/tournaments/list.html -->
<div hx-get="/tournaments/" hx-trigger="load" hx-swap="innerHTML">
    Loading...
</div>

<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>
</div>
```

### Consequences
- ✅ Simple mental model
- ✅ Less JavaScript to write
- ✅ Server-side rendering
- ⚠️ Less suitable for complex SPAs

### References
- **Source:** PART_4.1_UI_UX_DESIGN_FOUNDATIONS.md, Section 2

---

## ADR-009: Tailwind CSS for Styling

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need consistent, maintainable CSS system with rapid development capability.

### Decision
Use Tailwind CSS 3.4 with custom configuration for DeltaCrown design system.

### Alternatives Considered
1. **Bootstrap** - Component framework
   - ⚠️ Generic look
   - ⚠️ Harder to customize
   
2. **Custom CSS** - Write from scratch
   - ❌ Time-consuming
   - ❌ Inconsistency risk
   
3. **Tailwind CSS** - Utility-first framework
   - ✅ Rapid development
   - ✅ Highly customizable
   - ✅ Great DX

### Implementation
```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#3B82F6',
        secondary: '#8B5CF6',
      }
    }
  }
}
```

### Consequences
- ✅ Fast development
- ✅ Consistent design
- ✅ Small production CSS (with purge)
- ⚠️ Learning curve for utility classes

### References
- **Source:** PART_4.1_UI_UX_DESIGN_FOUNDATIONS.md, Section 3

---

## ADR-010: JWT with Refresh Tokens for API Authentication

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need secure, stateless authentication for REST API consumed by frontend and mobile apps.

### Decision
Use JWT (JSON Web Tokens) with refresh token pattern for API authentication.

### Alternatives Considered
1. **Session-based** - Traditional cookies
   - ❌ Not stateless
   - ❌ CSRF concerns
   
2. **Basic Auth** - Username/password in header
   - ❌ Insecure
   
3. **JWT with Refresh** - Token-based
   - ✅ Stateless
   - ✅ Scalable
   - ✅ Mobile-friendly

### Implementation
```python
# deltacrown/settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}
```

### Consequences
- ✅ Stateless authentication
- ✅ Mobile app support
- ✅ Scalable
- ⚠️ Token revocation complexity

### References
- **Source:** Strategic Recommendations, Enhancement #8

---

## ADR-011: Database Connection Pooling with pgbouncer

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need to optimize database connections under high load and prevent connection exhaustion.

### Decision
Use pgbouncer for PostgreSQL connection pooling.

### Alternatives Considered
1. **No Pooling** - Direct connections
   - ❌ Connection overhead
   - ❌ Limited scalability
   
2. **Django Database Pooling** - App-level pooling
   - ⚠️ Per-worker pools
   
3. **pgbouncer** - External connection pooler
   - ✅ Shared pool across workers
   - ✅ Better resource usage
   - ✅ Transaction/statement pooling

### Implementation
```yaml
# docker-compose.yml
pgbouncer:
  image: pgbouncer/pgbouncer
  environment:
    - DATABASE_URL=postgres://user:pass@db:5432/deltacrown
    - POOL_MODE=transaction
    - MAX_CLIENT_CONN=1000
    - DEFAULT_POOL_SIZE=25
```

### Consequences
- ✅ Better connection management
- ✅ Higher scalability
- ✅ Lower resource usage
- ⚠️ Additional service to maintain

### References
- **Source:** Strategic Recommendations, Enhancement #12

---

## ADR-012: Pytest for Testing Framework

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need comprehensive testing framework for unit, integration, and functional tests.

### Decision
Use pytest with pytest-django plugin as primary testing framework.

### Alternatives Considered
1. **Django TestCase** - Built-in testing
   - ⚠️ Less flexible
   - ⚠️ Verbose setup
   
2. **pytest** - Modern testing framework
   - ✅ More powerful fixtures
   - ✅ Better assertion introspection
   - ✅ Extensive plugin ecosystem
   
3. **unittest** - Python standard
   - ⚠️ More boilerplate

### Implementation
```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = deltacrown.settings_test_pg
python_files = test_*.py
addopts = --cov=apps --cov-report=html --cov-report=term
```

### Consequences
- ✅ Better test experience
- ✅ Powerful fixtures
- ✅ Great plugins
- ⚠️ Different syntax than Django tests

### References
- **Source:** PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md, Section 2

---

## ADR-013: Docker for Development and Deployment

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need consistent environment across development, staging, and production.

### Decision
Use Docker and docker-compose for all environments.

### Alternatives Considered
1. **Virtual Environments** - Python venv
   - ❌ Only handles Python
   - ❌ Manual service setup
   
2. **Vagrant** - VM-based
   - ❌ Heavy resource usage
   
3. **Docker** - Container-based
   - ✅ Lightweight
   - ✅ Complete environment
   - ✅ Production parity

### Implementation
```yaml
# docker-compose.yml
services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
```

### Consequences
- ✅ Environment consistency
- ✅ Easy onboarding
- ✅ Production parity
- ⚠️ Learning curve for Docker

### References
- **Source:** SETUP_GUIDE.md, Docker Setup Section

---

## ADR-014: Environment-Specific Settings Split

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need different configurations for development, staging, and production environments.

### Decision
Split settings into base + environment-specific files.

### Alternatives Considered
1. **Single settings.py** - Environment variables only
   - ❌ Hard to manage
   - ❌ Easy to misconfigure
   
2. **Settings Split** - Separate files per environment
   - ✅ Clear separation
   - ✅ Environment-specific defaults
   - ✅ Easy to maintain

### Implementation
```python
# deltacrown/settings/
#   __init__.py
#   base.py (common settings)
#   development.py (dev overrides)
#   staging.py (staging overrides)
#   production.py (prod overrides)

# Activate with:
# export DJANGO_SETTINGS_MODULE=deltacrown.settings.development
```

### Consequences
- ✅ Clear environment separation
- ✅ Easier to maintain
- ✅ Reduces misconfiguration risk
- ⚠️ More files to manage

### References
- **Source:** Strategic Recommendations, Enhancement #6

---

## ADR-015: Structured Logging with structlog

**Status:** ✅ Accepted  
**Date:** November 7, 2025

### Context
Need better observability and debugging capability with structured, searchable logs.

### Decision
Use structlog for structured JSON logging.

### Alternatives Considered
1. **Python logging** - Standard library
   - ⚠️ Unstructured strings
   - ⚠️ Hard to parse
   
2. **structlog** - Structured logging
   - ✅ JSON output
   - ✅ Searchable fields
   - ✅ Context preservation

### Implementation
```python
# deltacrown/settings.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.JSONRenderer()
    ]
)
```

### Consequences
- ✅ Better observability
- ✅ Easier debugging
- ✅ Log aggregation friendly
- ⚠️ Slightly different API

### References
- **Source:** Strategic Recommendations, Enhancement #9

---

## Summary of Key Decisions

| ADR | Decision | Impact |
|-----|----------|--------|
| 001 | Service Layer Pattern | ⭐⭐⭐ High |
| 002 | API Versioning | ⭐⭐⭐ High |
| 003 | Soft Delete Strategy | ⭐⭐ Medium |
| 004 | PostgreSQL Database | ⭐⭐⭐ High |
| 005 | Redis Cache/Broker | ⭐⭐⭐ High |
| 006 | Celery Background Tasks | ⭐⭐⭐ High |
| 007 | Django Channels WebSocket | ⭐⭐⭐ High |
| 008 | HTMX Frontend | ⭐⭐ Medium |
| 009 | Tailwind CSS | ⭐⭐ Medium |
| 010 | JWT Authentication | ⭐⭐⭐ High |
| 011 | pgbouncer Pooling | ⭐⭐ Medium |
| 012 | pytest Testing | ⭐⭐ Medium |
| 013 | Docker Deployment | ⭐⭐⭐ High |
| 014 | Settings Split | ⭐⭐ Medium |
| 015 | structlog Logging | ⭐⭐ Medium |

---

**Next Steps:**
- Review these decisions with team
- Document any disagreements or alternatives
- Update as new decisions are made
- Reference ADR numbers in code comments

---

**Version History:**
- v1.0 (Nov 7, 2025) - Initial ADR document created

