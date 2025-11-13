# Leaderboards Specification v1.0

**Status**: Draft Specification  
**Target Version**: DeltaCrown v6.0  
**Owner**: Product Team  
**Last Updated**: 2025-11-13

---

## 1. Executive Summary

Leaderboards are ranked player/team lists displayed across DeltaCrown pages (homepage, tournament pages, team profiles, player profiles). This spec defines:

- **Data Sources**: Where rankings come from (tournament placements, win/loss records, coins earned, match statistics)
- **Leaderboard Types**: Tournament-specific, global seasonal, all-time, team-based, player-based, game-specific
- **Update Cadence**: Real-time vs hourly vs daily updates (performance trade-offs)
- **Display Rules**: How to handle ties, inactive players, minimum participation thresholds
- **Caching Strategy**: Redis + pre-computed denormalized tables for fast reads
- **UI Components**: Reusable leaderboard widget for consistent presentation

**Key Design Goals**:
- **Fast Reads**: <100ms P95 latency for leaderboard fetches (cached + indexed)
- **Accurate Updates**: Update within 5 minutes of ranking change (trade-off: real-time vs performance)
- **Flexible Filtering**: By game, region, time period, tournament, team
- **Fair Ranking**: Handle ties, inactive players, smurfs, cheaters (policy + technical)
- **Scalable**: Support 100k+ players, 1000+ concurrent viewers

---

## 2. Leaderboard Types

### 2.1 Tournament Leaderboard

**Purpose**: Rank teams/players within a specific tournament.

**Data Source**: `tournaments.TournamentTeam.placement` + `tournaments.Match.winner` + points system

**Ranking Criteria** (priority order):
1. Tournament placement (1st > 2nd > 3rd > ...)
2. Match wins (if tied placement)
3. Head-to-head record (if tied wins)
4. Total points scored (game-specific, e.g., kills in Battle Royale)
5. Registration timestamp (earlier = tie-breaker)

**Update Cadence**: Real-time after each match result

**Visibility**: Public (tournament page, homepage carousel)

**Example Query**:
```sql
SELECT
  team.id,
  team.name,
  tt.placement,
  COUNT(m.id) FILTER (WHERE m.winner_id = team.id) AS wins,
  COUNT(m.id) FILTER (WHERE m.winner_id != team.id) AS losses,
  tt.points
FROM tournaments_tournamentteam tt
JOIN teams_team team ON tt.team_id = team.id
LEFT JOIN tournaments_match m ON (m.team1_id = team.id OR m.team2_id = team.id)
WHERE tt.tournament_id = ?
GROUP BY team.id, tt.placement, tt.points
ORDER BY tt.placement ASC, wins DESC, tt.points DESC, tt.registered_at ASC;
```

---

### 2.2 Global Seasonal Leaderboard

**Purpose**: Rank players across all tournaments within a season (e.g., Q4 2025).

**Data Source**: Aggregated tournament placements + coins earned + match wins

**Ranking Criteria**:
1. Total season points (weighted by tournament tier: Premier=100, Standard=50, Community=25)
2. Total coins earned
3. Total match wins
4. Tournament participation count (activity bonus)

**Update Cadence**: Hourly (too expensive to compute real-time)

**Visibility**: Public (homepage, /leaderboards/seasonal page)

**Point Weighting Formula**:
```python
season_points = sum(
    tournament_placement_points(placement) * tournament_tier_multiplier(tier)
    for placement, tier in player_tournament_results
)
```

**Example Placement Points**:
- 1st place: 1000 points
- 2nd place: 750 points
- 3rd place: 500 points
- 4th-8th: 250 points
- 9th-16th: 100 points
- Participation: 25 points

**Tier Multipliers**:
- Premier: 1.0x
- Standard: 0.5x
- Community: 0.25x

---

### 2.3 All-Time Global Leaderboard

**Purpose**: Historical rankings since platform launch.

**Data Source**: Same as seasonal, but no time filter.

**Ranking Criteria**: Same as seasonal leaderboard.

**Update Cadence**: Daily (historical data, no urgency)

