# 06 — Ecosystem Expansion Plan

*Connecting the Tournament Engine to Economy, Leaderboards, Competition, and Notifications for a production-grade esports platform.*

**Author:** Copilot (Principal Architect)
**Date:** February 20, 2026
**Status:** PLANNING — Awaiting Review
**Predecessor:** `05_IMPLEMENTATION_TRACKER.md` (Phase 1–4 Complete, 180 tests passing)

---

## Executive Summary

DeltaCrown's Tournament Engine (Phases 1–4) is now feature-complete: Smart Registration, Guest Teams, TOC, Bracket Engine, Match Medic, DeltaCoin Payment, Live Draw, and 11 notification event handlers — all tested and operational.

However, these systems currently operate in **silos**. The critical gap is the **connective tissue** between tournament match results and the rest of the platform:

| Signal | Current State | Target State |
|--------|--------------|--------------|
| Match completes → Player/Team stats update | Event handler exists but **feature-flagged OFF** | Automatic, real-time |
| Tournament ends → Prize pool distributed | `award_placements()` is **deprecated/stub** | Automated DeltaCoin payouts |
| Match result → ELO/MMR recalculated | ELO formula exists but **not wired to tournament matches** | Automatic after every match |
| Season ends → Rankings archived | Season model exists but **no rollover logic** | Automated seasonal snapshots |
| Achievement unlocked → Notification + Reward | Neither exists | Event-driven rewards engine |

This plan builds the **six integration pipelines** needed to make DeltaCrown a cohesive ecosystem.

---

## Architecture Audit Summary

### What Already Exists (Built & Tested)

| Component | Location | Readiness |
|-----------|----------|-----------|
| **Tournaments Engine** | `apps/tournaments/` | 95% — 180 tests |
| **DeltaCoin Ledger** | `apps/economy/services.py` | 75% — idempotent credit/debit with row-locking |
| **CoinPolicy** | `apps/economy/models.py` | Built — per-tournament payout amounts (winner/runner-up/top4/participation) |
| **ELO Formula** | `apps/tournament_ops/services/team_stats_service.py` | Built — K=32, standard formula |
| **TeamRanking Model** | `apps/leaderboards/models.py` | Built — per-game ELO + peak tracking |
| **UserStats / TeamStats** | `apps/leaderboards/models.py` | Built — wins/losses/played/win_rate per game |
| **Match History** | `apps/leaderboards/models.py` | Built — UserMatchHistory + TeamMatchHistory |
| **Ranking Engine V2** | `apps/leaderboards/engine.py` | Built — 1180 lines, delta tracking, caching (flagged OFF) |
| **Event Bus** | `apps/core/events/` | Built — subscribe/publish pattern, used by 11 handlers |
| **Notifications** | `apps/notifications/` | 80% — 37 types, multi-channel, enforcement, SSE |
| **Competition Rankings** | `apps/competition/services/` | 60% — compute + snapshot + tier, not actively triggered |
| **Challenge System** | `apps/competition/` | 60% — full lifecycle, not connected to economy |
| **Webhook Delivery** | `apps/notifications/services/webhook_service.py` | 95% — HMAC-signed, circuit breaker, retry |

### What's Missing (The Gaps This Plan Fills)

| Gap | Impact | Priority |
|-----|--------|----------|
| **No automated prize distribution** | Organizers must manually pay winners | P0 — Critical |
| **Match → Stats pipeline flagged OFF** | Zero real leaderboard data | P0 — Critical |
| **No tournament → ELO bridge** | Tournament matches don't affect rankings | P0 — Critical |
| **No seasonal rollover** | Seasons exist but don't reset/archive | P1 — High |
| **No achievement/reward engine** | No engagement loop beyond tournaments | P1 — High |
| **No payment gateway** | All top-ups are admin-manual | P2 — Medium |
| **No matchmaking for challenges** | Players can't find ranked opponents | P2 — Medium |
| **No fraud detection** | No anti-smurf, no transaction anomaly detection | P2 — Medium |
| **No push notifications** | Mobile users get no real-time alerts | P3 — Low |

---

## Industry Research: How Top Platforms Do It

