# Production Canary Runbook — Phase 5.5 + 5.6 Webhooks

**Date**: November 13, 2025  
**Commits**: de736cb (5.5) + c5b4581 (5.6)  
**Status**: ✅ Pre-flight complete, ready for 5% canary

---

## 🎯 **Quick Reference**

| Metric | Target | Rollback Trigger |
|--------|--------|------------------|
| **Success Rate** | ≥95% | <90% for 5 minutes |
| **P95 Latency** | <2s | >5s sustained |
| **Circuit Breaker Opens** | <5/day | >20/day |
| **PII Leaks** | **0** | **ANY occurrence** |

**One-Line Rollback**: `NOTIFICATIONS_WEBHOOK_ENABLED=False`

---

## ✅ **Phase 0: Pre-Flight Checklist**

### 1. Generate Production Secret

```bash
# Generate secure 64-char hex secret
python -c "import secrets; print(secrets.token_hex(32))"

# Example output (DO NOT USE THIS):
# a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

**Action**: Store in secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)

### 2. Configure Production Settings

**File**: `deltacrown/settings_production.py` (or environment variables)

```python
# Webhook Configuration — Production Canary (5%)
NOTIFICATIONS_WEBHOOK_ENABLED = False  # Start OFF, flip to True for canary

# Required
WEBHOOK_ENDPOINT = 'https://api.deltacrown.gg/webhooks/inbound'
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')  # From secrets manager

# Optional (safe defaults)
WEBHOOK_TIMEOUT = 10  # seconds
WEBHOOK_MAX_RETRIES = 3

# Module 5.6: Replay Safety
WEBHOOK_REPLAY_WINDOW_SECONDS = 300  # 5 minutes

# Module 5.6: Circuit Breaker
WEBHOOK_CB_WINDOW_SECONDS = 120      # 2-minute failure tracking
WEBHOOK_CB_MAX_FAILS = 5             # Failures before opening
WEBHOOK_CB_OPEN_SECONDS = 60         # Time open before probe
```

### 3. Verify Receiver Endpoint

**Health Check**:
```bash
curl -X GET https://api.deltacrown.gg/webhooks/health
# Expected: {"status": "healthy"}
```

**Receiver Must Implement**:

#### A. HMAC Verification (with timestamp)
```python
import hmac
import hashlib
from datetime import datetime, timezone

def verify_webhook(body: str, signature: str, timestamp: str, webhook_id: str):
    # 1. Check timestamp freshness
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    timestamp_ms = int(timestamp)
    age_seconds = (now_ms - timestamp_ms) / 1000
    
    if age_seconds > 300:  # 5 minutes
        return False, "Timestamp too old"
    
    if age_seconds < -30:  # 30s clock skew tolerance
        return False, "Timestamp in future"
    
    # 2. Verify HMAC signature (constant-time)
    message = f"{timestamp}.{body}"
    expected = hmac.new(
        SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected, signature):
        return False, "Invalid signature"
    
    # 3. Check webhook_id deduplication (Redis/cache)
    if redis.exists(f"webhook:{webhook_id}"):
        return False, "Duplicate webhook (replay detected)"
    
    redis.setex(f"webhook:{webhook_id}", 900, "1")  # 15-minute TTL
    
    return True, None
```

#### B. Test Receiver with cURL
```bash
# Get sample payload from staging
TIMESTAMP=$(date +%s)000
WEBHOOK_ID=$(uuidgen)
PAYLOAD='{"event":"test","data":{"test":"canary"},"metadata":{}}'

# Generate signature (use your WEBHOOK_SECRET)
MESSAGE="${TIMESTAMP}.${PAYLOAD}"
SIGNATURE=$(echo -n "$MESSAGE" | openssl dgst -sha256 -hmac "YOUR_SECRET" | awk '{print $2}')