**Visibility**: Public (/leaderboards/all-time page)

**Staleness Acceptable**: 24-hour delay acceptable (improves cache hit rate)

---

### 2.4 Team Leaderboard

**Purpose**: Rank teams by performance (not individual players).

**Data Source**: Team win/loss records, tournament placements, roster stability

**Ranking Criteria**:
1. Team win rate (min 10 matches)
2. Total tournament wins (1st place finishes)
3. Average placement across tournaments
4. Roster stability (low turnover = bonus points)

**Update Cadence**: Hourly

**Visibility**: Public (/teams/leaderboard page)

---

### 2.5 Game-Specific Leaderboard

**Purpose**: Rank players within a single game (e.g., "Top Valorant Players").

**Data Source**: Filtered by `Tournament.game_config.game`

**Ranking Criteria**: Same as global seasonal, but filtered by game.

**Update Cadence**: Hourly

**Visibility**: Public (/leaderboards/valorant, /leaderboards/efootball pages)

---

### 2.6 Player Profile Rank History

**Purpose**: Show individual player's rank over time (line chart).

**Data Source**: Daily snapshots of player's rank position.

**Display**: Time-series line chart (rank position vs date)

**Update Cadence**: Daily snapshot

**Visibility**: Player profile page

---

## 3. Data Model

### 3.1 LeaderboardEntry (Denormalized Cache Table)

Pre-computed leaderboard entries for fast reads.

```python
class LeaderboardEntry(models.Model):
    leaderboard_type = models.CharField(
        max_length=50,
        choices=[
            ("tournament", "Tournament"),
            ("seasonal", "Seasonal"),
            ("all_time", "All-Time"),
            ("team", "Team"),
            ("game_specific", "Game-Specific"),
        ]
    )
    
    # Scope (what leaderboard is this for?)
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )  # For tournament leaderboards
    game = models.CharField(max_length=100, null=True, blank=True)  # For game-specific
    season = models.CharField(max_length=50, null=True, blank=True)  # For seasonal (e.g., "2025_Q4")
    
    # Entity (who is ranked?)
    player = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    team = models.ForeignKey(
        "teams.Team",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    
    # Ranking
    rank = models.IntegerField()  # 1, 2, 3, ...
    points = models.IntegerField(default=0)  # Total points
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # e.g., 75.50
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)  # Inactive players hidden after 30 days
    
    class Meta:
        unique_together = [
            ("leaderboard_type", "tournament", "player"),
            ("leaderboard_type", "tournament", "team"),
            ("leaderboard_type", "game", "season", "player"),
        ]
        indexes = [
            models.Index(fields=["leaderboard_type", "rank"]),
            models.Index(fields=["leaderboard_type", "tournament", "rank"]),
            models.Index(fields=["leaderboard_type", "game", "season", "rank"]),
            models.Index(fields=["player", "leaderboard_type"]),
            models.Index(fields=["team", "leaderboard_type"]),
        ]
```

### 3.2 LeaderboardSnapshot (Historical Tracking)

Daily snapshots of player/team ranks for trend analysis.

```python
class LeaderboardSnapshot(models.Model):
    date = models.DateField()
    leaderboard_type = models.CharField(max_length=50)
    player = models.ForeignKey("accounts.User", null=True, on_delete=models.CASCADE)
    team = models.ForeignKey("teams.Team", null=True, on_delete=models.CASCADE)
    rank = models.IntegerField()
    points = models.IntegerField()
    
    class Meta:
        unique_together = [("date", "leaderboard_type", "player"), ("date", "leaderboard_type", "team")]
        indexes = [
            models.Index(fields=["player", "date"]),
            models.Index(fields=["team", "date"]),
        ]
```

---

## 4. Computation & Caching

### 4.1 Computation Strategy

**Tournament Leaderboards**: Computed on-demand (cheap, small scope)

**Seasonal/All-Time/Game-Specific**: Pre-computed hourly via Celery task

**Team Leaderboards**: Pre-computed hourly

**Player Rank History**: Snapshotted daily at 00:00 UTC