### FACEIT

- **ELO System:** Modified Glicko-2 with K-factor that decreases with games played (volatile new players, stable veterans). Separate ELO per game. Placement matches (10 games, higher K).
- **Leaderboards:** Per-game, per-region, monthly + all-time. Reset monthly ladders but keep all-time intact.
- **Rewards:** Premium subscribers earn FACEIT Points automatically per game played. Winners of organized tournaments get direct prize pool distribution (PayPal/bank). Hub-level leaderboard prizes distributed weekly.
- **Anti-cheat:** Client-side AC mandatory for ranked. Game-specific stat thresholds for smurf detection.

### Toornament

- **Rankings:** Custom ranking formulas per tournament series (points-based, not ELO). Series standings aggregate across multiple tournaments.
- **Prize Distribution:** Manual — organizer handles payouts externally. Toornament doesn't touch money.
- **Integration:** Strong API-first approach. Webhooks fire for every match result, bracket update, tournament status change. External systems consume webhooks for stats.

### Battlefy

- **Ladder System:** Separate from tournaments. Ladders use win/loss ratio + amount played for rankings. Seasonal resets.
- **Rewards:** Badge/achievement system for milestones (first win, 10-win streak, tournament champion). Virtual currency (Battlefy Points) for cosmetics.
- **Prize Distribution:** Integrated with PayPal for online payouts. Escrow-like hold during tournament, auto-release on completion.

### Key Takeaways for DeltaCrown

1. **ELO should be per-game, with placement volatility** (high K for first 10 matches, lower after)
2. **Leaderboards must have both seasonal and all-time views** with monthly snapshots
3. **Prize distribution must be automated** with escrow (hold entry fees, release to winners)
4. **Achievement/badge system drives retention** — lightweight to build, high engagement ROI
5. **Webhook-based integration** is industry standard for extensibility

---

## Integration Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EVENT BUS (apps.core.events)                    │
│                                                                     │
│  match.completed ──┬──► StatsHandler ──► UserStats / TeamStats     │
│                    ├──► ELOHandler ──► TeamRanking (per-game)       │
│                    ├──► HistoryHandler ──► MatchHistory records     │
│                    └──► LeaderboardHandler ──► Engine V2 recompute  │
│                                                                     │
│  tournament.completed ──┬──► PrizeHandler ──► DeltaCoin payouts    │
│                         ├──► AchievementHandler ──► Badge awards    │
│                         └──► SeasonHandler ──► Season points        │
│                                                                     │
│  challenge.settled ──┬──► ELOHandler ──► Team ELO update           │
│                      └──► WagerHandler ──► DeltaCoin transfer      │
│                                                                     │
│  season.ended ──┬──► ArchiveHandler ──► Snapshot + Reset           │
│                 └──► RewardHandler ──► Season prizes               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phased Execution Roadmap

### Phase 5: Match → Stats Pipeline (Foundation)

*Goal: When a tournament match completes, player/team stats update automatically.*

| Task | Description | Files |
|------|-------------|-------|
| **P5-T01** | **Enable & harden match.completed event emission** — Ensure every tournament match completion (via `winner_service`, `match_service`, `result_submission_service`) emits a `match.completed` event with match_id, tournament_id, winner_id, loser_id, scores, game_slug. Currently the event fires but data payload is inconsistent. | `apps/tournaments/services/winner_service.py`, `apps/tournaments/services/match_service.py` |
| **P5-T02** | **Wire stats handler to tournament match events** — The `leaderboards/event_handlers.py` handler exists but references `tournament_ops` DTOs. Refactor to consume the new normalized `match.completed` payload directly. Update UserStats + TeamStats atomically. | `apps/leaderboards/event_handlers.py` |
| **P5-T03** | **Wire ELO update to tournament matches** — On `match.completed`, call `TeamStatsService.calculate_elo_change()` and persist via `TeamRankingAdapter.update_elo_rating()`. Add placement match logic: K=64 for first 10 matches, K=32 after. | `apps/tournament_ops/services/team_stats_service.py`, `apps/tournament_ops/adapters/team_ranking_adapter.py` |
| **P5-T04** | **Wire match history creation** — On `match.completed`, create `UserMatchHistory` and `TeamMatchHistory` rows with ELO before/after snapshots. | `apps/leaderboards/event_handlers.py` |
| **P5-T05** | **Enable Ranking Engine V2** — Remove feature flag gating. Run `compute_tournament_rankings()` after each match. Enable Redis caching for leaderboard reads. | `apps/leaderboards/engine.py`, `apps/leaderboards/tasks.py`, `deltacrown/settings.py` |

