# Task 10: Monitoring & Alerts Configuration

## 🎯 Overview

This document defines monitoring metrics, alert thresholds, and incident response procedures for the DeltaCrown Teams app in production.

---

## 📊 Key Metrics to Monitor

### 1. Application Performance

#### Response Time Metrics
```
Metric: HTTP Response Time (p50, p95, p99)
Target: 
  - p50 < 200ms
  - p95 < 500ms
  - p99 < 1000ms

Alert Thresholds:
  - WARNING: p95 > 500ms for 5 minutes
  - CRITICAL: p95 > 1000ms for 2 minutes
```

#### Database Query Performance
```
Metric: Database Query Duration
Target: Average query time < 50ms

Alert Thresholds:
  - WARNING: Average > 100ms for 5 minutes
  - CRITICAL: Average > 250ms for 2 minutes
  - CRITICAL: Slow queries (>1s) > 10 in 5 minutes
```

#### Cache Hit Rate
```
Metric: Redis Cache Hit Rate
Target: > 80%

Alert Thresholds:
  - WARNING: Hit rate < 70% for 10 minutes
  - CRITICAL: Hit rate < 50% for 5 minutes
```

### 2. Celery Task Queue

#### Task Failure Rate
```
Metric: Celery Task Failures
Target: < 1% failure rate

Alert Thresholds:
  - WARNING: > 5 failures in 5 minutes
  - CRITICAL: > 20 failures in 5 minutes
  - CRITICAL: > 5% failure rate over 15 minutes
```

#### Queue Length
```
Metric: Celery Queue Depth
Target: < 100 tasks queued

Alert Thresholds:
  - WARNING: > 500 tasks queued for 5 minutes
  - CRITICAL: > 1000 tasks queued for 2 minutes
```

#### Task Duration
```
Metric: Task Execution Time
Target: < 30 seconds average

Alert Thresholds:
  - WARNING: Average > 60 seconds for 10 minutes
  - CRITICAL: Any task > 300 seconds (5 minutes)
```

### 3. Financial Operations

#### Coin Distribution Failures
```
Metric: Failed Coin Transactions
Target: 0 failures

Alert Thresholds:
  - WARNING: Any failed payout attempt
  - CRITICAL: > 3 failed payouts in 1 hour
  - CRITICAL: Duplicate payout detected (idempotency violation)
```

#### Ranking Recalculation
```
Metric: Ranking Job Success
Target: 100% success rate

Alert Thresholds:
  - WARNING: Ranking job failed
  - CRITICAL: Ranking job hasn't run in 25 hours
```

### 4. User Activity

#### Invite Rate
```
Metric: Team Invites Sent
Target: Normal range (based on historical data)

Alert Thresholds:
  - WARNING: > 100 invites/min (possible spam)
  - CRITICAL: > 500 invites/min (definite attack)
```

#### Failed Authentication
```
Metric: Login Failures
Target: < 5% of attempts

Alert Thresholds:
  - WARNING: > 10 failed logins from single IP in 5 minutes
  - CRITICAL: > 50 failed logins from single IP in 5 minutes
```

#### Registration Rate
```
Metric: New Team Registrations
Target: Normal variation

Alert Thresholds:
  - WARNING: > 50 new teams/hour (unusual spike)
  - CRITICAL: > 100 new teams/hour (possible bot attack)
```

### 5. Infrastructure

#### Redis Availability
```
Metric: Redis Connection Status
Target: 100% uptime

Alert Thresholds:
  - CRITICAL: Redis connection failed
  - CRITICAL: Redis memory usage > 90%
```

#### Database Connections
```
Metric: Active Database Connections
Target: < 80% of max connections

Alert Thresholds:
  - WARNING: > 80% of max connections
  - CRITICAL: > 95% of max connections
```

#### Disk Space
```
Metric: Available Disk Space
Target: > 20% free

Alert Thresholds:
  - WARNING: < 20% free space
  - CRITICAL: < 10% free space
```

---

## 🚨 Alert Definitions

### Critical Alerts (Immediate Response Required)

