# Admin Webhook Inspection API — Usage Guide

**Version**: 1.0  
**Status**: Production  
**Authentication**: Django Admin Staff Only  
**Last Updated**: 2025-11-13

---

## Overview

Read-only REST API for inspecting webhook deliveries, viewing statistics, and monitoring circuit breaker status. **No mutations** — all endpoints are GET-only.

**Base URL**: `/admin/api/webhooks/`

**Authentication**: Requires Django staff user (`is_staff=True`). Authenticated via Django session cookie.

---

## Endpoints

### 1. List Recent Webhook Deliveries

**GET** `/admin/api/webhooks/deliveries`

List recent webhook deliveries with filtering and pagination.

#### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `event` | string | Filter by event type | `payment_verified` |
| `status` | string | Filter by status | `success`, `failed`, `retrying` |
| `endpoint` | string | Filter by endpoint (partial match) | `api.example.com` |
| `cb_state` | string | Filter by circuit breaker state | `CLOSED`, `HALF_OPEN`, `OPEN` |
| `since` | ISO timestamp | Start time (default: 24h ago) | `2025-11-13T14:00:00Z` |
| `page` | integer | Page number (default: 1) | `2` |
| `page_size` | integer | Results per page (default: 50, max: 200) | `100` |

#### Example Request

```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/deliveries?event=payment_verified&status=success&page_size=50' \
  -H 'Cookie: sessionid=abc123...' \
  --cookie-jar cookies.txt
```

#### Example Response

```json
{
  "count": 150,
  "page": 1,
  "page_size": 50,
  "total_pages": 3,
  "results": [
    {
      "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "event": "payment_verified",
      "endpoint": "https://api.example.com/webhooks",
      "status": "success",
      "status_code": 200,
      "created_at": "2025-11-13T14:42:15Z",
      "delivered_at": "2025-11-13T14:42:15.145Z",
      "latency_ms": 145,
      "retry_count": 0,
      "circuit_breaker_state": "closed"
    },
    ...
  ]
}
```

---

### 2. Get Webhook Delivery Detail

**GET** `/admin/api/webhooks/deliveries/<webhook_id>`

Get detailed information about a specific webhook delivery.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `webhook_id` | UUID | Webhook delivery UUID |

#### Example Request

```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/deliveries/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d' \
  -H 'Cookie: sessionid=abc123...'
```

#### Example Response

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "event": "payment_verified",
  "endpoint": "https://api.example.com/webhooks",
  "status": "success",
  "status_code": 200,
  "created_at": "2025-11-13T14:42:15Z",
  "delivered_at": "2025-11-13T14:42:15.145Z",
  "latency_ms": 145,
  "retry_count": 0,
  "circuit_breaker_state": "closed",
  "payload": {
    "event": "payment_verified",
    "data": {
      "payment_id": 1001,
      "tournament_id": 501,
      "user_id": 2001,
      "amount": "50.00",
      "currency": "USD"
    }
  },
  "request_headers": {
    "Content-Type": "application/json",
    "X-Webhook-Signature": "***REDACTED***",
    "X-Webhook-Timestamp": "1700000000123",
    "X-Webhook-Id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
  },
  "response_body": "OK",
  "error_message": null,
  "retries": []
}
```

#### Redaction Policy

**Sensitive fields automatically redacted**:
- `X-Webhook-Signature` → `***REDACTED***`
- `Authorization` → `***REDACTED***`
- `X-API-Key` → `***REDACTED***`

**Response body truncated** to first 500 characters (prevent large payloads).

**Exposed fields** (safe to display):
- Timestamps (`X-Webhook-Timestamp`, `created_at`, `delivered_at`)
- Webhook ID (`X-Webhook-Id`)
- HTTP status code
- Latency metrics
- Retry count
- Endpoint URL (label only, no secrets)

---

### 3. Get Webhook Statistics

**GET** `/admin/api/webhooks/statistics`

Get aggregated webhook statistics for last 24 hours (or custom time range).

#### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `since` | ISO timestamp | Start time (default: 24h ago) | `2025-11-13T00:00:00Z` |
| `event` | string | Filter by event type | `payment_verified` |

#### Example Request

```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/statistics?since=2025-11-13T00:00:00Z' \
  -H 'Cookie: sessionid=abc123...'
```

#### Example Response

```json
{
  "time_range": {
    "start": "2025-11-13T00:00:00Z",
    "end": "2025-11-13T16:35:00Z"
  },
  "total_deliveries": 1250,
  "success_count": 1180,
  "failure_count": 70,
  "success_rate": 94.4,
  "latency": {
    "p50_ms": 145,
    "p95_ms": 412,
    "p99_ms": 1523,
    "avg_ms": 178.5,
    "min_ms": 98,
    "max_ms": 2104
  },
  "by_event": [
    {
      "event": "payment_verified",
      "count": 700,
      "success_count": 672,
      "success_rate": 96.0
    },
    {
      "event": "match_started",
      "count": 350,
      "success_count": 330,
      "success_rate": 94.3
    }
  ],
  "by_status_code": [
    {"code": 200, "count": 1150},
    {"code": 202, "count": 30},
    {"code": 503, "count": 60},
    {"code": 400, "count": 10}
  ],
  "circuit_breaker": {
    "opens_last_24h": 2,
    "currently_open_endpoints": [
      "https://api.receiver2.com/hooks"
    ]
  }
}
```

---

### 4. Get Circuit Breaker Status

**GET** `/admin/api/webhooks/circuit-breaker`

Get current circuit breaker status for all endpoints.

#### Example Request

```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/circuit-breaker' \
  -H 'Cookie: sessionid=abc123...'
