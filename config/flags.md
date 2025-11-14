# DeltaCrown Feature Flags Configuration

This document lists all feature flags, their default values, and rollback procedures.

---

## Moderation & Enforcement

### MODERATION_OBSERVABILITY_ENABLED
- **Default**: `false` (OFF)
- **Type**: Boolean
- **Purpose**: Enable Prometheus metrics emission for moderation gate decisions
- **Impact**: When OFF (default), zero overhead, no metrics. When ON, metrics at `/metrics` endpoint.
- **Rollback**: Set to `false` and restart application

**Usage**:
```bash
# Environment variable
export MODERATION_OBSERVABILITY_ENABLED=true

# Or in settings.py
MODERATION_OBSERVABILITY_ENABLED = os.getenv('MODERATION_OBSERVABILITY_ENABLED', 'false').lower() == 'true'
```

---

### MODERATION_CACHE_ENABLED
- **Default**: `true` (ON)
- **Type**: Boolean
- **Purpose**: Enable caching layer for sanction lookups (performance optimization)
- **Impact**: When ON, reduces DB queries by caching sanction states. When OFF, all queries hit DB.
- **Rollback**: Set to `false` if cache issues occur (invalidation storms, Redis outage)

**Usage**:
```bash
export MODERATION_CACHE_ENABLED=true
```

---

### MODERATION_CACHE_TTL_SECONDS
- **Default**: `60` (1 minute)
- **Type**: Integer (seconds)
- **Purpose**: Time-to-live for cached sanction entries
- **Impact**: Higher TTL = fewer DB queries but stale data risk. Lower TTL = fresher data but more DB load.
- **Tuning**: Increase to 300 (5 min) for high traffic, decrease to 30 for real-time requirements.

**Usage**:
```bash
export MODERATION_CACHE_TTL_SECONDS=60
```

---

### MODERATION_SAMPLING_RATE
- **Default**: `0.10` (10%)
- **Type**: Float (0.0 to 1.0)
- **Purpose**: Percentage of gate decisions to sample for metrics
- **Impact**: Lower rate = less metrics volume, higher rate = more visibility (100% during incidents)
- **Rollback**: N/A (sampling is non-invasive, adjust as needed)

**Usage**:
```bash
export MODERATION_SAMPLING_RATE=0.10
```

---

## Purchase & Economy (Future)

### PURCHASE_ENFORCEMENT_ENABLED
- **Default**: `false` (OFF)
- **Type**: Boolean
- **Purpose**: Block purchases for banned/suspended users
- **Impact**: When OFF (default), no purchase blocking. When ON, enforcement at checkout.
- **Rollback**: Set to `false` immediately if false positives occur

**Status**: Not yet implemented (Phase 10)

---

## Leaderboards (Phase E)

### LEADERBOARDS_COMPUTE_ENABLED
- **Default**: `false` (OFF)
- **Type**: Boolean
- **Purpose**: Enable leaderboard computation (Celery tasks, service layer)
- **Impact**: When OFF (default), all queries return empty DTOs with metadata. When ON, Celery tasks compute leaderboards.
- **Rollback**: Set to `false` to disable computation and return empty results

**Usage**:
```bash
# Enable computation
export LEADERBOARDS_COMPUTE_ENABLED=true

# Rollback (disable computation)
export LEADERBOARDS_COMPUTE_ENABLED=false
sudo systemctl restart deltacrown
```

**Effects**:
- OFF: `get_tournament_leaderboard()` returns empty list with `"computation_enabled": false`
- ON: Celery tasks populate `LeaderboardEntry` table, queries return data

---

### LEADERBOARDS_CACHE_ENABLED
- **Default**: `false` (OFF)
- **Type**: Boolean
- **Purpose**: Enable Redis caching for leaderboard reads
- **Impact**: When OFF, all queries hit DB. When ON, Redis cache with TTL (5min/1h/24h).
- **Rollback**: Set to `false` if cache issues occur (invalidation storms, stale data)

**Usage**:
```bash
# Enable caching
export LEADERBOARDS_CACHE_ENABLED=true

# Rollback (disable caching)
export LEADERBOARDS_CACHE_ENABLED=false
sudo systemctl restart deltacrown
```

**TTL Strategy**:
- Tournament: 5 minutes (real-time updates)
- Season: 1 hour (stable rankings)
- All-time: 24 hours (infrequent changes)

