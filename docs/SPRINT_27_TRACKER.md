# Sprint 27 — Progress Tracker

## Status: ✅ ALL PHASES COMPLETE

| Phase | Name | Status | Files Changed |
|-------|------|--------|---------------|
| 1A | Schedule Backend Enhancements | ✅ Done | brackets_service.py, brackets.py, urls.py |
| 1B | Schedule Frontend Rebuild | ✅ Done | toc-schedule.js, base.html |
| 2 | Overview Enhancements | ✅ Done | toc-overview.js, service.py, base.html |
| 3 | Scoring Config UI | ✅ Done | toc-settings.js, base.html |
| 4 | Hub-TOC Sync Fixes | ✅ Done | hub-engine.js, hub.html, _tab_schedule.html |

---

## Phase 1A: Schedule Backend — Details

| Task | Status | Notes |
|------|--------|-------|
| Enhanced `get_schedule()` with group/stage info | ✅ | + summary stats, per-day breakdown |
| New `reschedule_match()` method | ✅ | State validation included |
| Conflict detection logic | ✅ | O(n²) overlap detection |
| Schedule summary statistics | ✅ | 8 fields: total/scheduled/live/completed/pending/disputed/conflicts/est_end |
| Add `schedule/<pk>/reschedule/` URL | ✅ | POST endpoint |

## Phase 1B: Schedule Frontend — Details

| Task | Status | Notes |
|------|--------|-------|
| Complete JS rewrite with 3 view modes | ✅ | 301→780 lines |
| Timeline view (Gantt-style) | ✅ | Round headers, progress bars |
| List view (dense table) | ✅ | Sortable columns |
| Calendar view (day grid) | ✅ | Day grouping, today indicator |
| Inline reschedule functionality | ✅ | Per-match reschedule modal |
| Advanced filters (group/round/state/date) | ✅ | 6 filter dimensions |
| Smart stats (est. completion, conflicts) | ✅ | 6 stat cards |
| Conflict detection badges | ✅ | Red badges on conflicting matches |
| Keyboard shortcuts | ✅ | Ctrl+1/2/3 views, R refresh |
| HTML updates (base.html) | ✅ | View toggles, filter bar, stat cards |

## Phase 2: Overview Enhancements — Details

| Task | Status | Notes |
|------|--------|-------|
| Health score calculation | ✅ | Composite 0-100 with 5 weighted components, grade A-F |
| Upcoming matches widget | ✅ | Next 5 scheduled matches |
| Group stage progress snippet | ✅ | Per-group team counts, completion % |
| SVG animated health ring | ✅ | Color-coded, breakdown grid |

## Phase 3: Scoring Config — Details

| Task | Status | Notes |
|------|--------|-------|
| Points per W/D/L config panel | ✅ | + forfeit points |
| FPS round config | ✅ | rounds_to_win, overtime format |
| Sports goals config | ✅ | extra_time, penalties |
| Game-aware presets | ✅ | 4 presets: Valorant, MOBA, BR, Sports |
| Tiebreaker configuration | ✅ | 15 options, reorderable, add/remove |

## Phase 4: Hub-TOC Sync — Details

| Task | Status | Notes |
|------|--------|-------|
| Hub WebSocket connection | ✅ | Uses existing TournamentBracketConsumer |
| Exponential backoff reconnect | ✅ | 3s base, max 5 attempts |
| Cache invalidation on WS events | ✅ | bracket/match/standings caches cleared |
| Auto-refresh active tab | ✅ | _refreshActiveTab() on WS events |
| Toast notifications | ✅ | Lightweight animated toasts |
| WS connection indicator | ✅ | Navbar dot (green/red) |
| Hub match-level schedule | ✅ | Dynamic match cards in schedule tab |
| 30s ping keepalive | ✅ | Prevents idle disconnect |

---

## Change Log

| Date | Phase | Change |
|------|-------|--------|
| — | Setup | Master Plan + Tracker created |
| — | 1A | Enhanced get_schedule(), added reschedule_match(), conflict detection |
| — | 1B | Complete toc-schedule.js rewrite (3 views), base.html schedule section rebuild |
| — | 2 | Health score ring, upcoming matches, group progress (backend + HTML + JS) |
| — | 3 | Scoring system section in Settings (presets, tiebreakers, game-category config) |
| — | 4 | WebSocket connection, cache invalidation, toast notifications, schedule matches |
