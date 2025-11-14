# Webhook Receiver Integration Guide — Phase 5.6 (Hardened)

**Audience**: Teams implementing webhook receivers for DeltaCrown notifications  
**Protocol**: HMAC-SHA256 with timestamp replay protection  
**Version**: 5.6 (includes replay safety + backward compatible)

---

## 🎯 **Quick Start (5 Minutes)**

### Minimum Viable Receiver (Python/Flask)

```python
import hmac
import hashlib
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = 'your-64-char-hex-secret-here'
REPLAY_WINDOW_SECONDS = 300  # 5 minutes
CLOCK_SKEW_SECONDS = 30

# In-memory deduplication (use Redis in production)
seen_webhooks = set()

@app.route('/webhooks/inbound', methods=['POST'])
def webhook_inbound():
    """
    Receive webhook from DeltaCrown with:
    - HMAC-SHA256 signature verification
    - Timestamp replay protection
    - Webhook ID deduplication
    """
    
    # 1. Extract headers
    signature = request.headers.get('X-Webhook-Signature')
    timestamp = request.headers.get('X-Webhook-Timestamp')
    webhook_id = request.headers.get('X-Webhook-Id')
    event = request.headers.get('X-Webhook-Event')
    
    # 2. Validate headers present
    if not all([signature, timestamp, webhook_id, event]):
        return jsonify({"error": "Missing required headers"}), 400
    
    # 3. Get request body
    body = request.get_data(as_text=True)
    
    # 4. Verify timestamp freshness
    try:
        timestamp_ms = int(timestamp)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        age_seconds = (now_ms - timestamp_ms) / 1000
        
        # Reject stale webhooks (>5 minutes old)
        if age_seconds > REPLAY_WINDOW_SECONDS:
            return jsonify({"error": "Timestamp too old"}), 400
        
        # Reject future timestamps (beyond clock skew tolerance)
        if age_seconds < -CLOCK_SKEW_SECONDS:
            return jsonify({"error": "Timestamp in future"}), 400
    
    except ValueError:
        return jsonify({"error": "Invalid timestamp format"}), 400
    
    # 5. Verify HMAC signature (constant-time comparison)
    message = f"{timestamp}.{body}"
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    # 6. Deduplicate via webhook_id (prevent replay attacks)
    if webhook_id in seen_webhooks:
        return jsonify({"status": "duplicate", "message": "Webhook already processed"}), 200
    
    seen_webhooks.add(webhook_id)
    # In production: redis.setex(f"webhook:{webhook_id}", 900, "1")  # 15-min TTL
    
    # 7. Parse and process payload
    try:
        payload = json.loads(body)
        event_type = payload.get('event')
        data = payload.get('data', {})
        
        # Route to event handler
        if event_type == 'payment_verified':
            process_payment_verified(data)
        elif event_type == 'match_started':
            process_match_started(data)
        # ... other events
        
        return jsonify({"status": "accepted"}), 200
    
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON"}), 400
    except Exception as e:
        # Log error but return 200 to avoid retries for processing errors
        print(f"Processing error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_payment_verified(data):
    """Handle payment_verified event"""
    print(f"Payment verified: {data}")
    # Your business logic here

def process_match_started(data):
    """Handle match_started event"""
    print(f"Match started: {data}")
    # Your business logic here

if __name__ == '__main__':
    app.run(port=5000)
```

**Test your receiver**:
```bash
python receiver.py
# Server runs on http://localhost:5000
```

---

## 🔐 **Security Implementation**

### 1. HMAC-SHA256 Signature Verification

**Signature Format** (Phase 5.6 with timestamp):
```
HMAC-SHA256(timestamp + "." + body)
```

**Example**:
```python
import hmac
import hashlib

def verify_signature(body: str, signature: str, timestamp: str, secret: str) -> bool:
    """
    Verify webhook signature with timestamp.
    
    Args:
        body: Raw request body (JSON string)
        signature: X-Webhook-Signature header value (64-char hex)
        timestamp: X-Webhook-Timestamp header value (Unix ms)
        secret: Shared webhook secret (64-char hex)
    
    Returns:
        True if signature valid, False otherwise
    """
    message = f"{timestamp}.{body}"
    expected = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison (prevents timing attacks)
    return hmac.compare_digest(expected, signature)
```

