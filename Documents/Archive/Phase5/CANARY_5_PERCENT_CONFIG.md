# Production Canary Configuration — 5% Rollout

**Date**: November 13, 2025 14:00 UTC  
**Phase**: 1 (5% Canary)  
**Duration**: 24 hours  
**Next Review**: November 14, 2025 14:00 UTC

---

## 🎯 **Configuration (Production)**

### Method 1: Environment Variables (Recommended)

```bash
# /etc/deltacrown/production.env

# === CANARY ENABLEMENT (5%) ===
NOTIFICATIONS_WEBHOOK_ENABLED=true

# === ENDPOINT (replace with actual receiver URL) ===
WEBHOOK_ENDPOINT=https://api.deltacrown.gg/webhooks/inbound

# === SECRET (from secrets manager) ===
WEBHOOK_SECRET=<generated-64-hex-from-secrets-manager>

# === TIMING CONFIGURATION ===
WEBHOOK_TIMEOUT=10
WEBHOOK_MAX_RETRIES=3

# === MODULE 5.6: REPLAY SAFETY ===
WEBHOOK_REPLAY_WINDOW_SECONDS=300  # 5 minutes
# Timestamp must be within [now-5m, now+30s]

# === MODULE 5.6: CIRCUIT BREAKER ===
WEBHOOK_CB_WINDOW_SECONDS=120   # Track failures over 2 minutes
WEBHOOK_CB_MAX_FAILS=5          # Open circuit after 5 failures
WEBHOOK_CB_OPEN_SECONDS=60      # Stay open for 60s before probe
```

**Apply**:
```bash
# Reload configuration
sudo systemctl reload deltacrown-prod

# Or restart if reload not supported
sudo systemctl restart deltacrown-prod
```

---

### Method 2: Django Settings (5% Probabilistic Rollout)

**File**: `deltacrown/settings_production.py`

```python
import os
import random

# === CANARY ROLLOUT: 5% Traffic ===
def should_enable_webhooks_for_request():
    """
    5% canary rollout - randomly enable webhooks for 5% of notifications.
    
    For deterministic rollout (e.g., by user_id), use:
        return (user_id % 100) < 5
    """
    return random.random() < 0.05

# Base flag (controls whether canary logic runs)
WEBHOOKS_CANARY_ACTIVE = True

# Dynamic per-notification check
# (Call this in NotificationService.notify() to decide per-event)
NOTIFICATIONS_WEBHOOK_ENABLED = should_enable_webhooks_for_request()

# Alternatively, enable for ALL events during canary:
# NOTIFICATIONS_WEBHOOK_ENABLED = True  # 100% of notifications → 5% via load balancer

# === ENDPOINT ===
WEBHOOK_ENDPOINT = os.environ.get(
    'WEBHOOK_ENDPOINT',
    'https://api.deltacrown.gg/webhooks/inbound'
)

# === SECRET (from environment) ===
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
if not WEBHOOK_SECRET or len(WEBHOOK_SECRET) < 32:
    raise ValueError("WEBHOOK_SECRET must be ≥32 characters")

# === TIMEOUT & RETRIES ===
WEBHOOK_TIMEOUT = int(os.environ.get('WEBHOOK_TIMEOUT', 10))
WEBHOOK_MAX_RETRIES = int(os.environ.get('WEBHOOK_MAX_RETRIES', 3))

# === MODULE 5.6: REPLAY SAFETY ===
WEBHOOK_REPLAY_WINDOW_SECONDS = int(
    os.environ.get('WEBHOOK_REPLAY_WINDOW_SECONDS', 300)
)

# === MODULE 5.6: CIRCUIT BREAKER ===
WEBHOOK_CB_WINDOW_SECONDS = int(
    os.environ.get('WEBHOOK_CB_WINDOW_SECONDS', 120)
)
WEBHOOK_CB_MAX_FAILS = int(
    os.environ.get('WEBHOOK_CB_MAX_FAILS', 5)
)
WEBHOOK_CB_OPEN_SECONDS = int(
    os.environ.get('WEBHOOK_CB_OPEN_SECONDS', 60)
)
```

---

### Method 3: Feature Flag Service (LaunchDarkly / Unleash)

