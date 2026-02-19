# Tournament Lifecycle Overhaul — Master Build Plan

**Created:** 2025-06-30
**Status:** PLANNING → EXECUTION
**Reference:** FotMob Champions League, Valorant Esports Brackets, FACEIT, Battlefy

---

## 🎯 VISION

Transform DeltaCrown's tournament system from a static detail page into a **dynamic, status-aware tournament lifecycle experience** — where the page transforms based on tournament state (Registration → Check-In → Live → Completed), with real lobby rooms, live brackets, scoreboards, and a fully integrated dashboard.

**Real-world esports references:**
- **FotMob UCL** — Live match cards, dynamic status-aware layouts, real-time scores
- **Valorant Esports (VCT)** — Interactive bracket trees, stage-based navigation
- **FACEIT** — Lobby rooms, check-in flows, match rooms
- **Battlefy** — Registration dashboards, organizer tools, bracket generation
- **ESL/ESEA** — Match veto systems, anti-cheat integration panels:

---

## 📐 ARCHITECTURE OVERVIEW

### Current State (What Exists)
| Component | File | Notes |
|-----------|------|-------|
| Tournament Detail | `templates/tournaments/detailPages/detail.html` (1620 lines) | Single static page, 7 tabs, no status-awareness |
| Detail View | `apps/tournaments/views/detail.py` (793 lines) | CBV with rich context, no status routing |
| Lobby | `templates/tournaments/lobby/hub.html` | Basic check-in page |
| Lobby View | `apps/tournaments/views/lobby.py` (250 lines) | Check-in + roster |
| Bracket | `templates/tournaments/public/live/bracket.html` | Separate page, basic round display |
| Match Detail | `templates/tournaments/public/live/match_detail.html` | Separate page |
| Results | `templates/tournaments/public/live/results.html` | Separate page |
| Dashboard | `templates/dashboard/index.html` (665 lines) | Bento grid, no tournament CTAs |
| Arena/Watch | `templates/Arena.html` (575 lines) | Stream hub at `/watch/` |
| Navigation | `templates/partials/primary_navigation.html` | Shows "Arena" text, links to `/watch/` |

### Target State (What We Build)
| Component | Description |
|-----------|-------------|
| **Dynamic Detail Page** | Single URL `/tournaments/<slug>/` that renders different layouts based on `tournament.status` |
| **Registration Phase View** | Countdown, CTA, participant list growing live, prize display |
| **Check-In Phase View** | Check-in countdown, roster with green/pending indicators, lobby rules |
| **Live Tournament View** | Live bracket tree, active match cards with scores, scoreboard, stream embed |
| **Completed View** | Champion showcase, final bracket, full results, stats, achievements |
| **Match Room** | Individual match page with lobby info, veto/map picks, score submission |
| **Enhanced Lobby** | Pre-tournament hub with chat-like announcements, roster, countdown, rules |
| **Dashboard Integration** | Tournament CTAs, upcoming matches, active tournament cards |
| **Arena Overhaul** | URL rename `/watch/` → `/arena/`, add live tournament scoreboard section |

---

## 🔧 PHASE BREAKDOWN

### Phase 1: Foundation — Dynamic Detail View Router (Backend)
**Goal:** Make the detail view status-aware so it routes to different template layouts.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 1.1 | Create `_get_phase_context()` method in `TournamentDetailView` | `views/detail.py` | 20min |
| 1.2 | Add `get_template_names()` override for status-based template routing | `views/detail.py` | 15min |
| 1.3 | Create base detail layout template with shared hero + phase-specific content blocks | `templates/tournaments/detailPages/base_detail.html` | 30min |
| 1.4 | Create registration phase context builder (`_registration_phase_context`) | `views/detail.py` | 20min |
| 1.5 | Create live phase context builder (`_live_phase_context`) | `views/detail.py` | 25min |
| 1.6 | Create completed phase context builder (`_completed_phase_context`) | `views/detail.py` | 20min |

**Status → Template mapping:**
```
draft, pending_approval     → detail_draft.html (or redirect)
published                   → detail_registration.html (pre-registration)
registration_open           → detail_registration.html (with CTA active)
registration_closed         → detail_checkin.html (pre-tournament)
live                        → detail_live.html (live tournament)
completed                   → detail_completed.html (results)
cancelled                   → detail_cancelled.html
archived                    → detail_completed.html (read-only)
```

