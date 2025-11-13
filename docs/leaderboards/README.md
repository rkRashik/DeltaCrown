# Leaderboards Service - Operator Guide

## Overview

The Leaderboards Service provides **PII-free, read-only access** to tournament and player rankings.

### Key Features
- **Flag-Gated**: All functionality controlled by 3 feature flags
- **Redis Caching**: Multi-tier TTL strategy (5min/1h/24h)
- **IDs-Only Responses**: Returns participant_id, team_id, tournament_id only (no display names, usernames, emails)
- **Service Layer**: Delegates computation to Celery tasks
- **Public API**: RESTful endpoints for tournament/player/seasonal rankings
- **Name Resolution**: Clients resolve IDs via `/api/profiles/`, `/api/teams/`, `/api/tournaments/{id}/metadata/`

### SLO Targets
- **P95 Latency**: <100ms (cache hit), <500ms (cache miss)
- **Cache Hit Rate**: >90% (tournament), >85% (season/all-time)
- **Availability**: 99.9% (fail-open to empty results if backend unavailable)

---

## Feature Flags

### 1. LEADERBOARDS_COMPUTE_ENABLED
**Purpose**: Enable leaderboard computation backend (Celery tasks)

**Default**: `false` (OFF)

**Effects**:
- **OFF**: All queries return empty DTOs with `"computation_enabled": false`
- **ON**: Celery tasks populate `LeaderboardEntry` table, queries return data

**Rollout**:
```bash
# Enable computation (backend only, API still disabled)
export LEADERBOARDS_COMPUTE_ENABLED=true
sudo systemctl restart deltacrown

# Verify computation is running
celery -A deltacrown inspect active  # Should show leaderboard tasks
```

**Rollback**:
```bash
export LEADERBOARDS_COMPUTE_ENABLED=false
sudo systemctl restart deltacrown
```

---

### 2. LEADERBOARDS_CACHE_ENABLED
**Purpose**: Enable Redis caching for reads

**Default**: `false` (OFF)

**Effects**:
- **OFF**: All queries hit DB (higher latency, more DB load)
- **ON**: Redis cache with TTL strategy (5min/1h/24h)

**Cache Keys**:
- `lb:tournament:{tournament_id}` (TTL: 5 minutes)
- `lb:season:{season_id}:{game_code}` (TTL: 1 hour)
- `lb:all_time:{game_code}` (TTL: 24 hours)
- `lb:player_history:{player_id}` (TTL: 1 hour)

**Rollout**:
```bash
# Enable caching (after compute backend is stable)
export LEADERBOARDS_CACHE_ENABLED=true
sudo systemctl restart deltacrown

# Verify cache hits
redis-cli KEYS "lb:*"  # Should show cache keys
redis-cli GET "lb:tournament:501"  # Should return cached data
```

**Rollback**:
```bash
export LEADERBOARDS_CACHE_ENABLED=false
sudo systemctl restart deltacrown

# Clear cache if needed
redis-cli KEYS "lb:*" | xargs redis-cli DEL
```

---

### 3. LEADERBOARDS_API_ENABLED
**Purpose**: Enable public API endpoints

**Default**: `false` (OFF)

**Effects**:
- **OFF**: API returns 404 (feature disabled)
- **ON**: 3 endpoints accessible (requires IsAuthenticated)

**Endpoints**:
- `GET /api/tournaments/leaderboards/tournament/{id}/`
- `GET /api/tournaments/leaderboards/player/{id}/history/`
- `GET /api/tournaments/leaderboards/{scope}/`

**Rollout**:
```bash
# Enable API (after compute + cache are stable)
export LEADERBOARDS_API_ENABLED=true
sudo systemctl restart deltacrown

# Verify API is accessible
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/tournaments/leaderboards/all_time/
# Should return 200 with JSON
```

**Rollback**:
```bash
export LEADERBOARDS_API_ENABLED=false
sudo systemctl restart deltacrown

# Verify API is disabled
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/tournaments/leaderboards/all_time/
# Should return 404
```

---

## API Usage Examples

### 1. Tournament Leaderboard

**Endpoint**: `GET /api/tournaments/leaderboards/tournament/{tournament_id}/`

