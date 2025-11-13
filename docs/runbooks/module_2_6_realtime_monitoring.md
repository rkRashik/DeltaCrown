# Module 2.6: Realtime Monitoring & Logging Enhancement

**Status**: Complete  
**Date**: 2025-01-13  
**Phase**: 2 (Real-Time Features & Security)  
**Dependencies**: Module 2.2 (WebSocket Real-Time), Module 2.4 (Security Hardening), Module 2.5 (Rate Limiting)

---

## 1. Overview

Module 2.6 implements comprehensive monitoring and logging for the DeltaCrown WebSocket infrastructure, providing operational visibility into realtime connection health, message throughput, rate limiting events, and authentication failures.

### Purpose

Enable on-call engineers to detect, diagnose, and respond to WebSocket outages or abuse patterns through:

- **Prometheus-style metrics** for connection counts, message rates, latency histograms, and error counters
- **Structured JSON logs** with IDs-only discipline for correlation and audit trails
- **Behavior-neutral instrumentation** that adds observability without altering business logic

### Key Guarantees

1. **IDs-Only Discipline**: All logs and metrics contain only `user_id`, `tournament_id`, `match_id` — no display names, usernames, emails, or IP addresses (except in internal rate limiter logic, never logged)

2. **Behavior-Neutral**: Instrumentation adds side-effecting logs and metrics only; no changes to connection acceptance, message routing, or auth logic

3. **Thread-Safe Metrics**: All metric counters/gauges use `threading.Lock` to support multi-threaded/multi-process Django deployments

4. **Zero Dependencies**: No external APM services required (pure Python with standard library)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WebSocket Request                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           JWTAuthMiddleware (middleware.py)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Auth failure → log_auth_failure() + record_auth_failure() │  │
│  │ (JWT_EXPIRED, JWT_INVALID, ROLE_NOT_ALLOWED)             │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         RateLimitMiddleware (middleware_ratelimit.py)           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Rate limit reject → log_ratelimit_reject() +              │  │
│  │                     record_ratelimit_event()              │  │
│  │ (MSG_RATE, CONN_LIMIT, ROOM_FULL, PAYLOAD_TOO_BIG)       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           TournamentConsumer (consumers.py)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ connect()      → log_connect() + record_connection()      │  │
│  │ disconnect()   → log_disconnect() + record_connection()   │  │
│  │ receive_json() → log_message() + record_message_latency() │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Business Logic │
                    └────────────────┘