---

### Phase 2: Registration Phase Template
**Goal:** A compelling registration page that drives signups, inspired by Battlefy/FACEIT tournament listings.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 2.1 | Create registration phase template with hero, prize showcase, countdown | `templates/tournaments/detailPages/detail_registration.html` | 60min |
| 2.2 | Registration CTA section — dynamic button states (register/registered/full/closed) | Same template | 30min |
| 2.3 | Participants live counter — animated fill bar + recent registrations feed | Same template | 25min |
| 2.4 | Tournament info cards — format, rules summary, schedule timeline | Same template | 25min |
| 2.5 | Prize pool showcase — animated podium with 1st/2nd/3rd prizes | Same template | 20min |
| 2.6 | Organizer info card with past tournaments track record | Same template | 15min |
| 2.7 | Countdown timer (JS) — days/hours/minutes/seconds to registration close | `static/js/tournament_countdown.js` | 20min |
| 2.8 | Mobile-responsive registration CTA sticky bar | Same template | 15min |

**Key design elements:**
- Full-viewport hero with tournament banner + game-colored accents
- Live participant counter with "X of Y slots filled" progress ring
- Countdown to registration deadline (and then to tournament start)
- "Recent registrations" feed showing latest signups (like "PlayerX just registered!")
- Quick-info grid: Format, Platform, Mode, Region, Entry Fee
- Prize pool breakdown with visual podium
- Organizer trust badge (verified, X tournaments hosted, Y participants served)

---

### Phase 3: Live Tournament Template
**Goal:** Real-time tournament experience page inspired by FotMob live matches + VCT brackets.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 3.1 | Create live tournament template with bracket + scoreboard layout | `templates/tournaments/detailPages/detail_live.html` | 90min |
| 3.2 | Live match cards — active matches with scores, team logos, elapsed time | Same template | 40min |
| 3.3 | Mini bracket visualization (CSS/SVG) — interactive bracket tree | `templates/tournaments/components/_bracket_tree.html` | 90min |
| 3.4 | Scoreboard section — all matches scorecard table (like FotMob fixtures) | Same template | 30min |
| 3.5 | Live stream embed section — YouTube/Twitch player | Same template | 15min |
| 3.6 | Tournament progress bar — "Round 2 of 4" with visual progress | Same template | 15min |
| 3.7 | Real-time score update JS (polling every 15s for match scores) | `static/js/tournament_live.js` | 30min |
| 3.8 | Participant action panel — "Enter Match Room" CTA for active participants | Same template | 20min |

**Key design elements:**
- Split layout: Left = Active Matches + Bracket, Right = Scoreboard + Stream
- **Active Match Cards** (like FotMob): Team A [score] vs [score] Team B, with "LIVE" pulse
- **Bracket Tree** (like VCT): Interactive SVG bracket, click to expand match details
- **Scoreboard Table**: All matches with scores, status (Upcoming/Live/Complete), times
- **Stream embed**: Floating YouTube/Twitch player
- **Tournament Progress**: "Round X of Y · Z matches remaining"
- **For participants**: "Your next match" card with opponent info + "Enter Match Room" button

---

### Phase 4: Completed Tournament Template
**Goal:** Champions showcase + full results archive, inspired by esports post-event pages.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 4.1 | Create completed tournament template with champion showcase | `templates/tournaments/detailPages/detail_completed.html` | 60min |
| 4.2 | Champion/podium section — 1st/2nd/3rd with avatars/logos, confetti effect | Same template | 30min |
| 4.3 | Final bracket view — completed bracket tree with results | Same template | 20min |
| 4.4 | Full results table — all matches, final standings | Same template | 20min |
| 4.5 | Tournament stats summary — total matches, total participants, avg score | Same template | 15min |
| 4.6 | MVP/awards section (if applicable) | Same template | 15min |

**Key design elements:**
- **Champion Showcase**: Large hero with winner name/logo, confetti CSS animation
- **Podium Display**: 1st (gold), 2nd (silver), 3rd (bronze) with prize amounts
- **Final Bracket**: Complete bracket tree with all results filled in
- **Results Table**: Sortable table with all participants, W/L record, placement
- **Tournament Stats**: Quick stats bar (total matches, participants, etc.)
- **Share Results**: Social sharing for winners

