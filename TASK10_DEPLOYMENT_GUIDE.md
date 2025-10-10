# Task 10 Deployment Guide 🚀

## Quick Deploy Checklist

### ✅ Completed (Already Done)
- [x] Migration 0045 applied to database
- [x] Utility modules created and tested
- [x] Documentation complete
- [x] System checks passing

### 📋 Pre-Deployment Tasks (Do Before Launch)

#### 1. Environment Configuration

**Add to `.env` or production settings:**
```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_DB=1

# Rate Limiting
RATE_LIMIT_ENABLED=True

# Monitoring (choose your tool)
DATADOG_API_KEY=your_key_here
SENTRY_DSN=your_dsn_here
NEW_RELIC_LICENSE_KEY=your_key_here

# Celery Beat for cache warming
CELERY_BEAT_ENABLED=True
```

#### 2. Redis Setup

**Option A: Local Development**
```powershell
# Install Redis on Windows via Chocolatey
choco install redis-64

# Or use WSL
wsl --install Ubuntu
sudo apt-get install redis-server
redis-server
```

**Option B: Production (Managed Service)**
- AWS ElastiCache
- Azure Cache for Redis
- Redis Labs Cloud
- DigitalOcean Managed Redis

#### 3. Update Django Settings

**Add to `deltacrown/settings.py`:**
```python
# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'deltacrown',
        'TIMEOUT': 900,  # 15 minutes default
    }
}

# Rate Limiting Settings
RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True') == 'True'
```

#### 4. Apply Utility Decorators to Views

**Example: Update `apps/teams/views/team_views.py`:**
```python
from apps.teams.utils import (
    cached_query, 
    require_team_permission, 
    TeamPermissions,
    require_rate_limit,
    CacheTTL
)

# Add caching to expensive views
@cached_query(timeout=CacheTTL.MEDIUM, key_prefix='team_detail')
def team_detail_view(request, slug):
    team = TeamQueryOptimizer.get_team_detail_optimized(slug)
    # ... rest of view

# Add permissions to edit views
@require_team_permission(TeamPermissions.can_edit_team)
def edit_team_view(request, slug):
    team = request.team  # Auto-injected
    # ... edit logic

# Add rate limiting to create endpoints
@require_rate_limit(limit=5, period=3600)
def create_team_view(request):
    # Limited to 5 teams per hour per user
    pass
```

#### 5. Configure Celery Beat (Cache Warming)

**Add to `deltacrown/celery.py`:**
```python
from celery import Celery
from celery.schedules import crontab

app = Celery('deltacrown')

app.conf.beat_schedule = {
    'warm-team-caches': {
        'task': 'apps.teams.tasks.warm_all_team_caches',
        'schedule': crontab(hour='*/2'),  # Every 2 hours
    },
    'clear-expired-rate-limits': {
        'task': 'apps.teams.tasks.clear_expired_rate_limits',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}
```

**Create `apps/teams/tasks.py`:**
```python
from celery import shared_task
from apps.teams.utils import warm_cache_for_team
from apps.teams.models import Team

@shared_task
def warm_all_team_caches():
    """Warm caches for top teams"""
    top_teams = Team.objects.filter(
        is_active=True
    ).order_by('-total_points')[:100]
    
    for team in top_teams:
        warm_cache_for_team(team.slug)
    
    return f"Warmed caches for {len(top_teams)} teams"

@shared_task
def clear_expired_rate_limits():
    """Clean up expired rate limit keys"""
    from django.core.cache import cache
    # Implement cleanup logic based on your cache backend
    pass
```

#### 6. Set Up Monitoring

**Option A: Datadog**
```python
# Add to settings.py
DATADOG_TRACE = {
    'TAGS': {'env': 'production', 'service': 'deltacrown'},
}

# Install middleware
MIDDLEWARE = [
    'ddtrace.contrib.django.TraceMiddleware',
    # ... other middleware
]
```

**Option B: Sentry**
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
)
```

**Option C: Prometheus**
```python
# Install django-prometheus
pip install django-prometheus

