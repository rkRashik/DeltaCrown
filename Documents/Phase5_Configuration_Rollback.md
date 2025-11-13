# Phase 5 Configuration & Rollback Guide

## Feature Flags

### Default State: OFF

All Phase 5 webhook features are **disabled by default** across all environments:

```python
# Django settings (default)
NOTIFICATIONS_WEBHOOK_ENABLED = False  # ← Master switch: OFF
```

**Zero behavior change**: Notification system operates exactly as before Phase 5.

---

## Configuration Reference

### Required Settings (when enabled)

```python
# Feature flag - enable webhook delivery
NOTIFICATIONS_WEBHOOK_ENABLED = True

# Webhook endpoint URL (required)
WEBHOOK_ENDPOINT = 'https://api.example.com/webhooks/deltacrown'

# HMAC secret key (required, min 32 chars recommended)
WEBHOOK_SECRET = 'your-webhook-secret-key-here'

# Optional: HTTP timeout per request (default: 10 seconds)
WEBHOOK_TIMEOUT = 10

# Optional: Maximum retry attempts (default: 3)
WEBHOOK_MAX_RETRIES = 3
```

### Environment Variables (Recommended)

```bash
# Production
export NOTIFICATIONS_WEBHOOK_ENABLED=true
export WEBHOOK_ENDPOINT="https://api.example.com/webhooks/deltacrown"
export WEBHOOK_SECRET="$(openssl rand -hex 32)"  # Generate 64-char random hex
export WEBHOOK_TIMEOUT=10
export WEBHOOK_MAX_RETRIES=3

# Staging
export NOTIFICATIONS_WEBHOOK_ENABLED=true
export WEBHOOK_ENDPOINT="https://staging-api.example.com/webhooks/deltacrown"
export WEBHOOK_SECRET="staging-webhook-secret-key"

# Development (disabled by default)
export NOTIFICATIONS_WEBHOOK_ENABLED=false
```

### Secret Key Generation

```bash
# Generate cryptographically secure random key
openssl rand -hex 32

# Example output: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

**Security Best Practices**:
- Minimum 32 characters (64 recommended)
- Use cryptographically secure random generation
- Store in environment variables (never commit to Git)
- Rotate periodically (e.g., quarterly)
- Different secrets per environment (prod/staging/dev)

---

## Rollback Procedure

### One-Line Rollback

**Disable webhook delivery immediately:**

```python
# In Django settings
NOTIFICATIONS_WEBHOOK_ENABLED = False
```

**Or via environment variable:**

```bash
export NOTIFICATIONS_WEBHOOK_ENABLED=false
```

**Effect**:
- ✅ Webhook delivery immediately disabled
- ✅ Notification system continues to work (email delivery unaffected)
- ✅ Zero downtime
- ✅ No code deployment required
- ✅ No database changes required

### Verification

```bash
# Check current flag status
python manage.py shell -c "from django.conf import settings; print(f'Webhooks enabled: {getattr(settings, \"NOTIFICATIONS_WEBHOOK_ENABLED\", False)}')"

# Expected output (after rollback):
# Webhooks enabled: False
```

### Rollback Confirmation

```bash
# Run notification test with webhooks disabled
python manage.py shell <<EOF
from apps.notifications.services import notify
result = notify(
    event='test_event',
    title='Test Notification',
    body='Testing webhook rollback',
    targets=[1]  # User ID
)
print(f"Created: {result['created']}, Webhook sent: {result.get('webhook_sent', 0)}")
# Expected: Created: 1, Webhook sent: 0
EOF
```

---

## Environment Configuration Matrix

| Environment | ENABLED | ENDPOINT | SECRET | TIMEOUT | RETRIES |
|-------------|---------|----------|--------|---------|---------|
| **Production** | `true` | `https://api.deltacrown.gg/webhooks` | Env var (64 char) | 10s | 3 |
| **Staging** | `true` | `https://staging-api.deltacrown.gg/webhooks` | Env var (64 char) | 10s | 3 |
| **Development** | `false` | N/A | N/A | 10s | 3 |
| **Testing** | `false` | (mocked) | (test value) | 10s | 3 |