**⚠️ Common Mistakes**:
- ❌ Don't use `==` for signature comparison (timing attack vulnerable)
- ❌ Don't parse body before verification (verifies raw bytes)
- ❌ Don't skip timestamp validation (allows replay attacks)

---

### 2. Timestamp Replay Protection (Module 5.6)

**Validation Rules**:
1. **Freshness**: Timestamp must be ≤5 minutes old
2. **Clock Skew**: Allow up to 30 seconds in future (for clock drift)
3. **Format**: Unix milliseconds (13 digits)

```python
from datetime import datetime, timezone

def validate_timestamp(timestamp: str, max_age_seconds: int = 300) -> tuple[bool, str]:
    """
    Validate webhook timestamp freshness.
    
    Args:
        timestamp: X-Webhook-Timestamp header (Unix ms)
        max_age_seconds: Maximum allowed age (default 5 minutes)
    
    Returns:
        (valid, error_message) tuple
    """
    try:
        timestamp_ms = int(timestamp)
    except ValueError:
        return False, "Invalid timestamp format"
    
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    age_seconds = (now_ms - timestamp_ms) / 1000
    
    # Check if too old
    if age_seconds > max_age_seconds:
        return False, f"Timestamp too old: {age_seconds:.1f}s (max {max_age_seconds}s)"
    
    # Check if too far in future (clock skew tolerance: 30s)
    if age_seconds < -30:
        return False, f"Timestamp in future: {-age_seconds:.1f}s ahead"
    
    return True, None
```

**Example usage**:
```python
valid, error = validate_timestamp(request.headers.get('X-Webhook-Timestamp'))
if not valid:
    return jsonify({"error": error}), 400
```

---

### 3. Webhook ID Deduplication (Prevent Replays)

**Why**: Even with timestamp validation, an attacker could replay a fresh webhook multiple times.

**Implementation** (Redis recommended):

```python
import redis
from uuid import UUID

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def is_duplicate_webhook(webhook_id: str) -> bool:
    """
    Check if webhook has been processed before.
    
    Uses Redis SET with 15-minute TTL (3x replay window for safety).
    
    Args:
        webhook_id: X-Webhook-Id header (UUID v4)
    
    Returns:
        True if duplicate, False if first time seen
    """
    # Validate UUID format
    try:
        UUID(webhook_id, version=4)
    except ValueError:
        return False  # Invalid UUID, treat as unique (will fail later)
    
    key = f"webhook:{webhook_id}"
    
    # Check if exists
    if redis_client.exists(key):
        return True
    
    # Mark as seen (15-minute TTL = 900 seconds)
    redis_client.setex(key, 900, "1")
    return False
```

**Usage**:
```python
webhook_id = request.headers.get('X-Webhook-Id')

if is_duplicate_webhook(webhook_id):
    # Already processed - return success to avoid retries
    return jsonify({"status": "duplicate"}), 200

# Process webhook...
```

**Alternative (PostgreSQL with cleanup job)**:
```sql
CREATE TABLE processed_webhooks (
    webhook_id UUID PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Check before processing
INSERT INTO processed_webhooks (webhook_id)
VALUES ('550e8400-e29b-41d4-a716-446655440000')
ON CONFLICT (webhook_id) DO NOTHING
RETURNING webhook_id;
-- Returns NULL if duplicate

-- Cleanup job (run every 15 minutes)
DELETE FROM processed_webhooks
WHERE processed_at < NOW() - INTERVAL '15 minutes';
```

---

## 📦 **Payload Structure**

### Event: `payment_verified`

```json
{
  "event": "payment_verified",
  "data": {
    "payment_id": 12345,
    "tournament_id": 67890,
    "user_id": 11111,
    "amount": "50.00",
    "currency": "USD",
    "status": "verified",
    "verified_at": "2025-11-13T14:05:23Z"
  },
  "metadata": {
    "timestamp": "2025-11-13T14:05:23Z",
    "service": "deltacrown",
    "version": "5.6"
  }
}
```

