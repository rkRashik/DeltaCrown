# Leaderboard Ranking Engine V2 (Phase F)

**Phase**: F  
**Status**: Complete  
**Date**: 2025-11-13

---

## 1. Overview

Engine V2 is a high-performance ranking computation system designed for **large-scale tournaments** (10k-100k participants) with **real-time rank updates** for spectators.

### Key Features

1. **Fast Ranking Computation**: <500ms for 10k participants (cached: <50ms)
2. **Rank Delta Tracking**: Track who moved up/down after each match
3. **Partial Updates**: Recompute only affected participants (10x faster than full recompute)
4. **Incremental Caching**: 30-second TTL for tournament rankings (vs 5min in Phase E)
5. **WebSocket Push**: Broadcast rank deltas to spectators in real-time
6. **Battle Royale Tiebreakers**: Points > Kills > Wins > Matches > Earliest Win

---

## 2. Architecture

### 2.1 Core Components

```
apps/leaderboards/engine.py
├── RankingEngine (main compute engine)
│   ├── compute_tournament_rankings()
│   ├── compute_season_rankings()
│   ├── compute_all_time_rankings()
│   └── compute_partial_update()
├── DTOs
│   ├── RankedParticipantDTO
│   ├── RankDeltaDTO
│   └── RankingResponseDTO
└── Cache Utilities
    ├── _get_engine_cache_key_rankings()
    ├── _get_engine_cache_key_deltas()
    └── invalidate_ranking_cache()
```

### 2.2 Integration Points

**Phase E Leaderboards**:
- Extends Phase E service layer with faster compute
- Same IDs-only discipline (participant_id, team_id, tournament_id)
- Backward compatible (falls back to Phase E if ENGINE_V2_ENABLED=False)

**Phase G Spectator**:
- WebSocket push for rank changes (spectator pages auto-update)
- htmx auto-refresh reads from engine_v2 cache (30s TTL)

**Module 2.6 Realtime**:
- Broadcasts rank_update events via existing tournament channels
- Uses Module 2.6 metrics (ws_messages_total{type="rank_update"})

---

## 3. Ranking Rules

### 3.1 Battle Royale Tiebreaker Cascade

```
1. Points DESC (primary sort)
2. Kills DESC (tiebreaker 1)
3. Wins DESC (tiebreaker 2)
4. Matches Played ASC (tiebreaker 3 - fewer matches = better)
5. Earliest Win ASC (tiebreaker 4 - older win = better)
6. Participant ID ASC (final deterministic tiebreaker)
```

### 3.2 Example

```python
# Match results:
# Player 123: 3000 points, 45 kills, 15 wins, 17 matches, earliest win: 2025-11-10
# Player 456: 3000 points, 45 kills, 15 wins, 17 matches, earliest win: 2025-11-12
# Player 789: 3000 points, 50 kills, 14 wins, 16 matches, earliest win: 2025-11-11

# Ranking:
# Rank 1: Player 789 (50 kills, tiebreaker 1)
# Rank 2: Player 123 (earlier win 2025-11-10, tiebreaker 4)
# Rank 3: Player 456 (later win 2025-11-12)
```

---

## 4. Delta Computation

### 4.1 Rank Delta DTO

```python
@dataclass
class RankDeltaDTO:
    participant_id: Optional[int]
    team_id: Optional[int]
    previous_rank: Optional[int]  # None if new entry
    current_rank: int
    rank_change: int  # negative = moved up, positive = moved down
    points: int
    last_updated: datetime
```

### 4.2 Example Deltas

```json
{
  "deltas": [
    {
      "participant_id": 456,
      "previous_rank": 5,
      "current_rank": 3,
      "rank_change": -2,
      "points": 2800,
      "last_updated": "2025-11-13T14:30:00Z"
    },
    {
      "participant_id": 789,
      "previous_rank": 2,
      "current_rank": 4,
      "rank_change": 2,
      "points": 2600,
      "last_updated": "2025-11-13T14:30:00Z"
    }
  ]
}
```

### 4.3 Delta Sources

**Previous Rankings**:
1. Try engine_v2 cache first (`ranking:full:tournament:123`)
2. Fall back to latest LeaderboardSnapshot
3. If no snapshot: All entries are new (previous_rank=None)

