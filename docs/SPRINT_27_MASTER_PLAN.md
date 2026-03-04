# Sprint 27 — Master Plan: Schedule + Scoring + Overview + Hub Sync

## Mission Statement
Transform DeltaCrown's TOC into a **world-class tournament operations center** that is 3 steps ahead of platforms like Toornament, Battlefly, FACEIT, and start.gg. This sprint focuses on making the Schedule tab fully functional with modern UX, adding game-specific scoring configuration, enhancing the Overview with real data, and fixing Hub-TOC synchronization.

---

## Phase 1: Schedule Tab — Complete Rebuild (Sprint 27A)

### What Exists
- Backend: `get_schedule()`, `auto_schedule()`, `bulk_shift()`, `add_break()` in `brackets_service.py`
- Frontend: 301 lines of basic round-grouped card layout
- 4 stat cards, 3 action buttons (Auto-Schedule, Bulk Shift, Add Break)

### What Modern Platforms Have That We Don't
| Feature | Toornament | start.gg | FACEIT | DeltaCrown |
|---------|:----------:|:--------:|:------:|:----------:|
| Calendar/Gantt timeline view | ✅ | ✅ | ✅ | ❌ |
| Inline match time editing | ✅ | ✅ | — | ❌ |
| Conflict detection (team overlap) | ✅ | ✅ | — | ❌ |
| Station/stream assignment | ✅ | ✅ | ✅ | ❌ |
| Timezone-aware scheduling | ✅ | ✅ | ✅ | ❌ |
| Schedule export (PDF/image) | ✅ | ✅ | — | ❌ |
| Per-group/stage filtering | ✅ | ✅ | ✅ | ❌ |
| View toggle (Timeline/List/Calendar) | ✅ | ✅ | — | ❌ |
| Quick reschedule from schedule view | ✅ | ✅ | ✅ | ❌ |
| Smart auto-schedule with break windows | ✅ | ✅ | — | Partial |
| Estimated completion time | ✅ | ✅ | — | ❌ |

### Implementation Plan

#### Backend Enhancements (`brackets_service.py`)
1. **Enhanced `get_schedule()`** — Add group_name, stage info, estimated_end_time per match
2. **New `reschedule_match()`** — Per-match time editing with conflict detection
3. **Conflict detection** — Before scheduling, check if any team has overlapping matches
4. **Schedule statistics** — Total duration, estimated end, matches per day breakdown
5. **Export schedule** — Serialized schedule for PDF rendering

#### Frontend Rebuild (`toc-schedule.js` → 1200+ lines)
1. **View Modes**: Timeline (default), List, Calendar
2. **Timeline View**: Horizontal Gantt-style per-round with time axis
3. **List View**: Dense sortable table with all match details
4. **Calendar View**: Day-based grid showing matches by time slot
5. **Inline Reschedule**: Click match → datepicker → confirm
6. **Advanced Filters**: By group, round, state, date range
7. **Smart Stats**: Estimated completion, matches/day, conflicts detected
8. **Conflict Indicators**: Red badges on overlapping matches
9. **Quick Actions**: Reschedule, swap times, mark as streamed
10. **Timezone Toggle**: Show times in local vs tournament timezone

#### HTML Updates (`base.html`)
- Expand stats from 4 to 6 cards (add Conflicts, Est. Completion)
- Add view mode toggle buttons
- Add filter bar with group/round/state/date selectors
- Add schedule toolbar with search, timezone toggle

---

## Phase 2: Overview Enhancements (Sprint 27B)

### What Exists
- Lifecycle pipeline visualizer
- 4 hero stat cards + 6 quick stats
- Action Queue + Tournament Progress
- Activity Log + Upcoming Events
- 30s auto-refresh polling

### Enhancements
1. **Real Timeline Data**: Show actual dates on lifecycle stages, not just status
2. **Automated Lifecycle Pipeline**: Add "days since" / "days until" per stage
3. **Health Score**: Aggregate 0-100 tournament health from disputes/payments/no-shows
4. **Match Velocity Chart**: Mini sparkline showing matches completed per day
5. **Group Stage Progress**: Abbreviated group standings in overview
6. **Upcoming Matches Widget**: Next 5 scheduled matches with countdown
7. **Revenue Tracker**: Revenue vs target comparison bar

