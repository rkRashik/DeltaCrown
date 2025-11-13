# Admin Tournament Operations API

**Phase E Section 9** - Staff-only read-only inspection endpoints for tournament operations.

## Overview

The Tournament Operations API provides admin staff with real-time inspection capabilities for:

- **Payment verification tracking** - Monitor payment statuses, transaction IDs, verification progress
- **Match state and winner tracking** - View match progression, scores, winner determination
- **Dispute resolution tracking** - Monitor dispute statuses, resolution progress, evidence availability

All endpoints return **IDs-only responses** (no PII: no emails, names, phone numbers) for compliance and security.

---

## 🔐 Permission Model

**Permission Class**: `IsAdminUser` (Django built-in)

**Requirements**:
- User must be authenticated
- User must have `is_staff=True`

**Use Cases**:
- Support staff investigating payment issues
- Tournament organizers monitoring match progress
- Admin staff resolving disputes
- Monitoring dashboards and alerting systems

**Rate Limiting**: None (internal admin use only)

---

## 📡 Endpoints

### 1. Tournament Payments Inspection

```
GET /api/admin/tournaments/<tournament_id>/payments/
```

**Description**: List all payment verification statuses for a tournament.

**URL Parameters**:
- `tournament_id` (int, required) - Tournament ID

**Query Parameters**:
- `status` (string, optional) - Filter by payment status
  - Values: `pending`, `submitted`, `verified`, `rejected`, `refunded`
  - Example: `?status=verified`
- `limit` (int, optional) - Max results per page
  - Default: 100
  - Max: 500
  - Example: `?limit=50`
- `offset` (int, optional) - Pagination offset
  - Default: 0
  - Example: `?offset=100`

**Response Shape** (200 OK):

```json
{
  "tournament_id": 123,
  "payment_count": 50,
  "status_breakdown": {
    "pending": 5,
    "submitted": 10,
    "verified": 30,
    "rejected": 3,
    "refunded": 2
  },
  "pagination": {
    "limit": 100,
    "offset": 0,
    "total": 50,
    "has_more": false
  },
  "payments": [
    {
      "payment_id": 456,
      "registration_id": 789,
      "payment_method": "bkash",
      "amount": "500.00",
      "status": "verified",
      "transaction_id": "TXN123456",
      "reference_number": "REF789",
      "submitted_at": "2025-01-15T10:30:00Z",
      "verified_at": "2025-01-15T11:00:00Z",
      "verified_by_id": 1,
      "file_type": "IMAGE",
      "has_payment_proof": true
    }
  ]
}
```

**Response Fields** (IDs only, no PII):

| Field | Type | Description |
|-------|------|-------------|
| `payment_id` | int | Payment record ID |
| `registration_id` | int | Associated registration ID |
| `payment_method` | string | Payment method (bkash, nagad, rocket, bank, deltacoin) |
| `amount` | string | Payment amount in BDT (decimal as string) |
| `status` | string | Payment status (pending, submitted, verified, rejected, refunded) |
| `transaction_id` | string | Transaction ID from payment provider |
| `reference_number` | string | Payment reference number from receipt |
| `submitted_at` | datetime | When payment proof was submitted (ISO 8601) |
| `verified_at` | datetime | When payment was verified/rejected (ISO 8601, nullable) |
| `verified_by_id` | int | User ID who verified/rejected payment (nullable) |
| `file_type` | string | Type of uploaded proof (IMAGE, PDF, empty string) |
| `has_payment_proof` | bool | Whether payment proof file exists |

**Error Responses**:
- `401 Unauthorized` - User not authenticated
- `403 Forbidden` - User not staff
- `404 Not Found` - Tournament not found

**Example Requests**:

```bash
# All payments for tournament 123
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/payments/

# Verified payments only, paginated
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/payments/?status=verified&limit=50&offset=0

# Pending payments (need verification)
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/payments/?status=submitted
```

**Use Cases**:
- Monitor payment verification queue
- Identify stuck/rejected payments
- Audit payment processing times
- Support investigations (using payment_id/registration_id)

---

### 2. Tournament Matches Inspection

```
GET /api/admin/tournaments/<tournament_id>/matches/
```

