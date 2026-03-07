# Tournament Detail Page — Audit Implementation Tracker

> **Source:** `docs/audits/TOURNAMENT_DETAIL_PAGE_AUDIT.md` (v3, March 2026)  
> **Last Updated:** 2026-03-06  
> **Status Legend:** ✅ Done │ 🚧 In-Progress │ ❌ Not Started │ ⏩ Deferred │ 🐛 Bugfix

---

## Bug Fixes (Non-Sprint)

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| BF-1 | `description\|linebreaksbr` → `description\|safe` in detail_registration | ✅ Done | Fixed in Phase F |
| BF-2 | `rules_text\|linebreaksbr` → `rules_text\|safe` in detail_registration L363 | ✅ Done | Fixed in current session |
| BF-3 | `terms_and_conditions\|linebreaksbr` → `terms_and_conditions\|safe` in detail_registration L387 | ✅ Done | Fixed in current session |
| BF-4 | `tournament.rules\|linebreaksbr` → `tournament.rules_text\|safe` in _step_review.html L305 (wrong field name + wrong filter) | ✅ Done | Fixed in current session |
| BF-5 | `form_config.custom_registration_rules\|linebreaksbr` → `\|safe` in _step_review.html L327 | ✅ Done | Fixed in current session |
| BF-6 | `form_config.custom_tos_text\|linebreaksbr` → `\|safe` in _step_review.html L348 | ✅ Done | Fixed in current session |
| BF-7 | `form_config.custom_fair_play_text\|linebreaksbr` → `\|safe` in _step_review.html L368 | ✅ Done | Fixed in current session |
| BF-8 | Added `.desc-content` CSS to `smart_register.html` for registration flow rendering | ✅ Done | Fixed in current session |
| BF-9 | Roster eligibility error message raw ("Roster size (0) below minimum (1)") → user-friendly | ✅ Done | Fixed in Phase F |

---

## Sprint A: Foundation (Fix Critical Issues)

| # | Task | Type | Status | Implementation Notes |
|---|------|------|--------|---------------------|
| A1 | Archive `detail.html` monolith | Cleanup | ⏩ Deferred | Monolith kept as reference; phase system is primary |
| A2 | Wire Discord + all social links to sidebar | Feature | ✅ Done | Added social links card + Discord card in sidebar |
| A3 | Add `cancellation_reason` + `cancelled_at` fields | Bugfix | ✅ Done | Migration 0031, rendered in detail_cancelled.html |
| A4 | Override OG meta tags with tournament data | Feature | ✅ Done | `og_image`, `og_description` blocks in base template |
| A5 | Link spectator view from detail (live/completed) | Feature | ✅ Done | Spectator button in hero area |
| A6 | Call `_get_registration_status()` in view context | Bugfix | ✅ Done | Wired CoinPolicy, social links, spectator URL, registration status |
| A7 | Replace `alert()` with toast notification | UX | ✅ Done | Professional toast component |
| A8 | Render refund policy in registration section | Feature | ✅ Done | Refund policy card in detail_registration |

**Sprint A: 7/8 complete (A1 deferred by design)**

---

## Sprint B: Ecosystem Integration

| # | Task | Type | Status | Implementation Notes |
|---|------|------|--------|---------------------|
| B1 | Participant cards link to player profiles + team pages | Feature | ❌ Not Started | Need profile URL resolver for participant list |
| B2 | Show team ranking tier badge on participant cards | Feature | ❌ Not Started | Requires TeamRanking model integration |
| B3 | DeltaCoin reward tier display (from CoinPolicy) | Feature | ✅ Done | CoinPolicy queried in context, rendered in sidebar |
| B4 | Sponsor section on detail page | Feature | ❌ Not Started | Need TournamentSponsor model (may not exist yet) |
| B5 | Organizer card → profile link + tournament count | Feature | ❌ Not Started | Need organizer profile URL + tournament count query |
| B6 | Game identity labels ("Riot ID" vs "Character ID") | Feature | ✅ Done | Rendered via GamePlayerIdentityConfig |
| B7 | Show player roles per game (GameRole) | Feature | ❌ Not Started | Need GameRole integration in participant cards |