**Auth**: Required (IsAuthenticated)

**Request**:
```bash
curl -H "Authorization: Bearer <jwt_token>" \
  http://localhost:8000/api/tournaments/leaderboards/tournament/501/
```

**Response** (200 OK) - IDs Only:
```json
{
  "scope": "tournament",
  "entries": [
    {
      "rank": 1,
      "participant_id": 123,
      "team_id": 45,
      "points": 3000,
      "wins": 15,
      "losses": 2,
      "win_rate": 88.24,
      "last_updated": "2025-11-13T14:30:00Z"
    },
    {
      "rank": 2,
      "participant_id": 456,
      "team_id": 67,
      "points": 2800,
      "wins": 14,
      "losses": 3,
      "win_rate": 82.35,
      "last_updated": "2025-11-13T14:30:00Z"
    }
  ],
  "metadata": {
    "tournament_id": 501,
    "count": 16,
    "cache_hit": true,
    "cached_at": "2025-11-13T14:25:00Z"
  }
}
```

**Note**: Responses contain participant_id and team_id only. Resolve display names via `/api/profiles/{participant_id}/` and `/api/teams/{team_id}/`.
```

**Edge Cases**:
- Tournament doesn't exist: 404 Not Found
- Computation disabled: 200 OK with empty entries, `"computation_enabled": false`
- API disabled: 404 Not Found

---

### 2. Player History

**Endpoint**: `GET /api/tournaments/leaderboards/player/{player_id}/history/`

**Auth**: Required (IsAuthenticated)

**Request**:
```bash
curl -H "Authorization: Bearer <jwt_token>" \
  http://localhost:8000/api/tournaments/leaderboards/player/456/history/
```

**Response** (200 OK):
```json
{
  "player_id": 456,
  "history": [
    {
      "date": "2025-11-13",
      "rank": 5,
      "points": 2600,
      "leaderboard_type": "season"
    },
    {
      "date": "2025-11-12",
      "rank": 6,
      "points": 2400,
      "leaderboard_type": "season"
    },
    {
      "date": "2025-11-11",
      "rank": 7,
      "points": 2200,
      "leaderboard_type": "season"
    }
  ],
  "count": 15
}
```

**Edge Cases**:
- Player doesn't exist: 200 OK with empty history (not 404)
- No snapshots: 200 OK with `"count": 0`

---

### 3. Scoped Leaderboard (Season)

**Endpoint**: `GET /api/tournaments/leaderboards/{scope}/?game_code=valorant&season_id=2025_S1`

**Auth**: Required (IsAuthenticated)

**Request**:
```bash
curl -H "Authorization: Bearer <jwt_token>" \
  "http://localhost:8000/api/tournaments/leaderboards/season/?season_id=2025_S1&game_code=valorant"
```

**Response** (200 OK):
```json
{
  "scope": "season",
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
  "metadata": {
    "scope": "season",
    "game_code": "valorant",
    "season_id": "2025_S1",
    "count": 50,
    "cache_hit": false,
    "queried_at": "2025-11-13T14:30:00Z"
  }
}
```

**Query Parameters**:
- `season_id`: **Required** for scope="season" (e.g., "2025_S1")
- `game_code`: Optional filter (e.g., "valorant", "cs2", "lol")

**Edge Cases**:
- Invalid scope: 400 Bad Request
- Missing season_id for scope="season": 400 Bad Request
- No entries: 200 OK with empty entries

---

### 4. Scoped Leaderboard (All-Time)

**Endpoint**: `GET /api/tournaments/leaderboards/{scope}/?game_code=cs2`

**Request**:
```bash
# All-time (all games)
curl -H "Authorization: Bearer <jwt_token>" \
  http://localhost:8000/api/tournaments/leaderboards/all_time/

# All-time (CS2 only)
curl -H "Authorization: Bearer <jwt_token>" \
  "http://localhost:8000/api/tournaments/leaderboards/all_time/?game_code=cs2"