**Headers**:
```http
POST /webhooks/inbound HTTP/1.1
Host: api.deltacrown.gg
Content-Type: application/json
User-Agent: DeltaCrown-Webhook/1.0
X-Webhook-Signature: a3c8f7e2d1b4567890abcdef1234567890abcdef1234567890abcdef12345678
X-Webhook-Timestamp: 1700000000123
X-Webhook-Id: 550e8400-e29b-41d4-a716-446655440000
X-Webhook-Event: payment_verified
```

---

### Event: `match_started`

```json
{
  "event": "match_started",
  "data": {
    "match_id": 54321,
    "tournament_id": 67890,
    "game_id": 1,
    "game_name": "League of Legends",
    "team_a_id": 111,
    "team_b_id": 222,
    "scheduled_start": "2025-11-13T15:00:00Z",
    "status": "in_progress"
  },
  "metadata": {
    "timestamp": "2025-11-13T15:01:12Z",
    "service": "deltacrown",
    "version": "5.6"
  }
}
```

---

### Event: `tournament_registration_opened`

```json
{
  "event": "tournament_registration_opened",
  "data": {
    "tournament_id": 67890,
    "game_id": 2,
    "game_name": "Valorant",
    "title": "Winter Championship 2025",
    "registration_opens": "2025-11-13T00:00:00Z",
    "registration_closes": "2025-11-20T23:59:59Z",
    "max_teams": 32
  },
  "metadata": {
    "timestamp": "2025-11-13T00:00:15Z",
    "service": "deltacrown",
    "version": "5.6"
  }
}
```

---

## 🧪 **Testing Your Receiver**

### 1. Generate Test Signature

Use the provided verification tool:

```bash
# From DeltaCrown repository
python scripts/verify_webhook_signature.py

# Generates test payloads with valid signatures
```

**Manual generation** (Python):
```python
import hmac
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

# Configuration
SECRET = 'your-64-char-hex-secret'
ENDPOINT = 'http://localhost:5000/webhooks/inbound'

# Create payload
payload = {
    "event": "payment_verified",
    "data": {
        "payment_id": 12345,
        "tournament_id": 67890,
        "user_id": 11111,
        "amount": "50.00"
    },
    "metadata": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "deltacrown",
        "version": "5.6"
    }
}

body = json.dumps(payload)
timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))
webhook_id = str(uuid4())

# Generate signature
message = f"{timestamp}.{body}"
signature = hmac.new(
    SECRET.encode('utf-8'),
    message.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# Send via cURL
import subprocess
subprocess.run([
    'curl', '-X', 'POST', ENDPOINT,
    '-H', 'Content-Type: application/json',
    '-H', f'X-Webhook-Signature: {signature}',
    '-H', f'X-Webhook-Timestamp: {timestamp}',
    '-H', f'X-Webhook-Id: {webhook_id}',
    '-H', 'X-Webhook-Event: payment_verified',
    '-H', 'User-Agent: DeltaCrown-Webhook/1.0',
    '-d', body
])
```

---

### 2. Test Scenarios

#### A. Valid Request (200 OK)

```bash
curl -X POST http://localhost:5000/webhooks/inbound \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: <valid-signature>" \
  -H "X-Webhook-Timestamp: $(date +%s)000" \
  -H "X-Webhook-Id: $(uuidgen)" \
  -H "X-Webhook-Event: payment_verified" \
  -d '{"event":"payment_verified","data":{"payment_id":123}}'

# Expected: 200 OK
```

#### B. Invalid Signature (401 Unauthorized)

```bash
curl -X POST http://localhost:5000/webhooks/inbound \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: invalid_signature_here" \
  -H "X-Webhook-Timestamp: $(date +%s)000" \
  -H "X-Webhook-Id: $(uuidgen)" \
  -H "X-Webhook-Event: payment_verified" \
  -d '{"event":"payment_verified","data":{"payment_id":123}}'

# Expected: 401 Unauthorized, {"error": "Invalid signature"}
```

#### C. Stale Timestamp (400 Bad Request)

```bash
# Generate timestamp from 10 minutes ago
OLD_TIMESTAMP=$(($(date +%s) - 600))000

curl -X POST http://localhost:5000/webhooks/inbound \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: <valid-signature-for-old-timestamp>" \
  -H "X-Webhook-Timestamp: $OLD_TIMESTAMP" \
  -H "X-Webhook-Id: $(uuidgen)" \
  -H "X-Webhook-Event: payment_verified" \
  -d '{"event":"payment_verified","data":{"payment_id":123}}'

# Expected: 400 Bad Request, {"error": "Timestamp too old"}
```