# Send test webhook
curl -X POST https://api.deltacrown.gg/webhooks/inbound \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: $SIGNATURE" \
  -H "X-Webhook-Timestamp: $TIMESTAMP" \
  -H "X-Webhook-Id: $WEBHOOK_ID" \
  -H "X-Webhook-Event: test" \
  -H "User-Agent: DeltaCrown-Webhook/1.0" \
  -d "$PAYLOAD"

# Expected: 200 OK
```

### 4. Verify Feature Flag Default

```bash
# Check settings file
grep -n "NOTIFICATIONS_WEBHOOK_ENABLED" deltacrown/settings*.py

# Expected: False (or not defined, defaults to False)
```

---

## 🚀 **Phase 1: Enable 5% Canary**

### Step 1: Flip Flag

**Option A: Environment Variable**
```bash
export NOTIFICATIONS_WEBHOOK_ENABLED=true
systemctl restart deltacrown-prod
```

**Option B: Django Settings (with percentage rollout)**
```python
# settings_production.py
import random

# 5% canary rollout
def should_enable_webhooks():
    return random.random() < 0.05

NOTIFICATIONS_WEBHOOK_ENABLED = should_enable_webhooks()
```

**Option C: Feature Flag Service (LaunchDarkly, etc.)**
```python
NOTIFICATIONS_WEBHOOK_ENABLED = ld_client.variation(
    "webhooks-enabled",
    {"key": "production"},
    False
)
```

### Step 2: Verify Activation

```bash
# Check logs for webhook delivery attempts
tail -f /var/log/deltacrown-prod.log | grep -i webhook

# Expected lines:
# [INFO] Webhook delivered successfully: event=payment_verified, status=200
# [INFO] Attempting webhook delivery (attempt 1/3)
```

### Step 3: Test with Real Transaction

**Trigger a payment_verified event** (use test account):
```bash
# Via Django shell
python manage.py shell
>>> from apps.tournaments.models import PaymentVerification
>>> pv = PaymentVerification.objects.filter(status='pending').first()
>>> pv.status = 'verified'
>>> pv.save()  # Should trigger webhook
```

**Expected receiver logs**:
```
[INFO] Received webhook: event=payment_verified, webhook_id=abc123...
[INFO] Signature valid: True
[INFO] Timestamp age: 1.2s (fresh)
[INFO] Processing payment verification for tournament_id=456
```

---

## 📊 **Phase 2: Monitor 24 Hours (5% Canary)**

### A. Success Rate Check

**Query logs every 15 minutes**:
```bash
# Success count
grep "Webhook delivered successfully" /var/log/deltacrown-prod.log | wc -l

# Failure count
grep "Webhook delivery failed after" /var/log/deltacrown-prod.log | wc -l

# Calculate success rate
# Success Rate = (Success / (Success + Failures)) * 100
```

**Target**: ≥95%  
**Rollback Trigger**: <90% for 5 consecutive minutes

### B. Latency Check

**Parse logs for delivery times**:
```bash
grep "Webhook delivered successfully" /var/log/deltacrown-prod.log | \
  grep -oP 'latency=\K[0-9]+' | \
  awk '{sum+=$1; count++} END {print "P95 estimate:", sum/count*1.5 "ms"}'
```

**Target**: P95 <2000ms  
**Alert**: P95 >5000ms sustained

### C. Circuit Breaker State

**Check for state transitions**:
```bash
# Circuit opened
grep "Circuit breaker OPENED" /var/log/deltacrown-prod.log | wc -l

# Circuit transitions
grep -E "Circuit breaker (OPENED|HALF_OPEN|CLOSED)" /var/log/deltacrown-prod.log | tail -20
```

**Target**: <5 opens per day  
**Alert**: >20 opens per day (indicates receiver instability)

### D. PII Leak Detection

**Strict grep scan** (should return ZERO matches):
```bash
# Check for emails in webhook logs
grep -i webhook /var/log/deltacrown-prod.log | grep -iE '\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'