#### CRIT-001: Database Down
```yaml
Alert: database_connection_failed
Severity: CRITICAL
Condition: Cannot connect to database for > 30 seconds
Impact: Complete service outage
Response Time: Immediate (< 5 minutes)
Escalation: On-call engineer → Team lead → CTO

Actions:
  1. Check database server status
  2. Verify network connectivity
  3. Review database logs
  4. Failover to backup if available
  5. Notify stakeholders
```

#### CRIT-002: Duplicate Payout Detected
```yaml
Alert: duplicate_payout_detected
Severity: CRITICAL
Condition: Same deduplication key found in multiple transactions
Impact: Financial loss, user trust
Response Time: Immediate (< 5 minutes)
Escalation: On-call engineer → Finance team → Management

Actions:
  1. Stop all payout processing immediately
  2. Identify affected tournaments and users
  3. Review transaction logs
  4. Calculate financial impact
  5. Prepare rollback plan if needed
  6. Notify affected users
```

#### CRIT-003: High Task Failure Rate
```yaml
Alert: celery_high_failure_rate
Severity: CRITICAL
Condition: > 20 task failures in 5 minutes
Impact: Background jobs not processing
Response Time: < 15 minutes
Escalation: On-call engineer → Team lead

Actions:
  1. Check Celery worker status
  2. Review task error logs
  3. Identify failing task types
  4. Check Redis connectivity
  5. Restart workers if needed
```

### Warning Alerts (Monitor and Plan)

#### WARN-001: Slow Query Performance
```yaml
Alert: slow_database_queries
Severity: WARNING
Condition: > 10 queries taking > 1 second in 5 minutes
Impact: Degraded user experience
Response Time: < 1 hour
Escalation: On-call engineer

Actions:
  1. Identify slow queries via monitoring
  2. Check query execution plans
  3. Review missing indices
  4. Add to performance optimization backlog
```

#### WARN-002: Cache Hit Rate Low
```yaml
Alert: low_cache_hit_rate
Severity: WARNING
Condition: Cache hit rate < 70% for 10 minutes
Impact: Increased database load
Response Time: < 2 hours
Escalation: On-call engineer

Actions:
  1. Check Redis server status
  2. Review cache TTL settings
  3. Verify cache warming jobs
  4. Check for cache invalidation storms
```

#### WARN-003: High Invite Rate
```yaml
Alert: unusual_invite_spike
Severity: WARNING
Condition: > 100 invites/minute sustained for 5 minutes
Impact: Possible spam/abuse
Response Time: < 30 minutes
Escalation: On-call engineer → Abuse team

Actions:
  1. Identify users sending high volume
  2. Check for bot patterns
  3. Review recent account creation
  4. Enable rate limiting if not active
  5. Block abusive IPs if confirmed
```

---

## 📈 Monitoring Tools Configuration

### Datadog / New Relic Configuration

```python
# settings.py additions

MONITORING = {
    'DATADOG_API_KEY': os.getenv('DATADOG_API_KEY'),
    'SERVICE_NAME': 'deltacrown-teams',
    'ENVIRONMENT': os.getenv('ENVIRONMENT', 'production'),
    
    # Custom metrics
    'CUSTOM_METRICS': [
        'teams.created',
        'teams.invites.sent',
        'teams.roster.changed',
        'teams.tournaments.registered',
        'teams.payouts.distributed',
        'teams.payouts.failed',
    ],
    
    # APM settings
    'APM_ENABLED': True,
    'APM_SAMPLE_RATE': 1.0,  # 100% in production, adjust as needed
}
```

### Prometheus Metrics Endpoint

```python
# apps/teams/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
team_requests = Counter(
    'team_requests_total',
    'Total team-related requests',
    ['endpoint', 'method', 'status']
)

# Performance metrics
team_response_time = Histogram(
    'team_response_seconds',
    'Team endpoint response time',
    ['endpoint']
)

# Business metrics
teams_created = Counter('teams_created_total', 'Total teams created')
invites_sent = Counter('team_invites_sent_total', 'Total invites sent')
payouts_distributed = Counter('tournament_payouts_total', 'Total payouts', ['status'])

# Queue metrics
celery_queue_length = Gauge('celery_queue_length', 'Celery queue depth', ['queue'])
celery_task_duration = Histogram('celery_task_duration_seconds', 'Task duration', ['task'])
```