**Description**: List all match states and winner tracking for a tournament.

**URL Parameters**:
- `tournament_id` (int, required) - Tournament ID

**Query Parameters**:
- `state` (string, optional) - Filter by match state
  - Values: `scheduled`, `check_in`, `ready`, `live`, `pending_result`, `completed`, `disputed`, `forfeit`, `cancelled`
  - Example: `?state=completed`
- `round` (int, optional) - Filter by round number
  - Example: `?round=1`
- `limit` (int, optional) - Max results per page
  - Default: 100
  - Max: 500
- `offset` (int, optional) - Pagination offset
  - Default: 0

**Response Shape** (200 OK):

```json
{
  "tournament_id": 123,
  "match_count": 15,
  "state_breakdown": {
    "scheduled": 5,
    "check_in": 2,
    "ready": 1,
    "live": 3,
    "pending_result": 1,
    "completed": 2,
    "disputed": 1,
    "forfeit": 0,
    "cancelled": 0
  },
  "pagination": {
    "limit": 100,
    "offset": 0,
    "total": 15,
    "has_more": false
  },
  "matches": [
    {
      "match_id": 789,
      "round_number": 1,
      "match_number": 2,
      "state": "completed",
      "bracket_id": 456,
      "participant1_id": 101,
      "participant2_id": 102,
      "participant1_score": 13,
      "participant2_score": 7,
      "winner_id": 101,
      "loser_id": 102,
      "scheduled_time": "2025-01-15T14:00:00Z",
      "started_at": "2025-01-15T14:05:00Z",
      "completed_at": "2025-01-15T15:30:00Z",
      "participant1_checked_in": true,
      "participant2_checked_in": true,
      "has_disputes": true,
      "dispute_count": 1
    }
  ]
}
```

**Response Fields** (IDs only, no PII):

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | int | Match record ID |
| `round_number` | int | Bracket round number (1-indexed) |
| `match_number` | int | Match number within round |
| `state` | string | Match state (scheduled, check_in, ready, live, pending_result, completed, disputed, forfeit, cancelled) |
| `bracket_id` | int | Bracket ID (nullable) |
| `participant1_id` | int | Participant 1 ID (Team or User ID, nullable) |
| `participant2_id` | int | Participant 2 ID (Team or User ID, nullable) |
| `participant1_score` | int | Participant 1 score (nullable) |
| `participant2_score` | int | Participant 2 score (nullable) |
| `winner_id` | int | Winner ID (nullable, set when match completed) |
| `loser_id` | int | Loser ID (nullable, set when match completed) |
| `scheduled_time` | datetime | Scheduled match start time (ISO 8601, nullable) |
| `started_at` | datetime | Actual match start time (ISO 8601, nullable) |
| `completed_at` | datetime | Match completion time (ISO 8601, nullable) |
| `participant1_checked_in` | bool | Whether participant 1 checked in |
| `participant2_checked_in` | bool | Whether participant 2 checked in |
| `has_disputes` | bool | Whether match has any disputes |
| `dispute_count` | int | Number of disputes for this match |

**Error Responses**:
- `401 Unauthorized` - User not authenticated
- `403 Forbidden` - User not staff
- `404 Not Found` - Tournament not found

**Example Requests**:

```bash
# All matches for tournament 123
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/matches/

# Completed matches in round 1
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/matches/?state=completed&round=1

# Live matches (ongoing right now)
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/matches/?state=live

# Disputed matches (need resolution)
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/matches/?state=disputed
```

**Use Cases**:
- Monitor match progression in real-time
- Identify stuck matches (scheduled but not started)
- Verify winner determination (winner_id/loser_id)
- Investigate disputes (cross-reference with disputes endpoint)
- Audit match timing (scheduled_time vs started_at vs completed_at)

---

### 3. Tournament Disputes Inspection

```
GET /api/admin/tournaments/<tournament_id>/disputes/
```

**Description**: List all dispute resolution tracking for a tournament.

**URL Parameters**:
- `tournament_id` (int, required) - Tournament ID

**Query Parameters**:
- `status` (string, optional) - Filter by dispute status
  - Values: `open`, `under_review`, `resolved`, `escalated`
  - Example: `?status=open`