#### D. Duplicate Webhook (200 OK, not processed)

```bash
# Send same webhook_id twice
WEBHOOK_ID=$(uuidgen)

# First request
curl -X POST http://localhost:5000/webhooks/inbound \
  -H "X-Webhook-Id: $WEBHOOK_ID" \
  ... (other headers)

# Expected: 200 OK, {"status": "accepted"}

# Second request (duplicate)
curl -X POST http://localhost:5000/webhooks/inbound \
  -H "X-Webhook-Id: $WEBHOOK_ID" \
  ... (same headers)

# Expected: 200 OK, {"status": "duplicate"}
```

---

## 🔄 **Response Codes & Retry Behavior**

### Your Receiver Should Return:

| Code | Meaning | DeltaCrown Behavior |
|------|---------|---------------------|
| **200, 201, 202, 204** | Success | Mark as delivered, no retry |
| **400-499** | Client error (bad request, invalid signature) | **No retry**, log error |
| **500-599** | Server error (temporary failure) | **Retry** with exponential backoff (0s/2s/4s) |
| **Timeout** | Request took >10s | **Retry** (treated as 5xx) |

**Retry Schedule**:
- Attempt 1: Immediate (0s delay)
- Attempt 2: 2s delay
- Attempt 3: 4s delay
- After 3 failures: Give up, log error

**Circuit Breaker**:
- After 5 consecutive failures (all 3 retries exhausted) within 2 minutes: Circuit opens
- Open state: Webhooks blocked for 60 seconds
- After 60s: One probe attempt (half-open state)
- If probe succeeds: Circuit closes (resume normal operation)
- If probe fails: Circuit reopens (another 60s wait)

**Recommendation**: Return **500** for temporary errors (database down, rate limit exceeded), **400** for permanent errors (invalid event type, business rule violation).

---

## 🛡️ **Security Best Practices**

### 1. Always Verify Signature FIRST
```python
# ✅ CORRECT: Verify before processing
if not verify_signature(body, signature, timestamp, secret):
    return jsonify({"error": "Invalid signature"}), 401

# Process payload...
```

```python
# ❌ WRONG: Processing before verification
payload = json.loads(body)
user_id = payload['data']['user_id']

if not verify_signature(body, signature, timestamp, secret):
    return jsonify({"error": "Invalid signature"}), 401
```

---

### 2. Use Constant-Time Comparison

```python
# ✅ CORRECT: Prevents timing attacks
import hmac
return hmac.compare_digest(expected, actual)
```

```python
# ❌ WRONG: Vulnerable to timing attacks
return expected == actual
```

---

### 3. Validate Timestamp Before Signature

```python
# ✅ CORRECT: Reject stale timestamps early
valid, error = validate_timestamp(timestamp)
if not valid:
    return jsonify({"error": error}), 400

if not verify_signature(body, signature, timestamp, secret):
    return jsonify({"error": "Invalid signature"}), 401
```

Why? Prevents replay attacks even if signature is valid.

---

### 4. Store Webhook Secret Securely

```python
# ✅ CORRECT: Load from environment/secrets manager
import os
WEBHOOK_SECRET = os.environ['WEBHOOK_SECRET']
```

```python
# ❌ WRONG: Hardcoded secret
WEBHOOK_SECRET = 'a1b2c3d4...'  # Never commit secrets!
```

---

### 5. Deduplicate via webhook_id

```python
# ✅ CORRECT: Check before processing
if is_duplicate_webhook(webhook_id):
    return jsonify({"status": "duplicate"}), 200

# Process webhook...
```

```python
# ❌ WRONG: No deduplication
# Allows replay attacks within 5-minute window
```

---

## 🐛 **Troubleshooting**

### Problem: Signature Verification Always Fails

**Check**:
1. **Secret mismatch**: Verify `WEBHOOK_SECRET` matches sender
   ```bash
   echo $WEBHOOK_SECRET | wc -c  # Should be 65 (64 chars + newline)
   ```