### 4.2 Celery Tasks

```python
# tasks.py

@app.task
def compute_seasonal_leaderboard(season: str):
    """
    Compute seasonal leaderboard for all players.
    
    1. Clear existing LeaderboardEntry rows for (seasonal, season)
    2. Aggregate tournament results from all tournaments in season
    3. Apply point weighting (tier multipliers)
    4. Rank players by total points
    5. Bulk create LeaderboardEntry rows
    6. Cache top 100 in Redis (key: leaderboard:seasonal:{season})
    """
    pass


@app.task
def compute_game_specific_leaderboard(game: str, season: str):
    """
    Compute game-specific seasonal leaderboard.
    
    Same as compute_seasonal_leaderboard, but filter by game.
    """
    pass


@app.task
def snapshot_leaderboards():
    """
    Daily task: snapshot all leaderboards for historical tracking.
    
    Run at 00:00 UTC via cron.
    """
    pass
```

### 4.3 Redis Caching

**Keys**:
- `leaderboard:tournament:{tournament_id}` → Top 50 teams (TTL: 5 minutes)
- `leaderboard:seasonal:{season}` → Top 100 players (TTL: 1 hour)
- `leaderboard:all_time` → Top 100 players (TTL: 24 hours)
- `leaderboard:game:{game}:{season}` → Top 100 players (TTL: 1 hour)
- `leaderboard:team` → Top 50 teams (TTL: 1 hour)

**Invalidation**: Clear cache after Celery task completes.

---

## 5. API Endpoints

### 5.1 GET /api/leaderboards/tournament/<tournament_id>

**Response**:
```json
{
  "leaderboard_type": "tournament",
  "tournament": {
    "id": 501,
    "name": "Valorant Champions Q4 2025"
  },
  "entries": [
    {
      "rank": 1,
      "team": {
        "id": 101,
        "name": "Team Alpha",
        "logo_url": "https://cdn.deltacrown.gg/teams/101.png"
      },
      "wins": 12,
      "losses": 2,
      "points": 1250
    },
    ...
  ],
  "last_updated": "2025-11-13T14:42:15Z"
}
```

### 5.2 GET /api/leaderboards/seasonal?season=2025_Q4&game=valorant

**Response**:
```json
{
  "leaderboard_type": "seasonal",
  "season": "2025_Q4",
  "game": "valorant",
  "entries": [
    {
      "rank": 1,
      "player": {
        "id": 2001,
        "username": "ProPlayer123",
        "avatar_url": "https://cdn.deltacrown.gg/avatars/2001.jpg"
      },
      "points": 5400,
      "wins": 48,
      "losses": 12,
      "win_rate": 80.0,
      "tournaments_played": 8
    },
    ...
  ],
  "last_updated": "2025-11-13T14:00:00Z"
}
```

### 5.3 GET /api/leaderboards/player/<player_id>/history

**Response**:
```json
{
  "player": {
    "id": 2001,
    "username": "ProPlayer123"
  },
  "leaderboard_type": "seasonal",
  "season": "2025_Q4",
  "history": [
    {"date": "2025-11-01", "rank": 15, "points": 2400},
    {"date": "2025-11-02", "rank": 12, "points": 2650},
    {"date": "2025-11-03", "rank": 10, "points": 2900},
    ...
    {"date": "2025-11-13", "rank": 1, "points": 5400}
  ]
}
```

---

## 6. UI Components

### 6.1 Leaderboard Widget

**Location**: Homepage, tournament pages, team pages

**Design**:
```
┌─────────────────────────────────────┐
│  🏆 Top Players - Valorant Q4 2025 │
├────┬─────────────────┬──────┬──────┤
│ #  │ Player          │ W-L  │ Pts  │
├────┼─────────────────┼──────┼──────┤
│ 1  │ 👤 ProPlayer123 │ 48-12│ 5400 │
│ 2  │ 👤 SkillMaster  │ 45-15│ 5200 │
│ 3  │ 👤 TopFragger   │ 42-18│ 4800 │
│ .. │ ...             │ ...  │ ...  │
│ 25 │ 👤 RisingStar   │ 30-30│ 3200 │
└────┴─────────────────┴──────┴──────┘
     [View Full Leaderboard →]
```