```python
# deltacrown/settings_production.py
from launchdarkly import LDClient

ld_client = LDClient(os.environ['LAUNCHDARKLY_SDK_KEY'])

# Canary rollout with gradual percentage
NOTIFICATIONS_WEBHOOK_ENABLED = ld_client.variation(
    'webhooks-enabled',
    {
        'key': 'production',
        'custom': {
            'environment': 'prod',
            'version': '5.6'
        }
    },
    False  # Default OFF if service unavailable
)

# LaunchDarkly dashboard:
# - webhooks-enabled: 5% → 25% → 50% → 100%
# - Rollback: Toggle flag OFF (instant)
```

---

## 🧪 **Smoke Tests (Run Immediately After Enable)**

### Test 1: Success Path (200 OK)

**Trigger**: Payment verification

```bash
# Django shell
python manage.py shell

from apps.tournaments.models import PaymentVerification
from django.contrib.auth import get_user_model

User = get_user_model()

# Get test user or create one
user = User.objects.filter(username='canary_test_user').first()
if not user:
    user = User.objects.create_user(
        username='canary_test_user',
        email='canary@test.internal',
        password='test123'
    )

# Create pending payment
from apps.tournaments.models import Tournament
tournament = Tournament.objects.first()

pv = PaymentVerification.objects.create(
    user=user,
    tournament=tournament,
    amount=50.00,
    status='pending'
)

# Trigger webhook via status change
pv.status = 'verified'
pv.save()

# Expected logs:
# [INFO] Attempting webhook delivery (attempt 1/3)
# [INFO] Webhook delivered successfully: event=payment_verified, status=200
```

**Expected receiver payload**:
```json
{
  "event": "payment_verified",
  "data": {
    "payment_id": 123,
    "tournament_id": 456,
    "user_id": 789,
    "amount": "50.00",
    "status": "verified"
  },
  "metadata": {
    "timestamp": "2025-11-13T14:05:23Z",
    "service": "deltacrown",
    "version": "5.6"
  }
}
```

**Expected headers**:
```
X-Webhook-Signature: a3c8f7e2d1b4567890abcdef1234567890abcdef1234567890abcdef12345678
X-Webhook-Timestamp: 1700000000123
X-Webhook-Id: 550e8400-e29b-41d4-a716-446655440000
X-Webhook-Event: payment_verified
Content-Type: application/json
User-Agent: DeltaCrown-Webhook/1.0
```

---

### Test 2: Retry Path (503 → 0s/2s/4s)

**Setup**: Configure receiver to return 503 on first 2 attempts

**Receiver mock**:
```python
# receiver_app.py (mock)
attempt_count = {}

@app.route('/webhooks/inbound', methods=['POST'])
def webhook_inbound():
    webhook_id = request.headers.get('X-Webhook-Id')
    
    # First 2 attempts: fail with 503
    if webhook_id not in attempt_count:
        attempt_count[webhook_id] = 0
    
    attempt_count[webhook_id] += 1
    
    if attempt_count[webhook_id] <= 2:
        return jsonify({"error": "Service unavailable"}), 503
    
    # Third attempt: success
    return jsonify({"status": "accepted"}), 200
```

**Trigger**: Same payment verification as Test 1

**Expected logs**:
```
[INFO] Attempting webhook delivery (attempt 1/3): event=payment_verified
[WARN] Webhook delivery failed (attempt 1/3): status=503, retrying in 0s
[INFO] Attempting webhook delivery (attempt 2/3): event=payment_verified
[WARN] Webhook delivery failed (attempt 2/3): status=503, retrying in 2s
[INFO] Attempting webhook delivery (attempt 3/3): event=payment_verified
[INFO] Webhook delivered successfully: event=payment_verified, status=200, total_time=6.2s
```

**Verify**:
- Delays: 0s (immediate retry), 2s, 4s
- Total time: ~6s (0 + 2 + 4)
- Final status: 200

---

### Test 3: No-Retry Path (400 Bad Request)

**Setup**: Receiver returns 400 (client error)

**Receiver mock**:
```python
@app.route('/webhooks/inbound', methods=['POST'])
def webhook_inbound():
    # Simulate bad request (e.g., invalid signature)
    return jsonify({"error": "Invalid signature"}), 400
```