```

**Response** (200 OK):
```json
{
  "scope": "all_time",
  "entries": [
    {
      "rank": 1,
      "player_id": 123,
      "team_id": 45,
      "points": 10000,
      "wins": 60,
      "losses": 10,
      "win_rate": 85.71,
      "last_updated": "2025-11-13T10:00:00Z"
    }
  ],
  "metadata": {
    "scope": "all_time",
    "game_code": "cs2",
    "season_id": null,
    "count": 100,
    "cache_hit": true,
    "cached_at": "2025-11-12T14:30:00Z"
  }
}
```

**Query Parameters**:
- `game_code`: Optional (omit for cross-game aggregate)

---

## Name Resolution

**IDs-Only Policy**: All leaderboard responses contain **IDs only** (participant_id, team_id, tournament_id). No display names, usernames, or emails are included.

### Resolving IDs to Display Names

Clients must make separate API calls to resolve IDs:

**1. Resolve Participant Display Names**:
```bash
curl -H "Authorization: Token $TOKEN" \
  https://api.deltacrown.com/api/profiles/456/
# Response: {"id": 456, "display_name": "Dragon Slayers", "avatar_url": "..."}
```

**2. Resolve Team Names**:
```bash
curl -H "Authorization: Token $TOKEN" \
  https://api.deltacrown.com/api/teams/789/
# Response: {"id": 789, "name": "Phoenix Squad", "logo_url": "..."}
```

**3. Resolve Tournament Metadata**:
```bash
curl -H "Authorization: Token $TOKEN" \
  https://api.deltacrown.com/api/tournaments/123/metadata/
# Response: {"id": 123, "name": "Summer Championship 2025", "game_code": "valorant", ...}
```

### Two-Step Pattern Example

```bash
# Step 1: Fetch leaderboard (IDs only)
curl -H "Authorization: Token $TOKEN" \
  https://api.deltacrown.com/api/tournaments/leaderboards/tournament/123/ | jq '.entries[0]'
# {"rank": 1, "participant_id": 456, "team_id": 789, "points": 2450, ...}

# Step 2: Resolve names
PARTICIPANT_ID=456
TEAM_ID=789
curl -H "Authorization: Token $TOKEN" \
  "https://api.deltacrown.com/api/profiles/$PARTICIPANT_ID/" | jq '.display_name'
# "Dragon Slayers"

curl -H "Authorization: Token $TOKEN" \
  "https://api.deltacrown.com/api/teams/$TEAM_ID/" | jq '.name'
# "Phoenix Squad"
```

**Caching Tip**: Cache resolved names client-side to avoid redundant API calls.

---

## Cache Invalidation

### Manual Invalidation

```python
from apps.leaderboards.services import (
    invalidate_tournament_cache,
    invalidate_player_history_cache,
    invalidate_scoped_cache,
)

# Invalidate tournament cache (after match completion)
invalidate_tournament_cache(tournament_id=501)

# Invalidate player history (after entry update)
invalidate_player_history_cache(player_id=456)

# Invalidate seasonal cache (after recomputation)
invalidate_scoped_cache(scope="season", season_id="2025_S1", game_code="valorant")

# Invalidate all-time cache
invalidate_scoped_cache(scope="all_time", game_code="cs2")
```

### Bulk Invalidation (Emergency)

```bash
# Clear all leaderboard caches
redis-cli KEYS "lb:*" | xargs redis-cli DEL

# Verify cleared
redis-cli KEYS "lb:*"  # Should return empty
```

---

## Monitoring

### Cache Hit Rate

```bash
# Check cache keys
redis-cli KEYS "lb:*" | wc -l

# Monitor cache hits (Prometheus)
rate(redis_commands_total{cmd="get"}[5m])
```

### P95 Latency

```bash
# API latency (Prometheus)
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket{
    endpoint=~"/api/tournaments/leaderboards/.*"
  }[5m])
)
```

### Error Rate

```bash
# 4xx/5xx errors
rate(http_requests_total{
  endpoint=~"/api/tournaments/leaderboards/.*",
  status=~"4..|5.."
}[5m])
```

---

## Troubleshooting

### Issue: Empty Leaderboards

**Symptoms**: API returns empty entries with `"computation_enabled": false`

**Causes**:
1. `LEADERBOARDS_COMPUTE_ENABLED=false`
2. Celery tasks not running
3. No data in `LeaderboardEntry` table

**Fix**:
```bash
# 1. Enable computation
export LEADERBOARDS_COMPUTE_ENABLED=true
sudo systemctl restart deltacrown