**Exit Criteria:**
- [ ] Every completed tournament match creates UserStats + TeamStats entries
- [ ] ELO ratings update after every match (K=64 placement, K=32 standard)
- [ ] Match history rows created with ELO snapshots
- [ ] Leaderboard Engine V2 enabled and computing
- [ ] All existing 180 tests still pass + 15+ new tests

---

### Phase 6: Automated Prize Distribution

*Goal: When a tournament completes, winners automatically receive DeltaCoin payouts.*

| Task | Description | Files |
|------|-------------|-------|
| **P6-T01** | **Build PrizeDistributionService** — New service that reads `CoinPolicy` for the tournament and distributes prizes to winner, runner-up, top-4, and participation slots. Uses `economy_services.credit()` with idempotency keys (`prize_{tournament_id}_{placement}_{user_id}`). | `apps/tournaments/services/prize_distribution_service.py` (NEW) |
| **P6-T02** | **Wire to tournament.completed event** — Subscribe `PrizeDistributionService.distribute()` to the `tournament.completed` event. Handle edge cases: no CoinPolicy set (skip), already distributed (idempotency), DQ'd players (excluded). | `apps/tournaments/services/prize_distribution_service.py` |
| **P6-T03** | **Entry fee escrow** — When players pay DeltaCoin entry fees, hold the amount in a tournament escrow (new `TournamentEscrow` model or a designated wallet). On completion, combine escrow + organizer prize pool for total distribution. On cancellation, refund all escrowed fees. | `apps/economy/models.py` (TournamentEscrow), `apps/tournaments/services/payment_service.py` |
| **P6-T04** | **Prize distribution dashboard** — TOC module showing distribution status: who received what, pending payouts, failed transactions. Read-only. | `templates/tournaments/manage/prizes.html` (NEW) |
| **P6-T05** | **Organizer payout configuration** — Allow organizers to customize prize splits via TOC Settings (e.g., 50%/30%/10%/10% or fixed amounts). Falls back to CoinPolicy defaults. | `apps/tournaments/models/tournament.py`, `templates/tournaments/manage/settings.html` |

**Exit Criteria:**
- [ ] Tournament completion triggers automatic DeltaCoin distribution
- [ ] Idempotent — running twice does not double-pay
- [ ] Entry fees escrowed and distributed or refunded
- [ ] Organizer can customize prize splits
- [ ] 10+ new tests

---

### Phase 7: Seasonal Rankings & Leaderboards

*Goal: Competitive seasons with automated rollover, decay, and archival.*

| Task | Description | Files |
|------|-------------|-------|
| **P7-T01** | **Season lifecycle management** — Wire Season model to Celery beat: auto-close season on `end_date`, archive all rankings to `LeaderboardSnapshot`, reset ELO to 1200 (or weighted carry-over: `1200 + (current - 1200) * 0.5`). | `apps/leaderboards/tasks.py`, `apps/leaderboards/models.py` |
| **P7-T02** | **ELO decay for inactive players** — Celery weekly task: players/teams with 0 matches in 14+ days lose ELO proportional to inactivity (max -50/week, floor 1000). Uses `decay_rules_json` on Season model. | `apps/leaderboards/tasks.py` (NEW task) |
| **P7-T03** | **Seasonal leaderboard views** — Frontend pages showing current season standings with rank, ELO, wins, trend arrow (up/down from last snapshot). Filter by game, region. | `apps/leaderboards/views.py`, `templates/leaderboards/` |
| **P7-T04** | **All-time leaderboard** — Separate permanent leaderboard that never resets. Cumulative points from all seasons. | `apps/leaderboards/services.py` |
| **P7-T05** | **User/Team analytics snapshots** — Nightly Celery task computing `UserAnalyticsSnapshot` and `TeamAnalyticsSnapshot` (tier, percentile, KDA, streaks). Power the profile stats cards. | `apps/leaderboards/tasks.py` |