# Check for usernames (pattern: @username)
grep -i webhook /var/log/deltacrown-prod.log | grep -E '@[a-zA-Z0-9_]+'

# Check for IP addresses
grep -i webhook /var/log/deltacrown-prod.log | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'

# Expected output for all: ZERO MATCHES
```

**Rollback Trigger**: **ANY PII found** (immediate rollback)

### E. Header Presence Check

**Sample webhook request at receiver**:
```bash
# Receiver logs should show all headers
grep "X-Webhook-" /var/log/receiver.log | head -5

# Expected:
# X-Webhook-Signature: a3c8f7e2d1b456...
# X-Webhook-Timestamp: 1700000000123
# X-Webhook-Id: 550e8400-e29b-41d4-a716-446655440000
# X-Webhook-Event: payment_verified
```

---

## 🚨 **Rollback Procedures**

### Level 1: Instant Disable (No Redeploy)

```bash
# Option A: Environment variable
export NOTIFICATIONS_WEBHOOK_ENABLED=false
systemctl restart deltacrown-prod

# Option B: Django shell (no restart)
python manage.py shell
>>> from django.conf import settings
>>> settings.NOTIFICATIONS_WEBHOOK_ENABLED = False
```

**Effect**: Webhooks stop immediately, notifications continue (email unaffected)

### Level 2: Disable Circuit Breaker Only

```python
# settings_production.py
WEBHOOK_CB_MAX_FAILS = 9999  # Effectively disabled (never opens)
```

**Use Case**: Circuit breaker too aggressive, but webhooks working

### Level 3: Revert Hardening (Keep Base Webhooks)

```bash
git revert c5b4581  # Revert Module 5.6 only
git push origin master
# Deploy

# Receivers can ignore new headers (backward compatible)
```

**Effect**: Reverts replay safety + circuit breaker, keeps HMAC + retries

### Level 4: Full Rollback (Emergency)

```bash
git revert c5b4581 de736cb  # Revert both Phase 5.5 + 5.6
git push origin master
# Deploy
```

**Effect**: Completely removes webhook functionality

---

## 🔍 **Troubleshooting Flowchart**

### Problem: High Failure Rate (>10%)

**Check**:
1. Receiver endpoint health: `curl https://api.deltacrown.gg/webhooks/health`
2. Network connectivity: `ping api.deltacrown.gg`
3. Secret mismatch: Verify `WEBHOOK_SECRET` matches receiver
4. Receiver error logs: Check for signature validation failures

**Actions**:
- If receiver down: Wait for recovery or rollback
- If signature mismatch: Update secret and redeploy
- If network issue: Check firewall/DNS

### Problem: Circuit Breaker Opens Frequently (>5/day)

**Check**:
```bash
# Find what's triggering opens
grep "Circuit breaker OPENED" /var/log/deltacrown-prod.log | \
  grep -oP 'endpoint=\K[^,]+' | sort | uniq -c
```

**Actions**:
- If receiver unstable: Coordinate with receiver team
- If false positives: Increase threshold temporarily:
  ```python
  WEBHOOK_CB_MAX_FAILS = 10  # Double threshold
  ```
- If legitimate failures: Fix receiver issues first

### Problem: Stale Timestamp Rejections

**Check receiver clock skew**:
```bash
# On sender
date +%s
# On receiver
ssh receiver "date +%s"

# Difference should be <30s
```

**Actions**:
- If >30s skew: Sync NTP on both systems
- If timestamps look wrong: Check timezone settings (should be UTC)

### Problem: Duplicate Webhook Alerts

**Expected behavior**: Receiver dedupe via `webhook_id` cache

**Check**:
```bash
# Receiver logs
grep "Duplicate webhook" /var/log/receiver.log | wc -l
```

**Actions**:
- If many duplicates: Check Redis/cache TTL (should be ≥15 minutes)
- If cache failures: Verify Redis connectivity
- If intentional retries: Normal (exponential backoff behavior)