- `reason_code` (string, optional) - Filter by dispute reason
  - Values: `SCORE_MISMATCH`, `NO_SHOW`, `CHEATING`, `TECHNICAL_ISSUE`, `OTHER`
  - Example: `?reason_code=SCORE_MISMATCH`
- `limit` (int, optional) - Max results per page
  - Default: 100
  - Max: 500
- `offset` (int, optional) - Pagination offset
  - Default: 0

**Response Shape** (200 OK):

```json
{
  "tournament_id": 123,
  "dispute_count": 8,
  "status_breakdown": {
    "open": 2,
    "under_review": 3,
    "resolved": 2,
    "escalated": 1
  },
  "pagination": {
    "limit": 100,
    "offset": 0,
    "total": 8,
    "has_more": false
  },
  "disputes": [
    {
      "dispute_id": 999,
      "match_id": 789,
      "round_number": 2,
      "match_number": 1,
      "reason_code": "SCORE_MISMATCH",
      "status": "resolved",
      "initiated_by_id": 101,
      "resolved_by_id": 1,
      "final_participant1_score": 13,
      "final_participant2_score": 10,
      "has_evidence_screenshot": true,
      "has_evidence_video": false,
      "created_at": "2025-01-15T15:45:00Z",
      "resolved_at": "2025-01-15T16:30:00Z"
    }
  ]
}
```

**Response Fields** (IDs only, no PII):

| Field | Type | Description |
|-------|------|-------------|
| `dispute_id` | int | Dispute record ID |
| `match_id` | int | Associated match ID |
| `round_number` | int | Match round number (for context) |
| `match_number` | int | Match number within round (for context) |
| `reason_code` | string | Dispute reason enum (SCORE_MISMATCH, NO_SHOW, CHEATING, TECHNICAL_ISSUE, OTHER) |
| `status` | string | Dispute status (open, under_review, resolved, escalated) |
| `initiated_by_id` | int | User ID who initiated dispute |
| `resolved_by_id` | int | User ID who resolved dispute (nullable) |
| `final_participant1_score` | int | Final score for participant 1 after resolution (nullable) |
| `final_participant2_score` | int | Final score for participant 2 after resolution (nullable) |
| `has_evidence_screenshot` | bool | Whether screenshot evidence exists |
| `has_evidence_video` | bool | Whether video evidence URL exists |
| `created_at` | datetime | When dispute was created (ISO 8601) |
| `resolved_at` | datetime | When dispute was resolved (ISO 8601, nullable) |

**Error Responses**:
- `401 Unauthorized` - User not authenticated
- `403 Forbidden` - User not staff
- `404 Not Found` - Tournament not found

**Example Requests**:

```bash
# All disputes for tournament 123
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/disputes/

# Open disputes (need resolution)
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/disputes/?status=open

# Score mismatch disputes
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/disputes/?reason_code=SCORE_MISMATCH

# Escalated disputes (need admin attention)
curl -H "Authorization: Token YOUR_TOKEN" \
  https://deltacrown.gg/api/admin/tournaments/123/disputes/?status=escalated
```

**Use Cases**:
- Monitor dispute resolution queue
- Identify unresolved disputes (status=open)
- Investigate cheating accusations
- Audit resolution times (created_at vs resolved_at)
- Track escalations (status=escalated)

---

## 🛡️ PII Compliance

All endpoints return **IDs-only responses** with **no personally identifiable information**:

**✅ What's Included** (IDs-only discipline):
- IDs (payment_id, registration_id, match_id, dispute_id, participant_id, team_id, tournament_id)
- Enums (status, state, reason_code, payment_method) - **Note: reason_code uses uppercase (SCORE_MISMATCH, NO_SHOW, etc.)**
- Integers (scores, counts)
- Timestamps (ISO 8601 datetimes)
- Booleans (flags)
- Transaction/reference numbers (no personal data)

**❌ What's Excluded**:
- User emails
- User display names/usernames
- Team names
- Phone numbers
- Payment account numbers
- IP addresses
- Detailed descriptions/notes (may contain PII)

**Name Resolution**: Clients resolve IDs via `/api/profiles/`, `/api/teams/`, `/api/tournaments/{id}/metadata/`

