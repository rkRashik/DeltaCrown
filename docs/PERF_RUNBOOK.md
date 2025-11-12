# Performance Tuning Runbook

**Purpose**: Operational procedures for tuning DeltaCrown's performance stack under load.

**Audience**: SRE, Platform Engineering, Backend Developers

---

## 🎛️ Tuning Levers

### 1. PgBouncer (Connection Pooling)

**Problem**: Django opens 1 DB connection per request → high connection churn under load.

**Solution**: Deploy PgBouncer in transaction pooling mode.

#### Configuration

**PgBouncer Config** (`/etc/pgbouncer/pgbouncer.ini`):
```ini
[databases]
deltacrown = host=postgres-primary.internal port=5432 dbname=deltacrown

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pooling settings
pool_mode = transaction  # CRITICAL: transaction mode for Django
max_client_conn = 500    # Max concurrent clients
default_pool_size = 25   # Connections per database

# Timeouts
server_idle_timeout = 600
query_timeout = 60
```

**Django Settings** (`settings.py`):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'pgbouncer.internal',  # Point to PgBouncer, not Postgres
        'PORT': 6432,
        'NAME': 'deltacrown',
        'USER': 'deltacrown',
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'CONN_MAX_AGE': 0,  # MUST be 0 with transaction pooling
    }
}
```

**Expected Gain**:
- 30% reduction in DB connection latency
- 40% fewer connection errors under spike load
- DB max_connections can stay at 100 (vs 500 without pooling)

**Monitoring**:
```sql
-- PgBouncer stats
SHOW POOLS;
SHOW CLIENTS;
SHOW SERVERS;

-- Postgres connection count (should stay low)
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
```

---

### 2. Celery Task Queue Tuning

**Problem**: Background tasks (notifications, certificate generation) block user-facing operations.

**Solution**: Separate queues + autoscaling workers.

#### Configuration

**Celery Routing** (`celery.py`):
```python
CELERY_TASK_ROUTES = {
    # High-priority (user-facing)
    'apps.tournaments.tasks.generate_certificate': {'queue': 'high_priority'},
    'apps.notifications.tasks.send_realtime_notification': {'queue': 'high_priority'},
    
    # Background (batch)
    'apps.economy.tasks.process_refunds_batch': {'queue': 'background'},
    'apps.support.tasks.moderate_content_scan': {'queue': 'background'},
}

CELERY_TASK_DEFAULT_QUEUE = 'default'
```

**Worker Deployment** (Kubernetes):
```yaml
# High-priority workers (autoscale 2-10)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-high-priority
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: celery
        image: deltacrown:latest
        command: ["celery", "-A", "deltacrown", "worker", "-Q", "high_priority", "--concurrency=4"]
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "2Gi"

---
# Background workers (autoscale 1-5)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-background
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: celery
        image: deltacrown:latest
        command: ["celery", "-A", "deltacrown", "worker", "-Q", "background", "--concurrency=8"]
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
```

**HPA (Horizontal Pod Autoscaler)**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-high-priority-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-high-priority
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: celery_queue_length
      target:
        type: AverageValue
        averageValue: "50"  # Scale up if queue >50 tasks
```

**Expected Gain**:
- 20% reduction in p99 latency for notification workflows
- Zero task queue stalls under load spikes
- Clear separation of priority levels

**Monitoring**:
```python
# Grafana dashboard metrics
celery_task_queue_length{queue="high_priority"}
celery_task_runtime_seconds{queue="high_priority",quantile="0.95"}
celery_worker_pool_timeouts_total
```

---

### 3. Redis Caching for Tournament Queries

**Problem**: Tournament detail pages query 8 related tables on every request.

**Impact**: p95 = 245ms for tournament view (heavy N+1 queries).

**Solution**: Cache tournament JSON with 5-minute TTL, invalidate on updates.

#### Implementation

**Cache Decorator** (`apps/tournaments/views.py`):
```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

@cache_page(60 * 5, key_prefix='tournament_detail')  # 5min TTL
def tournament_detail(request, tournament_id):
    # Queries: Tournament, Game, Teams (M2M), Registrations, Results, etc.
    tournament = get_object_or_404(Tournament.objects.select_related('game').prefetch_related('teams'), id=tournament_id)
    return render(request, 'tournaments/detail.html', {'tournament': tournament})
```

**Cache Invalidation** (`apps/tournaments/models.py`):
```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver([post_save, post_delete], sender=Tournament)
def invalidate_tournament_cache(sender, instance, **kwargs):
    cache_key = f'views.decorators.cache.cache_page.tournament_detail.{instance.id}'
    cache.delete(cache_key)
    print(f"🔥 Invalidated cache for Tournament {instance.id}")

@receiver([post_save, post_delete], sender=Registration)
def invalidate_tournament_cache_on_registration(sender, instance, **kwargs):
    # Invalidate parent tournament
    cache_key = f'views.decorators.cache.cache_page.tournament_detail.{instance.tournament.id}'
    cache.delete(cache_key)
```