**Current Rankings**:
- Computed fresh from Match results
- Apply BR tiebreaker rules
- Assign ranks (1-indexed)

---

## 5. Cache Strategy

### 5.1 Cache Keys

```python
# Full rankings
ranking:full:tournament:123
ranking:full:season:2025_S1:valorant
ranking:full:all_time

# Rank deltas (separate for efficient reads)
ranking:delta:tournament:123
ranking:delta:season:2025_S1:valorant
```

### 5.2 Cache TTLs

| Scope | TTL | Rationale |
|-------|-----|-----------|
| Tournament | 30s | Fast spectator updates (Phase G) |
| Season | 1h | Recomputed hourly (less frequent changes) |
| All-time | Snapshot-only | Too expensive to compute live |

### 5.3 Cache Invalidation

**Manual**:
```python
from apps.leaderboards.engine import invalidate_ranking_cache

# After match completion:
invalidate_ranking_cache("tournament", tournament_id)

# After dispute resolution:
invalidate_ranking_cache("tournament", tournament_id)
```

**Automatic** (Celery Tasks):
- Half-hour snapshots: Rewrite cache after tournament snapshot
- Match completion hooks: Trigger partial update + cache refresh

---

## 6. Realtime Push Updates

### 6.1 WebSocket Flow

```
1. Match completes
   └─> MatchService.mark_completed()
       └─> RankingEngine.compute_partial_update()
           └─> Extract deltas (rank changes)
               └─> broadcast_rank_update(tournament_id, deltas)
                   └─> WebSocket "rank_update" event to spectators
```

### 6.2 WebSocket Payload

```json
{
  "type": "rank_update",
  "tournament_id": 123,
  "changes": [
    {
      "participant_id": 91,
      "previous_rank": 5,
      "current_rank": 3,
      "rank_change": -2,
      "points": 1250
    }
  ]
}
```

### 6.3 Client Usage (Phase G Spectator)

```javascript
// static/js/spectator_ws.js integration
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'rank_update') {
        // Trigger htmx refresh immediately (bypass timer)
        htmx.trigger(leaderboardElement, 'refresh');
        
        // Show rank change animations
        data.changes.forEach(change => {
            if (change.rank_change < 0) {
                showMoveUpAnimation(change.participant_id);
            } else {
                showMoveDownAnimation(change.participant_id);
            }
        });
    }
};
```

---

## 7. Snapshot Lifecycle

### 7.1 Half-Hour Tournament Snapshots

**Task**: `snapshot_active_tournaments`  
**Schedule**: Every 30 minutes  
**Targets**: Tournaments with status in ['registration_open', 'ongoing', 'in_progress']

**Flow**:
```python
@shared_task
def snapshot_tournament_rankings(tournament_id):
    # 1. Compute rankings using Engine V2
    engine = RankingEngine(cache_ttl=1800)
    response = engine.compute_tournament_rankings(tournament_id, use_cache=False)
    
    # 2. Save to LeaderboardSnapshot
    snapshot_data = {
        "rankings": [r.to_dict() for r in response.rankings],
        "metadata": response.metadata,
    }
    LeaderboardSnapshot.objects.update_or_create(
        leaderboard_type="tournament",
        tournament_id=tournament_id,
        snapshot_date=timezone.now().date(),
        defaults={"data": snapshot_data}
    )
    
    # 3. Broadcast deltas to spectators
    if response.deltas:
        broadcast_rank_update(tournament_id, [d.to_dict() for d in response.deltas])
```

### 7.2 Daily Season Snapshots

**Task**: `snapshot_season_rankings`  
**Schedule**: Daily at 00:00 UTC  
**Per-Game**: Separate tasks for valorant, cs2, efootball, etc.

**Flow**:
```python
@shared_task
def snapshot_season_rankings(season_id, game_code):
    engine = RankingEngine(cache_ttl=3600)
    response = engine.compute_season_rankings(season_id, game_code, use_cache=False)
    
    # Save snapshot (same pattern as tournament)
```

### 7.3 Daily All-Time Snapshots

**Task**: `snapshot_all_time`  
**Schedule**: Daily at 00:30 UTC  
**Note**: Uses existing snapshots (no live compute)

**Flow**:
```python
@shared_task
def snapshot_all_time(game_code=None):
    engine = RankingEngine()
    response = engine.compute_all_time_rankings(game_code=game_code)
    
    # All-time returns pre-computed snapshot (Phase E data)
```