2. **Body modification**: Ensure you're verifying raw body (not parsed JSON)
   ```python
   # ✅ CORRECT
   body = request.get_data(as_text=True)
   verify_signature(body, signature, timestamp, secret)
   
   # ❌ WRONG
   body = json.dumps(request.get_json())  # May change whitespace/ordering
   ```

3. **Timestamp format**: Check message is `"{timestamp}.{body}"`
   ```python
   message = f"{timestamp}.{body}"  # timestamp is string (Unix ms)
   ```

4. **Encoding**: Use UTF-8 for all strings
   ```python
   secret.encode('utf-8')
   message.encode('utf-8')
   ```

---

### Problem: Timestamp Validation Fails

**Check**:
1. **Clock skew**: Sync NTP on both systems
   ```bash
   date -u +%s  # Should match sender within ~30s
   ```

2. **Timezone**: Always use UTC
   ```python
   datetime.now(timezone.utc)  # Not datetime.now() (local time)
   ```

3. **Milliseconds**: Timestamp is Unix ms (13 digits), not seconds
   ```python
   timestamp_ms = int(timestamp)  # e.g., 1700000000123
   now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
   ```

---

### Problem: Duplicate Webhooks Processed

**Check**:
1. **Redis TTL**: Ensure ≥15 minutes (3x replay window)
   ```python
   redis_client.setex(f"webhook:{webhook_id}", 900, "1")  # 900s = 15min
   ```

2. **Cache connectivity**: Verify Redis is accessible
   ```python
   redis_client.ping()  # Should return True
   ```

3. **Return 200 for duplicates**: Don't return 4xx (triggers retries)
   ```python
   if is_duplicate_webhook(webhook_id):
       return jsonify({"status": "duplicate"}), 200  # ✅
       # NOT: return jsonify({"error": "Duplicate"}), 400  # ❌
   ```

---

## 📚 **Complete Examples**

### Node.js / Express

```javascript
const express = require('express');
const crypto = require('crypto');
const redis = require('redis');

const app = express();
const redisClient = redis.createClient();

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;
const REPLAY_WINDOW_SECONDS = 300;
const CLOCK_SKEW_SECONDS = 30;

app.use(express.json({
  verify: (req, res, buf) => {
    req.rawBody = buf.toString('utf8');
  }
}));

app.post('/webhooks/inbound', async (req, res) => {
  const signature = req.headers['x-webhook-signature'];
  const timestamp = req.headers['x-webhook-timestamp'];
  const webhookId = req.headers['x-webhook-id'];
  const event = req.headers['x-webhook-event'];
  
  // Validate headers
  if (!signature || !timestamp || !webhookId || !event) {
    return res.status(400).json({ error: 'Missing required headers' });
  }
  
  // Validate timestamp
  const timestampMs = parseInt(timestamp);
  const nowMs = Date.now();
  const ageSeconds = (nowMs - timestampMs) / 1000;
  
  if (ageSeconds > REPLAY_WINDOW_SECONDS) {
    return res.status(400).json({ error: 'Timestamp too old' });
  }
  
  if (ageSeconds < -CLOCK_SKEW_SECONDS) {
    return res.status(400).json({ error: 'Timestamp in future' });
  }
  
  // Verify signature
  const message = `${timestamp}.${req.rawBody}`;
  const expectedSignature = crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(message)
    .digest('hex');
  
  if (!crypto.timingSafeEqual(
    Buffer.from(expectedSignature),
    Buffer.from(signature)
  )) {
    return res.status(401).json({ error: 'Invalid signature' });
  }
  
  // Check for duplicate
  const isDuplicate = await redisClient.exists(`webhook:${webhookId}`);
  if (isDuplicate) {
    return res.status(200).json({ status: 'duplicate' });
  }
  
  await redisClient.setEx(`webhook:${webhookId}`, 900, '1');
  
  // Process webhook
  const payload = req.body;
  console.log(`Received ${payload.event}:`, payload.data);
  
  res.status(200).json({ status: 'accepted' });
});

app.listen(5000, () => console.log('Receiver listening on :5000'));
```

---

### Go