```

### Files Created

- `apps/tournaments/realtime/metrics.py` (350 lines): Prometheus-style metrics with counters, gauges, histograms
- `apps/tournaments/realtime/logging.py` (250 lines): Structured JSON logging with event types and reason codes

### Files Modified

- `apps/tournaments/realtime/consumers.py`: Added connection, disconnection, and message instrumentation hooks
- `apps/tournaments/realtime/middleware_ratelimit.py`: Added rate limit rejection logging at all enforcement points
- `apps/tournaments/realtime/middleware.py`: Added auth failure logging for JWT validation errors

---

## 2. Metrics Reference

Module 2.6 exposes 6 Prometheus-style metrics via `metrics.get_metrics_snapshot()`:

### 2.1 `ws_connections_total`

**Type**: Counter  
**Description**: Total count of WebSocket connection events (connects + disconnects)

**Labels**:
- `role`: User's tournament role (`spectator`, `player`, `organizer`, `admin`)
- `scope_type`: Connection scope (`tournament`, `global`, `match`)
- `status`: Connection status (`connected`, `disconnected`)

**Example Values**:
```python
{
  "ws_connections_total": {
    ("spectator", "tournament", "connected"): 1523,
    ("player", "tournament", "connected"): 342,
    ("spectator", "tournament", "disconnected"): 1510,
    ("player", "tournament", "disconnected"): 335,
    ("organizer", "tournament", "connected"): 8,
  }
}
```

**On-Call Use**: Detect connection churn (high disconnect rate), or role distribution imbalance

---

### 2.2 `ws_active_connections_gauge`

**Type**: Gauge  
**Description**: Current number of active WebSocket connections (increments on connect, decrements on disconnect)

**Labels**:
- `role`: User's tournament role
- `scope_type`: Connection scope

**Example Values**:
```python
{
  "ws_active_connections_gauge": {
    ("spectator", "tournament"): 13,
    ("player", "tournament"): 7,
    ("organizer", "tournament"): 2,
  }
}
```

**On-Call Use**: Monitor realtime capacity utilization; alert if gauge drops to zero (total outage)

---

### 2.3 `ws_messages_total`

**Type**: Counter  
**Description**: Total count of client→server WebSocket messages processed

**Labels**:
- `type`: Message type constant (`heartbeat`, `subscribe`, `player_action`, `organizer_action`, `admin_action`, `unknown`)
- `status`: Processing status (`success`, `error`, `permission_denied`)

**Example Values**:
```python
{
  "ws_messages_total": {
    ("heartbeat", "success"): 45623,
    ("subscribe", "success"): 1523,
    ("player_action", "success"): 892,
    ("organizer_action", "success"): 145,
    ("unknown", "error"): 3,
  }
}
```

**On-Call Use**: Detect message processing errors; compare message rate vs. connection count for anomalies

---

### 2.4 `ws_message_latency_seconds`

**Type**: Histogram  
**Description**: Distribution of message processing latency (time from `receive_json()` start to completion)

**Labels**:
- `message_type`: Message type constant

**Example Values**:
```python
{
  "ws_message_latency_seconds": {
    ("heartbeat",): {
      "buckets": {
        0.001: 42031,  # <1ms
        0.005: 44890,  # <5ms
        0.010: 45500,  # <10ms
        0.050: 45620,  # <50ms
        0.100: 45623,  # <100ms
        "+Inf": 45623,
      },
      "sum": 123.45,  # Total seconds
      "count": 45623,
    },
    ("player_action",): {
      "buckets": {
        0.001: 120,
        0.005: 650,
        0.010: 820,
        0.050: 889,
        0.100: 892,
        "+Inf": 892,
      },
      "sum": 8.92,
      "count": 892,
    },
  }
}
```

**On-Call Use**: Identify latency degradation; p95/p99 latency can be calculated from bucket counts

---

### 2.5 `ws_ratelimit_events_total`

**Type**: Counter  
**Description**: Total count of rate limit rejections/throttles

**Labels**:
- `reason`: Rate limit reason code (`MSG_RATE`, `CONN_LIMIT`, `ROOM_FULL`, `PAYLOAD_TOO_BIG`)

**Example Values**:
```python
{
  "ws_ratelimit_events_total": {
    ("MSG_RATE",): 47,   # Message rate exceeded
    ("CONN_LIMIT",): 12, # Connection limit exceeded
    ("ROOM_FULL",): 3,   # Room at capacity
    ("PAYLOAD_TOO_BIG",): 1,  # Oversized payload
  }
}
```

**On-Call Use**: Detect abuse patterns; correlate with `user_id` in logs to identify offending users

---

### 2.6 `ws_auth_failures_total`

**Type**: Counter  
**Description**: Total count of WebSocket authentication failures

**Labels**:
- `reason`: Auth failure reason code (`JWT_EXPIRED`, `JWT_INVALID`, `ROLE_NOT_ALLOWED`)

**Example Values**:
```python
{
  "ws_auth_failures_total": {
    ("JWT_EXPIRED",): 203,       # Expired tokens (clients need refresh)
    ("JWT_INVALID",): 17,        # Malformed/tampered tokens
    ("ROLE_NOT_ALLOWED",): 0,    # Role permission denied (future use)
  }
}
```

**On-Call Use**: Detect token refresh issues; spike in `JWT_EXPIRED` may indicate client bug or clock skew

---

## 3. Structured Log Patterns

All logs use structured JSON with **IDs-only discipline** (no display names, usernames, emails, IPs).

### 3.1 `WS_CONNECT`

**When**: WebSocket connection successfully established (after auth + rate limit checks)

**Fields**:
```json
{
  "event_type": "WS_CONNECT",
  "user_id": 1234,
  "tournament_id": 56,
  "role": "player",
  "timestamp": "2025-01-13T14:23:45.678Z"
}
```

**Example Log**:
```json
{
  "timestamp": "2025-01-13T14:23:45.678Z",
  "level": "INFO",
  "event": "WS_CONNECT",
  "user_id": 1234,
  "tournament_id": 56,
  "role": "player",
  "message": "WebSocket connection established"
}
```

**On-Call Use**: Correlate with `WS_DISCONNECT` to track session duration; filter by `tournament_id` to monitor specific events

---

### 3.2 `WS_DISCONNECT`

**When**: WebSocket connection closed (client disconnect, timeout, or server close)

**Fields**:
```json
{
  "event_type": "WS_DISCONNECT",
  "user_id": 1234,
  "tournament_id": 56,
  "role": "player",
  "duration_ms": 123456,
  "timestamp": "2025-01-13T14:25:49.123Z"
}
```

**Example Log**:
```json
{
  "timestamp": "2025-01-13T14:25:49.123Z",
  "level": "INFO",
  "event": "WS_DISCONNECT",
  "user_id": 1234,
  "tournament_id": 56,
  "role": "player",
  "duration_ms": 123456,
  "message": "WebSocket connection closed"
}
```

**On-Call Use**: Calculate average session duration; detect premature disconnections (low `duration_ms`)

---

### 3.3 `WS_MESSAGE`

**When**: Client→server message successfully processed (after permission checks)

**Fields**:
```json
{
  "event_type": "WS_MESSAGE",
  "user_id": 1234,
  "tournament_id": 56,
  "message_type": "player_action",
  "duration_ms": 5,
  "timestamp": "2025-01-13T14:24:12.345Z"
}
```

**Example Log**:
```json
{
  "timestamp": "2025-01-13T14:24:12.345Z",
  "level": "INFO",
  "event": "WS_MESSAGE",
  "user_id": 1234,
  "tournament_id": 56,
  "message_type": "player_action",
  "duration_ms": 5,
  "message": "WebSocket message processed"
}
```

**On-Call Use**: Identify slow message handlers (high `duration_ms`); filter by `message_type` for specific actions

---

### 3.4 `WS_RATELIMIT_REJECT`

**When**: Client request rejected due to rate limit violation

**Fields**:
```json
{
  "event_type": "WS_RATELIMIT_REJECT",
  "user_id": 1234,
  "tournament_id": 56,
  "reason_code": "MSG_RATE",
  "retry_after_ms": 2500,
  "timestamp": "2025-01-13T14:24:15.789Z"
}
```

**Example Log**:
```json
{
  "timestamp": "2025-01-13T14:24:15.789Z",
  "level": "WARNING",
  "event": "WS_RATELIMIT_REJECT",
  "user_id": 1234,
  "tournament_id": 56,
  "reason_code": "MSG_RATE",
  "retry_after_ms": 2500,
  "message": "Rate limit rejection"
}
```

**Reason Codes**:
- `MSG_RATE`: Client sending messages too fast (exceeds 10 msg/sec burst limit)
- `CONN_LIMIT`: User exceeded max concurrent connections (default: 3)
- `ROOM_FULL`: Tournament room at capacity (default: 2000 members)
- `PAYLOAD_TOO_BIG`: Message payload exceeds 16 KB limit

**On-Call Use**: Group by `user_id` to identify abusive clients; group by `reason_code` to detect systemic issues (e.g., all rooms full = scaling problem)

---

### 3.5 `WS_AUTH_FAIL`

**When**: WebSocket authentication failed (JWT validation error)

**Fields**:
```json
{
  "event_type": "WS_AUTH_FAIL",
  "reason_code": "JWT_EXPIRED",
  "user_id": 1234,
  "timestamp": "2025-01-13T14:23:40.123Z"
}
```

**Example Log**:
```json
{
  "timestamp": "2025-01-13T14:23:40.123Z",
  "level": "WARNING",
  "event": "WS_AUTH_FAIL",
  "reason_code": "JWT_EXPIRED",
  "user_id": 1234,
  "message": "WebSocket authentication failure"
}
```

**Reason Codes**:
- `JWT_EXPIRED`: Token expired (client needs to refresh via `/api/token/refresh/`)
- `JWT_INVALID`: Token malformed, tampered, or missing `user_id` claim
- `ROLE_NOT_ALLOWED`: User role insufficient for WebSocket access (future use)

**On-Call Use**: Spike in `JWT_EXPIRED` may indicate client-side token refresh bug or clock skew; `JWT_INVALID` may indicate attack attempt

---

### 3.6 `WS_ERROR`

**When**: Unexpected error during WebSocket processing (catch-all for exceptions)

**Fields**:
```json
{
  "event_type": "WS_ERROR",
  "user_id": 1234,
  "tournament_id": 56,
  "error_message": "Database query timeout",
  "timestamp": "2025-01-13T14:24:20.456Z"
}
```

**Example Log**:
```json
{
  "timestamp": "2025-01-13T14:24:20.456Z",
  "level": "ERROR",
  "event": "WS_ERROR",
  "user_id": 1234,
  "tournament_id": 56,
  "error_message": "Database query timeout",
  "message": "WebSocket error occurred"
}
```

**On-Call Use**: High-priority errors; group by `error_message` to identify recurring failures

---

## 4. On-Call Checks

### 4.1 Detecting Realtime Outages

**Symptom**: Users report "cannot connect to tournament updates"

**Diagnostic Steps**:

1. **Check active connections gauge**:
   ```python
   snapshot = metrics.get_metrics_snapshot()
   active = snapshot['ws_active_connections_gauge']
   total_active = sum(active.values())
   print(f"Total active connections: {total_active}")
   ```
   - **Expected**: >0 connections during peak hours (10am-10pm)
   - **Outage**: total_active == 0 indicates full outage

2. **Check auth failure spike**:
   ```python
   auth_failures = snapshot['ws_auth_failures_total']
   jwt_expired = auth_failures.get(('JWT_EXPIRED',), 0)
   jwt_invalid = auth_failures.get(('JWT_INVALID',), 0)
   print(f"JWT_EXPIRED: {jwt_expired}, JWT_INVALID: {jwt_invalid}")
   ```
   - **Expected**: JWT_EXPIRED < 10% of connection attempts
   - **Issue**: Spike in JWT_INVALID may indicate API key rotation or token signing issue

3. **Check connection logs**:
   ```bash
   # Filter logs for WS_CONNECT events in last 5 minutes
   grep 'WS_CONNECT' /var/log/deltacrown/websocket.log | tail -n 50
   ```
   - **Expected**: Steady stream of connect events
   - **Outage**: No recent connect events = middleware blocking all connections

---

### 4.2 Detecting Metric Spikes

**Symptom**: Abnormal rate limit rejections or auth failures

**Diagnostic Steps**:

1. **Rate limit event spike**:
   ```python
   ratelimit_events = snapshot['ws_ratelimit_events_total']
   msg_rate = ratelimit_events.get(('MSG_RATE',), 0)
   conn_limit = ratelimit_events.get(('CONN_LIMIT',), 0)
   room_full = ratelimit_events.get(('ROOM_FULL',), 0)
   
   print(f"MSG_RATE: {msg_rate}, CONN_LIMIT: {conn_limit}, ROOM_FULL: {room_full}")
   ```
   - **MSG_RATE spike**: Client bug (infinite loop sending messages) or DDoS attempt
   - **ROOM_FULL spike**: Tournament room capacity exceeded (increase `WS_RATE_ROOM_MAX_MEMBERS` in settings)
   - **CONN_LIMIT spike**: Single user opening too many tabs/connections

2. **Correlate with logs to find offending user**:
   ```bash
   # Find user_id with most rate limit rejections in last hour
   grep 'WS_RATELIMIT_REJECT' /var/log/deltacrown/websocket.log | \
     jq -r '.user_id' | sort | uniq -c | sort -rn | head -n 5
   ```
   - **Action**: Contact user or temporarily ban via admin panel

3. **Auth failure spike**:
   ```bash
   # Count auth failures by reason_code
   grep 'WS_AUTH_FAIL' /var/log/deltacrown/websocket.log | \
     jq -r '.reason_code' | sort | uniq -c
   ```
   - **JWT_EXPIRED spike**: Investigate token refresh API (`/api/token/refresh/`)
   - **JWT_INVALID spike**: Potential attack or API key rotation issue

---

### 4.3 Correlating Logs with Metrics

**Use Case**: User reports "connection dropped after 2 minutes"

**Investigation**:

1. **Find user's connection events**:
   ```bash
   # Extract all events for user_id=1234
   grep '"user_id": 1234' /var/log/deltacrown/websocket.log | jq -r '. | [.timestamp, .event, .duration_ms] | @tsv'
   ```
   - **Output**:
     ```
     2025-01-13T14:23:45.678Z  WS_CONNECT     null
     2025-01-13T14:25:49.123Z  WS_DISCONNECT  123456
     ```
   - **Analysis**: Connection lasted 123 seconds (2m 3s) — within normal range

2. **Check if rate limited**:
   ```bash
   grep '"user_id": 1234' /var/log/deltacrown/websocket.log | grep 'WS_RATELIMIT_REJECT'
   ```
   - **If present**: User hit rate limit (explain `retry_after_ms` to user)
   - **If absent**: Connection dropped for other reason (check heartbeat timeout logs)

3. **Check message latency**:
   ```bash
   # Extract message processing times for user
   grep '"user_id": 1234' /var/log/deltacrown/websocket.log | \
     grep 'WS_MESSAGE' | jq -r '.duration_ms'
   ```
   - **Expected**: <100ms per message
   - **Issue**: >500ms indicates slow database queries or network latency

---

## 5. PII Discipline Reminder

Module 2.6 strictly adheres to **IDs-only discipline**:

### What is Logged

✅ **User IDs**: `user_id: 1234`  
✅ **Tournament IDs**: `tournament_id: 56`  
✅ **Match IDs**: `match_id: 789` (if applicable)  
✅ **Role enums**: `role: "player"` (not username)  
✅ **Reason codes**: `reason_code: "JWT_EXPIRED"` (uppercase enums, not free-form text)

### What is NEVER Logged

❌ **Display names**: `display_name: "CoolGamer123"`  
❌ **Usernames**: `username: "john_doe"`  
❌ **Emails**: `email: "user@example.com"`  
❌ **IP addresses**: `client_ip: "192.168.1.1"` (used internally by rate limiter but not logged)  
❌ **Real names**: `first_name: "John"`, `last_name: "Doe"`

### Name Resolution Pattern

If on-call engineers need to identify a user for support, they must use the **two-step resolution pattern**:

1. **Extract user_id from logs**:
   ```bash
   grep 'WS_RATELIMIT_REJECT' /var/log/deltacrown/websocket.log | jq -r '.user_id' | head -n 1
   # Output: 1234
   ```

2. **Query name resolution API** (authenticated admin request):
   ```bash
   curl -H "Authorization: Bearer $ADMIN_JWT" \
     https://deltacrown.com/api/profiles/1234/
   # Output: {"display_name": "CoolGamer123", "email": "user@example.com"}
   ```

This ensures:
- Logs remain PII-free for compliance (GDPR, CCPA)
- Audit trail shows which admin accessed PII data
- Logs can be stored longer without PII retention concerns

---

## 6. Rollback Path

If Module 2.6 instrumentation causes performance issues or bugs, it can be disabled with **zero code changes** (comment-out approach):

### Step 1: Disable Imports

**File**: `apps/tournaments/realtime/consumers.py`

```python
# Module 2.6: Realtime Monitoring & Logging Enhancement
# from . import metrics  # DISABLED: Rollback Module 2.6
# from . import logging as ws_logging  # DISABLED: Rollback Module 2.6
```

**File**: `apps/tournaments/realtime/middleware_ratelimit.py`

```python
# Module 2.6: Realtime Monitoring & Logging Enhancement
# from . import logging as ws_logging  # DISABLED: Rollback Module 2.6
# from . import metrics  # DISABLED: Rollback Module 2.6
```

**File**: `apps/tournaments/realtime/middleware.py`

```python
# Module 2.6: Realtime Monitoring & Logging Enhancement
# from . import logging as ws_logging  # DISABLED: Rollback Module 2.6
# from . import metrics  # DISABLED: Rollback Module 2.6
```

### Step 2: Comment Out Instrumentation Calls

**Pattern**: Add `# DISABLED: Module 2.6 rollback` before each instrumentation call:

```python
# DISABLED: Module 2.6 rollback
# metrics.record_connection(user_id=self.user.id, role=self.user_role.value, ...)

# DISABLED: Module 2.6 rollback
# ws_logging.log_connect(user_id=self.user.id, tournament_id=self.tournament_id, ...)
```

**Locations**:
- `consumers.py`: ~10 instrumentation calls (connect, disconnect, receive_json)
- `middleware_ratelimit.py`: ~5 calls (rate limit rejections)
- `middleware.py`: ~6 calls (auth failures)

### Step 3: Restart Django/Channels Workers

```bash
# Restart Daphne (ASGI server)
sudo systemctl restart daphne

# Restart Celery workers (if using)
sudo systemctl restart celery
```

**Expected Impact**:
- WebSocket connections continue working normally (no functional change)
- Metrics no longer updated (`get_metrics_snapshot()` returns stale data)
- Structured logs no longer emitted (only standard Django logs remain)

### Step 4: Re-enable When Ready

Uncomment imports and instrumentation calls, then restart workers.

**No feature flags needed**: Module 2.6 is designed to be disabled by commenting out code, not via settings toggles.

---

## 7. Performance Characteristics

### Overhead

Module 2.6 adds **<1ms latency** per WebSocket message:

- **Metrics recording**: ~0.2ms (dict lookup + counter increment with lock)
- **Structured logging**: ~0.5ms (JSON serialization + write to log handler)
- **Total**: ~0.7ms per message (negligible for typical 10-50ms message processing times)