### Sentry Error Tracking

```python
# settings.py

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
    ],
    traces_sample_rate=0.1,  # 10% of transactions
    profiles_sample_rate=0.1,  # 10% of transactions
    environment=os.getenv('ENVIRONMENT', 'production'),
    
    # Custom error filtering
    before_send=lambda event, hint: None if should_ignore_error(event) else event,
)

def should_ignore_error(event):
    """Filter out known non-critical errors."""
    ignored_exceptions = [
        'Http404',
        'PermissionDenied',
        'SuspiciousOperation',
    ]
    
    if 'exception' in event:
        exc_type = event['exception']['values'][0]['type']
        return exc_type in ignored_exceptions
    
    return False
```

---

## 🔍 Log Aggregation

### ELK Stack / Datadog Logs

#### Critical Logs to Track

```python
# Structured logging format
import structlog

logger = structlog.get_logger()

# Financial operations
logger.info(
    "payout_distributed",
    tournament_id=tournament.id,
    team_id=team.id,
    amount=amount,
    dedup_key=dedup_key,
    user_id=captain_user.id
)

# Security events
logger.warning(
    "permission_denied",
    user_id=user.id,
    action=action,
    team_id=team.id,
    ip_address=request.META.get('REMOTE_ADDR')
)

# Performance issues
logger.warning(
    "slow_query",
    query=query_sql,
    duration_ms=duration,
    endpoint=request.path
)
```

#### Log Queries for Alerts

```
# Failed payouts
source:django level:error message:"payout" message:"failed"

# Permission violations
source:django level:warning message:"permission_denied"

# Slow queries
source:django message:"slow_query" @duration_ms:>1000

# Task failures
source:celery level:error message:"failed"

# Authentication failures
source:django message:"authentication_failed" @count:>10
```

---

## 📞 Incident Response Procedures

### Severity Levels

| Severity | Response Time | Examples |
|----------|--------------|----------|
| **P0 - Critical** | < 5 minutes | Database down, duplicate payouts, data loss |
| **P1 - High** | < 15 minutes | Celery workers down, Redis failure, high error rate |
| **P2 - Medium** | < 1 hour | Slow queries, cache issues, elevated errors |
| **P3 - Low** | < 4 hours | Minor bugs, cosmetic issues, optimization opportunities |

### On-Call Rotation

```
Primary On-Call: Backend Engineer (rotating weekly)
Secondary On-Call: Team Lead
Escalation: CTO

Schedule:
  Week 1: Engineer A
  Week 2: Engineer B
  Week 3: Engineer C
  Week 4: Engineer D
```

### Incident Communication

**Slack Channels:**
- `#incidents` - All incidents
- `#pager-critical` - P0/P1 incidents only
- `#team-leads` - Escalation channel

**Email:**
- Critical: `incidents@deltacrown.com`
- Non-critical: `alerts@deltacrown.com`

### Post-Incident Review

After every P0 or P1 incident:

1. **Within 24 hours:** Draft incident report
2. **Within 48 hours:** Conduct post-mortem meeting
3. **Within 1 week:** Implement preventive measures
4. **Document lessons learned:** Update runbooks

---

## 🛠️ Runbooks

### Runbook: Celery Worker Failure

```bash
# 1. Check worker status
celery -A deltacrown inspect active

# 2. Check queue length
celery -A deltacrown inspect stats

# 3. View recent failures
celery -A deltacrown events

# 4. Restart workers (systemd)
sudo systemctl restart celery-worker

# 5. Verify recovery
celery -A deltacrown inspect ping

# 6. Monitor for 10 minutes
watch -n 5 'celery -A deltacrown inspect stats'
```

### Runbook: Duplicate Payout Emergency

