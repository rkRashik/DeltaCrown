# DeltaCrown Product Improvement Plan
## Competitive Platform Comparison & Redesign Recommendations

**Date:** March 2026
**Scope:** /teams/ Hub, /competition/rankings/, Dashboard, Team Detail
**Reference Platforms:** FACEIT, Toornament, Battlefy

---

## 1. Executive Summary

DeltaCrown's ranking system (DCRS) has a solid backend foundation — 6-tier ELO/CP pipeline, anti-abuse mechanics, activity scoring — but the frontend UX significantly underperforms industry leaders. This document identifies specific gaps and provides actionable redesign recommendations prioritized by impact.

---

## 2. Platform Comparison Matrix

| Feature | FACEIT | Toornament | Battlefy | DeltaCrown (Current) |
|---------|--------|------------|----------|---------------------|
| **ELO/Rating System** | ✅ Per-game ELO (Levels 1-10) | ❌ No built-in rating | ❌ No built-in rating | ✅ Hidden ELO + visible CP + 6 tiers |
| **Leaderboards** | ✅ Regional/Global/Game | ✅ Per-tournament only | ✅ Per-tournament only | ⚠️ Global + per-game (no regional) |
| **Team Profiles** | ✅ Rich (stats, match history, roster) | ✅ Basic (tournament record) | ✅ Basic (tournament list) | ⚠️ Basic (tier badge, CP, no match history feed) |
| **Match History Feed** | ✅ Full timeline with stats | ⚠️ Per-tournament brackets | ⚠️ Per-tournament brackets | ❌ Missing |
| **Search & Discovery** | ✅ Game filters, region, skill level | ✅ Game/date/format/region | ✅ Game filter, platform | ⚠️ Basic search bar + tier filter (new) |
| **Player Stats Cards** | ✅ KDA, win rate, maps, headshot % | ❌ Not applicable | ❌ Not applicable | ❌ Missing |
| **Activity/Engagement Score** | ✅ FBI (FACEIT Behavior Index) | ❌ None | ❌ None | ✅ Activity Score 0-100 (in DB, partially displayed) |
| **Progression Visualization** | ✅ ELO graph over time, level badges | ❌ None | ❌ None | ❌ Missing (have data, no visualization) |
| **Social/Community** | ✅ Friends, hubs, posts | ⚠️ Organizer community | ⚠️ Discord integration | ⚠️ Team announcements exist but no social feed |
| **Notifications Hub** | ✅ Real-time (matches, invites) | ✅ Tournament notifications | ✅ Basic alerts | ⚠️ Backend exists, frontend limited |
| **Tournament Discovery** | ✅ Browse by game/region/entry/prize | ✅ Excellent filter system | ✅ Game selector on homepage | ⚠️ Tournament listing exists but weak discovery |
| **Mobile Experience** | ✅ Native app + responsive web | ⚠️ Responsive web only | ⚠️ Responsive web only | ⚠️ Responsive (Tailwind) but not optimized |
| **Real-time Updates** | ✅ WebSocket live scores | ⚠️ Polling-based | ⚠️ Polling-based | ❌ No live scores yet |

---

## 3. Critical Gaps (Ordered by Impact)

### GAP 1: No Match History Feed (HIGH IMPACT)
**What competitors do:** FACEIT shows a full chronological match timeline on every team/player profile — opponent, score, map, ELO change, duration.
**DeltaCrown current state:** Match results exist in the DB (`apps/competition/` models) but are not surfaced on team profiles or anywhere in the frontend.
**Recommendation:**
- Add a "Recent Matches" tab/section to Team Detail page
- Show: opponent name/logo, result (W/L), CP change (+/- delta), date, tournament name
- Limit to last 20 matches, lazy-load more
- Estimated backend: Query `MatchResult` → aggregate by team → paginate
- Template: Add to `_body.html` as a new tab or collapsible section

### GAP 2: No ELO/CP Progression Graph (HIGH IMPACT)
**What competitors do:** FACEIT shows an ELO-over-time line chart on every profile. Players obsess over their rating trajectory.
**DeltaCrown current state:** `elo_rating` field exists, `rank_change_24h` and `rank_change_7d` are stored, but there's no historical tracking table and no graph.
**Recommendation:**
- Create `TeamRankingHistory` model: (team_id, date, cp, elo, tier, global_rank)
- Populate via daily cron or post-match hook
- Add Chart.js or lightweight SVG sparkline to team detail page
- Add mini sparkline to leaderboard rows (FACEIT does this)
- Priority: Create the model+migration first, then add the chart