---

### Phase 5: Match Room / Battlefield Page
**Goal:** Individual match pages where participants interact before/during a match.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 5.1 | Create match room template — pre-match lobby with opponent info | `templates/tournaments/match_room/room.html` | 60min |
| 5.2 | Match room view — load match data, participants, lobby info | `views/match_room.py` | 40min |
| 5.3 | Pre-match state: opponent profile cards, match rules, lobby code display | Template | 25min |
| 5.4 | In-match state: score tracking, dispute button, lobby info | Template | 25min |
| 5.5 | Post-match state: result submission form, screenshot upload | Template | 20min |
| 5.6 | URL registration for match room | `urls.py` | 5min |
| 5.7 | Match room access control (only match participants + organizer) | View | 10min |

**Key design elements (inspired by FACEIT match rooms):**
- **Pre-Match**: "Match Starting in X:XX" countdown, both teams/players displayed with avatars, map/veto info, lobby code (organizer can set), rules reminder, check-in buttons
- **In-Match**: Live score entry, "Report Result" button, dispute button, chat/comms
- **Post-Match**: Result submission form, screenshot/proof upload, auto-confirm timer, dispute window

---

### Phase 6: Enhanced Lobby Hub
**Goal:** Upgrade the participant lobby from basic check-in to a full pre-tournament hub.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 6.1 | Redesign lobby template — countdown hero, roster grid, announcements | `templates/tournaments/lobby/hub.html` | 60min |
| 6.2 | Check-in roster grid — live status indicators (checked-in/pending/missing) | Same template | 25min |
| 6.3 | Announcements feed — organizer messages with timestamps | Same template | 15min |
| 6.4 | Tournament bracket preview — seedings/positions once generated | Same template | 15min |
| 6.5 | Quick rules section — collapsible rules/format reminder | Same template | 10min |
| 6.6 | HTMX roster polling — auto-refresh checked-in status every 10s | Same template + view | 20min |

**Key design elements:**
- **Countdown Hero**: Large countdown to tournament start, check-in deadline
- **Check-In Button**: Prominent, game-colored, disabled if already checked in
- **Roster Grid**: All participants with check-in status (green checkmark / amber pending / red missing)
- **Announcements Section**: Real-time organizer messages
- **Your Bracket Position**: Show seed/position once bracket is generated
- **Quick Rules**: Collapsible format + rules reminder

---

### Phase 7: Dashboard Tournament Integration
**Goal:** Add tournament-specific widgets and CTAs to the user dashboard.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 7.1 | Add "Active Tournaments" bento tile to dashboard | `templates/dashboard/index.html` | 30min |
| 7.2 | Add "Upcoming Matches" bento tile with next match info | `templates/dashboard/index.html` | 25min |
| 7.3 | Add tournament registration CTA cards | `templates/dashboard/index.html` | 20min |
| 7.4 | Add "My Tournaments" quick actions section | `templates/dashboard/index.html` | 15min |
| 7.5 | Update dashboard view to query tournament data efficiently | `apps/dashboard/views.py` | 20min |
| 7.6 | Live tournament notification banner — "Tournament X is LIVE" | `templates/dashboard/index.html` | 15min |

**Key dashboard additions:**
- **Active Tournament Card** (span-8): Shows tournament name, your status (Registered/Checked-In/Playing), next action CTA ("Check In Now" / "Enter Lobby" / "View Bracket"), countdown
- **Upcoming Match Card** (span-4): Opponent info, scheduled time, "Enter Match Room"
- **Featured Tournament CTA** (span-6): Upsell card for open tournaments ("Join the DeltaCrown Cup!")
- **Live Tournament Banner**: Full-width alert "Tournament X is LIVE — Enter Lobby"

---

### Phase 8: Arena Overhaul (Watch → Arena)
**Goal:** Rename the Watch page to Arena, update URLs, and add live tournament scoreboard.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 8.1 | Add `/arena/` URL path (keep `/watch/` as redirect for backward compat) | `apps/siteui/urls.py` | 5min |
| 8.2 | Update navigation link from `/watch/` to `/arena/` | `templates/partials/primary_navigation.html` | 5min |
| 8.3 | Add "Live Tournaments" scoreboard section to Arena template | `templates/Arena.html` | 40min |
| 8.4 | Add "Tournament Scorecards" — live match scores from active tournaments | `templates/Arena.html` | 30min |
| 8.5 | Update arena view to query live tournaments and match scores | `apps/siteui/views.py` | 20min |
| 8.6 | Arena scoreboard auto-refresh with HTMX/JS polling | `static/js/arena_scoreboard.js` | 15min |