**Exit Criteria:**
- [ ] Seasons auto-close and archive rankings
- [ ] ELO decays for inactive players/teams
- [ ] Seasonal + all-time leaderboard pages working
- [ ] Nightly analytics snapshots computing
- [ ] 12+ new tests

---

### Phase 8: Achievement & Rewards Engine

*Goal: Event-driven achievement system that awards badges, DeltaCoin, and inventory items.*

| Task | Description | Files |
|------|-------------|-------|
| **P8-T01** | **Achievement model & catalog** — New models: `Achievement` (slug, name, description, icon, category, rarity, criteria_json, reward_type, reward_amount) and `UserAchievement` (user FK, achievement FK, earned_at, progress). Categories: Tournament (first win, 10 wins, champion), Social (first team, first org), Economy (first purchase, whale), Competitive (10-win streak, Diamond tier). | `apps/leaderboards/models.py` or `apps/achievements/` (NEW) |
| **P8-T02** | **Achievement evaluation engine** — On relevant events (match.completed, tournament.completed, season.ended), evaluate achievement criteria against user stats. Award if unearned. Support progress tracking (e.g., "5/10 tournament wins"). | `apps/achievements/services.py` (NEW) |
| **P8-T03** | **Achievement rewards integration** — When achievement earned, dispatch rewards: DeltaCoin credit, inventory item grant, notification. Use economy `credit()` with reason=`ACHIEVEMENT_REWARD`. | `apps/achievements/services.py` |
| **P8-T04** | **Achievement display** — Profile section showing earned achievements with badges. "Trophy case" on public profile. Achievement unlock notification. | `templates/user_profile/achievements.html` (NEW) |

**Exit Criteria:**
- [ ] 15+ achievements in catalog covering tournament, social, economy categories
- [ ] Achievements auto-evaluate on match/tournament completion
- [ ] Rewards (DeltaCoin + items) automatically granted
- [ ] Achievements visible on user profiles
- [ ] 10+ new tests

---

### Phase 9: Competition App Integration

*Goal: Wire the Challenge/Bounty system to economy and rankings.*

| Task | Description | Files |
|------|-------------|-------|
| **P9-T01** | **Challenge settling → DeltaCoin** — When a wager challenge is settled, transfer DeltaCoin from loser's wallet to winner's wallet (minus platform fee). Use `economy_services.transfer()`. | `apps/competition/services/challenge_service.py` |
| **P9-T02** | **Challenge results → ELO** — Ranked challenges update team ELO using the same pipeline as tournament matches. Weight: challenges count as 0.5x the ELO impact of tournament matches. | `apps/competition/services/challenge_service.py` |
| **P9-T03** | **Bounty claim → Economy** — When a bounty claim is verified, credit the claimer's wallet. Debit the issuer's wallet (held at bounty creation time). | `apps/competition/services/bounty_service.py` (NEW) |
| **P9-T04** | **Simple matchmaking** — "Find Opponent" feature: match teams by ELO proximity (±200 range), same game, both online. Create a challenge automatically. | `apps/competition/services/matchmaking_service.py` (NEW) |

**Exit Criteria:**
- [ ] Wager challenges auto-settle with DeltaCoin transfer
- [ ] Ranked challenges affect ELO (0.5x weight)
- [ ] Bounty payouts work end-to-end
- [ ] Basic ELO-based matchmaking functional
- [ ] 8+ new tests

---

### Phase 10: Notification & Observability Hardening

*Goal: Complete the notification delivery story and add platform observability.*

