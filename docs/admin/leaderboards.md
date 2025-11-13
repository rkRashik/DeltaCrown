# Admin Leaderboards API - Operator Guide

## Overview

Staff-only endpoints for leaderboard inspection with debug metadata. All responses are **PII-free** (IDs + aggregates only).

### Endpoints

1. `GET /api/admin/leaderboards/tournaments/{tournament_id}/` - Tournament leaderboard with cache debug info
2. `GET /api/admin/leaderboards/snapshots/{snapshot_id}/` - Snapshot metadata
3. `GET /api/admin/leaderboards/scoped/{scope}/` - Seasonal/all-time leaderboard with debug info

### Permissions

All endpoints use `IsAdminUser` permission:
- Requires `is_staff=True` or `is_superuser=True`
- Only allows `GET`, `HEAD`, `OPTIONS` methods (read-only)

### PII Compliance

All responses contain **IDs + aggregates only** (IDs-only discipline):
- ✅ `participant_id`, `team_id`, `tournament_id`
- ✅ `points`, `wins`, `losses`, `rank`
- ❌ No display names, usernames, emails, full names, IP addresses
- ✅ Clients resolve IDs via `/api/profiles/`, `/api/teams/`, `/api/tournaments/{id}/metadata/`

---

## Endpoint 1: Tournament Leaderboard (Debug)

**Endpoint**: `GET /api/admin/leaderboards/tournaments/{tournament_id}/`

**Auth**: Admin/Staff only

**Purpose**: Inspect tournament leaderboard with cache metadata for debugging.

### Request

```bash
curl -H "Authorization: Token <admin_token>" \
  http://localhost:8000/api/admin/leaderboards/tournaments/501/
```

### Response (200 OK)

```json
{
  "tournament_id": 501,
  "source": "cache",
  "as_of": "2025-11-13T14:30:00Z",
  "entries": [
    {
      "rank": 1,
      "player_id": 123,
      "team_id": 45,
      "points": 3000,
      "wins": 15,
      "losses": 2,
      "win_rate": 88.24,
      "last_updated": "2025-11-13T14:25:00Z"
    },
    {
      "rank": 2,
      "player_id": 456,
      "team_id": 67,
      "points": 2800,
      "wins": 14,
      "losses": 3,
      "win_rate": 82.35,
      "last_updated": "2025-11-13T14:25:00Z"
    }
  ],
  "debug": {
    "cache_key": "lb:tournament:501",
    "cache_ttl_seconds": 285,
    "cache_hit": true,
    "computation_enabled": true,
    "cache_enabled": true,
    "api_enabled": true,
    "entry_count": 16,
    "query_time_ms": 12.5
  }
}
```

### Debug Fields

- `source`: Where data came from
  - `cache`: Redis cache hit
  - `live`: Fresh DB query (cache disabled or miss)
  - `snapshot`: Historical snapshot
  - `disabled`: `LEADERBOARDS_COMPUTE_ENABLED=False`
- `cache_key`: Redis key used
- `cache_ttl_seconds`: Remaining TTL (null if cache disabled)
- `cache_hit`: Whether cache was hit
- `computation_enabled`: `LEADERBOARDS_COMPUTE_ENABLED` flag state
- `cache_enabled`: `LEADERBOARDS_CACHE_ENABLED` flag state
- `api_enabled`: `LEADERBOARDS_API_ENABLED` flag state
- `entry_count`: Number of entries returned
- `query_time_ms`: Query execution time

### Use Cases

1. **Verify cache behavior**: Check if cache is being hit/missed
2. **Debug empty leaderboards**: Check flag states in `debug` block
3. **Performance troubleshooting**: Monitor `query_time_ms`
4. **Cache TTL verification**: Check remaining TTL for cache entries

### Errors

- `403 Forbidden`: Not staff/admin
- `404 Not Found`: Tournament doesn't exist

---

## Endpoint 2: Snapshot Detail

**Endpoint**: `GET /api/admin/leaderboards/snapshots/{snapshot_id}/`

**Auth**: Admin/Staff only

**Purpose**: Get metadata for a historical snapshot.

### Request

```bash
curl -H "Authorization: Token <admin_token>" \
  http://localhost:8000/api/admin/leaderboards/snapshots/123/
```

### Response (200 OK)

```json
{
  "snapshot_id": 123,
  "date": "2025-11-13",
  "leaderboard_type": "season",
  "player_id": 456,
  "team_id": null,
  "rank": 5,
  "points": 2600,
  "created_at": "2025-11-13"
}
```

