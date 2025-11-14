# Moderation System Runbooks

**Phase 8.3 - Enforcement, Observability, and Cache Operations**

---

## Table of Contents

1. [Feature Flag Rollout/Rollback](#feature-flag-rolloutrollback)
2. [False-Positive Sanction Triage](#false-positive-sanction-triage)
3. [Cache Invalidation & Warming](#cache-invalidation--warming)
4. [Observability Sampling Tuning](#observability-sampling-tuning)

---

## Feature Flag Rollout/Rollback

### Flag Matrix

| Flag | Default | Purpose | Dependencies |
|------|---------|---------|--------------|
| `MODERATION_ENFORCEMENT_ENABLED` | `False` | Master switch for all enforcement | None (master) |
| `MODERATION_ENFORCEMENT_WS` | `False` | WebSocket CONNECT gates | Requires master=True |
| `MODERATION_ENFORCEMENT_PURCHASE` | `False` | Economy purchase gates | Requires master=True |
| `MODERATION_POLICY_CACHE_ENABLED` | `False` | Policy read-through cache (TTL=60s) | None (independent) |
| `MODERATION_OBSERVABILITY_ENABLED` | `False` | Event emission (test-only) | None (test-only) |
| `MODERATION_OBSERVABILITY_SAMPLE_RATE` | `0.0` | Sampling rate (0.0-1.0) | Requires observability=True |

### Safe Canary Rollout Steps

**Phase 1: Enable enforcement (no gates)**
1. Set `MODERATION_ENFORCEMENT_ENABLED=True` in canary environment
2. Verify no errors in logs (enforcement checks running, but gates disabled)
3. Monitor metrics: `moderation.enforcement.check_count`, `moderation.enforcement.latency_p95`
4. **Acceptance:** Zero increase in error rate, p95 latency < 50ms

**Phase 2: Enable WebSocket gate (staged)**
1. Set `MODERATION_ENFORCEMENT_WS=True` in canary (5% traffic)
2. Monitor:
   - `moderation.ws_gate.blocked_count` (should see active bans blocking)
   - `moderation.ws_gate.false_positive_rate` (target: <0.1%)
   - User complaints/support tickets
3. Wait 24 hours, verify no false-positive spikes
4. Roll out to 25% → 50% → 100% with 24h intervals
5. **Acceptance:** False-positive rate < 0.1%, no rollback triggers

**Phase 3: Enable Economy gate (staged)**
1. Set `MODERATION_ENFORCEMENT_PURCHASE=True` in canary (5% traffic)
2. Monitor:
   - `moderation.purchase_gate.blocked_count`
   - `moderation.purchase_gate.false_positive_rate`
   - Revenue metrics (ensure no unexpected drops)
3. Roll out to 25% → 50% → 100% with 24h intervals
4. **Acceptance:** False-positive rate < 0.1%, revenue unchanged

### Instant Rollback Procedure

**Trigger Criteria:**
- False-positive rate > 1.0% (10x normal)
- User complaints > 5 in 1 hour
- p95 latency > 100ms (2x SLO)
- Unhandled exceptions in enforcement code

**Rollback Steps:**
1. **Immediate:** Set all flags to `False` in `.env`:
   ```bash
   MODERATION_ENFORCEMENT_ENABLED=False
   MODERATION_ENFORCEMENT_WS=False
   MODERATION_ENFORCEMENT_PURCHASE=False
   ```
2. Restart application (no code deploy required)
3. Verify: All users can connect/purchase (gates return `allowed=True`)
4. Post-mortem: Review logs, identify false-positive root cause
5. Fix in staging, re-test, then retry rollout

**Rollback Verification:**
```bash
# Check enforcement status
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.deltacrown.com/admin/moderation/status

# Expected: "enforcement_enabled": false
```

---

## False-Positive Sanction Triage

### Symptoms
- User reports "I can't connect to the tournament"
- User reports "I can't buy coins even though I have balance"
- Support ticket with `reason_code: BAN/MUTE/SUSPEND`

### Triage Flow

**Step 1: Verify Sanction Exists**
```bash
# Admin panel: Moderation → Sanctions
# Search by user ID or username
# Check: Is there an active sanction?
```

**Step 2: Validate Sanction Legitimacy**
- **Review reason:** Does it match user behavior?
- **Check evidence:** Are there attached reports, screenshots, logs?
- **Verify moderator:** Was it issued by a trusted moderator?
- **Scope check:** Is it global or tournament-specific?

**Step 3: Decision Matrix**

| Scenario | Action | Timeline |
|----------|--------|----------|
| **Legitimate sanction, user appealing** | Escalate to senior moderator for review | 24-48h |
| **False positive (moderator error)** | Immediate revocation + apology | <15 min |
| **False positive (system bug)** | Revoke + file bug report + rollback flag | <15 min |
| **Expired but still cached** | Manual cache invalidation | <5 min |
| **User lying/confused** | Explain sanction, provide appeal process | Immediate |

**Step 4: Revocation (if false positive)**
```python
# Django admin shell or API
from apps.moderation.services import sanctions_service

sanctions_service.revoke_sanction(
    sanction_id=<SANCTION_ID>,
    revoked_by_id=<YOUR_MODERATOR_ID>,
    notes={
        'reason': 'false_positive',
        'explanation': 'Moderator error / system bug / expired but cached',
        'ticket_id': 'SUP-12345'
    }
)
```

**Step 5: Cache Invalidation (if needed)**
```python
# If revocation doesn't immediately take effect (cache lag)
from apps.moderation import cache as mod_cache

mod_cache.invalidate_user_sanctions(user_id=<USER_ID>)
# User can now reconnect/purchase immediately
```

**Step 6: Post-Incident**
- Log false-positive in incident tracker
- If system bug: file GitHub issue, assign to eng team
- If moderator error: additional training/review of mod actions
- If false-positive rate spikes: consider rollback (see above)

---

## Cache Invalidation & Warming

### When to Invalidate

**Automatic Invalidation (handled by code):**
- On `create_sanction()` → invalidates user's cache
- On `revoke_sanction()` → invalidates user's cache

**Manual Invalidation (operator action):**
- False-positive sanction revoked but cache not clearing
- Bulk sanction updates (e.g., mass-revoke after incident)
- Cache corruption suspected (stale data persisting beyond TTL)

### Manual Invalidation Procedure

**Single User:**
```python
from apps.moderation import cache as mod_cache

# Invalidate all caches for user
mod_cache.invalidate_user_sanctions(user_id=12345)
```

**Tournament-Scoped:**
```python
# Invalidate tournament-specific + global caches
mod_cache.invalidate_tournament_sanctions(user_id=12345, tournament_id=67890)
```

**Pattern-Based (Redis only):**
```python
# Clear all caches for multiple users (use with caution)
from django.core.cache import cache

# If Redis backend supports pattern deletion
if hasattr(cache, 'delete_pattern'):
    deleted = cache.delete_pattern("moderation:user:*:sanctions")
    print(f"Cleared {deleted} cache entries")
```

### Cache Warming Procedure

**Use Case:** Pre-warm cache for high-traffic event (tournament finals, etc.)

```python
from apps.moderation.services import sanctions_service
from apps.moderation import cache as mod_cache

# Fetch participants for tournament
participants = TournamentRegistration.objects.filter(
    tournament_id=12345
).values_list('user_profile_id', flat=True)

# Warm cache for each participant
for user_id in participants:
    policies = sanctions_service.effective_policies(user_id)
    mod_cache.warm_cache_for_user(user_id, policies)

print(f"Warmed cache for {len(participants)} participants")
```

### Cache Monitoring

**Metrics to Track:**
- `moderation.cache.hit_rate` (target: >80% after warm-up)
- `moderation.cache.miss_count` (high misses = cold cache or TTL too short)
- `moderation.cache.invalidation_count` (high = frequent sanction changes)

**Cache Stats (Redis):**
```python
from apps.moderation import cache as mod_cache

stats = mod_cache.get_cache_stats()
print(f"Cache enabled: {stats['enabled']}")
print(f"Backend: {stats['backend']}")
print(f"Hits: {stats.get('hits', 'N/A')}")
print(f"Misses: {stats.get('misses', 'N/A')}")
```

---

## Observability Sampling Tuning

### Sampling Rate Guidelines

| Environment | Recommended Rate | Rationale |
|-------------|------------------|-----------|
| **Development** | `1.0` (100%) | Full visibility for debugging |
| **Staging** | `0.5` (50%) | Representative sample, low overhead |
| **Production (normal)** | `0.01` (1%) | Minimal overhead, sufficient for monitoring |
| **Production (incident)** | `0.25` (25%) | Higher fidelity during troubleshooting |
| **Load testing** | `0.0` (0%) | Zero overhead for pure perf testing |

### Tuning Procedure

**Step 1: Set Sampling Rate**
```bash
# .env or environment variables
MODERATION_OBSERVABILITY_ENABLED=True
MODERATION_OBSERVABILITY_SAMPLE_RATE=0.01  # 1% sampling
```

**Step 2: Restart Application**
```bash
# No code deploy needed, just restart
systemctl restart deltacrown-web
```

**Step 3: Verify Sampling in Logs**
```bash
# Check logs for event emission
tail -f /var/log/deltacrown/app.log | grep "Moderation event"

# Should see ~1% of enforcement checks logged
```

**Step 4: Adjust Based on Telemetry**
- **If overhead too high (CPU/memory spike):** Decrease rate (e.g., 0.01 → 0.001)
- **If insufficient data for debugging:** Increase rate temporarily (e.g., 0.01 → 0.25)
- **If incident resolved:** Return to baseline (0.01 or disable)

### Sampling Statistical Validation

**Test Sampling Accuracy:**
```python
# Run in Django shell or test environment
from apps.moderation.observability import emit_gate_check, get_emitter

get_emitter().clear()

# Emit 1000 events
for i in range(1000):
    emit_gate_check('websocket', i, True, None, None, 10.0)

# Check actual rate
events = get_emitter().get_events()
actual_rate = len(events) / 1000

# Expected: within ±10% tolerance
# e.g., rate=0.25 → 225-275 events
print(f"Expected: 0.25, Actual: {actual_rate:.3f}")
```

### PII Guard Verification

**Ensure Zero PII in Events:**
```python
# Check emitted events for PII leakage
from apps.moderation.observability import get_emitter

events = get_emitter().get_events()

for event in events:
    payload_str = str(event['payload']).lower()
    
    # Assert NO PII fields
    assert 'username' not in payload_str
    assert 'email' not in payload_str
    assert 'ip' not in payload_str
    
    print(f"✅ Event {event['event']} is PII-safe")
```

---

## Emergency Contacts

| Role | Contact | Responsibility |
|------|---------|----------------|
| **On-Call Engineer** | +880-XXX-XXXX | Immediate rollback, cache invalidation |
| **Lead Moderator** | moderator@deltacrown.com | False-positive triage, mass revocations |
| **Platform Architect** | arch@deltacrown.com | System design questions, SLO violations |
| **Support Team** | support@deltacrown.com | User complaints, ticket escalation |

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-01-12 | 1.0 | Phase 8.3 Team | Initial runbooks (flags, false-positives, cache, sampling) |

---

**End of Runbooks**
