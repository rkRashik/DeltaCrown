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

## Related Documentation
- [MODULE_8.3_OBSERVABILITY_NOTES.md](../MODULE_8.3_OBSERVABILITY_NOTES.md) - Detailed observability guide
- [PHASE_9_SMOKE_AND_ALERTING.md](../PHASE_9_SMOKE_AND_ALERTING.md) - Smoke tests and alerting
- [Documents/ExecutionPlan/00_MASTER_EXECUTION_PLAN.md](../Documents/ExecutionPlan/00_MASTER_EXECUTION_PLAN.md) - Phase roadmap