| Task | Description | Files |
|------|-------------|-------|
| **P10-T01** | **WebSocket notification delivery** — Replace SSE polling with WebSocket push for instant notification bell updates. Use existing Django Channels infrastructure. | `apps/notifications/consumers.py` (NEW), `apps/notifications/sse.py` |
| **P10-T02** | **Notification grouping/collapse** — Group similar notifications: "5 new followers" instead of 5 separate items. Collapse tournament bulk notifications. | `apps/notifications/services.py` |
| **P10-T03** | **Discord webhook delivery** — Wire the existing `opt_out_discord` preference to actual Discord webhook delivery for tournament events. | `apps/notifications/tasks.py` |
| **P10-T04** | **Admin observability dashboard** — Grafana-ready metrics: tournaments created/day, avg match duration, payment success rate, notification delivery rate, API response times. | `deltacrown/metrics.py`, `grafana/` |
| **P10-T05** | **Transaction fraud detection** — Flag suspicious patterns: >10 transactions/minute, >5000 DC transferred in 1 hour, same-IP multi-account transfers. Alert via admin notification. | `apps/economy/fraud_detection.py` (NEW) |

**Exit Criteria:**
- [ ] WebSocket notifications replace SSE
- [ ] Notification grouping reduces spam
- [ ] Discord webhooks functional
- [ ] Observability metrics exported
- [ ] Basic fraud detection alerting
- [ ] 8+ new tests

---

## Implementation Priority Matrix

```
                    HIGH IMPACT
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
    │   Phase 5         │   Phase 6         │
    │   Match→Stats     │   Prize Payouts   │
    │   (FOUNDATION)    │   (REVENUE)       │
    │                   │                   │
LOW ├───────────────────┼───────────────────┤ HIGH
EFFORT│                 │                   │ EFFORT
    │   Phase 8         │   Phase 9         │
    │   Achievements    │   Competition     │
    │   (ENGAGEMENT)    │   Integration     │
    │                   │                   │
    │   Phase 7         │   Phase 10        │
    │   Seasons         │   Notif + Obs     │
    │   (RETENTION)     │   (HARDENING)     │
    │                   │                   │
    └───────────────────┼───────────────────┘
                        │
                    LOW IMPACT
```

**Recommended Execution Order:**
1. **Phase 5** (Match → Stats) — Foundation for everything else
2. **Phase 6** (Prize Distribution) — Revenue-critical, organizer trust
3. **Phase 7** (Seasons) — Retention driver, builds on Phase 5
4. **Phase 8** (Achievements) — Engagement loop, builds on Phase 5 + 6
5. **Phase 9** (Competition) — Extends existing challenge system
6. **Phase 10** (Hardening) — Polish pass before production launch

---

## Data Flow Diagrams

### Match Completion Pipeline

```
Tournament Match Completed
    │
    ├─ winner_service.py sets match.winner_id
    │
    ├─ event_bus.publish(match.completed)
    │       │
    │       ├─► [StatsHandler] ──► UPDATE UserStats SET wins+=1 WHERE user=winner
    │       │                  ──► UPDATE UserStats SET losses+=1 WHERE user=loser
    │       │                  ──► UPDATE TeamStats (same pattern)
    │       │
    │       ├─► [ELOHandler]   ──► calculate_elo_change(winner_elo, loser_elo, K)
    │       │                  ──► UPDATE TeamRanking SET elo=new, peak=max(new,peak)
    │       │
    │       ├─► [HistoryHandler] ──► INSERT UserMatchHistory (elo_before, elo_after)
    │       │                    ──► INSERT TeamMatchHistory (elo_before, elo_after)
    │       │
    │       ├─► [LeaderboardHandler] ──► engine.compute_with_deltas(tournament)
    │       │                        ──► cache.invalidate(game_leaderboard)
    │       │
    │       └─► [AchievementHandler] ──► evaluate_criteria(user, "10_wins")
    │                                ──► IF earned: credit(wallet, 50, "achievement")
    │
    └─ If final match → event_bus.publish(tournament.completed)
            │
            ├─► [PrizeHandler] ──► CoinPolicy.get_for_tournament()
            │                  ──► credit(winner_wallet, winner_amount)
            │                  ──► credit(runner_up_wallet, runner_up_amount)
            │                  ──► credit(top4_wallets, top4_amount)
            │                  ──► credit(all_wallets, participation_amount)
            │
            └─► [SeasonHandler] ──► season.add_points(winner, tournament_weight)
```

