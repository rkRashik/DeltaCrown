# Sprint 26 Implementation Tracker

## Phase A: Backend Hardening ✅ COMPLETE
- [x] A1: Enrich `_serialize_match` (+group_label, lobby_info, check-in fields, bracket_id)
- [x] A3: Add `?group=` filter to match list API  
- [x] A4: Fix silent exception swallowing (submit_score, mark_live, forfeit_match)
- [x] A5: Add total_count to match list response (`{matches:[], total_count: N}`)

## Phase B: Frontend Overhaul — UI/UX ✅ COMPLETE
- [x] B1: Font size pass — all `text-[8px]`→removed, `text-[9px]`→`text-xs`, `text-[10px]`→`text-xs`/`text-sm`
- [x] B2: Match list card redesign — bigger fonts, check-in dots, group tags, accessibility
- [x] B3: Detail panel — lobby info row, check-in indicators, match room link, avatars
- [x] B4: Action row — min-h-[36px] buttons, verify button added, grouped by intent
- [x] B5: Empty state — informative message with link to Schedule tab
- [x] B6: XSS protection — `esc()` helper applied to all user-generated content in JS
- [x] B7: Accessibility — `tabindex="0"`, `role="option/tab/tabpanel/listbox"`, `aria-selected/label/controls`, `for` on labels

## Phase C: Lobby Integration ✅ COMPLETE
- [x] C1: Lobby info panel in match detail header (code + copy, map, server)
- [x] C2: Lobby editor modal (set code, password, map, server, game mode)
- [x] C3: Check-in status display (per-card dots + detail panel indicators + deadline)

## Phase D: Polish ✅ COMPLETE
- [x] D1: Custom dispute modal (replaces `prompt()`) — full modal with reason code dropdown + description
- [x] D2: Mobile responsiveness — back button (`lg:hidden`), stacked layout
- [x] D3: Keyboard shortcuts — Arrow Up/Down navigate list, Enter/Space select, Escape close, 1/2/3 tabs, S/D/N/V/L quick actions
- [x] D4: Touch support for evidence viewer (pinch-zoom, single-finger pan)

---

### Files Modified
| File | Changes |
|------|---------|
| `apps/tournaments/api/toc/matches_service.py` | +GroupStanding import, group_cache, enrich serializer, group filter, total_count, narrow exceptions |
| `apps/tournaments/api/toc/matches.py` | Pass `group` param, return enriched response |
| `templates/tournaments/toc/base.html` | Complete Matches tab HTML rewrite (~310 lines) |
| `static/tournaments/toc/js/toc-matches.js` | Complete JS rewrite (850→770 lines) with XSS, lobbies, modals, shortcuts |

_Last updated: Sprint 26 — all phases complete_