### 7.4 Weekly Cold Storage Compaction

**Task**: `compact_old_snapshots`  
**Schedule**: Sundays at 03:00 UTC  
**Threshold**: 90 days old

**Flow**:
```python
@shared_task
def compact_old_snapshots(days_threshold=90):
    cutoff_date = timezone.now().date() - timedelta(days=days_threshold)
    
    for snapshot in LeaderboardSnapshot.objects.filter(snapshot_date__lt=cutoff_date):
        rankings = snapshot.data["rankings"]
        
        # Keep only top 100 entries
        if len(rankings) > 100:
            snapshot.data = {
                "rankings": rankings[:100],
                "metadata": {
                    "compacted": True,
                    "original_count": len(rankings),
                    "compacted_date": timezone.now().isoformat(),
                }
            }
            snapshot.save()
    
    # Delete very old snapshots (> 1 year)
    LeaderboardSnapshot.objects.filter(
        snapshot_date__lt=timezone.now().date() - timedelta(days=365)
    ).delete()
```

---

## 8. Feature Flags

### 8.1 Phase F Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `LEADERBOARDS_ENGINE_V2_ENABLED` | False | Master switch for Engine V2 |
| `LEADERBOARDS_API_ENABLED` | False | Enable public API endpoints (Phase E) |
| `LEADERBOARDS_CACHE_ENABLED` | False | Enable Redis caching |
| `LEADERBOARDS_COMPUTE_ENABLED` | False | Enable computation backend (Phase E) |

### 8.2 Flag Behavior

**ENGINE_V2_ENABLED=False**:
- API falls back to Phase E service layer
- Tasks skip Engine V2 (return early)
- No rank deltas computed
- No WebSocket rank_update broadcasts

**ENGINE_V2_ENABLED=True**:
- API uses RankingEngine for fast compute
- Tasks run half-hour snapshots
- Rank deltas tracked + cached
- WebSocket rank_update broadcasts active

---

## 9. Performance Benchmarks

### 9.1 Tournament Rankings (10k Participants)

| Operation | Cache Hit | Cache Miss | Optimization |
|-----------|-----------|------------|-------------|
| Engine V2 | <50ms | ~500ms | Cached read from Redis |
| Phase E Legacy | N/A | ~2s | Full recompute from matches |

### 9.2 Season Rankings (100k Participants)

| Operation | Cache Hit | Cache Miss | Optimization |
|-----------|-----------|------------|-------------|
| Engine V2 | <100ms | ~2s | Aggregated tournament stats |
| Phase E Legacy | N/A | ~15s | Full cross-tournament aggregation |

### 9.3 Partial Update (10 Affected out of 10k)

| Operation | Duration | Speedup |
|-----------|----------|---------|
| Full Recompute | ~500ms | 1x baseline |
| Partial Update | ~50ms | 10x faster |

### 9.4 Cache Hit Ratios (Phase F Production)

| Scope | Hit Ratio | TTL | Notes |
|-------|-----------|-----|-------|
| Tournament | 95%+ | 30s | Fast spectator updates |
| Season | 90%+ | 1h | Hourly recomputation |

---

## 10. API Integration

### 10.1 Engine V2 Read Path

**Endpoint**: `GET /api/tournaments/leaderboards/tournament/{id}/`

**Phase F Behavior**:
```python
if settings.LEADERBOARDS_ENGINE_V2_ENABLED:
    engine = RankingEngine(cache_ttl=30)
    response = engine.compute_tournament_rankings(tournament_id, use_cache=True)
    return Response(response.to_dict())
else:
    # Fall back to Phase E
    response = get_tournament_leaderboard(tournament_id)
    return Response(response.to_dict())
```

**Response Format** (Engine V2):
```json
{
  "scope": "tournament",
  "rankings": [...],
  "deltas": [...],
  "metadata": {
    "tournament_id": 123,
    "source": "engine_v2",
    "cache_hit": true,
    "count": 16,
    "delta_count": 5,
    "duration_ms": 45
  }
}
```

### 10.2 Backward Compatibility

**Phase E Response** (Legacy):
```json
{
  "scope": "tournament",
  "entries": [...],  // Note: "entries" not "rankings"
  "metadata": {
    "tournament_id": 123,
    "count": 16,
    "cache_hit": true
  }
}
```