### Fields

- `snapshot_id`: Unique snapshot ID
- `date`: Snapshot date (UTC)
- `leaderboard_type`: Scope (`tournament`, `season`, `all_time`)
- `player_id`: Player ID (null if team leaderboard)
- `team_id`: Team ID (null if player leaderboard)
- `rank`: Rank at snapshot time
- `points`: Points at snapshot time
- `created_at`: Snapshot creation timestamp

### Use Cases

1. **Historical analysis**: Inspect past leaderboard states
2. **Audit trail**: Verify rank changes over time
3. **Debugging**: Check if snapshots are being created

### Errors

- `403 Forbidden`: Not staff/admin
- `404 Not Found`: Snapshot doesn't exist

---

## Endpoint 3: Scoped Leaderboard (Debug)

**Endpoint**: `GET /api/admin/leaderboards/scoped/{scope}/?game_code=valorant&season_id=2025_S1`

**Auth**: Admin/Staff only

**Purpose**: Inspect seasonal/all-time leaderboard with debug metadata.

### URL Parameters

- `scope`: Must be `season` or `all_time`

### Query Parameters

- `game_code`: Optional game filter (e.g., `valorant`, `cs2`, `lol`)
- `season_id`: **Required** for `scope=season` (e.g., `2025_S1`)

### Request Examples

**Season leaderboard (Valorant):**
```bash
curl -H "Authorization: Token <admin_token>" \
  "http://localhost:8000/api/admin/leaderboards/scoped/season/?season_id=2025_S1&game_code=valorant"
```

**All-time leaderboard (all games):**
```bash
curl -H "Authorization: Token <admin_token>" \
  http://localhost:8000/api/admin/leaderboards/scoped/all_time/
```

**All-time leaderboard (CS2 only):**
```bash
curl -H "Authorization: Token <admin_token>" \
  "http://localhost:8000/api/admin/leaderboards/scoped/all_time/?game_code=cs2"
```

### Response (200 OK)

```json
{
  "scope": "season",
  "season_id": "2025_S1",
  "game_code": "valorant",
  "entry_count": 50,
  "as_of": "2025-11-13T14:30:00Z",
  "entries": [
    {
      "rank": 1,
      "player_id": 789,
      "team_id": null,
      "points": 5000,
      "wins": 30,
      "losses": 5,
      "win_rate": 85.71,
      "last_updated": "2025-11-13T12:00:00Z"
    }
  ],
  "debug": {
    "cache_key": "lb:season:2025_S1:valorant",
    "cache_ttl_seconds": 3600,
    "cache_hit": false,
    "computation_enabled": true,
    "cache_enabled": true,
    "query_time_ms": 25.3
  }
}
```

### Debug Fields

Same as Endpoint 1, plus:
- `cache_key`: Redis key pattern for scoped leaderboard
- `cache_ttl_seconds`: 3600s (1h) for season, 86400s (24h) for all-time

### Use Cases

1. **Verify seasonal rankings**: Check if season data is being computed
2. **Debug cross-game leaderboards**: Test `game_code` filtering
3. **Cache performance**: Monitor cache hit rates for seasonal vs all-time

### Errors

- `400 Bad Request`: Invalid scope or missing `season_id`
- `403 Forbidden`: Not staff/admin

---

## Permission Model: IsStaffReadOnly

All admin leaderboard endpoints use the `IsAdminUser` permission class:

```python
from rest_framework.permissions import IsAdminUser

@api_view(['GET'])
@permission_classes([IsAdminUser])
def my_admin_view(request):
    ...
```

### Behavior

**Allows**:
- Authenticated users with `is_staff=True` or `is_superuser=True`
- Only `GET`, `HEAD`, `OPTIONS` methods

**Blocks**:
- Unauthenticated requests → `401 Unauthorized`
- Non-staff users → `403 Forbidden`
- `POST`, `PUT`, `PATCH`, `DELETE` methods → `403 Forbidden`

### Testing Permission

```bash
# Non-staff user (should fail with 403)
curl -H "Authorization: Token <regular_user_token>" \
  http://localhost:8000/api/admin/leaderboards/tournaments/501/

# Staff user (should succeed with 200)
curl -H "Authorization: Token <staff_token>" \
  http://localhost:8000/api/admin/leaderboards/tournaments/501/
```

---

## Debug Info: What It Tells You

### Cache Hit/Miss Analysis