```sql
-- 1. Find duplicate transactions
SELECT 
    metadata->>'dedup_key' as dedup_key,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM economy_cointransaction
WHERE transaction_type = 'tournament_payout'
GROUP BY metadata->>'dedup_key'
HAVING COUNT(*) > 1;

-- 2. Identify affected tournaments
SELECT 
    tournament_id,
    COUNT(*) as duplicate_count
FROM economy_cointransaction
WHERE metadata->>'dedup_key' IN (
    SELECT metadata->>'dedup_key'
    FROM economy_cointransaction
    GROUP BY metadata->>'dedup_key'
    HAVING COUNT(*) > 1
);

-- 3. Calculate financial impact
SELECT 
    SUM(amount) as overpaid_amount,
    COUNT(DISTINCT user_id) as affected_users
FROM economy_cointransaction
WHERE id IN (
    SELECT id FROM (
        SELECT 
            id,
            ROW_NUMBER() OVER (PARTITION BY metadata->>'dedup_key' ORDER BY created_at) as rn
        FROM economy_cointransaction
        WHERE transaction_type = 'tournament_payout'
    ) t WHERE rn > 1
);
```

```python
# 4. Stop payout processing
from django.conf import settings
settings.CELERY_TASK_ALWAYS_EAGER = True  # Process synchronously

# 5. Rollback duplicates (careful!)
from apps.economy.models import CoinTransaction
from django.db import transaction

with transaction.atomic():
    # Identify duplicates
    duplicates = CoinTransaction.objects.raw('''
        SELECT * FROM economy_cointransaction
        WHERE id IN (
            SELECT id FROM (
                SELECT 
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY metadata->>'dedup_key' 
                        ORDER BY created_at DESC
                    ) as rn
                FROM economy_cointransaction
                WHERE transaction_type = 'tournament_payout'
            ) t WHERE rn > 1
        )
    ''')
    
    for dup in duplicates:
        # Create reversal transaction
        CoinTransaction.objects.create(
            user=dup.user,
            amount=-dup.amount,
            transaction_type='payout_reversal',
            description=f"Reversal of duplicate payout {dup.id}",
            metadata={'original_transaction_id': dup.id}
        )
```

### Runbook: Database Performance Degradation

```sql
-- 1. Find slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;

-- 2. Check missing indices
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename LIKE 'teams_%'
ORDER BY n_distinct DESC;

-- 3. Check table bloat
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;

-- 4. Vacuum if needed
VACUUM ANALYZE teams_team;
VACUUM ANALYZE teams_teammembership;
```

---

## ✅ Health Check Endpoints

### `/health/` - Basic Health Check

```python
# apps/teams/views/health.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    """
    Basic health check endpoint.
    Returns 200 if all systems operational.
    """
    checks = {
        'database': check_database(),
        'cache': check_cache(),
        'celery': check_celery(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JsonResponse({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks
    }, status=status_code)

def check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False

def check_cache():
    try:
        cache.set('health_check', 'ok', 10)
        return cache.get('health_check') == 'ok'
    except Exception:
        return False

def check_celery():
    try:
        from deltacrown.celery import app
        inspector = app.control.inspect()
        active = inspector.active()
        return bool(active)
    except Exception:
        return False
```

---

## 📊 Dashboard Widgets

### Recommended Monitoring Dashboard Layout

**Row 1: Critical Metrics**
- Database Connection Status
- Celery Worker Status
- Redis Status
- API Error Rate (5xx)

**Row 2: Performance**
- Response Time (p50, p95, p99)
- Database Query Time
- Cache Hit Rate
- Celery Queue Length

**Row 3: Business Metrics**
- Teams Created (24h)
- Invites Sent (24h)
- Payouts Distributed (24h)
- Active Users (24h)

**Row 4: Infrastructure**
- CPU Usage
- Memory Usage
- Disk Usage
- Network I/O

---

## 🔔 Alert Routing

```yaml
# PagerDuty / Opsgenie routing rules

Critical Alerts (P0):
  - Page on-call engineer immediately
  - Send SMS + phone call
  - Escalate to team lead after 5 minutes no-ack
  - Escalate to CTO after 15 minutes no-resolution

High Priority (P1):
  - Page on-call engineer
  - Send Slack notification to #incidents
  - Escalate after 15 minutes no-ack

Medium Priority (P2):
  - Send Slack notification
  - Email on-call engineer
  - No escalation

Low Priority (P3):
  - Create ticket
  - Email notification
  - No pages
```

---

**Document Version:** 1.0  
**Last Updated:** October 9, 2025  
**Owner:** DevOps Team  
**Review Schedule:** Quarterly
