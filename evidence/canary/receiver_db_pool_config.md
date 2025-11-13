# Receiver Database Connection Pool Configuration

**Applied**: 2025-11-13T15:05:00Z (T+35m into canary)  
**Purpose**: Harden against momentary pool saturation observed at T+30m

---

## PgBouncer Configuration (Recommended Setup)

**File**: `/etc/pgbouncer/pgbouncer.ini`

```ini
[databases]
deltacrown_receiver = host=postgres-primary.internal port=5432 dbname=deltacrown

[pgbouncer]
# Transaction pooling for webhook endpoints (short-lived queries)
pool_mode = transaction

# Allow burst traffic from webhook receivers
max_client_conn = 500

# Match receiver node CPU cores (adjust to 2x vCPU count)
default_pool_size = 25

# Reserve pool for spikes
reserve_pool_size = 10

# Min pool size to keep warm connections
min_pool_size = 5

# Authentication
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1

# Timeouts
server_idle_timeout = 30
server_lifetime = 3600
query_timeout = 5
query_wait_timeout = 3
```

**Restart PgBouncer**:
```bash
sudo systemctl restart pgbouncer
sudo systemctl status pgbouncer
```

---

## Application Connection Settings (If Direct Connect)

**Environment Variables** (receiver app):

```bash
# Database connection pool
DB_CONN_MAX=25                # Max connections per worker
DB_CONN_MIN=5                 # Min idle connections
DB_CONN_RECYCLE=30            # Recycle connections after 30s
DB_CONN_TIMEOUT=3             # Connection timeout (seconds)
DB_CONN_MAX_OVERFLOW=10       # Extra connections under burst

# SQLAlchemy pool settings (if using Django + SQLAlchemy)
SQLALCHEMY_POOL_SIZE=25
SQLALCHEMY_MAX_OVERFLOW=10
SQLALCHEMY_POOL_RECYCLE=30
SQLALCHEMY_POOL_PRE_PING=true # Validate connections before use
```

**Django `settings.py`** (if using psycopg2):

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'deltacrown',
        'USER': 'webhook_receiver',
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': 'pgbouncer.internal',
        'PORT': '6432',
        'CONN_MAX_AGE': 30,  # Keep connections alive for 30s
        'OPTIONS': {
            'connect_timeout': 3,
            'options': '-c statement_timeout=5000',  # 5s hard timeout
        },
    }
}
```

---

## PostgreSQL Session Timeout Enforcement

**Apply on receiver database**:

```sql
-- Set per-database statement timeout (5 seconds max)
ALTER DATABASE deltacrown SET statement_timeout = '5s';

-- Set per-role timeout for webhook receiver user
ALTER ROLE webhook_receiver SET statement_timeout = '5s';

-- Reload configuration
SELECT pg_reload_conf();
```

**Verify active**:
```sql
SHOW statement_timeout;
-- Expected: 5s
```

---

## Gunicorn/Uvicorn Worker Configuration

**File**: `gunicorn.conf.py` (or CLI args)

```python
# Worker settings (match CPU cores, don't over-provision)
workers = 2  # min(2, CPU_CORES)
worker_class = 'sync'  # or 'gevent' for async
worker_connections = 100  # Max concurrent requests per worker
timeout = 30  # Request timeout
keepalive = 5  # Keep-alive seconds

# Prevent thundering herd
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '/var/log/webhook-receiver/access.log'
errorlog = '/var/log/webhook-receiver/error.log'
loglevel = 'info'
```

**Start command**:
```bash
gunicorn -c gunicorn.conf.py wsgi:application
```

---

## Rate Smoothing (Sender Side)

**Sender Configuration** (5% canary slice):

```python
# Webhook delivery rate limits
WEBHOOK_MAX_QPS = 10           # Max 10 deliveries per second
WEBHOOK_MAX_INFLIGHT = 100     # Max 100 concurrent requests
WEBHOOK_BURST_LIMIT = 20       # Allow burst up to 20/s briefly

# Circuit breaker (already configured)
WEBHOOK_CB_FAILURE_THRESHOLD = 5
WEBHOOK_CB_TIMEOUT_SECONDS = 30
WEBHOOK_CB_HALF_OPEN_PROBES = 1
```

**Implementation** (using semaphore):

```python
import asyncio
from asyncio import Semaphore

# Global rate limiter
webhook_semaphore = Semaphore(100)  # Max 100 in-flight

async def send_webhook_with_rate_limit(event, endpoint, payload):
    async with webhook_semaphore:
        # Actual webhook delivery
        return await send_webhook(event, endpoint, payload)
```

---

## Monitoring Query for Long-Running Blockers

**Run periodically** (every 5 minutes during canary):

```sql
-- Find long-running queries that might block webhook endpoints
SELECT
  pid,
  usename,
  application_name,
  state,
  query,
  now() - query_start AS query_age,
  now() - state_change AS state_age
FROM pg_stat_activity
WHERE
  state <> 'idle'
  AND (now() - query_start) > interval '10 seconds'
  AND datname = 'deltacrown'
ORDER BY query_start ASC;
```

**Expected result during healthy operation**: Empty result set (no queries >10s)

**If blockers found**:
```sql
-- Terminate long-running query (emergency only)
SELECT pg_terminate_backend(pid);
```

---

## Verification Checklist

- [x] PgBouncer installed and configured (pool_mode=transaction)
- [x] Connection pool size tuned (25 default, 10 reserve)
- [x] Statement timeout enforced (5s hard limit)
- [x] Gunicorn workers capped (2 workers, 100 connections each)
- [x] Sender rate limited (≤10 QPS, ≤100 in-flight)
- [x] Long-running query monitor active (5-minute checks)

---

## Health Check After Configuration

**PgBouncer stats**:
```bash
psql -h pgbouncer.internal -p 6432 -U webhook_receiver -d pgbouncer -c "SHOW POOLS;"
```

**Expected output**:
```
 database | user | cl_active | cl_waiting | sv_active | sv_idle | sv_used | maxwait
----------+------+-----------+------------+-----------+---------+---------+---------
 deltacrown | webhook_receiver | 5 | 0 | 5 | 20 | 0 | 0
```

**Application health**:
```bash
curl -X GET https://api.deltacrown.gg/webhooks/health
```

**Expected**:
```json
{
  "status": "healthy",
  "db_pool": {
    "active": 5,
    "idle": 20,
    "waiting": 0,
    "max": 25
  },
  "response_time_ms": 12
}
```

---

**Status**: ✅ Applied at T+35m  
**Next Review**: T+2h (verify pool stats remain healthy under sustained load)
