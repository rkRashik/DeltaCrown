# DeltaCrown Competitive System Design

> Phase 18–19 — Skill + Activity + Seasons + ELO
> Effective: March 2026

---

## 1. CP (CROWN POINTS) — SKILL-BASED RANKING

### 1.1 Win/Loss CP Logic (CONFIRMED)

| Result | Base CP | Floor | Ceiling |
|--------|---------|-------|---------|
| WIN    | +100    | +50   | +300    |
| LOSS   | -30     | -100  | -10     |
| DRAW   | +10     | fixed | fixed   |

**Opponent Tier Weighting:**
```
multiplier = 1.0 + (opponent_tier_value × 0.06)

Tier values: ROOKIE=0, CHALLENGER=1, ELITE=2, MASTER=3,
             LEGEND=4, THE_CROWN=5
```

Example: Beating a LEGEND (4) opponent → 100 × 1.24 = 124 base CP

### 1.2 Streak Bonuses (CONFIRMED)

| Win Streak | Bonus |
|------------|-------|
| 3–5 wins   | +10%  |
| 6–9 wins   | +20%  |
| 10+ wins   | +30% (HARD CAP) |

Streak resets to 0 on any loss.

### 1.3 Tier Thresholds (Phase 19 — Rebranded)

| Tier       | Min CP  |
|------------|---------|
| The Crown  | 30,000  |
| Legend     |  8,000  |
| Master     |  2,000  |
| Elite      |    500  |
| Challenger |    100  |
| Rookie     |      0  |

### 1.4 ELO Rating System (Phase 19 — INTERNAL ONLY)

ELO powers CP scaling but is **never exposed** to users, API, or frontend.

**Parameters:**
- Default ELO: 1200
- K-factor: 32
- Floor: 100 (minimum ELO)

**Standard ELO Formula:**
```
Expected(A) = 1 / (1 + 10^((B_elo - A_elo) / 400))
Δ_elo = K × (actual - expected)
```

**ELO → CP Scaling:**
After computing base CP from tier/streak, multiply by surprise factor:
```
elo_diff = loser_elo - winner_elo   (positive = underdog win)
elo_scale_win  = clamp(1.0 + elo_diff/800, 0.5, 1.6)
elo_scale_loss = clamp(1.0 - elo_diff/800, 0.5, 1.6)
```

| Scenario              | ELO Scale | CP Effect          |
|-----------------------|-----------|--------------------|
| Beat stronger team    | 1.0–1.6x  | Higher CP gain     |
| Beat weaker team      | 0.5–1.0x  | Lower CP gain      |
| Lose to weaker team   | 1.0–1.6x  | Harsher CP penalty  |
| Lose to stronger team | 0.5–1.0x  | Softer CP penalty   |

CP floor/ceiling (+50/+300 win, -10/-100 loss) still applies after ELO scaling.

### 1.4 Anti-Farming (CONFIRMED + NEW)

**Existing:**
- CP floor/ceiling per match (50–300 win, 10–100 loss)
- Streak bonus capped at +30%
- Opponent tier scaling (beating UNRANKED gives less)

**New — Same-Opponent Diminishing Returns:**
- 1st match vs opponent in 24h: 100% CP
- 2nd match vs same opponent in 24h: 50% CP
- 3rd+ match vs same opponent in 24h: 25% CP
- Tracked via `recent_opponents` JSONField on TeamRanking

**New — Daily Match Cap:**
- Maximum 10 ranked matches per day per team
- Matches beyond cap still play but award 0 CP
- Tracked via `matches_today` counter, reset at midnight UTC

---

## 2. ACTIVITY SYSTEM (NEW)

### 2.1 Activity Score

A **0–100 score** measuring team engagement. NOT a ranking factor —
used for badges, visibility, and season rewards only.

### 2.2 Sources

| Action                | Points | Daily Cap |
|-----------------------|--------|-----------|
| Complete a match      | +5     | 50/day    |
| Win a match           | +2     | (bonus)   |
| Tournament entry      | +10    | 30/day    |
| 7-day login streak    | +5     | 5/week    |