**Cache Invalidation**:
```python
from apps.leaderboards.services import invalidate_tournament_cache
invalidate_tournament_cache(tournament_id=501)  # Clear cache after match completion
```

---

### LEADERBOARDS_API_ENABLED
- **Default**: `false` (OFF)
- **Type**: Boolean
- **Purpose**: Enable public API endpoints (`/api/tournaments/leaderboards/...`)
- **Impact**: When OFF, API returns 404 (feature disabled). When ON, endpoints are accessible.
- **Rollback**: Set to `false` to immediately disable API access

**Usage**:
```bash
# Enable API
export LEADERBOARDS_API_ENABLED=true

# Rollback (disable API)
export LEADERBOARDS_API_ENABLED=false
sudo systemctl restart deltacrown
```

**Endpoints**:
- `GET /api/tournaments/leaderboards/tournament/{id}/` (tournament leaderboard)
- `GET /api/tournaments/leaderboards/player/{id}/history/` (player history)
- `GET /api/tournaments/leaderboards/{scope}/` (season/all-time)

**Requires**: `LEADERBOARDS_COMPUTE_ENABLED=true` for non-empty responses

**Rollout Example**:
```bash
# Step 1: Enable computation only (API disabled, Celery populates data)
export LEADERBOARDS_COMPUTE_ENABLED=true
export LEADERBOARDS_API_ENABLED=false

# Step 2: Enable caching (after data populated)
export LEADERBOARDS_CACHE_ENABLED=true

# Step 3: Enable API (after cache warmed)
export LEADERBOARDS_API_ENABLED=true
```

**One-Line Rollback** (emergency):
```bash
export LEADERBOARDS_API_ENABLED=false LEADERBOARDS_CACHE_ENABLED=false LEADERBOARDS_COMPUTE_ENABLED=false; sudo systemctl restart deltacrown
```

---

## General Rollback Procedure

For any flag causing issues:

1. **Immediate**: Set flag to safe default (usually `false` or previous value)
2. **Restart**: Application restart required for most flags (Django settings cached)
3. **Verify**: Check logs and metrics for expected behavior
4. **Document**: Add incident to `Documents/ExecutionPlan/SECURITY_HARDENING_STATUS.md`

**Example**:
```bash
# Rollback observability flag
export MODERATION_OBSERVABILITY_ENABLED=false
sudo systemctl restart deltacrown

# Verify metrics stopped
curl http://localhost:8000/metrics | grep moderation_  # Should return nothing
```

---

## Testing Flags Locally

```bash
# Run tests with flags enabled
MODERATION_OBSERVABILITY_ENABLED=true MODERATION_CACHE_ENABLED=true pytest -v tests/observability/

# Run tests with flags disabled
MODERATION_OBSERVABILITY_ENABLED=false MODERATION_CACHE_ENABLED=false pytest -v tests/observability/
```

---

## Monitoring Flag State

### Prometheus Metric (future)
```
deltacrown_feature_flags{flag_name="MODERATION_OBSERVABILITY_ENABLED", state="true|false"}
```

### Django Admin Check
Navigate to: `/admin/settings/feature-flags/` (if Feature Flag UI implemented)

---

## Drill Toggles (Phase 10)

**All drill tests are test-only** (no production behavior change).

Drills simulate failure scenarios in test environments:
- Redis outage (test fallback logic)
- DB read-only mode (test fast-fail paths)
- S3 unavailable (test local fallback)
- Rate limit burst (test throttling at 200 rps)

**No production flags**: Drills are executed via `pytest -m ops tests/ops/` only.

**Related**: See `tests/ops/test_dr_chaos_minidrill.py` for drill implementation.

---

## Related Documentation
- [MODULE_8.3_OBSERVABILITY_NOTES.md](../MODULE_8.3_OBSERVABILITY_NOTES.md) - Detailed observability guide
- [PHASE_9_SMOKE_AND_ALERTING.md](../PHASE_9_SMOKE_AND_ALERTING.md) - Smoke tests and alerting
- [RUNBOOKS/ONCALL_HANDOFF.md](../RUNBOOKS/ONCALL_HANDOFF.md) - On-call runbook (uses drill scenarios)
- [Documents/ExecutionPlan/Core/00_MASTER_EXECUTION_PLAN.md](../Documents/ExecutionPlan/Core/00_MASTER_EXECUTION_PLAN.md) - Phase roadmap