**Rationale**:
- IDs allow cross-referencing with other systems (CRM, admin panel) without exposing PII
- Staff can investigate issues using IDs without violating GDPR/privacy
- Responses are safe to cache, log, and share between staff
- Minimal data exposure reduces security risk

**To Get PII**:
- Use IDs to look up details in Django Admin or internal CRM
- Example: `dispute_id=999` → Django Admin → view full description, user details

---

## 🧪 Testing

All endpoints are **read-only** and safe to test in production:

**Test Coverage**:
- Unit tests: Basic response shape validation (minimal, per Section 9 requirements)
- Integration tests: None (endpoints use existing models, no new business logic)
- Manual testing: Use curl/Postman with staff token

**Sample Tests** (if needed, keep extremely thin):

```python
# tests/admin/test_tournament_ops_api.py
import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
def test_tournament_payments_requires_staff(api_client, tournament):
    """Verify staff-only access"""
    url = reverse('admin_api:tournament_payments', args=[tournament.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_tournament_payments_returns_shape(admin_api_client, tournament):
    """Verify response shape"""
    url = reverse('admin_api:tournament_payments', args=[tournament.id])
    response = admin_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'tournament_id' in response.data
    assert 'status_breakdown' in response.data
    assert 'payments' in response.data
```

**Manual Testing**:

```bash
# 1. Get staff user token
curl -X POST https://deltacrown.gg/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "YOUR_PASSWORD"}'
# Response: {"token": "abc123..."}

# 2. Test payments endpoint
curl -H "Authorization: Token abc123..." \
  https://deltacrown.gg/api/admin/tournaments/1/payments/ | jq

# 3. Test matches endpoint
curl -H "Authorization: Token abc123..." \
  https://deltacrown.gg/api/admin/tournaments/1/matches/?state=live | jq

# 4. Test disputes endpoint
curl -H "Authorization: Token abc123..." \
  https://deltacrown.gg/api/admin/tournaments/1/disputes/?status=open | jq
```

---

## 🚨 Troubleshooting

### Issue: 403 Forbidden
**Cause**: User is authenticated but not staff  
**Fix**: Ensure user has `is_staff=True` in Django Admin

### Issue: 404 Not Found
**Cause**: Tournament ID doesn't exist  
**Fix**: Verify tournament ID with `Tournament.objects.filter(id=X).exists()`

### Issue: Empty Results
**Cause**: No matching data (e.g., no payments, no matches, no disputes)  
**Fix**: Check `payment_count`, `match_count`, `dispute_count` in response

### Issue: Pagination Not Working
**Cause**: Incorrect limit/offset values  
**Fix**: Use `pagination.total` and `pagination.has_more` to navigate pages

---

## 📊 Monitoring

**Key Metrics to Track**:
- Request count per endpoint (CloudWatch/Prometheus)
- Response times (p50, p95, p99)
- Error rates (401/403/404)
- Top tournaments by request count

**Example Prometheus Queries**:

```promql
# Request rate (requests per second)
rate(http_requests_total{path=~"/api/admin/tournaments/.*/payments/"}[5m])

# Error rate (4xx/5xx)
sum(rate(http_requests_total{path=~"/api/admin/tournaments/.*", status=~"4.."}[5m]))

# Response time p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{path=~"/api/admin/tournaments/.*"}[5m]))
```

**Alerting Rules**:
- Alert if error rate > 5% for 5 minutes
- Alert if p95 response time > 2 seconds
- Alert if tournament not found (404) rate > 10% (may indicate bad tournament IDs)

---

## 🔗 Related Documentation

- [Admin Leaderboards API](./leaderboards.md) - Admin leaderboards debug endpoints
- [Phase E PR Description](../../PHASE_E_PR_DESCRIPTION.md) - Full Phase E context
- [Phase E Runbook](../runbooks/phase_e_leaderboards.md) - Operational procedures

---

## 📝 Changelog

### Phase E Section 9 (January 2025)
- Initial implementation of Tournament Operations API
- 3 endpoints: payments, matches, disputes
- IDs-only responses (PII compliance)
- Staff-only read-only access
- Pagination support (limit/offset)
- Status/state/reason filtering