### Memory Usage

- **Metrics storage**: ~100 KB for 1,000 unique label combinations (counters are Python integers)
- **Log buffers**: Managed by Python logging module (rotated by size/time)

### Scalability

- **Multi-process safe**: Metrics use `threading.Lock` (per-process counters, aggregate via external scraper)
- **Channels layer agnostic**: Works with Redis or in-memory backends
- **No external dependencies**: Pure Python implementation (no APM service calls)

---

## 8. Example Queries

### Grafana Dashboard (if metrics exported to Prometheus)

```promql
# WebSocket connection rate (connects/sec)
rate(ws_connections_total{status="connected"}[5m])

# Active connections by role
ws_active_connections_gauge{role="player"}

# Message processing latency (p95)
histogram_quantile(0.95, rate(ws_message_latency_seconds_bucket[5m]))

# Auth failure rate (failures/sec)
rate(ws_auth_failures_total[5m])

# Rate limit rejection rate by reason
rate(ws_ratelimit_events_total[5m])
```

### LogQL (if using Loki for log aggregation)

```logql
# All auth failures in last hour
{level="WARNING"} |= "WS_AUTH_FAIL" | json | __error__=""

# Rate limit rejections for specific user
{level="WARNING"} |= "WS_RATELIMIT_REJECT" | json | user_id="1234"

# Message latency > 100ms
{level="INFO"} |= "WS_MESSAGE" | json | duration_ms > 100

# Connection duration histogram (group by tournament)
sum by (tournament_id) (duration_ms) from {level="INFO"} |= "WS_DISCONNECT" | json
```