### Prize Distribution Flow

```
Tournament Created (entry_fee > 0)
    │
    ├─ Registration confirmed → debit(player_wallet, entry_fee)
    │                        → credit(escrow_wallet, entry_fee)
    │
    ├─ Tournament cancelled → refund all: debit(escrow) + credit(player)
    │
    └─ Tournament completed → PrizeDistributionService.distribute()
            │
            ├─ Read CoinPolicy OR custom prize_split config
            ├─ Calculate distribution:
            │     total_pool = escrow_balance + organizer_prize_pool
            │     winner_payout = total_pool * split.winner_pct
            │     runner_up_payout = total_pool * split.runner_up_pct
            │     ...
            ├─ For each placement:
            │     credit(player_wallet, payout, idempotency="prize_{t_id}_{place}_{u_id}")
            │     notify(player, "prize_distributed", amount, tournament)
            └─ Mark tournament.prizes_distributed = True
```

---

## Model Changes Required

### New Models

| Model | App | Purpose |
|-------|-----|---------|
| `TournamentEscrow` | economy | Holds entry fees during tournament lifecycle |
| `PrizeDistribution` | tournaments | Records each payout (who, how much, placement, txn_id) |
| `Achievement` | achievements (NEW) | Achievement catalog (slug, criteria, rewards) |
| `UserAchievement` | achievements | User's earned achievements + progress tracking |

### Model Modifications

| Model | Change |
|-------|--------|
| `Tournament` | Add `prizes_distributed` (BooleanField), `prize_split_config` (JSONField) |
| `Season` | Add `is_archived` (BooleanField), `final_snapshot_id` (FK to LeaderboardSnapshot) |
| `TeamRanking` | Add `placement_matches_played` (IntegerField) for K-factor logic |
| `CoinPolicy` | Add FK to Tournament model (replace legacy integer `tournament_id`) |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Double-paying prizes on retry | Medium | Critical | Idempotency keys on every `credit()` call |
| ELO manipulation via challenge farming | Medium | High | Rate-limit challenges per team/day, anti-smurf ELO floor |
| Escrow accounting mismatch | Low | Critical | Dual-entry bookkeeping, reconciliation Celery task |
| Leaderboard compute cost at scale | Medium | Medium | Redis caching, incremental updates, Engine V2 partial recompute |
| Achievement criteria race condition | Low | Low | Evaluate inside `transaction.atomic()` with `select_for_update` |
| Season rollover during live tournament | Low | High | Block rollover if any tournament in `live` status for that game |

---

## Test Strategy

| Phase | New Tests | Cumulative |
|-------|-----------|------------|
| Phase 5 (Stats) | ~15 | ~195 |
| Phase 6 (Prizes) | ~10 | ~205 |
| Phase 7 (Seasons) | ~12 | ~217 |
| Phase 8 (Achievements) | ~10 | ~227 |
| Phase 9 (Competition) | ~8 | ~235 |
| Phase 10 (Hardening) | ~8 | ~243 |

Each phase has its own exit criteria requiring all prior tests to remain green plus new tests.

---

## Timeline Estimate

| Phase | Complexity | Estimated Sessions |
|-------|-----------|-------------------|
| Phase 5 | Medium | 2 sessions |
| Phase 6 | High | 2–3 sessions |
| Phase 7 | Medium | 2 sessions |
| Phase 8 | Medium | 1–2 sessions |
| Phase 9 | Medium | 1–2 sessions |
| Phase 10 | Medium | 2 sessions |
| **Total** | | **10–13 sessions** |

---

## Dependencies

```
Phase 5 (Stats) ──► Phase 7 (Seasons) ──► Phase 7 complete
     │                                         │
     └──► Phase 6 (Prizes) ──────────────────► Phase 8 (Achievements)
     │
     └──► Phase 9 (Competition Integration)
     
Phase 10 (Hardening) — independent, can run in parallel after Phase 5
```

---

> **Ready for review.** Phase 5 can begin immediately upon approval — it has zero external dependencies and unblocks all subsequent phases.