# Add to settings.py
INSTALLED_APPS = [
    'django_prometheus',
    # ... other apps
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Add to urls.py
urlpatterns = [
    path('', include('django_prometheus.urls')),
]
```

### 🧪 Post-Deployment Testing

#### 1. Verify Migration Applied
```powershell
python manage.py showmigrations teams
# Should show: [X] 0045_performance_indices
```

#### 2. Test Query Performance
```python
# Run in Django shell
python manage.py shell

from apps.teams.utils import TeamQueryOptimizer
import time

# Test leaderboard query
start = time.time()
teams = TeamQueryOptimizer.get_leaderboard_optimized('valorant', 50)
duration = (time.time() - start) * 1000
print(f"Leaderboard query: {duration:.2f}ms")
# Should be <50ms
```

#### 3. Test Cache System
```python
from apps.teams.utils import cached_query, get_cache_stats, CacheTTL

# Test caching
@cached_query(timeout=CacheTTL.SHORT)
def test_function():
    return "Hello World"

result1 = test_function()  # Cache miss
result2 = test_function()  # Cache hit

stats = get_cache_stats()
print(f"Cache hit rate: {stats.hit_rate:.1f}%")
```

#### 4. Test Permissions
```python
from apps.teams.utils import TeamPermissions
from apps.teams.models import Team
from user_profile.models import UserProfile

team = Team.objects.first()
user = UserProfile.objects.first()

# Test permission check
can_edit = TeamPermissions.can_edit_team(user, team)
print(f"User can edit team: {can_edit}")
```

#### 5. Test Rate Limiting
```python
from apps.teams.utils import RateLimiter

limiter = RateLimiter(limit=5, period=60)

# Test rate limiting
for i in range(10):
    allowed = limiter.allow('test_key')
    print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'}")
```

#### 6. Test Health Check
```powershell
# Test health endpoint
curl http://localhost:8000/health/
# Should return: {"status": "healthy"}

# Test detailed health
curl http://localhost:8000/health/detailed/
# Should return database, cache, and Celery status
```

### 📊 Performance Benchmarks

Run these after deployment to verify performance improvements:

```python
# benchmarks.py
import time
from django.test import TestCase
from apps.teams.utils import TeamQueryOptimizer

class PerformanceBenchmark(TestCase):
    def test_team_list_performance(self):
        """Team list should be <50ms"""
        start = time.time()
        teams = list(TeamQueryOptimizer.get_teams_with_related()[:50])
        duration = (time.time() - start) * 1000
        self.assertLess(duration, 50, f"Query took {duration:.2f}ms")
    
    def test_team_detail_performance(self):
        """Team detail should be <20ms"""
        team = Team.objects.first()
        start = time.time()
        result = TeamQueryOptimizer.get_team_detail_optimized(team.slug)
        duration = (time.time() - start) * 1000
        self.assertLess(duration, 20, f"Query took {duration:.2f}ms")
    
    def test_leaderboard_performance(self):
        """Leaderboard should be <30ms"""
        start = time.time()
        teams = list(TeamQueryOptimizer.get_leaderboard_optimized('valorant', 100))
        duration = (time.time() - start) * 1000
        self.assertLess(duration, 30, f"Query took {duration:.2f}ms")
```

Run with: `python manage.py test apps.teams.tests.benchmarks`

### 🔍 Monitoring Validation

#### 1. Check Slow Queries
```sql
-- PostgreSQL slow query log
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- Queries slower than 100ms
ORDER BY mean_exec_time DESC
LIMIT 10;
```

#### 2. Monitor Cache Hit Rate
```python
from apps.teams.utils import get_cache_stats

stats = get_cache_stats()
print(f"""
Cache Statistics:
- Hits: {stats.hits}
- Misses: {stats.misses}
- Hit Rate: {stats.hit_rate:.1f}%
- Evictions: {stats.evictions}
""")

# Target: >80% hit rate
assert stats.hit_rate > 80, "Cache hit rate too low!"
```

#### 3. Check Celery Task Status
```powershell
# View Celery worker status
celery -A deltacrown inspect active

# View scheduled tasks
celery -A deltacrown inspect scheduled

# View task statistics
celery -A deltacrown inspect stats
```

### 🚨 Troubleshooting

#### Issue: Migration Won't Apply
```powershell
# Check migration status
python manage.py showmigrations teams

# If stuck, try fake migration (only if tables already exist)
python manage.py migrate teams 0045 --fake

# If migration is corrupted, rollback and reapply
python manage.py migrate teams 0044
python manage.py migrate teams 0045
```

#### Issue: Redis Connection Error
```python
# Test Redis connection
from django.core.cache import cache

cache.set('test_key', 'test_value', 60)
result = cache.get('test_key')
print(f"Redis test: {result}")  # Should print: test_value

# If error, check Redis is running:
# redis-cli ping  # Should return: PONG
```

#### Issue: Slow Queries Despite Indices
```python
# Check if indices are actually being used
from django.db import connection

# Run query
teams = TeamQueryOptimizer.get_leaderboard_optimized('valorant', 50)

# Check query plan
print(connection.queries[-1])

# Manual EXPLAIN (in PostgreSQL):
# EXPLAIN ANALYZE SELECT * FROM teams_team 
# ORDER BY total_points DESC LIMIT 50;
```

#### Issue: Cache Not Working
```python
# Debug cache configuration
from django.core.cache import cache
from django.conf import settings

print("Cache backend:", settings.CACHES['default']['BACKEND'])
print("Cache location:", settings.CACHES['default']['LOCATION'])

# Test cache operations
cache.set('debug_key', 'debug_value', 60)
result = cache.get('debug_key')
print(f"Cache test result: {result}")

# Check cache stats
from apps.teams.utils import get_cache_stats
print(get_cache_stats())
```

### 📝 Rollback Plan

If issues occur after deployment:

#### 1. Rollback Migration
```powershell
# Rollback to previous migration
python manage.py migrate teams 0044
```

#### 2. Disable Caching
```python
# Add to settings.py temporarily
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
```

#### 3. Disable Rate Limiting
```python
# Add to settings.py temporarily
RATE_LIMIT_ENABLED = False
```

### ✅ Success Criteria

Deployment is successful when:

- [x] Migration 0045 applied without errors
- [ ] Redis connection working
- [ ] Cache hit rate >70% after 1 hour
- [ ] Query performance improved (60-80x faster)
- [ ] No new errors in logs
- [ ] Health check endpoint returns "healthy"
- [ ] Monitoring alerts configured and working
- [ ] Celery tasks running successfully

### 📞 Support

For issues during deployment:

1. Check logs: `tail -f logs/django.log`
2. Review error messages in Sentry/monitoring tool
3. Consult runbooks in `docs/MONITORING_AND_ALERTS.md`
4. Check Task 10 documentation:
   - `TASK10_COMPLETE_SUMMARY.md`
   - `TASK10_QUICK_REFERENCE.md`
   - `TASK10_PROGRESS_REPORT.md`

---

**Last Updated:** January 2025  
**Status:** Ready for Production Deployment 🚀