**Redis Config** (production-optimized):
```yaml
# Redis deployment with persistence
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cache
spec:
  serviceName: redis-cache
  replicas: 1
  template:
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command:
          - redis-server
          - --maxmemory 2gb
          - --maxmemory-policy allkeys-lru  # Evict LRU keys when full
          - --save ""  # Disable persistence (cache only)
        resources:
          requests:
            cpu: "250m"
            memory: "2Gi"
          limits:
            cpu: "1000m"
            memory: "2Gi"
```

**Expected Gain**:
- 60% reduction in tournament view latency (245ms → 98ms)
- 80% reduction in DB query count for cached views
- ~2GB Redis memory for 10K tournaments (with 5min TTL)

**Monitoring**:
```bash
# Redis stats
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO memory | grep used_memory_human

# Cache hit rate (should be >70%)
Cache Hit Rate = keyspace_hits / (keyspace_hits + keyspace_misses)
```

---

## 📊 Performance Budget

| Component | Budget | Measurement | Action Trigger |
|-----------|--------|-------------|----------------|
| **Registration p95** | ≤215ms | Harness + APM | >215ms for 10min → alert |
| **Result Submit p95** | ≤167ms | Harness + APM | >167ms for 10min → alert |
| **WS Broadcast p95** | <5000ms | Harness + APM | >5000ms for 10min → alert |
| **Economy Transfer p95** | ≤265ms | Harness + APM | >265ms for 10min → alert |
| **DB Connection Pool** | ≤80% used | PgBouncer stats | >80% for 5min → scale DB |
| **Celery Queue Length** | <50 tasks | Redis queue monitor | >50 for 5min → scale workers |
| **Cache Hit Rate** | ≥70% | Redis INFO stats | <70% for 1hr → review TTLs |

---

## 🔥 Incident Response Playbook

### Scenario: p95 Latency Spike (>15% above baseline)

**Symptoms**:
- APM alerts: "Registration p95 = 248ms (SLO: 215ms)"
- User reports: "Tournament pages loading slowly"

**Immediate Actions**:
1. **Check DB connection pool**:
   ```sql
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   ```
   If >80% of connections active → scale PgBouncer pool.

2. **Check Celery queue depth**:
   ```bash
   celery -A deltacrown inspect active_queues
   ```
   If high_priority queue >50 tasks → scale workers.

3. **Check Redis cache hit rate**:
   ```bash
   redis-cli INFO stats | grep keyspace_hits
   ```
   If hit rate <50% → increase TTL or review cache strategy.

4. **Review slow query log**:
   ```sql
   SELECT query, mean_exec_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_exec_time DESC 
   LIMIT 10;
   ```
   If new slow query detected → add index or optimize.

**Post-Incident**:
- Update baseline if load pattern changed
- Review capacity planning (scale DB/Redis/Celery proactively)

---

### Scenario: Database Connection Pool Exhaustion

**Symptoms**:
- Error logs: "FATAL: remaining connection slots reserved"
- APM: DB connection wait time >500ms

**Immediate Actions**:
1. **Increase PgBouncer pool size** (temporary):
   ```ini
   default_pool_size = 50  # Was 25
   ```
   Restart PgBouncer: `systemctl restart pgbouncer`

2. **Kill idle connections** (emergency):
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle' AND state_change < now() - interval '5 minutes';
   ```

3. **Scale Postgres read replicas** (if read-heavy):
   ```yaml
   # Add read replica to settings.py
   DATABASES['default']['OPTIONS'] = {
       'sslmode': 'require',
       'read_default_file': '/etc/mysql/replica.cnf'
   }
   ```

**Long-term Fix**:
- Audit connection usage: `SELECT count(*) FROM pg_stat_activity GROUP BY application_name;`
- Review `CONN_MAX_AGE` setting (should be 0 with PgBouncer)
- Add connection pooling monitoring (Grafana alert)

---

## 🛠️ Tuning Checklist

Before deploying performance changes:
- [ ] Run baseline harness (500 samples)
- [ ] Deploy change to staging
- [ ] Run regression guards (`pytest tests/perf/test_slo_regression_guards.py`)
- [ ] If regression <15%, proceed to production
- [ ] If regression >15%, rollback and re-tune
- [ ] Monitor for 24 hours post-deployment
- [ ] Update baseline if new normal established

---

## 📚 Related Documentation

- [MODULE_6.6_PERF_REPORT.md](../Documents/Reports/MODULE_6.6_PERF_REPORT.md) — Baseline results
- [perf_harness.py](../tests/perf/perf_harness.py) — Load testing tool
- [PgBouncer Docs](https://www.pgbouncer.org/usage.html)
- [Celery Optimization](https://docs.celeryq.dev/en/stable/userguide/optimizing.html)
- [Django Caching](https://docs.djangoproject.com/en/5.0/topics/cache/)

---

**Last Updated**: 2025-01-20  
**Maintained By**: Platform Engineering Team