```go
package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
    "os"
    "strconv"
    "time"
    
    "github.com/go-redis/redis/v8"
)

var (
    webhookSecret = os.Getenv("WEBHOOK_SECRET")
    redisClient   = redis.NewClient(&redis.Options{Addr: "localhost:6379"})
)

type Payload struct {
    Event    string                 `json:"event"`
    Data     map[string]interface{} `json:"data"`
    Metadata map[string]interface{} `json:"metadata"`
}

func webhookHandler(w http.ResponseWriter, r *http.Request) {
    // Extract headers
    signature := r.Header.Get("X-Webhook-Signature")
    timestamp := r.Header.Get("X-Webhook-Timestamp")
    webhookID := r.Header.Get("X-Webhook-Id")
    event := r.Header.Get("X-Webhook-Event")
    
    if signature == "" || timestamp == "" || webhookID == "" || event == "" {
        http.Error(w, `{"error":"Missing required headers"}`, http.StatusBadRequest)
        return
    }
    
    // Read body
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, `{"error":"Cannot read body"}`, http.StatusBadRequest)
        return
    }
    
    // Validate timestamp
    timestampMs, err := strconv.ParseInt(timestamp, 10, 64)
    if err != nil {
        http.Error(w, `{"error":"Invalid timestamp"}`, http.StatusBadRequest)
        return
    }
    
    nowMs := time.Now().UnixMilli()
    ageSeconds := float64(nowMs-timestampMs) / 1000
    
    if ageSeconds > 300 {
        http.Error(w, `{"error":"Timestamp too old"}`, http.StatusBadRequest)
        return
    }
    
    if ageSeconds < -30 {
        http.Error(w, `{"error":"Timestamp in future"}`, http.StatusBadRequest)
        return
    }
    
    // Verify signature
    message := fmt.Sprintf("%s.%s", timestamp, string(body))
    mac := hmac.New(sha256.New, []byte(webhookSecret))
    mac.Write([]byte(message))
    expectedSignature := hex.EncodeToString(mac.Sum(nil))
    
    if !hmac.Equal([]byte(expectedSignature), []byte(signature)) {
        http.Error(w, `{"error":"Invalid signature"}`, http.StatusUnauthorized)
        return
    }
    
    // Check for duplicate
    ctx := r.Context()
    exists, err := redisClient.Exists(ctx, "webhook:"+webhookID).Result()
    if err == nil && exists > 0 {
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(map[string]string{"status": "duplicate"})
        return
    }
    
    redisClient.SetEX(ctx, "webhook:"+webhookID, "1", 15*time.Minute)
    
    // Parse and process
    var payload Payload
    if err := json.Unmarshal(body, &payload); err != nil {
        http.Error(w, `{"error":"Invalid JSON"}`, http.StatusBadRequest)
        return
    }
    
    fmt.Printf("Received %s: %v\n", payload.Event, payload.Data)
    
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(map[string]string{"status": "accepted"})
}

func main() {
    http.HandleFunc("/webhooks/inbound", webhookHandler)
    fmt.Println("Receiver listening on :5000")
    http.ListenAndServe(":5000", nil)
}
```

---

## ✅ **Production Checklist**

Before going live:

- [ ] **Secret stored securely** (secrets manager, not hardcoded)
- [ ] **Signature verification** implemented with `hmac.compare_digest`
- [ ] **Timestamp validation** (5-min window + 30s skew)
- [ ] **Webhook ID deduplication** (Redis or database with TTL)
- [ ] **Error handling** (return 500 for retryable errors, 400 for permanent)
- [ ] **Logging** (log all webhook receipts, signature failures, duplicates)
- [ ] **Monitoring** (track success rate, latency, duplicate rate)
- [ ] **Load testing** (can handle 100 webhooks/second?)
- [ ] **TLS/HTTPS** enabled (don't expose webhook endpoint over HTTP)
- [ ] **Rate limiting** (prevent DoS via webhook spam)

---

## 📞 **Support**

**Documentation**: `Documents/PHASE_5_6_FINAL_DELIVERY.md`  
**Verification Tool**: `scripts/verify_webhook_signature.py`  
**Staging Test Payloads**: `Documents/staging_payments_output.json`

**Questions?** Contact Engineering Team via `#webhooks-support` Slack channel.

---

**Integration Guide Version**: 5.6  
**Last Updated**: November 13, 2025  
**Status**: ✅ Production-ready (Phase 5.5 + 5.6 merged)