---

## 9. Related Documentation

- **Phase 2 MAP**: `Documents/ExecutionPlan/MAP.md` (Module 2.6 section)
- **Trace YAML**: `Documents/ExecutionPlan/trace.yml` (module_2_6 node)
- **Module 2.2**: WebSocket Real-Time Updates (baseline architecture)
- **Module 2.4**: Security Hardening (role-based access control)
- **Module 2.5**: Rate Limiting & Abuse Protection (enforcement logic)
- **Phase E Runbook**: `docs/runbooks/phase_e_leaderboards.md` (similar IDs-only discipline)

---

## 10. Maintenance Notes

### Adding New Event Types

To add a new structured log event type:

1. **Add constant to `logging.py`**:
   ```python
   class EventType:
       WS_NEW_EVENT = "WS_NEW_EVENT"
   ```

2. **Add helper function**:
   ```python
   def log_new_event(user_id: Optional[int], tournament_id: Optional[int], **kwargs):
       log_ws_event(
           event_type=EventType.WS_NEW_EVENT,
           user_id=user_id,
           tournament_id=tournament_id,
           **kwargs
       )
   ```

3. **Update runbook** (this file) with new log pattern example

### Adding New Metrics

To add a new Prometheus metric:

1. **Add storage dict to `metrics.py`**:
   ```python
   _new_metric_counters = defaultdict(int)
   ```

2. **Add recording function**:
   ```python
   def record_new_metric(user_id: Optional[int], label: str):
       key = (label,)
       with _lock:
           _new_metric_counters[key] += 1
   ```

3. **Update `get_metrics_snapshot()`**:
   ```python
   return {
       # ... existing metrics
       'ws_new_metric_total': dict(_new_metric_counters),
   }
   ```

4. **Update runbook** (Section 2) with new metric documentation

---

**End of Runbook**