**Key Arena additions:**
- **Live Tournaments Section**: Cards for each live tournament with match count, current round
- **Match Scorecards**: FotMob-style match cards showing Team A [2] - [1] Team B, with time/status
- **Upcoming Tournaments**: Registration-open tournaments carousel
- Streams section remains as-is

---

### Phase 9: Bracket Visualization Component
**Goal:** Build a reusable, interactive bracket tree component (SVG/CSS).

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 9.1 | Create bracket tree component — single elimination SVG layout | `templates/tournaments/components/_bracket_tree.html` | 90min |
| 9.2 | Double elimination bracket support (winners + losers bracket) | Same component | 60min |
| 9.3 | Round-robin group stage table component | `templates/tournaments/components/_group_table.html` | 30min |
| 9.4 | Bracket node component — match card with scores, teams, status | `templates/tournaments/components/_bracket_node.html` | 25min |
| 9.5 | Interactive bracket JS — click to expand match, hover effects | `static/js/bracket_interactive.js` | 30min |
| 9.6 | Bracket API endpoint — return bracket data as JSON for JS rendering | `views/bracket_api.py` or addition to existing | 20min |

**Bracket design (VCT-inspired):**
```
 R1          QF          SF          FINAL
┌─────┐   ┌─────┐   ┌─────┐    ┌─────────┐
│ T1  │───│     │   │     │    │         │
│ T2  │   │ Win │───│     │    │         │
└─────┘   │     │   │ Win │────│         │
┌─────┐   └─────┘   │     │   │  CHAMP  │
│ T3  │───│     │   └─────┘   │         │
│ T4  │   │ Win │              │         │
└─────┘   └─────┘              └─────────┘
```
- Dark glassmorphism cards for each match node
- Game-colored connector lines between rounds
- Animated data flow — new results slide in
- Click match to see details modal
- Winner highlighted with game color, loser dimmed

---

### Phase 10: Polish, Testing & Documentation
**Goal:** Final polish, manual testing, and documentation updates.

| # | Task | File(s) | Est |
|---|------|---------|-----|
| 10.1 | Mobile responsiveness pass on all new templates | All templates | 30min |
| 10.2 | Cross-browser testing (Chrome, Firefox, Edge) | Manual | 15min |
| 10.3 | Update seed script to create tournaments in different states | `seed_full_tournament.py` | 20min |
| 10.4 | Update manual testing guide with new pages/flows | `docs/MyTesting/` | 15min |
| 10.5 | Add transition animations between tournament phases | CSS | 15min |
| 10.6 | Error states — empty brackets, no matches, cancelled tournaments | Templates | 15min |
| 10.7 | Performance audit — N+1 queries, template rendering speed | Views | 15min |

---

## 📋 EXECUTION TRACKER

| Phase | Description | Status | Tasks | Notes |
|-------|-------------|--------|-------|-------|
| **1** | Dynamic Detail View Router | ✅ COMPLETE | 6/6 | `detail.py` — PHASE_TEMPLATES, get_template_names(), _get_phase_context() |
| **2** | Registration Phase Template | ✅ COMPLETE | 8/8 | `detail_registration.html` — countdown, CTA, prize podium, participants |
| **3** | Live Tournament Template | ✅ COMPLETE | 8/8 | `detail_live.html` — match cards, bracket mini-view, progress bar, auto-refresh |
| **4** | Completed Tournament Template | ✅ COMPLETE | 6/6 | `detail_completed.html` — champion showcase, podium, bracket, standings |
| **5** | Match Room / Battlefield | ✅ COMPLETE | 7/7 | `match_room.py` + `room.html` — access control, check-in, lobby info |
| **6** | Enhanced Lobby Hub | ⏭️ SKIPPED | — | Existing lobby (255 lines) already well-built |
| **7** | Dashboard Integration | ✅ COMPLETE | 6/6 | Next match CTA banner, clickable tournament cards, status badges |
| **8** | Arena Overhaul | ✅ COMPLETE | 6/6 | `/arena/` URL, nav updated, live scoreboard section |
| **9** | Bracket Visualization | ✅ COMPLETE | 6/6 | Enhanced CSS connectors, participant names, winner highlighting |
| **10** | Polish & Testing | 🔄 IN PROGRESS | 3/7 | Imports validated, templates discoverable, URLs resolve |

