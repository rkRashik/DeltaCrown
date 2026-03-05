# Sprint 28 — Master Plan: No-Show Timers, Cloning, Standings & Check-in Hub

## Mission Statement
Elevate DeltaCrown TOC from a capable platform to a world-class competitive tournament operations center by closing the top critical gaps identified in the Sprint 28 Research (TOC_MISSING_FEATURES_AND_MENUS.md). Focus: operations automation (no-show DQ), organizer productivity (tournament cloning), and visibility (dedicated Standings tab).  

---

## Phase 1: No-Show Timer / Auto-DQ (Sprint 28A)

### What Exists
- `MatchService.forfeit_match(match, reason, forfeiting_participant_id)` — works correctly
- `Match` state machine: SCHEDULED → CHECK_IN → READY → LIVE → (no_show window here)
- `notify_match_ready` beat task pattern (5-min window task) — good template

### What's Needed
1. `no_show_timeout_minutes` field on Tournament model (default: 10)
2. `enable_no_show_timer` BooleanField on Tournament (default: False — opt-in only)
3. Celery beat task `check_no_show_matches` — runs every 2 minutes
4. Wire new fields into TOC Settings → Match tab
5. Emit Discord + in-platform notification on auto-DQ

### Logic
- Finds matches with `state__in = [READY, LIVE]` and `scheduled_time + timeout < now`
- For each expired match: determine which participant(s) didn't check in → forfeit
- If both missed: cancel match (or both forfeit, configurable)
- Sets `lobby_info['no_show_auto_dq'] = True` for audit trail
- Triggers `TOCNotificationsService.fire_auto_event('match_forfeit', context)`

---

## Phase 2: Tournament Cloning (Sprint 28B)

### What's Needed
1. `TournamentCloningService.clone(source, overrides)` — deep-copies:
   - All settings, format config, rules, registration fields
   - Prize pool, entry fee, sponsor/branding fields  
   - TOC notification rules
   - Excludes: registrations, brackets, matches, payments, disputes
2. API endpoint: `POST /api/toc/{slug}/clone/`
3. TOC Settings → Danger Zone → "Clone Tournament" button
4. Redirect immediately to new tournament's TOC Settings to customize dates

---

## Phase 3: Dedicated Standings Tab (Sprint 28C)

### What Exists
- Group stage standings visible inside Brackets tab only
- No cross-format standings view
- No public-facing standings widget

### What's Needed
**Backend `standings_service.py`:**
- `get_standings_data(tournament)` → unified view across all formats:
  - Group stage: per-group tables (W/L/D, points, tiebreakers)
  - Bracket: current live bracket position
  - Swiss (future): standings after each round
- Overall tournament leaderboard (by points or advancement stage)
- Export-ready format (image/CSV)

**New TOC Tab:**
- HTML partial: `_tab_standings.html` (included in base.html)
- New JS module: `toc-standings.js`
- API endpoint: `GET /api/toc/{slug}/standings/`

**UI Features:**
- Toggle: Group View / Overall Leaderboard / Bracket Position
- Qualification line indicator (top N advance highlighted)
- Point breakdown tooltip (click team for breakdown)
- "Copy as Image" button (canvas rendering)
- Auto-refresh every 30s (same pattern as overview)

---

## Phase 4: Check-in Hub Upgrades (Sprint 28D)

### What Exists
- Check-in toggle in Participants tab
- `check_in_minutes_before` / `check_in_closes_minutes_before` on Tournament
- `CheckInViewSet` with GET/POST endpoints

### What's Needed
- Dedicated **Check-in Hub** section in the Participants tab (promoted, not buried)
- Real-time check-in dashboard (WebSocket-powered) with:
  - Visual grid: team cards (checked-in ✅ / pending ⏳ / no-show ❌)  
  - Live countdown timer to check-in deadline
  - One-click force check-in (organizer override)
  - One-click DQ team from check-in
  - Progress bar: X/Y checked in
  - "Blast reminder" button → sends in-platform + Discord notification to all pending teams

---

## File Change Matrix

| File | Action | Phase |
|------|--------|-------|
| `apps/tournaments/models/tournament.py` | Add `no_show_timeout_minutes`, `enable_no_show_timer` | 1 |
| `apps/tournaments/migrations/0028_add_no_show_timer_fields.py` | Migration | 1 |
| `apps/tournaments/tasks/no_show_timer.py` | New beat task | 1 |
| `apps/tournaments/tasks/__init__.py` | Add export | 1 |
| `deltacrown/celery.py` | Add beat schedule entry | 1 |
| `apps/tournaments/api/toc/settings_service.py` | Expose no-show fields | 1 |
| `static/tournaments/toc/js/toc-settings.js` | No-show timer UI in Match section | 1 |
| `apps/tournaments/services/tournament_cloning_service.py` | New cloning service | 2 |
| `apps/tournaments/api/toc/cloning.py` | New API endpoint | 2 |
| `apps/tournaments/api/toc/urls.py` | Add clone URL | 2 |
| `static/tournaments/toc/js/toc-settings.js` | Clone button in Danger Zone | 2 |
| `apps/tournaments/api/toc/standings_service.py` | New standings service | 3 |
| `apps/tournaments/api/toc/standings.py` | Standings API view | 3 |
| `apps/tournaments/api/toc/urls.py` | Add standings URL | 3 |
| `templates/tournaments/toc/tabs/_tab_standings.html` | New tab HTML | 3 |
| `templates/tournaments/toc/base.html` | Add Standings tab nav + include | 3 |
| `static/tournaments/toc/js/toc-standings.js` | New JS module | 3 |
| `templates/tournaments/toc/tabs/_tab_participants.html` | Check-in hub section | 4 |
| `static/tournaments/toc/js/toc-participants.js` | Check-in hub JS | 4 |

---

## Execution Order
1. **28A**: No-show timer (model fields → migration → Celery task → settings wiring)
2. **28B**: Tournament cloning (service → API → UI button)
3. **28C**: Standings tab (backend service → API → HTML partial → JS module)
4. **28D**: Check-in hub upgrade (HTML + JS only, no new backend needed)

## Success Criteria
- [x] Matches auto-forfeit when no-show timeout expires (if enabled)
- [x] Tournament can be cloned via one-click in Settings
- [x] Dedicated Standings tab shows per-group tables + overall leaderboard
- [x] Qualification advancement lines visible on standings
- [x] Check-in hub shows real-time progress with force check-in / DQ controls
- [ ] All existing tests pass