---

## Phase 3: Game-Specific Scoring Configuration (Sprint 27C)

### What Exists
- `GameScoringRule` model (win_loss / points_accumulation / placement_order / time_based / custom)
- `BRScoringMatrix` (placement_points JSON, kill_points)
- `Group.config.points_system` (win/draw/loss points: 3/1/0 default)
- `GameRulesEngine` service (`score_match()`, `determine_winner()`)
- `GameMatchConfig` (1:1 with Tournament)
- Settings service has `GameConfigView`, `BRScoringView`

### What We Need to Expose in TOC
1. **Scoring Config Sub-Panel in Settings** — Dedicated section for:
   - Points per Win/Draw/Loss (all formats)
   - BR Placement bonus table editor
   - Kill point multiplier
   - Tiebreaker order configuration
2. **Game-Aware Defaults** — When game changes, auto-fill appropriate scoring template:
   - FPS (Valorant/CS2): Round-based, no draws, map veto
   - MOBA (Dota2/MLBB): Bo3/Bo5, draft-pick
   - BR (PUBG/FF): Placement+kills matrix
   - Sports (FIFA/RL): Win/Draw/Loss points, goals
3. **Preview**: Show how scoring would apply to sample matches

---

## Phase 4: Hub-TOC Sync Fixes (Sprint 27D)

### Critical Bugs
1. **`broadcast_bracket_generated` NEVER AWAITED** — Fix with `async_to_sync()`
2. **Hub caches NEVER invalidated** — Add clear-on-WS-event logic
3. **Hub has ZERO WebSocket** — Connect `hub-engine.js` to existing consumers
4. **Hub schedule shows milestones only** — Add match-level schedule

### Implementation
1. Fix async broadcast bug in bracket views
2. Add WS connection to hub-engine.js
3. On WS events, invalidate relevant caches
4. Add `/hub/api/schedule/` endpoint for match-level schedule data

---

## File Change Matrix

| File | Action | Phase |
|------|--------|-------|
| `apps/tournaments/api/toc/brackets_service.py` | Enhance schedule methods | 1 |
| `apps/tournaments/api/toc/brackets.py` | Add reschedule endpoint | 1 |
| `apps/tournaments/api/toc/urls.py` | Add new schedule URL | 1 |
| `static/tournaments/toc/js/toc-schedule.js` | **Complete rewrite** (301→1200+) | 1 |
| `templates/tournaments/toc/base.html` | Expand schedule HTML section | 1 |
| `static/tournaments/toc/js/toc-overview.js` | Add health score, upcoming matches | 2 |
| `templates/tournaments/toc/base.html` | Add overview widgets | 2 |
| `apps/tournaments/api/toc/service.py` | Enhance overview data | 2 |
| `apps/tournaments/api/toc/settings_service.py` | Enhance scoring config | 3 |
| `static/tournaments/toc/js/toc-settings.js` | Add scoring config panel | 3 |
| `static/tournaments/js/hub-engine.js` | Add WebSocket connection | 4 |
| `apps/tournaments/api/toc/brackets.py` | Fix async broadcast | 4 |

---

## Execution Order
1. **Phase 1A**: Schedule backend enhancements (conflict detection, reschedule, stats)
2. **Phase 1B**: Schedule HTML + JS complete rebuild
3. **Phase 2**: Overview enhancements (health score, upcoming matches, timeline dates)
4. **Phase 3**: Scoring config UI in Settings
5. **Phase 4**: Hub-TOC sync fixes

## Success Criteria
- [ ] Schedule tab shows matches in 3 view modes (Timeline/List/Calendar)
- [ ] Auto-schedule generates times with conflict detection
- [ ] Inline reschedule works from schedule view
- [ ] Overview shows real timeline dates and health score
- [ ] Game scoring is configurable from Settings
- [ ] Hub receives real-time updates via WebSocket
- [ ] All existing tests pass