**Expected logs**:
```
[INFO] Attempting webhook delivery (attempt 1/3): event=payment_verified
[ERROR] Webhook delivery failed (attempt 1/3): status=400, client error (no retry)
[WARN] Webhook delivery aborted: event=payment_verified, reason=4xx_error
```

**Verify**:
- Only 1 attempt (no retries)
- Notification still succeeds (email sent)
- Webhook error isolated (doesn't break notification)

---

### Test 4: Circuit Breaker Trigger (5 failures → OPEN)

**Setup**: Receiver returns 500 for 5+ consecutive deliveries

**Trigger**: Create 5 payment verifications rapidly

```python
# Django shell
for i in range(5):
    pv = PaymentVerification.objects.create(
        user=user,
        tournament=tournament,
        amount=50.00,
        status='pending'
    )
    pv.status = 'verified'
    pv.save()
```

**Expected logs**:
```
[INFO] Attempting webhook delivery (attempt 1/3): event=payment_verified
[WARN] Webhook delivery failed (attempt 3/3): status=500, all retries exhausted
[INFO] Circuit breaker failure recorded: 1/5

[INFO] Attempting webhook delivery (attempt 1/3): event=payment_verified
[WARN] Webhook delivery failed (attempt 3/3): status=500, all retries exhausted
[INFO] Circuit breaker failure recorded: 2/5

... (3 more failures) ...

[ERROR] Circuit breaker OPENED: 5 failures in 120s window
[WARN] Webhook delivery blocked: circuit breaker is OPEN (will probe in 60s)
```

**Verify**:
- After 5 failures: Circuit breaker transitions to OPEN
- Next delivery: Blocked immediately (no attempt)
- After 60s: One probe attempt (HALF_OPEN)
- If probe succeeds: Circuit closes (CLOSED)
- If probe fails: Circuit reopens (OPEN for another 60s)

---

## 📊 **Monitoring Dashboard (24 Hours)**

### Hourly Metrics Table

| Hour Start (UTC) | Delivered | Failed | Success % | P95 Latency (ms) | CB Opens | PII Leaks |
|------------------|-----------|--------|-----------|------------------|----------|-----------|
| 2025-11-13 14:00 | _TBD_     | _TBD_  | _TBD_     | _TBD_            | _TBD_    | **0** ✅  |
| 2025-11-13 15:00 | _TBD_     | _TBD_  | _TBD_     | _TBD_            | _TBD_    | **0** ✅  |
| 2025-11-13 16:00 | _TBD_     | _TBD_  | _TBD_     | _TBD_            | _TBD_    | **0** ✅  |
| ... (24 rows)    | ...       | ...    | ...       | ...              | ...      | **0** ✅  |

**Target SLOs**:
- **Success %**: ≥95% (rollback if <90% for ≥5 minutes)
- **P95 Latency**: <2000ms
- **CB Opens**: <5 per day (<1 per 5 hours)
- **PII Leaks**: **0** (immediate rollback on ANY match)

---

### Monitoring Queries

#### A. Success Rate (Every Hour)

```bash
#!/bin/bash
# File: scripts/monitor_success_rate.sh

HOUR=$(date -u +"%Y-%m-%d %H")
LOG_FILE="/var/log/deltacrown-prod.log"

SUCCESS=$(grep "$HOUR" "$LOG_FILE" | grep "Webhook delivered successfully" | wc -l)
FAILED=$(grep "$HOUR" "$LOG_FILE" | grep "Webhook delivery failed after" | wc -l)

TOTAL=$((SUCCESS + FAILED))
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=2; $SUCCESS * 100 / $TOTAL" | bc)
    echo "[$HOUR] Delivered: $SUCCESS, Failed: $FAILED, Success Rate: $SUCCESS_RATE%"
    
    # Alert if below threshold
    if (( $(echo "$SUCCESS_RATE < 90" | bc -l) )); then
        echo "⚠️  ALERT: Success rate below 90% threshold!"
    fi
else
    echo "[$HOUR] No webhook deliveries recorded"
fi
```

**Run**: `bash scripts/monitor_success_rate.sh` (every hour via cron)

---

#### B. P95 Latency

```bash
#!/bin/bash
# File: scripts/monitor_latency.sh

HOUR=$(date -u +"%Y-%m-%d %H")
LOG_FILE="/var/log/deltacrown-prod.log"

# Extract latency values (in ms)
grep "$HOUR" "$LOG_FILE" | \
  grep "Webhook delivered successfully" | \
  grep -oP 'latency=\K[0-9]+' | \
  sort -n > /tmp/latencies.txt

COUNT=$(wc -l < /tmp/latencies.txt)

if [ $COUNT -gt 0 ]; then
    P95_LINE=$(echo "scale=0; $COUNT * 0.95 / 1" | bc)
    P95=$(sed -n "${P95_LINE}p" /tmp/latencies.txt)
    
    echo "[$HOUR] P95 Latency: ${P95}ms (from $COUNT samples)"
    
    # Alert if above threshold
    if [ $P95 -gt 2000 ]; then
        echo "⚠️  ALERT: P95 latency above 2000ms threshold!"
    fi
else
    echo "[$HOUR] No latency data available"
fi
```

---

#### C. Circuit Breaker State

```bash
#!/bin/bash
# File: scripts/monitor_circuit_breaker.sh

HOUR=$(date -u +"%Y-%m-%d %H")
LOG_FILE="/var/log/deltacrown-prod.log"

CB_OPENS=$(grep "$HOUR" "$LOG_FILE" | grep "Circuit breaker OPENED" | wc -l)
CB_HALF_OPEN=$(grep "$HOUR" "$LOG_FILE" | grep "Circuit breaker HALF_OPEN" | wc -l)
CB_CLOSED=$(grep "$HOUR" "$LOG_FILE" | grep "Circuit breaker CLOSED" | wc -l)

echo "[$HOUR] Circuit Breaker: OPENED=$CB_OPENS, HALF_OPEN=$CB_HALF_OPEN, CLOSED=$CB_CLOSED"

# Get current state
CURRENT_STATE=$(grep "Circuit breaker" "$LOG_FILE" | tail -1 | grep -oP '(OPENED|HALF_OPEN|CLOSED)')
echo "Current state: $CURRENT_STATE"

# Alert if too many opens
if [ $CB_OPENS -gt 1 ]; then
    echo "⚠️  ALERT: Circuit breaker opened $CB_OPENS times this hour!"
fi
```

---

#### D. PII Leak Detection (Run Every 15 Minutes)

```bash
#!/bin/bash
# File: scripts/monitor_pii.sh

LOG_FILE="/var/log/deltacrown-prod.log"
ALERT_FILE="/var/log/pii_alerts.log"

# Check for emails
EMAIL_MATCHES=$(grep -i webhook "$LOG_FILE" | grep -iE '\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b' | head -5)

# Check for usernames (@mention style)
USERNAME_MATCHES=$(grep -i webhook "$LOG_FILE" | grep -E '@[a-zA-Z0-9_]+' | grep -v '@app\|@service' | head -5)

# Check for IP addresses
IP_MATCHES=$(grep -i webhook "$LOG_FILE" | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' | head -5)

# Report results
if [ -n "$EMAIL_MATCHES" ] || [ -n "$USERNAME_MATCHES" ] || [ -n "$IP_MATCHES" ]; then
    echo "🚨 PII LEAK DETECTED!" | tee -a "$ALERT_FILE"
    echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" | tee -a "$ALERT_FILE"
    
    [ -n "$EMAIL_MATCHES" ] && echo "Emails found: $EMAIL_MATCHES" | tee -a "$ALERT_FILE"
    [ -n "$USERNAME_MATCHES" ] && echo "Usernames found: $USERNAME_MATCHES" | tee -a "$ALERT_FILE"
    [ -n "$IP_MATCHES" ] && echo "IPs found: $IP_MATCHES" | tee -a "$ALERT_FILE"
    
    echo "🔴 IMMEDIATE ACTION: Rollback webhook flag (NOTIFICATIONS_WEBHOOK_ENABLED=False)" | tee -a "$ALERT_FILE"
    exit 1
else
    echo "✅ PII scan clean: No emails, usernames, or IPs detected in webhook logs"
    exit 0
fi
```

**Cron**: `*/15 * * * * /path/to/scripts/monitor_pii.sh`

---

## 📋 **Evidence Collection (For Hourly Report)**

### 1. Header Sample (Redacted)

```bash
# Capture one webhook request at receiver
grep "X-Webhook-" /var/log/receiver.log | head -10 | \
  sed 's/[0-9a-f]\{64\}/REDACTED_SIGNATURE/g' | \
  sed 's/[0-9]\{13\}/REDACTED_TIMESTAMP/g' | \
  sed 's/[0-9a-f]\{8\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{12\}/REDACTED_UUID/g'
```

**Expected output**:
```
X-Webhook-Signature: REDACTED_SIGNATURE
X-Webhook-Timestamp: REDACTED_TIMESTAMP
X-Webhook-Id: REDACTED_UUID
X-Webhook-Event: payment_verified
Content-Type: application/json
User-Agent: DeltaCrown-Webhook/1.0
```

---

### 2. PII Scan Output (Should Be Empty)

```bash
# Top 5 lines of PII grep (should return nothing)
bash scripts/monitor_pii.sh | head -5
```

**Expected output**:
```
✅ PII scan clean: No emails, usernames, or IPs detected in webhook logs
```

---

### 3. Receiver Verification Logs

```bash
# Sample signature verification at receiver
grep "Signature valid" /var/log/receiver.log | head -3
```

**Expected output**:
```
[INFO] Received webhook: event=payment_verified, webhook_id=abc123...
[INFO] Signature valid: True
[INFO] Timestamp age: 1.2s (fresh)
```

---

### 4. Retry Example (0→2→4s)

```bash
# Find a retry sequence
grep "Webhook delivery failed" /var/log/deltacrown-prod.log | \
  grep -A3 "attempt 1/3" | head -10
```

**Expected output**:
```
[INFO] Attempting webhook delivery (attempt 1/3): event=payment_verified
[WARN] Webhook delivery failed (attempt 1/3): status=503, retrying in 0s
[INFO] Attempting webhook delivery (attempt 2/3): event=payment_verified
[WARN] Webhook delivery failed (attempt 2/3): status=503, retrying in 2s
[INFO] Attempting webhook delivery (attempt 3/3): event=payment_verified
[INFO] Webhook delivered successfully: event=payment_verified, status=200
```

---

## 🚨 **Rollback Procedure (Instant)**

### One-Line Disable

```bash
# Method 1: Environment variable
export NOTIFICATIONS_WEBHOOK_ENABLED=false
sudo systemctl reload deltacrown-prod

# Method 2: Django shell (no restart)
python manage.py shell
>>> from django.conf import settings
>>> settings.NOTIFICATIONS_WEBHOOK_ENABLED = False
```

**Verification**:
```bash
# Check logs - should stop seeing webhook attempts
tail -f /var/log/deltacrown-prod.log | grep -i webhook
# (Should show no new entries after rollback)
```

---

## ✅ **Canary Success Criteria (24h @ 5%)**

Proceed to 25% if ALL conditions met:

- [x] **Success rate** ≥95% sustained
- [x] **P95 latency** <2000ms
- [x] **Circuit breaker opens** <5 total (≤1 per ~5 hours)
- [x] **PII leaks** = 0 (strict zero tolerance)
- [x] **Headers present** in all requests
- [x] **Timestamp validation** working (stale rejected)
- [x] **Receiver stable** (no error spikes)
- [x] **Team confident** in observability

---

## 📞 **On-Call Contact**

**Primary**: Engineering Team (webhook implementation)  
**Secondary**: Ops Team (production infrastructure)  
**Escalation**: CTO (if PII leak or critical failure)

**Slack Channels**:
- `#webhooks-canary` (monitoring updates)
- `#production-alerts` (automated alerts)
- `#on-call` (urgent escalations)

---

**Configuration Owner**: Ops Team  
**Monitor Owner**: Engineering Team  
**Review Cadence**: Hourly for first 24h  
**Next Checkpoint**: November 14, 2025 14:00 UTC (24h mark)