**Total Tasks: 66 | Completed: 56 | Remaining: 4**

---

## 🏗️ TEMPLATE HIERARCHY

```
templates/tournaments/
├── base.html                           (existing — shared base)
├── list.html                           (existing — tournament listing)
├── detailPages/
│   ├── detail.html                     (EXISTING — current monolith, will become fallback)
│   ├── _base_detail.html               (NEW — shared hero + sidebar skeleton)
│   ├── detail_registration.html        (NEW — registration open/published phase)
│   ├── detail_checkin.html             (NEW — check-in / pre-tournament phase)
│   ├── detail_live.html                (NEW — live tournament phase)
│   ├── detail_completed.html           (NEW — completed/archived phase)
│   └── detail_cancelled.html           (NEW — cancelled tournament)
├── components/
│   ├── _bracket_tree.html              (NEW — reusable bracket component)
│   ├── _bracket_node.html              (NEW — individual match node)
│   ├── _group_table.html               (NEW — round-robin group table)
│   ├── _match_card_live.html           (NEW — live match scorecard)
│   ├── _countdown_timer.html           (NEW — reusable countdown component)
│   ├── _participant_roster.html        (NEW — check-in aware roster grid)
│   ├── _prize_podium.html              (NEW — prize breakdown display)
│   ├── _champion_showcase.html         (NEW — winner celebration)
│   └── (existing components remain)
├── match_room/
│   ├── room.html                       (NEW — match lobby/battlefield page)
│   ├── _pre_match.html                 (NEW — pre-match waiting state)
│   ├── _in_match.html                  (NEW — during match state)
│   └── _post_match.html                (NEW — result submission state)
└── lobby/
    └── hub.html                        (REDESIGN — enhanced lobby)
```

---

## 🎨 DESIGN SYSTEM NOTES

- **Dark glassmorphism** base (existing): `#030303` background, `rgba(17,17,17,0.65)` glass panels
- **Game-dynamic branding**: `--game-color` CSS custom property from `game_spec`
- **Typography**: Rajdhani for headings/tabs, Inter for body
- **Icons**: Lucide icons (existing)
- **CSS Framework**: Tailwind CSS utilities (existing)
- **Animations**: CSS keyframes for subtle motion (pulse, float, fade-in)
- **Color semantics**:
  - Live: `#ef4444` red pulse
  - Registration Open: `#06b6d4` cyan
  - Completed: `#10b981` emerald
  - Cancelled: `#6b7280` gray

---

## 🔗 URL MAP (Final)

| URL | Page | Status Awareness |
|-----|------|------------------|
| `/tournaments/` | Tournament List | — |
| `/tournaments/<slug>/` | **Dynamic Detail** (routes by status) | ✅ |
| `/tournaments/<slug>/lobby/` | Enhanced Lobby Hub | registered only |
| `/tournaments/<slug>/bracket/` | Full-page bracket view | live/completed |
| `/tournaments/<slug>/matches/<id>/` | Match Room / Battlefield | participants only |
| `/tournaments/<slug>/results/` | Results page | completed |
| `/tournaments/<slug>/register/` | Registration flow | reg open |
| `/arena/` | Arena (scoreboard + streams) | global |
| `/watch/` | → 301 redirect to `/arena/` | deprecated |
| `/dashboard/` | Dashboard (with tournament tiles) | authenticated |

---

## 📝 NOTES

1. **Backward Compatibility**: The existing `detail.html` (1620 lines) stays as fallback. New phase templates will be loaded via `get_template_names()` override.
2. **No Database Migrations**: This is purely a frontend/view-layer overhaul. Models stay the same.
3. **Progressive Enhancement**: New templates can be rolled out one phase at a time. If a phase template doesn't exist yet, falls back to existing `detail.html`.
4. **Reusable Components**: Bracket tree, match cards, countdown timer, etc. are built as include-able components.
5. **Seed Script Updates**: Need tournaments in `registration_open`, `live`, and `completed` states for testing.