### 2.3 Decay

- Activity score decays by 3 points/day if no matches played
- Floor at 0, ceiling at 100

### 2.4 Storage

New fields on `TeamRanking`:
```python
activity_score      = IntegerField(default=0)    # 0–100
matches_today       = IntegerField(default=0)    # reset midnight UTC
matches_today_reset = DateField(null=True)       # last reset date
recent_opponents    = JSONField(default=dict)    # {team_id: [timestamps]}
```

### 2.5 Interaction with CP

Activity does **NOT** modify CP calculations directly.

Optional future use:
- Highlighted on leaderboard (activity badge)
- Tie-breaking for same-CP teams on leaderboard
- Season reward eligibility (must have activity_score ≥ 20)

---

## 3. SEASON SYSTEM

### 3.1 Season Duration

- **45 days** per season (6 days buffer between seasons)
- Model: `leaderboards.Season` (already exists)
- Active season gated by `is_active` flag + date range

### 3.2 Soft Reset Rules

At season end:

| Current CP   | Reset Formula          | Result        |
|-------------|------------------------|---------------|
| ≥ 40,000    | new_cp = cp × 0.40     | Keep 40%      |
| ≥ 15,000    | new_cp = cp × 0.50     | Keep 50%      |
| ≥ 5,000     | new_cp = cp × 0.60     | Keep 60%      |
| ≥ 1,500     | new_cp = cp × 0.70     | Keep 70%      |
| < 1,500     | new_cp = cp × 0.80     | Keep 80%      |

- `season_cp` resets to 0
- `all_time_cp` never resets
- `activity_score` resets to 0
- Streaks reset to 0
- Global ranks recomputed after reset

### 3.3 Season Rewards (Future — metadata only for now)

| Category        | Criteria                     |
|----------------|------------------------------|
| Top Ranked     | Top 3 by `current_cp`        |
| Most Active    | Top 3 by `activity_score`    |
| Most Improved  | Top 3 by `season_cp` gain    |
| Tier Champions | Highest CP in each tier      |

Rewards stored as JSON on Season model (no separate model needed yet).

---

## 4. ANTI-ABUSE SUMMARY

| Protection                    | Mechanism                            |
|------------------------------|--------------------------------------|
| Match spam                   | 10 ranked matches/day cap            |
| Same-opponent farming        | Diminishing returns (100→50→25% CP)  |
| Win trading                  | Opponent tier scaling                |
| CP inflation                 | Hard ceiling +300/match              |
| Inactivity exploitation      | 5% weekly decay after 7 days        |
| Streak abuse                 | +30% cap                             |
| Season CP hoarding           | Soft reset (40–80% carry-over)       |

---

## 5. MODEL CHANGES REQUIRED

### 5.1 TeamRanking — New Fields

```python
# Anti-abuse (Phase 18)
matches_today       = IntegerField(default=0)
matches_today_reset = DateField(null=True, blank=True)
recent_opponents    = JSONField(default=dict, blank=True)

# Activity (Phase 18)
activity_score      = IntegerField(default=0)

# ELO (Phase 19 — internal only)
elo_rating          = IntegerField(default=1200)
```

### 5.2 No New Models

- Season model already exists in `leaderboards.Season`
- Activity is a field, not a separate model
- Anti-abuse tracking is inline on TeamRanking
- ELO is a single field on TeamRanking (not exposed anywhere)

---

## 6. IMPLEMENTATION PLAN

1. Add 4 new fields to TeamRanking + migration (Phase 18)
2. Update `apply_match_result()` with daily cap + opponent diminishing returns
3. Update `apply_match_result()` to increment activity_score
4. Add `reset_daily_match_counters` Celery task (midnight UTC)
5. Add `apply_activity_decay` to nightly Celery beat
6. Create match simulation command
7. Validate with simulated data
8. Rebrand tiers: Rookie/Challenger/Elite/Master/Legend/The Crown (Phase 19)
9. Add ELO field + migrate existing tier values (Phase 19)
10. Implement ELO calculation + ELO→CP scaling in apply_match_result (Phase 19)