```

#### Example Response

```json
{
  "endpoints": [
    {
      "endpoint": "https://api.example.com/webhooks",
      "state": "closed",
      "failure_count": 0,
      "last_failure": null,
      "last_success": "2025-11-13T14:42:15Z",
      "opens_last_24h": 0,
      "half_open_probe_due": null
    },
    {
      "endpoint": "https://api.receiver2.com/hooks",
      "state": "open",
      "failure_count": 5,
      "last_failure": "2025-11-13T14:38:00Z",
      "last_success": "2025-11-13T14:30:00Z",
      "opens_last_24h": 2,
      "half_open_probe_due": "2025-11-13T14:39:00Z"
    }
  ]
}
```

---

## Authentication

### Session-Based Authentication

API uses Django's standard session authentication. Staff users must log in via Django admin (`/admin/login`).

**Example login flow**:

```bash
# 1. Get CSRF token
curl -c cookies.txt https://deltacrown.gg/admin/login

# 2. Login (extract csrftoken from cookies.txt)
curl -b cookies.txt -c cookies.txt \
  -X POST https://deltacrown.gg/admin/login/ \
  -d "username=admin&password=yourpass&csrfmiddlewaretoken=TOKEN"

# 3. Access API with session cookie
curl -b cookies.txt https://deltacrown.gg/admin/api/webhooks/deliveries
```

### Permission Requirements

- User must have `is_staff=True`
- Enforced by `@staff_member_required` decorator
- Non-staff users get `302 Redirect` to login page

---

## Rate Limiting

**API is read-only** but rate-limited to prevent abuse.

| Limit Type | Value |
|------------|-------|
| **Requests/minute** | 60 (per IP) |
| **Concurrent requests** | 10 (per session) |
| **Burst allowance** | 100 (5-minute window) |

**Rate limit headers** (included in response):

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1700000060
```

**Rate limit exceeded response**:

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 30
}
```

**Status Code**: `429 Too Many Requests`

---

## Error Responses

### 401 Unauthorized

**Cause**: No session cookie or session expired.

```json
{
  "error": "Authentication required"
}
```

**Action**: Login via `/admin/login` and retry with session cookie.

---

### 403 Forbidden

**Cause**: User is authenticated but not staff (`is_staff=False`).

```json
{
  "error": "Staff permissions required"
}
```

**Action**: Request staff access from admin.

---

### 404 Not Found

**Cause**: Webhook ID does not exist.

```json
{
  "error": "Webhook delivery not found"
}
```

**Action**: Verify webhook ID is correct (must be UUID format).

---

### 400 Bad Request

**Cause**: Invalid query parameter (e.g., malformed ISO timestamp).

```json
{
  "error": "Invalid parameter",
  "details": "since must be ISO 8601 timestamp"
}
```

**Action**: Fix query parameter format and retry.

---

## Common Use Cases

### 1. Find Recent Failures

```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/deliveries?status=failed&page_size=20' \
  -H 'Cookie: sessionid=...'
```

### 2. Check Circuit Breaker Opens Today

```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/statistics?since=$(date -u +%Y-%m-%dT00:00:00Z)' \
  -H 'Cookie: sessionid=...' | jq '.circuit_breaker.opens_last_24h'
```

### 3. Inspect Specific Webhook Retry Chain

```bash
WEBHOOK_ID="a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
curl -X GET "https://deltacrown.gg/admin/api/webhooks/deliveries/$WEBHOOK_ID" \
  -H 'Cookie: sessionid=...' | jq '.retries'
```

### 4. Monitor Current Circuit Breaker State

```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/circuit-breaker' \
  -H 'Cookie: sessionid=...' | jq '.endpoints[] | select(.state != "closed")'
```

### 5. Export Last 24h Statistics to CSV

```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/statistics' \
  -H 'Cookie: sessionid=...' \
  | jq -r '.by_event[] | [.event, .count, .success_count, .success_rate] | @csv' \
  > webhook_stats.csv
```

---

## Security Considerations

### Data Protection

- **Signatures redacted**: Never expose `X-Webhook-Signature` in responses
- **Response truncation**: Large response bodies truncated to 500 chars
- **No mutation**: All endpoints read-only (GET only)
- **Staff-only**: Requires Django admin permissions

### Audit Logging

All API requests logged to `/var/log/deltacrown-admin-api.log`:

```
[2025-11-13T16:45:00Z] INFO: Admin API access
  user=admin_user
  endpoint=/admin/api/webhooks/deliveries
  query=?status=failed&page_size=20
  ip=192.168.1.100
  status=200
  response_time_ms=42
```

### HTTPS Only

API enforced over HTTPS in production:

```python
# settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## Troubleshooting

### "Session expired" errors

**Solution**: Re-login via `/admin/login` and get fresh session cookie.

### Slow response times (>1s)

**Cause**: Large result sets or missing indexes.

**Solution**:
- Reduce `page_size` (default 50, max 200)
- Add time filter (`since` parameter)
- Check database indexes on `created_at`, `event`, `endpoint`

### Missing recent webhooks in list

**Cause**: Default `since` filter is 24 hours ago.

**Solution**: Override `since` parameter:
```bash
curl -X GET 'https://deltacrown.gg/admin/api/webhooks/deliveries?since=2025-11-13T16:00:00Z'
```

---

## Future Enhancements

Planned for v2.0:

- [ ] Export to CSV/JSON (bulk download)
- [ ] Webhook replay endpoint (admin-only mutation)
- [ ] Real-time WebSocket updates (live dashboard)
- [ ] Advanced filters (latency ranges, payload search)
- [ ] Aggregated daily reports (pre-computed)

---

**Questions?** Contact `#platform-team` or email `platform@deltacrown.gg`
