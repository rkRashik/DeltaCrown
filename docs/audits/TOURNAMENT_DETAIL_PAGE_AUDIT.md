# Tournament Detail Page — Definitive Audit v3

> **Date:** March 2026 | **Scope:** Full re-audit with complete platform context  
> **Files:** 7 detail templates (3,618 lines), 12 Hub templates (2,191 lines), detail.py (980 lines), hub.py (1,546 lines), Tournament model (78 fields), Game system (7 models), full platform (25+ apps)

---

## Table of Contents

1. [Platform Context — Why This Matters](#1-platform-context)
2. [Architecture: Detail vs Hub — The Split](#2-architecture-detail-vs-hub)
3. [What the Hub Already Covers (Don't Duplicate)](#3-what-the-hub-already-covers)
4. [What the Detail Page Must Be](#4-what-the-detail-page-must-be)
5. [Current Detail Page Feature Inventory](#5-current-detail-page-feature-inventory)
6. [Game-Dynamic Requirements](#6-game-dynamic-requirements)
7. [Audience Matrix — Who Sees What](#7-audience-matrix)
8. [Tournament State Behavior](#8-tournament-state-behavior)
9. [Platform Integration — The Ecosystem Links](#9-platform-integration)
10. [Gap Analysis — What's Missing](#10-gap-analysis)
11. [Unique Detail Page Vision for DeltaCrown](#11-unique-detail-page-vision)
12. [Prioritized Roadmap](#12-prioritized-roadmap)

---

## 1. Platform Context

DeltaCrown is **not** a tournament platform. It is an **esports operating system** — a complete gamer lifecycle ecosystem encompassing:

| System | Purpose | Tournament Connection |
|--------|---------|----------------------|
| **User Profile** | Professional esports identity with GamePassports, career stats, skill ratings, badges, hardware loadout, bounties, LFT status, trophies | Tournament results feed career stats, unlocks badges/trophies |
| **Teams (Organizations)** | Professional org structure: teams, rosters, captain/IGL, branding, CP rankings, org hierarchy | Teams register for tournaments, roster validation, captain check-in |
| **Economy (DeltaCoin)** | Digital currency: wallets, entry fees, prize distribution, bKash/Nagad/Rocket payments, escrow | Entry fees deducted, prizes distributed, DeltaCoin rewards per placement |
| **Leaderboards** | Multi-dimensional rankings: tournament, seasonal, all-time, team, game-specific, ELO/MMR, historical snapshots | Every match → ranking update → leaderboard entry |
| **Competition** | Cross-game ranking engine: team ELO, tier system (Crown→Unranked), challenges, bounties, match verification | Tournament performance feeds team tier/ELO, Crown Points |
| **Games (11 titles)** | Game-agnostic config: roster rules, scoring types, match formats, identity requirements, roles, tiebreakers per game | Determines everything: team size, scoring, roles, IDs, match format |
| **Challenges** | Team-vs-team wagering, scrims, bounties, duels | Alternative competitive mode between tournament participants |
| **Shop / E-Commerce** | DeltaCoin marketplace + real merchandise | Players spend earnings from tournaments |
| **Spectator** | Read-only live views with htmx/WebSocket | Public viewing of live tournaments |
| **Notifications** | Multi-channel notifications (SSE, email, push) | Auto-fire on bracket gen, check-in, match ready, results |
| **Discord** | Webhook integration per tournament | Auto-posts: registrations, brackets, match results, announcements |

**The tournament detail page is the gateway to this entire ecosystem.** It's not just "tournament info" — it's the public storefront that converts visitors into registered participants, spectators into followers, and casual gamers into career-building competitors.

---

## 2. Architecture: Detail vs Hub — The Split

### Current URL Structure

```
/tournaments/<slug>/           → TournamentDetailView  → PUBLIC (anyone)
/tournaments/<slug>/hub/       → TournamentHubView     → PRIVATE (registered participants + staff)
/tournaments/<slug>/spectator/ → PublicSpectatorView    → PUBLIC (live/completed only)
/toc/<slug>/                   → TOC views              → PRIVATE (organizer/staff only)
```

### The Fundamental Rule

| Page | Audience | Purpose | Analogy |
|------|----------|---------|---------|
| **Detail Page** | EVERYONE — anonymous, logged-in, potential registrants, fans, spectators, scouts | **Storefront + Live Stadium** — convince people to register, let fans watch live, show completed results, link to the ecosystem | A football match page on ESPN/FotMob — anyone can see it |
| **Hub** | REGISTERED participants + tournament staff ONLY | **War Room + Locker Room** — check-in, match lobby, squad management, roster swaps, result submission, support tickets | The team's private dressing room — only players and staff enter |
| **TOC** | Organizer + staff ONLY | **Control Tower** — manage tournament operations | The referee/broadcast room — organizers only |
| **Spectator** | Anyone (live/completed) | **Spectator Gallery** — focused bracket/standings/matches view | The press box — watch-only |

### What This Means for the Audit

The previous audits made the mistake of evaluating the detail page in isolation. The detail page should NOT:
- Duplicate Hub features (squad management, check-in actions, match lobby, roster swaps, support tickets, prize claims)
- Include participant-only operational tools
- Be a "everything page" that tries to do what Hub does

The detail page SHOULD:
- Be the best PUBLIC face of the tournament
- Dynamically adapt based on game, tournament state, and viewer type
- Link seamlessly into the ecosystem (profiles, teams, leaderboards, economy)
- Convert visitors into participants/fans
- Serve as the live scoreboard for spectators
- Showcase results and champion glory when completed

---

## 3. What the Hub Already Covers

The Hub is a 2,191-line SPA with 11 tabs powered by real-time JSON APIs. Here's what's already handled there:

| Feature | Hub Tab | Lines | Don't Duplicate On Detail |
|---------|---------|-------|--------------------------|
| Check-in action (button + states) | Overview + Matches | 435 + 126 | ❌ Don't add check-in button to detail |
| Squad management (roster swaps, game IDs) | Squad | 229 | ❌ Don't add roster editing to detail |
| Match lobby (lobby codes, result submission) | Matches | 126 | ❌ Don't add match operations to detail |
| Prize claims (claim flow, payment methods) | Prizes | 141 | ❌ Don't add prize claim form to detail |
| Support/dispute tickets | Support | 301 | ❌ Don't add support form to detail |
| Participant search + directory | Participants | 73 | ⚠️ Detail should show participants but READ-ONLY, no search utility |
| Rulebook (PDF iframe + text) | Rulebook | 50 | ⚠️ Detail should show rules summary, full rulebook in Hub |
| Sponsor showcase (tiered display) | Resources | 332 | ✅ Sponsors SHOULD also be on detail (public visibility) |
| Social/contact links | Resources + Sidebar | 183 + 332 | ✅ These MUST be on detail (public discoverability) |
| Announcements | Overview | 435 | ⚠️ Detail could show latest 1-2 pinned announcements, full feed in Hub |
| Bracket (zoomable, async) | Bracket | 100 | ⚠️ Detail should show static/mini bracket, full interactive in Hub |
| Standings (async, "You" highlight) | Standings | 54 | ⚠️ Detail shows public standings table, Hub adds personal highlight |
| Schedule timeline | Schedule | 168 | ✅ Detail already has phase timeline — this is appropriate |

### Key Insight

The Hub is the participant's **private workspace**. The detail page is the tournament's **public stage**. Features should exist on detail ONLY if they serve a public audience. The Hub already handles all operational participant needs — the detail page should focus on:

1. **Information** — What is this tournament?
2. **Conversion** — Why should I register?
3. **Spectating** — What's happening live?
4. **Results** — Who won?
5. **Ecosystem** — How does this connect to the larger DeltaCrown world?

---

## 4. What the Detail Page Must Be

### For DeltaCrown Specifically

This is not Toornament or Battlefy where a tournament is an isolated event. In DeltaCrown, a tournament is a **career milestone** in a player's journey. The detail page must reflect this:

```
┌────────────────────────────────────────────────────────────────┐
│  TOURNAMENT DETAIL PAGE = PUBLIC STAGE                         │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ INFORM       │  │ CONVERT      │  │ CONNECT TO ECOSYSTEM │ │
│  │              │  │              │  │                      │ │
│  │ Game info    │  │ Register CTA │  │ Player profiles      │ │
│  │ Format       │  │ Prize pool   │  │ Team pages           │ │
│  │ Schedule     │  │ Countdown    │  │ Leaderboard rank     │ │
│  │ Rules brief  │  │ Org trust    │  │ Past tournaments     │ │
│  │ Venue        │  │ Slot fill %  │  │ Game passport link   │ │
│  └──────────────┘  └──────────────┘  │ Economy (DC rewards) │ │
│                                      │ Organization page    │ │
│  ┌──────────────┐  ┌──────────────┐  └──────────────────────┘ │
│  │ SPECTATE     │  │ CELEBRATE    │                           │
│  │              │  │              │                           │
│  │ Live scores  │  │ Champion     │                           │
│  │ Live bracket │  │ Podium       │                           │
│  │ Stream embed │  │ Final bracket│                           │
│  │ Fan follow   │  │ Stats        │                           │
│  └──────────────┘  └──────────────┘                           │
└────────────────────────────────────────────────────────────────┘
```

---

## 5. Current Detail Page Feature Inventory

### Template Architecture (Dual System)

| Template | Lines | Status |
|----------|-------|--------|
| `detail.html` (monolith) | 1,684 | Fallback — all-in-one with client-side tabs |
| `_base_detail.html` (shared base) | 674 | Active — phase-routed base with 6 hook blocks |
| `detail_registration.html` | 565 | Active — registration/pre-reg/check-in phases |
| `detail_live.html` | 433 | Active — live tournament with match cards |
| `detail_completed.html` | 335 | Active — champion showcase, final results |
| `detail_cancelled.html` | 99 | Active — cancellation notice |
| `spectator/hub.html` | 228 | Active — standalone spectator view |

**Verdict:** The phase-routed system is the authoritative architecture. The monolith is legacy debt.

### What Currently Works Well

| Feature | Location | Assessment |
|---------|----------|------------|
| **Game-dynamic CSS theming** | `_base_detail.html` L7-289 | **Unique advantage** — CSS vars from GameSpec make each tournament visually distinct per game. No competitor does this. |
| **Phase-routed templates** | `detail.py` `PHASE_TEMPLATES` dict | **Architecturally superior** — Each state gets a purpose-built template. Better than competitors' one-size-fits-all. |
| **Working countdown timer** | `_base_detail.html` L652-674, `detail_registration.html` L96-114 | ✅ JS-based days/hours/minutes/seconds targeting reg close or tournament start |
| **FotMob-style live match cards** | `detail_live.html` L145-210 | ✅ Team logos, live scores, stream link per match |
| **Champion showcase with confetti** | `detail_completed.html` L16-60, L95-126 | **Best-in-class** — 6 confetti pieces, gold shimmer text, trophy glow. No competitor matches this. |
| **Podium (1st/2nd/3rd)** | `detail_completed.html` L129-150, `detail_registration.html` L164-218 | ✅ Medal colors, prize amounts |
| **Hero with parallax banner** | `detail.html` L161-185, `_base_detail.html` shared | ✅ slowPan animation, HiDPI overrides |
| **9 status badges** | Across all templates | ✅ Live pulse, reg open pulse, color-coded per state |
| **Phase timeline (5 steps)** | `detail.html` L419-520 | ✅ Animated gradient progress bar |
| **Match configuration grid** | `detail.html` L522-590 | ✅ Format, match type, game, capacity |
| **Prize pool display** | Multiple locations | ✅ BDT + DeltaCoin hybrid |
| **Registration CTA (3 states)** | Multiple locations | ✅ Register/Registered/Closed |
| **Venue section (LAN/Hybrid)** | `detail.html` L849-888 | ✅ Name, address, Google Maps link |
| **Feature flags sidebar** | `detail.html` L1583-1600 | ✅ 6 toggles displayed |
| **Mobile sticky CTA** | `_base_detail.html` L634-649 | ✅ Fixed bottom bar |

### What's Broken or Incomplete

| Issue | Location | Severity |
|-------|----------|----------|
| **Monolith vs phase system coexist** | `detail.html` (1,684 lines) + phase system | Critical — maintain debt, feature drift |
| **`cancellation_reason` missing from model** | `detail_cancelled.html` L34 references nonexistent field | High — template renders blank |
| **`_get_registration_status()` never called** | `detail.py` L309-382 — defined but not invoked | Medium — detailed reg state unreachable |
| **14+ model fields never rendered** | Social links, contact, refund policy, promo video | High — valuable data invisible |
| **Spectator view undiscoverable** | No link from detail page to `/spectator/` | High — feature exists but invisible |
| **60s full page reload for live** | `detail_live.html` L412-433 | Medium — loses scroll, jarring UX |
| **`alert()` for share feedback** | `detail.html` share button handler | Low — unprofessional |
| **No tournament-specific OG meta** | Generic base.html OG tags | Medium — social sharing broken |
| **Report button non-functional** | `detail.html` L353 | Low — button exists, no handler |

---

## 6. Game-Dynamic Requirements

DeltaCrown supports 11 games across 4 categories. The detail page MUST adapt per game — not just colors, but **information architecture**.

### Current Game-Dynamic Features (Working)

| Feature | How It Adapts |
|---------|---------------|
| CSS theme colors | `--game-color`, `--game-color-secondary` from `Game.primary_color/secondary_color` |
| Game badge | `game_spec.icon.url` + `game_spec.display_name` |
| Team size display | `game_spec.roster_config.get_team_size_display` → "5v5", "4v4", "1v1" |
| Platform badge | `tournament.platform` → smartphone/gamepad/monitor icons |

### What MUST Become Game-Dynamic (Currently Static)

| Feature | Current | Should Be |
|---------|---------|-----------|
| **Standings table columns** | Hardcoded MP/W/D/L/Pts with generic stats | FPS: RD (Round Diff), MOBA: W/L, BR: Kills/Avg Place, Sports: GD/GF/GA |
| **Match card stats** | Just scores | FPS: Round score (13-7), BR: Placement + Kills, Sports: Goals + Possession |
| **Scoring type label** | Not shown | "Round-Based" (FPS), "Placement+Kill" (BR), "Goal-Based" (Sports), "Win/Loss" (MOBA) |
| **Tiebreaker rules** | Not displayed | Should show per-game tiebreaker order in rules/info section |
| **Player identity labels** | Generic "Game ID" | "Riot ID" (Valorant), "Character ID" (PUBG), "EA ID" (FIFA) |
| **Role display** | Not shown at all | Valorant: Duelist/Controller, MLBB: Tank/Support, Dota2: Carry/Mid. None for BR/Sports |
| **Match format badge** | Shows default only | "BO3" (FPS/MOBA), "Single Match" (BR), "BO1" (Sports) |
| **Draw possibility** | Not shown | Sports: "Draws Allowed", FPS: "Overtime decides" |
| **Match duration estimate** | Not shown | ~45min (FPS), ~20min (MOBA), ~30min (BR), ~15min (Sports) |

### Game Category Visual Profiles

For the unique DeltaCrown detail page, each game category should have a subtly different information layout:

**FPS (Valorant, CS2, R6, CODM):**
- Featured stat: Round Difference
- Match cards: Map name + round score (13-7)
- Roster shows: Player roles (Duelist, Controller, etc.)
- Hero accent: Tactical/sharp visual language

**MOBA (Dota2, MLBB):**
- Featured stat: Win/Loss record
- Match cards: Game score (2-1 in BO3)
- Roster shows: Lane roles (Carry, Mid, Support)
- Hero accent: Strategic/ability-based visual language

**Battle Royale (PUBG Mobile, Free Fire):**
- Featured stat: Kill leaderboard + Average Placement
- Match cards: Placement position (#1, #4) + Kill count
- Roster shows: Squad members (no roles)
- Hero accent: Survival/intensity visual language
- **Unique:** Standings should show placement points table, not traditional W/L

**Sports (EA FC, eFootball, Rocket League):**
- Featured stat: Goal Difference
- Match cards: Goal score (3-1) with overtime indicator
- Solo tournaments (1v1) — no roster display needed
- Hero accent: Athletic/clean visual language
- **Unique:** Draw is a valid result

---

## 7. Audience Matrix — Who Sees What

### User Types

| Type | Detection | What They Need from Detail Page |
|------|-----------|-------------------------------|
| **Anonymous visitor** | `not request.user.is_authenticated` | Full tournament info, CTA to sign up → register, social proof (participant count, org reputation) |
| **Logged-in, not registered** | `is_authenticated and not is_registered` | Same + personalized CTA ("Register Now"), eligibility check, prize info, entry fee with wallet balance hint |
| **Logged-in, registered** | `is_registered == True` | "Enter Hub" CTA (NOT check-in/lobby tools — those are in Hub), tournament status at a glance, quick link to their next match |
| **Scout / recruiter** | Any logged-in user viewing participants | Participant cards should link to player profiles + game passports — this is how talent discovery works in DeltaCrown |
| **Fan / spectator** | Anyone during live/completed | Live scores, bracket, standings, stream embed, share buttons, follow button (future) |
| **Team org manager** | Logged in, team's org | Their team's placement, org branding on participant card, link to team management |
| **Organizer / staff** | `is_organizer == True` | Quick stats, TOC link, Hub link — but NOT management tools on detail page |
| **Admin** | `is_staff or is_superuser` | Same as organizer + moderation shortcuts |

### What's Different from Other Platforms

On Toornament/Battlefy, participants only exist within that tournament. On DeltaCrown:
- Every participant has a **persistent profile** with career stats, game passports, badges, trophies
- Every team has a **persistent team page** with rankings, CP tier, match history
- Every team may belong to an **organization** with its own branding and hierarchy
- Every player has **leaderboard rankings** that span across tournaments

**This means:** Participant cards on the detail page should be *portals* into the ecosystem — clicking a team name should go to their team page, clicking a player name should go to their profile, showing their team's current ranking tier badge.

---

## 8. Tournament State Behavior

### Phase Template Routing

```python
PHASE_TEMPLATES = {
    'draft':               'detail_registration.html',   # "Coming Soon"
    'pending_approval':    'detail_registration.html',   # "Coming Soon"
    'published':           'detail_registration.html',   # Pre-registration info
    'registration_open':   'detail_registration.html',   # Active registration
    'registration_closed': 'detail_registration.html',   # Check-in phase
    'live':                'detail_live.html',            # Live tournament
    'completed':           'detail_completed.html',       # Results + champion
    'archived':            'detail_completed.html',       # Historical record
    'cancelled':           'detail_cancelled.html',       # Cancellation notice
}
```

### Per-State Information Priority

| State | Primary Content | Secondary Content | CTA |
|-------|----------------|-------------------|-----|
| **Draft** | Tournament info, game, format, prize | Coming soon messaging | None (not public) |
| **Published** | Full info, schedule timeline, rules brief | Countdown to reg open | "Notify Me" (future) |
| **Reg Open** | Prize pool, participant progress, countdown to close | Requirements, entry fee, format details | **"Register Now"** (hero-level) |
| **Reg Closed** | Participants locked, countdown to start | Schedule, bracket preview | "Enter Hub" (registered) / "Watch Soon" (public) |
| **Live** | **Live scores + bracket + stream** (primary), standings | Match progress, next matches | "Enter Hub" (registered) / "Watch Live" (public) |
| **Completed** | **Champion + podium + final results** | Full bracket, standings, stats | "View Results" / share |
| **Archived** | Same as completed but muted | Historical context | None |
| **Cancelled** | Cancellation reason, refund info | Preserved tournament details | Support contact |

---

## 9. Platform Integration — The Ecosystem Links

### Current Integration (Working)

| Link | From Detail | To | Status |
|------|------------|-----|--------|
| TOC button | Hero section | `/toc/<slug>/` | ✅ Organizer-only |
| Hub button | Hero + sidebar | `/<slug>/hub/` | ✅ Organizer-only (should also show for registered) |
| Register CTA | Multiple | `/<slug>/register/` | ✅ |
| Lobby link | Sidebar CTA | `/<slug>/lobby/` → Hub | ✅ Registered-only |
| Stream link | Hero button | External YouTube/Twitch | ✅ |
| Full bracket | Phase templates | `/<slug>/bracket/` | ✅ "Full View" link |

### Missing Integration (Should Be Added)

| Link | From Detail | To | Impact |
|------|------------|-----|--------|
| **Player profile links** | Participant cards | `/profile/<username>/` | High — connects to career system |
| **Team page links** | Participant cards (team mode) | `/teams/<slug>/` | High — connects to org system |
| **Team ranking tier badge** | Participant cards | Visual only (Crown/Diamond/Gold badge) | Medium — shows competitive context |
| **Game passport data** | Participant cards | Visual only (IGN, rank, verification check) | Medium — shows game-specific identity |
| **Leaderboard context** | Sidebar or info section | `/leaderboards/?game=<slug>` | Medium — shows where this tournament fits |
| **Organizer profile** | Organizer card | `/profile/<username>/` | Medium — trust signal |
| **Organization page** | Organizer card (if org-hosted) | `/organizations/<slug>/` | Medium — trust signal |
| **DeltaCoin reward info** | Prize section | Visual only (participation/win/top4 rewards) | Medium — shows ecosystem value |
| **Discord server** | Social section (currently missing) | External Discord link | Critical — community is everything in esports |
| **Social links** | Social section (currently missing) | External social links | High — 7 fields exist, none rendered |
| **Spectator view** | Live/completed hero | `/<slug>/spectator/` | High — feature exists but undiscoverable |
| **Player's own team** | Registered user view | "Your team" summary with Hub link | Medium — registered participant awareness |
| **Related tournaments** | Bottom of page | Other tournaments by same organizer/game | Low — retention |
| **Series context** | Header/breadcrumb | Future series/season page | Low — not yet built |

---

## 10. Gap Analysis — What's Missing

### Tier 1: Critical (Detail Page Fundamentals)

| # | Gap | Detail | Effort |
|---|-----|--------|--------|
| 1.1 | **Resolve dual template architecture** | Commit to phase system, archive 1,684-line monolith. Phase system already has MORE features. | Medium |
| 1.2 | **Wire social links + Discord** | 7 social fields + contact_email + support_info exist on model. Hub renders them (sidebar + resources tab). Detail page renders NONE. Discord is critical for esports communities. | Low |
| 1.3 | **Tournament-specific OG meta tags** | `og:image` → `tournament.banner_image.url`, `og:description` → `tournament.meta_description`, `og:url` → canonical URL. Currently generic. Social sharing is broken without this. | Low |
| 1.4 | **Add `cancellation_reason` to model** | `detail_cancelled.html` references it, field doesn't exist. | Low |
| 1.5 | **Link spectator view from detail** | Feature exists at `/<slug>/spectator/`, nowhere linked. Add "Spectator Mode" button for live/completed. | Low |
| 1.6 | **DeltaCoin reward display** | CoinPolicy exists (participation: 5 DC, top4: 25 DC, runner_up: 50 DC, winner: 100 DC). Not shown on detail page. This is a KEY conversion lever — "Compete and earn DeltaCoin regardless of placement." | Low-Med |

### Tier 2: High Priority (Ecosystem Integration)

| # | Gap | Detail | Effort |
|---|-----|--------|--------|
| 2.1 | **Participant cards → profile/team links** | Currently participant names are plain text. In DeltaCrown, every player has a profile, every team has a team page. Participant cards should link to both, showing team ranking tier badge if available. | Medium |
| 2.2 | **Game-dynamic standings columns** | Hardcoded W/D/L/Pts. Should be: FPS → Round Diff, BR → Kills/Avg Place, Sports → GD/GF/GA. `GameTournamentConfig` already has scoring config. | Medium |
| 2.3 | **Game-dynamic match card stats** | Match cards only show basic scores. Should show game-relevant stats: round score (FPS), placement+kills (BR), goals+possession (Sports). `GameMatchResultSchema` exists. | Medium |
| 2.4 | **Render refund policy** | `refund_policy` + `refund_policy_text` fields exist. Not shown. Critical for trust when entry fees are involved. | Low |
| 2.5 | **Sponsor section (public)** | Hub has 4-tier sponsor showcase in Resources tab. Detail page has NONE. Sponsors need public visibility — that's the whole point of sponsorship. The `TournamentSponsor` model exists. | Medium |
| 2.6 | **Wire `_get_registration_status()`** | 73 lines of detailed registration state logic defined but never called. Enables better CTA states (payment pending, check-in required, etc.) | Low |
| 2.7 | **Show player roles per game** | `GameRole` data exists (Valorant: Duelist/Controller/Initiator/Sentinel, etc.). Participant roster shows no roles. For team games this is meaningful competitive info. | Low-Med |

### Tier 3: Medium Priority (Live Experience + UX)

| # | Gap | Detail | Effort |
|---|-----|--------|--------|
| 3.1 | **Replace 60s full reload with AJAX polling** | `detail_live.html` reloads entire page every 60 seconds. Replace with AJAX polling match scores + bracket state every 10s. Hub already uses JSON APIs that could be reused. | Medium |
| 3.2 | **Replace `alert()` with toast** | Share button uses `alert('Link copied!')`. Needs custom toast notification. | Low |
| 3.3 | **Add Web Share API** | Only clipboard copy exists. Add native share sheet (mobile) with fallback to Twitter/WhatsApp/Discord share URLs. | Low |
| 3.4 | **JSON-LD Event structured data** | No schema.org markup. Needed for Google rich results: Event type with name, date, location, organizer, offers. | Low |
| 3.5 | **Scoring type + tiebreaker display** | `GameTournamentConfig` has `get_tiebreakers_display()`. Not surfaced. Players want to know HOW standings are calculated. | Low |
| 3.6 | **Match duration estimate** | `GameTournamentConfig.default_match_duration_minutes` exists. Not shown. Helpful for scheduling. | Low |
| 3.7 | **Recent matches on overview** | Match results only visible in Matches tab. Show last 3-5 completed matches on overview for quick context. | Low |
| 3.8 | **Render promo video** | `promo_video_url` field exists. Not rendered. Would add engagement on tournament info section. | Low |

### Tier 4: Future Vision (Build Unique Identity)

| # | Gap | Detail | Effort |
|---|-----|--------|--------|
| 4.1 | **Follow/favorite tournament** | No bookmark/follow mechanism. Critical for re-engagement + notifications. | Medium |
| 4.2 | **Interactive bracket (SVG/D3)** | Mini bracketsexist but static HTML. Full bracket page exists. Detail page needs an embedded mini-bracket that's actually interactive. | High |
| 4.3 | **Real-time WebSocket scores** | Replace polling with Django Channels push. Hub already has WebSocket consumer (`hub-ws-indicator` exists). | High |
| 4.4 | **Fan voting UI** | `enable_fan_voting` flag exists, renders as a feature flag check mark, but no actual voting interface. | Med-High |
| 4.5 | **BR placement point table** | For Battle Royale tournaments, show the placement → points conversion table. `BRScoringMatrix` exists in games models. | Low-Med |
| 4.6 | **Series/season context** | No tournament series linking. "Previous Editions" or "Part of Season X" context. | High |
| 4.7 | **Embeddable widgets** | Bracket/standings widgets for external sites/Discord. Hub bracket tab links to spectator view — detail page could offer embed codes. | Medium |
| 4.8 | **Map pool / veto display** | FPS/MOBA games have map pools. No UI for this. | Medium |

---

## 11. Unique Detail Page Vision for DeltaCrown

### Why DeltaCrown's Detail Page Should Be Different

DeltaCrown is not a tournament tool — it's a **gamer's career platform** that happens to run tournaments. The detail page must reflect this by being:

1. **Ecosystem-connected** — Every entity on the page (player, team, organizer, game) is a clickable portal into the broader platform
2. **Career-contextualized** — Show team rankings, player stats, DeltaCoin rewards — make every tournament feel like a step in a larger journey
3. **Game-native** — Not just different colors, but different *information architecture* per game category
4. **Community-first** — Discord link, social feeds, announcements are first-class, not afterthoughts
5. **Conversion-optimized** — The page's job during registration is to convert visitors into participants. Prize pool, DeltaCoin rewards, slot fill %, countdown, org trust signals — all serve conversion

### Proposed Information Architecture

```
╔══════════════════════════════════════════════════════════╗
║  HERO                                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │ [Game banner — parallax, game-themed colors]        │  ║
║  │                                                     │  ║
║  │ [Status Badge] [Game Badge] [Platform] [Mode]       │  ║
║  │                                                     │  ║
║  │ TOURNAMENT NAME                                     │  ║
║  │ Short description                                   │  ║
║  │                                                     │  ║
║  │ [Prize Pool]  [Start Date]  [Team Size]  [Format]   │  ║
║  │                                                     │  ║
║  │ [Register CTA]  [Share]  [Enter Hub]  [Spectate]    │  ║
║  │ [Organizer Tools: TOC | Hub] (organizer only)       │  ║
║  └─────────────────────────────────────────────────────┘  ║
╠══════════════════════════════════════════════════════════╣
║  MAIN CONTENT (2-col: content + sidebar)                  ║
║                                                           ║
║  ┌─ Content (Left) ──────────────────────────────────┐   ║
║  │                                                    │   ║
║  │  Game-Dynamic Info:                                │   ║
║  │  ┌──────────────────────────────────────────────┐  │   ║
║  │  │ Format: Single Elimination  │ BO3           │  │   ║
║  │  │ Scoring: Round-Based (FPS)  │ Overtime: Yes │  │   ║
║  │  │ Platform: Mobile            │ Mode: Online  │  │   ║
║  │  │ Duration: ~45 min/match     │ Draws: No     │  │   ║
║  │  │ Tiebreakers: H2H → RD → RW                 │  │   ║
║  │  └──────────────────────────────────────────────┘  │   ║
║  │                                                    │   ║
║  │  Event Briefing (read more/less)                   │   ║
║  │                                                    │   ║
║  │  Prize Pool + DeltaCoin Rewards:                   │   ║
║  │  ┌──────────────────────────────────────────────┐  │   ║
║  │  │ 🥇 10,000 BDT + 100 DC                     │  │   ║
║  │  │ 🥈  5,000 BDT +  50 DC                     │  │   ║
║  │  │ 🥉  2,000 BDT +  25 DC                     │  │   ║
║  │  │ ── Every participant earns 5 DC ──          │  │   ║
║  │  └──────────────────────────────────────────────┘  │   ║
║  │                                                    │   ║
║  │  Phase Timeline (Registration → Live → Complete)   │   ║
║  │                                                    │   ║
║  │  [Phase-specific content]:                         │   ║
║  │  - REG: Countdown + Participant list + Rules brief │   ║
║  │  - LIVE: Live match cards + Mini bracket + Stream  │   ║
║  │  - DONE: Champion showcase + Final results         │   ║
║  │                                                    │   ║
║  │  Participants (with ecosystem links):              │   ║
║  │  ┌──────────────────────────────────────────────┐  │   ║
║  │  │ [Team Logo] Team Name [Crown Tier Badge]    │  │   ║
║  │  │   → Links to team page                      │  │   ║
║  │  │ Player1 (Duelist) | Player2 (Controller)    │  │   ║
║  │  │   → Each links to profile                   │  │   ║
║  │  └──────────────────────────────────────────────┘  │   ║
║  │                                                    │   ║
║  │  Standings (game-dynamic columns)                  │   ║
║  │  Bracket (mini interactive preview)                │   ║
║  │                                                    │   ║
║  └────────────────────────────────────────────────────┘   ║
║                                                           ║
║  ┌─ Sidebar (Right) ─────────────────────────────────┐   ║
║  │                                                    │   ║
║  │  Registration Card:                                │   ║
║  │  - CTA button (state-aware)                        │   ║
║  │  - Slot progress bar (X/Max)                       │   ║
║  │  - Entry fee + payment methods                     │   ║
║  │  - Refund policy (if applicable)                   │   ║
║  │                                                    │   ║
║  │  Organizer Card:                                   │   ║
║  │  - Avatar + name (links to profile)                │   ║
║  │  - Official badge / Community badge                │   ║
║  │  - Trust signals (verified, # tournaments hosted)  │   ║
║  │                                                    │   ║
║  │  Community & Contact:                              │   ║
║  │  - Discord (prominent, with member count if avail) │   ║
║  │  - Twitter, Instagram, YouTube, etc.               │   ║
║  │  - Contact email                                   │   ║
║  │  - Support info                                    │   ║
║  │                                                    │   ║
║  │  Game Info:                                        │   ║
║  │  - Game icon + name (links to game page)           │   ║
║  │  - Category (FPS/MOBA/BR/Sports)                   │   ║
║  │  - Required ID type ("Riot ID", "Character ID")    │   ║
║  │  - Roles (if applicable for this game)             │   ║
║  │                                                    │   ║
║  │  DeltaCrown Rewards Card:                          │   ║
║  │  - "Earn DeltaCoin by competing"                   │   ║
║  │  - Win: 100 DC / Runner-up: 50 DC / Top 4: 25 DC  │   ║
║  │  - Participation: 5 DC                             │   ║
║  │                                                    │   ║
║  │  Feature Flags:                                    │   ║
║  │  - Check-In, Live Updates, Certificates, etc.      │   ║
║  │                                                    │   ║
║  │  Sponsors (if any):                                │   ║
║  │  - Title/Gold/Silver sponsor logos                  │   ║
║  │                                                    │   ║
║  └────────────────────────────────────────────────────┘   ║
╠══════════════════════════════════════════════════════════╣
║  BOTTOM SECTION                                           ║
║  [Pinned Announcements] (1-2 latest)                      ║
║  [Related Tournaments by this Organizer / Same Game]      ║
╚══════════════════════════════════════════════════════════╝
```

### What Makes This Unique (vs. Competitors)

| Aspect | Competitors | DeltaCrown Detail Page |
|--------|-------------|----------------------|
| **Participant cards** | Plain names/teams | Links to profiles + team pages with ranking tier badges |
| **Prize display** | Cash only | Cash + DeltaCoin + participation rewards |
| **Game adaptation** | Same layout for all games | Different stat columns, card layouts, role displays per game category |
| **Community** | Discord link buried | Discord as first-class sidebar element |
| **Organizer trust** | Basic name | Profile link + official badge + verified indicator + tournament count |
| **Career context** | None | "This tournament counts toward your Season 1 ranking" |
| **Economy integration** | None | DeltaCoin reward tiers shown, wallet balance hint for entry fee |
| **Player identity** | Generic | Game-specific identity labels ("Riot ID", "UID") + verification status |
| **Post-tournament** | Basic results | Champion showcase + career stat updates + badge unlocks |

---

## 12. Prioritized Roadmap

### Sprint A: Foundation (Fix Critical Issues)

| # | Task | Type | Effort | Impact |
|---|------|------|--------|--------|
| A1 | Archive `detail.html` monolith, commit to phase system | Cleanup | Medium | Eliminates dual-maintenance debt |
| A2 | Wire Discord + all social links to detail page sidebar | Feature | Low | Community discoverability |
| A3 | Add `cancellation_reason` field to Tournament model | Bugfix | Low | Fixes blank cancellation page |
| A4 | Override OG meta tags with tournament-specific data | Feature | Low | Fixes social sharing |
| A5 | Link spectator view from detail (live/completed) | Feature | Low | Makes existing feature discoverable |
| A6 | Call `_get_registration_status()` in view context | Bugfix | Low | Enables detailed CTA states |
| A7 | Replace `alert()` with toast notification | UX | Low | Professional polish |
| A8 | Render refund policy in registration section | Feature | Low | Trust and transparency |

### Sprint B: Ecosystem Integration

| # | Task | Type | Effort | Impact |
|---|------|------|--------|--------|
| B1 | Participant cards link to player profiles + team pages | Feature | Medium | Connects to career/team system |
| B2 | Show team ranking tier badge on participant cards | Feature | Low-Med | Shows competitive context |
| B3 | DeltaCoin reward tier display (from CoinPolicy) | Feature | Low-Med | Conversion lever — "earn DC just by participating" |
| B4 | Sponsor section on detail page (from TournamentSponsor) | Feature | Medium | Public sponsor visibility |
| B5 | Organizer card → profile link + tournament count | Feature | Low | Trust signal |
| B6 | Game identity labels ("Riot ID" vs "Character ID") | Feature | Low | Game-native feel |
| B7 | Show player roles per game (GameRole) | Feature | Low-Med | Competitive info for team games |

### Sprint C: Game-Dynamic Information

| # | Task | Type | Effort | Impact |
|---|------|------|--------|--------|
| C1 | Game-dynamic standings columns | Feature | Medium | Correct stats per game category |
| C2 | Game-dynamic match card stats | Feature | Medium | Relevant info per game |
| C3 | Scoring type + tiebreaker display | Feature | Low | Transparency |
| C4 | Match format + duration + draws info | Feature | Low | Complete match configuration |
| C5 | BR placement points table (from BRScoringMatrix) | Feature | Low-Med | BR-specific info |
| C6 | JSON-LD Event structured data | SEO | Low | Google rich results |

### Sprint D: Live Experience Enhancement

| # | Task | Type | Effort | Impact |
|---|------|------|--------|--------|
| D1 | Replace 60s reload with AJAX polling (10s) | Feature | Medium | Smooth live experience |
| D2 | Web Share API with platform fallbacks | Feature | Low | Better sharing |
| D3 | Follow/favorite tournament (UserFavorite model) | Feature | Medium | Re-engagement |
| D4 | Recent matches on overview tab | Feature | Low | Quick context |
| D5 | Render promo video on detail page | Feature | Low | Engagement |

### Sprint E: Future Vision

| # | Task | Type | Effort | Impact |
|---|------|------|--------|--------|
| E1 | Interactive SVG bracket (D3.js) | Feature | High | Tournament centerpiece |
| E2 | WebSocket real-time scores | Feature | High | Eliminates polling |
| E3 | Fan voting UI | Feature | Med-High | Community engagement |
| E4 | Embeddable bracket/standings widgets | Feature | Medium | External sharing |
| E5 | Tournament series/season context | Feature | High | Career progression |
| E6 | Map veto/pool display | Feature | Medium | Game-specific feature |
| E7 | Related tournaments section | Feature | Low-Med | Retention |

### Quick Wins (Can Implement Today)

1. **Wire Discord link** — `{% if tournament.social_discord %}<a href="{{ tournament.social_discord }}">{% endif %}` in sidebar
2. **Add cancellation_reason** — `cancellation_reason = TextField(blank=True, default='')` + migration
3. **Override OG image** — `{% block og_image %}{{ tournament.banner_image.url }}{% endblock %}`
4. **Link spectator view** — `{% if tournament.status in 'live,completed' %}<a href="spectator/">{% endif %}` in hero
5. **Show DeltaCoin rewards** — Query `CoinPolicy` for tournament, display in prize section
6. **Replace alert with toast** — 5-line CSS + JS replacement
7. **Render contact email** — `{% if tournament.contact_email %}` in sidebar
8. **Display scoring type** — `{{ game_spec.tournament_config.get_default_scoring_type_display }}` in match config

---

## Appendix A: Complete Template-to-Model Field Mapping

### Fields Rendered on Detail Page ✅

`name`, `slug`, `description`, `organizer`, `is_official`, `game` (via game_spec), `format`, `participation_type`, `platform`, `mode`, `venue_name/address/city/map_url`, `max_participants`, `registration_start/end`, `tournament_start/end`, `prize_pool`, `prize_deltacoin`, `prize_distribution`, `has_entry_fee/entry_fee_amount/entry_fee_deltacoin`, `payment_methods`, `enable_fee_waiver/fee_waiver_top_n_teams`, `banner_image`, `rules_text/rules_pdf`, `terms_and_conditions/terms_pdf`, `require_terms_acceptance`, `stream_youtube_url/stream_twitch_url`, `enable_check_in/check_in_minutes_before`, `enable_live_updates`, `enable_certificates`, `enable_dynamic_seeding`, `enable_challenges`, `enable_fan_voting`, `status`

### Fields NOT Rendered — Should Be ❌

| Field | Value for Detail Page |
|-------|----------------------|
| `social_discord` | **Critical** — Community hub link |
| `social_twitter` | High — Social engagement |
| `social_instagram` | High — Social engagement |
| `social_youtube` | Medium — Content channel |
| `social_facebook` | Medium — Social engagement |
| `social_tiktok` | Low — Social engagement |
| `social_website` | Medium — External site |
| `contact_email` | High — Organizer contact |
| `contact_phone` | Low — Alternative contact |
| `support_info` | Medium — Support details |
| `promo_video_url` | Medium — Engagement content |
| `meta_description` | Medium — OG description |
| `thumbnail_image` | Medium — OG image fallback |
| `refund_policy/refund_policy_text` | High — Trust when fees involved |
| `is_featured` | Low — Could show "Featured" badge |
| `timezone_name` | Low — Local time conversion |

### Fields Referenced but MISSING from Model

| Field | Template | Fix |
|-------|----------|-----|
| `cancellation_reason` | `detail_cancelled.html` L34 | Add `TextField(blank=True, default='')` |

## Appendix B: Hub Features That Complement (Not Duplicate) Detail

The following Hub features provide context that the detail page can *reference* without duplicating:

| Hub Feature | Detail Page Role |
|-------------|-----------------|
| Hub Overview — Countdown + Check-in | Detail shows countdown too (✅ already works), but does NOT have check-in action |
| Hub Match Lobby — Active matches with lobby codes | Detail shows match scores (read-only), Hub has operational tools |
| Hub Squad — Roster management + swaps | Detail shows participant list (read-only), Hub has editing |
| Hub Bracket — Interactive zoomable bracket | Detail shows mini bracket, Hub has full interactive |
| Hub Standings — "You" highlight | Detail shows public standings, Hub personalizes |
| Hub Prizes — Claim flow with payment methods | Detail shows prize pool info, Hub has claim actions |
| Hub Resources — Full social/rules/sponsors | Detail shows summary, Hub has comprehensive view |
| Hub Support — Ticket submission + FAQ | Detail has NO support (correct — that's private) |

---

*Audit v3 — March 2026*  
*Full platform context: 25+ apps, 11 games, 78 model fields, 3,618 detail lines, 2,191 Hub lines*  
*Philosophy: Detail = Public Stage, Hub = Private War Room, ecosystem-connected, game-dynamic, career-contextualized*