# 2. Verify Celery tasks
celery -A deltacrown inspect active

# 3. Check DB
psql -d deltacrown -c "SELECT COUNT(*) FROM leaderboards_leaderboardentry;"
```

---

### Issue: High Latency

**Symptoms**: P95 >500ms, cache hit rate <80%

**Causes**:
1. `LEADERBOARDS_CACHE_ENABLED=false`
2. Redis outage
3. Cache TTL too low

**Fix**:
```bash
# 1. Enable caching
export LEADERBOARDS_CACHE_ENABLED=true
sudo systemctl restart deltacrown

# 2. Verify Redis
redis-cli PING  # Should return PONG

# 3. Check cache keys
redis-cli KEYS "lb:*"
```

---

### Issue: 404 Errors

**Symptoms**: All API requests return 404

**Causes**:
1. `LEADERBOARDS_API_ENABLED=false`
2. Wrong URL pattern

**Fix**:
```bash
# 1. Enable API
export LEADERBOARDS_API_ENABLED=true
sudo systemctl restart deltacrown

# 2. Verify URL
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/tournaments/leaderboards/all_time/
```

---

## Emergency Rollback

**One-line disable all features**:
```bash
export LEADERBOARDS_API_ENABLED=false LEADERBOARDS_CACHE_ENABLED=false LEADERBOARDS_COMPUTE_ENABLED=false; sudo systemctl restart deltacrown
```

**Verify**:
```bash
# API should return 404
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/tournaments/leaderboards/all_time/

# Cache should be cleared
redis-cli KEYS "lb:*"  # Should return empty
```

---

## Rollout Checklist

### Phase 1: Computation Backend
- [ ] Set `LEADERBOARDS_COMPUTE_ENABLED=true`
- [ ] Restart application
- [ ] Verify Celery tasks running
- [ ] Check `LeaderboardEntry` table has data
- [ ] Wait 24 hours for data population

### Phase 2: Caching Layer
- [ ] Set `LEADERBOARDS_CACHE_ENABLED=true`
- [ ] Restart application
- [ ] Verify Redis keys created (`redis-cli KEYS "lb:*"`)
- [ ] Monitor cache hit rate (target >85%)
- [ ] Wait 24 hours for cache warmup

### Phase 3: Public API
- [ ] Set `LEADERBOARDS_API_ENABLED=true`
- [ ] Restart application
- [ ] Test all 3 endpoints (tournament, player, scoped)
- [ ] Monitor P95 latency (target <100ms)
- [ ] Monitor error rate (target <1%)
- [ ] Announce API availability

---

## Observability & Metrics

### Metrics Instrumentation

**Module**: `apps.leaderboards.metrics`

**Metrics Tracked**:
- `leaderboards_requests_total` - Total requests by scope (tournament, season, all_time)
- `leaderboards_cache_hits_total` - Cache hit count
- `leaderboards_cache_misses_total` - Cache miss count
- `leaderboards_latency_ms_bucket` - Request latency histogram (p50, p95, p99)

**Usage** (automatic via service layer):
```python
from apps.leaderboards.metrics import record_leaderboard_request

with record_leaderboard_request(scope='tournament', source='cache'):
    # Metrics automatically recorded on context exit
    response = get_tournament_leaderboard(123)