**Props**:
- `leaderboard_type` (tournament, seasonal, all_time, team, game_specific)
- `limit` (default: 10, max: 50)
- `show_filters` (boolean, enable game/season filters)

**Django Template Tag**:
```django
{% load leaderboards %}
{% leaderboard "seasonal" limit=10 game="valorant" season="2025_Q4" %}
```

---

## 7. Business Rules

### 7.1 Tie-Breaking

When multiple players have same points:
1. Total wins (more wins = higher rank)
2. Win rate (higher % = higher rank)
3. Tournament participation count (more active = higher rank)
4. Registration date (earlier = higher rank)

### 7.2 Inactive Players

Players with no activity in last 30 days are marked `is_active=False` and hidden from public leaderboards (but still in database).

### 7.3 Minimum Participation Threshold

Seasonal leaderboards require ≥3 tournaments played to appear in rankings (prevent "one-hit wonders").

### 7.4 Cheater/Smurf Handling

Players flagged as cheaters/smurfs are removed from leaderboards (soft delete: `is_active=False`, `ban_reason="cheating"`).

---

## 8. Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Fetch Latency (P95)** | <100ms | /api/leaderboards/* endpoints |
| **Cache Hit Rate** | >90% | Redis cache for top 100 |
| **Computation Time** | <5min | Hourly Celery task |
| **Database Load** | <10 QPS | SELECT from LeaderboardEntry (indexed) |
| **Concurrent Viewers** | 1000+ | No degradation under load |

---

## 9. Implementation Phases

### Phase 1: Tournament Leaderboards (v6.0)
- Create `LeaderboardEntry` model
- Implement tournament leaderboard computation (real-time)
- Add `/api/leaderboards/tournament/<id>` endpoint
- Create leaderboard widget UI component
- Tests: ≥20 tests (ranking logic, ties, API)

### Phase 2: Seasonal & All-Time (v6.1)
- Implement seasonal leaderboard Celery task
- Add Redis caching layer
- Add `/api/leaderboards/seasonal` endpoint
- Tests: ≥15 tests (computation, caching, filters)

### Phase 3: Player Rank History (v6.2)
- Create `LeaderboardSnapshot` model
- Implement daily snapshot task
- Add `/api/leaderboards/player/<id>/history` endpoint
- Create rank history chart UI component
- Tests: ≥10 tests (snapshots, trends)

### Phase 4: Team & Game-Specific (v6.3)
- Implement team leaderboard computation
- Implement game-specific leaderboard filtering
- Add `/api/leaderboards/team` endpoint
- Tests: ≥12 tests (team rankings, game filters)

---

## 10. Open Questions

1. **Should we show "rank change" arrows (↑ ↓) in UI?**
   - Requires comparing today's rank vs yesterday's rank (need daily snapshots)
   - Decision: YES (adds engagement), implement in Phase 3

2. **How to handle multi-game players?**
   - Player plays both Valorant and eFootball
   - Decision: Separate leaderboards per game (player can appear in both)

3. **Should tournament participation count toward seasonal points even if player loses all matches?**
   - Decision: YES (25 participation points) to encourage activity

4. **How to handle team roster changes mid-season?**
   - Player switches teams halfway through season
   - Decision: Points follow the player, not the team (player leaderboard)

5. **Should we expose leaderboard API publicly (no auth)?**
   - Decision: YES (public read-only, no sensitive data)

---

## 11. Success Metrics

After v6.0 launch, track:
- Leaderboard page views (target: 10k/week)
- Average time on leaderboard page (target: >2 minutes)
- Cache hit rate (target: >90%)
- P95 latency (target: <100ms)
- User engagement (comments like "I'm rank 50, climbing!")

---

**Approval Required**: Product Manager, Engineering Lead  
**Target Release**: Q1 2026  
**Estimated Effort**: 120 engineering hours (4 phases × 30 hours)