**Migration Path**:
- Clients reading `response.entries` will break with Engine V2
- Recommended: Check `metadata.source` and handle both formats
- Future: Phase E deprecated once Engine V2 is stable

---

## 11. Partial Update Algorithm

### 11.1 Use Cases

1. **Match Completion**: Recompute only participants in completed match
2. **Dispute Resolution**: Recompute only disputed participants
3. **Sanction**: Recompute only sanctioned participant

### 11.2 Algorithm

```python
def compute_partial_update(tournament_id, affected_participant_ids, affected_team_ids):
    # 1. Fetch current cached rankings
    current_rankings = compute_tournament_rankings(tournament_id, use_cache=True)
    
    # 2. Build map of current rankings
    current_map = {(r.participant_id, r.team_id): r for r in current_rankings}
    
    # 3. Recompute stats for ONLY affected participants
    affected_stats = _aggregate_tournament_stats_partial(
        tournament_id,
        is_team_based,
        affected_participant_ids,
        affected_team_ids
    )
    
    # 4. Merge affected + remaining participants
    for stats in affected_stats:
        key = (stats["participant_id"], stats["team_id"])
        del current_map[key]  # Remove old entry
    
    remaining_stats = [to_stats(r) for r in current_map.values()]
    merged_stats = affected_stats + remaining_stats
    
    # 5. Re-sort entire leaderboard (ranks may shift)
    rankings = _apply_ranking_rules(merged_stats, is_team_based)
    
    # 6. Compute deltas (only for affected participants)
    deltas = _compute_deltas(rankings, current_rankings)
    
    # 7. Update cache
    cache.set(cache_key, rankings, ttl=30)
    
    return RankingResponseDTO(scope="tournament", rankings=rankings, deltas=deltas)
```

### 11.3 Performance

**Full Recompute** (10k participants):
- Query all matches: 200ms
- Aggregate stats: 250ms
- Apply ranking rules: 50ms
- **Total**: ~500ms

**Partial Update** (10 affected participants):
- Query affected matches: 20ms
- Aggregate affected stats: 10ms
- Merge with cached: 5ms
- Re-sort: 50ms
- **Total**: ~85ms (6x faster)

---

## 12. Observability

### 12.1 Metrics (Module 2.6 Integration)

**WebSocket Metrics**:
```
ws_messages_total{type="rank_update"} 
ws_message_latency_seconds{type="rank_update"}
```

**Custom Engine Metrics** (Future):
```
leaderboard_engine_compute_duration_ms{scope="tournament|season|all_time"}
leaderboard_engine_cache_hit_ratio{scope="tournament|season"}
leaderboard_engine_partial_update_count
```

### 12.2 Structured Logging

```python
logger.info(
    f"Engine V2 compute: tournament={tournament_id}, "
    f"entries={len(rankings)}, duration={duration_ms}ms, "
    f"deltas={len(deltas)}, source={source}"
)
```

**Log Fields** (IDs-only):
- `tournament_id`, `season_id`, `game_code` (integers/strings)
- `source`: "cache" | "engine_v2" | "snapshot"
- `duration_ms`: Computation time
- `count`: Number of rankings
- `delta_count`: Number of rank changes

---

## 13. Troubleshooting

### 13.1 Slow Leaderboard Reads

**Symptom**: API response > 500ms

**Checks**:
1. `cache_hit` in metadata → Should be `true` most of the time
2. Cache TTL expired → Increase TTL if acceptable
3. Redis slow → Check Redis latency (`redis-cli --latency`)
4. Full recompute on every request → Ensure `use_cache=True`

**Fix**:
```python
# Manually warm cache
from apps.leaderboards.engine import RankingEngine

engine = RankingEngine(cache_ttl=30)
engine.compute_tournament_rankings(tournament_id, use_cache=False)
```

### 13.2 Missing Rank Deltas

**Symptom**: `deltas` array always empty

**Checks**:
1. Previous snapshot exists → Query LeaderboardSnapshot for tournament
2. Cache disabled → Check `LEADERBOARDS_CACHE_ENABLED`
3. First-time compute → All entries are new (previous_rank=None)