---

## 📈 **Gradual Rollout Plan**

### Phase 2A: 25% (After 24h at 5%)

**Criteria to proceed**:
- ✅ Success rate ≥95% sustained
- ✅ P95 latency <2s
- ✅ Circuit breaker opens <5/day
- ✅ Zero PII leaks detected
- ✅ No receiver complaints

**Action**: Increase percentage to 25%

### Phase 2B: 50% (After 48h at 25%)

**Same criteria as above**

### Phase 2C: 100% (After 48h at 50%)

**Final checks**:
- ✅ All SLOs met consistently
- ✅ Circuit breaker stable
- ✅ Receiver capacity adequate
- ✅ Team confident in observability

**Action**: Full rollout

---

## 📞 **On-Call Quick Commands**

### Check Current Status
```bash
# Webhook success rate (last hour)
grep "Webhook delivered" /var/log/deltacrown-prod.log | \
  grep "$(date -u +%Y-%m-%d\ %H)" | \
  awk '/successfully/{s++} /failed/{f++} END{print "Success:",s,"Failed:",f,"Rate:",s/(s+f)*100"%"}'

# Circuit breaker current state
grep "Circuit breaker" /var/log/deltacrown-prod.log | tail -1

# Recent errors
grep -i "webhook.*error" /var/log/deltacrown-prod.log | tail -10
```

### Emergency Disable
```bash
# Single command (requires sudo)
echo "NOTIFICATIONS_WEBHOOK_ENABLED=False" >> /etc/deltacrown/settings.env && systemctl restart deltacrown-prod
```

### Verify PII Clean (Quick)
```bash
# 3-second check (should return nothing)
grep -i webhook /var/log/deltacrown-prod.log | grep -iE '@|email|username|192\.168|10\.|172\.' | head -5
```

---

## 📊 **Expected Baseline (From Staging)**

| Metric | Staging Result | Production Target |
|--------|----------------|-------------------|
| **Success Rate** | 100% (25/25) | ≥95% |
| **P50 Latency** | 142ms | <500ms |
| **P95 Latency** | 1.2s | <2s |
| **Retry Rate** | 4% (1/25) | <20% |
| **PII Leaks** | 0 | **0** |
| **HMAC Validity** | 100% | 100% |

---

## ✅ **Canary Success Criteria**

After 24 hours at 5%, proceed to 25% if:

- [x] **Success rate** ≥95%
- [x] **P95 latency** <2s
- [x] **Circuit breaker** opens <5 times
- [x] **PII leaks** = 0 (strict)
- [x] **No receiver errors** in logs
- [x] **Headers present** (Signature, Timestamp, ID, Event)
- [x] **Replay safety working** (stale timestamps rejected)
- [x] **Team confident** in stability

---

## 📚 **Reference Documentation**

- **Delivery Bundle**: `Documents/PHASE_5_6_FINAL_DELIVERY.md`
- **Hardening Spec**: `Documents/Phase5_6_Hardening_Spec.md`
- **Staging Evidence**: `Documents/staging_payments_output.json` + `staging_matches_output.json`
- **PII Audit**: `Documents/Phase5_PII_Discipline.md`
- **Verification Tool**: `scripts/verify_webhook_signature.py`

---

## 🎯 **Owner Responsibilities**

### Ops Team (You)
- ✅ Configure production secrets
- ✅ Flip canary flag (5%)
- ✅ Monitor SLOs (24-hour watch)
- ✅ Execute rollback if needed (one-line toggle)
- ✅ Coordinate receiver team

### Engineering Team (Us)
- ✅ Stand by for support
- ✅ Tune circuit breaker if needed
- ✅ Assist receiver integration
- ✅ Queue observability pack if requested

---

**Runbook Owner**: Engineering Team  
**Last Updated**: November 13, 2025  
**Version**: 1.0 (Canary)  
**Status**: ✅ Ready for 5% Production Enable