### Settings File Organization

```python
# deltacrown/settings.py (base settings)
NOTIFICATIONS_WEBHOOK_ENABLED = False  # Default: OFF

# Optional defaults (used if not specified)
WEBHOOK_TIMEOUT = 10
WEBHOOK_MAX_RETRIES = 3

# deltacrown/settings_production.py
NOTIFICATIONS_WEBHOOK_ENABLED = os.getenv('NOTIFICATIONS_WEBHOOK_ENABLED', 'false').lower() == 'true'
WEBHOOK_ENDPOINT = os.getenv('WEBHOOK_ENDPOINT')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
WEBHOOK_TIMEOUT = int(os.getenv('WEBHOOK_TIMEOUT', 10))
WEBHOOK_MAX_RETRIES = int(os.getenv('WEBHOOK_MAX_RETRIES', 3))

# Validate required settings if enabled
if NOTIFICATIONS_WEBHOOK_ENABLED:
    if not WEBHOOK_ENDPOINT:
        raise ValueError("WEBHOOK_ENDPOINT is required when NOTIFICATIONS_WEBHOOK_ENABLED=True")
    if not WEBHOOK_SECRET:
        raise ValueError("WEBHOOK_SECRET is required when NOTIFICATIONS_WEBHOOK_ENABLED=True")
    if len(WEBHOOK_SECRET) < 32:
        import warnings
        warnings.warn("WEBHOOK_SECRET should be at least 32 characters for security")
```

---

## Deployment Checklist

### Phase 5 Enable (Production)

- [ ] Generate secure webhook secret (64 characters)
- [ ] Store secret in production environment variables
- [ ] Configure webhook endpoint URL
- [ ] Test webhook endpoint is reachable (200/202 response)
- [ ] Verify webhook receiver can validate HMAC signatures
- [ ] Set `NOTIFICATIONS_WEBHOOK_ENABLED=true` in production env
- [ ] Deploy settings change (no code changes required)
- [ ] Monitor logs for webhook delivery success/failure
- [ ] Verify notification emails still work (backup delivery)
- [ ] Test rollback procedure (disable flag, verify notifications continue)

### Pre-Deployment Testing

```bash
# 1. Test webhook service in isolation
pytest tests/test_webhook_service.py -v

# 2. Test integration with notifications
pytest tests/test_webhook_integration.py -v

# 3. Test with feature flag OFF (default behavior)
NOTIFICATIONS_WEBHOOK_ENABLED=false pytest tests/test_notification_signals.py -v

# 4. Test with feature flag ON (webhook delivery)
NOTIFICATIONS_WEBHOOK_ENABLED=true pytest tests/test_webhook_integration.py -v

# Expected: All 43 tests passing
```

---

## Monitoring & Observability

### Key Metrics to Track

```python
# Webhook delivery success rate
webhook_success_rate = successful_deliveries / total_attempts

# Average retry count
avg_retries = sum(retry_counts) / len(retry_counts)

# Timeout rate
timeout_rate = timeout_failures / total_attempts

# 4xx error rate (configuration issues)
client_error_rate = client_errors / total_attempts

# 5xx error rate (receiver issues)
server_error_rate = server_errors / total_attempts
```

### Log Monitoring

```bash
# Success
grep "Webhook delivered successfully" logs/app.log

# Failures requiring investigation
grep "Webhook delivery failed after .* attempts" logs/app.log

# Client errors (configuration issues)
grep "Client errors (4xx) are not retried" logs/app.log

# Authentication failures
grep "Authentication failed - check webhook secret" logs/app.log
```

### Alerts (Recommended)

