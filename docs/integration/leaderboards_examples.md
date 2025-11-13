# Leaderboards API Integration Examples

**Version**: 1.0  
**Last Updated**: January 26, 2025  
**Status**: Production Ready (Promoted to 25% traffic after T+24h canary)  
**Audience**: Frontend developers, API consumers, integration partners  

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Public API Examples](#public-api-examples)
   - [Tournament Leaderboard](#1-tournament-leaderboard)
   - [Player History](#2-player-history-across-tournaments)
   - [Scoped Queries](#3-scoped-leaderboard-queries)
4. [Admin API Examples](#admin-api-examples)
   - [Leaderboard Inspection](#1-leaderboard-inspection)
   - [Cache Status](#2-cache-status-inspection)
   - [Cache Invalidation](#3-manual-cache-invalidation)
   - [Payment Tracking](#4-payment-verification-tracking)
   - [Match Tracking](#5-match-state-tracking)
   - [Dispute Tracking](#6-dispute-resolution-tracking)
5. [Error Scenarios & Feature Flags](#error-scenarios--feature-flags)
6. [Response Schema Reference](#response-schema-reference)
7. [Rate Limits & Best Practices](#rate-limits--best-practices)

---

## Overview

The DeltaCrown Leaderboards API provides **3 public endpoints** (authenticated) and **6 admin endpoints** (staff-only) for accessing tournament leaderboards, player histories, and operational insights.

**Key Features**:
- **3 leaderboard scopes**: tournament, season, all-time
- **Real-time score aggregation**: No dedicated leaderboard tables (V1), scores computed from Match model
- **5-step tie-breaker cascade**: points DESC → wins DESC → total_matches ASC → earliest_win ASC → participant_id ASC
- **Redis caching**: 5-minute TTL (flag-gated, default OFF)
- **IDs-only discipline**: All responses contain participant_id, team_id, tournament_id only (no display names, emails, usernames)
- **Name resolution**: Clients resolve IDs via `/api/profiles/`, `/api/teams/`, `/api/tournaments/{id}/metadata/`
- **Feature flag control**: Master switch + cache toggle + API toggle (all default OFF)
- **Prometheus metrics**: Request counts, cache hits/misses, latency (p50/p95/p99)

**Base URL**: `https://api.deltacrown.com`  
**API Version**: v1 (Phase E Leaderboards)

---

## Authentication

**All public endpoints require authentication.** Admin endpoints require **staff permissions**.

### Authentication Methods

1. **Session Authentication** (Cookie-based, for web frontend):
   ```http
   GET /api/tournaments/123/leaderboard/ HTTP/1.1
   Host: api.deltacrown.com
   Cookie: sessionid=abc123...
   ```

2. **Bearer Token** (JWT, for mobile apps/SPAs):
   ```http
   GET /api/tournaments/123/leaderboard/ HTTP/1.1
   Host: api.deltacrown.com
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

### Obtaining a Token

**POST** `/api/token/` (JWT token endpoint)

```bash
curl -X POST https://api.deltacrown.com/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "player123",
    "password": "securepassword"
  }'
```

**Response**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Use the `access` token as `Authorization: Bearer <token>` for subsequent requests. Tokens expire after 60 minutes (configurable). Refresh tokens are valid for 7 days.

---

## Public API Examples

### 1. Tournament Leaderboard

**GET** `/api/tournaments/{tournament_id}/leaderboard/`

Fetch the leaderboard for a specific tournament (tournament scope).

#### Request (cURL)

```bash
curl -X GET https://api.deltacrown.com/api/tournaments/123/leaderboard/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Response (200 OK)

```json
{
  "count": 150,
  "next": "https://api.deltacrown.com/api/tournaments/123/leaderboard/?page=2",
  "previous": null,
  "results": [
    {
      "rank": 1,
      "participant_id": 456,
      "team_id": 789,
      "points": 2450,
      "wins": 12,
      "losses": 1,
      "last_updated_at": "2025-01-26T14:35:22Z"
    },
    {
      "rank": 2,
      "participant_id": 457,
      "team_id": 790,
      "points": 2400,
      "wins": 11,
      "losses": 2,
      "last_updated_at": "2025-01-26T14:30:15Z"
    },
    {
      "rank": 3,
      "participant_id": 458,
      "team_id": null,
      "points": 2200,
      "wins": 10,
      "losses": 3,
      "last_updated_at": "2025-01-26T14:28:03Z"
    }
  ]
}
```

#### Query Parameters

- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Number of results per page (default: 50, max: 200)

#### Response Fields (IDs-Only)

- **rank**: Position in leaderboard (1-based, tied participants share rank)
- **participant_id**: Unique participant identifier (Registration ID)
- **team_id**: Team identifier (null for solo participants)
- **points**: Total points earned
- **wins**: Number of wins
- **losses**: Number of losses
- **last_updated_at**: ISO 8601 timestamp of last leaderboard update (UTC)

**Name Resolution**: Resolve IDs to display names via:
- Participant names: `GET /api/profiles/{participant_id}/` → `display_name`
- Team names: `GET /api/teams/{team_id}/` → `name`
- Tournament metadata: `GET /api/tournaments/{tournament_id}/metadata/` → `name`, `game_code`, etc.

---

### 2. Player History Across Tournaments

**GET** `/api/tournaments/leaderboards/participant/{participant_id}/history/`

Fetch a participant's leaderboard history across all tournaments they've competed in.

#### Request (cURL)

```bash
curl -X GET https://api.deltacrown.com/api/tournaments/leaderboards/participant/456/history/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Response (200 OK)

```json
{
  "count": 8,
  "next": null,
  "previous": null,
  "results": [
    {
      "tournament_id": 123,
      "rank": 1,
      "points": 2450,
      "wins": 12,
      "losses": 1,01-20T18:00:00Z"
    },
    {
      "tournament_id": 98,
      "rank": 3,
      "points": 1850,
      "wins": 9,
      "losses": 4,
      "tournament_ended_at": "2024-12-15T16:30:00Z"
    }
  ]
}
```

#### Query Parameters

- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 50, max: 200)
- `tournament_status` (optional): Filter by tournament status (e.g., `CONCLUDED`)

#### Response Fields (IDs-Only)

- **tournament_id**: Tournament identifier (resolve name via `/api/tournaments/{id}/metadata/`)
- **rank**: Final rank in that tournament
- **points**: Total points earned
- **wins/losses**: Match record
- **tournament_ended_at**: ISO 8601 timestamp when tournament concluded (UTC)

---

### 3. Scoped Leaderboard Queries

**GET** `/api/tournaments/leaderboards/scoped/`

Query leaderboards by scope: tournament, season, or all-time.

#### Example: Season Leaderboard

```bash
curl -X GET 'https://api.deltacrown.com/api/tournaments/leaderboards/scoped/?scope=season&season=2025-spring' \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Response (200 OK)

```json
{
  "scope": "season",
  "season": "2025-spring",
  "count": 2450,
  "next": "https://api.deltacrown.com/api/tournaments/leaderboards/scoped/?scope=season&season=2025-spring&page=2",
  "previous": null,
  "results": [
    {
      "rank": 1,
      "participant_id": 456,
      "team_id": 789,
      "points": 8750,
      "wins": 45,
      "losses": 5,
      "tournaments_played": 6,
      "last_updated_at": "2025-01-26T14:35:22Z"
    }
  ]
}
```

#### Example: All-Time Leaderboard

```bash
curl -X GET 'https://api.deltacrown.com/api/tournaments/leaderboards/scoped/?scope=all_time' \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Query Parameters

- **scope** (required): `tournament`, `season`, or `all_time`
- **tournament_id** (required if scope=tournament): Tournament identifier
- **season** (required if scope=season): Season identifier (e.g., `2025-spring`, `2024-fall`)
- `page`, `page_size`: Pagination controls

#### Response Fields (Season/All-Time)

Same as tournament leaderboard, plus:
- **tournaments_played**: Number of tournaments participated in during the season/all-time

---

## Admin API Examples

**All admin endpoints require staff permissions** (`IsAdminUser` in Django). Attempts without staff access return `403 Forbidden`.

### 1. Leaderboard Inspection

**GET** `/api/admin/leaderboards/inspect/{tournament_id}/`

Inspect raw aggregation data for debugging score discrepancies.

#### Request (cURL)

```bash
curl -X GET https://api.deltacrown.com/api/admin/leaderboards/inspect/123/ \
  -H "Authorization: Bearer <staff_token>"
```

#### Response (200 OK)

```json
{
  "tournament_id": 123,
  "flag_states": {
    "LEADERBOARDS_COMPUTE_ENABLED": true,
    "LEADERBOARDS_CACHE_ENABLED": true,
    "LEADERBOARDS_API_ENABLED": true
  },
  "raw_aggregations": [
    {
      "participant_id": 456,
      "points": 2450,
      "wins": 12,
      "losses": 1,
      "total_matches": 13,
      "match_ids": [1001, 1002, 1003, "..."],
      "earliest_win": "2025-01-15T10:00:00Z"
    }
  ],
  "cache_metadata": {
    "cached": true,
    "cache_key": "leaderboard:tournament:123",
    "ttl_seconds": 287,
    "last_refresh": "2025-01-26T14:35:22Z"
  },
  "computed_at": "2025-01-26T14:40:15Z"
}
```

#### Use Cases

- Debug score discrepancies: Compare raw aggregations vs displayed leaderboard
- Verify flag states: Check if compute/cache/API flags are enabled
- Investigate cache issues: See if data is cached and TTL remaining

---

### 2. Cache Status Inspection

**GET** `/api/admin/leaderboards/cache/status/`

Inspect cache hit rates, eviction counts, and TTL distribution.

#### Request (cURL)

```bash
curl -X GET https://api.deltacrown.com/api/admin/leaderboards/cache/status/ \
  -H "Authorization: Bearer <staff_token>"
```

#### Response (200 OK)

```json
{
  "cache_enabled": true,
  "redis_connected": true,
  "cache_keys_count": 87,
  "metrics": {
    "cache_hit_ratio": 0.92,
    "total_requests": 1450,
    "cache_hits": 1334,
    "cache_misses": 116,
    "evictions_count": 5
  },
  "ttl_distribution": {
    "expired_count": 2,
    "0_60_seconds": 15,
    "60_180_seconds": 48,
    "180_300_seconds": 22
  },
  "checked_at": "2025-01-26T14:40:30Z"
}
```

#### Use Cases

- Monitor cache health: Check hit ratio (target: ≥90%)
- Diagnose cache issues: See if Redis is connected, keys present
- Optimize TTL: Review TTL distribution for tuning

---

### 3. Manual Cache Invalidation

**POST** `/api/admin/leaderboards/cache/invalidate/`

Manually invalidate cached leaderboards (useful after fixing score bugs).

#### Request (cURL - Invalidate Single Tournament)

```bash
curl -X POST https://api.deltacrown.com/api/admin/leaderboards/cache/invalidate/ \
  -H "Authorization: Bearer <staff_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tournament_id": 123
  }'
```

#### Response (200 OK)

```json
{
  "invalidated_count": 1,
  "cache_keys_removed": ["leaderboard:tournament:123"],
  "invalidated_at": "2025-01-26T14:45:00Z"
}
```

#### Request (cURL - Invalidate All Caches)

```bash
curl -X POST https://api.deltacrown.com/api/admin/leaderboards/cache/invalidate/ \
  -H "Authorization: Bearer <staff_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "all"
  }'
```

#### Response (200 OK)

```json
{
  "invalidated_count": 87,
  "cache_keys_removed": ["leaderboard:tournament:123", "leaderboard:season:2025-spring", "..."],
  "invalidated_at": "2025-01-26T14:46:15Z"
}
```

#### Request Body Parameters

- **tournament_id** (optional): Invalidate specific tournament (mutually exclusive with `scope`)
- **scope** (optional): Invalidate by scope (`tournament`, `season`, `all_time`, or `all`)

---

### 4. Payment Verification Tracking

**GET** `/api/admin/tournaments/{tournament_id}/payments/`

Track payment verification status for a tournament (bulk monitoring, not detailed investigation).

#### Request (cURL)

```bash
curl -X GET https://api.deltacrown.com/api/admin/tournaments/123/payments/ \
  -H "Authorization: Bearer <staff_token>"
```

#### Response (200 OK)

```json
{
  "tournament_id": 123,
  "status_breakdown": {
    "PENDING": 12,
    "VERIFIED": 138,
    "REJECTED": 5
  },
  "payments": [
    {
      "payment_id": 4567,
      "participant_id": 456,
      "status": "PENDING",
      "submitted_at": "2025-01-25T10:30:00Z"
    },
    {
      "payment_id": 4568,
      "participant_id": 457,
      "status": "VERIFIED",
      "verified_at": "2025-01-24T14:15:00Z"
    }
  ],
  "count": 155,
  "next": "https://api.deltacrown.com/api/admin/tournaments/123/payments/?page=2",
  "previous": null
}
```

#### Query Parameters

- `status` (optional): Filter by status (`PENDING`, `VERIFIED`, `REJECTED`)
- `page`, `limit`: Pagination controls

#### PII Compliance Note

**No PII exposed**: Responses contain `payment_id`, `participant_id`, `status` only. No emails, usernames, or payment proof URLs. For full details (payment proof images, rejection reasons), use Django admin interface.

---

### 5. Match State Tracking

**GET** `/api/admin/tournaments/{tournament_id}/matches/`

Track match state distribution for tournament health monitoring.

#### Request (cURL)

```bash
curl -X GET https://api.deltacrown.com/api/admin/tournaments/123/matches/ \
  -H "Authorization: Bearer <staff_token>"
```

#### Response (200 OK)

```json
{
  "tournament_id": 123,
  "state_breakdown": {
    "SCHEDULED": 8,
    "LIVE": 2,
    "COMPLETED": 142,
    "DISPUTED": 3
  },
  "matches": [
    {
      "match_id": 8901,
      "state": "DISPUTED",
      "scheduled_time": "2025-01-26T16:00:00Z",
      "dispute_reason_code": "SCORE_MISMATCH"
    },
    {
      "match_id": 8902,
      "state": "LIVE",
      "scheduled_time": "2025-01-26T14:30:00Z"
    }
  ],
  "count": 155,
  "next": null,
  "previous": null
}
```

#### Query Parameters

- `state` (optional): Filter by state (`SCHEDULED`, `LIVE`, `COMPLETED`, `DISPUTED`)
- `page`, `limit`: Pagination controls

---

### 6. Dispute Resolution Tracking

**GET** `/api/admin/tournaments/{tournament_id}/disputes/`

Track dispute resolution status for quick triage.

#### Request (cURL)

```bash
curl -X GET 'https://api.deltacrown.com/api/admin/tournaments/123/disputes/?status=OPEN' \
  -H "Authorization: Bearer <staff_token>"
```

#### Response (200 OK)

```json
{
  "tournament_id": 123,
  "status_breakdown": {
    "OPEN": 3,
    "RESOLVED": 15,
    "REJECTED": 2
  },
  "disputes": [
    {
      "dispute_id": 5678,
      "match_id": 8901,
      "status": "OPEN",
      "reason_code": "SCORE_MISMATCH",
      "created_at": "2025-01-26T14:35:00Z"
    }
  ],
  "count": 20,
  "next": null,
  "previous": null
}
```

#### Query Parameters

- `status` (optional): Filter by status (`OPEN`, `RESOLVED`, `REJECTED`)
- `reason_code` (optional): Filter by reason enum (`SCORE_MISMATCH`, `NO_SHOW`, `CHEATING`, `TECHNICAL_ISSUE`, `OTHER`)
- `page`, `limit`: Pagination controls

---

## Error Scenarios & Feature Flags

### Common Error Responses

#### 1. Feature Flag Disabled

**Scenario**: `LEADERBOARDS_COMPUTE_ENABLED=False` or `LEADERBOARDS_API_ENABLED=False`

**Request**:
```bash
curl -X GET https://api.deltacrown.com/api/tournaments/123/leaderboard/ \
  -H "Authorization: Bearer <token>"
```

**Response (503 Service Unavailable)**:
```json
{
  "detail": "Leaderboards API is currently unavailable. Please try again later.",
  "error_code": "FEATURE_DISABLED",
  "retry_after_seconds": 300
}
```

#### 2. Tournament Not Found

**Request**:
```bash
curl -X GET https://api.deltacrown.com/api/tournaments/99999/leaderboard/ \
  -H "Authorization: Bearer <token>"
```

**Response (404 Not Found)**:
```json
{
  "detail": "Tournament with id 99999 not found.",
  "error_code": "TOURNAMENT_NOT_FOUND"
}
```

#### 3. Authentication Required

**Request** (missing Authorization header):
```bash
curl -X GET https://api.deltacrown.com/api/tournaments/123/leaderboard/
```

**Response (401 Unauthorized)**:
```json
{
  "detail": "Authentication credentials were not provided.",
  "error_code": "NOT_AUTHENTICATED"
}
```

#### 4. Insufficient Permissions (Admin Endpoints)

**Request** (non-staff user accessing admin endpoint):
```bash
curl -X GET https://api.deltacrown.com/api/admin/leaderboards/inspect/123/ \
  -H "Authorization: Bearer <non_staff_token>"
```

**Response (403 Forbidden)**:
```json
{
  "detail": "You do not have permission to perform this action.",
  "error_code": "PERMISSION_DENIED"
}
```

#### 5. Rate Limit Exceeded

**Request** (100+ requests in 1 hour from same user):
```bash
curl -X GET https://api.deltacrown.com/api/tournaments/123/leaderboard/ \
  -H "Authorization: Bearer <token>"
```

**Response (429 Too Many Requests)**:
```json
{
  "detail": "Request was throttled. Expected available in 3600 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after_seconds": 3600
}
```

### Feature Flag States

The Leaderboards API behavior is controlled by 3 feature flags:

| Flag | Default | Effect When OFF | Effect When ON |
|------|---------|-----------------|----------------|
| `LEADERBOARDS_COMPUTE_ENABLED` | `False` | All leaderboard endpoints return 503 | Leaderboard computation enabled |
| `LEADERBOARDS_CACHE_ENABLED` | `False` | No caching (live queries only) | Redis caching with 5-minute TTL |
| `LEADERBOARDS_API_ENABLED` | `False` | All public API endpoints return 503 | Public APIs accessible |

**Rollback Procedure**: Set all 3 flags to `False` in environment config, restart application (no code deployment needed).

---

## Response Schema Reference

### LeaderboardEntryDTO (IDs-Only)

```json
{
  "rank": 1,                          // Integer (1-based, tied participants share rank)
  "participant_id": 456,              // Integer (Registration ID, resolve via /api/profiles/{id}/)
  "team_id": 789,                     // Integer or null (Team ID, null for solo, resolve via /api/teams/{id}/)
  "points": 2450,                     // Integer (total points earned)
  "wins": 12,                         // Integer (number of wins)
  "losses": 1,                        // Integer (number of losses)
  "last_updated_at": "2025-01-26T14:35:22Z"  // ISO 8601 UTC timestamp
}
```

### Pagination Envelope (DRF Standard)

```json
{
  "count": 150,                       // Integer (total results)
  "next": "https://...",              // String or null (next page URL)
  "previous": null,                   // String or null (previous page URL)
  "results": [/* LeaderboardEntryDTO array */]
}
```

---

## Rate Limits & Best Practices

### Rate Limits

| Endpoint Type | Limit | Window | Scope |
|---------------|-------|--------|-------|
| Public API (authenticated users) | 100 requests | 1 hour | Per user |
| Admin API (staff users) | 100 requests | 1 hour | Per user |
| Cache invalidation (admin) | 10 requests | 1 hour | Per user |

**Headers on Rate Limit**:
```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1706280000
Retry-After: 3600
```

### Best Practices

1. **Cache Responses Locally**:
   - Public leaderboards update every 5 minutes (when caching enabled)
   - Cache responses in your frontend for 1-2 minutes to reduce API calls
   - Example (JavaScript):
     ```javascript
     const CACHE_TTL_MS = 120000; // 2 minutes
     let leaderboardCache = { data: null, timestamp: 0 };
     
     async function fetchLeaderboard(tournamentId) {
       const now = Date.now();
       if (leaderboardCache.data && (now - leaderboardCache.timestamp) < CACHE_TTL_MS) {
         return leaderboardCache.data; // Return cached data
       }
       
       const response = await fetch(`https://api.deltacrown.com/api/tournaments/${tournamentId}/leaderboard/`, {
         headers: { 'Authorization': `Bearer ${accessToken}` }
       });
       const data = await response.json();
       
       leaderboardCache = { data, timestamp: now };
       return data;
     }
     ```

2. **Handle Feature Flag Outages Gracefully**:
   - Check for `503 Service Unavailable` responses
   - Display user-friendly message: "Leaderboards temporarily unavailable"
   - Retry with exponential backoff: 5s → 10s → 30s

3. **Use Pagination Efficiently**:
   - Default page size: 50 entries (adjust with `page_size` param)
   - Max page size: 200 entries (requests for >200 return 400 Bad Request)
   - Load "Top 10" initially, offer "Load More" button for full leaderboard

4. **IDs-Only Discipline (PII Compliance)**:
   - All responses contain participant_id, team_id, tournament_id only
   - No display names, usernames, or emails in API responses
   - Resolve IDs to names via `/api/profiles/`, `/api/teams/`, `/api/tournaments/{id}/metadata/`
   - Store only IDs locally (names may change, IDs are stable)
   - Cache resolved names client-side (1-2 minute TTL) to reduce API calls

5. **Monitor Your Integration**:
   - Log API errors with timestamps and tournament IDs
   - Track rate limit headers to avoid throttling
   - Set up alerts for persistent 503 errors (indicates backend issues)

6. **Admin API Usage**:
   - Use admin endpoints for **bulk monitoring**, not detailed investigation
   - For full details (payment proof images, match lobby info), use Django admin interface
   - Always check `flag_states` in inspection responses to verify feature flag status

---

## Additional Resources

- **Runbook**: [docs/runbooks/phase_e_leaderboards.md](../runbooks/phase_e_leaderboards.md) - Operational procedures for rollback, troubleshooting
- **Architecture Docs**: [docs/leaderboards/README.md](../leaderboards/README.md) - Service layer design, observability, metrics
- **Admin API Docs**:
  - [docs/admin/leaderboards.md](../admin/leaderboards.md) - Leaderboard debug endpoints
  - [docs/admin/tournament_ops.md](../admin/tournament_ops.md) - Payment/match/dispute tracking
- **Metrics Dashboard**: [Prometheus/Grafana dashboards](../runbooks/phase_e_leaderboards.md#section-4-observability) - Query examples for monitoring

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-26 | Initial release (Phase E Leaderboards V1) |

---

**Questions or Issues?**

- **Technical Support**: support@deltacrown.com
- **API Issues**: File a ticket in [DeltaCrown Support Portal](https://support.deltacrown.com)
- **Feature Requests**: Contact your DeltaCrown account manager

---

**End of Integration Examples Document**