**High cache hit rate (>90%):**
- ✅ Good performance
- ✅ Low DB load
- ✅ Cache TTL is appropriate

**Low cache hit rate (<70%):**
- ⚠️ Cache TTL may be too short
- ⚠️ High cache invalidation frequency
- ⚠️ Check if `LEADERBOARDS_CACHE_ENABLED=True`

### Query Time Thresholds

**Cache hit:**
- Good: <50ms
- Warning: 50-100ms
- Critical: >100ms (Redis latency issue)

**Cache miss:**
- Good: <200ms
- Warning: 200-500ms
- Critical: >500ms (DB performance issue)

### Flag State Debugging

If `entries` is empty, check `debug` block:

```json
{
  "debug": {
    "computation_enabled": false,  // ← Root cause
    "cache_enabled": false,
    "api_enabled": false
  }
}
```

**Fix**: Enable `LEADERBOARDS_COMPUTE_ENABLED=true` and restart.

---

## Common Debugging Scenarios

### Scenario 1: Empty Leaderboard

**Symptoms**: `entries` array is empty

**Check**:
1. `debug.computation_enabled` → Should be `true`
2. `debug.entry_count` → Should be >0
3. Query DB directly: `SELECT COUNT(*) FROM leaderboards_leaderboardentry WHERE tournament_id=501;`

**Fix**:
```bash
export LEADERBOARDS_COMPUTE_ENABLED=true
sudo systemctl restart deltacrown
```

---

### Scenario 2: High Latency

**Symptoms**: `query_time_ms` >500ms

**Check**:
1. `debug.cache_hit` → Should be `true` (if cache enabled)
2. `debug.cache_enabled` → Should be `true`
3. Redis health: `redis-cli PING`

**Fix**:
```bash
# Enable caching
export LEADERBOARDS_CACHE_ENABLED=true
sudo systemctl restart deltacrown

# Verify Redis
redis-cli PING  # Should return PONG
```

---

### Scenario 3: Stale Data

**Symptoms**: Leaderboard hasn't updated after match completion

**Check**:
1. `debug.cache_ttl_seconds` → How long until auto-refresh?
2. `debug.cache_key` → Note the key

**Fix (immediate)**:
```bash
# Clear cache for tournament
redis-cli DEL "lb:tournament:501"

# Or use service function
python manage.py shell
>>> from apps.leaderboards.services import invalidate_tournament_cache
>>> invalidate_tournament_cache(501)
```

---

## Security & PII Compliance

### What's Exposed

✅ **Safe to expose**:
- Player IDs, team IDs, tournament IDs
- Points, wins, losses, rank
- Timestamps
- Cache metadata

❌ **Never exposed**:
- Usernames, emails, full names
- IP addresses, session tokens
- Personal information
- Credentials

### Logs

Admin endpoint access is logged with IDs only:

```
[INFO] Admin leaderboard query: tournament_id=501, user_id=10, query_time_ms=12.5
```

No PII in logs.

---

## Monitoring Queries

### Cache Hit Rate

```bash
# Via Redis
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses

# Via admin endpoint
curl -H "Authorization: Token <admin_token>" \
  http://localhost:8000/api/admin/leaderboards/tournaments/501/ \
  | jq '.debug.cache_hit'
```

### Query Performance

```bash
# Sample multiple tournaments
for tid in 501 502 503; do
  curl -s -H "Authorization: Token <admin_token>" \
    http://localhost:8000/api/admin/leaderboards/tournaments/$tid/ \
    | jq '.debug.query_time_ms'
done
```

### Flag States

```bash
# Check all flags at once
curl -s -H "Authorization: Token <admin_token>" \
  http://localhost:8000/api/admin/leaderboards/tournaments/501/ \
  | jq '.debug | {computation_enabled, cache_enabled, api_enabled}'
```

---

## Emergency Procedures

### Disable Admin API

Admin API shares flags with public API. To disable:

```bash
# Disable all leaderboards features
export LEADERBOARDS_API_ENABLED=false
export LEADERBOARDS_CACHE_ENABLED=false
export LEADERBOARDS_COMPUTE_ENABLED=false
sudo systemctl restart deltacrown
```

### Clear All Caches

```bash
# Nuclear option: clear all leaderboard caches
redis-cli KEYS "lb:*" | xargs redis-cli DEL

# Verify
redis-cli KEYS "lb:*"  # Should return empty
```

### Rollback

Admin endpoints have no database writes, so no data rollback needed. Simply disable flags and restart.