### GAP 3: No Regional Leaderboards (MEDIUM IMPACT)
**What competitors do:** FACEIT has continent/country/city leaderboards. Regional competition drives engagement.
**DeltaCrown current state:** `regional_rank` field exists in TeamRanking but is never computed or displayed. No region data on teams.
**Recommendation:**
- Add `region` field to Team model (or derive from Organization's country)
- Compute `regional_rank` in `compute_global_ranks()` grouped by region
- Add region tabs/filter to leaderboard_global.html
- Regions: NA, EU, LATAM, APAC, MEA (or country-level)

### GAP 4: Tournament Discovery is Weak (MEDIUM IMPACT)
**What competitors do:** Battlefy's homepage IS a tournament finder — game selector, platform filter, date range, entry fee range. Toornament has the best filter system (game, format, size, region, date, status).
**DeltaCrown current state:** Tournaments are listed but discovery UX is basic. No prominent "Find a Tournament" CTA on the teams hub.
**Recommendation:**
- Add "Upcoming Tournaments" section to /teams/ hub (below Featured Teams)
- Show: game icon, tournament name, date, format, team slots remaining, entry status
- Link to full tournament browser with filters
- Cross-link from team detail: "Tournaments available for your tier"

### GAP 5: Team Profile Depth (MEDIUM IMPACT)
**What competitors do:** FACEIT team profiles show roster with individual stats, team win rate, map preferences, average ELO, recent form streak.
**DeltaCrown current state:** Team detail shows tier badge, CP, global rank, roster list. No aggregate stats.
**Recommendation:**
- Add computed stats section: Win Rate, Matches Played (total/this month), Average Member Activity
- Add "Team Achievements" section: highest rank reached, longest win streak, tournaments won
- These can be computed from existing data without new models

### GAP 6: Weak Search & Filter UX (LOW-MEDIUM IMPACT)
**What competitors do:** FACEIT search is instant with autocomplete. Battlefy has a game selector as the primary interaction on landing.
**DeltaCrown current state:** New Alpine.js search bar on /teams/ hub filters client-side. No server-side search endpoint, no autocomplete.
**Recommendation:**
- Add AJAX search endpoint that queries teams by name (ILIKE)
- Add autocomplete dropdown showing top 5 matches with team logo + tier badge
- Add filters: game, region, tier, recruiting status, organization
- Consider HTMX for instant partial page updates

### GAP 7: No Real-time/Live Elements (LOW IMPACT — Future)
**What competitors do:** FACEIT has live match scores, queue status, and notifications via WebSocket.
**DeltaCrown current state:** ASGI/Channels infrastructure exists (routing.py, asgi.py) but no consumer for live data.
**Recommendation:**
- Phase 1: Add "Live Now" indicator to teams currently in match
- Phase 2: WebSocket consumer for match score updates
- Phase 3: Live leaderboard position changes (rank animation)
- This is a long-term investment, not urgent

---

## 4. Quick Wins (Can Ship This Sprint)

| # | Improvement | Effort | Impact |
|---|-----------|--------|--------|
| 1 | Add team **win rate** stat to team detail page | 2hr | Medium — makes profiles feel complete |
| 2 | Add **CP change indicator** (↑/↓) next to rank on leaderboards | 1hr | Medium — shows momentum |
| 3 | Add **"Trending Teams"** section (biggest CP gain in 7d) | 2hr | Medium — engagement hook |
| 4 | Add **mini activity bar** to leaderboard rows (visual, not just number) | 1hr | Low — polish |
| 5 | Add **tier explainer tooltip** on hover over tier badges everywhere | 1hr | Low — reduces confusion |
| 6 | Add **"Find Tournaments"** CTA button to teams hub | 30min | Medium — cross-navigation |
| 7 | Show **roster count** on team cards in hub | 30min | Low — context |
| 8 | Add **"Share Profile"** button to team detail | 30min | Low — growth loop |

---

## 5. Redesign Recommendations by Page

### 5A. /teams/ Hub (Current: vnext_hub)
**Current layout:** Hero carousel → Spotlight teams → Featured Teams (new) → Global Standings → Filters sidebar
**Proposed layout:**
```
┌─────────────────────────────────────────────────┐
│  Hero: "The Crown Awaits" + CTA + top 3 teams   │
├─────────────────────────────────────────────────┤
│  🔍 Search bar + Game/Tier/Region filters        │
├──────────────────────┬──────────────────────────┤
│  Trending Teams (3)  │  Live Matches (if any)   │
│  (biggest CP gain)   │  or Upcoming Tournaments │
├──────────────────────┴──────────────────────────┤
│  Global Standings (top 20, expandable)           │
│  With sparkline + CP change + activity bar       │
├─────────────────────────────────────────────────┤
│  Featured Teams (recruiting / active)            │
│  Card grid with tier badge + roster count        │
├─────────────────────────────────────────────────┤
│  Tier Distribution Chart (how many teams/tier)   │
│  CTA: "Start climbing → Create Team"            │
└─────────────────────────────────────────────────┘
```

### 5B. /competition/rankings/ (Current: leaderboard_global)
**Current:** Good — game tabs, tier filter, score bars, activity score. 
**Additions needed:**
- Regional filter tabs (when regional data available)
- CP change column (rank_change_24h / rank_change_7d — data exists)
- Sparkline (when history model exists)
- "Your Team" highlight row (exists but subtle — make it sticky/prominent)
- Pagination (currently shows up to 100 — add infinite scroll or page numbers)

### 5C. Team Detail Page (_body.html)
**Current:** Basic — name, logo, tier badge, CP, rank, roster.
**Additions needed:**
- Stats row: Win Rate | Matches Played | Activity Score | Streak
- Recent Matches tab (GAP 1)
- CP/ELO progression chart (GAP 2)
- Achievements section
- "Similar Teams" (same tier, same game) for competitive context
- Recruitment status + apply button (if open)

### 5D. Dashboard (index.html)
**Current:** Shows user's team tier and rank.
**Additions needed:**
- Mini leaderboard showing user's team + 2 above + 2 below (competitive context)
- CP change this week (motivational)
- Next tournament recommendation
- "Climb to [next tier] — need X more CP" progress bar

---

## 6. Technical Prerequisites

| Prerequisite | Status | Needed For |
|-------------|--------|------------|
| `TeamRankingHistory` model | ❌ Not created | GAP 2 (progression graph) |
| `region` field on Team/Org | ❌ Not present | GAP 3 (regional leaderboards) |
| Match history query service | ⚠️ Models exist, no service method | GAP 1 (match history feed) |
| AJAX search endpoint | ❌ Not built | GAP 6 (search UX) |
| Chart.js or SVG lib | ❌ Not included | GAP 2 (graphs) |
| WebSocket consumers | ❌ Not built | GAP 7 (live updates) |
| `rank_change_24h` computation | ⚠️ Field exists, computation not scheduled | Quick Win 2 (CP change indicator) |

---

## 7. Prioritized Roadmap

### Sprint N (Now — Quick Wins)
- [ ] Add CP change indicator to leaderboards (rank_change_24h already in model)
- [ ] Add "Find Tournaments" CTA to /teams/ hub
- [ ] Show roster count on team cards
- [ ] Add win rate to team detail (compute from match models)

### Sprint N+1 (Near Term — Core Gaps)
- [ ] Create `TeamRankingHistory` model + daily snapshot command
- [ ] Build match history query service + team detail tab
- [ ] Add AJAX search endpoint with autocomplete
- [ ] Add "Trending Teams" section to hub

### Sprint N+2 (Medium Term — Differentiation)
- [ ] Chart.js CP/ELO progression graph on team detail
- [ ] Regional leaderboard support (add region, compute regional ranks)
- [ ] Team achievements system
- [ ] Dashboard mini-leaderboard + progress bar

### Sprint N+3 (Long Term — Premium Features)
- [ ] Live match indicators
- [ ] WebSocket score updates
- [ ] Advanced filters (game + region + tier + format)
- [ ] "Similar Teams" recommendation engine

---

## 8. Competitive Positioning Summary

**DeltaCrown's strengths vs. competitors:**
- ✅ Built-in ELO + CP ranking (Toornament and Battlefy don't have this)
- ✅ Activity scoring system (unique — even FACEIT's FBI is behavior, not activity)
- ✅ 6-tier progression system (clearer than FACEIT's 10 numeric levels)
- ✅ Anti-abuse mechanics (daily caps, diminishing returns — competitors lack this)

**DeltaCrown's weaknesses vs. competitors:**
- ❌ No match history feed (FACEIT's killer feature)
- ❌ No progression visualization (FACEIT's ELO graph is addictive)
- ❌ No regional competition (FACEIT's regional boards drive local community)
- ❌ Weak tournament discovery (Battlefy and Toornament excel here)
- ❌ No real-time/live elements (FACEIT's queue system keeps users on-platform)

**Bottom line:** DeltaCrown has a stronger ranking *engine* than all three competitors but a weaker ranking *experience*. The data infrastructure is ahead — the presentation layer needs to catch up.