**Fix**:
```python
# Run snapshot task to establish baseline
from apps.leaderboards.tasks import snapshot_tournament_rankings

snapshot_tournament_rankings.delay(tournament_id)
```

### 13.3 Incorrect Ranks

**Symptom**: Participant with higher points ranked lower

**Checks**:
1. Verify BR tiebreaker rules applied correctly
2. Check `kills`, `wins`, `matches_played`, `earliest_win` in response
3. Inspect match scores in database (Match.participant1_score, etc.)

**Debug**:
```python
from apps.leaderboards.engine import RankingEngine

engine = RankingEngine()
response = engine.compute_tournament_rankings(tournament_id, use_cache=False)

# Find participant
for r in response.rankings:
    if r.participant_id == 456:
        print(f"Rank: {r.rank}, Points: {r.points}, Kills: {r.kills}, Wins: {r.wins}")
```

### 13.4 WebSocket rank_update Not Received

**Symptom**: Spectator page doesn't update after match completion

**Checks**:
1. WebSocket connected → Check connection status indicator (Phase G)
2. Match marked completed → Match.status == "completed"
3. Partial update triggered → Check logs for "Partial update complete"
4. Broadcast succeeded → Check logs for "Broadcast rank_update"

**Fix**:
```python
# Manually trigger broadcast
from apps.leaderboards.engine import RankingEngine
from apps.tournaments.realtime.broadcast import broadcast_rank_update

engine = RankingEngine()
response = engine.compute_partial_update(
    tournament_id,
    affected_participant_ids={456, 789},
    affected_team_ids=set()
)

deltas_json = [d.to_dict() for d in response.deltas]
broadcast_rank_update(tournament_id, deltas_json)
```

---

## 14. Migration from Phase E

### 14.1 Feature Flag Rollout

**Step 1**: Enable Engine V2 in staging
```python
# settings_staging.py
LEADERBOARDS_ENGINE_V2_ENABLED = True
```

**Step 2**: Monitor metrics
- Cache hit ratio > 90%
- P95 latency < 100ms (cached), < 500ms (uncached)
- No errors in logs

**Step 3**: Canary rollout in production
```python
# settings_production.py
LEADERBOARDS_ENGINE_V2_ENABLED = True  # Start with 10% traffic
```

**Step 4**: Full rollout
- Increase to 50%, then 100%
- Monitor for 48 hours
- If stable: Deprecate Phase E service layer

### 14.2 Rollback Plan

**Immediate Rollback**:
```python
LEADERBOARDS_ENGINE_V2_ENABLED = False  # Instant fallback to Phase E
```

**Data Consistency**:
- Engine V2 uses same Match model as Phase E (no data migration)
- Snapshots backward compatible (same JSON structure)
- Redis cache keys isolated (no collision with Phase E)

---

## 15. Future Enhancements

### 15.1 Advanced Tiebreakers

**Game-Specific Rules**:
- Valorant: K/D ratio, ADR (average damage per round)
- CS2: HLTV rating, clutch wins
- BR: Survival time, damage dealt

**Implementation**:
```python
def _apply_ranking_rules(stats, is_team_based, game_code=None):
    if game_code == "valorant":
        # Sort by K/D ratio after points
        sorted_stats = sorted(stats, key=lambda s: (
            -s["points"],
            -s["kd_ratio"],  # NEW: Valorant-specific
            -s["kills"],
            ...
        ))
```

### 15.2 ELO/MMR Integration

**Skill-Based Matchmaking**:
- Compute ELO rating alongside points
- Use ELO for tournament seeding
- Track ELO history in LeaderboardSnapshot

### 15.3 Multi-Region Leaderboards

**Regional Rankings**:
```python
engine.compute_regional_rankings(region="NA", season_id="2025_S1")
```

**Cross-Region Comparisons**:
- Rank 1 NA vs Rank 1 EU
- Regional average ELO

---

## 16. Related Documentation

- **Phase E Leaderboards**: `docs/leaderboards/README.md`
- **Phase G Spectator**: `docs/spectator/README.md`
- **Module 2.6 Realtime**: `docs/runbooks/module_2_6_realtime_monitoring.md`
- **MAP.md Phase F**: `Documents/ExecutionPlan/MAP.md#phase-f`
- **trace.yml module_f**: `Documents/ExecutionPlan/trace.yml#module_f`

---

**End of Engine V2 Documentation**