1. **High Failure Rate**: Alert if webhook failure rate > 5% over 15 minutes
2. **Consistent 4xx Errors**: Alert if 4xx errors persist for > 5 minutes (config issue)
3. **Receiver Down**: Alert if 5xx/timeout rate > 80% over 5 minutes (receiver outage)
4. **Secret Mismatch**: Alert on 401 Unauthorized responses (secret rotation issue)

---

## Troubleshooting

### Issue: Webhooks Not Being Sent

**Check**:
```bash
python manage.py shell -c "from django.conf import settings; print(settings.NOTIFICATIONS_WEBHOOK_ENABLED)"
```

**Expected**: `True`

**Fix**: Enable feature flag in environment configuration.

---

### Issue: 401 Unauthorized Responses

**Cause**: HMAC signature mismatch (secret key mismatch)

**Check**:
```bash
# Run verification script
python scripts/verify_webhook_signature.py

# Test with production secret
python manage.py shell <<EOF
from apps.notifications.services.webhook_service import get_webhook_service
service = get_webhook_service()
payload = {"event": "test", "data": {}, "metadata": {}}
signature = service.generate_signature(payload)
print(f"Generated signature: {signature}")
EOF
```

**Fix**: Ensure webhook receiver uses same secret as `WEBHOOK_SECRET` setting.

---

### Issue: All Webhook Deliveries Timing Out

**Cause**: Endpoint unreachable or slow

**Check**:
```bash
# Test endpoint connectivity
curl -v -X POST https://api.example.com/webhooks/deltacrown \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Expected: 200-204 response within 10 seconds
```

**Fix**: 
- Verify endpoint URL is correct
- Check firewall/network rules allow outbound HTTPS
- Increase `WEBHOOK_TIMEOUT` if receiver is legitimately slow
- Contact webhook receiver to optimize response time

---

### Issue: Notifications Not Being Created

**Cause**: Webhook failure breaking notification service

**Check**: This should never happen (error isolation)

**Verification**:
```bash
# Test error isolation
pytest tests/test_webhook_integration.py::TestWebhookIntegration::test_webhook_failure_does_not_break_notification -v

# Expected: PASSED
```

**Fix**: If notifications fail when webhooks fail, this is a bug. Rollback immediately:
```python
NOTIFICATIONS_WEBHOOK_ENABLED = False
```

Then file bug report with logs.

---

## Success Criteria

### Phase 5 Fully Deployed ✅

- [ ] Feature flag OFF by default (zero behavior change)
- [ ] All 43 tests passing (Phase 4 + Phase 5)
- [ ] Webhook delivery working in staging
- [ ] HMAC signatures validated by receiver
- [ ] Exponential backoff observed in logs (0s/2s/4s)
- [ ] 4xx errors abort without retry (confirmed in logs)
- [ ] Rollback tested and verified (flag OFF → webhooks stop, notifications continue)
- [ ] No PII in webhook payloads (IDs only)
- [ ] Documentation complete (MAP.md, trace.yml, evidence pack)
- [ ] Secrets stored in environment variables (not committed to Git)

---

## Rollback Decision Matrix

| Scenario | Action | Urgency |
|----------|--------|---------|
| **5xx errors > 80% for 5min** | Rollback if receiver down | High |
| **4xx errors persisting** | Check config, may need rollback | Medium |
| **Webhook latency impacting app** | Rollback, investigate async solution | High |
| **Receiver security incident** | Rollback immediately, rotate secrets | Critical |
| **Business decision** | Rollback (one-line change) | Low |

**Rollback Command**:
```bash
# Emergency rollback (one command)
echo "NOTIFICATIONS_WEBHOOK_ENABLED=false" >> /etc/deltacrown/env && systemctl reload deltacrown
```

---

## Phase 5 Configuration Complete ✅

All configuration and rollback procedures documented. Feature is production-ready with safe defaults (OFF) and simple one-line rollback procedure.