**Sprint B: 2/7 complete**

---

## Sprint C: Game-Dynamic Information

| # | Task | Type | Status | Implementation Notes |
|---|------|------|--------|---------------------|
| C1 | Game-dynamic standings columns | Feature | ❌ Not Started | Different stat columns per game category |
| C2 | Game-dynamic match card stats | Feature | ❌ Not Started | Different info per game on match cards |
| C3 | Scoring type + tiebreaker display | Feature | ✅ Done | Shown in Quick Details card via GameTournamentConfig |
| C4 | Match format + duration + draws info | Feature | ❌ Not Started | Complete match configuration display |
| C5 | BR placement points table | Feature | ❌ Not Started | BR-specific scoring matrix display |
| C6 | JSON-LD Event structured data | SEO | ❌ Not Started | Schema.org markup for search engines |

**Sprint C: 1/6 complete**

---

## Sprint D: Live Experience Enhancement

| # | Task | Type | Status | Implementation Notes |
|---|------|------|--------|---------------------|
| D1 | Replace 60s reload with AJAX polling (10s) | Feature | ❌ Not Started | Smooth live experience without full reloads |
| D2 | Web Share API with platform fallbacks | Feature | ❌ Not Started | Native sharing on mobile, clipboard on desktop |
| D3 | Follow/favorite tournament (UserFavorite) | Feature | ❌ Not Started | Requires UserFavorite model + toggle endpoint |
| D4 | Recent matches on overview tab | Feature | ❌ Not Started | Show latest completed matches for quick context |
| D5 | Render promo video on detail page | Feature | ❌ Not Started | Embed `promo_video_url` in hero or dedicated section |

**Sprint D: 0/5 complete**

---

## Sprint E: Future Vision

| # | Task | Type | Status | Implementation Notes |
|---|------|------|--------|---------------------|
| E1 | Interactive SVG bracket (D3.js) | Feature | ❌ Not Started | Major frontend effort |
| E2 | WebSocket real-time scores | Feature | ❌ Not Started | Replaces AJAX polling with WS |
| E3 | Fan voting UI | Feature | ❌ Not Started | Community engagement feature |
| E4 | Embeddable bracket/standings widgets | Feature | ❌ Not Started | For external sharing |
| E5 | Tournament series/season context | Feature | ❌ Not Started | Career progression integration |
| E6 | Map veto/pool display | Feature | ❌ Not Started | Game-specific feature for FPS/MOBA |
| E7 | Related tournaments section | Feature | ❌ Not Started | By same organizer or same game |

**Sprint E: 0/7 complete**

---

## Summary

| Sprint | Done | Total | % |
|--------|------|-------|---|
| Bug Fixes | 9 | 9 | 100% |
| Sprint A | 7 | 8 | 88% |
| Sprint B | 2 | 7 | 29% |
| Sprint C | 1 | 6 | 17% |
| Sprint D | 0 | 5 | 0% |
| Sprint E | 0 | 7 | 0% |
| **Total** | **19** | **42** | **45%** |

---

## Next Priority Items

### High Priority (Sprint B remaining)
1. **B1** — Participant profile links (medium effort, high ecosystem value)
2. **B5** — Organizer profile link + count (low effort, trust signal)
3. **B7** — Player roles display (low-med effort, competitive context)

### Medium Priority (Sprint C/D)
4. **C4** — Match format/duration info (low effort, transparency)
5. **C6** — JSON-LD structured data (low effort, SEO win)
6. **D2** — Web Share API (low effort, UX win)
7. **D4** — Recent matches on overview (low effort, context)
8. **D5** — Promo video embed (low effort, engagement)

### Deferred (High effort / dependency)
- B2 (tier badges — needs ranking data), B4 (sponsors — needs model)
- C1, C2 (game-dynamic — needs per-game template logic)
- C5 (BR points — needs BRScoringMatrix)
- D1 (AJAX polling — needs API endpoints), D3 (favorites — needs model)
- E1-E7 (all future vision)