```

### Logging Format

**Structured Logs** (IDs only, no PII):

```json
{
  "level": "INFO",
  "scope": "tournament",
  "source": "cache",
  "tournament_id": 123,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Log Fields**:
- `scope`: Leaderboard scope (tournament, season, all_time)
- `source`: Data source (cache, snapshot, live, disabled)
  - `cache`: Cache hit (fast path)
  - `live`: Cache miss, queried DB (slow path)
  - `snapshot`: Historical snapshot query
  - `disabled`: Flags disabled, returned empty
- `duration_ms`: Request duration in milliseconds (computed by metrics module)
- `tournament_id`, `player_id`, etc.: IDs only (no PII)

**Example Logs**:

```
# Cache hit (fast)
INFO Cache HIT for tournament leaderboard scope=tournament source=cache tournament_id=123

# Cache miss (slow)
INFO Cache MISS for tournament leaderboard, querying DB scope=tournament source=live tournament_id=123

# Flags disabled
INFO Leaderboards disabled, returning empty scope=tournament source=disabled tournament_id=123
```

### Healthy Patterns

**Good Signals**:
- Cache hit ratio >90% for tournament scope
- P95 latency <100ms for cache hits
- P95 latency <500ms for cache misses
- Zero `source=disabled` logs (flags enabled)

**Bad Signals**:
- Cache hit ratio <80% (investigate TTL or cache eviction)
- P95 latency >1000ms (investigate DB query performance)
- Frequent `source=disabled` logs (flags not enabled)
- High error rate (>1%) on API endpoints

### Metrics Dashboard

**Get Current Metrics Snapshot**:
```python
from apps.leaderboards.metrics import get_metrics_snapshot

snapshot = get_metrics_snapshot()
print(f"Cache hit ratio: {snapshot['cache_hit_ratio']:.2%}")
print(f"P95 latency: {snapshot['latency_percentiles']['p95']:.2f}ms")
```

**Example Output**:
```json
{
  "requests_total": {
    "tournament": 1250,
    "season": 430,
    "all_time": 120
  },
  "cache_hits_total": 1580,
  "cache_misses_total": 220,
  "cache_hit_ratio": 0.878,
  "latency_percentiles": {
    "p50": 35.2,
    "p95": 89.5,
    "p99": 145.8
  },
  "sample_count": 1000
}
```

### Prometheus Integration (Future)

**Planned Metrics** (not yet implemented, see TODO in `metrics.py`):

```python
# Request rate by scope
rate(leaderboards_requests_total[5m])

# Cache hit ratio
sum(rate(leaderboards_cache_hits_total[5m])) / 
(sum(rate(leaderboards_cache_hits_total[5m])) + sum(rate(leaderboards_cache_misses_total[5m])))

# P95 latency
histogram_quantile(0.95, rate(leaderboards_latency_ms_bucket[5m]))
```

**AlertManager Rules** (future):
```yaml
# Alert if cache hit ratio drops below 80%
- alert: LeaderboardsCacheHitLow
  expr: sum(rate(leaderboards_cache_hits_total[5m])) / (sum(rate(leaderboards_cache_hits_total[5m])) + sum(rate(leaderboards_cache_misses_total[5m]))) < 0.80
  for: 10m
  annotations:
    summary: "Leaderboards cache hit ratio below 80%"

# Alert if P95 latency exceeds 500ms
- alert: LeaderboardsLatencyHigh
  expr: histogram_quantile(0.95, rate(leaderboards_latency_ms_bucket[5m])) > 500
  for: 5m
  annotations:
    summary: "Leaderboards P95 latency exceeds 500ms"
```

### Troubleshooting with Metrics

**Scenario 1: High latency (P95 >500ms)**

1. Check cache hit ratio:
   ```python
   snapshot = get_metrics_snapshot()
   print(snapshot['cache_hit_ratio'])
   ```
2. If ratio <80%, check Redis:
   ```bash
   redis-cli INFO stats | grep evicted_keys
   ```
3. If evictions high, increase Redis memory or lower TTL

**Scenario 2: Low cache hit ratio (<80%)**

1. Check cache enable flag:
   ```bash
   echo $LEADERBOARDS_CACHE_ENABLED  # Should be 'true'
   ```
2. Check Redis connectivity:
   ```bash
   redis-cli PING  # Should return 'PONG'
   ```
3. Check cache key patterns:
   ```bash
   redis-cli KEYS "leaderboard:tournament:*"
   ```

**Scenario 3: All requests show source=disabled**

1. Check compute flag:
   ```bash
   echo $LEADERBOARDS_COMPUTE_ENABLED  # Should be 'true'
   ```
2. Verify Celery tasks running:
   ```bash
   celery -A deltacrown inspect active
   ```

---
